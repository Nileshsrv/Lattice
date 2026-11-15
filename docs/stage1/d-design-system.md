# Stage 1(d) — Design System & Interaction Patterns

Aesthetic: minimal, modern, crystal-glassmorphic, calm, technical, premium.
Priority order (binding, [Source A prevails]):
**1 readability & scientific clarity · 2 efficient workflow · 3 hierarchy & discoverability ·
4 consistent visual language · 5 visual effects.**
Any conflict between glass and legibility resolves against glass, automatically.

## 1. Surface model (where glass is allowed)

| Surface class | Treatment | Used for |
|---|---|---|
| **Work surface** | Opaque (≥ 98% opacity), no backdrop blur, solid background token | Notebook canvas, plots, tables, equations, long text, result panels |
| **Chrome glass** | Translucent + backdrop blur | Top bar, left nav, right panel, tool palettes, overlays/modals, command palette |
| **Float glass** | Lighter translucency, stronger blur | Tooltips, context menus, transient popovers |

Hard rules: no transparency behind equations, data tables, chart labels, or body text.
Blur/glow/gradient may never reduce text or data-ink contrast below §6 thresholds.

## 2. Tokens (starting values — tunable; contrast pairs validated by automated check from Stage 3, see e-acceptance-tests T-UX)

Dark theme is the default identity; light theme is a first-class peer, not an afterthought.

```
— Glass —
glass.blur.chrome        16px        glass.blur.float       24px
glass.opacity.chrome     0.72 (dark) / 0.80 (light)
glass.opacity.float      0.60 (dark) / 0.70 (light)
glass.border             1px, white @ 8% (dark) / black @ 8% (light)
glass.highlight          inner top edge, white @ 6%, dark theme only
glass.shadow             y=8 blur=24 @ 10–14% black — one elevation scale, 3 steps

— Color roles (dark / light) —
bg.canvas                #0E1116  /  #F7F8FA      app backdrop
bg.work                  #151A21  /  #FFFFFF      opaque work surfaces
text.primary             #E8EBEF  /  #1A1F26
text.secondary           #9AA3AF  /  #525A66
accent                   single restrained accent (azure family), interactive elements only
semantic                 ok · warn · error · running — each paired with an icon/shape (never color alone)
data palette             6 categorical series colors, colorblind-safe set (validated), plus
                         fit-line style (solid) vs data style (points) vs uncertainty band
                         (translucent fill + outline) distinguished by SHAPE as well as color

— Type —
font.ui                  humanist sans; sizes 13/14/16/20/24; line-height ≥ 1.5 body
font.data                tabular lining numerals everywhere numbers align (tables, results, ticks)
font.math                proper math rendering for equations (not italic text)
font.mono                code cells, ids, hashes

— Space & motion —
space                    4px base scale
radius                   10px chrome · 6px controls · 2px plots-internal
motion                   120–200ms ease-out; state changes only; no ambient/background
                         animation; honors reduced-motion preference by disabling all
                         non-essential motion
```

## 3. Scientific display rules (non-negotiable)

- Every physical quantity renders with its **unit**; dimensionless is explicit.
- Significant figures controlled and consistent; full precision on hover/copy.
- Numbers selectable and copyable everywhere, including plot-adjacent readouts.
- Uncertainty shown where defined (± , CI band); its absence is honest, not implied-zero.
- Plots: high-contrast axes/ticks/legends; zoom, pan, range-select, point inspection;
  export of underlying numbers always adjacent to image export.
- Provenance label (measured/calculated/simulated/estimated/ai-suggested) and maturity badge
  (validated/educational/experimental/beta) are visible chips, not tooltips.
- Guard statements from the tool contract (`guards[]`) render inside the result panel.

## 4. Component inventory (MVP)

### 4.1 Chrome
Top bar · project switcher · global command/search palette · left nav (two zones) ·
right inspector panel · presence avatars · notifications · run-status indicator.

### 4.2 Primitives
Buttons (primary/secondary/danger/Run) · chips & badges (state, provenance, maturity) ·
**parameter control = paired slider + numeric field + unit**, with constraint hints and
out-of-range messaging (blocking, not clamping) · select (model/method/preset) ·
file dropzone with format/license capture · toast/inline alerts · tabs · tooltip ·
dialog · empty-state pattern (every empty area names the next action).

### 4.3 Standard tool anatomy (every tool, standalone page or notebook block)
1 title + purpose · 2 domain + maturity · 3 model/method selector · 4 input panel
(units, constraints) · 5 data/preset selection · 6 main visualisation ·
7 numerical results (+ uncertainty) · 8 equations & assumptions (collapsible, present) ·
9 validation/warnings panel · 10 run history & compare · 11 save-to-project / export ·
12 references. Blocks collapse to a summary row (name, key result, state chip).

### 4.4 Scientific views
Plot frame (standard toolbar: zoom/pan/select/inspect/export-data/export-image) ·
data table (virtualised, unit headers, copy) · equation block · dataset preview
(+ unknowns panel) · run detail view (the full §3 record, human-readable) ·
**comparison view** (param diff table + overlaid/stacked plots) · lineage tree ·
comment thread (anchored) · report section editor with reference chips.

## 5. Interaction patterns

| Pattern | Behaviour |
|---|---|
| Live exploration | `instant` tools recompute on input change; "unsaved" chip visible; Save creates the run |
| Explicit run | `long-running` tools: Run button, progress, cancel; results land atomically |
| Sweep | choose variable(s) + range + steps; output is an array artifact; plot is its view |
| Overlay/compare | select ≥2 runs anywhere runs are listed → comparison view |
| Drill-down | any displayed value → popover: run, inputs, method, parents → full run detail |
| Save-as-artifact | one gesture from any result/plot/table; lands in project with lineage |
| Annotate | comment on block, point, row, equation; thread follows the artifact |
| Inverse analysis | result includes solution set, non-uniqueness statement, assumptions |
| Stale handling | upstream change marks downstream views stale (badge + "review & update" action); nothing auto-recomputes |
| Keyboard | command palette covers open/insert/run/compare; full focus-visible traversal |

## 6. Accessibility checklist (checked per component, automated where possible)

- Contrast: ≥ 4.5:1 body text, ≥ 3:1 large text and essential UI/graphics — measured
  against the *worst-case backdrop* for glass surfaces (test harness renders glass over
  the busiest permitted backdrop and measures).
- Never color-only encoding: state uses icon+color; series use shape/dash+color.
- Visible focus states on all interactive elements; logical tab order; command palette
  fully keyboard-driven.
- Reduced-motion preference disables non-essential animation.
- Plots: data table alternative reachable from every chart; axis labels real text.
- Hit targets ≥ 24px; slider values always editable numerically.
- Responsive: usable at 1280px laptop width; below that, right panel overlays, nav
  collapses to icons, tool blocks stack — reading and reviewing degrade gracefully,
  heavy editing may remain desktop-first (stated, not pretended otherwise).
