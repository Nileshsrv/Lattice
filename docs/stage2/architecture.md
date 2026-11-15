# Stage 2 — System Architecture

Stack-independent design first; the concrete stack is argued in
[decision-records.md](decision-records.md). Everything here must satisfy the Stage 1
invariants (I-1…I-14) and decisions D1–D6.

## 1. Topology: modular monolith with an extraction seam

One deployable server for the MVP (solo dev, local-first), structured internally as
modules with hard interfaces so the pieces that must scale or isolate later can be
extracted without rewrites:

```
┌────────────────────────────  Browser (SPA)  ───────────────────────────┐
│  Notebook UI · tool blocks · plots · comparisons · report editor       │
│  (renders values it is GIVEN; computes nothing scientific)             │
└───────────────▲───────────────────────────────▲───────────────────────┘
                │ HTTPS/JSON API                │ WebSocket (presence, run
                │                               │ status, comments, notifications)
┌───────────────┴───────────────────────────────┴───────────────────────┐
│                         Application server                             │
│ ┌─────────────┐ ┌──────────────┐ ┌───────────────┐ ┌────────────────┐ │
│ │ Projects &  │ │ Artifact &   │ │ Tool registry │ │ Report builder │ │
│ │ auth/roles  │ │ provenance   │ │ & contract    │ │ (resolve refs, │ │
│ │ (I-14)      │ │ store (graph)│ │ validation    │ │  render, freeze│ │
│ └─────────────┘ └──────┬───────┘ └──────┬────────┘ └────────────────┘ │
│                        │                │                              │
│                 ┌──────┴────────────────┴──────┐                      │
│                 │  Run orchestrator (job queue) │                      │
│                 └──────────────┬───────────────┘                      │
└────────────────────────────────┼──────────────────────────────────────┘
                                 │ spawns, time/memory-limited
                     ┌───────────┴───────────┐
                     │  Compute workers       │  ← extraction seam #1
                     │  (subprocesses running │    (becomes a separate
                     │   registered tools)    │     service when hosted)
                     └───────────┬───────────┘
            ┌────────────────────┼──────────────────────┐
     ┌──────┴──────┐      ┌──────┴───────┐       ┌──────┴───────┐
     │ Metadata DB │      │ Object store │       │ Scientific   │
     │ (relational)│      │ (content-    │       │ engine libs  │
     │             │      │  addressed)  │       │ (validated)  │
     └─────────────┘      └──────────────┘       └──────────────┘
```

Extraction seams (designed now, used later): #1 compute workers → separate hosted
service; #2 WebSocket hub → dedicated real-time server when Phase 2 CRDT lands;
#3 object store interface → S3-compatible backend.

**Client computes nothing scientific.** Live "instant" tools still execute in the
compute layer; latency budget for instant tools is <150 ms round-trip locally, which
analytic formulas meet easily. This keeps I-3/I-4 enforceable in one place and keeps
engine versions in provenance truthful (a browser-side duplicate engine would fork them).

## 2. The artifact graph is the data bus

The core architectural challenge — outputs flowing between tools and into reports with
no manual transfer — is solved by one mechanism, not point-to-point integrations:

- **Metadata DB** holds the graph: artifacts, versions, typed edges (derived-from,
  produced-by, input-to, cites, anchors-to), runs, members, comments, activity.
- **Object store** holds content: raw uploads, derived data, run output arrays/tables,
  rendered figures — addressed by content hash (`objects/<sha256[:2]>/<sha256>`).
  Content-addressing gives I-1 (immutability verifiable), dedup, and cheap versioning.
- A tool input of kind "dataset/series" is bound by **reference** (artifact@version);
  the orchestrator resolves it to object-store content at execution time and records
  the resolved hash in the run. The report builder reads the same graph the same way.
- Scalars/small outputs live in the run record itself; arrays/tables as objects with a
  declared columnar schema (names, quantities, units) so any downstream tool can
  interrogate compatibility before binding.

## 3. Run lifecycle (enforces I-4, I-5, I-6)

```
draft config (client) ──POST run──▶ validate against tool contract
   │ invalid: 422 naming the violated constraint (never clamped)
   ▼ valid
run row created (queued) ─▶ orchestrator spawns worker subprocess
   worker: resolve input refs → verify hashes → execute engine fn
           → post-run checks (contract `checks[]`, e.g. R+T=1) → write outputs
   ▼
run completed | failed (logs kept) | cancelled (user) | killed (time/mem limit)
   ▼
WebSocket notifies clients; run is now immutable; downstream staleness computed
```

