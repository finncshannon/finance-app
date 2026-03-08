# Session 9A — Universe Data Files + Backend Loader
## Phase 9: Scanner

**Priority:** High (Tier 3 — shared asset needed by Phase 7 events + 9B hydration + 10E allocation)
**Type:** Backend Only
**Depends On:** None
**Spec Reference:** `specs/phase9_scanner.md` → Areas 1A, 1B, 1D backend

---

## SCOPE SUMMARY

Create curated static JSON data files for S&P 500, DOW 30, and Russell 3000 tickers (with company name, sector, industry for each). Enhance `UniverseService` to load from these files with proper universe tagging. Update the scanner backend to filter by universe tag. Add a `POST /universe/load-curated` endpoint.

---

## TASKS

### Task 1: Create Static Universe Data Files
**Description:** Create 3 JSON files in `backend/data/` containing curated ticker lists with metadata. These are build-time static assets used by the universe loader, events system (Phase 7), hydration service (9B), and allocation (10E). Format must include all 4 fields: `ticker`, `company_name`, `sector`, `industry`.

**Subtasks:**
- [ ] 1.1 — Create directory `backend/data/` if it doesn't exist.
- [ ] 1.2 — Create `backend/data/dow_tickers.json` — 30 tickers. Format:
  ```json
  [
    {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
    {"ticker": "MSFT", "company_name": "Microsoft Corporation", "sector": "Technology", "industry": "Software—Infrastructure"},
    {"ticker": "JPM", "company_name": "JPMorgan Chase & Co.", "sector": "Financial Services", "industry": "Banks—Diversified"},
    ...
  ]
  ```
  Use current DOW 30 components as of early 2025. All 30 must have accurate company names, GICS sectors, and industries.
- [ ] 1.3 — Create `backend/data/sp500_tickers.json` — ~503 tickers (same format). Use current S&P 500 components. Include all 4 fields for every entry. This file is also shared with Phase 7C (events system) — if 7C already created a minimal version, replace it with this complete one.
- [ ] 1.4 — Create `backend/data/russell3000_tickers.json` — ~3000 tickers (same format). Source: a publicly available index (e.g., iShares IWV holdings or a similar Russell 3000 reference). 100% accuracy is NOT required — this is a static seed that can be updated later. Coverage is more important than perfection. Sectors and industries should be reasonably accurate for the top 1000; smaller tickers can have "Unknown" as a fallback.

**Implementation Notes:**
- The JSON format uses lowercase field names matching the `companies` table columns: `ticker`, `company_name`, `sector`, `industry`.
- Sectors should use standard GICS sector names: Technology, Financial Services, Healthcare, Consumer Cyclical, Communication Services, Industrials, Consumer Defensive, Energy, Utilities, Real Estate, Basic Materials.
- Industries should be specific (e.g., "Software—Infrastructure" not just "Software").
- The Russell 3000 file will be ~500KB as JSON — perfectly fine to ship as a static asset.
- These files are read-only at runtime. Updates happen by replacing the files in a future release.

---

### Task 2: Curated Universe Loader
**Description:** Add a `load_curated_universe(name)` method to `UniverseService` that reads the static JSON files, bulk-inserts/upserts into the `companies` table with proper metadata, and tags each company with a `universe_tags` field.

