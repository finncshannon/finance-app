# Session 8M — Sliders + State Persistence + Assumptions Sync
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 8L (step precision updates), 8D (modelStore sync infrastructure: pendingSliderOverrides, pushSliderToAssumptions, pullAssumptionsToSliders, clearSliderOverrides, sensitivityParams)
**Spec Reference:** `specs/phase8_model_builder_sensitivity.md` → Areas 1A–1F, 5A, 5B

---

## SCOPE SUMMARY

Fix slider percent formatting to correctly parse Python format strings from the backend, add a current-assumption marker on each slider track, add a direct number input for precise value entry, persist slider state in modelStore across tab switches, implement full Push/Pull bidirectional sync between Sensitivity sliders and the Assumptions tab, and add custom slider CSS styling.

---

## TASKS

### Task 1: Percent Formatting Fix
**Description:** The current `formatParamValue` function checks for hardcoded type strings (`'percentage'`, `'pct'`, `'currency'`, etc.) that don't match the backend's actual Python format strings (`"{:.1%}"`, `"{:.2%}"`, `"{:.1f}x"`). After 8L updates, some params use `"{:.2%}"` (2 decimal places). Rewrite the formatter to parse Python format strings.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.tsx`, replace the current `formatParamValue` function:
  ```typescript
  function formatParamValue(value: number, format: string): string {
    // Parse Python-style: {:.1%}, {:.2%}, {:.1f}x, etc.
    const pctMatch = format.match(/\{:\.(\d+)%\}/);
    if (pctMatch) {
      const decimals = parseInt(pctMatch[1], 10);
      return `${(value * 100).toFixed(decimals)}%`;
    }
    const floatMatch = format.match(/\{:\.(\d+)f\}(.*)/);
    if (floatMatch) {
      const decimals = parseInt(floatMatch[1], 10);
      const suffix = floatMatch[2] || '';
      return `${value.toFixed(decimals)}${suffix}`;
    }
    // Legacy fallback
    if (format === 'percentage' || format === 'pct') return `${(value * 100).toFixed(1)}%`;
    if (format === 'currency' || format === 'dollar') return `$${value.toFixed(2)}`;
    if (format === 'multiple' || format === 'x') return `${value.toFixed(1)}x`;
    return value.toFixed(2);
  }
  ```
- [ ] 1.2 — Verify all displayed values use `formatParamValue`: slider value display (`.sliderValue`), min/max range labels (`.sliderRange span`). The result banner uses its own dollar/pct formatting which is correct.

---

### Task 2: Current Assumption Marker
**Description:** Add a thin white vertical line on each slider track at the `current_value` position (the model's original assumption before slider overrides). Shows how far the user has deviated from the model's default.

**Subtasks:**
- [ ] 2.1 — In `SlidersPanel.tsx`, inside each slider row's `.sliderTrack` div, render a positioned marker div:
  ```tsx
  <div className={styles.sliderTrack}>
    {p.current_value != null && (
      <div
        className={styles.currentMarker}
        style={{
          left: `${((p.current_value - p.min_val) / (p.max_val - p.min_val)) * 100}%`,
        }}
        title={`Current: ${formatParamValue(p.current_value, p.display_format)}`}
      />
    )}
    <input type="range" ... />
    <div className={styles.sliderRange}>...</div>
  </div>
  ```
- [ ] 2.2 — Ensure `.sliderTrack` has `position: relative` in CSS (currently it's a flex column — add `position: relative`).
- [ ] 2.3 — In `SlidersPanel.module.css`, add marker styles:
  ```css
  .currentMarker {
    position: absolute;
    top: 0;
    width: 2px;
    height: 20px;
    background: #FFFFFF;
    opacity: 0.7;
    pointer-events: none;
    z-index: 1;
  }
  .currentMarker::after {
    content: 'Current';
    position: absolute;
    top: -14px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 8px;
    color: var(--text-tertiary);
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.15s ease;
  }
  .sliderTrack:hover .currentMarker::after {
    opacity: 1;
  }
  ```

---

### Task 3: Direct Number Input
**Description:** Add a compact number input field next to each slider for typing precise values. The input displays in display units (e.g., `11.20` for a percentage) and converts to/from raw decimals internally. Replaces the existing read-only `.sliderValue` span.

**Subtasks:**
- [ ] 3.1 — In `SlidersPanel.tsx`, add helpers to extract format info:
  ```typescript
  function getFormatDecimals(format: string): number {
    const match = format.match(/\.(\d+)/);
    return match ? parseInt(match[1], 10) : 1;
  }
  function isPercentFormat(format: string): boolean {
    return format.includes('%');
  }
  ```
- [ ] 3.2 — Replace the `.sliderValue` span with a number input for each slider row:
  ```tsx
  const isPct = isPercentFormat(p.display_format);
  const decimals = getFormatDecimals(p.display_format);
  const displayVal = isPct ? value * 100 : value;
  const stepDisplay = isPct ? p.step * 100 : p.step;

  <input
    type="number"
    className={styles.numberInput}
    value={displayVal.toFixed(decimals)}
    step={stepDisplay}
    onChange={(e) => {
      const raw = parseFloat(e.target.value);
      if (isNaN(raw)) return;
      const decimal = isPct ? raw / 100 : raw;
      const clamped = Math.max(p.min_val, Math.min(p.max_val, decimal));
      handleSliderChange(p.key_path, clamped);
    }}
  />
  ```
- [ ] 3.3 — In `SlidersPanel.module.css`, add number input styles:
  ```css
  .numberInput {
    width: 76px;
    padding: 2px 6px;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    text-align: right;
    outline: none;
  }
  .numberInput:focus {
    border-color: var(--accent-primary);
  }
  ```

---

### Task 4: State Persistence in modelStore
**Description:** Move slider override state and result from local component state into `modelStore` so values persist when switching away from the Sensitivity tab and back. Session 8D adds `pendingSliderOverrides` and sync methods; 8M adds the slider-specific state.

**Subtasks:**
- [ ] 4.1 — In `frontend/src/stores/modelStore.ts`, add to the `ModelState` interface and defaults (check if 8D's additions are already present; add only what's missing):
  ```typescript
  // 8M additions
  sliderOverrides: Record<string, number>;
  sliderResult: SliderResult | null;
  setSliderOverride: (key: string, value: number) => void;
  setSliderOverrides: (overrides: Record<string, number>) => void;
  setSliderResult: (result: SliderResult | null) => void;
  ```
  Defaults: `sliderOverrides: {}, sliderResult: null`
  Actions:
  ```typescript
  setSliderOverride: (key, value) =>
    set((s) => ({ sliderOverrides: { ...s.sliderOverrides, [key]: value } })),
  setSliderOverrides: (overrides) => set({ sliderOverrides: overrides }),
  setSliderResult: (result) => set({ sliderResult: result }),
  ```
  Update `reset()` to include `sliderOverrides: {}, sliderResult: null`.
  Import `SliderResult` type from `'../types/models'`.

- [ ] 4.2 — In `SlidersPanel.tsx`, replace local state with store reads/writes:
  - **Remove:** `const [overrides, setOverrides] = useState<Record<string, number>>({})` and `const [result, setResult] = useState<SliderResult | null>(null)`
  - **Add:**
    ```tsx
    const sliderOverrides = useModelStore((s) => s.sliderOverrides);
    const sliderResult = useModelStore((s) => s.sliderResult);
    const setSliderOverrides = useModelStore((s) => s.setSliderOverrides);
    const setSliderOverride = useModelStore((s) => s.setSliderOverride);
    const setSliderResult = useModelStore((s) => s.setSliderResult);
    ```
  - Use `sliderOverrides` everywhere `overrides` was used, `sliderResult` for `result`.

- [ ] 4.3 — Update the parameter fetch `useEffect`: when params load, only seed store overrides if the store is empty for this ticker (don't overwrite existing slider state when switching back to the tab):
  ```tsx
  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);

    api.get<SensitivityParameterDef[]>(
      `/api/v1/model-builder/${ticker}/sensitivity/parameters`,
    ).then((data) => {
      setParams(data);
      // Only seed if store is empty (first load or ticker change)
      if (Object.keys(sliderOverrides).length === 0) {
        const initial: Record<string, number> = {};
        for (const p of data) {
          if (p.current_value != null) initial[p.key_path] = p.current_value;
        }
        setSliderOverrides(initial);
      }
      setLoading(false);
    }).catch(/* ... */);
  }, [ticker]);
  ```

- [ ] 4.4 — Update `handleSliderChange` to write to store:
  ```tsx
  const handleSliderChange = useCallback((keyPath: string, value: number) => {
    setSliderOverride(keyPath, value);
    fireSlider({ ...sliderOverrides, [keyPath]: value });
  }, [sliderOverrides, setSliderOverride, fireSlider]);
  ```

- [ ] 4.5 — Update `fireSlider` to write result to store:
  ```tsx
  .then((data) => {
    setSliderResult(data);
    setComputing(false);
  })
  ```

---

### Task 5: Push/Pull Sync Buttons
**Description:** Implement bidirectional sync between slider overrides and model assumptions. "Apply to Model" pushes slider values into assumptions. "Reset to Model" resets sliders back to current assumption values.

**Subtasks:**
- [ ] 5.1 — In `SlidersPanel.tsx`, read sync methods from modelStore (added by 8D):
  ```tsx
  const pushSliderToAssumptions = useModelStore((s) => s.pushSliderToAssumptions);
  const pullAssumptionsToSliders = useModelStore((s) => s.pullAssumptionsToSliders);
  const clearSliderOverrides = useModelStore((s) => s.clearSliderOverrides);
  ```
- [ ] 5.2 — Add a sync banner below the result banner when slider overrides differ from assumptions. Compute `hasDrift`:
  ```tsx
  const hasDrift = useMemo(() => {
    return params.some((p) => {
      const override = sliderOverrides[p.key_path];
      return override != null && p.current_value != null && Math.abs(override - p.current_value) > 1e-8;
    });
  }, [params, sliderOverrides]);
  ```
  Render:
  ```tsx
  {hasDrift && (
    <div className={styles.syncBanner}>
      <span>Sliders differ from model assumptions.</span>
      <button className={styles.applyBtn} onClick={() => pushSliderToAssumptions()}>
        Apply to Model
      </button>
      <button className={styles.resetBtn} onClick={() => {
        const current: Record<string, number> = {};
        params.forEach((p) => { if (p.current_value != null) current[p.key_path] = p.current_value; });
        setSliderOverrides(current);
        setSliderResult(null);
      }}>
        Reset to Model
      </button>
    </div>
  )}
  ```
- [ ] 5.3 — In `SlidersPanel.module.css`, add sync banner styles:
  ```css
  .syncBanner {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: rgba(59, 130, 246, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: 12px;
    color: var(--text-secondary);
  }
  .applyBtn {
    padding: 4px 12px;
    background: var(--accent-primary);
    color: var(--text-on-accent);
    border: none;
    border-radius: var(--radius-sm);
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }
  .resetBtn {
    padding: 4px 12px;
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-sm);
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
  }
  ```

---

### Task 6: Custom Slider Styling
**Description:** Upgrade the slider appearance with a larger thumb, border, and subtle shadow for better UX.

**Subtasks:**
- [ ] 6.1 — In `SlidersPanel.module.css`, update `.slider` pseudo-element selectors:
  ```css
  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--accent-primary);
    cursor: pointer;
    border: 2px solid var(--bg-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    transition: background var(--transition-micro), transform 0.1s ease;
  }
  .slider::-webkit-slider-thumb:hover {
    background: var(--accent-hover);
    transform: scale(1.1);
  }
  .slider::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--accent-primary);
    cursor: pointer;
    border: 2px solid var(--bg-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }
  ```
- [ ] 6.2 — Keep the track at 4px height, dark theme consistent (`var(--border-medium)` background).

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: All slider display values correctly parse Python format strings (`"{:.2%}"` → `11.20%`, `"{:.1f}x"` → `15.5x`).
- [ ] AC-2: Current assumption marker (white 2px line) visible on each slider track at the `current_value` position.
- [ ] AC-3: "Current" label appears above marker on hover.
- [ ] AC-4: Direct number input next to each slider, showing display units (percentages as `11.20`, multiples as `15.5`).
- [ ] AC-5: Number input syncs bidirectionally with slider position.
- [ ] AC-6: Number input clamps values between `min_val` and `max_val`.
- [ ] AC-7: Slider state (overrides + result) persists in modelStore across tab switches.
- [ ] AC-8: Switching to Assumptions tab and back does NOT reset slider positions.
- [ ] AC-9: "Apply to Model" button pushes slider overrides into assumptions in modelStore.
- [ ] AC-10: "Reset to Model" button resets sliders back to current assumption `current_value` values.
- [ ] AC-11: Sync banner appears only when slider overrides differ from model assumptions.
- [ ] AC-12: Slider thumb is 16px with border and shadow. Hover scales slightly.
- [ ] AC-13: Step precision matches 8L backend updates (0.1% for WACC, etc.).
- [ ] AC-14: No regressions on slider run/compute functionality.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.tsx` — rewrite formatParamValue, add current marker, number input, store integration (remove local state), sync buttons, hasDrift computation
- `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.module.css` — current marker, number input, sync banner, updated slider thumb, position:relative on sliderTrack
- `frontend/src/stores/modelStore.ts` — add `sliderOverrides`, `sliderResult`, setters, update `reset()`. Import `SliderResult` type.

