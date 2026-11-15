"""Executable form of the tool contract (docs/stage1/c-schemas.md §7).

Inputs are validated and unit-converted BEFORE execution; out-of-range values
are rejected with the violated constraint named, never clamped (I-5 adjacent,
c-schemas §7 rules).
"""

from typing import Any, Callable, Literal

import numpy as np
from astropy import units as u
from pydantic import BaseModel, Field


class ScalarInputSpec(BaseModel):
    name: str
    label: str
    quantity: str                     # physical quantity, e.g. "wavelength"
    canonical_unit: str               # SI unit inputs are converted to, e.g. "m"
    minimum: float | None = None      # bounds in canonical unit, exclusive of None
    maximum: float | None = None
    default: float | None = None      # in canonical unit
    required: bool = True


class DatasetInputSpec(BaseModel):
    name: str
    label: str
    required_columns: list[dict]      # [{name, quantity, canonical_unit}]


class OutputSpec(BaseModel):
    name: str
    label: str
    unit: str                         # "" means dimensionless (I-9: explicit)
    kind: Literal["scalar", "array", "table"] = "scalar"


class ModelSpec(BaseModel):
    name: str
    equations: list[str]
    assumptions: list[str]
    validity: list[str]


class MethodSpec(BaseModel):
    name: str
    settings: dict[str, Any] = Field(default_factory=dict)


class ToolContract(BaseModel):
    id: str
    name: str
    version: str
    domain: str
    tags: list[str] = Field(default_factory=list)
    maturity: Literal["validated-method", "educational-model", "experimental", "beta"]
    category: Literal["instant", "long-running", "specialised"]
    inputs: list[ScalarInputSpec] = Field(default_factory=list)
    dataset_inputs: list[DatasetInputSpec] = Field(default_factory=list)
    outputs: list[OutputSpec] = Field(default_factory=list)
    model: ModelSpec
    method: MethodSpec
    guards: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    license: str = "MIT"


class CheckResult(BaseModel):
    name: str
    passed: bool
    detail: str


class ToolResult(BaseModel):
    # scalar outputs: {name: {"value": float, "unit": str, "sigma": float | None}}
    scalars: dict[str, dict] = Field(default_factory=dict)
    # array outputs: {name: {"columns": {col: list[float]}, "units": {col: str}}}
    arrays: dict[str, dict] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)


ToolFn = Callable[[dict[str, float], dict[str, dict]], ToolResult]


class InputValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def convert_and_validate(
    contract: ToolContract, raw_inputs: dict[str, dict]
) -> dict[str, float]:
    """raw_inputs: {name: {"value": number, "unit": "nm"}} → canonical-unit floats."""
    errors: list[str] = []
    converted: dict[str, float] = {}
    for spec in contract.inputs:
        raw = raw_inputs.get(spec.name)
        if raw is None:
            if spec.default is not None:
                converted[spec.name] = spec.default
                continue
            if not spec.required:
                continue
            errors.append(f"{spec.name}: required input missing")
            continue
        try:
            value = float(raw["value"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{spec.name}: value must be a number")
            continue
        if not np.isfinite(value):
            errors.append(f"{spec.name}: value must be finite")
            continue
        unit_str = raw.get("unit", spec.canonical_unit)
        try:
            quantity = value * u.Unit(unit_str)
            canonical = quantity.to(u.Unit(spec.canonical_unit)).value
        except Exception:
            errors.append(
                f"{spec.name}: unit '{unit_str}' is not convertible to "
                f"'{spec.canonical_unit}' ({spec.quantity})"
            )
            continue
        if spec.minimum is not None and canonical < spec.minimum:
            errors.append(
                f"{spec.name}: {canonical} {spec.canonical_unit} is below the "
                f"minimum {spec.minimum} {spec.canonical_unit}"
            )
            continue
        if spec.maximum is not None and canonical > spec.maximum:
            errors.append(
                f"{spec.name}: {canonical} {spec.canonical_unit} is above the "
                f"maximum {spec.maximum} {spec.canonical_unit}"
            )
            continue
        converted[spec.name] = float(canonical)
    for name in raw_inputs:
        if name not in {s.name for s in contract.inputs}:
            errors.append(f"{name}: not an input of tool {contract.id}")
    if errors:
        raise InputValidationError(errors)
    return converted
