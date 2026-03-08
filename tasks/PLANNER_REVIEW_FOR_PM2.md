# Planner Review Notes for PM2
## From: Planner (original author of all specs)
## Date: March 6, 2026

---

## PURPOSE

I (the Planner) designed every feature, fix, and upgrade in this update cycle through direct conversation with Finn (the app owner). PM1 produced task files for Phases 7–8. I have reviewed every Phase 7 and Phase 8 task file against the original specs and this document contains my findings, directives, and corrections for PM2.

**Read this file before starting any work.** It will save you from propagating issues and give you context that neither the specs nor PM1's handoff captured.

---

## REVIEW RESULTS — PHASE 7 (7A–7E): ✅ ALL PASS

PM1 produced excellent task files for Phase 7. Every session matches the spec accurately. No corrections needed. Specific notes:

- **7A:** PM1 added a `v2.0` version bump that wasn't explicitly in the spec — this is correct and should stay.
- **7A:** PM1 improved on the spec by splitting the boot animation flag into `justBooted` + `dashboardAnimationPlayed` instead of a single flag. Better approach — keep it.
- **7C:** PM1 correctly noted the 9A dependency for the S&P 500 JSON file and handled it by having 7C create a minimal version. This is the right call.
- **7E:** PM1 added `useRef` for timer cleanup in the auto-clearing error messages. Good defensive coding — keep it.

---

## REVIEW RESULTS — PHASE 8 (8A–8O): ✅ ALL PASS (8K–8O need Builder prompt enrichment as noted)

All 15 Phase 8 task files have correct tasks, subtasks, acceptance criteria, and file lists. No contradictions with specs. Dependency chains are correct. Cross-cutting rules included in every Builder prompt.

**Sessions 8A–8J:** Full production quality. No changes needed.

**Sessions 8K–8O:** Correctly flagged as drafts by PM1. Tasks and acceptance criteria are complete and accurate. Builder prompts need the "Existing code" sections and inline code examples. PM1 provided all the source code context you need in `PM2_STARTUP_PROMPT.md` — use it to enrich the Builder prompts to match the quality of 8F or 8I.

Specific notes per session:

- **8K (DCF Key Outputs):** The spec calls for a "storytelling panel" with 3 headline cards + a step-down calculation. Make sure the Builder prompt includes the exact layout from the spec (EV → net debt → equity → shares → price step-down). Also note that `net_debt` and `shares_outstanding` are needed for the step-down but may not be directly on `DCFScenarioResult` — they're in `DCFAssumptions` (`dcf.net_debt`, `dcf.shares_outstanding`). The Builder will need to pass these through.
- **8L (Sensitivity Backend):** Straightforward parameter changes. The Builder prompt just needs the current values table and the new values table side by side. PM1's task file already has this — just make sure the Builder prompt includes the full `SensitivityParameterDef` class definition so the Builder knows the field types.
- **8M (Sliders):** The `formatParamValue` function needs to parse Python format strings (`"{:.2%}"`, `"{:.1f}x"`) — PM1's task file correctly identified this. Make sure the Builder prompt includes the existing `formatParamValue` code so the Builder can see what to replace.
- **8N (Tornado/MC/Tables):** This is the largest remaining session. The Builder prompt needs to show the current TornadoChart, MonteCarloPanel, and DataTablePanel source code. PM1's PM2 startup prompt has some of this but may not have all three panels' full source. Read the actual files to supplement if needed.
- **8O (History):** The Builder prompt needs the current `HistoryTab.tsx` source and the `ModelRepo` methods. PM1's PM2 startup prompt covers HistoryTab but may not cover ModelRepo — read `backend/repositories/model_repo.py` to verify the `create_model` and related methods exist.

---

## DIRECTIVES FOR PHASES 9–14

When you produce task files for the remaining phases, follow everything in `PM1_STARTUP_PROMPT.md` and add these specific directives:

### Phase 9 — Scanner

1. **9A creates shared assets.** The S&P 500 JSON file, DOW JSON, and Russell 3000 JSON are used by multiple phases (7C events, 9B hydration, 10E allocation). Make sure the Builder prompt for 9A notes this and includes the full JSON format spec with all 4 fields (ticker, company_name, sector, industry).
2. **9A is large scope.** Generating 3000-ticker JSON files with accurate metadata is non-trivial. The Builder prompt should note that the Russell 3000 list can use a publicly available source (e.g., iShares IWV holdings) and that 100% accuracy isn't required — it's a static seed that can be updated later.
3. **9B hydration must respect the rate limiter.** The existing `_RateLimiter` in `yahoo_finance.py` caps at 2000 req/hour. The hydration service must check `_rate_limiter.remaining` before each batch and back off if low. Include this in the Builder prompt.
4. **9C dynamic columns logic.** The spec says "last 3 columns are variable based on active filters." Make sure the Builder prompt clearly explains the priority: manual column selector overrides auto-detection. If the user has manually configured columns, don't auto-change them.