**Subtasks:**
- [ ] 2.1 — In `backend/services/universe_service.py`, add a method to load from JSON:
  ```python
  import json
  from pathlib import Path

  DATA_DIR = Path(__file__).resolve().parent.parent / "data"

  UNIVERSE_FILES = {
      "dow": "dow_tickers.json",
      "sp500": "sp500_tickers.json",
      "r3000": "russell3000_tickers.json",
  }

  async def load_curated_universe(self, name: str) -> int:
      """Load a curated universe from a static JSON file.
      
      Upserts each ticker into the companies table with company_name,
      sector, industry, and adds the universe name to universe_tags.
      Returns count of companies loaded.
      """
      filename = UNIVERSE_FILES.get(name)
      if not filename:
          raise ValueError(f"Unknown curated universe: {name}")
      
      filepath = DATA_DIR / filename
      if not filepath.exists():
          raise FileNotFoundError(f"Universe file not found: {filepath}")
      
      with open(filepath, "r", encoding="utf-8") as f:
          entries = json.load(f)
      
      loaded = 0
      for entry in entries:
          ticker = entry["ticker"].upper()
          existing = await self.company_repo.get_by_ticker(ticker)
          
          if existing:
              # Update company_name, sector, industry if they were placeholder values
              updates = {}
              if existing.get("company_name") == ticker or existing.get("company_name") == "Unknown":
                  updates["company_name"] = entry.get("company_name", ticker)
              if existing.get("sector") == "Unknown":
                  updates["sector"] = entry.get("sector", "Unknown")
              if existing.get("industry") == "Unknown":
                  updates["industry"] = entry.get("industry", "Unknown")
              
              # Add universe tag
              current_tags = existing.get("universe_tags") or ""
              if name not in current_tags.split(","):
                  tag_list = [t for t in current_tags.split(",") if t] + [name]
                  updates["universe_tags"] = ",".join(tag_list)
              
              if updates:
                  await self.company_repo.update(ticker, updates)
          else:
              await self.company_repo.create({
                  "ticker": ticker,
                  "company_name": entry.get("company_name", ticker),
                  "sector": entry.get("sector", "Unknown"),
                  "industry": entry.get("industry", "Unknown"),
                  "universe_source": name,
                  "universe_tags": name,
              })
          loaded += 1
      
      logger.info("Curated universe '%s' loaded: %d tickers from %s", name, loaded, filename)
      return loaded
  ```

- [ ] 2.2 — Add a convenience method to load all curated universes in priority order:
  ```python
  async def load_all_curated(self) -> dict[str, int]:
      """Load all curated universes: DOW → S&P 500 → R3000."""
      results = {}
      for name in ["dow", "sp500", "r3000"]:
          try:
              count = await self.load_curated_universe(name)
              results[name] = count
          except Exception as exc:
              logger.error("Failed to load curated universe '%s': %s", name, exc)
              results[name] = 0
      return results
  ```

---

### Task 3: Add universe_tags Column to Companies Table
**Description:** The `companies` table already has `universe_source` (single value) but needs a `universe_tags` column (comma-separated) so tickers can belong to multiple universes (e.g., AAPL is in DOW, S&P 500, and R3000).

**Subtasks:**
- [ ] 3.1 — In `backend/db/init_user_db.py`, add `universe_tags` column to the `companies` CREATE TABLE statement:
  ```sql
  universe_tags   TEXT DEFAULT '',
  ```
  Add it after `universe_source`. Since the table uses `CREATE TABLE IF NOT EXISTS`, existing databases won't get the column automatically.

- [ ] 3.2 — Add an ALTER TABLE migration at the end of `init_user_db` to handle existing databases:
  ```python
  # Migration: add universe_tags column if missing
  try:
      await db.execute("ALTER TABLE companies ADD COLUMN universe_tags TEXT DEFAULT ''")
      await db.commit()
  except Exception:
      pass  # Column already exists
  ```

- [ ] 3.3 — Update `CompanyRepo.create()` to include `universe_tags` in the INSERT statement. It's already accepting arbitrary `data` dict fields via column names, but the INSERT has explicit column lists. Add `universe_tags` to the list:
  ```python
  # In the INSERT VALUES list, add:
  data.get("universe_tags", ""),
  ```

---

### Task 4: Update Scanner to Filter by Universe Tags
**Description:** The scanner's `_build_base_query` already filters by `universe_source`. Update it to also support filtering by `universe_tags` so that selecting "dow" returns all companies tagged with DOW (even if their `universe_source` is different).

