# Session 8O — History Fix (Auto-Save on Run, Save Macro, Snapshot Formatting)
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Mixed (Backend + Frontend)
**Depends On:** None (but logically runs after model views are stabilized: 8I, 8J, 8K)
**Spec Reference:** `specs/phase8_model_builder_history.md` → Areas 1, 2, 3

---

## SCOPE SUMMARY

Fix the History tab by auto-creating a model record in the DB whenever a model is run (so `activeModelId` is never null after a run, and History/Export work immediately). Add a "Save" macro button in the Model Builder page header for one-click version saving from any sub-tab. Polish the History tab: replace raw JSON snapshot viewer with formatted key outputs panel, make "Load" actually restore assumptions and re-run, add a disabled "Compare" stub button.

---

## TASKS

### Task 1: Auto-Create Model Record on Run (Backend)
**Description:** Add a `get_or_create_model()` method to `ModelRepo` and call it from each `/run/{engine}` endpoint so that running a model always persists a record and returns `model_id` in the response.

**Subtasks:**
- [ ] 1.1 — In `backend/repositories/model_repo.py`, add `get_or_create_model()`:
  ```python
  async def get_or_create_model(self, ticker: str, model_type: str) -> dict:
      """Get existing model for ticker+type, or create one."""
      existing = await self.get_model_by_ticker_type(ticker, model_type)
      if existing:
          return existing
      return await self.create_model({
          "ticker": ticker.upper(),
          "model_type": model_type,
      })
  ```
  Note: The `create_model` method expects optional detection fields (`auto_detection_score`, `auto_detection_confidence`, etc.) but they default to None. For auto-created records, just pass `ticker` and `model_type`.

- [ ] 1.2 — In `backend/routers/models_router.py`, update `run_dcf` to auto-persist and include `model_id`:
  ```python
  @router.post("/{ticker}/run/dcf")
  async def run_dcf(ticker: str, body: RunRequest, request: Request):
      try:
          engine = request.app.state.assumption_engine
          assumptions = await engine.generate_assumptions(
              ticker, model_type="dcf", overrides=body.overrides,
          )
          data, price = await _gather_engine_data(ticker, request)
          result = DCFEngine.run(assumptions, data, price)

          # Auto-persist model record
          model_repo: ModelRepo = request.app.state.model_repo
          model = await model_repo.get_or_create_model(ticker, "dcf")

          result_dict = result.model_dump(mode="json")
          result_dict["model_id"] = model["id"]
          return success_response(data=result_dict)
      except Exception as exc:
          logger.exception("DCF run failed for %s", ticker)
          return error_response("ENGINE_ERROR", str(exc))
  ```

- [ ] 1.3 — Apply the same pattern to `run_ddm`:
  ```python
  model = await model_repo.get_or_create_model(ticker, "ddm")
  result_dict = result.model_dump(mode="json")
  result_dict["model_id"] = model["id"]
  return success_response(data=result_dict)
  ```

- [ ] 1.4 — Apply to `run_comps`:
  ```python
  model = await model_repo.get_or_create_model(ticker, "comps")
  result_dict = result.model_dump(mode="json")
  result_dict["model_id"] = model["id"]
  return success_response(data=result_dict)
  ```

- [ ] 1.5 — Apply to `run_revbased`:
  ```python
  model = await model_repo.get_or_create_model(ticker, "revenue_based")
  result_dict = result.model_dump(mode="json")
  result_dict["model_id"] = model["id"]
  return success_response(data=result_dict)
  ```

- [ ] 1.6 — Apply to `run_all_models` — persist a record for each engine that ran:
  ```python
  for model_type_key, engine_result_dict in results.items():
      model = await model_repo.get_or_create_model(ticker, model_type_key)
      engine_result_dict["model_id"] = model["id"]
  ```

**Implementation Notes:**
- `model_repo` is on `request.app.state.model_repo` (already available in the router).
- The `get_or_create_model` pattern ensures idempotency: running DCF for AAPL twice uses the same model record, doesn't create duplicates.
- `get_model_by_ticker_type(ticker, model_type)` already exists in `ModelRepo` — it returns `dict | None`.
- The current `run_dcf` pattern ends with `return success_response(data=result.model_dump(mode="json"))`. Change to: dump to dict first, add `model_id`, then return.

---

