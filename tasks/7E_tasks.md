# Session 7E — Error Handling Polish
## Phase 7: Dashboard

**Priority:** Low
**Type:** Frontend Only
**Depends On:** None
**Spec Reference:** `specs/phase7_dashboard.md` → Area 3C

---

## SCOPE SUMMARY

Replace silent error swallowing (`catch { /* swallow */ }`) across dashboard widgets and the WatchlistPicker modal with proper inline error feedback. Users will see brief, auto-clearing error messages when operations fail, instead of nothing happening. Optionally create a lightweight inline error utility for reuse.

---

## TASKS

### Task 1: WatchlistWidget Error Handling
**Description:** Replace all `catch { /* swallow */ }` blocks in `WatchlistWidget.tsx` with inline error messages that auto-clear after 3 seconds.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.tsx`, add local state: `const [inlineError, setInlineError] = useState<string | null>(null)`
- [ ] 1.2 — Create helper function:
  ```typescript
  function showError(msg: string) {
    setInlineError(msg);
    setTimeout(() => setInlineError(null), 3000);
  }
  ```
- [ ] 1.3 — Replace the `catch { /* swallow */ }` in `handleAddTicker` with:
  ```typescript
  catch (err) {
    showError(err instanceof Error ? err.message : 'Failed to add ticker');
  }
  ```
- [ ] 1.4 — Replace the `catch { /* swallow */ }` in `handleRemoveItem` with:
  ```typescript
  catch (err) {
    showError('Failed to remove ticker');
  }
  ```
- [ ] 1.5 — Replace the `catch { /* swallow */ }` in `handleCreateWatchlist` with:
  ```typescript
  catch (err) {
    showError('Failed to create watchlist');
  }
  ```
- [ ] 1.6 — Replace the `catch { /* swallow */ }` in `handleDeleteWatchlist` with:
  ```typescript
  catch (err) {
    showError('Failed to delete watchlist');
  }
  ```
- [ ] 1.7 — Replace the `catch { setDetail(null); }` in `loadDetail` with:
  ```typescript
  catch (err) {
    setDetail(null);
    showError('Failed to load watchlist');
  }
  ```
- [ ] 1.8 — Render the inline error message in the widget body, below the table/content area:
  ```tsx
  {inlineError && <div className={s.inlineError}>{inlineError}</div>}
  ```
- [ ] 1.9 — In `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.module.css`, add `.inlineError` style:
  - `padding: 6px 12px`, `font-size: 11px`, `color: var(--color-negative)`, `background: var(--bg-tertiary)`, `border-radius: var(--radius-sm)`, `margin: 8px 12px`, `text-align: center`
  - Add a subtle fade-in animation: `animation: fadeIn 200ms ease-out`

**Implementation Notes:**
- There are exactly 5 `catch` blocks that swallow errors in the current WatchlistWidget:
  1. `handleAddTicker` — `catch { /* swallow */ }`
  2. `handleRemoveItem` — `catch { /* swallow */ }`
  3. `handleCreateWatchlist` — `catch { /* swallow */ }`
  4. `handleDeleteWatchlist` — `catch { /* swallow */ }`
  5. `loadDetail` — `catch { setDetail(null); }`
- Each needs a user-visible error message. The auto-clear timeout ensures messages don't persist.
- The `ApiClientError` from `api.ts` has a `.message` property that may contain useful detail from the backend.

---

### Task 2: WatchlistPicker Modal Error Handling
**Description:** Replace the silent error swallowing in `WatchlistPicker.tsx` with visible error feedback inside the modal.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.tsx`, the `useEffect` fetch already catches and sets empty: `.catch(() => setWatchlists([]))`. Upgrade this to also show an error message:
  ```typescript
  .catch(() => {
    setWatchlists([]);
    setMessage('Failed to load watchlists');
  });
  ```
- [ ] 2.2 — In `handleCreate`, replace `catch { // silently fail }` with:
  ```typescript
  catch (err) {
    setMessage('Failed to create watchlist');
  }
  ```
- [ ] 2.3 — In `handleAdd`, the failure case already sets a message (`"may already be in this watchlist"`). This is adequate but could be improved: if the `addToWatchlist` call throws (network error), catch it:
  ```typescript
  try {
    const ok = await navigationService.addToWatchlist(ticker, watchlistId);
    if (ok) {
      setMessage(`Added ${ticker} to watchlist`);
      setTimeout(onClose, 800);
    } else {
      setMessage(`${ticker} may already be in this watchlist`);
    }
  } catch {
    setMessage('Failed to add ticker');
  }
  ```
- [ ] 2.4 — Style error messages differently from success messages. In `WatchlistPicker.module.css`, add a `.messageError` class or use conditional styling:
  - Detect error messages (those starting with "Failed") and apply `color: var(--color-negative)` instead of the default message color.
  - Alternative: track `messageType: 'success' | 'error'` in state and apply CSS conditionally.

