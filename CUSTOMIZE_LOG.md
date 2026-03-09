# CUSTOMIZE_LOG.md — Session Handoff Document

> **Last updated:** 2026-03-08
> **Session scope:** News system — company-specific news tab + full system polish
> **Branch:** main (uncommitted changes)

---

## Project Overview

**Finance App** is a professional desktop equity valuation and portfolio management tool built for a single user (Finn, finance/investment professional).

### Tech Stack
| Layer | Technology | Location |
|-------|-----------|----------|
| Desktop shell | Electron 33.4.11 | `electron/` |
| Frontend | React 19 + TypeScript 5.7 + Vite 6.1 | `frontend/` |
| Backend | Python 3.12 + FastAPI + uvicorn | `backend/` |
| Database | SQLite (aiosqlite) — two DBs | `backend/db/` |
| State mgmt | Zustand 5 | `frontend/src/stores/` |
| Styling | CSS Modules + CSS custom properties | `frontend/src/styles/` |
| Charts | Recharts 3.7 | — |

### Current State
- **Version:** 2.0.0
- **Status:** Working. Backend and frontend are functional. News system fully operational with company-specific news, classification engine, and DB persistence.
- **Dev ports:** Frontend on `5174`, Backend on `8000`
- **Known issue:** Electron's embedded backend (Python 3.11 at `electron/resources/python/python.exe`) serves stale code. For development, always kill the embedded backend first, then start standalone: `cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000`

---

## Change History (This Session)

### 1. Company News Tab — CSS Completion
**Files:** `frontend/src/pages/Research/News/NewsTab.module.css`
**Change:** Added `.modeBtnCompany` class (light blue `#4fc3f7` accent) for the ticker toggle button in company news mode. The TSX already referenced this class but the CSS definition was missing from a prior session.
**Why:** Complete the company-specific news tab feature requested by user.

### 2. Backend Restart — Standalone Instance
**Change:** Killed Electron's embedded backend (PID on port 8000, running old Python 3.11 code) and started standalone backend with system Python 3.12 so the new `/api/v1/news/company/{ticker}` endpoint is available.
**Why:** Embedded backend serves stale code without the company news endpoint.

### 3. Fixed 1H Time Filter Bypass in Company Mode
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Before:** Time filter had a special condition `if (mode !== 'company' || timeFilter !== '1h')` that skipped filtering entirely when in company mode with 1H selected — showing all articles regardless of time.
**After:** Removed the bypass. Time filter applies uniformly across all modes:
```typescript
const cutoff = TIME_FILTER_MS[timeFilter];
if (cutoff !== Infinity) {
  result = result.filter((a) => { ... });
}
```
**Why:** User reported 1H showing 50 articles that weren't from the last hour, while other filters worked correctly.

### 4. Increased Company News Article Limit
**Files:** `backend/services/news_service.py`, `backend/routers/news_router.py`
**Before:** `get_company_news` default limit was 50, router max was 200.
**After:** Default limit 200, router max 500.
**Why:** User said "it shouldn't be only 50 per company" — just return whatever Google News provides.

### 5. Full System Polish — Backend (12 changes)

#### 5a. Race Condition Fix — Async Lock on RSS Cache
**Files:** `backend/services/news_service.py`
**Change:** Added `self._fetch_lock = asyncio.Lock()` in `NewsService.__init__`. The stale-check-and-fetch block in `get_top_news` is now wrapped in `async with self._fetch_lock:`. Prevents concurrent requests from triggering duplicate RSS fetches (thundering herd).

#### 5b. Per-Ticker Lock for Company News
**Files:** `backend/services/news_service.py`
**Change:** Added `self._company_locks: dict[str, asyncio.Lock] = {}`. Company news uses double-checked locking — check cache before lock, acquire per-ticker lock, check cache again, then fetch if still needed.

#### 5c. Classification Single-Pass Optimization
**Files:** `backend/services/news_service.py`
**Before:** `_classify_article` called `_score_text` 4 times per article (category+region x title+full_text), each iterating ~600+ regex patterns = ~2400 regex searches per article.
**After:** Replaced with `_score_all()` that scores both category AND region rules in one function call. Called twice (full_text + title with boost) instead of four times. Same thresholds preserved (`_CATEGORY_MIN_SCORE=2.0`, `_REGION_MIN_SCORE=2.0`, `_TITLE_BOOST=2.0`).

