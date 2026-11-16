"""One-dimensional rectangular-barrier transmission with analytic cross-check."""

import numpy as np
from scipy.linalg import solve

from ..physics.constants import h, m_e
from .contract import CheckResult, ModelSpec, MethodSpec, OutputSpec, ScalarInputSpec, ToolContract, ToolResult

HBAR = h / (2.0 * np.pi)
INVERSE_CAVEAT = "Barrier width is inferred only within the stated 1-D rectangular-barrier model; other potentials or masses can produce the same transmission."

CONTRACT = ToolContract(
    id="quantum.rectangular_tunneling",
    name="Quantum Tunnelling Lab",
    version="0.1.0",
    domain="quantum mechanics",
    tags=["quantum", "tunnelling", "barrier"],
    maturity="validated-method",
    category="instant",
    inputs=[
        ScalarInputSpec(name="energy", label="Particle energy", quantity="energy", canonical_unit="J", minimum=0.0),
        ScalarInputSpec(name="barrier_height", label="Barrier height", quantity="energy", canonical_unit="J", minimum=0.0),
        ScalarInputSpec(name="width", label="Barrier width", quantity="length", canonical_unit="m", minimum=0.0),
        ScalarInputSpec(name="mass", label="Particle mass", quantity="mass", canonical_unit="kg", minimum=0.0, default=m_e),
        ScalarInputSpec(name="target_transmission", label="Target transmission (optional inverse estimate)", quantity="dimensionless", canonical_unit="", minimum=0.0, maximum=1.0, required=False),
    ],
    outputs=[
        OutputSpec(name="transmission", label="Transmission probability", unit=""),
        OutputSpec(name="reflection", label="Reflection probability", unit=""),
        OutputSpec(name="inverse_width", label="Inferred width for target transmission", unit="m"),
        OutputSpec(name="barrier_profile", label="Potential profile", unit="", kind="array"),
        OutputSpec(name="wavefunction", label="Wavefunction probability density", unit="", kind="array"),
    ],
    model=ModelSpec(
        name="1-D rectangular potential barrier",
        equations=["E < V₀: T = [1 + V₀² sinh²(κa)/(4E(V₀−E))]⁻¹", "κ = √(2m(V₀−E))/ħ", "R = 1 − T"],
        assumptions=["Single non-relativistic particle in a one-dimensional rectangular barrier", "Potential is zero outside and V₀ within the barrier"],
        validity=["Schrödinger model; invalid when relativistic effects or non-1-D structure dominate", "Near E=V₀ the continuous limiting expression is used"],
    ),
    method=MethodSpec(name="analytic transfer-matrix solution with independent closed-form cross-check", settings={"probability_tolerance": 1e-10, "thick_barrier_asymptote_kappa_a": 5.0}),
    guards=[INVERSE_CAVEAT],
    references=["Time-independent Schrödinger equation for a rectangular potential barrier"],
)


def _dimensionless_strength(energy: float, barrier: float, width: float, mass: float) -> float:
    if width == 0.0 or barrier == 0.0:
        return 0.0
    delta = energy - barrier
    scale = 2.0 * mass * width**2 / HBAR**2
    if abs(delta) <= np.finfo(float).eps * max(energy, barrier):
        return scale * barrier / 4.0
    if delta < 0.0:
        kappa_width = np.sqrt(-delta * scale)
        sinh_value = np.sinh(kappa_width) if kappa_width < 350.0 else np.inf
        return barrier**2 * sinh_value**2 / (4.0 * energy * (barrier - energy))
    wave_width = np.sqrt(delta * scale)
    return barrier**2 * np.sin(wave_width)**2 / (4.0 * energy * delta)


def transmission_probability(energy: float, barrier: float, width: float, mass: float) -> float:
    if energy <= 0.0 or barrier < 0.0 or width < 0.0 or mass <= 0.0:
        raise ValueError("energy and mass must be positive; barrier and width must be nonnegative")
    strength = _dimensionless_strength(energy, barrier, width, mass)
    if np.isinf(strength):
        return 0.0
    return float(1.0 / (1.0 + strength))


