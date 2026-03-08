# PM2 Handoff → PM3 (ClickUp Integration + Builder Prompts)
## From: PM2 | Date: March 6, 2026

---

## WHAT WAS DONE

PM2 completed **all remaining task files** for the Finance App v2.0 update cycle. Every phase now has full production-quality task files.

### PM1 Produced (Phases 7–8, sessions 7A–8J): ✅ No changes needed
### PM2 Rewrote (Phase 8, sessions 8K–8O): ✅ Full quality
### PM2 Produced (Phases 9–14, sessions 9A–14A): ✅ Full quality

**Total: 34 task files covering 34 sessions across 6 phases.**

---

## COMPLETE FILE INVENTORY

| Phase | Session | File | AC | Priority | Type |
|-------|---------|------|-----|----------|------|
| **7 — Dashboard** | 7A | `tasks/7A_tasks.md` | ~14 | Normal | Frontend |
| | 7B | `tasks/7B_tasks.md` | ~12 | Low | Frontend |
| | 7C | `tasks/7C_tasks.md` | ~15 | Normal | Backend |
| | 7D | `tasks/7D_tasks.md` | ~12 | Normal | Frontend |
| | 7E | `tasks/7E_tasks.md` | ~12 | Low | Frontend |
| **8 — Model Builder** | 8A | `tasks/8A_tasks.md` | 25 | Normal | Frontend |
| | 8B | `tasks/8B_tasks.md` | 17 | Normal | Backend |
| | 8C | `tasks/8C_tasks.md` | 23 | Normal | Frontend |
| | 8D | `tasks/8D_tasks.md` | 16 | Normal | Frontend |
| | 8E | `tasks/8E_tasks.md` | 15 | Normal | Backend |
| | 8F | `tasks/8F_tasks.md` | 22 | Normal | Frontend |
| | 8G | `tasks/8G_tasks.md` | 23 | Normal | Backend |
| | 8H | `tasks/8H_tasks.md` | 15 | High | Backend |
| | 8I | `tasks/8I_tasks.md` | 20 | High | Frontend |
| | 8J | `tasks/8J_tasks.md` | 17 | Normal | Frontend |
| | 8K | `tasks/8K_tasks.md` | 17 | Normal | Frontend |
| | 8L | `tasks/8L_tasks.md` | 13 | Normal | Backend |
| | 8M | `tasks/8M_tasks.md` | 14 | Normal | Frontend |
| | 8N | `tasks/8N_tasks.md` | 19 | Normal | Frontend |
| | 8O | `tasks/8O_tasks.md` | 15 | Normal | Mixed |
| **9 — Scanner** | 9A | `tasks/9A_tasks.md` | 14 | High | Backend |
| | 9B | `tasks/9B_tasks.md` | 14 | High | Backend |
| | 9C | `tasks/9C_tasks.md` | 17 | Normal | Frontend |
| **10 — Portfolio** | 10A | `tasks/10A_tasks.md` | 15 | Normal | Backend |
| | 10B | `tasks/10B_tasks.md` | 22 | Normal | Frontend |
| | 10C | `tasks/10C_tasks.md` | 17 | **CRITICAL** | Backend |
| | 10D | `tasks/10D_tasks.md` | 17 | High | Frontend |
| | 10E | `tasks/10E_tasks.md` | 13 | Normal | Backend |
| | 10F | `tasks/10F_tasks.md` | 14 | Normal | Frontend |
| **11 — Research** | 11A | `tasks/11A_tasks.md` | 13 | **CRITICAL** | Backend |
| | 11B | `tasks/11B_tasks.md` | 13 | High | Mixed |
| | 11C | `tasks/11C_tasks.md` | 13 | Normal | Frontend |
| | 11D | `tasks/11D_tasks.md` | 14 | Normal | Frontend |
| **14 — Packaging** | 14A | `tasks/14A_tasks.md` | 12 | Last | Mixed |

---

## YOUR JOB — PM3

### Primary Task: Push to ClickUp

Take every task file and create the corresponding ClickUp structure:

**Mapping:**
- **Phase** → ClickUp List (e.g., "Phase 9 — Scanner")
- **Session** → ClickUp Task (e.g., "9A — Universe Data Files + Backend Loader")
- **Tasks within session** → ClickUp Subtasks (e.g., "Task 1: Create Static Universe Data Files")
- **Subtasks within tasks** → ClickUp checklist items on the subtask
- **Acceptance criteria** → ClickUp checklist on the parent session task
- **Builder Prompt** → ClickUp task description on the session task (the full `## BUILDER PROMPT` section)

**What to include in each ClickUp task:**
- Title: `{Session ID} — {Title}`
- Description: The `## BUILDER PROMPT` section from the task file (this is the self-contained instruction for the Builder agent)
- Priority: Map from the task file (CRITICAL → Urgent, High → High, Normal → Normal, Low → Low)
- Type label: Backend / Frontend / Mixed
- Dependencies: Note in description (e.g., "Depends on: 8L, 8D")
- Acceptance criteria: As a checklist

