# Finance App — Model Builder: History Sub-Tab Update Plan
## Phase 8: Model Builder — History

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Model Builder → History sub-tab fix + Save to History macro button

---

## PLAN SUMMARY

The History tab works but is inaccessible because running a model from the Model tab doesn't create a `model` record in the database. `activeModelId` stays null, so History shows "No model found." The fix is two parts:

1. **Auto-create model record on run** — When a model is run from the Model tab, auto-persist a model record in the DB so History has something to work with
2. **Save to History macro button** — A visible "Save" button in the Model Builder header area (next to the search bar / model pills) so saving a version is one click from anywhere, not buried in the History tab

---

## AREA 1: AUTO-CREATE MODEL RECORD ON RUN

### Current Flow
```
User runs DCF → POST /run/dcf → engine computes → result returned to frontend → displayed
                                                   (nothing saved to DB)
```

### New Flow
```
User runs DCF → POST /run/dcf → engine computes → result returned to frontend → displayed
                               → auto-create/update model record in DB
                               → store model_id in response
                               → frontend sets activeModelId in modelStore
```

### Backend Changes
- In each `/run/{engine}` endpoint (`run_dcf`, `run_ddm`, `run_comps`, `run_revbased`):
  1. After successfully computing the result, upsert a model record: `INSERT OR REPLACE INTO models (ticker, model_type, last_run_at) VALUES (?, ?, ?)`
  2. Store the output in `model_outputs`
  3. Include `model_id` in the response envelope so the frontend can set it
- The model record is idempotent — running DCF for AAPL twice updates the same record, doesn't create duplicates
- Use `ModelRepo.get_or_create_model(ticker, model_type)` pattern

### Frontend Changes
- `ModelTab.tsx`: After a successful run, read `model_id` from the response and call `modelStore.setActiveModelId(id)`
- This makes History immediately functional after any model run

**Files touched:**
- `backend/routers/models_router.py` — add model persistence in run endpoints, include model_id in response
- `backend/repositories/model_repo.py` — add `get_or_create_model()` method
- `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx` — set activeModelId from response

---

## AREA 2: SAVE TO HISTORY MACRO BUTTON

### Goal
A "Save" button visible from the Model Builder page header so you can save the current model state to version history without navigating to the History tab.

### UI Location
In the `ModelBuilderPage.tsx` search bar area, next to the Export dropdown:

```
[Enter ticker...] [DCF] [DDM] [Comps] [Rev]  [Export ▾] [💾 Save]
```

### Behavior
- Button is disabled when no model has been run (`activeModelId` is null)
- On click: opens a small inline dialog (same as History tab's save dialog) — optional annotation input + Save/Cancel
- On save: POSTs to `/api/v1/model-builder/model/{modelId}/save-version` with the annotation
- Shows a brief success toast/flash: "Version saved"
- The History tab automatically shows the new version on next visit

### Files touched
- `frontend/src/pages/ModelBuilder/ModelBuilderPage.tsx` — add Save button in header, save dialog
- `frontend/src/pages/ModelBuilder/ModelBuilder.module.css` — save button and dialog styles

---

## AREA 3: HISTORY TAB POLISH (Minor)

### Small fixes while we're in here:
- The snapshot viewer shows raw JSON (`JSON.stringify`). Replace with a formatted view — at minimum, show key model outputs (implied price, WACC, scenarios) in a readable panel instead of a JSON dump
- The "Load" button doesn't actually restore the version's assumptions — it just opens the viewer same as "View." Either make Load actually restore the assumptions into the modelStore, or remove the button to avoid confusion. Recommend: make Load functional — it restores the version's assumptions and re-runs the model.
- Add a "Compare" feature stub: select two versions to see what changed (can be a future enhancement, just add the UI affordance now)

**Files touched:**
- `frontend/src/pages/ModelBuilder/History/HistoryTab.tsx` — formatted snapshot view, functional Load button
- `frontend/src/pages/ModelBuilder/History/HistoryTab.module.css` — snapshot panel styles

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8O — History Fix (Backend + Frontend)
**Scope:** All three areas
**Files:**
- `backend/routers/models_router.py` — auto-persist model record on run
- `backend/repositories/model_repo.py` — get_or_create_model
- `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx` — set activeModelId
- `frontend/src/pages/ModelBuilder/ModelBuilderPage.tsx` — Save button + dialog
- `frontend/src/pages/ModelBuilder/ModelBuilder.module.css` — button styles
- `frontend/src/pages/ModelBuilder/History/HistoryTab.tsx` — snapshot formatting, Load fix
- `frontend/src/pages/ModelBuilder/History/HistoryTab.module.css` — snapshot styles
**Complexity:** Medium (backend persistence is straightforward, frontend is button + dialog + snapshot formatting)
**Estimated acceptance criteria:** 12–15

---

## DECISIONS MADE

1. Running any model auto-creates/updates a model record in the DB — no separate "create model" step
2. `model_id` returned in run response so frontend can set it immediately
3. Save button lives in the Model Builder header bar, visible from all sub-tabs
4. Save dialog is inline (not a separate page/modal), matching the History tab's existing pattern
5. Snapshot viewer shows formatted key outputs instead of raw JSON
6. Load button actually restores version assumptions and re-runs the model
7. Compare feature is a stub/placeholder for future work

---

*End of Model Builder — History Sub-Tab Update Plan*
*Phase 8O · Prepared March 5, 2026*
