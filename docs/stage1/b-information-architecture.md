# Stage 1(b) — Information Architecture

Web application (D2). Five primary areas plus persistent project context and a collapsible
AI panel (reserved; functional in Stage 5). No standalone chat — discussion anchors to artifacts.

## 1. Entity hierarchy

```
Account (user)
└── Project  (the unit of access control; private by default)
    ├── Members & roles        owner · editor · collaborator · reviewer · viewer
    ├── Datasets               raw (immutable) + derived chains
    ├── Runs                   with lineage (parent run / branch)
    ├── Notebooks              ordered block documents
    ├── Artifacts (other)      figures, tables, equations, saved comparisons, notes
    ├── References             (MVP: user-entered citations; Phase 4: Research Library)
    ├── Comments & tasks       anchored to artifacts / sub-anchors
    ├── Reports                drafts + frozen exported versions
    └── Activity & versions    append-only history
```

Everything under a project is a **Research Artifact** with a stable identity (c-schemas §1).
Tools live *outside* projects in the Workbench registry; a project references tools at
pinned versions via its runs.

## 2. Addressing

Every artifact is addressable as `project / artifact-id @ version`. Requirements:

- Stable across renames; survives export (reports embed these references).
- Granular sub-anchors for comments: `artifact@v # anchor` where anchor may be a table row,
  a plotted series/point, an equation, a notebook block, or a line-match entry.
- A reference without `@version` means "latest" only in live views; reports and comparisons
  always pin versions (I-10).

## 3. Navigation model

### Top bar (persistent)
Product/home · **project switcher with current project context** · global search / command
entry (§5) · presence avatars (restrained) · notifications · run/sync status · account.

### Left nav (two zones)
**Global areas:** Projects · Workbench · Notebook · Research Library *(placeholder, Phase 4,
visibly labelled "coming later" rather than hidden, so the IA is honest about scope)* · Reports.
**Project zone (when a project is open):** Overview · Datasets · Runs & simulations ·
Notebooks · Reports · Tasks & comments · Activity · Settings/members.

### Central workspace
Tabbed/panelled: an open notebook, a standalone tool, a dataset preview, a comparison view,
or a report draft. Tabs preserve project context. Blocks within a notebook are reorderable,
collapsible, and comparable (d-design-system §5).

### Right panel (collapsible)
Contextual to selection: run details / parameter editor / comments for the selected artifact.
The AI assistant occupies this slot from Stage 5; until then the slot is the
artifact-inspector. When closed it consumes no space.

## 4. Area-by-area scope (MVP vs later)

| Area | MVP | Later |
|---|---|---|
| **Projects** | Create, invite, roles, overview with real status (recent activity, latest runs, open tasks, report state), activity feed | Institution roles, governance (Phase 6) |
| **Workbench** | Registry of the 4 labs + shared math utilities; browse by discipline/task; tool page = standard anatomy; maturity labels | Contributed tools, private collections (Phase 6) |
| **Notebook** | Blocks: rich text, equations, code cells*, tool blocks, plots, tables, dataset previews, figures, attachments, user-entered citations, comments. Versioned saves; variants. *Code-cell execution scope decided at Stage 2 (sandboxing). | Live co-editing (Phase 2), AI-drafted blocks flagged (Stage 5) |
| **Research Library** | Navigation placeholder only | Phase 4 per roadmap |
| **Reports** | Templates (lab report, computational analysis); assemble from artifacts; numbering; citation list from project references; review states; export PDF/HTML | DOCX/LaTeX, regeneration against newer runs with version preservation |

## 5. Search & command

One entry point returning **actions, not documentation links**:
open tool, open artifact, insert block, start comparison.
Searchable by: tool name, discipline, task phrase ("fit a Gaussian peak"), physical quantity,
artifact name, dataset, project content. MVP may rank naively; the contract is that results
are *executable*.

## 6. Permissions

- Private by default; owner manages membership and link sharing (off in MVP beyond members).
- Roles gate: viewing, commenting, running tools, saving runs, editing notebooks,
  approving reviews, exporting, managing members.
- Reviewer can comment and set review states but not edit content.
- Every permission-relevant action lands in the activity history (audit trail).
- UI always answers "who can see this?" from the artifact itself.

## 7. State vocabulary (used identically everywhere)

| State | Applies to | Meaning |
|---|---|---|
| draft / unsaved | tool configs, report sections | live, not yet an artifact; visually distinct |
| queued / running | runs | explicit execution in progress; cancellable |
| completed / failed / cancelled | runs | terminal; failures keep logs + partial provenance |
| stale | downstream views | an upstream artifact has a newer version; nothing auto-updates |
| needs review / approved / archived | reviewable artifacts, reports | human decisions, recorded |