#### 5d. Removed Duplicate "chatbot" Pattern
**Files:** `backend/services/news_service.py`
**Change:** Technology category had `("chatbot", 2.0)` and `("chatbot", 2.5)` — both compiled into separate regex patterns, inflating scores to 5.0 combined. Removed the 2.0 entry, kept 2.5.

#### 5e. Non-Blocking DB Persist
**Files:** `backend/services/news_service.py`
**Before:** `await self._repo.upsert_articles(fresh)` blocked the API response.
**After:** `asyncio.create_task(self._persist_articles(fresh))` with a helper that logs errors. DB write no longer adds latency to the response.

#### 5f. Fuzzy Dedup Optimization
**Files:** `backend/services/news_service.py`
**Change:** Pre-computes word sets into `key_to_words` dict before the O(n^2) double loop, instead of calling `_title_words()` on every comparison.

#### 5g. Periodic Auto-Prune
**Files:** `backend/services/news_service.py`
**Change:** Added `_last_prune` counter. After a successful fetch+persist, prunes articles older than 30 days via `asyncio.create_task(self._prune_old_articles())`, at most once per hour. Previously `prune_old()` existed in the repo but was never called.

#### 5h. Company News Relevance Filter
**Files:** `backend/services/news_service.py`
**Change:** After dedup, filters out articles where neither title nor snippet contains the ticker or company name. Falls back to unfiltered if the filter removes everything (prevents aggressive filtering on ambiguous tickers).

#### 5i. Company News Title Dedup
**Files:** `backend/services/news_service.py`
**Change:** Added title-key dedup after URL dedup in `get_company_news`, using the existing `_title_key()` function. Catches same article appearing with different Google News redirect URLs.

#### 5j. Module-Level Imports
**Files:** `backend/services/news_service.py`, `backend/routers/news_router.py`
**Change:** Moved `from datetime import datetime, timezone`, `from urllib.parse import quote_plus` to top-level in news_service.py. Moved `from repositories.company_repo import CompanyRepo` to top of news_router.py. Previously these were inline imports inside hot paths.

#### 5k. Fixed Gzip Handling
**Files:** `backend/services/news_service.py`
**Before:** `_fetch_url_sync` had an `else` branch that blindly attempted `gzip.decompress()` on every non-gzip response, generating suppressed exceptions.
**After:** Only decompresses when `Content-Encoding: gzip` header is present.

#### 5l. Composite DB Indexes + Cleanup
**Files:** `backend/db/init_cache_db.py`
**Change:** Added `idx_news_cat_pub(category, published_at DESC)` and `idx_news_reg_pub(region, published_at DESC)` composite indexes. Removed unused `idx_news_source` index.

#### 5m. Robust Company Name Suffix Stripping
**Files:** `backend/services/news_service.py`
**Before:** Sequential `.replace()` calls for suffixes like "Inc.", "Corp." — order-dependent and fragile.
**After:** Single `re.sub()` regex pattern for all corporate suffixes, followed by `.strip(' &,')`.

### 6. Full System Polish — Frontend (10 changes)

#### 6a. Fixed Duplicate Fetch on Company Mode Switch
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Before:** `handleModeChange` called `fetchCompanyNews(ticker)` directly AND the `useEffect` at line 125 also triggered on mode change — causing double concurrent fetches.
**After:** `handleModeChange` only calls `setMode(newMode)`. The `useEffect` is the sole trigger.

#### 6b. Sort Button Visual Distinction
**Files:** `frontend/src/pages/Research/News/NewsTab.module.css`
**Before:** `.sortBtnActive` used `var(--text-primary)` and `var(--bg-tertiary)` — nearly identical to hover state.
**After:** Uses accent orange `#FF9F1C` with matching border and background, consistent with filter pills.

#### 6c. Sort/Filter Font Consistency
**Files:** `frontend/src/pages/Research/News/NewsTab.module.css`
**Change:** `.sortBtn` font changed from `var(--font-sans)` to `var(--font-mono)` to match adjacent filter pills.