**Implementation Notes:**
- The existing `message` state already displays text at the bottom of the modal. Error messages will use the same slot but with different styling.
- The `setMessage` call with "Failed to load watchlists" should auto-clear after 3 seconds or persist until the modal closes.

---

### Task 3: Dashboard Widget Error Indicators (Optional Enhancement)
**Description:** For dashboard widgets that fetch data (Market, Portfolio, Watchlist, Models, Events), ensure that fetch failures show a small error indicator within the widget rather than blank content or misleading placeholders.

**Subtasks:**
- [ ] 3.1 — Review each dashboard widget for error handling:
  - `MarketOverviewWidget` — check if it handles loading/error states
  - `PortfolioSummaryWidget` — check if null portfolio data shows appropriate empty state
  - `RecentModelsWidget` — check if empty models array shows good empty state
  - The `UpcomingEventsWidget` was already addressed in 7D (skeleton + error state)
  - `WatchlistWidget` — addressed in Task 1 above
- [ ] 3.2 — For any widget that currently shows blank/misleading content on error, add a small error indicator:
  ```tsx
  <div className={styles.widgetError}>
    <span>Unable to load data</span>
    <button onClick={retry}>Retry</button>
  </div>
  ```
- [ ] 3.3 — Add `.widgetError` style in `DashboardPage.module.css`:
  - Centered text, small font, `color: var(--text-tertiary)`, with a subtle retry button

