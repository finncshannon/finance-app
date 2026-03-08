# WORKFLOW — Multi-Computer Planning & Execution
> Created by Designer Agent | February 22, 2026
> Status: APPROVED BY FINN

---

## Two-Environment Setup

### School Computer (Planning Only)
- **Location:** OneDrive → `Finance App/`
- **Contains:**
  - `specs/` — all planning and spec documents
  - `reference_code/` — read-only snapshots of source files (copied from home)
  - `brainstorm_plan.md` — session tracker
  - `open_items.md` — unresolved questions
  - This workflow document
- **Activity:** Planning sessions with Claude (Designer Agent)
- **Output:** New spec documents (text/markdown only)
- **Rule:** NO code execution, NO production file editing, planning only

### Home Computer (Production + Validation + Execution)
- **Location (local):** `C:\Claude Access Point\StockValuation\` — production codebase
- **Location (synced):** OneDrive → `Finance App/` — planning workspace (syncs with school)
- **Activity:**
  1. Prep reference code snapshots before school sessions
  2. Validate specs created at school against actual codebase
  3. Run downstream agent pipeline (PM → Architect → Developer → QA → Reviewer → Docs)

---

## Session Workflow

### Before a School Session (Home Computer)
1. Claude reads relevant source files from `StockValuation/`
2. Claude copies them into `Finance App/reference_code/` as read-only snapshots
3. Files sync to school computer via OneDrive
4. School computer now has everything needed for the planning session

### During a School Session (School Computer)
1. Claude reads existing specs from `Finance App/specs/`
2. Claude reads reference code from `Finance App/reference_code/` (if needed)
3. Designer Agent and Finn run the planning session
4. New spec document saved to `Finance App/specs/`
5. Updated brainstorm_plan.md reflects session completion

### After a School Session (Home Computer)
1. New spec documents sync from OneDrive automatically
2. Claude cross-checks new spec against actual codebase in `StockValuation/`
3. Any inaccuracies or assumptions are flagged and corrected
4. Finn reviews and approves the validated spec
5. Spec is now "approved" — ready for downstream agents

### Agent Execution (Home Computer Only)
1. Approved specs are fed to downstream agents in order:
   PM Agent → Architect Agent → Developer Agent → QA Agent → Reviewer → Docs
2. Agents read specs from `Finance App/specs/`
3. Agents write code into `StockValuation/` (or new project directory)
4. All code execution happens on home computer only

---

## Reference Code Management

### What Gets Copied to reference_code/
Only source files needed for upcoming planning sessions. Copied as-is, never modified.

| Source File | Needed For |
|-------------|-----------|
| python_scripts/auto_detect_model.py | Phase 1B (DDM), 1E (Assumption Engine) |
| python_scripts/config.py | Phase 1B-1D (model named ranges) |
| python_scripts/excel_writer.py | Phase 1B-1D (model write functions) |
| python_scripts/data_extractor.py | Phase 0B (database schema) |
| python_scripts/market_implied_calculator.py | Phase 1B (DDM), 1E (Assumption Engine) |
| python_scripts/data_cache.py | Phase 0B (database schema) |
| Screening_Tool/core/*.py | Phase 2 (Scanner) |
| Screening_Tool/gui/*.py | Phase 2 (Scanner — for understanding current UI) |
| Finance App/Setup files/*.md | Any session (agent pipeline reference) |

### What Never Gets Copied
- `venv/` or `.venv/`
- `__pycache__/`
- `data/filings/` and `data/financials/`
- `logs/`
- `*.db` (SQLite databases)
- `MasterValuation_F.xlsm` (too large, binary, already documented in specs)

---

## Validation Checklist (Post-School Session)
Before marking any spec as "approved," verify on home computer:

- [ ] Does the spec accurately describe how the existing code works?
- [ ] Are all named ranges, function signatures, and data flows correct?
- [ ] Are there assumptions in the spec that should be verified against code?
- [ ] Does the spec conflict with any previously approved spec?
- [ ] Is the spec self-contained enough for a downstream agent to work from?

Once all checks pass, spec status changes from "Complete" to "Approved" in
the brainstorm_plan.md tracker.

---

## Key Principle
> Specs are never "ill-informed" by the time they reach an agent.
> Written with code reference, verified against real source. Two passes.
> Planning happens anywhere. Execution happens at home.
