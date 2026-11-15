# Stage 2 — Architecture & Stack Proposal

Status: **awaiting approval**. Approval locks in what
[decision-records.md](decision-records.md) lists in its final section; Stage 3 (vertical
slice) begins only after that.

| Doc | Contents |
|---|---|
| [architecture.md](architecture.md) | Modular monolith with extraction seams; artifact graph as the data bus; run lifecycle; MVP + Phase 2 collaboration design; report pipeline; honest security posture; answers to all four Stage 1 open items (§8) |
| [decision-records.md](decision-records.md) | Three stack options with trade-offs; recommendation (Option 1: Python/FastAPI + React/TS); DR-1…DR-10 |

**Recommendation in one paragraph:** Python owns everything scientific — engines,
tool-contract validation, run execution, provenance — because that is where NumPy/SciPy/
Astropy live and where the run record's "environment" field is simply the truth of the
executing process. TypeScript/React owns the interface. The artifact graph (relational
metadata + content-addressed object store) is the single mechanism by which tool outputs
reach other tools and the report builder. Compute runs in killable, limited subprocesses
from day one so the hosted version changes configuration, not contracts. Real-time
co-editing stays out of the MVP (D1) but the notebook storage model is CRDT-shaped now,
and result blocks hold references — never values — so future co-editing cannot corrupt
provenance by construction.

**The one deliberately open decision:** the Phase 2 CRDT sync-server implementation
(DR-5). Everything else is proposed for lock-in.