**Implementation Notes:**
- This task is investigative — the Builder should check each widget and only add error indicators where needed. Some widgets may already handle errors adequately.
- The DashboardPage itself has an `error` state with an error banner. Individual widget errors are different — they should be contained within the widget boundary, not replace the entire dashboard.
- This is lower priority than Tasks 1 and 2. If scope is tight, skip this task.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `WatchlistWidget` — "Add ticker" failure shows inline error "Failed to add ticker" that auto-clears after 3 seconds.
- [ ] AC-2: `WatchlistWidget` — "Remove ticker" failure shows inline error that auto-clears.
- [ ] AC-3: `WatchlistWidget` — "Create watchlist" failure shows inline error that auto-clears.
- [ ] AC-4: `WatchlistWidget` — "Delete watchlist" failure shows inline error that auto-clears.
- [ ] AC-5: `WatchlistWidget` — "Load detail" failure shows inline error (in addition to clearing detail).
- [ ] AC-6: `WatchlistWidget` — no `catch { /* swallow */ }` patterns remain.
- [ ] AC-7: `WatchlistPicker` — watchlist load failure shows "Failed to load watchlists" message in modal.
- [ ] AC-8: `WatchlistPicker` — watchlist create failure shows "Failed to create watchlist" message in modal.
- [ ] AC-9: `WatchlistPicker` — add-to-watchlist network failure shows error message.
- [ ] AC-10: `WatchlistPicker` — no `catch { // silently fail }` patterns remain.
- [ ] AC-11: Error messages are visually distinct from success messages (red/negative color).
- [ ] AC-12: Error messages auto-clear after ~3 seconds or on next successful action.
- [ ] AC-13: No functional regressions — successful operations (add, remove, create, delete) continue to work identically.
- [ ] AC-14: (Optional) Dashboard widgets show "Unable to load data" with retry button on fetch failure instead of blank content.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.tsx` — replace 5 silent catch blocks with inline error messages
- `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.module.css` — add `.inlineError` style
- `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.tsx` — replace 2 silent catch blocks with visible error messages
- `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.module.css` — add error message styling
- `frontend/src/pages/Dashboard/DashboardPage.module.css` — (optional) add `.widgetError` style

---

## BUILDER PROMPT

> **Session 7E — Error Handling Polish**
>
> You are building session 7E of the Finance App v2.0 update.
>
> **What you're doing:** Replacing silent error swallowing (`catch { /* swallow */ }`) in the WatchlistWidget and WatchlistPicker components with proper inline error messages that auto-clear after 3 seconds. This is a polish/UX quality pass.
>
> **Context:** Several dashboard components silently swallow errors — when operations fail, nothing happens and the user gets no feedback. You're adding visible but non-intrusive error messages.
>
> **Existing code:**
>
> `WatchlistWidget.tsx` has these silent catch blocks:
> 1. `handleAddTicker` — `catch { /* swallow */ }` — should show "Failed to add ticker"
> 2. `handleRemoveItem` — `catch { /* swallow */ }` — should show "Failed to remove ticker"
> 3. `handleCreateWatchlist` — `catch { /* swallow */ }` — should show "Failed to create watchlist"
> 4. `handleDeleteWatchlist` — `catch { /* swallow */ }` — should show "Failed to delete watchlist"
> 5. `loadDetail` — `catch { setDetail(null); }` — should also show "Failed to load watchlist"
>
> `WatchlistPicker.tsx` has these silent catch blocks:
> 1. `useEffect` fetch — `.catch(() => setWatchlists([]))` — should also show "Failed to load watchlists"
> 2. `handleCreate` — `catch { // silently fail }` — should show "Failed to create watchlist"
> 3. `handleAdd` — add try/catch around the whole function for network errors
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`. (Not directly relevant to this session, but included per standing directive.)
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: WatchlistWidget Error Handling**
>
> In `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.tsx`:
> - Add state: `const [inlineError, setInlineError] = useState<string | null>(null)`
> - Add helper:
>   ```typescript
>   function showError(msg: string) {
>     setInlineError(msg);
>     setTimeout(() => setInlineError(null), 3000);
>   }
>   ```
>   Note: if a new error comes in before the timeout clears the old one, the new message should replace it and reset the timer. Use a `useRef` for the timer ID to clear the previous timeout.
> - Replace all 5 catch blocks with calls to `showError(...)` with descriptive messages.
> - Render inline error at the bottom of the widget body:
>   ```tsx
>   {inlineError && <div className={s.inlineError}>{inlineError}</div>}
>   ```
> - On successful operations, clear any existing error: `setInlineError(null)`
>
> In `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.module.css`:
> ```css
> .inlineError {
>   padding: 6px 12px;
>   margin: 8px 12px;
>   font-size: 11px;
>   color: var(--color-negative);
>   background: rgba(239, 68, 68, 0.08);
>   border: 1px solid rgba(239, 68, 68, 0.15);
>   border-radius: var(--radius-sm);
>   text-align: center;
>   animation: errorFadeIn 200ms ease-out;
> }
>
> @keyframes errorFadeIn {
>   from { opacity: 0; transform: translateY(-4px); }
>   to { opacity: 1; transform: translateY(0); }
> }
> ```
>
> **Task 2: WatchlistPicker Error Handling**
>
> In `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.tsx`:
> - Add state: `const [messageType, setMessageType] = useState<'success' | 'error'>('success')`
> - Create helper:
>   ```typescript
>   function showMessage(msg: string, type: 'success' | 'error' = 'success') {
>     setMessage(msg);
>     setMessageType(type);
>     if (type === 'error') {
>       setTimeout(() => setMessage(''), 3000);
>     }
>   }
>   ```
> - Update the `useEffect` fetch catch:
>   ```typescript
>   .catch(() => {
>     setWatchlists([]);
>     showMessage('Failed to load watchlists', 'error');
>   });
>   ```
> - Update `handleCreate` catch:
>   ```typescript
>   catch (err) {
>     showMessage('Failed to create watchlist', 'error');
>   }
>   ```
> - Wrap `handleAdd` in try/catch for network errors:
>   ```typescript
>   try {
>     const ok = await navigationService.addToWatchlist(ticker, watchlistId);
>     if (ok) {
>       showMessage(`Added ${ticker} to watchlist`, 'success');
>       setTimeout(onClose, 800);
>     } else {
>       showMessage(`${ticker} may already be in this watchlist`, 'error');
>     }
>   } catch {
>     showMessage('Failed to add ticker', 'error');
>   }
>   ```
> - Apply conditional styling to the message:
>   ```tsx
>   {message && (
>     <div className={`${styles.message} ${messageType === 'error' ? styles.messageError : ''}`}>
>       {message}
>     </div>
>   )}
>   ```
>
> In `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.module.css`:
> ```css
> .messageError {
>   color: var(--color-negative) !important;
> }
> ```
>
> **Task 3 (Optional): Dashboard Widget Error Indicators**
>
> Review `MarketOverviewWidget`, `PortfolioSummaryWidget`, and `RecentModelsWidget` for error handling. If any show blank content on fetch failure, add a small centered "Unable to load data" message with a retry button. This is low priority — skip if the existing error handling is adequate.
>
> **Acceptance criteria:**
> 1. WatchlistWidget shows inline error messages (auto-clearing after 3s) for all 5 failure cases
> 2. No `/* swallow */` or `// silently fail` comments remain in either file
> 3. WatchlistPicker shows error messages for load, create, and add failures
> 4. Error messages are red/negative colored, success messages retain their current style
> 5. Error messages auto-clear after 3 seconds
> 6. Successful operations clear any existing error message
> 7. No functional regressions
>
> **Files to create:** None
>
> **Files to modify:**
> - `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.tsx`
> - `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.module.css`
> - `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.tsx`
> - `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.module.css`
> - `frontend/src/pages/Dashboard/DashboardPage.module.css` (optional)
>
> **Technical constraints:**
> - CSS modules for all styling
> - Use `setTimeout` for auto-clear with `useRef` for timer cleanup
> - Error messages must be non-blocking — they appear inline, not as modals or alerts
> - Use `var(--color-negative)` for error text color (exists in design system)
> - Keep error messages concise (under 40 characters)
> - Clear previous error timeout when a new error occurs (prevent stale timers)

---

*PM1 completed through session 7E. Phase 7 (Dashboard) is fully covered.*
*Next PM should start at Phase 8, session 8A, reading `specs/phase8_model_builder_overview.md`.*