#### 6d. Skeleton Filter Bar Placeholders
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`, `NewsTab.module.css`
**Change:** Loading skeleton now includes shimmer placeholders for 7 time filter pills and 2 sort buttons, preventing layout shift (CLS) when content loads. Added `.skeletonPill` CSS class.

#### 6e. Empty State Hint
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Change:** When `filtered.length === 0` but `sourceArticles.length > 0` and `timeFilter !== 'all'`, shows a "Show all time periods" button that sets `timeFilter` to `'all'`.

#### 6f. timeAgo Fallback
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Before:** `timeAgo()` returned the raw `dateStr` when `isNaN(then)`, exposing malformed strings in UI.
**After:** Returns empty string `''`.

#### 6g. Space Key Accessibility
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Change:** Article card `onKeyDown` now handles both `Enter` and `Space` keys (with `e.preventDefault()` for Space to avoid scroll).

#### 6h. Memoized handleArticleClick
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Change:** Wrapped in `useCallback` with empty dependency array.

#### 6i. Memoized visibleArticles
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Change:** `filtered.slice(0, visibleCount)` wrapped in `useMemo([filtered, visibleCount])`.

#### 6j. Fixed snippet Type
**Files:** `frontend/src/pages/Research/types.ts`
**Change:** `snippet: string` changed to `snippet?: string` in `NewsArticle` interface to match defensive render.

### 7. Fixed React Hooks Ordering Error
**Files:** `frontend/src/pages/Research/News/NewsTab.tsx`
**Before:** The `useMemo` for `visibleArticles` (change 6i) was placed AFTER the loading/error early returns, causing "Rendered fewer hooks than expected" React error.
**After:** Moved `visibleArticles` useMemo and `hasMore` computation BEFORE the early return blocks, ensuring hooks execute in the same order every render.

---

## Current Known Issues

1. **Electron embedded backend serves stale code** — The packaged Python 3.11 at `electron/resources/python/python.exe` doesn't have the latest backend changes. For development, always kill the embedded process on port 8000 and start standalone with system Python 3.12.

2. **News DB history is shallow** — The `news_articles` table was recently created. RSS feeds only carry ~24h of articles. Historical depth accumulates over time with each fetch cycle (every 90 seconds). After a few days of running, 7D filter will show significantly more articles.

3. **Company news relies on Google News RSS** — Google may rate-limit or block if hit too frequently. Current TTL is 120 seconds per ticker. If Google changes their RSS format, company news will break.

4. **Uncommitted changes** — All changes from this session are NOT committed. Run `git status` to see the full diff.

5. **`_company_cache` grows unbounded** — The in-memory company news cache (`self._company_cache`) has no eviction policy. Each ticker searched adds an entry that's never removed (only refreshed after TTL). For a single-user app this is fine, but if many tickers are searched, memory usage grows.

6. **`max()` type warning** — In `_classify_article`, `max(cat_scores, key=cat_scores.get)` passes `.get` (which returns `Optional[float]`) where `float` is expected. Works correctly at runtime but may trigger a type checker warning.

---

## Architecture Notes

### Patterns & Conventions
- **CSS Modules** — Every component has a `.module.css` file. Use `styles.className` pattern. No Tailwind.
- **CSS Variables** — All design tokens in `frontend/src/styles/variables.css`. Use `var(--token-name)` not hardcoded values. Exception: accent orange `#FF9F1C` is used directly in News components.
- **Font stack** — Inter (sans), JetBrains Mono (mono). Imported via Google Fonts in `global.css`.
- **API pattern** — `api.get<ResponseType>(path)` from `frontend/src/services/api.ts`. Backend returns `{ status, data, error }` envelope via `success_response()` / `error_response()`.
- **No React Router** — Page switching via Zustand `uiStore.activeModule`. Each page is a direct component import.
- **Backend repos** — Data access through repository classes (`backend/repositories/`), not direct SQL in services.
- **DB schema** — Two SQLite databases: `user_data.db` (portfolios, models) and `market_cache.db` (prices, news, cached data). Cache DB is ATTACHed as `cache` schema.

### Important File Relationships
| If you change... | Also update... |
|---|---|
| `backend/services/news_service.py` (response fields) | `frontend/src/pages/Research/types.ts` (NewsArticle interface) |
| `backend/db/init_cache_db.py` (table schema) | `backend/repositories/news_repo.py` (queries) |
| `frontend/src/styles/variables.css` (design tokens) | Nothing — CSS modules consume them automatically |
| `electron/preload.ts` (IPC API) | `electron/main.ts` (IPC handlers) + `frontend/src/vite-env.d.ts` (types) |
| Any backend router | `backend/main.py` (router registration in lifespan) |

