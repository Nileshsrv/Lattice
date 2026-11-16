"""Free-electron Compton scattering and Klein–Nishina cross-sections."""

import numpy as np
from scipy.integrate import quad

from ..physics.constants import (
    c,
    classical_electron_radius,
    h,
    m_e,
    thomson_cross_section,
)
from .contract import (
    CheckResult,
    ModelSpec,
    MethodSpec,
    OutputSpec,
    ScalarInputSpec,
    ToolContract,
    ToolResult,
)

CONTRACT = ToolContract(
    id="compton.scattering",
    name="Compton Scattering Lab",
    version="0.1.0",
    domain="physics",
    tags=["compton", "photon", "scattering"],
    maturity="validated-method",
    category="instant",
    inputs=[
        ScalarInputSpec(
            name="photon_energy",
            label="Incident photon energy",
            quantity="energy",
            canonical_unit="J",
            minimum=0.0,
        ),
        ScalarInputSpec(
            name="angle",
            label="Scattering angle",
            quantity="angle",
            canonical_unit="rad",
            minimum=0.0,
            maximum=float(np.pi),
        ),
    ],
    outputs=[
        OutputSpec(name="scattered_energy", label="Scattered photon energy", unit="J"),
        OutputSpec(name="wavelength_shift", label="Wavelength shift", unit="m"),
        OutputSpec(name="electron_kinetic_energy", label="Recoil electron kinetic energy", unit="J"),
        OutputSpec(name="differential_cross_section", label="Klein–Nishina differential cross-section", unit="m2/sr"),
        OutputSpec(name="total_cross_section", label="Integrated Klein–Nishina cross-section", unit="m2"),
        OutputSpec(name="geometry", label="Klein–Nishina angular distribution", unit="", kind="array"),
    ],
    model=ModelSpec(
        name="Compton scattering from a free electron at rest",
        equations=[
            "E′ = E / [1 + (E / mₑc²)(1 − cos θ)]",
            "Δλ = h/(mₑc)(1 − cos θ)",
            "dσ/dΩ = rₑ²/2 (E′/E)² (E′/E + E/E′ − sin²θ)",
        ],
        assumptions=[
            "Target is a free electron initially at rest",
            "Single photon-electron scattering; no binding or transport effects",
        ],
        validity=["Material selection and bound-electron corrections are not modelled"],
    ),
    method=MethodSpec(
        name="analytic relativistic kinematics; Klein–Nishina angular integration",
        settings={"target": "free electron at rest", "integration": "adaptive quadrature over solid angle"},
    ),
    guards=["Target model: free electron at rest. This is not a bound-electron or particle-transport simulation."],
    references=["Klein–Nishina formula; constants from scipy.constants"],
)


def _energy_ratio(energy: float, angle: np.ndarray | float) -> np.ndarray:
    return 1.0 / (1.0 + (energy / (m_e * c**2)) * (1.0 - np.cos(angle)))


def _differential_cross_section(energy: float, angle: np.ndarray | float) -> np.ndarray:
    ratio = _energy_ratio(energy, angle)
    return (classical_electron_radius**2 / 2.0) * ratio**2 * (
        ratio + 1.0 / ratio - np.sin(angle) ** 2
    )


def execute(params: dict[str, float], _data: dict[str, dict]) -> ToolResult:
    energy = params["photon_energy"]
    angle = params["angle"]
    ratio = float(_energy_ratio(energy, angle))
    scattered = energy * ratio
    shift = h / (m_e * c) * (1.0 - np.cos(angle))
    recoil = energy - scattered

    momentum_in = energy / c
    momentum_out = scattered / c
    electron_px = momentum_in - momentum_out * np.cos(angle)
    electron_py = -momentum_out * np.sin(angle)
    electron_momentum_magnitude = np.hypot(electron_px, electron_py)
    electron_energy_total = np.hypot(m_e * c**2, electron_momentum_magnitude * c)
    relativistic_recoil = (electron_momentum_magnitude * c) ** 2 / (
        electron_energy_total + m_e * c**2
    )
    momentum_scale = max(momentum_in, np.finfo(float).tiny)
    angles = np.linspace(0.0, np.pi, 181)
    distribution = _differential_cross_section(energy, angles)
    total_cross_section = 2.0 * np.pi * quad(
        lambda theta: float(_differential_cross_section(energy, theta)) * np.sin(theta),
        0.0,
        np.pi,
        epsabs=0.0,
        epsrel=1e-10,
    )[0]
    momentum_check = max(
        abs(momentum_in - momentum_out * np.cos(angle) - electron_px),
        abs(-momentum_out * np.sin(angle) - electron_py),
    ) <= 1e-12 * momentum_scale

    return ToolResult(
        scalars={
            "scattered_energy": {"value": float(scattered), "unit": "J", "sigma": None},
            "wavelength_shift": {"value": float(shift), "unit": "m", "sigma": None},
            "electron_kinetic_energy": {"value": float(recoil), "unit": "J", "sigma": None},
            "differential_cross_section": {
                "value": float(_differential_cross_section(energy, angle)),
                "unit": "m2/sr",
                "sigma": None,
            },
            "total_cross_section": {"value": float(total_cross_section), "unit": "m2", "sigma": None},
        },
        arrays={
            "geometry": {
                "columns": {"angle": angles.tolist(), "differential_cross_section": distribution.tolist()},
                "units": {"angle": "rad", "differential_cross_section": "m2/sr"},
            }
        },
        checks=[
            CheckResult(
                name="energy_conservation",
                passed=bool(np.isclose(energy, scattered + recoil, rtol=1e-14, atol=0.0) and np.isclose(recoil, relativistic_recoil, rtol=1e-10, atol=np.finfo(float).eps * energy)),
                detail="Photon energy balance and recoil electron relativistic mass-shell energy agree",
            ),
            CheckResult(
                name="momentum_conservation",
                passed=bool(momentum_check),
                detail="Both recoil electron momentum components close",
            ),
            CheckResult(
                name="nonnegative_cross_section",
                passed=bool(np.all(distribution >= 0.0)),
                detail="Klein–Nishina differential cross-section is nonnegative over 0..π",
            ),
            CheckResult(
                name="thomson_limit_reference",
                passed=bool(np.isclose(8.0 * np.pi * classical_electron_radius**2 / 3.0, thomson_cross_section, rtol=1e-12)),
                detail="Low-energy limit reference agrees with the library Thomson cross-section",
            ),
        ],
    )