### Task 2: Frontend — Set activeModelId from Run Response
**Description:** After a successful model run, extract `model_id` from the response and set it in modelStore so History and Export work immediately.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx`, update the `runModel` function to extract `model_id`:
  ```typescript
  const runModel = useCallback(
    async (ticker: string, type: ModelType) => {
      setLoading(true);
      setError(null);
      setResult(null);

      const endpoint = MODEL_ENDPOINTS[type];
      try {
        const data = await api.post<ModelResult & { model_id?: number }>(
          `/api/v1/model-builder/${ticker}/run/${endpoint}`,
          {},
        );
        setResult(data);
        // Set activeModelId from response
        if (data.model_id) {
          useModelStore.getState().setActiveModelId(data.model_id);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to run model';
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [],
  );
  ```
- [ ] 2.2 — The extra `model_id` field is harmless to view components — they ignore unknown fields. No type changes needed beyond the intersection type `& { model_id?: number }` in the API call.

---

### Task 3: Save Macro Button in Page Header
**Description:** Add a "Save" button in the `ModelBuilderPage.tsx` header bar (next to the Export dropdown) for one-click version saving from any sub-tab.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/ModelBuilderPage.tsx`, add Save button state and handler:
  ```tsx
  const activeModelId = useModelStore((s) => s.activeModelId);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveAnnotation, setSaveAnnotation] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = useCallback(async () => {
    if (!activeModelId) return;
    setSaving(true);
    try {
      await api.post(`/api/v1/model-builder/model/${activeModelId}/save-version`, {
        annotation: saveAnnotation.trim() || null,
      });
      setShowSaveDialog(false);
      setSaveAnnotation('');
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch {
      // Could show error but keep simple
    } finally {
      setSaving(false);
    }
  }, [activeModelId, saveAnnotation]);
  ```

- [ ] 3.2 — Render the Save button in the header area, next to the ExportDropdown:
  ```tsx
  <button
    className={styles.saveBtn}
    onClick={() => setShowSaveDialog(true)}
    disabled={!activeModelId}
    title={!activeModelId ? 'Run a model first to enable saving' : 'Save current model to version history'}
  >
    💾 Save
  </button>
  {saveSuccess && <span className={styles.saveFlash}>Version saved</span>}
  ```

- [ ] 3.3 — Render the inline annotation dialog when `showSaveDialog` is true:
  ```tsx
  {showSaveDialog && (
    <div className={styles.saveDialog}>
      <input
        className={styles.saveInput}
        type="text"
        placeholder="Add annotation (optional)..."
        value={saveAnnotation}
        onChange={(e) => setSaveAnnotation(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') void handleSave();
          if (e.key === 'Escape') { setShowSaveDialog(false); setSaveAnnotation(''); }
        }}
        autoFocus
      />
      <button className={styles.saveConfirmBtn} onClick={() => void handleSave()} disabled={saving}>
        {saving ? 'Saving...' : 'Save'}
      </button>
      <button className={styles.saveCancelBtn} onClick={() => { setShowSaveDialog(false); setSaveAnnotation(''); }}>
        Cancel
      </button>
    </div>
  )}
  ```

- [ ] 3.4 — In `frontend/src/pages/ModelBuilder/ModelBuilder.module.css`, add Save button and dialog styles:
  ```css
  .saveBtn {
    padding: 5px 12px;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .saveBtn:hover:not(:disabled) {
    background: var(--bg-quaternary);
    color: var(--text-primary);
    border-color: var(--border-medium);
  }
  .saveBtn:disabled { opacity: 0.4; cursor: not-allowed; }
  .saveFlash {
    font-size: 11px;
    color: var(--color-positive);
    animation: fadeOut 2s forwards;
  }
  @keyframes fadeOut { 0% { opacity: 1; } 70% { opacity: 1; } 100% { opacity: 0; } }
  .saveDialog {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-md);
  }
  .saveInput {
    width: 200px;
    padding: 4px 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 12px;
  }
  .saveConfirmBtn {
    padding: 4px 12px;
    background: var(--accent-primary);
    color: var(--text-on-accent);
    border: none;
    border-radius: var(--radius-sm);
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }
  .saveCancelBtn {
    padding: 4px 12px;
    background: transparent;
    color: var(--text-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    font-size: 11px;
    cursor: pointer;
  }
  ```

---

### Task 4: History Tab Polish
**Description:** Replace the raw JSON snapshot viewer with a formatted key outputs panel, make "Load" actually restore assumptions, add a disabled "Compare" stub.

**Subtasks:**
- [ ] 4.1 — In `frontend/src/pages/ModelBuilder/History/HistoryTab.tsx`, replace the snapshot modal's raw JSON viewer. The current code renders:
  ```tsx
  <pre className={styles.snapshotJson}>
    {viewingVersion.snapshot
      ? JSON.stringify(viewingVersion.snapshot, null, 2)
      : viewingVersion.snapshot_blob
        ? viewingVersion.snapshot_blob
        : 'No snapshot data available.'}
  </pre>
  ```
  Replace with a formatted panel that extracts key values from the snapshot:
  ```tsx
  const snapshot = viewingVersion.snapshot;
  const output = snapshot?.output;
  const modelInfo = snapshot?.model;

  <div className={styles.snapshotFormatted}>
    <div className={styles.snapshotSection}>
      <span className={styles.snapshotSectionTitle}>Model</span>
      <div className={styles.snapshotRow}>
        <span>Type:</span><span>{modelInfo?.model_type ?? '—'}</span>
      </div>
      <div className={styles.snapshotRow}>
        <span>Ticker:</span><span>{modelInfo?.ticker ?? '—'}</span>
      </div>
    </div>
    {output && (
      <div className={styles.snapshotSection}>
        <span className={styles.snapshotSectionTitle}>Key Outputs</span>
        <div className={styles.snapshotRow}>
          <span>Implied Price:</span>
          <span>${(output.intrinsic_value_per_share ?? 0).toFixed(2)}</span>
        </div>
        <div className={styles.snapshotRow}>
          <span>Enterprise Value:</span>
          <span>${((output.enterprise_value ?? 0) / 1e9).toFixed(2)}B</span>
        </div>
      </div>
    )}
    <details className={styles.rawDetails}>
      <summary>Raw JSON</summary>
      <pre className={styles.snapshotJson}>
        {JSON.stringify(snapshot, null, 2)}
      </pre>
    </details>
  </div>
  ```

- [ ] 4.2 — Make the "Load" button actually restore the version's assumptions. Currently `handleLoad` just opens the viewer (same as View). Update it:
  ```tsx
  const handleLoad = useCallback(async (version: ModelVersion) => {
    if (!modelId) return;
    try {
      const full = await api.get<ModelVersion>(
        `/api/v1/model-builder/model/${modelId}/version/${version.id}`,
      );
      // Restore assumptions to modelStore
      if (full.snapshot?.assumptions) {
        useModelStore.getState().setAssumptions(full.snapshot.assumptions);
      }
      setViewingVersion(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load version';
      setError(message);
    }
  }, [modelId]);
  ```

- [ ] 4.3 — Add a disabled "Compare" button stub in the header next to "Save Current":
  ```tsx
  <button className={styles.compareBtn} disabled title="Compare versions — coming soon">
    Compare
  </button>
  ```

- [ ] 4.4 — In `HistoryTab.module.css`, add formatted snapshot styles:
  ```css
  .snapshotFormatted {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-3);
  }
  .snapshotSection {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .snapshotSectionTitle {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: var(--text-tertiary);
    margin-bottom: var(--space-1);
  }
  .snapshotRow {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    padding: 2px 0;
  }
  .snapshotRow span:first-child { color: var(--text-secondary); }
  .snapshotRow span:last-child {
    font-family: var(--font-mono);
    font-weight: 600;
    color: var(--text-primary);
  }
  .rawDetails { margin-top: var(--space-2); }
  .rawDetails summary {
    font-size: 11px;
    color: var(--text-tertiary);
    cursor: pointer;
  }
  .compareBtn {
    padding: 5px 12px;
    background: transparent;
    color: var(--text-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    font-size: 12px;
    cursor: not-allowed;
    opacity: 0.5;
  }
  ```

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Running any model (DCF, DDM, Comps, RevBased) auto-creates/updates a model record in the DB.
- [ ] AC-2: `model_id` included in run response for all 4 engines.
- [ ] AC-3: `activeModelId` set in modelStore after every successful model run.
- [ ] AC-4: History tab works immediately after running a model (no longer shows "No model found").
- [ ] AC-5: Export button (from 8I) works after a run because `activeModelId` is now set.
- [ ] AC-6: Model record is idempotent — running DCF for AAPL twice updates same record, doesn't create duplicates.
- [ ] AC-7: Save button visible in Model Builder header, disabled when no model run yet.
- [ ] AC-8: Save button opens inline annotation input + Save/Cancel.
- [ ] AC-9: Success flash "Version saved" shown for 2 seconds after save.
- [ ] AC-10: Snapshot viewer shows formatted key outputs (model type, ticker, implied price, EV) instead of raw JSON.
- [ ] AC-11: Raw JSON still available in collapsible `<details>` section.
- [ ] AC-12: Load button restores version's assumptions into modelStore.
- [ ] AC-13: Compare button present as disabled stub with tooltip "Compare versions — coming soon".
- [ ] AC-14: `run_all_models` also persists model records for each engine.
- [ ] AC-15: No regressions on existing model run or history functionality.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `backend/repositories/model_repo.py` — add `get_or_create_model(ticker, model_type)` method
- `backend/routers/models_router.py` — add auto-persist in `run_dcf`, `run_ddm`, `run_comps`, `run_revbased`, `run_all_models`; include `model_id` in response
- `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx` — extract `model_id` from run response, call `setActiveModelId`
- `frontend/src/pages/ModelBuilderPage.tsx` — Save button + inline annotation dialog + success flash
- `frontend/src/pages/ModelBuilder/ModelBuilder.module.css` — save button, dialog, flash animation styles
- `frontend/src/pages/ModelBuilder/History/HistoryTab.tsx` — formatted snapshot panel, functional Load, Compare stub
- `frontend/src/pages/ModelBuilder/History/HistoryTab.module.css` — snapshot formatted styles, compare button

---

## BUILDER PROMPT

> **Session 8O — History Fix (Auto-Save on Run, Save Macro, Snapshot Formatting)**
>
> You are building session 8O of the Finance App v2.0 update.
>
> **What you're doing:** Three things: (1) Backend: auto-create model record on every model run so `activeModelId` is always set, (2) Frontend: add a Save button in the Model Builder header for one-click version saving, (3) Polish the History tab with formatted snapshot viewer and functional Load button.
>
> **Context:** Currently running a model doesn't persist anything to the DB — `activeModelId` stays null, so History shows "No model found" and Export is disabled. You're fixing the full chain: run → persist → set ID → History works → Export works → Save works.
>
> **Existing code:**
>
> `model_repo.py` (at `backend/repositories/model_repo.py`):
> - `ModelRepo` class with CRUD methods: `get_model(id)`, `get_models_for_ticker(ticker)`, `get_model_by_ticker_type(ticker, model_type)`, `create_model(data)`, `update_model(model_id, data)`, `delete_model(model_id)`
> - Also has: `get_assumptions()`, `upsert_assumptions()`, `get_output()`, `get_outputs_for_model()`, `create_output()`, `get_version()`, `get_versions_for_model()`, `create_version()`
> - `create_model(data)` expects: `ticker`, `model_type`, plus optional detection fields (`auto_detection_score`, `auto_detection_confidence`, etc.)
> - **Missing:** `get_or_create_model(ticker, model_type)` — check if exists via `get_model_by_ticker_type`, create if not
>
> `models_router.py` (at `backend/routers/models_router.py`):
> - `run_dcf` current pattern:
>   ```python
>   engine = request.app.state.assumption_engine
>   assumptions = await engine.generate_assumptions(ticker, model_type="dcf", overrides=body.overrides)
>   data, price = await _gather_engine_data(ticker, request)
>   result = DCFEngine.run(assumptions, data, price)
>   return success_response(data=result.model_dump(mode="json"))
>   ```
> - Same pattern for `run_ddm`, `run_comps` (with peer data), `run_revbased`. None currently persist to DB or return `model_id`.
> - `model_repo` accessed via `request.app.state.model_repo`
> - `run_all_models` iterates all 4 engines, returns combined results dict under `results` key
> - Existing error handling: `try/except Exception` → `error_response("ENGINE_ERROR", str(exc))`
>
> `ModelTab.tsx` (at `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx`):
> - `runModel(ticker, type)` async function: calls `api.post<ModelResult>('/run/{endpoint}', {})` → `setResult(data)`
> - Does NOT call `setActiveModelId`. Response currently has no `model_id`.
> - Uses `useModelStore` for `activeTicker` only
> - `MODEL_ENDPOINTS` maps `dcf→'dcf'`, `ddm→'ddm'`, `comps→'comps'`, `revenue_based→'revbased'`
>
> `ModelBuilderPage.tsx` (at `frontend/src/pages/ModelBuilderPage.tsx`):
> - Header area has: search input, dropdown, model type pills
> - ExportDropdown conditional: `{activeTicker && useModelStore.getState().activeModelId && (<ExportDropdown ... />)}`
> - **No Save button currently**
>
> `HistoryTab.tsx` (at `frontend/src/pages/ModelBuilder/History/HistoryTab.tsx`):
> - Resolves `modelId` from `activeModelId` in store or falls back to API lookup (`GET /{ticker}/models`)
> - If no model: shows "No model found for {ticker}. Run a valuation first."
> - Version list: table with version_number, date, annotation, size, Load/View buttons
> - Save dialog: inline input for annotation + Save/Cancel, POSTs to `/model/{modelId}/save-version`
> - Snapshot viewer: modal overlay with `<pre>JSON.stringify(snapshot, null, 2)</pre>` — **raw JSON dump**
> - `handleLoad`: fetches version and opens viewer (same as View) — does NOT restore assumptions
> - `handleView`: fetches full version with snapshot and opens modal
>
> `modelStore.ts`:
> - Has `activeModelId: number | null` and `setActiveModelId(id)` — already exists
> - Has `setAssumptions(assumptions)` — available for Load restoration
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for any backend keys shown in UI.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull, Base default.
>
> **Task 1: Backend — get_or_create_model + Auto-Persist**
>
> In `model_repo.py`, add `get_or_create_model(ticker, model_type)`: check `get_model_by_ticker_type`, return existing if found, `create_model` if not.
>
> In `models_router.py`, update all 5 run endpoints: after computing result, call `model_repo.get_or_create_model()`, dump result to dict, add `model_id`, return. Pattern:
> ```python
> model_repo: ModelRepo = request.app.state.model_repo
> model = await model_repo.get_or_create_model(ticker, "dcf")
> result_dict = result.model_dump(mode="json")
> result_dict["model_id"] = model["id"]
> return success_response(data=result_dict)
> ```
>
> **Task 2: Frontend — Set activeModelId**
>
> In `ModelTab.tsx`, after successful run:
> ```typescript
> if (data.model_id) {
>   useModelStore.getState().setActiveModelId(data.model_id);
> }
> ```
> Use intersection type `ModelResult & { model_id?: number }`.
>
> **Task 3: Save Macro Button**
>
> In `ModelBuilderPage.tsx`, add Save button next to ExportDropdown:
> - Disabled when `activeModelId` is null (tooltip: "Run a model first")
> - Click opens inline dialog: text input + Save/Cancel
> - Save POSTs to `/api/v1/model-builder/model/${activeModelId}/save-version`
> - Success flash: "Version saved" for 2s with fadeOut animation
>
> **Task 4: History Tab Polish**
>
> - Replace raw JSON `<pre>` with formatted panel: Model (type, ticker), Key Outputs (implied price, EV), raw JSON in `<details>`
> - Load restores `snapshot.assumptions` to modelStore via `setAssumptions()`
> - Disabled Compare stub with tooltip
>
> **Acceptance criteria:**
> 1. Running any model auto-persists model record
> 2. `model_id` in all run responses
> 3. `activeModelId` set after every run
> 4. History works immediately after running
> 5. Export works after running
> 6. Idempotent model records
> 7. Save button in header, disabled without model
> 8. Annotation dialog + success flash
> 9. Formatted snapshot viewer
> 10. Raw JSON in collapsible details
> 11. Load restores assumptions
> 12. Compare stub present
> 13. No regressions
>
> **Files to create:** None
>
> **Files to modify:**
> - `backend/repositories/model_repo.py`
> - `backend/routers/models_router.py`
> - `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx`
> - `frontend/src/pages/ModelBuilderPage.tsx`
> - `frontend/src/pages/ModelBuilder/ModelBuilder.module.css`
> - `frontend/src/pages/ModelBuilder/History/HistoryTab.tsx`
> - `frontend/src/pages/ModelBuilder/History/HistoryTab.module.css`
>
> **Technical constraints:**
> - `ModelRepo` uses `DatabaseConnection` with async `execute`/`fetchone`/`fetchall`/`commit`
> - Response envelope: `success_response(data=...)` and `error_response(code, message)`
> - `model_repo` via `request.app.state.model_repo`
> - Frontend: `api.post<T>` / `api.get<T>` for all API calls
> - Zustand: `useModelStore.getState().setActiveModelId(id)` for imperative access outside render
> - CSS modules for all styling
> - `create_model` expects optional detection fields — for auto-created records just pass `ticker` and `model_type`