### Dev Environment
- **Frontend dev server:** `npm run dev:frontend` → port 5174 (changed from 5173 to avoid conflict with Fulcrum launcher)
- **Backend:** `cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000`
- **Electron:** `npm run dev:electron` — starts Electron shell + embedded backend. For dev work, prefer standalone backend.
- **TypeScript check:** `cd frontend && npx tsc --noEmit`

---

## UI/Brand Status

### Branding
- **Working name:** "Spectre" (set in `electron/electron-builder.yml` productName)
- **App ID:** `com.financeapp.desktop`
- **Icons:** `electron/resources/icon.ico` and `icon.png` (custom icons exist)

### Color Scheme (Dark Theme)
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0D0D0D` | Main background |
| `--bg-secondary` | `#141414` | Card/panel backgrounds |
| `--bg-tertiary` | `#1A1A1A` | Hover/skeleton backgrounds |
| `--text-primary` | `#F5F5F5` | Main text |
| `--text-secondary` | `#A3A3A3` | Secondary text |
| `--accent-primary` | `#3B82F6` | Blue accent (buttons, links) |
| `--positive` | `#22C55E` | Green (gains) |
| `--negative` | `#EF4444` | Red (losses) |
| News accent | `#FF9F1C` | Orange — used throughout News tab |
| Company mode | `#4fc3f7` | Light blue — company news toggle |

### Typography
- **Sans-serif:** Inter (400/500/600/700)
- **Monospace:** JetBrains Mono (400/500/600)
- Both imported from Google Fonts in `frontend/src/styles/global.css`

### What's Customized vs Default
- **Fully custom:** Dark theme, all color tokens, boot sequence, news tab design
- **Default/framework:** Electron window chrome, scrollbar styling (minimal custom), Recharts default chart styles
- **Not yet built:** Many features from the 34-session roadmap (Phases 7-14) are spec'd but not implemented. The News tab and basic Research page are live; other pages may be stubs or partially built.

---

## News System Architecture (Detail)

Since this session focused heavily on the news system, here's a detailed reference:

### Data Flow
```
Google News RSS (13 feeds) → _fetch_all_feeds() → _parse_single_feed()
    → dedup (title-key + fuzzy 45% overlap) → _classify_article()
    → persist to DB (background) → serve from DB with historical depth

Google News RSS Search (per ticker) → _fetch_query()
    → dedup (URL + title-key) → relevance filter → _classify_article()
    → in-memory cache (120s TTL) → serve directly
```

### Key Files
| File | Purpose |
|------|---------|
| `backend/services/news_service.py` | ~1150 lines. RSS fetcher, XML parser, classification engine (800+ weighted keywords across 11 categories + 6 regions), dedup, company search |
| `backend/repositories/news_repo.py` | DB CRUD for `cache.news_articles` table |
| `backend/routers/news_router.py` | `/api/v1/news/top` and `/api/v1/news/company/{ticker}` endpoints |
| `backend/db/init_cache_db.py` | Table schema + indexes for news_articles |
| `frontend/src/pages/Research/News/NewsTab.tsx` | Three-mode UI (company/top/all), time/category/region filters, infinite scroll |
| `frontend/src/pages/Research/News/NewsTab.module.css` | All news tab styling |
| `frontend/src/pages/Research/types.ts` | `NewsArticle` interface |

### Classification Engine
- **Method:** Pre-compiled `re.Pattern` with word-boundary matching + weighted scoring
- **Categories (11):** Markets, Technology, Finance, Economy, Energy, Healthcare, Politics, Defense, World, Sports, Entertainment
- **Regions (6):** US, Europe, Asia, Middle East, Americas, Africa
- **Thresholds:** Category min score 2.0, Region min score 2.0, title boost 2x
- **Fallback:** "General" category, "Global" region

### Caching
- **Top news:** 90-second in-memory cache for RSS fetch frequency + SQLite DB for historical depth (up to 30 days)
- **Company news:** 120-second per-ticker in-memory cache, no DB persistence
