# Finance App — Model Builder: Assumptions Sub-Tab Update Plan
## Phase 8: Model Builder — Assumptions (General Fixes)

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Assumptions sub-tab general fixes — terminal value clipping, scenario reorder, confidence warnings, slider↔assumptions sync prep

---

## PLAN SUMMARY

Four items:

1. **Terminal Value Section Clipping Fix** — CSS bug causing content cutoff
2. **Scenario Pill Reorder** — Bear / Base / Bull (left to right), Base default
3. **Confidence Threshold Warning** — Flag assumptions below 80 with prominent visual warning
4. **Slider ↔ Assumptions Sync Prep** — Cross-tab state infrastructure for bidirectional push/pull between Sensitivity sliders and Assumptions (full UI in Sensitivity plan)

---

## AREA 1: TERMINAL VALUE SECTION CLIPPING

### Problem
The Terminal Value section card is cutting off content. Likely caused by an overflow constraint on `.section`, `.sectionBody`, or the parent `.body` container.

### Fix
- Audit `AssumptionsTab.module.css` — the `.body` has `overflow: auto` which is correct, but individual `.section` cards may have an implicit height constraint
- Ensure `.sectionBody` has no `max-height` or `overflow: hidden`
- Ensure the Terminal Value section renders both fields (Terminal Growth Rate + Terminal Exit Multiple) without clipping
- Test with varying numbers of fields (DDM section can have up to 5 cards)

**Files touched:**
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.module.css` — fix overflow/height on section cards
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionCard.module.css` — verify row height isn't constraining

---

## AREA 2: SCENARIO PILL REORDER

### Current
`Base / Bull / Bear` — left to right. Base is first and default.

### New
`Bear / Base / Bull` — left to right. Base stays default (center position). Conceptual flow: pessimistic → neutral → optimistic.

**Change:**
```typescript
// Current
const SCENARIOS = [
  { id: 'base', label: 'Base' },
  { id: 'bull', label: 'Bull' },
  { id: 'bear', label: 'Bear' },
];

// New
const SCENARIOS = [
  { id: 'bear', label: 'Bear' },
  { id: 'base', label: 'Base' },
  { id: 'bull', label: 'Bull' },
];
```

Default state stays `useState<ScenarioKey>('base')`.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx` — reorder SCENARIOS array

---

## AREA 3: CONFIDENCE THRESHOLD WARNING

### Current Behavior
The engine generates assumptions with confidence scores typically landing at 65–75. The overall confidence badge shows this score with color coding (green ≥80, yellow ≥60, orange ≥40, red <40). Scores of 65–75 show as yellow — technically passing but not great. No specific warning or call to action.

### New Behavior
- Any section with confidence below 80 gets a visible warning indicator on its section header
- The section header shows a small warning icon + "Review recommended" text next to the confidence badge when score < 80
- The overall confidence badge in the header gets a tooltip explaining: "Scores below 80 may indicate limited data or high uncertainty. Review and adjust assumptions manually."
- Sections below 80 default to expanded; sections at or above 80 can be collapsed

**Note:** The actual confidence scoring logic in the backend stays the same for now. The Monte Carlo assumption generation upgrade (separate plan) will naturally produce higher-confidence outputs. This change is UI-only to make low confidence more visible and actionable.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx` — add warning indicator logic to Section component, collapsible sections
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.module.css` — warning icon styles, collapsible animation

---

## AREA 4: SLIDER ↔ ASSUMPTIONS SYNC PREP

### Concept
Bidirectional sync between Sensitivity sliders and Assumptions tab. User explores on sliders, commits back to assumptions. Or loads current assumptions into sliders as starting point.

### What's Needed in This Session (Prep Only)
The full UI (buttons, sync flow) will be built in the Sensitivity sub-tab plan. This session prepares the shared state infrastructure.

**Changes:**
- Add to `modelStore.ts`:
  - `pendingSliderOverrides: Record<string, number>` — slider values that haven't been pushed to assumptions yet
  - `pushSliderToAssumptions()` — copies pendingSliderOverrides into the assumptions override map
  - `pullAssumptionsToSliders()` — copies current assumption values into slider starting positions
  - `clearSliderOverrides()` — resets pending slider state
- The Assumptions tab should read from `pendingSliderOverrides` and show a banner when uncommitted slider changes exist: "You have {N} uncommitted changes from Sensitivity sliders. [Apply] [Dismiss]"

**Cross-tab dependency:** Sensitivity sub-tab plan will add the "Push to Assumptions" button and the actual slider state management. This session just adds the store methods and the receiving banner on the Assumptions side.

**Additional fix:** Sensitivity data currently doesn't persist when switching tabs. Add state persistence to `modelStore` for sensitivity parameters so they survive tab navigation.

**Files touched:**
- `frontend/src/stores/modelStore.ts` — add slider sync state and methods, persist sensitivity state
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx` — add banner for pending slider overrides

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8D — Assumptions General Fixes (Frontend Only)
**Scope:** All four areas
**Files:**
- `AssumptionsTab.tsx` — scenario reorder, confidence warnings, collapsible sections, slider sync banner
- `AssumptionsTab.module.css` — clipping fix, warning styles, collapse animation
- `AssumptionCard.module.css` — height verification
- `modelStore.ts` — slider sync state, sensitivity persistence
**Complexity:** Medium (mostly CSS fixes and state management, no new components)
**Estimated acceptance criteria:** 15–18

---

## DECISIONS MADE

1. Scenario order: Bear / Base / Bull (left to right), Base remains default
2. Confidence threshold: 80 is the "good" bar — below 80 gets visual warnings but no blocking
3. Backend confidence scoring unchanged in this session (Monte Carlo upgrade is separate)
4. Slider sync is prep-only here — full UI built in Sensitivity plan
5. Sensitivity state persistence fix included in this session
6. Terminal value fix is CSS-only, no structural changes

---

*End of Model Builder — Assumptions General Fixes Plan*
*Phase 8D · Prepared March 5, 2026*
