"""Generate the representative sample spectrum (decision D6, Stage 3 scope).

Synthetic — NOT an observation: a Planck continuum at T = 5772 K (solar
effective temperature) with gaussian absorption features at real hydrogen and
calcium line wavelengths, plus seeded gaussian noise. Licensed CC0. Its
provenance label on import must be 'simulated'. A real public-archive spectrum
replaces/joins it in Stage 4.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lattice.physics.planck import planck_lambda, wien_lambda_max

SEED = 42
T_EFF = 5772.0          # K, IAU nominal solar effective temperature
WL_MIN_NM, WL_MAX_NM, STEP_NM = 320.0, 1000.0, 0.5
NOISE_SIGMA = 0.01      # relative to peak flux (= 1.0 in arbitrary units)

# (center_nm, depth, width_nm): H-beta, H-alpha, Ca II H & K, Na I D (approx)
LINES = [
    (393.37, 0.35, 0.6),
    (396.85, 0.30, 0.6),
    (486.13, 0.25, 0.5),
    (589.3, 0.15, 0.4),
    (656.28, 0.30, 0.5),
]


def main() -> None:
    rng = np.random.default_rng(SEED)
    wl_nm = np.arange(WL_MIN_NM, WL_MAX_NM + STEP_NM / 2, STEP_NM)
    wl_m = wl_nm * 1e-9

    peak_wl = wien_lambda_max(T_EFF)
    continuum = planck_lambda(wl_m, T_EFF) / planck_lambda(peak_wl, T_EFF)

    absorption = np.ones_like(wl_nm)
    for center, depth, width in LINES:
        absorption -= depth * np.exp(-0.5 * ((wl_nm - center) / width) ** 2)
    flux = continuum * absorption + rng.normal(0.0, NOISE_SIGMA, wl_nm.size)

    out_dir = Path(__file__).resolve().parents[2] / "sample_data"
    out_dir.mkdir(exist_ok=True)

    csv_path = out_dir / "sample-spectrum.csv"
    with csv_path.open("w", newline="") as fh:
        fh.write("wavelength_nm,flux\n")
        for w, f in zip(wl_nm, flux):
            fh.write(f"{w:.1f},{f:.6f}\n")

    meta = {
        "name": "sample-spectrum",
        "kind": "synthetic",
        "description": (
            "Synthetic stellar-like spectrum: Planck continuum at T_eff = 5772 K "
            "with gaussian absorption features at H/Ca II/Na I wavelengths and "
            "seeded gaussian noise. Not an observation."
        ),
        "provenance_label": "simulated",
        "license": "CC0-1.0",
        "generator": "server/scripts/generate_sample_spectrum.py",
        "seed": SEED,
        "true_parameters": {"T_eff_K": T_EFF, "noise_sigma_rel": NOISE_SIGMA, "lines": LINES},
        "columns": {"wavelength_nm": "nm", "flux": "arbitrary (relative), calibration unknown"},
        "known_unknowns": ["absolute flux calibration"],
    }
    (out_dir / "sample-spectrum.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {csv_path} ({wl_nm.size} rows), T_eff={T_EFF} K, seed={SEED}")


if __name__ == "__main__":
    main()
