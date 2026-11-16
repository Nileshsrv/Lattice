"""Linear regression for imported, unit-described x/y datasets."""

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import normaltest, t as student_t

from .contract import (
    CheckResult,
    DatasetInputSpec,
    ModelSpec,
    MethodSpec,
    OutputSpec,
    ScalarInputSpec,
    ToolContract,
    ToolResult,
)

CONTRACT = ToolContract(
    id="analysis.linear_regression",
    name="Scientific Analysis — Linear Regression",
    version="0.1.0",
    domain="scientific analysis",
    tags=["regression", "residuals", "uncertainty", "analysis"],
    maturity="validated-method",
    category="instant",
    dataset_inputs=[
        DatasetInputSpec(
            name="observations",
            label="Observations (columns named x and y)",
            required_columns=[
                {"name": "x", "quantity": "independent variable", "canonical_unit": ""},
                {"name": "y", "quantity": "dependent variable", "canonical_unit": ""},
            ],
        )
    ],
    outputs=[
        OutputSpec(name="slope", label="Slope (y units / x units)", unit="y/x"),
        OutputSpec(name="intercept", label="Intercept (y units)", unit="y"),
        OutputSpec(name="r_squared", label="Coefficient of determination", unit=""),
        OutputSpec(name="slope_standard_error", label="Slope standard error", unit="y/x"),
        OutputSpec(name="slope_ci_low", label="Slope 95% confidence interval lower bound", unit="y/x"),
        OutputSpec(name="slope_ci_high", label="Slope 95% confidence interval upper bound", unit="y/x"),
        OutputSpec(name="residuals", label="Fit and residual series", unit="", kind="array"),
    ],
    model=ModelSpec(
        name="Ordinary least squares: y = slope·x + intercept",
        equations=["β̂ = (XᵀX)⁻¹Xᵀy", "s² = RSS/(n−2)", "Cov(β̂) = s²(XᵀX)⁻¹"],
        assumptions=[
            "Observations are independent with correctly specified x and y values",
            "For confidence intervals, residuals are approximately normal with constant variance",
        ],
        validity=["Requires at least three distinct x values and nonzero x variation", "Confidence interval is conditional on the linear model and stated residual assumptions"],
    ),
    method=MethodSpec(name="ordinary least squares with Student-t confidence interval", settings={"confidence_level": 0.95}),
    guards=["Regression estimates association under the selected model; it does not establish causation."],
    references=["Classical ordinary least squares; Student-t inference under linear-model assumptions"],
)


