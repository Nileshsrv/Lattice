# Stage 1(e) — MVP Acceptance Tests & Physics Validation Suites

Two layers: **product acceptance tests** (A-n, Given/When/Then, mapping §13 of the master
prompt) and **physics validation suites** (P-n, automated, a tool is not "done" until its
suite passes — §5). Numeric anchors below are exact identities or values safe to state;
every other expected value is *computed at test time from the governing formula with
library constants*, never hand-typed (invariant I-12).

Tolerances: `rtol` = relative. Defaults: analytic identities 1e-12 · numeric-vs-analytic
cross-checks 1e-8 · conservation closures 1e-10 (each tool's contract may tighten).

---

## A. Product acceptance tests

**A-1 Project & membership.** Given a new account → user creates a project → project is
private; a second account cannot see it. Owner invites collaborator with role `collaborator`
→ collaborator sees the project, can run tools and comment, cannot manage members.
All membership events appear in activity history (I-14).

**A-2 Dataset ingest.** User uploads `sample-spectrum` → preview renders; columns show
quantity + unit; source/license/access-date recorded (I-13); content hash stored; any
undetectable metadata appears in the *unknowns* panel (I-11). Re-downloading the raw file
yields bytes identical to upload (I-1).

**A-3 Derived data.** User windows the spectrum to [λ₁, λ₂] → a derived dataset exists with
the step recorded and parent link (I-2); the raw dataset is unchanged (I-1). Deleting is
blocked while dependents exist, or cascades only with explicit confirmation listing them.

**A-4 Run provenance.** Running any tool produces a run containing every field of
c-schemas §3 (schema-checked). Re-running with identical inputs + seed reproduces outputs
within the tool's stated tolerance. Changing one parameter creates a *new* run; the old run
is byte-identical to before (I-6). A saved figure opens its run from a click (R1/I-3).

**A-5 Unsaved vs saved.** Moving a slider changes the live view and shows the unsaved
marker; the previously saved run remains unchanged (I-5).

**A-6 Variants.** From baseline run B, two users create variants V1, V2 → B, V1, V2 all
exist; lineage tree shows both parents correctly; no write by one user altered the other's
artifacts (I-7, I-8).

**A-7 Comparison.** Selecting B and V1 opens a comparison: parameter diff table correct;
overlaid plots render; the comparison can be saved and cites both runs @ version (I-10).

**A-8 Chained analysis (no re-upload).** Output arrays of a sweep run feed the Scientific
Analysis Lab's fitting tool *by reference selection in the UI* — at no point does the user
export/re-import a file. The fit run's `input_artifacts` names the sweep run's output.

**A-9 Anchored discussion.** Collaborator comments on a specific table row of a line-match
result → thread visible from the artifact and from the project's comments list; after the
artifact gains a new version, the comment remains, marked as on the older version.

**A-10 Notebook integrity.** Editing prose around a result block changes no run (I-6);
the block re-binds only when the user re-runs; old run persists and remains reachable.

**A-11 Report generation.** Generating a lab-report draft from the stellar project pulls
only saved artifacts; every figure/value chip resolves to artifact@version (I-10);
flagged unknowns (A-2) appear in the limitations section (I-11); an unapproved value is
flagged in the draft. Export (PDF/HTML) freezes versions; a later re-export against newer
runs creates a new report version and the old export is preserved.

**A-12 Review states.** Reviewer sets needs-review → approved; the approval records user +
time and is worded as a human decision, not platform validation.

**A-13 Guard rendering.** The stellar fit result panel contains the
temperature-not-composition statement (contract `guards[]`), visible without interaction.

**A-14 Honest numbers.** Static analysis / registry check: no physical constant literal in
tool code (I-12, allow-listed test files excepted); every UI number traces to run/dataset/
user input (I-3, I-4 — enforced by construction, spot-checked by test).

**T-UX Accessibility & glass.** Automated contrast checks pass per d-design-system §6,
including glass-over-worst-case-backdrop; keyboard traversal covers the spine journey;
reduced-motion verified.

---

## B. Physics validation suites

### P-1 Stellar Analysis Lab

| # | Check | Anchor / method |
|---|---|---|
| P-1.1 | Wien: λ_max·T equals the library's Wien displacement constant b | identity, rtol 1e-12; b ≈ 2.897771955×10⁻³ m·K (asserted ≈ library value, not hand-maintained) |
| P-1.2 | T = 5772 K → λ_max = b/T (≈ 502 nm) | computed both ways, rtol 1e-12 |
| P-1.3 | Planck curve: ∫B_λ dλ over [0,∞) consistent with σT⁴/π | numerical integration vs Stefan–Boltzmann, rtol 1e-6 |
| P-1.4 | Planck peak position found numerically equals b/T | optimizer vs identity, rtol 1e-8 |
| P-1.5 | Stefan–Boltzmann: L = 4πR²σT⁴ with IAU nominal R_sun and T = 5772 K reproduces nominal L_sun ≈ 3.828×10²⁶ W | rtol 1e-3 (nominal-value consistency) |
| P-1.6 | Round-trip: T → synthetic Planck spectrum (+ gaussian noise, fixed seed) → fit recovers T within its own reported confidence interval | statistical; repeated seeds |
| P-1.7 | Fit on `sample-spectrum` is stable: same data + seed → identical result | reproducibility |
| P-1.8 | Units: feeding wavelength in nm vs m yields identical T | dimensional handling |
| P-1.9 | Guard: result payload includes the composition disclaimer | contract check |

### P-2 Compton Scattering Lab

| # | Check | Anchor / method |
|---|---|---|
| P-2.1 | Δλ(θ=0) = 0 exactly | identity |
| P-2.2 | Δλ(θ=180°) = 2λ_C; Δλ(90°) = λ_C; λ_C = h/(m_e c) ≈ 2.4263×10⁻¹² m from library constants | rtol 1e-12 |
| P-2.3 | E′ = E / [1 + (E/m_e c²)(1−cosθ)] consistent with the Δλ form | two formulations agree, rtol 1e-12 |
| P-2.4 | Symbolic anchor: E = m_e c², θ = 90° → E′ = E/2 and electron kinetic energy = E/2 | exact, rtol 1e-12 |
| P-2.5 | Energy conservation: E = E′ + T_e; momentum closure in both components | residuals < 1e-10 (relative) across an (E, θ) grid |
| P-2.6 | Monotonicity: E′ strictly decreasing in θ on (0°, 180°) for E > 0 | property test |
| P-2.7 | Klein–Nishina: E → 0 limit of total cross-section → Thomson σ_T ≈ 6.6525×10⁻²⁹ m² (library value) | rtol 1e-4 at suitably small E, with convergence trend checked |
| P-2.8 | KN differential cross-section ≥ 0 everywhere; symmetric requirements of the formula hold | property test |
| P-2.9 | Target model labelled "free electron at rest" in run record and UI | contract check |

### P-3 Quantum Tunnelling Lab (1-D rectangular barrier)

| # | Check | Anchor / method |
|---|---|---|
| P-3.1 | E < V₀: T = [1 + V₀² sinh²(κa) / (4E(V₀−E))]⁻¹, κ = √(2m(V₀−E))/ħ — numerical engine (transfer matrix) vs analytic | rtol 1e-8 over a parameter grid |
| P-3.2 | R + T = 1 | abs residual < 1e-10, entire grid |
| P-3.3 | E > V₀ branch (sin form with k₂ = √(2m(E−V₀))/ħ) correct; resonances T = 1 at k₂a = nπ | located numerically, rtol 1e-8 |
| P-3.4 | E → V₀ continuity: both branches approach T = [1 + m a² V₀ / (2ħ²)]⁻¹ | limit from both sides, rtol 1e-6 |
| P-3.5 | Thick-barrier asymptote T ≈ 16(E/V₀)(1−E/V₀)e^(−2κa) | ratio → 1 as κa grows (trend + rtol 1e-3 at κa ≥ threshold stated in tool contract) |
| P-3.6 | Limits: a → 0 ⇒ T → 1; E ≫ V₀ ⇒ T → 1; E → 0⁺ ⇒ T → 0 | property tests |
| P-3.7 | Classical-forbidden sanity: 0 < T < 1 for 0 < E < V₀, a > 0 | property test |
| P-3.8 | Inverse estimation: for a target T, returned widths re-evaluate to that T (rtol 1e-6) and the result carries the non-uniqueness caveat | round-trip + contract check |
| P-3.9 | Unit handling: (eV, nm, mₑ) and SI inputs agree | rtol 1e-10 |

### P-4 Scientific Analysis Lab

| # | Check | Anchor / method |
|---|---|---|
| P-4.1 | Linear regression on exact line (no noise) recovers slope/intercept | rtol 1e-12 |
| P-4.2 | Known-seed noisy linear data: estimates within reported CIs; CI coverage ≈ nominal over many seeds | statistical |
| P-4.3 | Gaussian peak fit on synthetic peak recovers (μ, σ, A) | rtol per noise level, seeded |
| P-4.4 | Residuals of a correct model pass runs/normality sanity checks; of a wrong model, fail them | diagnostic validity |
| P-4.5 | Error propagation: f = x·y and f = x+y with independent σs match analytic propagation | rtol 1e-10 |
| P-4.6 | Import → fit → export: exported numbers equal displayed numbers at full precision | round-trip |

---

## C. Definition of done (MVP)

All A-tests and T-UX pass; P-suites pass for the three physics labs + analysis lab;
the spine journey (a-user-journeys §0) is demonstrable end-to-end by a user with no
manual file transfer between steps 3–14; and every claim in the exported sample report
traces to a real artifact. AI-assistant criteria (operates tools without inventing
outputs, links explanations to saved results) are accepted at Stage 5 against the same
invariants (I-3, I-4).
