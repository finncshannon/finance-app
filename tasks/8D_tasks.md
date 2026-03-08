# Session 8D — Assumptions General Fixes (Terminal Clip, Scenario Reorder, Confidence, Sync Prep)
## Phase 8: Model Builder

**Priority:** Normal (Tier 2 per MASTER_INDEX — blocking bug fix + sync infrastructure)
**Type:** Frontend Only
**Depends On:** None
**Spec Reference:** `specs/phase8_model_builder_assumptions_general.md` → Areas 1–4

---

## SCOPE SUMMARY

Fix the CSS clipping bug on the Terminal Value section, reorder scenario pills to Bear/Base/Bull (Base stays default), add confidence threshold warnings (score < 80) with collapsible sections, and build the slider↔assumptions sync infrastructure in modelStore with a pending-overrides banner on the Assumptions tab.

---

## TASKS

### Task 1: Terminal Value Section Clipping Fix
**Description:** Fix CSS overflow issue causing the Terminal Value section card to cut off content.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.module.css`, audit the `.body` container (which wraps all sections). It currently has `overflow: hidden` or implicit height constraints. Change to `overflow-y: auto` if not already.
- [ ] 1.2 — Ensure `.section` cards have no `max-height` or `overflow: hidden` that would clip content.
- [ ] 1.3 — Ensure `.sectionBody` has `overflow: visible` (not hidden or constrained).
- [ ] 1.4 — In `frontend/src/pages/ModelBuilder/Assumptions/AssumptionCard.module.css`, verify that individual card rows don't have a fixed height that constrains content.
- [ ] 1.5 — Test with DDM assumptions which can have up to 5 cards in a section — no clipping should occur.

**Implementation Notes:**
- The `.container` has `overflow: hidden` and `height: 100%`. The `.body` should have `overflow-y: auto; flex: 1;` to allow scrolling while keeping header and metadata bar fixed.
- Look for any `max-height` on `.section` or `.sectionBody` — remove them.

---

### Task 2: Scenario Pill Reorder
**Description:** Change scenario order from Base/Bull/Bear to Bear/Base/Bull (left to right), keeping Base as the default selection.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx`, update the `SCENARIOS` array:
  ```typescript
  const SCENARIOS: { id: ScenarioKey; label: string }[] = [
    { id: 'bear', label: 'Bear' },
    { id: 'base', label: 'Base' },
    { id: 'bull', label: 'Bull' },
  ];
  ```
- [ ] 2.2 — Verify the default `useState<ScenarioKey>('base')` remains unchanged — Base is still the default on load.
- [ ] 2.3 — Verify the pill styling: the active pill highlight should still correctly indicate the selected scenario. Check that CSS doesn't rely on ordinal position (e.g. `:first-child` special styling).

---

### Task 3: Confidence Threshold Warning
**Description:** Add visual warning indicators to assumption sections with confidence scores below 80, and make sections collapsible.

**Subtasks:**
- [ ] 3.1 — In `AssumptionsTab.tsx`, update the `Section` sub-component to accept a new prop `collapsible: boolean` and `defaultExpanded: boolean`:
  ```typescript
  interface SectionProps {
    title: string;
    confidence?: ConfidenceDetail;
    reasoning?: string;
    overallScore: number;
    collapsible?: boolean;
    defaultExpanded?: boolean;
    children: React.ReactNode;
  }
  ```
- [ ] 3.2 — Implement collapse/expand: add `const [expanded, setExpanded] = useState(defaultExpanded ?? true)` in the Section component. When collapsed, hide `.sectionBody`. Toggle on header click (or a chevron button).
- [ ] 3.3 — Auto-expand logic: sections with confidence < 80 default to expanded; sections ≥ 80 can optionally start collapsed. Pass `defaultExpanded={score < 80}` (or always true if not collapsible).
- [ ] 3.4 — Warning indicator: when `score < 80`, show a small warning icon (⚠ or inline SVG) and "Review recommended" text next to the confidence badge in the section header.
  ```tsx
  {score < 80 && (
    <span className={styles.sectionWarning}>
      <span className={styles.warningIcon}>⚠</span>
      Review recommended
    </span>
  )}
  ```
- [ ] 3.5 — Overall confidence badge tooltip: add `title="Scores below 80 may indicate limited data or high uncertainty. Review and adjust assumptions manually."` to the overall confidence badge in the header.
- [ ] 3.6 — In `AssumptionsTab.module.css`, add:
  - `.sectionWarning` — `font-size: 10px; color: var(--color-warning); display: flex; align-items: center; gap: 4px;`
  - `.warningIcon` — `font-size: 12px;`
  - `.sectionHeaderClickable` — `cursor: pointer;` (when collapsible)
  - `.sectionBodyCollapsed` — `display: none;`
  - `.chevron` — small rotate animation for collapse indicator (0deg → -90deg when collapsed)
  - Smooth transition on `.sectionBody`: `max-height` transition or `display` toggle