### Timeout Risk Management

Phase 8 is the largest (15 sessions, ~320 AC). If you risk timing out:

**Batch by phase in this order:**
1. Phase 7 (5 sessions) — smallest, good warmup
2. Phase 9 (3 sessions) — small
3. Phase 10 (6 sessions) — medium
4. Phase 11 (4 sessions) — medium
5. Phase 8 (15 sessions) — largest, do last or split into 8A–8J + 8K–8O
6. Phase 14 (1 session) — trivial, do anytime

**If you need to hand off mid-way**, note which phases are in ClickUp and which aren't. The task files are the source of truth — nothing is lost if you stop partway through.

### Secondary Task: Builder Prompts (if context allows)

After ClickUp is populated, if you have context remaining, you can start executing Builder prompts — meaning actually feeding the Builder Prompt sections to a Builder agent to implement the code. Follow the MASTER_INDEX build order:

**Tier 1 — CRITICAL (do first):**
1. 11A + 10C (data integrity — coordinate per `specs/10C_11A_COORDINATION.md`)

**Tier 2 — High (blocking bugs):**
2. 8H + 8I (Comps crash fix)
3. 8D (terminal clip + scenario reorder)

**Tier 3 — Infrastructure:**
4. 9A (shared universe asset)
5. 9B (hydration)

**Tier 4 — Features (phase order):**
6. Everything else, grouped by phase

**Tier 5 — Last:**
7. 14A (packaging — after everything works)

---

## KEY REFERENCES

| File | Purpose |
|------|---------|
| `specs/MASTER_INDEX.md` | Session map, dependencies, build order, cross-cutting rules |
| `specs/cross_cutting_underscore_cleanup.md` | Display name rule (included in every Builder prompt) |
| `specs/10C_11A_COORDINATION.md` | **Critical** — coordination between 10C and 11A (overlapping files, build order) |
| `tasks/PM1_HANDOFF.md` | PM1's original handoff (for reference only — all work is now complete) |
| `tasks/PM2_STARTUP_PROMPT.md` | PM2's startup context (for reference only) |
| `tasks/PLANNER_REVIEW_FOR_PM2.md` | Planner's review notes with directives for Phases 9–14 |

---

## CROSS-CUTTING RULES (in every Builder prompt)

Every Builder prompt already includes these. Verify they're preserved when pushing to ClickUp:

1. **Display Name Rule:** All backend snake_case keys displayed in UI must use `displayNames.ts`. Never show raw keys. Never use inline `.replace(/_/g, ' ')`.
2. **Chart Quality:** Fidelity/Yahoo Finance information-density standards — labels, tooltips, annotations, crosshairs, responsive.
3. **Data Format:** All ratios/percentages stored as decimal ratios (0.15 = 15%). Frontend `fmtPct()` multiplies by 100.
4. **Scenario Order:** Bear / Base / Bull (left to right), Base default.

---

## COORDINATION NOTES

### 10C ↔ 11A: Data Integrity
These two sessions modify overlapping files (`yahoo_finance.py`, `market_data_service.py`, `data_extraction_service.py`). **Run 11A first**, then 10C. Full details in `specs/10C_11A_COORDINATION.md`. Both task files have prominent warnings at the top.

### 7C ↔ 9A: S&P 500 List
9A creates the full curated universe files. 7C creates a minimal S&P 500 list for events. If building in phase order (7 before 9), 7C's minimal list works. When 9A runs later, it replaces/expands it.

### 10F ↔ Phase 7: Upcoming Dividends
10F's Income tab has an "Upcoming Dividends" component that pulls from the events system built in Phase 7. If Phase 7 hasn't been built, the endpoint returns a graceful fallback message and the UI shows "Enable events to see upcoming dividends." This is already handled in the task file.

### 8O ↔ 8I: Export Button
8I adds export buttons that require `activeModelId` (set by 8O's auto-save-on-run). 8I's task file handles this with a disabled state + tooltip when no model ID exists. Ideally 8O runs before 8I but it works either way.

---

## QUALITY STANDARD

PM1's gold-standard references (also noted in the Planner review):
- **8F** — complex frontend with live recalculation, linked inputs, detailed CSS
- **8I** — multi-area session with 5 workstreams, null safety, cross-module fixes
- **7C** — backend session with SQL queries in the Builder prompt, startup integration

All PM2 task files match this standard. Every Builder prompt has: summary, context, existing code excerpts, cross-cutting rules, numbered tasks with file paths + code snippets, acceptance criteria, files list, technical constraints.

---

*PM2 Handoff — March 6, 2026*
*34 sessions complete (7A–14A) · 0 sessions remaining*
*Next: Push to ClickUp, then execute Builder prompts per MASTER_INDEX build order*
