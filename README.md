# Lattice

**A collaborative computational research workspace** — scientists explore, simulate,
analyse, discuss, and document research in one connected environment, instead of
juggling notebooks, simulators, chat, file shares, and manual report assembly.

A researcher creates a project, invites collaborators, imports a real dataset or
starts from a theoretical model, runs interactive physics tools, compares experiment
variants, discusses specific results, chains outputs into further analyses, and
generates a reproducible report — with every figure and value traceable to the exact
computation and data that produced it.

> Lattice is not a calculator directory, a generic chatbot, or a static dashboard.
> Its differentiator is **connection**: tools, data, people, AI assistance, and
> outputs linked in one reproducible workflow.

---

## Core principles

| Principle | What it means in the product |
|---|---|
| **AI assists; engines calculate** | Every number comes from an explicit tool computation or verified data. The assistant plans and explains, but has no write-path for values except approved tool runs. |
| **Reproducibility is first-class** | Every saved run records inputs with units, data hashes, model, assumptions, method, tolerances, package versions, and lineage. Raw data is immutable. |
| **Scientific honesty as UI** | Units, uncertainty, assumptions, maturity labels, and validity limits render *with* results. A blackbody fit says plainly that it estimates temperature and does not determine composition. |
| **Collaboration on artifacts, not just text** | Comments anchor to runs, table rows, and notebook blocks; review states record human decisions; variants never overwrite a baseline. |
| **Tools are building blocks** | One tool's output feeds the next analysis by reference — never by export and re-upload. |

## Features

### Physics & analysis workbench (8 validated tools)
- **Stellar Analysis** — Wien's displacement law; Planck blackbody continuum fitting
  with statistical uncertainty, residuals, and calibration caveats.
- **Compton Scattering** — free-electron kinematics, recoil quantities, Klein–Nishina
  differential cross-section, energy/momentum conservation checks surfaced in the UI.
- **Quantum Tunnelling** — 1-D rectangular barrier (analytic + independent
  wave-amplitude cross-check), R+T=1 verification, energy sweeps, above-barrier
  resonances, inverse barrier estimation with non-uniqueness caveats.
- **Scientific Analysis** — OLS regression with confidence intervals and residual
  normality diagnostics, Gaussian peak fitting, independent error propagation.

Every tool ships with a validation test suite (exact identities, limiting cases,
conservation closures, round-trip recovery) and is gated on passing it. Physical
constants come from one CODATA facade — hand-typed constants fail the test suite.

### Connected research workflow
- **Projects** with roles (owner/editor/collaborator/reviewer/viewer), private by
  default, with an append-only activity trail.
- **Datasets**: CSV ingest with unit detection, content hashing, immutable raw bytes,
  derived windowing as new artifacts, and *flagged unknowns* (undeclared units,
  missing licenses) that propagate automatically into report limitations.
- **Runs** with full provenance; re-running with changed parameters creates a new run
  and never mutates the old one; failed runs persist with their logs.
- **Comparisons**: saved side-by-side diffs of two runs (parameters, outputs, overlay
  plots).
- **Notebooks**: text, headings, KaTeX equations, and figure blocks that *reference*
  a run version rather than pasting values; per-block conflict protection so no
  collaborator's edit is silently lost.
- **Live presence** over WebSocket; comments anchorable to blocks with
  resolve/reopen; review states (draft → needs review → approved → archived).
- **Reports** assembled from saved artifacts only: numbered figures and equations,
  parameter tables, guards, auto-collected limitations, and a frozen
  artifact@version + SHA-256 manifest per export. Export as HTML or server-rendered
  PDF (headless Chromium); re-exports create new versions and old ones stay
  byte-stable.

### AI research assistant
A rule-based tool dispatcher (no external LLM in this build): it maps a request to a
registered tool, shows the plan with its guards, and executes only on explicit
approval — producing a normal run labelled `ai-suggested`. It cannot fabricate
numbers by construction. The orchestration boundary (registered tools, validated
inputs, logged runs) is designed so an LLM-backed assistant can slot in behind the
same approve-execute contract.

## Tech stack

- **Backend**: Python · FastAPI · SQLAlchemy/Alembic (SQLite → Postgres-ready) ·
  NumPy/SciPy/Astropy · content-addressed object store · subprocess compute workers
  with wall-clock timeouts and an RSS memory watchdog.
- **Frontend**: React + TypeScript + Vite · Plotly (basic dist) · KaTeX · dark
  crystal-glassmorphic design system (readability ranked above visual effects).
- **Testing**: pytest + Hypothesis; 54 tests covering physics anchors (P-suites),
  provenance invariants, API acceptance, and PDF export.

## Getting started

```bash
# Backend (Python 3.12+)
python -m venv .venv
.venv/Scripts/pip install -r server/requirements.txt
.venv/Scripts/python -m playwright install chromium   # optional, for PDF export
.venv/Scripts/python -m uvicorn lattice.app:app --port 8000 --app-dir server

# Frontend (Node 18+)
npm install --prefix frontend
npm run dev --prefix frontend    # http://localhost:5173, proxies /api to :8000

# Tests
cd server && ../.venv/Scripts/python -m pytest tests -q
```

Sample data lives in [`sample_data/`](sample_data/README.md): a synthetic 5772 K
spectrum (labelled `simulated`) and a real CALSPEC solar standard spectrum (CC0,
provenance recorded).

## Repository map

| Path | Contents |
|---|---|
| `docs/stage1/` | Product definition: user journeys, information architecture, schemas & invariants, design system, acceptance tests |
| `docs/stage2/` | Architecture and stack decision records (DR-1…DR-10) |
| `docs/stage3..5/` | Per-stage build reports: what was built, how it was verified, honest limitations |
| `server/` | FastAPI backend, physics engines, tool contracts, tests, migrations |
| `frontend/` | React SPA |
| `sample_data/` | Licensed sample spectra with metadata |

## Status & roadmap

The MVP (per the concept brief's acceptance criteria) is complete: projects and
collaboration, 8 validated tools, real-data analysis, reference-chained workflows,
variants and comparison, provenance-preserving runs, and traceable report export.

Next horizons (designed-for, not yet built): real-time co-editing on the
CRDT-shaped notebook model, an LLM-backed assistant behind the existing
approve-execute boundary, the research library (arXiv/ADS/Zotero integrations),
and expansion into further physics domains. Known limitations are documented
honestly per stage in `docs/`.

## License

No license has been chosen yet — until one is added, all rights reserved.
Sample data files carry their own licenses (see `sample_data/`).