**Implementation Notes:**
- The `Section` component currently always renders its children. Adding collapse wraps the children in a conditional `{expanded && children}` or a container with animated height.
- For simplicity, use `display: none` when collapsed (no animation needed — `max-height` transitions with auto are tricky). If smoother animation is desired, use a `ref` to measure content height.
- All sections should pass `collapsible={true}` by default.

---

### Task 4: Slider ↔ Assumptions Sync Prep (modelStore Infrastructure)
**Description:** Add shared state to modelStore for bidirectional sync between Sensitivity sliders and Assumptions, plus sensitivity state persistence.

**Subtasks:**
- [ ] 4.1 — In `frontend/src/stores/modelStore.ts`, add the following state:
  ```typescript
  pendingSliderOverrides: Record<string, number>;
  ```
  Default: `{}`
- [ ] 4.2 — Add actions:
  ```typescript
  setPendingSliderOverride: (key: string, value: number) => void;
  pushSliderToAssumptions: () => void;
  pullAssumptionsToSliders: (assumptions: Record<string, number>) => void;
  clearSliderOverrides: () => void;
  ```
- [ ] 4.3 — Implement `pushSliderToAssumptions()`:
  - Merges `pendingSliderOverrides` into `assumptions` (the existing assumptions record)
  - Clears `pendingSliderOverrides` afterward
  ```typescript
  pushSliderToAssumptions: () => set((state) => ({
    assumptions: { ...state.assumptions, ...state.pendingSliderOverrides },
    pendingSliderOverrides: {},
  })),
  ```
- [ ] 4.4 — Implement `pullAssumptionsToSliders(assumptions)`:
  - Sets `pendingSliderOverrides` to the provided map (called from the Sensitivity tab to load current assumptions as slider starting points)
  ```typescript
  pullAssumptionsToSliders: (assumptions) => set({ pendingSliderOverrides: assumptions }),
  ```
- [ ] 4.5 — Implement `clearSliderOverrides()`:
  ```typescript
  clearSliderOverrides: () => set({ pendingSliderOverrides: {} }),
  ```
- [ ] 4.6 — Add sensitivity persistence state to survive tab navigation:
  ```typescript
  sensitivityParams: Record<string, unknown> | null;
  setSensitivityParams: (params: Record<string, unknown> | null) => void;
  ```
  Default: `null`. The Sensitivity tab will store its parameter state here when navigating away.
- [ ] 4.7 — Update `reset()` action to also clear `pendingSliderOverrides: {}` and `sensitivityParams: null`.

---

### Task 5: Pending Slider Overrides Banner on Assumptions Tab
**Description:** Show a banner on the Assumptions tab when there are uncommitted slider changes from the Sensitivity tab.

**Subtasks:**
- [ ] 5.1 — In `AssumptionsTab.tsx`, read `pendingSliderOverrides` from `modelStore`:
  ```typescript
  const pendingOverrides = useModelStore((s) => s.pendingSliderOverrides);
  const pushSliderToAssumptions = useModelStore((s) => s.pushSliderToAssumptions);
  const clearSliderOverrides = useModelStore((s) => s.clearSliderOverrides);
  const pendingCount = Object.keys(pendingOverrides).length;
  ```
- [ ] 5.2 — When `pendingCount > 0`, render a banner at the top of the body area (below header, above sections):
  ```tsx
  {pendingCount > 0 && (
    <div className={styles.syncBanner}>
      <span className={styles.syncBannerText}>
        You have {pendingCount} uncommitted change{pendingCount > 1 ? 's' : ''} from Sensitivity sliders.
      </span>
      <button className={styles.syncBannerApply} onClick={pushSliderToAssumptions}>
        Apply
      </button>
      <button className={styles.syncBannerDismiss} onClick={clearSliderOverrides}>
        Dismiss
      </button>
    </div>
  )}
  ```
