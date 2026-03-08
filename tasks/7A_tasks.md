# Session 7A — Boot Sequence & Dashboard Animations
## Phase 7: Dashboard

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** None
**Spec Reference:** `specs/phase7_dashboard.md` → Areas 1A, 1B, 3A

---

## SCOPE SUMMARY

Extend the boot sequence animation from ~2 seconds to ~4–5 seconds with more boot lines, slower stagger, a completion status line, and a pulsing cursor. After the boot overlay fades, add staggered widget entry animations to the dashboard. Also add a spinner icon to the Refresh button while loading.

---

## TASKS

### Task 1: Extend Boot Duration and Add Boot Lines
**Description:** Increase phase timings, add more boot lines, slow the stagger and checkmark speeds, add a completion line, and add a pulsing cursor.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/components/BootSequence/BootSequence.tsx`, update phase timing constants: `PHASE_BLACK_DURATION` 200→300, `PHASE_TERMINAL_DURATION` 600→1500, `PHASE_SHIFT_DURATION` 700→800, `PHASE_FADEOUT_DURATION` 500→600
- [ ] 1.2 — In `frontend/src/components/BootSequence/BootPhase.tsx`, expand `BOOT_LINES` array from 5 to 9–10 lines. Add: "Scanning universe", "Syncing portfolio", "Loading watchlists", "Connecting market feeds". Reorder logically. Change the last line's prefix to `└──`.
- [ ] 1.3 — In `BootPhase.tsx`, increase `staggerMs` default from 70 to 110. Increase checkmark stagger from 60 to 90.
- [ ] 1.4 — In `BootPhase.tsx`, add an "All systems online" completion status line that appears after all checkmarks are visible, before the shift phase begins. Style it with a slightly brighter color (e.g. `var(--accent-primary)`).
- [ ] 1.5 — In `BootSequence.module.css`, add a pulsing cursor/caret animation (blinking `_` or `▌`) that appears on the status line while boot lines are animating. Use CSS `@keyframes` with `opacity` toggle at 500ms intervals. Hide cursor once "All systems online" appears.
- [ ] 1.6 — Update the version string in `BootPhase.tsx` from `VALUATION ENGINE v1.0` to `VALUATION ENGINE v2.0`.

**Implementation Notes:**
- Current `BootPhase` renders headers (title, divider, status), then boot lines, then checkmarks. The "All systems online" line should be a new element after the boot lines list, shown only when `visibleChecks === BOOT_LINES.length`.
- The cursor should be a `::after` pseudo-element on the status line, or a dedicated `<span>` toggled by state.
- Total boot time calculation: 300ms black + 1500ms terminal (with ~10 lines × 110ms = 1100ms for lines + ~10 × 90ms = 900ms for checks, overlapping with terminal phase) + 800ms shift + 600ms fadeout ≈ 3.2–4.5s depending on backend readiness.

---

### Task 2: Dashboard Widget Entry Animations
**Description:** After boot overlay fades, dashboard widgets animate in with a staggered cascade (fade-up + subtle scale), only on initial boot.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/stores/uiStore.ts`, add a `justBooted: boolean` flag (default: `false`) and a `setJustBooted: (val: boolean) => void` action.
- [ ] 2.2 — In `frontend/src/App.tsx`, inside the `handleBootComplete` callback, call `useUIStore.getState().setJustBooted(true)` so the dashboard knows this is the first load after boot.
- [ ] 2.3 — In `frontend/src/pages/Dashboard/DashboardPage.tsx`, read `justBooted` from `uiStore`. If `justBooted` is true and data is loaded, run a staggered animation sequence: set an `animationPhase` state from 0→5 (one per widget) with 175ms intervals via `setTimeout`. After all 5 phases complete, `justBooted` remains `true` (never reset — it just controls the initial cascade). If `justBooted` is false (tab switch back to dashboard), skip animation entirely — all widgets render immediately.
- [ ] 2.4 — In `DashboardPage.tsx`, apply CSS classes to each grid cell: `styles.widgetHidden` when `animationPhase < index`, and `styles.widgetVisible` when `animationPhase >= index`. The stagger order is: 0=Market, 1=Portfolio, 2=Watchlist, 3=Models, 4=Events.
- [ ] 2.5 — In `frontend/src/pages/Dashboard/DashboardPage.module.css`, add `.widgetHidden` (opacity: 0, transform: translateY(12px) scale(0.98)) and `.widgetVisible` (opacity: 1, transform: translateY(0) scale(1), transition: opacity 300ms ease-out, transform 300ms ease-out).