---

## BUILDER PROMPT

> **Session 8M — Sliders + State Persistence + Assumptions Sync**
>
> You are building session 8M of the Finance App v2.0 update.
>
> **What you're doing:** Six things: (1) Fix slider formatting to parse Python format strings, (2) Add current-assumption markers on slider tracks, (3) Add direct number inputs, (4) Persist slider state in modelStore, (5) Implement Push/Pull sync with Assumptions tab, (6) Custom slider styling.
>
> **Context:** Session 8D added sync infrastructure to modelStore: `pendingSliderOverrides`, `pushSliderToAssumptions()`, `pullAssumptionsToSliders()`, `clearSliderOverrides()`, `sensitivityParams`, `setSensitivityParams()`. Session 8L updated backend step precision (WACC 0.1%, etc.) and display formats (`"{:.2%}"` for some params). The current `SlidersPanel.tsx` uses local state that resets on tab switch.
>
> **Existing code:**
>
> `SlidersPanel.tsx` (at `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.tsx`):
> - Reads `activeTicker` from `useModelStore`
> - **Local state (to be replaced with store):** `params` (SensitivityParameterDef[]), `overrides` (Record<string, number>), `result` (SliderResult | null), `loading`, `error`, `computing`
> - On mount: fetches param defs from `GET /api/v1/model-builder/${ticker}/sensitivity/parameters`, seeds `overrides` with `p.current_value` per param
> - On slider change: debounced (300ms) POST to `/api/v1/model-builder/${ticker}/sensitivity/slider` with `{ overrides: newOverrides }`
> - `formatParamValue(value, format)` — **BUG:** checks for `'percentage'`/`'pct'` strings but backend sends Python format strings like `"{:.1%}"`, `"{:.2%}"`, `"{:.1f}x"`. Must be rewritten to parse Python format patterns.
> - Renders: result banner (implied price, delta, compute time) → constraints → slider list
> - Each slider row (`.sliderRow`): grid layout `160px 1fr 80px` → label, `.sliderTrack` (flex column: `<input type="range">` + `.sliderRange` min/max), `.sliderValue` span
> - Currently no current-assumption marker on tracks
> - No direct number input — only slider drag + read-only value display
>
> `SlidersPanel.module.css`:
> - `.container` — flex column gap-4
> - `.resultBanner` — flex row, bg-tertiary, border-subtle, radius-lg
> - `.slidersList` — flex column gap-2
> - `.sliderRow` — grid `160px 1fr 80px`, bg-secondary, border-subtle, radius-md
> - `.sliderTrack` — flex column gap-2px (does NOT have `position: relative` — **add it** for marker positioning)
> - `.slider` — webkit/moz styled, 4px track, 14px thumb, accent-primary
> - `.sliderRange` — flex space-between, 10px mono tertiary
> - `.sliderValue` — 13px mono 600, right-aligned
>
> `modelStore.ts` (at `frontend/src/stores/modelStore.ts`):
> - Current state: `activeTicker`, `activeModelType`, `activeModelId`, `detectionResult`, `assumptions`, `output`, `versions`, `loading`, `isCalculating`
> - **After 8D adds:** `pendingSliderOverrides: Record<string, number>`, `sensitivityParams: Record<string, unknown> | null`, `setPendingSliderOverride()`, `pushSliderToAssumptions()`, `pullAssumptionsToSliders()`, `clearSliderOverrides()`, `setSensitivityParams()`
> - **8M must add:** `sliderOverrides: Record<string, number>`, `sliderResult: SliderResult | null`, `setSliderOverride()`, `setSliderOverrides()`, `setSliderResult()`
> - Uses Zustand (`create` from 'zustand')
>
> `SensitivityParameterDef` type (from `frontend/src/types/models.ts`):
> ```typescript
> interface SensitivityParameterDef {
>   name: string; key_path: string; param_type: string;
>   min_val: number; max_val: number; step: number;
>   display_format: string; current_value: number | null;
> }
> ```
> `display_format` values: `"{:.2%}"` (WACC, CapEx, NWC, Terminal Growth), `"{:.1%}"` (Rev Growth, Op Margin, Tax), `"{:.1f}x"` (Exit Multiple)
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for any backend keys shown in UI.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%). Sliders operate on raw decimals internally, display values in percent.
> - Scenario Order: Bear / Base / Bull, Base default.
>
> **Task 1: Fix formatParamValue** — Parse Python format strings with regex: `{:.N%}` → multiply by 100, N decimals; `{:.Nf}suffix` → N decimals + suffix. Keep legacy fallback.
>
> **Task 2: Current Assumption Marker** — For each slider, render a `<div className={styles.currentMarker}>` inside `.sliderTrack` at `left: ((current_value - min) / (max - min)) * 100%`. Position absolute, 2px white line, pointer-events none. "Current" label appears on hover via CSS.
>
> **Task 3: Direct Number Input** — Replace `.sliderValue` span with `<input type="number">`. Display in user units (pct shows `11.20`, multiple shows `15.5`). On change, convert back to decimal (divide by 100 for pct). Clamp between min/max. Step in display units.
>
> **Task 4: Store Integration** — Add `sliderOverrides`, `sliderResult`, setters to modelStore. Remove local `overrides`/`result` state from SlidersPanel. Read from / write to store. On param fetch, only seed store if empty (preserve state across tab switches).
>
> **Task 5: Push/Pull Sync** — Compute `hasDrift` (any slider differs from `current_value` by > 1e-8). Show sync banner when drift exists. "Apply to Model" calls `pushSliderToAssumptions()`. "Reset to Model" resets `sliderOverrides` to `current_value` map and clears result.
>
> **Task 6: Slider Styling** — Thumb: 16px with 2px border and shadow. Hover: accent-hover + scale(1.1).
>
> **Acceptance criteria:**
> 1. formatParamValue correctly parses `"{:.2%}"` → `11.20%`, `"{:.1f}x"` → `15.5x`
> 2. Current marker visible on each track
> 3. Number input syncs with slider, clamps values
> 4. State persists in store across tab switches
> 5. Apply pushes overrides to assumptions
> 6. Reset returns sliders to current values
> 7. Sync banner shows only on drift
> 8. Slider thumb upgraded (16px, shadow, hover scale)
> 9. No regressions
>
> **Files to create:** None
>
> **Files to modify:**
> - `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.tsx`
> - `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.module.css`
> - `frontend/src/stores/modelStore.ts`
>
> **Technical constraints:**
> - Zustand for state management (`create` from 'zustand')
> - CSS modules for all styling
> - `api.get<T>` / `api.post<T>` for data fetching
> - Debounce: 300ms on slider change (existing pattern, keep it)
> - Import `SliderResult` from `'../../../types/models'` in modelStore
> - The sync methods (`pushSliderToAssumptions`, `pullAssumptionsToSliders`, `clearSliderOverrides`) are added by session 8D — check if present, add stubs if not
> - `.sliderTrack` needs `position: relative` added for marker positioning
> - Number input uses display units (pct × 100) externally, raw decimals internally