**Subtasks:**
- [ ] 4.1 — In `backend/services/scanner/scanner_service.py`, update the universe filter in `_build_base_query`:
  ```python
  # Universe filter — check both universe_source and universe_tags
  if request.universe and request.universe != "all":
      wheres.append("(c.universe_source = ? OR c.universe_tags LIKE ?)")
      params.extend([request.universe, f"%{request.universe}%"])
  ```

- [ ] 4.2 — Similarly update `UniverseService.get_universe_tickers()` to check both columns:
  ```python
  async def get_universe_tickers(self, universe: str = "r3000") -> list[str]:
      if universe == "all":
          rows = await self.db.fetchall("SELECT ticker FROM companies ORDER BY ticker")
      else:
          rows = await self.db.fetchall(
              "SELECT ticker FROM companies WHERE universe_source = ? OR universe_tags LIKE ? ORDER BY ticker",
              (universe, f"%{universe}%"),
          )
      return [row["ticker"] for row in rows]
  ```

---

### Task 5: Add Load-Curated Endpoint
**Description:** Add a `POST /universe/load-curated` endpoint to trigger loading of the curated JSON files.

**Subtasks:**
- [ ] 5.1 — In `backend/routers/universe_router.py`, add a new request model and endpoint:
  ```python
  class LoadCuratedBody(BaseModel):
      name: str | None = None  # "dow", "sp500", "r3000", or None for all

  @router.post("/load-curated")
  async def load_curated_universe(request: Request, body: LoadCuratedBody = LoadCuratedBody()):
      """Load curated universe from static JSON files."""
      t0 = time.monotonic()
      svc = request.app.state.universe_service
      if body.name:
          count = await svc.load_curated_universe(body.name)
          result = {body.name: count}
      else:
          result = await svc.load_all_curated()
      ms = int((time.monotonic() - t0) * 1000)
      return success_response(data=result, duration_ms=ms)
  ```

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `backend/data/dow_tickers.json` exists with 30 entries, each having ticker, company_name, sector, industry.
- [ ] AC-2: `backend/data/sp500_tickers.json` exists with ~503 entries, each having all 4 fields.
- [ ] AC-3: `backend/data/russell3000_tickers.json` exists with ~3000 entries, each having all 4 fields (sector/industry may be "Unknown" for smaller tickers).
- [ ] AC-4: All JSON files use standard GICS sector names.
- [ ] AC-5: `UniverseService.load_curated_universe("dow")` loads 30 tickers into companies table with correct names, sectors, industries.
- [ ] AC-6: `UniverseService.load_curated_universe("sp500")` loads ~503 tickers.
- [ ] AC-7: `UniverseService.load_curated_universe("r3000")` loads ~3000 tickers.
- [ ] AC-8: Companies in multiple universes (e.g., AAPL) have comma-separated `universe_tags` (e.g., "dow,sp500,r3000").
- [ ] AC-9: Loading a universe twice is idempotent — doesn't create duplicate rows, updates metadata if improved.
- [ ] AC-10: `companies` table has `universe_tags` column (added via migration for existing DBs).
- [ ] AC-11: Scanner filter by universe="dow" returns all DOW-tagged companies (checks both `universe_source` and `universe_tags`).
- [ ] AC-12: `POST /universe/load-curated` endpoint works with `name` param or loads all when omitted.
- [ ] AC-13: `GET /universe/tickers?universe=sp500` returns S&P 500 tickers.
- [ ] AC-14: No regressions on existing SEC EDGAR universe load or scanner functionality.

---

## FILES TOUCHED

**New files:**
- `backend/data/dow_tickers.json` — 30 DOW tickers with metadata
- `backend/data/sp500_tickers.json` — ~503 S&P 500 tickers with metadata
- `backend/data/russell3000_tickers.json` — ~3000 Russell 3000 tickers with metadata

