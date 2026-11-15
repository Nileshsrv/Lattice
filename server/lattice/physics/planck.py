"""Planck radiation law and Wien displacement relations.

Model: ideal blackbody spectral radiance per unit wavelength,
    B_lambda(lambda, T) = (2 h c^2 / lambda^5) * 1 / (exp(h c / (lambda k_B T)) - 1)
SI units throughout: wavelength [m], temperature [K], B_lambda [W m^-3 sr^-1].
Validity: thermal equilibrium continuum; no spectral lines.
"""

import numpy as np

from .constants import b_wien, c, h, k_B


def planck_lambda(wavelength_m, temperature_K):
    wl = np.asarray(wavelength_m, dtype=float)
    if np.any(wl <= 0):
        raise ValueError("wavelength must be positive")
    if temperature_K <= 0:
        raise ValueError("temperature must be positive")
    x = h * c / (wl * k_B * temperature_K)
    with np.errstate(over="ignore"):
        return (2.0 * h * c**2) / wl**5 / np.expm1(x)


def wien_lambda_max(temperature_K: float) -> float:
    if temperature_K <= 0:
        raise ValueError("temperature must be positive")
    return b_wien / temperature_K


def wien_temperature(lambda_max_m: float) -> float:
    if lambda_max_m <= 0:
        raise ValueError("peak wavelength must be positive")
    return b_wien / lambda_max_m