def _scattering_amplitudes(energy: float, barrier: float, width: float, mass: float) -> tuple[complex, complex, complex, complex]:
    """Solve the four wave-amplitude boundary conditions independently."""
    if width == 0.0 or barrier == 0.0:
        return 0j, 1.0 + 0j, 0j, 1.0 + 0j
    wave_number = np.sqrt(2.0 * mass * energy) / HBAR
    interior = np.sqrt(2.0 * mass * (energy - barrier) + 0j) / HBAR
    if abs(interior) <= np.finfo(float).eps * wave_number:
        phase_width = wave_number * width
        matrix = np.array([
            [1.0, -1.0, 0.0, 0.0],
            [-1j, 0.0, -1.0 / phase_width, 0.0],
            [0.0, 1.0, 1.0, -1.0],
            [0.0, 0.0, 1.0, -1j * phase_width],
        ], dtype=complex)
        reflection, inside_value, scaled_slope, transmission = solve(
            matrix, np.array([-1.0, -1j, 0.0, 0.0], dtype=complex)
        )
        return reflection, inside_value, scaled_slope / width, transmission
    left_phase = np.exp(1j * interior * width)
    right_phase = np.exp(1j * wave_number * width)
    matrix = np.array([
        [1.0, -1.0, -1.0, 0.0],
        [-1j * wave_number, -1j * interior, 1j * interior, 0.0],
        [0.0, left_phase, 1.0 / left_phase, -right_phase],
        [0.0, 1j * interior * left_phase, -1j * interior / left_phase, -1j * wave_number * right_phase],
    ], dtype=complex)
    amplitudes = solve(matrix, np.array([-1.0, -1j * wave_number, 0.0, 0.0], dtype=complex))
    return tuple(complex(value) for value in amplitudes)


def _transfer_matrix_transmission(energy: float, barrier: float, width: float, mass: float) -> float:
    if abs(energy - barrier) <= np.finfo(float).eps * max(energy, barrier):
        return float(1.0 / (1.0 + mass * width**2 * barrier / (2.0 * HBAR**2)))
    amplitudes = _scattering_amplitudes(energy, barrier, width, mass)
    return float(abs(amplitudes[3]) ** 2)


def execute(params: dict[str, float], _data: dict[str, dict]) -> ToolResult:
    energy = params["energy"]
    barrier = params["barrier_height"]
    width = params["width"]
    mass = params["mass"]
    transmission = transmission_probability(energy, barrier, width, mass)
    reflection = 1.0 - transmission
    inverse_width = None
    target = params.get("target_transmission")
    if target is not None:
        if not 0.0 < target < 1.0 or not 0.0 < energy < barrier:
            raise ValueError("inverse width requires 0 < target transmission < 1 and 0 < energy < barrier height")
        kappa = np.sqrt(2.0 * mass * (barrier - energy)) / HBAR
        factor = barrier**2 / (4.0 * energy * (barrier - energy))
        inverse_width = float(np.arcsinh(np.sqrt((1.0 / target - 1.0) / factor)) / kappa)

    if width > 0.0 and 0.0 < energy < barrier and np.sqrt(2.0 * mass * (barrier - energy)) * width / HBAR >= 350.0:
        positions = np.concatenate((np.linspace(-width, 0.0, 67), np.linspace(0.0, width, 67), np.linspace(width, 2.0 * width, 67)))
        density = np.exp(-2.0 * np.sqrt(2.0 * mass * (barrier - energy)) * np.maximum(positions, 0.0) / HBAR)
        density[positions > width] *= transmission
    else:
        positions = np.concatenate((np.linspace(-width, 0.0, 67), np.linspace(0.0, width, 67), np.linspace(width, 2.0 * width, 67))) if width else np.linspace(-1e-15, 1e-15, 201)
        reflection_amplitude, inside_forward, inside_backward, transmission_amplitude = _scattering_amplitudes(energy, barrier, width, mass)
        wave_number = np.sqrt(2.0 * mass * energy) / HBAR
        interior_number = np.sqrt(2.0 * mass * (energy - barrier) + 0j) / HBAR
        density = np.empty_like(positions)
        left = positions < 0.0
        inside = (positions >= 0.0) & (positions <= width)
        right = positions > width
        density[left] = np.abs(np.exp(1j * wave_number * positions[left]) + reflection_amplitude * np.exp(-1j * wave_number * positions[left])) ** 2
        if abs(energy - barrier) <= np.finfo(float).eps * max(energy, barrier):
            density[inside] = np.abs(inside_forward + inside_backward * positions[inside]) ** 2
        else:
            density[inside] = np.abs(inside_forward * np.exp(1j * interior_number * positions[inside]) + inside_backward * np.exp(-1j * interior_number * positions[inside])) ** 2
        density[right] = np.abs(transmission_amplitude * np.exp(1j * wave_number * (positions[right] - width))) ** 2
    transfer_value = _transfer_matrix_transmission(energy, barrier, width, mass)
    thick_ratio = None
    if 0.0 < energy < barrier and width > 0:
        kappa_width = np.sqrt(2.0 * mass * (barrier - energy)) * width / HBAR
        if kappa_width >= CONTRACT.method.settings["thick_barrier_asymptote_kappa_a"]:
            asymptote = 16.0 * (energy / barrier) * (1.0 - energy / barrier) * np.exp(-2.0 * kappa_width)
            thick_ratio = transmission / asymptote if asymptote > 0 else None

    scalars = {
        "transmission": {"value": transmission, "unit": "", "sigma": None},
        "reflection": {"value": reflection, "unit": "", "sigma": None},
    }
    if inverse_width is not None:
        scalars["inverse_width"] = {"value": inverse_width, "unit": "m", "sigma": None}
    checks = [
        CheckResult(name="unitarity", passed=abs(transmission + reflection - 1.0) < 1e-10, detail=f"R + T = {reflection + transmission:.16g}"),
        CheckResult(name="transfer_matrix_crosscheck", passed=bool(np.isclose(transmission, transfer_value, rtol=1e-12, atol=1e-14)), detail=f"analytic T={transmission:.12g}; transfer-matrix T={transfer_value:.12g}"),
    ]
    if inverse_width is not None:
        recovered = transmission_probability(energy, barrier, inverse_width, mass)
        checks.append(CheckResult(name="inverse_round_trip", passed=bool(np.isclose(recovered, target, rtol=1e-6)), detail=f"requested T={target:.8g}; recovered T={recovered:.8g}"))
    if thick_ratio is not None:
        checks.append(CheckResult(name="thick_barrier_asymptote", passed=bool(np.isclose(thick_ratio, 1.0, rtol=1e-3)), detail=f"exact/asymptotic transmission ratio={thick_ratio:.8g}"))

    return ToolResult(
        scalars=scalars,
        arrays={
            "barrier_profile": {"columns": {"position": positions.tolist(), "potential": np.where((positions >= 0) & (positions <= width), barrier, 0.0).tolist()}, "units": {"position": "m", "potential": "J"}},
            "wavefunction": {"columns": {"position": positions.tolist(), "probability_density": density.tolist()}, "units": {"position": "m", "probability_density": "incident-amplitude-squared"}},
        },
        checks=checks,
    )


