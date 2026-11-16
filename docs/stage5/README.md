# Stage 5 — Collaboration, Assistant, Report Polish: Completion Report

Status: **complete**. Stage 5 was started with Codex/Antigravity assistance
(committed as the Stage 4 baseline commit); this report covers the finishing work
and the verified state of the whole stage.

## Inherited at the start of this pass (already working, committed as baseline)

- Anchored artifact **comments** API (create/list/resolve, author/role rules) wired
  into the run page.
- **Review states** (draft → needs-review → approved → archived) with role
  enforcement and audit events, wired into the run page.
- **Saved run comparisons** (comparison artifacts, parameter/output diffs, overlay
  plots) with a comparison page.
- **Report polish**: report types, staleness detection against source artifacts,
  print CSS + Print/Save-as-PDF action.
- **Assistant API**: rule-based tool dispatcher with approval-gated execution.

## Finished in this pass

1. **Assistant tool-map fix**: stellar suggestions pointed at a nonexistent id
   (`stellar.wien`), so they silently never fired; the map now names only
   registered tools, and a regression test pins every mapping to the registry.
2. **Assistant execution safety**: tools that take datasets are refused at the
   execute endpoint (the assistant binds no data) and the UI routes the user to
   the tool page instead, where data is bound by reference.
3. **Assistant UI**: collapsible panel on the project page — question → tool plan
   with guards and maturity shown → per-input approval form → execution produces a
   normal run with provenance `ai-suggested`. The panel states plainly that it is
   a rule-based dispatcher that computes nothing itself.
4. **Presence**: WebSocket hub (`/api/ws/projects/{id}`), session-cookie
   authenticated, members only; online members show live on the project page.
   This is extraction seam #2 from the architecture, ready to grow into the
   Phase 2 sync server.
5. **Notebook comments**: comment thread on the notebook page, anchorable to a
   specific block, with resolve/reopen.

## Verification

- **50 backend tests pass** (was 44): six new Stage 5 tests cover assistant
  suggestion correctness, approval gating (nothing executes on `approved: false`),
  `ai-suggested` provenance on assistant runs, dataset-tool refusal, presence
  join/leave broadcasts, non-member WebSocket rejection, and anchored notebook
  comments with resolution.
- Frontend `tsc` + production build clean.
- Live browser walk: presence marker appears over the WebSocket; assistant asked
  for Compton scattering produced a plan with the free-electron guard, and the
  approved execution returned λ-shift = λ_C and E′ = E/2 at (E ≈ m_e c², θ = 90°)
  — the exact P-2 anchors — saved as an `ai-suggested` run.

## Decisions and honest limitations

- **The assistant is rule-based, not an LLM** (deviation from standing assumption
  D5, which planned the Claude API here). The inherited implementation satisfies
  the §8 hard rules by construction — it cannot fabricate numbers because it has
  no generative path at all. Wiring the Claude API behind the same
  plan-approve-execute contract remains future work gated on an API key and cost
  controls; the orchestration boundary (registered tools, validated inputs,
  logged runs) is already the one §11 requires of an LLM-backed assistant.
- Presence is the only real-time fact pushed so far; run status and comments still
  arrive on reload (runs are synchronous, so nothing is lost).
- Live co-editing remains Phase 2 by decision D1; the per-block conflict flow is
  the MVP behaviour.
- Prior stages' standing gaps (worker memory caps on Windows, headless PDF
  export, Plotly bundle size, regression column naming) are unchanged and tracked
  in docs/stage3 and docs/stage4.

## MVP acceptance criteria (§13) — status

Create project & invite ✓ · project holds datasets/notes/equations*/simulations/
plots/reports ✓ (*equations render in tool panels and reports; a dedicated
notebook equation block is still open) · ≥3 physics tools with documented models,
units and passing validation suites ✓ (8 tools, P-1…P-4) · real dataset imported
and analysed ✓ (CALSPEC solar spectrum) · outputs feed downstream tools without
re-upload ✓ · two collaborators review and discuss results ✓ (roles, comments,
review states) · alternative configurations compared ✓ (comparisons; branch
lineage via parent_run) · provenance preserved ✓ · report generated from real
artifacts and exported ✓ · assistant operates tools without inventing outputs,
linked to saved results ✓.