def execute(_params: dict[str, float], data: dict[str, dict]) -> ToolResult:
    x = np.asarray(data["observations"]["x"], dtype=float)
    y = np.asarray(data["observations"]["y"], dtype=float)
    units = data["observations"].get("_units", {})
    x_unit = units.get("x") or "unit unknown"
    y_unit = units.get("y") or "unit unknown"
    slope_unit = f"({y_unit})/({x_unit})"
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size:
        raise ValueError("x and y columns must be one-dimensional arrays with equal lengths")
    if x.size < 3 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("linear regression requires at least three finite x/y observations")
    x_dev = x - np.mean(x)
    sxx = float(np.sum(x_dev**2))
    if sxx <= 0.0 or not np.isfinite(sxx):
        raise ValueError("x values must contain at least two distinct values")
    y_dev = y - np.mean(y)
    sxy = float(np.sum(x_dev * y_dev))
    slope = float(sxy / sxx)
    intercept = float(np.mean(y) - slope * np.mean(x))
    fitted = slope * x + intercept
    residuals = y - fitted
    rss = float(residuals @ residuals)
    centered = y - np.mean(y)
    total = float(centered @ centered)
    r_squared = 1.0 - rss / total if total > 0 else (1.0 if rss == 0 else 0.0)
    degrees_freedom = x.size - 2
    s2 = rss / degrees_freedom
    slope_se = float(np.sqrt(max(s2 / sxx, 0.0)))
    intercept_se = float(np.sqrt(max(s2 * (1.0 / x.size + np.mean(x)**2 / sxx), 0.0)))
    critical = float(student_t.ppf(0.975, degrees_freedom))
    if x.size >= 8 and rss > 0.0:
        residual_normality_p = float(normaltest(residuals).pvalue)
        residual_diagnostic_passed = residual_normality_p >= 0.01
        residual_diagnostic_detail = (
            f"D’Agostino–Pearson normality diagnostic p={residual_normality_p:.6g}; "
            "failure indicates model/residual mismatch, not proof of a particular alternative"
        )
    else:
        residual_diagnostic_passed = False
        residual_diagnostic_detail = "At least eight non-identical residuals are needed for the normality diagnostic"
    return ToolResult(
        scalars={
            "slope": {"value": slope, "unit": slope_unit, "sigma": slope_se},
            "intercept": {"value": intercept, "unit": y_unit, "sigma": intercept_se},
            "r_squared": {"value": float(r_squared), "unit": "", "sigma": None},
            "slope_standard_error": {"value": slope_se, "unit": slope_unit, "sigma": None},
            "slope_ci_low": {"value": slope - critical * slope_se, "unit": slope_unit, "sigma": None},
            "slope_ci_high": {"value": slope + critical * slope_se, "unit": slope_unit, "sigma": None},
        },
        arrays={"residuals": {"columns": {"x": x.tolist(), "observed": y.tolist(), "fitted": fitted.tolist(), "residual": residuals.tolist()}, "units": {"x": x_unit, "observed": y_unit, "fitted": y_unit, "residual": y_unit}}},
        checks=[
            CheckResult(name="finite_fit", passed=bool(np.isfinite(slope) and np.isfinite(intercept)), detail="Slope and intercept are finite"),
            CheckResult(name="residual_normality_diagnostic", passed=residual_diagnostic_passed, detail=residual_diagnostic_detail),
        ],
    )


GAUSSIAN_CONTRACT = ToolContract(
    id="analysis.gaussian_peak_fit",
    name="Scientific Analysis — Gaussian Peak Fit",
    version="0.1.0",
    domain="scientific analysis",
    tags=["gaussian", "peak", "fit", "uncertainty"],
    maturity="validated-method",
    category="instant",
    dataset_inputs=CONTRACT.dataset_inputs,
    outputs=[
        OutputSpec(name="amplitude", label="Peak amplitude", unit="y",),
        OutputSpec(name="mean", label="Peak center", unit="x"),
        OutputSpec(name="sigma", label="Peak standard deviation", unit="x"),
        OutputSpec(name="residual_rms", label="Residual RMS", unit="y"),
        OutputSpec(name="gaussian_fit", label="Gaussian fit and residuals", unit="", kind="array"),
    ],
    model=ModelSpec(
        name="Gaussian peak with constant offset",
        equations=["y = A exp(−(x−μ)²/(2σ²)) + c"],
        assumptions=["One isolated Gaussian-shaped peak with a constant local baseline", "Input uncertainties are not supplied; parameter uncertainty is estimated from residuals"],
        validity=["Overlapping peaks and strongly varying baselines require a richer model"],
    ),
    method=MethodSpec(name="nonlinear least squares (scipy.optimize.curve_fit)", settings={"maxfev": 20000}),
    guards=["Peak-fit parameter uncertainty is statistical under the selected model and excludes calibration/systematic effects."],
    references=["Gaussian nonlinear least squares"],
)