SWEEP_CONTRACT = ToolContract(
    id="quantum.rectangular_tunneling_sweep",
    name="Quantum Tunnelling — Energy Sweep",
    version="0.1.0",
    domain="quantum mechanics",
    tags=["quantum", "tunnelling", "barrier", "sweep"],
    maturity="validated-method",
    category="instant",
    inputs=[
        ScalarInputSpec(name="energy_min", label="Minimum particle energy", quantity="energy", canonical_unit="J", minimum=0.0),
        ScalarInputSpec(name="energy_max", label="Maximum particle energy", quantity="energy", canonical_unit="J", minimum=0.0),
        ScalarInputSpec(name="barrier_height", label="Barrier height", quantity="energy", canonical_unit="J", minimum=0.0),
        ScalarInputSpec(name="width", label="Barrier width", quantity="length", canonical_unit="m", minimum=0.0),
        ScalarInputSpec(name="mass", label="Particle mass", quantity="mass", canonical_unit="kg", minimum=0.0, default=m_e),
        ScalarInputSpec(name="points", label="Number of sweep points", quantity="dimensionless", canonical_unit="", minimum=2.0, maximum=1000.0, default=101.0),
    ],
    outputs=[OutputSpec(name="energy_sweep", label="Transmission and reflection versus energy", unit="", kind="array")],
    model=CONTRACT.model,
    method=MethodSpec(name="uniform energy sweep using the analytic rectangular-barrier solution", settings={"max_points": 1000}),
    guards=CONTRACT.guards,
    references=CONTRACT.references,
)


def execute_sweep(params: dict[str, float], _data: dict[str, dict]) -> ToolResult:
    energy_min = params["energy_min"]
    energy_max = params["energy_max"]
    points_value = params["points"]
    if energy_min <= 0 or energy_max <= energy_min:
        raise ValueError("energy_max must be greater than a positive energy_min")
    if not points_value.is_integer():
        raise ValueError("number of sweep points must be an integer")
    count = int(points_value)
    energies = np.linspace(energy_min, energy_max, count)
    transmission = np.asarray([
        transmission_probability(value, params["barrier_height"], params["width"], params["mass"])
        for value in energies
    ])
    reflection = 1.0 - transmission
    closure = bool(np.all(np.abs(transmission + reflection - 1.0) < 1e-10))
    return ToolResult(
        arrays={"energy_sweep": {
            "columns": {"energy": energies.tolist(), "transmission": transmission.tolist(), "reflection": reflection.tolist()},
            "units": {"energy": "J", "transmission": "", "reflection": ""},
        }},
        checks=[CheckResult(name="probability_closure", passed=closure, detail="R + T = 1 at every energy in the sweep")],
    )
