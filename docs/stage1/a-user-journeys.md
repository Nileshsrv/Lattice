# Stage 1(a) — User Journeys

Three worked journeys over one shared spine. Each step names the **artifacts created** and the
**provenance captured**, because those two columns are the product: remove them and what remains
is an ordinary notebook app.

Conventions: `A:` artifact created, `P:` provenance captured, `→` output consumed downstream
by reference (never by export/re-upload).

---

## 0. The spine (every journey specialises this)

```
create project → add people → bring data OR define model → configure tool → run
      → inspect result → save run → narrate in notebook → branch variants → compare
      → discuss on artifacts → assemble report → human review → export
```

| Step | User action | System response | Artifacts / provenance |
|---|---|---|---|
| 1 | Create project: title, research question, objectives, domain | Private-by-default project; overview page with empty states that point to next actions | A: project |
| 2 | Invite collaborator, assign role | Member list with roles; activity entry | P: membership history |
| 3a | Import dataset (file upload in MVP) | Format detected, preview, metadata shown, missing info flagged (units, calibration) — *flagged, not guessed* | A: dataset (raw, immutable). P: source, license, upload time, content hash |
| 3b | …or start model-first | Workbench filtered to the project's domain | — |
| 4 | Open a tool (standalone from Workbench, or as a notebook block) | Standard tool anatomy (d-design-system §4.3): inputs with units, presets, assumptions visible before first run | A: tool-config (draft, unsaved) |
| 5 | Adjust parameters | Instant tools: live recompute. Long-running: explicit **Run** with status | — (draft state clearly marked as unsaved) |
| 6 | Run | Result panel: values with units + uncertainty, plot, warnings, validation checks | A: run. P: full run record (c-schemas §3) |
| 7 | Save run to project | Run becomes a referenceable artifact; appears in project run history | P: parent links (dataset →, tool version) |
| 8 | Insert result into notebook | Figure/value block bound to run id + version, not a pasted image | A: notebook blocks → run |
| 9 | Branch a variant | Independent copy from the saved baseline; baseline untouched | A: variant. P: parent run/branch |
| 10 | Compare runs | Side-by-side: parameters diffed, plots overlaid, outputs tabulated | A: comparison view (saveable) |
| 11 | Comment on a specific result/plot/row | Thread anchored to the artifact, visible wherever that artifact appears | A: comment (anchored) |
| 12 | Generate report | Sections assembled from saved artifacts only; every figure/claim carries its artifact reference; AI-drafted text (Stage 5+) flagged for review | A: report (draft) → runs, datasets, figures |
| 13 | Review & approve | Review state recorded as a human decision | P: who approved, when |
| 14 | Export | PDF/HTML in MVP (DOCX/LaTeX when supported); references resolved at a pinned version | A: report version (frozen) |

**Friction removed vs. status quo:** steps 6→8 and 8→12 are the replacement for
"screenshot plot → paste into document → lose the parameters". The chain
`dataset → run → figure → report` is navigable in both directions from any point.

---

## 1. Journey A — Stellar analysis (data-first)

**Persona:** final-year physics student analysing a stellar spectrum with one labmate.

1. **Create project** "Spectrum of Star X" with the research question.
   Invite labmate as *collaborator*.
2. **Import `sample-spectrum`** (public-domain spectrum, license recorded).
   System previews flux vs wavelength, lists metadata, and flags what it cannot find
   (e.g., flux calibration method) as *unknown* rather than assuming.
   - A: dataset · P: source URL, access date, license, hash
3. **Select wavelength range** in the Stellar Analysis Lab block. Range selection is itself
   a recorded preprocessing step — the raw dataset is untouched.
   - A: derived dataset (windowed) · P: step = "window [λ₁, λ₂]", parent = raw
4. **Fit a blackbody (Planck) model.** Tool shows, before running: model equation,
   assumption list (thermal continuum approximation; fit estimates *effective temperature only*),
   method, and maturity label.
   Result: T_eff with uncertainty, fitted curve over data, residuals panel, fit diagnostics.
   - A: run (fit) · P: everything in c-schemas §3, including solver settings and tolerances
   - **Hard rule surfaced in UI:** result panel states that composition is *not* determined
     by this fit. The words appear with the result, not in distant documentation.
5. **Inspect spectral lines.** Separate tool block: candidate absorption features vs
   reference line list. Matches are ranked and labelled *candidate* until the researcher
   confirms each one; confirmations are recorded as human decisions.
   - A: line-inspection run; per-line confirmation records · P: reference data source + version
6. **Labmate joins**, comments on one line match (thread anchored to that table row),
   and **branches a variant** with a different fit range. Baseline run untouched.
   - A: comment, variant run