def execute_gaussian(_params: dict[str, float], data: dict[str, dict]) -> ToolResult:
    x = np.asarray(data["observations"]["x"], dtype=float)
    y = np.asarray(data["observations"]["y"], dtype=float)
    units = data["observations"].get("_units", {})
    x_unit = units.get("x") or "unit unknown"
    y_unit = units.get("y") or "unit unknown"
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size or x.size < 5:
        raise ValueError("Gaussian fitting requires at least five paired x/y values")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or np.ptp(x) <= 0:
        raise ValueError("Gaussian fitting requires finite data with a nonzero x range")

    def gaussian(values, amplitude, mean, sigma, offset):
        return amplitude * np.exp(-0.5 * ((values - mean) / sigma) ** 2) + offset

    baseline = float(np.percentile(y, 10))
    amplitude_guess = float(np.max(y) - baseline)
    mean_guess = float(x[np.argmax(y)])
    sigma_guess = float(np.ptp(x) / 6.0)
    params, covariance = curve_fit(
        gaussian,
        x,
        y,
        p0=[amplitude_guess, mean_guess, sigma_guess, baseline],
        bounds=([-np.inf, float(np.min(x)), np.finfo(float).eps, -np.inf], [np.inf, float(np.max(x)), np.inf, np.inf]),
        maxfev=GAUSSIAN_CONTRACT.method.settings["maxfev"],
    )
    amplitude, mean, sigma, offset = (float(value) for value in params)
    fitted = gaussian(x, *params)
    residual = y - fitted
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    rms = float(np.sqrt(np.mean(residual**2)))
    return ToolResult(
        scalars={
            "amplitude": {"value": amplitude, "unit": y_unit, "sigma": float(standard_errors[0])},
            "mean": {"value": mean, "unit": x_unit, "sigma": float(standard_errors[1])},
            "sigma": {"value": abs(sigma), "unit": x_unit, "sigma": float(standard_errors[2])},
            "offset": {"value": offset, "unit": y_unit, "sigma": float(standard_errors[3])},
            "residual_rms": {"value": rms, "unit": y_unit, "sigma": None},
        },
        arrays={"gaussian_fit": {"columns": {"x": x.tolist(), "observed": y.tolist(), "fitted": fitted.tolist(), "residual": residual.tolist()}, "units": {"x": x_unit, "observed": y_unit, "fitted": y_unit, "residual": y_unit}}},
        checks=[
            CheckResult(name="fit_converged", passed=bool(np.all(np.isfinite(covariance))), detail="Fit covariance is finite"),
        CheckResult(name="residual_finite", passed=bool(np.all(np.isfinite(residual))), detail="Residuals are finite"),
        ],
    )


PROPAGATION_CONTRACT = ToolContract(
    id="analysis.independent_error_propagation",
    name="Scientific Analysis — Independent Error Propagation",
    version="0.1.0",
    domain="scientific analysis",
    tags=["uncertainty", "error propagation"],
    maturity="validated-method",
    category="instant",
    inputs=[
        ScalarInputSpec(name="x", label="x", quantity="dimensionless", canonical_unit=""),
        ScalarInputSpec(name="sigma_x", label="Standard uncertainty of x", quantity="dimensionless", canonical_unit="", minimum=0.0),
        ScalarInputSpec(name="y", label="y", quantity="dimensionless", canonical_unit=""),
        ScalarInputSpec(name="sigma_y", label="Standard uncertainty of y", quantity="dimensionless", canonical_unit="", minimum=0.0),
    ],
    outputs=[OutputSpec(name="sum", label="x + y", unit=""), OutputSpec(name="sum_sigma", label="Uncertainty of x + y", unit=""), OutputSpec(name="product", label="x · y", unit=""), OutputSpec(name="product_sigma", label="Uncertainty of x · y", unit="")],
    model=ModelSpec(name="First-order independent uncertainty propagation", equations=["σ²(x+y)=σ²x+σ²y", "σ²(xy)=y²σ²x+x²σ²y"], assumptions=["Input uncertainties are independent standard uncertainties"], validity=["Linearized propagation; large relative uncertainties may require a distribution-based method"]),
    method=MethodSpec(name="analytic first-order propagation", settings={}),
    references=["First-order Taylor-series uncertainty propagation"],
)


def execute_propagation(params: dict[str, float], _data: dict[str, dict]) -> ToolResult:
    x, sigma_x, y, sigma_y = (params[key] for key in ("x", "sigma_x", "y", "sigma_y"))
    return ToolResult(scalars={
        "sum": {"value": x + y, "unit": "", "sigma": None},
        "sum_sigma": {"value": float(np.hypot(sigma_x, sigma_y)), "unit": "", "sigma": None},
        "product": {"value": x * y, "unit": "", "sigma": None},
        "product_sigma": {"value": float(np.hypot(y * sigma_x, x * sigma_y)), "unit": "", "sigma": None},
    }, checks=[CheckResult(name="finite_outputs", passed=bool(np.all(np.isfinite([x + y, x * y, sigma_x, sigma_y]))), detail="Propagated values and uncertainties are finite")])