### Phase 10 — Portfolio

5. **10C is CRITICAL and overlaps with 11A.** The spec and MASTER_INDEX both flag this. Your task file for 10C must include a prominent note: "This session should be coordinated with or merged into 11A (Data Accuracy Normalization). They modify the same files. Run 11A first for the full pipeline audit, then 10C adds the live refresh / startup / WebSocket layer on top."
6. **10C day_change_pct investigation.** The Builder for 10C needs to actually trace the value through the pipeline. Include instructions to: (a) add temporary logging at each layer (Yahoo return → cache write → API response), (b) run the app with a known ticker, (c) verify the value at each layer, (d) then fix. Don't just guess the fix — investigate first.
7. **10B is large.** It has 4 areas: CSV import UI, context menu fix, company info hover card, edit position modal. Consider whether to split into 10B-1 and 10B-2 if the acceptance criteria exceed 25. Use your judgment.
8. **10E and 10F depend on Phase 7 events system.** The Income tab's "Upcoming Dividends" component pulls from the events cache. If Phase 7 hasn't been built when 10F runs, the Builder should show a placeholder with "Enable events to see upcoming dividends" instead of crashing. Include this fallback in the Builder prompt.

### Phase 11 — Research

9. **11A is CRITICAL and should coordinate with 10C.** Same note as above but from the other direction. The task file for 11A should include the full list of fields to audit (from the spec's Area 1A) and explicit instructions for the Builder to create a normalization spec document as part of the session output — a table mapping every field through all 5 layers with its expected format.
10. **11D (Price Charts) uses the existing historical endpoint.** The backend already has `GET /api/v1/companies/{ticker}/historical?period=1y` returning OHLCV bars. The Builder prompt should note that no backend changes are needed and should include the `PriceBar` type definition from `providers/base.py` so the Builder knows the response shape.
11. **11C (Trend Chart + DuPont) depends on 11A accuracy fix.** If chart values are still wrong (dividend yield 39%, etc.), the Fidelity upgrade is meaningless. Note this dependency clearly.

### Phase 14 — Packaging

12. **14A is last.** Don't produce this task file until all feature phases are done. It's fine to produce it as a placeholder with a note: "Build after all features are complete and tested."

---

## QUALITY STANDARDS TO MATCH

Reference these PM1 task files as the gold standard for quality:
- **8F (WACC Frontend)** — best example of a complex new component with live recalculation logic, linked inputs, override tracking, and detailed CSS specs
- **8I (Comps Frontend + Error Boundary)** — best example of a multi-area session with 5 workstreams, null safety patterns, and cross-module fixes
- **7C (Events Backend)** — best example of a backend session with multiple new service methods, SQL queries in the Builder prompt, and startup task integration

Every Builder prompt you write should have:
1. **"What you're doing"** — 2-3 sentence summary
2. **"Context"** — what exists now, what the user wants changed, why
3. **"Existing code"** — actual code excerpts from the current codebase (class signatures, key methods, CSS class names, TypeScript interfaces)
4. **Cross-cutting rules** — all 4 rules, every time
5. **Numbered tasks** with exact file paths and code snippets showing what to write
6. **Acceptance criteria** — numbered, testable
7. **Files to create / modify** — complete list
8. **Technical constraints** — libraries, patterns, conventions specific to this codebase

---

## HANDOFF PROTOCOL

When your context runs out:
1. Note which session you stopped at
2. Write a `PM2_HANDOFF.md` in `tasks/` with the same format PM1 used — status table, what's complete vs draft, what's remaining
3. If you created draft-quality files, note which ones and what's missing
4. Write a `PM3_STARTUP_PROMPT.md` with source code context for any incomplete sessions (same pattern PM1 used for PM2)
5. Include any observations or issues you found during code reading that future PMs should know about

---

## ONE FINAL NOTE

The specs in `specs/` and the task files in `tasks/` are the sole source of truth for this project going forward. Finn (the owner) has approved everything in the specs. Your job is to translate specs into Builder-executable task files with zero information loss. If something in a spec is ambiguous, err on the side of including more detail in the task file, not less. The Builder agents will have no access to the specs, this review, or any conversation history — they only see the Builder prompt you write.

---

*End of Planner Review Notes for PM2*
*March 6, 2026*
