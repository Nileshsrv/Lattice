"""Wien's displacement law temperature estimator."""

from ...physics.planck import wien_temperature
from ..contract import (
    CheckResult,
    ModelSpec,
    MethodSpec,
    OutputSpec,
    ScalarInputSpec,
    ToolContract,
    ToolResult,
)

COMPOSITION_GUARD = (
    "This estimates an effective temperature under stated assumptions. "
    "It does not determine elemental composition; composition requires spectral-line "
    "measurements, atomic data, and more advanced modelling."
)

CONTRACT = ToolContract(
    id="stellar.wien_temperature",
    name="Wien's Displacement Law Calculator",
    version="0.1.0",
    domain="astrophysics",
    tags=["stellar", "blackbody", "temperature"],
    maturity="validated-method",
    category="instant",
    inputs=[
        ScalarInputSpec(
            name="lambda_max",
            label="Peak wavelength",
            quantity="wavelength",
            canonical_unit="m",
            minimum=1e-12,
            maximum=1.0,
        )
    ],
    outputs=[OutputSpec(name="T_eff", label="Effective temperature", unit="K")],
    model=ModelSpec(
        name="Wien displacement law",
        equations=[r"\lambda_{max} T = b"],
        assumptions=[
            "The spectrum is well approximated by a blackbody continuum near its peak",
            "lambda_max is the true peak of the spectral radiance per unit wavelength",
        ],
        validity=[
            "Requires the actual continuum peak; a peak outside the observed window "
            "or distorted by strong lines invalidates the estimate"
        ],
    ),
    method=MethodSpec(name="analytic identity", settings={}),
    guards=[COMPOSITION_GUARD],
    references=["Wien displacement constant b: CODATA via scipy.constants"],
)


def execute(params: dict[str, float], _data: dict[str, dict]) -> ToolResult:
    temperature = wien_temperature(params["lambda_max"])
    return ToolResult(
        scalars={"T_eff": {"value": temperature, "unit": "K", "sigma": None}},
        checks=[
            CheckResult(
                name="physical_range",
                passed=temperature > 0,
                detail=f"T_eff = {temperature:.6g} K > 0",
            )
        ],
    )