**Modified files:**
- `backend/services/universe_service.py` — add `load_curated_universe()`, `load_all_curated()`, `DATA_DIR`, `UNIVERSE_FILES` constants, update `get_universe_tickers()` to check `universe_tags`
- `backend/db/init_user_db.py` — add `universe_tags` column to schema + ALTER TABLE migration
- `backend/repositories/company_repo.py` — add `universe_tags` to `create()` INSERT
- `backend/services/scanner/scanner_service.py` — update universe filter in `_build_base_query()` to check `universe_tags`
- `backend/routers/universe_router.py` — add `POST /load-curated` endpoint

---

## BUILDER PROMPT

> **Session 9A — Universe Data Files + Backend Loader**
>
> You are building session 9A of the Finance App v2.0 update.
>
> **What you're doing:** Creating curated static JSON data files for 3 stock universes (DOW 30, S&P 500, Russell 3000) with company metadata, and building the backend loader to populate the companies table from these files. This is a shared asset — multiple phases (7C events, 9B hydration, 10E allocation) depend on these files.
>
> **Context:** The `companies` table currently gets populated from SEC EDGAR CIK mapping (~13K tickers) but with raw ticker strings as company names and no sector/industry data. The scanner universe shows "X companies" but only ~10 have actual financial data. These curated lists provide clean company names, sectors, and industries so the scanner and events system work immediately.
>
> **Existing code:**
>
> `universe_service.py` (at `backend/services/universe_service.py`):
> - `UniverseService.__init__(self, db, sec_provider)` — uses `CompanyRepo(db)` for DB access
> - `load_universe(name="r3000")` — fetches from SEC EDGAR CIK mapping, inserts with `company_name=ticker` (just the ticker string, no real names)
> - `get_universe_tickers(universe)` — returns `list[str]` filtered by `universe_source` column
> - `get_universe_stats()` — returns total, with_financials, with_market_data counts
> - `refresh_universe(universe)` — re-fetches CIK mapping and adds new tickers
>
> `company_repo.py` (at `backend/repositories/company_repo.py`):
> - `CompanyRepo.create(data)` — INSERT with explicit column list: ticker, company_name, sector, industry, cik, exchange, currency, description, employees, country, website, universe_source, gics_sector_code, gics_industry_code, fiscal_year_end, first_seen, last_refreshed
> - `CompanyRepo.upsert(data)` — checks if exists, updates or creates
> - `CompanyRepo.update(ticker, data)` — dynamic UPDATE from dict
> - `CompanyRepo.get_by_ticker(ticker)` — SELECT * from companies
>
> `init_user_db.py` (at `backend/db/init_user_db.py`):
> - Companies table schema:
>   ```sql
>   CREATE TABLE IF NOT EXISTS companies (
>       ticker TEXT PRIMARY KEY,
>       company_name TEXT NOT NULL,
>       sector TEXT DEFAULT 'Unknown',
>       industry TEXT DEFAULT 'Unknown',
>       cik TEXT,
>       exchange TEXT,
>       currency TEXT DEFAULT 'USD',
>       description TEXT,
>       employees INTEGER,
>       country TEXT,
>       website TEXT,
>       universe_source TEXT DEFAULT 'manual',
>       gics_sector_code TEXT,
>       gics_industry_code TEXT,
>       fiscal_year_end TEXT,
>       first_seen TEXT NOT NULL,
>       last_refreshed TEXT
>   );
>   ```
> - Does NOT currently have a `universe_tags` column — **add it**
>
> `scanner_service.py` (at `backend/services/scanner/scanner_service.py`):
> - `_build_base_query()` — universe filter currently: `wheres.append("c.universe_source = ?")` — update to also check `universe_tags`
>
> `universe_router.py` (at `backend/routers/universe_router.py`):
> - Current endpoints: `GET /stats`, `GET /tickers`, `POST /load`, `POST /refresh`
> - Uses `success_response(data=..., duration_ms=...)` pattern
>
> `main.py` — initializes `UniverseService(db, sec_provider)` and stores as `app.state.universe_service`
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for any backend keys shown in UI.
> - Data Format: All ratios/percentages as decimal ratios (0.15 = 15%).
>
> **Task 1: Create Static JSON Files**
>
> Create `backend/data/` directory with 3 files:
> - `dow_tickers.json` — 30 DOW components. Each entry: `{"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"}`. Use standard GICS sector names.
> - `sp500_tickers.json` — ~503 S&P 500 components, same format.
> - `russell3000_tickers.json` — ~3000 tickers, same format. Source from a public Russell 3000 reference. 100% accuracy not required — this is a static seed. Coverage matters more than perfection. Smaller tickers can have "Unknown" for sector/industry.
>
> **Task 2: Curated Universe Loader**
>
> In `universe_service.py`:
> - Add `DATA_DIR = Path(__file__).resolve().parent.parent / "data"` and `UNIVERSE_FILES` mapping
> - Add `load_curated_universe(name)`: read JSON, upsert each ticker into companies table, tag with `universe_tags`
> - Add `load_all_curated()`: load DOW → S&P 500 → R3000 in priority order
> - Upsert logic: if ticker exists, update company_name/sector/industry if they were placeholders ("Unknown" or same as ticker). Add universe name to comma-separated `universe_tags`.
> - If ticker doesn't exist, create with all metadata + `universe_source=name` + `universe_tags=name`.
>
> **Task 3: Schema Migration**
>
> In `init_user_db.py`:
> - Add `universe_tags TEXT DEFAULT ''` to the CREATE TABLE for companies
> - Add ALTER TABLE migration: `ALTER TABLE companies ADD COLUMN universe_tags TEXT DEFAULT ''` (wrapped in try/except for existing DBs)
>
> In `company_repo.py`:
> - Add `universe_tags` to the `create()` INSERT column list
>
> **Task 4: Scanner Universe Filter**
>
> In `scanner_service.py` `_build_base_query()`:
> - Change universe filter from `c.universe_source = ?` to `(c.universe_source = ? OR c.universe_tags LIKE ?)`
> - Pass both params
>
> In `universe_service.py` `get_universe_tickers()`:
> - Same dual check: `WHERE universe_source = ? OR universe_tags LIKE ?`
>
> **Task 5: Load-Curated Endpoint**
>
> In `universe_router.py`:
> - Add `POST /load-curated` with optional `name` param
> - If name provided, load that one universe. If not, load all.
>
> **Acceptance criteria:**
> 1. DOW JSON: 30 entries with all 4 fields
> 2. S&P 500 JSON: ~503 entries with all 4 fields
> 3. R3000 JSON: ~3000 entries (sector/industry may be Unknown for small tickers)
> 4. Load curated populates companies table with real names/sectors
> 5. Multi-universe tickers get comma-separated tags
> 6. Idempotent loading
> 7. Scanner filters by universe_tags
> 8. Load-curated endpoint works
> 9. No regressions
>
> **Files to create:**
> - `backend/data/dow_tickers.json`
> - `backend/data/sp500_tickers.json`
> - `backend/data/russell3000_tickers.json`
>
> **Files to modify:**
> - `backend/services/universe_service.py`
> - `backend/db/init_user_db.py`
> - `backend/repositories/company_repo.py`
> - `backend/services/scanner/scanner_service.py`
> - `backend/routers/universe_router.py`
>
> **Technical constraints:**
> - JSON files are static build-time assets — NOT fetched at runtime
> - `CompanyRepo.upsert()` already exists and handles insert-or-update. But for the curated loader, use manual check + create/update for more control over which fields to overwrite.
> - `universe_tags` is comma-separated TEXT (e.g., "dow,sp500,r3000"). Use `LIKE` for tag matching.
> - `Path` from `pathlib` for file paths (already used elsewhere in the backend)
> - `companies` table uses `ticker` as PRIMARY KEY (TEXT) — no duplicates possible
> - Standard GICS sectors: Technology, Financial Services, Healthcare, Consumer Cyclical, Communication Services, Industrials, Consumer Defensive, Energy, Utilities, Real Estate, Basic Materials
> - The `backend/data/` directory does not currently exist — create it
