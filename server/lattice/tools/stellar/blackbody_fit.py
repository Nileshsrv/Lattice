"""Blackbody (Planck) continuum fit: estimates effective temperature from a spectrum.

Fitted model (scale-normalised for numerical conditioning):
    flux(lambda) = A * B_lambda(lambda, T) / B_lambda(lambda_ref, T)
with lambda_ref fixed at the data's flux-weighted peak, so A is of order the
peak flux and T is the only shape parameter.
"""

import numpy as np
from scipy.optimize import curve_fit

from ...physics.planck import planck_lambda, wien_lambda_max, wien_temperature
from ..contract import (
    CheckResult,
    DatasetInputSpec,
    ModelSpec,
    MethodSpec,
    OutputSpec,
    ScalarInputSpec,
    ToolContract,
    ToolResult,
)
from .wien import COMPOSITION_GUARD

CALIBRATION_WARNING = (
    "Flux treated as relative (free amplitude); reported uncertainty on T_eff is "
    "statistical only and excludes calibration systematics."
)

CONTRACT = ToolContract(
    id="stellar.blackbody_fit",
    name="Blackbody Continuum Fit",
    version="0.1.0",
    domain="astrophysics",
    tags=["stellar", "blackbody", "fitting", "spectrum"],
    maturity="validated-method",
    category="instant",
    inputs=[
        ScalarInputSpec(
            name="lambda_min",
            label="Fit window minimum",
            quantity="wavelength",
            canonical_unit="m",
            minimum=1e-12,
            maximum=1.0,
            required=False,
        ),
        ScalarInputSpec(
            name="lambda_max",
            label="Fit window maximum",
            quantity="wavelength",
            canonical_unit="m",
            minimum=1e-12,
            maximum=1.0,
            required=False,
        ),
    ],
    dataset_inputs=[
        DatasetInputSpec(
            name="spectrum",
            label="Spectrum",
            required_columns=[
                {"name": "wavelength", "quantity": "wavelength", "canonical_unit": "m"},
                {"name": "flux", "quantity": "spectral flux", "canonical_unit": ""},
            ],
        )
    ],
    outputs=[
        OutputSpec(name="T_eff", label="Effective temperature", unit="K"),
        OutputSpec(name="rms_residual", label="RMS residual (relative flux)", unit=""),
        OutputSpec(name="n_points", label="Points in fit window", unit=""),
        OutputSpec(name="fit", label="Fitted curve and residuals", unit="", kind="array"),
    ],
    model=ModelSpec(
        name="Planck blackbody continuum, free relative amplitude",
        equations=[
            r"B_\lambda(\lambda,T) = \frac{2hc^2}{\lambda^5}\frac{1}{e^{hc/\lambda k_B T}-1}",
            r"f(\lambda) = A\, B_\lambda(\lambda,T) / B_\lambda(\lambda_{ref},T)",
        ],
        assumptions=[
            "Continuum is thermal (blackbody-like) over the fit window",
            "Spectral lines are treated as noise around the continuum",
            "Absolute flux calibration is unknown; amplitude is a free parameter",
        ],
        validity=[
            "Window should bracket or approach the continuum peak for a "
            "well-constrained T",
            "Strong line blanketing or non-thermal continua bias the estimate",
        ],
    ),
    method=MethodSpec(
        name="nonlinear least squares (scipy.optimize.curve_fit, Levenberg-Marquardt)",
        settings={"maxfev": 10000, "p0": "Wien estimate from smoothed data peak"},
    ),
    guards=[COMPOSITION_GUARD, CALIBRATION_WARNING],
    references=["Planck law; CODATA constants via scipy.constants"],
)


def execute(params: dict[str, float], data: dict[str, dict]) -> ToolResult:
    spectrum = data["spectrum"]
    wl = np.asarray(spectrum["wavelength"], dtype=float)
    flux = np.asarray(spectrum["flux"], dtype=float)

    mask = np.isfinite(wl) & np.isfinite(flux)
    lo = params.get("lambda_min")
    hi = params.get("lambda_max")
    if lo is not None:
        mask &= wl >= lo
    if hi is not None:
        mask &= wl <= hi
    wl_fit, flux_fit = wl[mask], flux[mask]
    if wl_fit.size < 10:
        raise ValueError(
            f"fit window contains {wl_fit.size} points; at least 10 are required"
        )

    kernel = np.ones(min(21, max(3, wl_fit.size // 50)))
    kernel /= kernel.sum()
    smoothed = np.convolve(flux_fit, kernel, mode="same")
    wl_ref = float(wl_fit[np.argmax(smoothed)])
    t0 = wien_temperature(wl_ref)
    a0 = float(np.max(smoothed))

    def model(wavelength, amplitude, temperature):
        return amplitude * planck_lambda(wavelength, temperature) / planck_lambda(
            wl_ref, temperature
        )

    popt, pcov = curve_fit(
        model, wl_fit, flux_fit, p0=[a0, t0], maxfev=CONTRACT.method.settings["maxfev"]
    )
    amplitude, temperature = float(popt[0]), float(popt[1])
    perr = np.sqrt(np.diag(pcov))
    sigma_T = float(perr[1])

    fitted = model(wl_fit, amplitude, temperature)
    residuals = flux_fit - fitted
    rms = float(np.sqrt(np.mean(residuals**2)))

    warnings = [CALIBRATION_WARNING]
    checks = [
        CheckResult(
            name="fit_converged",
            passed=bool(np.all(np.isfinite(pcov))),
            detail="covariance matrix finite",
        ),
        CheckResult(
            name="physical_range",
            passed=temperature > 0,
            detail=f"T_eff = {temperature:.6g} K",
        ),
    ]
    peak_wl = wien_lambda_max(temperature)
    if not (wl_fit.min() <= peak_wl <= wl_fit.max()):
        warnings.append(
            "Fitted continuum peak lies outside the fit window; the temperature "
            "estimate is extrapolated and less well constrained."
        )

    return ToolResult(
        scalars={
            "T_eff": {"value": temperature, "unit": "K", "sigma": sigma_T},
            "rms_residual": {"value": rms, "unit": "", "sigma": None},
            "n_points": {"value": float(wl_fit.size), "unit": "", "sigma": None},
        },
        arrays={
            "fit": {
                "columns": {
                    "wavelength": wl_fit.tolist(),
                    "flux": flux_fit.tolist(),
                    "fitted": fitted.tolist(),
                    "residual": residuals.tolist(),
                },
                "units": {
                    "wavelength": "m",
                    "flux": "arb",
                    "fitted": "arb",
                    "residual": "arb",
                },
            }
        },
        warnings=warnings,
        checks=checks,
    )