**Implementation Notes:**
- The `justBooted` flag is set once on boot complete and never cleared during the session. The animation only runs once because `DashboardPage` unmounts when navigating away and remounts when returning — but on remount, the `animationPhase` local state resets to 0 and the component should check `justBooted` and, if a second visit, skip straight to all widgets visible.
- Actually, `justBooted` should be used as a "first visit" flag. Better approach: add `dashboardAnimationPlayed: boolean` to `uiStore` (default: false). On first render after boot, play the cascade and set `dashboardAnimationPlayed = true`. On subsequent visits, skip.
- Revised: Replace `justBooted` with `dashboardAnimationPlayed`. App.tsx sets `justBooted = true` on boot complete. DashboardPage checks `justBooted && !dashboardAnimationPlayed` to decide whether to animate.

---

### Task 3: Refresh Button Spinner
**Description:** Add a CSS-only animated spinner icon to the dashboard Refresh button while loading.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/Dashboard/DashboardPage.tsx`, when `loading` is true, render a `<span className={styles.spinner} />` element inside the refresh button before the text.
- [ ] 3.2 — In `frontend/src/pages/Dashboard/DashboardPage.module.css`, add `.spinner` styles: an 11px × 11px circle with 2px border (top border colored `var(--accent-primary)`, rest `var(--border-subtle)`), `border-radius: 50%`, CSS `@keyframes spin { to { transform: rotate(360deg) } }`, `animation: spin 0.7s linear infinite`. Add `display: inline-block` and appropriate margin.

**Implementation Notes:**
- Keep the existing "Refreshing..." text. The spinner sits to the left of the text.
- The refresh button already has `display: flex; align-items: center; gap: var(--space-2)` styling, so the spinner just needs to be the first child.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Boot sequence total duration is approximately 4–5 seconds (was ~2 seconds).
- [ ] AC-2: Boot terminal shows 9–10 boot lines (was 5), each appearing with ~110ms stagger.
- [ ] AC-3: Checkmarks appear after all lines are visible with ~90ms stagger (was 60ms).
- [ ] AC-4: An "All systems online" status line appears after all checkmarks complete, styled in accent color.
- [ ] AC-5: A blinking cursor/caret is visible on the status line during boot line animation, disappears after "All systems online" shows.
- [ ] AC-6: Phase timing constants are updated: black=300ms, terminal=1500ms, shift=800ms, fadeout=600ms.
- [ ] AC-7: Title reads "VALUATION ENGINE v2.0".
- [ ] AC-8: After boot overlay fades, dashboard widgets animate in with staggered fade-up + scale cascade (~175ms between each, 300ms per widget transition).
- [ ] AC-9: Widget entry animation order: Market → Portfolio → Watchlist → Models → Events.
- [ ] AC-10: Widget entry animation only plays on initial app boot, not on subsequent Dashboard tab visits.
- [ ] AC-11: `uiStore` has `justBooted` and `dashboardAnimationPlayed` flags.
- [ ] AC-12: Refresh button shows a small spinning circle icon while loading, alongside "Refreshing..." text.
- [ ] AC-13: All existing boot sequence behavior (backend readiness gating, fade-out overlay, phase transitions) is preserved.
- [ ] AC-14: No visual regressions on dashboard grid layout, widget styling, or responsive breakpoints.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/components/BootSequence/BootSequence.tsx` — phase timing constants (4 values)
- `frontend/src/components/BootSequence/BootPhase.tsx` — boot lines array (add 4–5 lines), stagger timing, checkmark stagger, completion status line, cursor logic, version string
- `frontend/src/components/BootSequence/BootSequence.module.css` — cursor blink keyframes, completion line styles
- `frontend/src/pages/Dashboard/DashboardPage.tsx` — animation phase logic, conditional CSS classes on grid cells, spinner in refresh button
- `frontend/src/pages/Dashboard/DashboardPage.module.css` — `.widgetHidden`, `.widgetVisible` animation classes, `.spinner` keyframes
- `frontend/src/stores/uiStore.ts` — add `justBooted: boolean`, `dashboardAnimationPlayed: boolean`, and their setters
- `frontend/src/App.tsx` — call `setJustBooted(true)` in `handleBootComplete`

