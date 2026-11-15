# Stage 1(c) — Conceptual Schemas

Behavioural specs, not storage designs. Field names are conceptual; Stage 2 maps them to a
stack. "MUST" is load-bearing: acceptance tests in e-acceptance-tests.md check these.

## 1. Research Artifact (base)

Every saved thing specialises this.

| Field | Notes |
|---|---|
| id | stable, unique within project, survives renames |
| type | dataset · run · figure · table · equation · note · notebook · comparison · report · comment |
| project, creator, created_at | — |
| name, description | mutable without creating versions of *content* |
| version | monotonically increasing; content changes create versions, metadata edits may not |
| provenance_label | **measured · calculated · simulated · estimated · ai-suggested** — exactly one, shown wherever the artifact's values are shown |
| links | typed edges: derived-from, input-to, produced-by, cites, anchors-to |
| review_state | draft · needs-review · approved · archived (where applicable) |

## 2. Dataset

| Field | Notes |
|---|---|
| raw_content | **immutable after upload**; content hash recorded at ingest |
| format, size | declared + detected |
| columns/axes | name, physical quantity, **unit**, missing-value convention |
| source | origin (upload/URL/archive), access date, license/attribution, citation |
| quality_flags | missing values, suspect rows — flagged, never auto-removed |
| unknowns | metadata the system could not determine (e.g., calibration) — explicit list, surfaced in UI and reports |
| derived_from + processing_step | derived datasets record parent + exact step (operation, parameters, tool version). Chain: raw → windowed → normalised… each link an artifact |

## 3. Run

The reproducibility record. A run is created by executing a registered tool and MUST capture:

```
id · project · author · started/finished · status (queued|running|completed|failed|cancelled)
tool_id + tool_version · model identifier · method + solver settings + tolerances
inputs: {name, value, unit}  — schema-validated against the tool contract before execution
input_artifacts: dataset ids @ version (+ hashes)
assumptions in effect (from contract + any user choices)
environment: package/engine versions, execution location (local|hosted|external — stated)
random_seed (when stochastic)
outputs: values/arrays/tables with units + uncertainty where defined; plots as views over outputs
warnings & validation_checks: e.g. "R+T−1 = 3e−12 (tol 1e−10): pass"
parent_run / branch (variant lineage)
```

Rules:
- Completed runs are **immutable**. "Editing" a run = new run with parent link.
- Failed runs persist with logs and whatever provenance exists (debuggability is provenance).
- Outputs are data; every plot/figure artifact references the run outputs it renders.

## 4. Variant / branch

A variant is a new run (or config) whose `parent_run` points at a shared baseline.
MUST: creating or editing a variant never mutates the baseline or any sibling.
Lineage is a tree navigable from any node. A comparison view references ≥2 runs @ version
and diffs inputs, environment, and outputs.

## 5. Notebook & blocks

Ordered document of typed blocks: text · heading · equation · code* · tool-block ·
figure · table · dataset-preview · attachment · citation · (Stage 5: ai-drafted, flagged).
(*code-cell execution semantics decided at Stage 2 with sandboxing.)

Rules:
- A result-bearing block stores a **reference** (run id @ version), never a copy of values.
- Editing prose NEVER changes any run. Changing a tool-block's inputs and re-running
  creates a new run; the block updates its reference and the old run remains.
- Notebook saves create versions; variants of notebooks follow §4 semantics.
- Designed for conflict-free concurrent editing (D1); MVP writes through a single-editor
  lock per notebook *section* at most — Stage 2 decides the representation, this spec
  requires that no merge can silently drop a block or re-bind a result reference.

## 6. Report

- Composed of sections; each section holds prose + **resolved references**
  (`artifact@version`) for every figure, table, value, and citation it uses.
- Generation pulls from saved artifacts only. A value with provenance_label
  `ai-suggested` or review_state ≠ approved is flagged in the draft.
- Export freezes resolution: the exported report version records the exact
  artifact versions used. Regeneration against newer versions creates a new report
  version; prior versions persist.
- Review states per §7 of the master prompt; approval records a human decision only.

## 7. Tool Contract

What the Workbench registry stores per tool; what the execution layer enforces.

```
identity: id · name · version · domain · tags
maturity: validated-method | educational-model | experimental | beta
category: instant | long-running | specialised     (drives Run-button vs live UX)
inputs[]: name · physical quantity · type · unit · range/constraints · default · validation
datasets?: required/optional input data shapes (columns, quantities, units)
outputs[]: name · type · unit · uncertainty semantics (how it is computed, or "none")
model: equations (renderable) · assumptions[] · boundary conditions · validity limits
method: algorithm name · tolerances · convergence criteria (where numerical)
guards[]: statements the UI MUST render with results
          (e.g. stellar fit → "estimates effective temperature only; does not determine composition")
checks[]: post-run validations auto-executed and recorded (e.g. R+T=1 within tol; conservation closure)
presets[]: named example configurations (labelled as examples)
references[] · license · validation_status (link to its passing test set)
```

Rules:
- Inputs are schema-validated (type, unit, range) **before** execution; violations block the
  run with a message naming the constraint — never silently clamped.
- A tool without a passing validation test set cannot carry maturity `validated-method`.
- Contract versions are pinned by runs; registry updates never rewrite history.

## 8. Comment / task

anchor = artifact id @ version + optional sub-anchor (block, table row, plotted series/point,
equation, line-match entry). Threaded; mentions; a comment may be promoted to a task
(assignee, status). Comments on version N remain visible (marked as on an older version)
when N+1 exists.

## 9. System invariants (testable; referenced as I-n elsewhere)

| # | Invariant |
|---|---|
| I-1 | Raw dataset bytes never change after ingest; hash verifies |
| I-2 | Every preprocessing step is a recorded artifact with a parent link |
| I-3 | Every displayed numeric result is reachable from a run or dataset (no orphan numbers) |
| I-4 | Numbers enter the system only as tool outputs, dataset values, or user-typed inputs — the AI layer (Stage 5) has no write-path for values except through registered tool execution |
| I-5 | Moving a control never mutates a saved run; save is explicit; unsaved state is visually distinct |
| I-6 | Completed runs are immutable; re-execution creates a child run |
| I-7 | Variants never overwrite baselines or siblings; lineage is complete |
| I-8 | No concurrent action by two members can silently destroy the other's saved work |
| I-9 | Every value carries exactly one provenance label and a unit (or is explicitly dimensionless) |
| I-10 | Reports and comparisons pin artifact versions; exports freeze them |
| I-11 | Unknown metadata is represented as unknown, propagated to limitations — never defaulted silently |
| I-12 | Physical constants come from one maintained CODATA source; hand-typed constants are a test failure |
| I-13 | Every externally-sourced dataset/reference records source, access date, and license |
| I-14 | Audit: membership, permission, approval, and deletion events are append-only history |
