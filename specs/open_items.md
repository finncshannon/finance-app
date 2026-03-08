# OPEN ITEMS — Deferred Decisions & Open Questions
> Maintained by Designer Agent
> Last updated: February 26, 2026

---

## RESOLVED (since last update)

All design-phase items are resolved. The following were addressed:
- Database schema: 23 tables fully defined (Phase 0B + Integration Review)
- API endpoints: 87 endpoints fully defined (Phase 0C + Integration Review)
- All modules specced: Dashboard, Model Builder, Scanner, Portfolio, Research, Settings, Export
- Cross-module navigation: ticker header bar with [Model] [Research] [+ Watchlist] shortcuts
- Naming consistency: standardized to "revbased" everywhere

---

## DEFERRED TO IMPLEMENTATION PHASE

### 1. Multi-Computer File Sync
**Question:** How to access project files across home computer and school computer lab.
**Status:** Deferred — revisit when ready to work from second machine.
**Recommendation from earlier session:**
- OneDrive for specs + source code
- Exclude from sync: venv/, __pycache__/, *.db, data/filings/, data/financials/, logs/
- Better long-term: GitHub for code, OneDrive for planning docs only
- SQLite databases must NOT sync (corruption risk)

### 2. Agent Orchestration (OpenClaw / Mac Mini)
**Question:** Can an AI orchestration framework manage coding agents autonomously?
**Status:** Deferred — revisit after design phase completes.
**Context:** Finn is exploring OpenClaw with a Mac Mini M4 Pro (48GB) as a home server.
Model routing pattern: simple tasks → local 14B model (free), complex → Claude API (paid).
**Decision needed:** Which framework, how much autonomy, quality gates.

### 3. Architect-Level Decisions (Implementation)
These decisions were explicitly deferred to the Architect agent or implementation phase:

| Decision | Options | Notes |
|----------|---------|-------|
| CSS approach | CSS-in-JS vs Tailwind vs custom CSS | Phase 0D recommends custom CSS, but Architect may choose |
| Charting library | Recharts vs TradingView Lightweight Charts vs D3 | Phase 0D leaves open |
| State management | Zustand vs Redux Toolkit | Phase 0 leaves open |
| ORM choice | SQLAlchemy vs raw SQL | Phase 0B leaves open |
| PDF generation | ReportLab vs WeasyPrint | Phase 2F leaves open |
| Testing framework | pytest + Playwright vs alternatives | Not specced |
| CI/CD pipeline | GitHub Actions vs local scripts | Not specced |

### 4. Filing Parser Implementation
**Question:** How to reliably parse SEC EDGAR filings (XBRL + HTML formats).
**Status:** Architecture defined in Phase 4 (Research), implementation details deferred.
**Key challenge:** Older filings are HTML-only, newer are XBRL inline. Parser needs to handle both.

### 5. Russell 3000 Universe Data Source
**Question:** Where to get the current R3000 constituent list.
**Status:** Architecture defined in Phase 2 (Scanner), data source TBD.
**Options:** iShares IWV holdings CSV (free, updated daily), manual maintenance, paid data provider.

---

## NICE-TO-HAVE (Post-MVP)

Features explicitly scoped as post-MVP across all specs:

| Feature | Referenced In | Priority |
|---------|--------------|----------|
| Broker API integration | Phase 3 (Portfolio) | High — architecture ready |
| LBO Model | Phase 1G (Future Models) | Medium |
| NAV Model | Phase 1G (Future Models) | Medium-Low |
| Dashboard widget customization (drag/drop) | Phase 5 (Dashboard) | Medium |
| International expansion (non-US markets) | Phase 2 (Scanner) | Low |
| Multi-currency support | Phase 2E (Settings) | Low |
| Push notifications (Telegram/OpenClaw) | Phase 3 (Portfolio) | Low |
| ETF holdings import for universe | Phase 2 (Scanner) | Low |
