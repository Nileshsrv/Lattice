"""P-4 Scientific Analysis Lab validation anchors."""

import numpy as np
import pytest

from lattice.tools.analysis import CONTRACT, GAUSSIAN_CONTRACT, PROPAGATION_CONTRACT, execute, execute_gaussian, execute_propagation


def test_exact_linear_regression_and_residuals():
    x = np.arange(-4.0, 5.0)
    y = 2.5 * x - 3.0
    result = execute({}, {"observations": {"x": x.tolist(), "y": y.tolist()}})
    assert result.scalars["slope"]["value"] == pytest.approx(2.5, rel=1e-12)
    assert result.scalars["intercept"]["value"] == pytest.approx(-3.0, abs=1e-12)
    assert result.scalars["r_squared"]["value"] == pytest.approx(1.0)
    assert max(abs(value) for value in result.arrays["residuals"]["columns"]["residual"]) < 1e-12


def test_seeded_linear_fit_has_uncertainty_and_interval_cover():
    rng = np.random.default_rng(194)
    x = np.linspace(-2, 2, 80)
    y = 1.7 * x + 0.4 + rng.normal(0, 0.25, size=x.size)
    result = execute({}, {"observations": {"x": x.tolist(), "y": y.tolist()}})
    values = result.scalars
    assert abs(values["slope"]["value"] - 1.7) < 3 * values["slope_standard_error"]["value"]
    assert values["slope_ci_low"]["value"] < 1.7 < values["slope_ci_high"]["value"]


def test_bad_inputs_rejected_and_residual_diagnostic_flags_wrong_model():
    with pytest.raises(ValueError, match="at least three"):
        execute({}, {"observations": {"x": [1, 2], "y": [2, 4]}})
    assert any("does not establish causation" in guard for guard in CONTRACT.guards)
    x = np.linspace(-3, 3, 90)
    wrong_model_y = x**2 + np.random.default_rng(72).normal(0, 0.01, x.size)
    checks = {check.name: check for check in execute({}, {"observations": {"x": x.tolist(), "y": wrong_model_y.tolist()}}).checks}
    assert not checks["residual_normality_diagnostic"].passed
    assert "D’Agostino–Pearson" in checks["residual_normality_diagnostic"].detail


def test_gaussian_fit_recovers_seeded_peak_parameters():
    rng = np.random.default_rng(52)
    x = np.linspace(-5, 5, 301)
    y = 4.2 * np.exp(-0.5 * ((x - 0.65) / 0.82) ** 2) + 0.3 + rng.normal(0, 0.015, x.size)
    result = execute_gaussian({}, {"observations": {"x": x.tolist(), "y": y.tolist()}})
    assert result.scalars["amplitude"]["value"] == pytest.approx(4.2, rel=0.01)
    assert result.scalars["mean"]["value"] == pytest.approx(0.65, abs=0.01)
    assert result.scalars["sigma"]["value"] == pytest.approx(0.82, rel=0.01)
    assert set(result.arrays["gaussian_fit"]["columns"]) == {"x", "observed", "fitted", "residual"}
    assert GAUSSIAN_CONTRACT.dataset_inputs


def test_independent_sum_and_product_error_propagation():
    result = execute_propagation({"x": 3.0, "sigma_x": 0.4, "y": 5.0, "sigma_y": 0.2}, {})
    assert result.scalars["sum"]["value"] == 8.0
    assert result.scalars["sum_sigma"]["value"] == pytest.approx(np.hypot(0.4, 0.2))
    assert result.scalars["product"]["value"] == 15.0
    assert result.scalars["product_sigma"]["value"] == pytest.approx(np.hypot(5 * 0.4, 3 * 0.2))
    assert PROPAGATION_CONTRACT.id == "analysis.independent_error_propagation"
