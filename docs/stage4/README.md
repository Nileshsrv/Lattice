# Stage 4 — Remaining MVP Labs: Implementation & Verification Report

Status: **Complete — ready for review**. All Stage 4 changes remain preserved as uncommitted modifications in the worktree. Staged protocol requires stopping for user review before Stage 5.

---

## 1. Scope Implemented

### 1.1 Core Physics Labs
- **Compton Scattering Lab** (`compton.scattering`):
  - Analytic free-electron-at-rest kinematics, recoil-electron kinetic energy and momentum.
  - Wavelength shift identity $\Delta\lambda = \lambda_C(1 - \cos\theta)$ and relativistic energy shift $E' = E / [1 + (E/m_e c^2)(1 - \cos\theta)]$.
  - Klein–Nishina differential cross-section $d\sigma/d\Omega$ across 180° angular grid and integrated total cross-section.
  - Validation guards and checks: Thomson low-energy limit ($\sigma_T \approx 6.6524587 \times 10^{-29}\text{ m}^2$), symbolic anchor ($E = m_e c^2, \theta = 90^\circ \implies E' = E/2$), and 2-D energy/momentum conservation closure over an $(E, \theta)$ grid.
- **Quantum Tunnelling Lab** (`quantum.rectangular_tunneling` & `quantum.tunneling_energy_sweep`):
  - 1-D rectangular potential barrier with exact analytic sub-barrier ($E < V_0$) and above-barrier transmission resonances ($E > V_0$, $k_2 a = n\pi$).
  - Independent complex wave-amplitude boundary solver matching continuous $\psi$ and $d\psi/dx$ across interfaces.
  - Exact threshold continuity ($E \to V_0$) approaching $T = [1 + m a^2 V_0 / (2\hbar^2)]^{-1}$.
  - Probability conservation check ($R + T = 1$) within tolerance across parameter space.
  - Sub-barrier inverse estimation for barrier width $a$ from a target transmission $T$ with explicit non-uniqueness guard.
  - Dedicated energy-sweep tool saving transmission series array artifacts.
- **Scientific Analysis Lab**:
  - `analysis.linear_regression`: Ordinary least-squares linear regression with standard errors, $t$-distribution 95% confidence intervals on slope and intercept, coefficient of determination $R^2$, residual array, and D’Agostino–Pearson normality test on residuals.
  - `analysis.gaussian_peak_fit`: Nonlinear least-squares Gaussian peak parameter recovery (amplitude, mean, standard deviation, baseline) with residuals.
  - `analysis.independent_error_propagation`: First-order analytic Gaussian error propagation for independent sums and products.

### 1.2 Connected Workspace Mechanics
- **Array rendering across the stack**: Run detail, notebook blocks, and exported reports support dynamic multi-trace plots (e.g. potential profiles, wavefunction densities, differential cross-sections, and regression residuals).
- **Dataset windowing** (`/api/datasets/{id}/window`): Creates a new immutable CSV artifact derived from a parent dataset without mutating raw source bytes. Records column bounds, row counts, and parent linkage.
- **Saved run comparisons** (`/api/projects/{id}/comparisons` and `/api/comparisons/{id}`): Persists a `comparison` artifact referencing two completed runs in the project. Generates parameter diffs, output quantity diffs, and shared array overlays (e.g. comparing differential cross-sections or wavefunctions across variants).
- **Report Print / PDF workflow**: Exported HTML reports include print CSS (`@media print`) preventing page-break splits across figures and tables; UI provides a direct "Print / Save as PDF" trigger.
- **Properly Licensed Public Archive Spectrum**:
  - STScI CALSPEC solar spectrophotometric standard spectrum (`sample_data/calspec-sun-stis.csv`, `calspec-sun-stis.meta.json`).
  - Sourced from the Space Telescope Science Institute (STScI) CALSPEC database (`sun_reference_stis_002.fits`), combining HST/STIS observations and reference measurements from UV (119.5 nm) to NIR (2695.7 nm).
  - License: CC0-1.0 (Public Domain per NASA/STScI open data policy).
  - Ingests with provenance label `measured`, verified 0 unknowns, and recovers optical solar continuum effective temperature ($T_{\text{eff}} \approx 5588\text{ K}$) via blackbody fit.

---

## 2. Test Runner Stall Investigation & Resolution

### Root Cause Diagnosis
API tests (including the existing Wien end-to-end test) appeared to hang when executed inside the standard terminal sandbox:
1. `TestClient(app)` from Starlette/FastAPI runs the ASGI application via `anyio.from_thread.start_blocking_portal()`.
2. On Windows, `start_blocking_portal()` starts an event loop thread using Python's default `asyncio.ProactorEventLoop`.
3. `ProactorEventLoop` calls `_make_self_pipe()` during initialization to allow cross-thread wakeups (`call_soon_threadsafe`).
4. On Windows, Python implements `socket.socketpair()` via `_fallback_socketpair`, binding a loopback TCP socket on `127.0.0.1:0`, connecting a client socket, and calling `accept()`.
5. Under the Windows sandbox isolation policy (`BypassSandbox: false`), Windows Filtering Platform (WFP) blocks network loopback socket connections (`WinError 10013: An attempt was made to access a socket in a way forbidden by its access permissions`).
6. Because `_fallback_socketpair` connects the client socket in non-blocking mode, the connection failure is masked as `BlockingIOError`, and `lsock.accept()` hangs indefinitely waiting for a TCP handshake that the kernel blocks.

### Resolution & Test Fixes
- Running the test suite outside sandbox isolation (`BypassSandbox: true`) restores TCP loopback communication for `TestClient`.
- Fixed a floating-point strict equality check in `server/tests/test_api_slice.py` (`test_stage4_analysis_consumes_dataset_reference_and_saves_fit`) where slope `1.9999999999999998` was compared to `2.0` with `==`, updating to `pytest.approx(2.0)`.
- Added end-to-end API tests for saved run comparisons (`test_stage4_saved_run_comparison`) and real public archive spectrum ingest and blackbody fitting (`test_stage4_public_archive_spectrum_ingest_and_analysis`).

---

## 3. Verification Evidence

### 3.1 Automated Test Suite
**38 tests passed** (0 failures, 0 errors, in 5.68s):
- `test_constants_policy.py`: 2 passed (CODATA facade validation, no hand-typed constants).
- `test_p1_physics.py`: 8 passed (Wien displacement, Stefan–Boltzmann numerical integration, Planck peak, validation rejection).
- `test_p2_compton.py`: 5 passed (P-2 suite: endpoints, conservation grid, Klein–Nishina positivity, Thomson limit).
- `test_p3_tunneling.py`: 6 passed (P-3 suite: rectangular barrier, probability closure $R+T=1$, threshold continuity, inverse width estimation, energy sweeps).
- `test_p4_analysis.py`: 5 passed (P-4 suite: OLS regression, confidence intervals, Gaussian peak recovery, D’Agostino–Pearson normality test, error propagation).
- `test_api_slice.py`: 12 passed (A-1 privacy/roles, A-2/A-3 ingest & hash, A-4/A-5 provenance & immutability, A-10 notebook conflict & reference binding, A-11 report manifest freezing, Wien E2E, Compton & Tunneling persistence, Analysis dataset binding, dataset windowing, saved run comparisons, and CALSPEC archive spectrum ingest).

### 3.2 Frontend Build
- `npm.cmd --prefix frontend run build` (`tsc -b && vite build`) passed with exit code 0 and zero TypeScript errors.

---

## 4. Remaining Limitations (Documented & Honest)

1. **Regression input convention**: `analysis.linear_regression` and `analysis.gaussian_peak_fit` currently expect dataset columns named `x` and `y` and assume homoscedastic, independent observations. Arbitrary column-to-axis mapping is scheduled for Stage 5/workspace refinement.
2. **Worker sandboxing on Windows**: Memory ceilings on subprocess workers are not enforced on Windows (wall-clock timeout remains active).
3. **Print-to-PDF**: Print output is formatted via print media CSS and triggered via browser print dialog; automated headless PDF generation (Playwright headless Chromium) remains an enhancement for the export service.
4. **Plotly bundle size**: Frontend bundle remains ~4.86 MB uncompressed due to full Plotly.js dist bundling (accepted trade-off under DR-7).
5. **Stage boundary**: Collaborative co-editing, branching/variants UX, and AI assistant orchestration remain Phase 2/3 / Stage 5 scope.

---

## 5. Next Steps

Stop here for user review and approval of Stage 4 before proceeding to Stage 5.
