"""Tool registry: id → (contract, execute). Runs pin the contract version they used."""

from .contract import ToolContract, ToolFn
from .stellar import blackbody_fit, wien
from . import compton
from . import tunneling
from . import analysis

_REGISTRY: dict[str, tuple[ToolContract, ToolFn]] = {
    wien.CONTRACT.id: (wien.CONTRACT, wien.execute),
    blackbody_fit.CONTRACT.id: (blackbody_fit.CONTRACT, blackbody_fit.execute),
    compton.CONTRACT.id: (compton.CONTRACT, compton.execute),
    tunneling.CONTRACT.id: (tunneling.CONTRACT, tunneling.execute),
    tunneling.SWEEP_CONTRACT.id: (tunneling.SWEEP_CONTRACT, tunneling.execute_sweep),
    analysis.CONTRACT.id: (analysis.CONTRACT, analysis.execute),
    analysis.GAUSSIAN_CONTRACT.id: (analysis.GAUSSIAN_CONTRACT, analysis.execute_gaussian),
    analysis.PROPAGATION_CONTRACT.id: (analysis.PROPAGATION_CONTRACT, analysis.execute_propagation),
}


def contracts() -> list[ToolContract]:
    return [contract for contract, _fn in _REGISTRY.values()]


def get(tool_id: str) -> tuple[ToolContract, ToolFn]:
    if tool_id not in _REGISTRY:
        raise KeyError(f"unknown tool: {tool_id}")
    return _REGISTRY[tool_id]