- Workers are separate OS processes even in the MVP: wall-clock timeout, memory cap,
  kill-on-cancel, and crash isolation come free, and the hosted version keeps the
  same contract (DR-4).
- The worker records the engine package versions *it actually imported* into the run.
- "Instant" tools use the same path with a fast lane (pre-warmed worker, no queue wait).

## 4. Real-time collaboration (D1: designed now, co-editing Phase 2)

**MVP ships:** presence (who is in the project/notebook), live run status, comments,
notifications — all via one WebSocket hub with per-project channels; these are
append-only or server-authoritative facts, so no conflict problem exists.

**Notebook editing in MVP:** server-authoritative optimistic concurrency **per block**.
Each block carries a revision; a stale write is rejected and surfaced as "N has edited
this block — review their version / keep yours as a copy". Simultaneous edits to
*different* blocks always merge. A rejected write is never discarded silently (I-8) —
the losing edit is parked as a draft copy.

**Phase 2 (CRDT):** the notebook model is already CRDT-shaped: the document is a
sequence of block IDs + per-block content maps, mapping 1:1 onto a CRDT doc
(sequence type for order, map/text types per block). Result-bearing blocks store only
an artifact reference — the CRDT never carries scientific values, so collaborative
editing can never corrupt provenance (I-3/I-4 survive co-editing by construction).
Phase 2 swaps the per-block lock for a CRDT sync provider behind seam #2; the stored
format gains a CRDT state field alongside the materialised blocks (kept for search,
reports, and history).

## 5. Report pipeline (answers Stage 1 open item 4)

1. Report sections store prose + reference chips `{artifact_id, version}`.
2. Builder resolves each chip through the artifact store; unresolvable or
   not-approved/ai-suggested content is flagged in the draft (never auto-dropped).
3. Figures are re-rendered from the referenced run's *output data* through the same
   plot component the app uses (one rendering path — what you reviewed is what exports),
   captured as vector graphics.
4. Export renders the report to HTML, then prints to PDF via a headless browser
   (DR-9), embedding a manifest: every chip's resolved artifact@version + hash.
   The manifest is stored with the frozen report version (I-10).
5. Regeneration against newer artifact versions = new report version; old manifest
   and export preserved.

## 6. Security posture (stated honestly, per Source A §18)

MVP is **single-tenant, local, trusted-machine** software:
- Real things: password-hashed local accounts, role checks on every API route,
  private-by-default projects, append-only audit events, upload size/type limits,
  worker time/memory limits, no external calls without the user seeing them listed.
- Explicit non-claims: no multi-tenant isolation; registered first-party tools run
  with the server's OS privileges; **user-authored code cells** execute in a worker
  subprocess with limits but are NOT a security sandbox — acceptable only because
  MVP runs on the author's own machine. Before any hosted multi-user deployment,
  code-cell execution must move to real isolation (container/microVM/WASM — a
  Phase 2/3 gate, recorded in DR-8). The UI's security/"who can see this" copy may
  not promise more than this section.

## 7. Deployment path (D3)

- **Now:** one process on Windows/localhost; embedded relational DB (file-based);
  object store = local content-addressed directory; two browser profiles exercise
  multi-user flows.
- **Later (unchanged code, different config):** container image; managed/hosted
  Postgres-class DB (the ORM/migrations layer is written against the common subset
  from day one); S3-compatible object store behind the same interface; compute
  workers optionally on a second container (seam #1). No step requires schema or
  API rewrites; the swap points are configuration.

## 8. Answers to Stage 1 open items

| # | Open item | Answer |
|---|---|---|
| 1 | Local execution isolation → hosted mapping | Subprocess workers with time/memory caps now; same orchestrator contract backs a remote worker service later (seam #1). §3, §6, DR-4 |
| 2 | Dataset size ceiling | MVP ceiling **100 MB/file, 1 GB/project**, enforced at upload with a clear message; hashing and parsing are streaming so the ceiling is policy, not architecture. Revisit when a real need appears |
| 3 | Conflict-free notebook representation | Block-sequence model, per-block optimistic concurrency in MVP, CRDT-shaped storage for Phase 2; result blocks are references so CRDTs never touch scientific values. §4, DR-5 |
| 4 | Report-time reference resolution | Chip → artifact@version → object store, single rendering path, frozen manifest on export. §5, DR-9 |