- [ ] 5.3 — In `AssumptionsTab.module.css`, add banner styles:
  - `.syncBanner` — `display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-4); background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.15); border-radius: var(--radius-md); margin: var(--space-3) var(--space-4) 0;`
  - `.syncBannerText` — `font-size: 12px; color: var(--text-secondary); flex: 1;`
  - `.syncBannerApply` — primary action style (accent color, small button)
  - `.syncBannerDismiss` — ghost style (text-only, subtle)

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Terminal Value section content is fully visible, no clipping.
- [ ] AC-2: DDM assumptions with 5 cards in a section display without clipping.
- [ ] AC-3: `.body` container scrolls when content exceeds viewport.
- [ ] AC-4: Scenario pills order is Bear / Base / Bull (left to right).
- [ ] AC-5: Base scenario is still the default on load.
- [ ] AC-6: Sections with confidence < 80 show warning icon and "Review recommended" text.
- [ ] AC-7: Sections are collapsible (click header or chevron to toggle).
- [ ] AC-8: Sections with confidence < 80 default to expanded; ≥ 80 may start collapsed (or all expanded is fine).
- [ ] AC-9: Overall confidence badge has a tooltip explaining the 80 threshold.
- [ ] AC-10: `modelStore` has `pendingSliderOverrides` state with `setPendingSliderOverride`, `pushSliderToAssumptions`, `pullAssumptionsToSliders`, `clearSliderOverrides` actions.
- [ ] AC-11: `modelStore` has `sensitivityParams` state for persistence across tab navigation.
- [ ] AC-12: `modelStore.reset()` clears slider overrides and sensitivity params.
- [ ] AC-13: When `pendingSliderOverrides` has entries, Assumptions tab shows a blue banner: "You have N uncommitted changes from Sensitivity sliders. [Apply] [Dismiss]"
- [ ] AC-14: "Apply" button merges pending overrides into assumptions and clears pending.
- [ ] AC-15: "Dismiss" button clears pending overrides without applying.
- [ ] AC-16: No visual regressions on existing Assumptions tab functionality (override, reset, generate, scenario switching).

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx` — scenario reorder, Section collapse/expand, confidence warning, slider sync banner
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.module.css` — overflow fix, warning styles, collapse styles, sync banner styles
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionCard.module.css` — verify no height constraints (may not need changes)
- `frontend/src/stores/modelStore.ts` — add `pendingSliderOverrides`, `sensitivityParams`, sync actions

---

## BUILDER PROMPT

> **Session 8D — Assumptions General Fixes (Terminal Clip, Scenario Reorder, Confidence, Sync Prep)**
>
> You are building session 8D of the Finance App v2.0 update.
>
> **What you're doing:** Fixing 4 items on the Assumptions tab: (1) CSS clipping bug on Terminal Value section, (2) reorder scenario pills to Bear/Base/Bull, (3) add confidence warnings and collapsible sections, (4) build slider↔assumptions sync infrastructure in modelStore.
>
> **Context:** The Assumptions tab (`AssumptionsTab.tsx`) lets users view and override auto-generated assumptions per scenario (base/bull/bear). Each section (Growth, Margins, Terminal Value, DCF, DDM) has a confidence score. The tab uses `AssumptionCard` components for individual fields. Sensitivity sliders (separate tab) will sync with these assumptions bidirectionally — you're building the shared state infrastructure now.
>
> **Existing code:**
> - `AssumptionsTab.tsx` — located at `frontend/src/pages/ModelBuilder/Assumptions/`. Has `SCENARIOS` array (currently Base/Bull/Bear order), `Section` sub-component, `AssumptionCard` usage per field. Reads `activeTicker` from modelStore. Local state: `data` (AssumptionSet), `loading`, `error`, `scenario` (ScenarioKey), `overrides`.
> - `AssumptionsTab.module.css` — `.container { height: 100%; overflow: hidden }`, `.body` wraps sections, `.section` cards with `.sectionHeader` + `.sectionBody`. Confidence badge classes: `.confGreen` (≥80), `.confYellow` (≥60), etc.
> - `modelStore.ts` — Zustand store with `activeTicker`, `activeModelType`, `assumptions: Record<string, unknown>`, `output`, `versions`, actions. No slider sync state yet.
> - The `Section` sub-component takes `title`, `confidence`, `reasoning`, `overallScore`, `children`. Currently always shows body (not collapsible).
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Terminal Value Clipping Fix**
>
> In `AssumptionsTab.module.css`:
> - Ensure `.container` has `overflow: hidden` (correct — it frames the page)
> - Ensure `.body` (the scrollable area between header and metaBar) has `flex: 1; overflow-y: auto;`
> - Remove any `max-height` or `overflow: hidden` on `.section` or `.sectionBody`
> - Ensure `.sectionBody` children can grow without constraint
>
> In `AssumptionCard.module.css`:
> - Verify cards don't have fixed heights that constrain content
>
> **Task 2: Scenario Pill Reorder**
>
> In `AssumptionsTab.tsx`, change:
> ```typescript
> const SCENARIOS: { id: ScenarioKey; label: string }[] = [
>   { id: 'bear', label: 'Bear' },
>   { id: 'base', label: 'Base' },
>   { id: 'bull', label: 'Bull' },
> ];
> ```
> Keep default: `useState<ScenarioKey>('base')` unchanged.
>
> **Task 3: Confidence Warnings + Collapsible Sections**
>
> Update the `Section` sub-component:
> - Add props: `collapsible?: boolean`, `defaultExpanded?: boolean`
> - Add state: `const [expanded, setExpanded] = useState(defaultExpanded ?? true)`
> - Make header clickable when collapsible (toggle expanded)
> - Add a small chevron (▶ / ▼) that rotates based on state
> - When collapsed: hide `.sectionBody` (`{expanded && <div className={styles.sectionBody}>{children}</div>}`)
> - When confidence score < 80: show warning indicator next to confidence badge:
>   ```tsx
>   {score < 80 && (
>     <span className={styles.sectionWarning}>⚠ Review recommended</span>
>   )}
>   ```
> - Add tooltip to the overall confidence badge in the header (the one at the tab level, not per-section):
>   `title="Scores below 80 may indicate limited data or high uncertainty. Review and adjust assumptions manually."`
> - When calling `<Section>`, pass `collapsible={true}` and `defaultExpanded={score < 80 || true}` (expand low-confidence sections by default; optionally keep all expanded initially — user can collapse manually).
>
> CSS additions:
> - `.sectionWarning { font-size: 10px; color: var(--color-warning); display: flex; align-items: center; gap: 4px; margin-left: auto; }`
> - `.sectionHeaderClickable { cursor: pointer; user-select: none; }`
> - `.chevron { font-size: 10px; color: var(--text-tertiary); transition: transform 150ms ease; }`
> - `.chevronCollapsed { transform: rotate(-90deg); }`
>
> **Task 4: modelStore Slider Sync Infrastructure**
>
> In `frontend/src/stores/modelStore.ts`:
>
> Add to state interface:
> ```typescript
> pendingSliderOverrides: Record<string, number>;
> sensitivityParams: Record<string, unknown> | null;
>
> setPendingSliderOverride: (key: string, value: number) => void;
> pushSliderToAssumptions: () => void;
> pullAssumptionsToSliders: (assumptions: Record<string, number>) => void;
> clearSliderOverrides: () => void;
> setSensitivityParams: (params: Record<string, unknown> | null) => void;
> ```
>
> Add defaults:
> ```typescript
> pendingSliderOverrides: {},
> sensitivityParams: null,
> ```
>
> Implement actions:
> ```typescript
> setPendingSliderOverride: (key, value) =>
>   set((state) => ({
>     pendingSliderOverrides: { ...state.pendingSliderOverrides, [key]: value },
>   })),
>
> pushSliderToAssumptions: () =>
>   set((state) => ({
>     assumptions: { ...state.assumptions, ...state.pendingSliderOverrides },
>     pendingSliderOverrides: {},
>   })),
>
> pullAssumptionsToSliders: (assumptions) =>
>   set({ pendingSliderOverrides: assumptions }),
>
> clearSliderOverrides: () => set({ pendingSliderOverrides: {} }),
>
> setSensitivityParams: (params) => set({ sensitivityParams: params }),
> ```
>
> Update `reset()` to include:
> ```typescript
> pendingSliderOverrides: {},
> sensitivityParams: null,
> ```
>
> **Task 5: Pending Slider Overrides Banner**
>
> In `AssumptionsTab.tsx`:
> - Read `pendingSliderOverrides`, `pushSliderToAssumptions`, `clearSliderOverrides` from modelStore
> - When `Object.keys(pendingSliderOverrides).length > 0`, show a banner at the top of the body area:
>   ```
>   You have N uncommitted change(s) from Sensitivity sliders. [Apply] [Dismiss]
>   ```
> - "Apply" calls `pushSliderToAssumptions()` then re-generates/re-fetches
> - "Dismiss" calls `clearSliderOverrides()`
> - Banner style: subtle blue background, inline flex, accent-colored "Apply" button, ghost "Dismiss"
>
> **Acceptance criteria:**
> 1. Terminal Value section fully visible, no clipping, body scrolls
> 2. Scenario order: Bear / Base / Bull (left to right), Base default
> 3. Sections with confidence < 80: warning icon + "Review recommended"
> 4. Sections are collapsible (click header to toggle)
> 5. Overall confidence badge has tooltip explaining 80 threshold
> 6. modelStore has pendingSliderOverrides + sync actions
> 7. modelStore has sensitivityParams for persistence
> 8. reset() clears all new state
> 9. Pending overrides banner shows when slider changes exist
> 10. Apply merges overrides, Dismiss clears them
> 11. No regressions on existing Assumptions functionality
>
> **Files to create:** None
>
> **Files to modify:**
> - `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx`
> - `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.module.css`
> - `frontend/src/pages/ModelBuilder/Assumptions/AssumptionCard.module.css` (verify only)
> - `frontend/src/stores/modelStore.ts`
>
> **Technical constraints:**
> - CSS modules for all styling
> - Zustand for all state management
> - Collapse: use conditional rendering (`{expanded && children}`) for simplicity — no animation library needed
> - Scenario order convention: Bear / Base / Bull everywhere in the app
> - The sync infrastructure is prep-only — the Sensitivity tab (session 8M) will build the full UI
> - Don't modify any backend files