---

## BUILDER PROMPT

> **Session 7A — Boot Sequence & Dashboard Animations**
>
> You are building session 7A of the Finance App v2.0 update.
>
> **What you're doing:** Extending the boot sequence animation from ~2 seconds to ~4–5 seconds, adding a staggered dashboard widget entry animation after boot, and adding a spinner to the Refresh button.
>
> **Context:** The app has an eDEX-UI inspired boot sequence with 4 phases (black → terminal → shift → fadeout). Currently it has 5 boot lines with 70ms stagger. After boot, the dashboard renders all widgets instantly. You're making the boot more immersive and adding a reveal cascade for widgets.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`. (Note: `displayNames.ts` does not exist yet — it will be created in session 8A. For this session, this rule is informational only.)
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Extend Boot Duration and Add Boot Lines**
>
> In `frontend/src/components/BootSequence/BootSequence.tsx`:
> - Update timing constants: `PHASE_BLACK_DURATION` = 300, `PHASE_TERMINAL_DURATION` = 1500, `PHASE_SHIFT_DURATION` = 800, `PHASE_FADEOUT_DURATION` = 600
>
> In `frontend/src/components/BootSequence/BootPhase.tsx`:
> - Change default `staggerMs` from 70 to 110
> - Change checkmark stagger from 60 to 90
> - Expand `BOOT_LINES` to 9–10 lines. Keep the existing 5 and add: "Scanning universe", "Syncing portfolio", "Loading watchlists", "Connecting market feeds". Reorder logically (e.g., database → market data → model engine → scanning universe → syncing portfolio → loading watchlists → connecting market feeds → portfolio sync → UI components ready). Last line uses `└──` prefix.
> - Update version title from `VALUATION ENGINE v1.0` to `VALUATION ENGINE v2.0`
> - After all checkmarks are visible, show a new "All systems online" status line styled with `var(--accent-primary)` color. This appears before the shift phase begins.
> - Add a blinking cursor character (`▌` or `_`) that appears on the "Initializing core systems..." status line while boot lines are appearing. Hide it when "All systems online" shows. Use a CSS class with `@keyframes` blinking at 500ms intervals.
>
> In `frontend/src/components/BootSequence/BootSequence.module.css`:
> - Add `.cursor` class with blinking animation (`@keyframes cursorBlink { 0%, 100% { opacity: 1 } 50% { opacity: 0 } }`, `animation: cursorBlink 1s step-end infinite`)
> - Add `.completionLine` class: `color: var(--accent-primary); opacity: 0; transform: translateY(4px);`
> - Add `.completionLineVisible` class: `opacity: 1; transform: translateY(0); transition: opacity 200ms ease-out, transform 200ms ease-out;`
>
> **Task 2: Dashboard Widget Entry Animations**
>
> In `frontend/src/stores/uiStore.ts`:
> - Add `justBooted: boolean` (default: false) with setter `setJustBooted`
> - Add `dashboardAnimationPlayed: boolean` (default: false) with setter `setDashboardAnimationPlayed`
>
> In `frontend/src/App.tsx`:
> - In the `handleBootComplete` callback, add: `useUIStore.getState().setJustBooted(true)`
>
> In `frontend/src/pages/Dashboard/DashboardPage.tsx`:
> - Read `justBooted` and `dashboardAnimationPlayed` from uiStore
> - Add local state `animationPhase` (number, starts at -1)
> - On mount: if `justBooted && !dashboardAnimationPlayed && data` (data loaded), run a cascade:
>   - Set `animationPhase` from 0 to 4 with 175ms intervals using `setTimeout`
>   - After phase 4, call `setDashboardAnimationPlayed(true)` from uiStore
> - If `!justBooted` or `dashboardAnimationPlayed`, skip animation — set `animationPhase` to 4 immediately
> - Apply CSS classes to each grid cell:
>   - When `animationPhase < cellIndex`: add `styles.widgetHidden`
>   - When `animationPhase >= cellIndex`: add `styles.widgetVisible`
>   - Cell index mapping: gridMarket=0, gridPortfolio=1, gridWatchlist=2, gridModels=3, gridEvents=4
>
> In `frontend/src/pages/Dashboard/DashboardPage.module.css`:
> - Add `.widgetHidden { opacity: 0; transform: translateY(12px) scale(0.98); }`
> - Add `.widgetVisible { opacity: 1; transform: translateY(0) scale(1); transition: opacity 300ms ease-out, transform 300ms ease-out; }`
>
> **Task 3: Refresh Button Spinner**
>
> In `frontend/src/pages/Dashboard/DashboardPage.tsx`:
> - When `loading` is true, render a `<span className={styles.spinner} />` as the first child of the refresh button, before the text
>
> In `frontend/src/pages/Dashboard/DashboardPage.module.css`:
> - Add `.spinner`:
>   ```css
>   .spinner {
>     display: inline-block;
>     width: 11px;
>     height: 11px;
>     border: 2px solid var(--border-subtle);
>     border-top-color: var(--accent-primary);
>     border-radius: 50%;
>     animation: spin 0.7s linear infinite;
>   }
>   @keyframes spin { to { transform: rotate(360deg); } }
>   ```
>
> **Acceptance criteria:**
> 1. Boot sequence total duration ≈ 4–5 seconds (was ~2 seconds)
> 2. Boot terminal shows 9–10 lines with ~110ms stagger
> 3. Checkmarks appear with ~90ms stagger
> 4. "All systems online" completion line appears after all checkmarks, in accent color
> 5. Blinking cursor visible during boot line animation, hidden after completion
> 6. Title reads "VALUATION ENGINE v2.0"
> 7. Dashboard widgets cascade in after boot: fade-up + scale, ~175ms between each, 300ms transition
> 8. Animation order: Market → Portfolio → Watchlist → Models → Events
> 9. Animation only plays once on initial boot, not on tab switches
> 10. Refresh button shows a spinning circle icon alongside "Refreshing..." text while loading
> 11. No regressions: existing boot phases, backend readiness gating, dashboard grid layout, responsive breakpoints all preserved
>
> **Files to create:** None
>
> **Files to modify:**
> - `frontend/src/components/BootSequence/BootSequence.tsx`
> - `frontend/src/components/BootSequence/BootPhase.tsx`
> - `frontend/src/components/BootSequence/BootSequence.module.css`
> - `frontend/src/pages/Dashboard/DashboardPage.tsx`
> - `frontend/src/pages/Dashboard/DashboardPage.module.css`
> - `frontend/src/stores/uiStore.ts`
> - `frontend/src/App.tsx`
>
> **Technical constraints:**
> - Use CSS modules (`.module.css`), not inline styles, for all animations
> - Use CSS variables from the existing design system (e.g., `var(--accent-primary)`, `var(--bg-secondary)`)
> - All state management via Zustand `uiStore` (no Context or Redux)
> - Web Audio API not needed for this session (that's 7B)
> - Do not modify any backend files
