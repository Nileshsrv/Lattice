"""Tool registry: id → (contract, execute). Runs pin the contract version they used."""

from .contract import ToolContract, ToolFn
from .stellar import blackbody_fit, wien

_REGISTRY: dict[str, tuple[ToolContract, ToolFn]] = {
    wien.CONTRACT.id: (wien.CONTRACT, wien.execute),
    blackbody_fit.CONTRACT.id: (blackbody_fit.CONTRACT, blackbody_fit.execute),
}


def contracts() -> list[ToolContract]:
    return [contract for contract, _fn in _REGISTRY.values()]


def get(tool_id: str) -> tuple[ToolContract, ToolFn]:
    if tool_id not in _REGISTRY:
        raise KeyError(f"unknown tool: {tool_id}")
    return _REGISTRY[tool_id]
