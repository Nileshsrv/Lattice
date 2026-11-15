# Stage 2 — Stack Options & Decision Records

Three whole-stack options first, then individual decision records (DR-n) that hold
regardless of option where noted. **Recommendation: Option 1.** Nothing is installed or
pinned yet; exact versions are chosen and locked at Stage 3 setup.

## Stack options

### Option 1 — Python backend + TypeScript/React frontend  ← recommended

Backend: Python + FastAPI · Pydantic (tool contracts as validated models) ·
SQLAlchemy/Alembic over SQLite→Postgres · subprocess compute workers importing
NumPy/SciPy/Astropy/lmfit directly.
Frontend: React + TypeScript + Vite · Plotly.js · KaTeX · CodeMirror · WebSocket client.

*For:* the scientific engines, the contract validation, and the provenance capture live
in **one language and one process family** — the run record's "package versions" is just
the truth of the executing interpreter. `scipy.constants`/`astropy` are the exact
libraries Source A names. Pydantic gives the tool contract (c-schemas §7) an executable
form almost 1:1. Smallest conceptual surface for a solo dev.
*Against:* two languages overall (unavoidable for a serious web UI); Python WebSocket
fan-out is less battle-tested than Node's for the Phase 2 CRDT server — mitigated by
extraction seam #2 (a dedicated sync server can be added in Phase 2 without touching
the science).

### Option 2 — Full TypeScript, physics in the browser (Pyodide/WASM)

Next.js or SPA + Node API; scientific Python via Pyodide in the browser.
*For:* one language; free static hosting; zero-latency "instant" tools.
*Against:* **fails the product's core constraints.** Engine versions in provenance depend
on each visitor's browser/WASM build; long-running jobs die with the tab; the server can
no longer guarantee I-3/I-4 (values computed client-side must be trusted, not enforced);
collaboration and report rendering need a server anyway. Rejected.

### Option 3 — Node/TypeScript backend + Python compute microservice

Fastify/NestJS API + hocuspocus (native Yjs server) + a separate FastAPI compute service.
*For:* best-in-class real-time stack for Phase 2; typed end-to-end API.
*Against:* two services, two languages, duplicated schema definitions (contracts defined
in TS, validated again in Python), double the ops for one developer, and the MVP doesn't
need CRDT yet. This is where Option 1 can *migrate toward* in Phase 2 if the Python sync
hub proves weak — adopting it now buys nothing and costs integration tax at the moment
of least capacity. Rejected for MVP.

## Decision records

**DR-1 · Backend = Python/FastAPI (Option 1).** Context: engines must be NumPy/SciPy/
Astropy; contracts need runtime validation; solo dev. Alternatives: options 2–3 above.
Consequence: one requirements set defines the scientific environment; accepted risk on
Phase 2 real-time noted above, with seam #2 as the exit.

**DR-2 · Frontend = React + TypeScript + Vite.** Alternatives: Svelte (leaner, smaller
ecosystem for scientific widgets), Next.js (SSR unneeded — this is an authenticated app,
and it drags the stack toward Node). React has the deepest ecosystem for the components
this product lives on (CodeMirror, Plotly, KaTeX, Yjs bindings, virtualised tables).
Consequence: SPA served by the backend; TS types for API generated from the backend's
OpenAPI schema so contracts stay single-sourced.

**DR-3 · Persistence = relational DB (SQLite now, Postgres later) + content-addressed
object store.** Alternatives: document DB (the artifact *graph* with role checks and
audit is relational-shaped; transactions matter for I-6/I-8); everything-in-DB (blobs
bloat backups and defeat content addressing). Consequence: SQL kept to the
SQLite∩Postgres subset; Alembic migrations from day one; object interface with local-dir
and S3 backends (seam #3).

**DR-4 · Run execution = subprocess worker pool inside the app.** Alternatives: in-process
calls (no kill/limits — violates §18 honesty), Celery/Redis now (an extra broker to
operate for zero MVP benefit). Consequence: timeouts, memory caps, cancel-by-kill, and
truthful environment capture in MVP; the orchestrator→worker contract is the hosted
extraction seam (#1).

**DR-5 · Real-time = WebSocket hub for facts now; CRDT (Yjs-family) in Phase 2.**
Alternatives: CRDT now (complexity before users exist, against D1), operational
transforms (effectively requires central server forever, weaker offline story).
Consequence: per-block optimistic concurrency with parked-copy conflict UX in MVP
(architecture §4); storage format CRDT-shaped from day one; Phase 2 choice between
y-py-based hub vs dedicated Node sync server stays open — recorded as the one
deliberately deferred decision.

**DR-6 · Units & constants = astropy.units for quantities; constants via one internal
facade over scipy.constants/astropy.constants (CODATA).** Alternatives: pint (fine
generally, weaker spectral equivalencies), raw floats + convention (how unit bugs are
born; violates I-9). Consequence: tool contracts declare units as astropy units; the
facade records source+version into every run (I-12); mixing unit systems is impossible
by construction.

**DR-7 · Plotting = Plotly.js in the client, rendering run output data.** Alternatives:
ECharts (close second, fewer scientific conventions out of the box: error bars, log
axes, WebGL point clouds), server-rendered matplotlib (dead plots: no zoom/inspect,
violates the interaction patterns). Consequence: plots are *views* over stored arrays
(R9); the same component renders app views and report figures (one rendering path);
accepted cost: bundle size, mitigated with the partial bundle.

**DR-8 · Code cells (MVP policy).** Context: Source A demands isolated execution; real
sandboxing is heavy; MVP is single-tenant on the author's machine. Decision: MVP code
cells run in the limited worker subprocess, inputs/outputs recorded like any run,
**explicitly labelled as not a security boundary**; a hosted deployment is gated on real
isolation (container/microVM/WASM) — this gate is written into architecture §6 and may
not be waived silently. Alternatives rejected: display-only cells (kills the notebook's
value), full sandbox now (weeks of work serving no MVP user).

**DR-9 · Reports = HTML template + headless-browser print-to-PDF (Playwright).**
Alternatives: WeasyPrint (no JS → KaTeX/Plotly fidelity gap vs the app), LaTeX pipeline
(beautiful, but a second typesetting universe to maintain; revisit at the DOCX/LaTeX
export phase). Consequence: exported figures/math are pixel-faithful to what was
reviewed; Playwright also serves as the UI test driver (one tool, two jobs).

**DR-10 · Testing = pytest + Hypothesis (property tests for P-suites) backend;
Vitest frontend; Playwright end-to-end for the A-tests.** Consequence: e-acceptance-tests
map 1:1 onto named test files; CI-ready though CI itself waits (D4, solo).

## What approval of this stage locks in

The architecture document's structure (graph-as-bus, subprocess workers, block-model
notebook, frozen-manifest reports), Option 1, and DR-1…DR-10 — *except* the Phase 2
sync-server implementation (DR-5, deliberately open). Stage 3 then builds the vertical
slice: project → import `sample-spectrum` → Wien/blackbody run with full provenance →
notebook block → minimal report export, with P-1 subset + relevant A-tests passing.
