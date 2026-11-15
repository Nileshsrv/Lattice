# Stage 1 — Product Definition

Status: **awaiting review** (staged protocol §15; no code until Stage 3, no stack until Stage 2 approval).

This folder is the product definition for the Collaborative Computational Research Workspace
(working name "Lattice" after this repository — the product name is undecided).
It translates Source A (concept brief) and the master prompt into reviewable specs.
Source A prevails over any conflict; resolutions marked **[Source A prevails]** in the
master prompt are preserved here and must not be reverted.

## Deliverables

| Doc | Contents |
|---|---|
| [a-user-journeys.md](a-user-journeys.md) | The spine workflow and three worked journeys (stellar, tunnelling, Compton), each annotated with the artifacts and provenance created at every step |
| [b-information-architecture.md](b-information-architecture.md) | Areas, entity hierarchy, navigation, addressing, search, permissions |
| [c-schemas.md](c-schemas.md) | Conceptual specs: Artifact, Dataset, Run, Variant, Notebook, Report, Tool Contract, Comment — plus the system invariants |
| [d-design-system.md](d-design-system.md) | Glassmorphic design tokens, component inventory, interaction patterns, state and accessibility rules |
| [e-acceptance-tests.md](e-acceptance-tests.md) | Refined MVP acceptance tests and the physics validation suites with concrete anchors and tolerances |

## Stage 0 decision record (baseline for everything below)

| # | Decision | Consequence in these docs |
|---|---|---|
| D1 | Real-time co-editing ships in Phase 2; MVP ships shared projects, presence, anchored comments, variants, version history | Data model is designed conflict-free from day one (see c-schemas invariants I-7, I-8); no live text co-editing in MVP acceptance tests |
| D2 | Web application, laptop/desktop screens first | IA and design system assume browser; responsive degradation rules in d-design-system |
| D3 | Local-first development; cheaply deployable later | No architecture here; Stage 2 must show a local-dev → small-cloud path without rework |
| D4 | Solo build (user + Claude); first users are the user plus a few collaborators | Lightweight process; tests concentrate on physics and provenance correctness |
| D5 (standing assumption) | AI assistant arrives in Stage 5 using the Claude API; cost is a design constraint | AI panel is reserved in the IA and design system but every MVP flow works without it |
| D6 (standing assumption) | Representative dataset = public-domain stellar spectrum with licensing recorded | Journey A and acceptance tests reference it as `sample-spectrum` |

## Deliberately absent

- **No technology stack.** Anything that looks like an implementation hint (e.g., "content hash") is a requirement on behaviour, not a library choice.
- **No AI assistant behaviour spec beyond §8 of the master prompt.** Stage 5 will refine it against the then-existing tool registry.
- **No Research Library design.** Phase 4; the IA reserves its navigation slot only.

## Open items that Stage 2 (architecture) must answer

1. How run execution is isolated and resource-limited on a local machine, and how the same contract maps to a hosted environment later.
2. How content hashing and immutable raw storage work for datasets of realistic size (a FITS spectrum is small; design must state its assumed size ceiling honestly).
3. The conflict-free data representation for notebook/variant state (chosen for D1).
4. How the report builder resolves `artifact@version` references at export time.
