"""P-3 rectangular-barrier physics validation anchors in SI units."""

import numpy as np
import pytest

from lattice.physics.constants import e_charge, h, m_e
from lattice.tools.contract import convert_and_validate
from lattice.tools.tunneling import CONTRACT, SWEEP_CONTRACT, execute, execute_sweep, transmission_probability

HBAR = h / (2.0 * np.pi)
EV = e_charge
NM = 1e-9


def test_subbarrier_formula_and_independent_amplitude_solver_grid():
    mass = m_e
    barrier = 1.0 * EV
    for energy_fraction in (0.1, 0.5, 0.9):
        energy = energy_fraction * barrier
        for width_nm in (0.1, 0.5, 1.0):
            width = width_nm * NM
            kappa = np.sqrt(2 * mass * (barrier - energy)) / HBAR
            expected = 1.0 / (1.0 + barrier**2 * np.sinh(kappa * width) ** 2 / (4 * energy * (barrier - energy)))
            assert transmission_probability(energy, barrier, width, mass) == pytest.approx(expected, rel=1e-12)
            result = execute({"energy": energy, "barrier_height": barrier, "width": width, "mass": mass}, {})
            assert all(check.passed for check in result.checks)


def test_above_barrier_resonance_and_probability_closure():
    mass = m_e
    barrier = 2.0 * EV
    energy = 3.0 * EV
    width = np.pi * HBAR / np.sqrt(2 * mass * (energy - barrier))
    assert transmission_probability(energy, barrier, width, mass) == pytest.approx(1.0, abs=1e-12)
    for e in (0.5 * EV, barrier, 3.0 * EV):
        t = transmission_probability(e, barrier, 0.4 * NM, mass)
        assert 0 <= t <= 1
        assert t + (1 - t) == pytest.approx(1.0, abs=1e-15)


def test_threshold_continuity_and_limits():
    barrier = EV
    width = 0.2 * NM
    mass = m_e
    threshold = 1.0 / (1.0 + mass * width**2 * barrier / (2 * HBAR**2))
    assert transmission_probability(barrier * (1 - 1e-8), barrier, width, mass) == pytest.approx(threshold, rel=1e-6)
    assert transmission_probability(barrier * (1 + 1e-8), barrier, width, mass) == pytest.approx(threshold, rel=1e-6)
    threshold_run = execute({"energy": barrier, "barrier_height": barrier, "width": width, "mass": mass}, {})
    assert all(check.passed for check in threshold_run.checks)
    assert all(np.isfinite(value) for value in threshold_run.arrays["wavefunction"]["columns"]["probability_density"])
    assert transmission_probability(0.5 * EV, barrier, 0.0, mass) == 1.0
    assert transmission_probability(1e-8 * EV, barrier, 0.5 * NM, mass) < 1e-6
    assert transmission_probability(1e6 * EV, barrier, 0.5 * NM, mass) > 0.99


def test_inverse_width_round_trip_and_nonuniqueness_caveat():
    energy, barrier, width, mass = 0.5 * EV, EV, 0.4 * NM, m_e
    target = transmission_probability(energy, barrier, width, mass)
    result = execute({"energy": energy, "barrier_height": barrier, "width": 0.1 * NM, "mass": mass, "target_transmission": target}, {})
    assert result.scalars["inverse_width"]["value"] == pytest.approx(width, rel=1e-6)
    assert any("same transmission" in guard for guard in CONTRACT.guards)
    assert any(check.name == "inverse_round_trip" and check.passed for check in result.checks)


def test_unit_conversion_electron_volts_nanometres_and_electron_mass():
    converted = convert_and_validate(
        CONTRACT,
        {"energy": {"value": 1.0, "unit": "eV"}, "barrier_height": {"value": 2.0, "unit": "eV"}, "width": {"value": 1.0, "unit": "nm"}, "mass": {"value": m_e, "unit": "kg"}},
    )
    assert converted["energy"] == pytest.approx(EV, rel=1e-12)
    assert converted["width"] == pytest.approx(NM)
    assert transmission_probability(converted["energy"], converted["barrier_height"], converted["width"], converted["mass"]) > 0


def test_energy_sweep_saves_probability_series_and_closes():
    inputs = convert_and_validate(
        SWEEP_CONTRACT,
        {"energy_min": {"value": 0.1, "unit": "eV"}, "energy_max": {"value": 2.0, "unit": "eV"},
         "barrier_height": {"value": 1.0, "unit": "eV"}, "width": {"value": 0.3, "unit": "nm"},
         "points": {"value": 31}},
    )
    result = execute_sweep(inputs, {})
    columns = result.arrays["energy_sweep"]["columns"]
    assert len(columns["energy"]) == 31
    assert all(0.0 <= t <= 1.0 for t in columns["transmission"])
    assert all(check.passed for check in result.checks)
