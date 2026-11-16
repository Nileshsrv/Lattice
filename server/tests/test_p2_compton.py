"""P-2 Compton physics validation anchors."""

import numpy as np
import pytest
from scipy import constants as scipy_constants

from lattice.physics.constants import c, h, m_e, thomson_cross_section
from lattice.tools.compton import CONTRACT, execute
from lattice.tools.contract import convert_and_validate


def run(energy, angle):
    params = convert_and_validate(
        CONTRACT,
        {"photon_energy": {"value": energy, "unit": "J"}, "angle": {"value": angle, "unit": "rad"}},
    )
    return execute(params, {})


def test_p2_compton_shift_endpoints_and_wavelength_energy_consistency():
    compton_wavelength = h / (m_e * c)
    assert run(1e-14, 0.0).scalars["wavelength_shift"]["value"] == 0.0
    for angle, expected in ((np.pi, 2 * compton_wavelength), (np.pi / 2, compton_wavelength)):
        result = run(1e-14, angle)
        assert result.scalars["wavelength_shift"]["value"] == pytest.approx(expected, rel=1e-12)
        energy = 1e-14
        predicted_energy = energy / (1 + energy / (m_e * c**2) * (1 - np.cos(angle)))
        wavelength_energy = energy / (1 + energy * expected / (h * c))
        assert result.scalars["scattered_energy"]["value"] == pytest.approx(predicted_energy, rel=1e-12)
        assert predicted_energy == pytest.approx(wavelength_energy, rel=1e-12)


def test_p2_symbolic_anchor_and_conservation_grid():
    energy = m_e * c**2
    result = run(energy, np.pi / 2)
    assert result.scalars["scattered_energy"]["value"] == pytest.approx(energy / 2, rel=1e-12)
    assert result.scalars["electron_kinetic_energy"]["value"] == pytest.approx(energy / 2, rel=1e-12)
    for incident in np.geomspace(1e-18, 1e-11, 8):
        for angle in np.linspace(0, np.pi, 13):
            checks = {check.name: check.passed for check in run(incident, angle).checks}
            assert checks["energy_conservation"]
            assert checks["momentum_conservation"]


def test_p2_scattered_energy_decreases_with_angle_and_kn_is_nonnegative():
    energies = [run(m_e * c**2, angle).scalars["scattered_energy"]["value"] for angle in np.linspace(0, np.pi, 181)]
    assert all(left > right for left, right in zip(energies, energies[1:]))
    curve = run(m_e * c**2, np.pi / 4).arrays["geometry"]["columns"]["differential_cross_section"]
    assert min(curve) >= 0


def test_p2_thomson_limit_and_target_assumption():
    result = run(m_e * c**2 * 1e-7, np.pi / 3)
    total = result.scalars["total_cross_section"]["value"]
    assert total == pytest.approx(thomson_cross_section, rel=1e-4)
    assert scipy_constants.physical_constants["Thomson cross section"][0] == thomson_cross_section
    assert CONTRACT.method.settings["target"] == "free electron at rest"
    assert any("free electron at rest" in guard for guard in CONTRACT.guards)


def test_p2_contract_accepts_degree_and_energy_units():
    params = convert_and_validate(
        CONTRACT,
        {"photon_energy": {"value": 511, "unit": "keV"}, "angle": {"value": 90, "unit": "deg"}},
    )
    assert params["photon_energy"] == pytest.approx(m_e * c**2, rel=1e-3)
    assert params["angle"] == pytest.approx(np.pi / 2)