7. **Compare** the two fits side-by-side: windowed ranges diffed, T_eff values with
   uncertainties adjacent, residual plots stacked.
8. **Notebook narrative:** prose + equation + both figures (bound to their runs) + the
   open calibration question recorded as a limitation, not resolved by guesswork.
9. **Report** "Results" section assembled from the saved runs; the T_eff claim carries
   its run reference; limitations section auto-includes the flagged unknown calibration.
10. **Review → approve → export.**

**What this journey proves:** dataset immutability + derived steps; fit provenance;
the temperature-vs-composition guard; anchored discussion; variant-not-overwrite.

---

## 2. Journey B — Quantum tunnelling (model-first, no dataset)

**Persona:** three collaborators splitting a parameter study.

1. **Create project**; invite two collaborators.
2. **Open Quantum Tunnelling Lab.** Inputs: particle (electron preset), energy E, mass m,
   barrier height V₀, width a. Potential profile renders immediately.
3. **Live exploration** (instant execution category): T and R update as sliders move;
   unsaved state clearly marked. Moving a slider never mutates any saved run (I-5).
4. **Save baseline run** (E = 5 eV, V₀ = 10 eV, a = 1 nm, say).
   - A: run · P: model = "1-D rectangular barrier, analytic", R+T check result recorded
5. **Each collaborator branches a variant** from the baseline — different V₀, different a,
   different sweep. Three branches, zero overwrites, lineage visible as a small tree.
6. **Sweeps:** T vs a at fixed E; T vs E at fixed barrier. Overlay all three collaborators'
   curves in one comparison view.
   - A: sweep runs (arrays as outputs, exportable as numbers not screenshots)
7. **Inverse estimation:** "what barrier widths give T = 0.01?" Tool returns the solution(s)
   *with the non-uniqueness caveat rendered alongside the answer* and the assumption set.
8. **Notebook:** derivation (equation blocks), the three variant figures, discussion of the
   thick-barrier limit against the asymptotic formula.
9. **Report** with model, equations, parameter table (from runs, not retyped), plots, limitations
   (1-D, lossless, rectangular; validity range).

**What this journey proves:** model-first flow; live vs saved state; branching for parallel
work (D1 scope: shared project + variants, no live co-editing); inverse analysis with
ambiguity shown; numeric export.

---

## 3. Journey C — Compton scattering (analytic model + reference-data layer)

**Persona:** researcher preparing teaching material that must be numerically honest.

1. **Create project.** Open Compton Lab: inputs = incident photon energy E, scattering angle θ;
   target model = *free electron at rest* (the only model in MVP, stated as such).
2. **Single-point calculation:** scattered λ′/E′, recoil electron kinetic energy and angle,
   geometry visualisation. The conservation panel shows energy and momentum closure
   numerically (residuals shown, not hidden).
   - A: run · P: model + CODATA constants source + versions
3. **Angle sweep** 0°–180°: Δλ(θ) and E′(θ) curves; endpoints annotated
   (zero shift at 0°, maximum 2λ_C at 180°).
4. **Klein–Nishina block:** differential cross-section vs θ at several energies, overlaid;
   Thomson limit shown as the low-energy reference curve.
5. **Material/target data layer (post-MVP, designed-for now):** attenuation reference data
   (e.g., NIST XCOM) appears as a *separately labelled data layer* — the UI never implies
   bound-electron or transport effects are simulated. A conceptual animation, if shown,
   is labelled illustrative.
6. **Notebook + report** as in the spine; the report's methods section names the
   free-electron model and its limits explicitly.

**What this journey proves:** analytic engine with conservation checks surfaced;
model-vs-reference-data separation; animation-vs-simulation honesty.

---

## 4. Cross-journey requirements extracted (feed IA and schemas)

| # | Requirement | Source step |
|---|---|---|
| R1 | Every value on screen is traceable to a run or dataset (drill-down) | all |
| R2 | Unsaved/live state visually distinct from saved runs; saving is explicit | B3–B4 |
| R3 | Derived data steps are artifacts; raw data immutable | A3 |
| R4 | Unknown metadata is flagged, never defaulted silently | A2, A9 |
| R5 | Comments anchor to artifacts and sub-elements (table row, plot, line match) | A6 |
| R6 | Variants form a visible lineage tree; baselines are never mutated | B5 |
| R7 | Comparison is a first-class view over ≥2 runs | A7, B6 |
| R8 | Scientific guard-rails are rendered *with results*, not in docs | A4, C5 |
| R9 | Sweep outputs are data (exportable arrays), plots are views of them | B6, C3 |
| R10 | Reports cite artifact@version; export freezes the resolution | spine 12–14 |
