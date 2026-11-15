"""P-1 physics validation suite (docs/stage1/e-acceptance-tests.md §B).

Expected values are computed from library constants at test time, never
hand-typed (I-12); the one literal below (502 nm) is a coarse sanity bracket,
not an expected value.
"""

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import minimize_scalar

from lattice.physics.constants import b_wien, sigma_sb
from lattice.physics.planck import planck_lambda, wien_lambda_max, wien_temperature
from lattice.tools.stellar import blackbody_fit, wien
from lattice.tools.contract import convert_and_validate
from tests.conftest import synthetic_spectrum_csv


def test_p1_1_wien_identity():
    for t in (300.0, 5772.0, 30000.0):
        assert wien_lambda_max(t) * t == pytest.approx(b_wien, rel=1e-12)
        assert wien_temperature(b_wien / t) == pytest.approx(t, rel=1e-12)


def test_p1_2_solar_peak_wavelength():
    lam = wien_lambda_max(5772.0)
    assert lam == pytest.approx(b_wien / 5772.0, rel=1e-12)
    assert 490e-9 < lam < 515e-9  # coarse bracket: ~502 nm


def test_p1_3_planck_integral_vs_stefan_boltzmann():
    for t in (3000.0, 5772.0, 10000.0):
        peak = wien_lambda_max(t)
        total, _err = quad(
            lambda wl: planck_lambda(wl, t),
            1e-9,
            1e-2,
            points=[peak, 5 * peak, 20 * peak],
            limit=300,
        )
        expected = sigma_sb * t**4 / np.pi
        assert total == pytest.approx(expected, rel=1e-6)


def test_p1_4_numeric_peak_matches_wien():
    for t in (4000.0, 5772.0, 9000.0):
        res = minimize_scalar(
            lambda wl: -planck_lambda(wl, t),
            bounds=(b_wien / t / 5, b_wien / t * 5),
            method="bounded",
            options={"xatol": 1e-16},
        )
        assert res.x == pytest.approx(b_wien / t, rel=1e-8)


def test_p1_6_fit_recovers_known_temperature():
    t_true = 6000.0
    for seed in (1, 2, 3):
        csv = synthetic_spectrum_csv(t_eff=t_true, noise=0.01, seed=seed)
        rows = csv.decode().strip().splitlines()[1:]
        wl_nm, flux = zip(*(map(float, r.split(",")) for r in rows))
        result = blackbody_fit.execute(
            {},
            {"spectrum": {"wavelength": [w * 1e-9 for w in wl_nm], "flux": list(flux)}},
        )
        t_fit = result.scalars["T_eff"]["value"]
        sigma = result.scalars["T_eff"]["sigma"]
        assert abs(t_fit - t_true) < 4 * sigma
        assert t_fit == pytest.approx(t_true, rel=0.01)
        assert all(check.passed for check in result.checks)


def test_p1_8_unit_handling_nm_vs_m():
    contract = wien.CONTRACT
    params_nm = convert_and_validate(contract, {"lambda_max": {"value": 502.0, "unit": "nm"}})
    params_m = convert_and_validate(contract, {"lambda_max": {"value": 502.0e-9, "unit": "m"}})
    t_nm = wien.execute(params_nm, {}).scalars["T_eff"]["value"]
    t_m = wien.execute(params_m, {}).scalars["T_eff"]["value"]
    assert t_nm == pytest.approx(t_m, rel=1e-12)
    # Angstrom too
    params_aa = convert_and_validate(
        contract, {"lambda_max": {"value": 5020.0, "unit": "Angstrom"}}
    )
    assert wien.execute(params_aa, {}).scalars["T_eff"]["value"] == pytest.approx(
        t_nm, rel=1e-12
    )


def test_p1_9_guard_present():
    result = wien.execute({"lambda_max": 5.02e-7}, {})
    assert result.scalars["T_eff"]["unit"] == "K"
    assert any("composition" in g for g in wien.CONTRACT.guards)
    assert any("composition" in g for g in blackbody_fit.CONTRACT.guards)


def test_input_validation_rejects_bad_units_and_ranges():
    contract = wien.CONTRACT
    from lattice.tools.contract import InputValidationError

    with pytest.raises(InputValidationError, match="not convertible"):
        convert_and_validate(contract, {"lambda_max": {"value": 1.0, "unit": "kg"}})
    with pytest.raises(InputValidationError, match="below the minimum"):
        convert_and_validate(contract, {"lambda_max": {"value": -5, "unit": "nm"}})
    with pytest.raises(InputValidationError, match="required input missing"):
        convert_and_validate(contract, {})
