# Update Log — Spectre v2.2.0

**Status:** Complete
**Branch:** main
**Started:** 2026-03-09

---

## Changes

### 1. Fix title boost double-counting in news classifier
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** Title keywords were scored at 3x (1x in full_text pass + 2x title boost) instead of the documented 2x. Refactored to score title and snippet separately — title at `TITLE_BOOST` weight, snippet at 1x — then merge. Also replaced `_score_all` two-ruleset function with simpler `_score_text` single-ruleset function. Fixed `max()` type warning by using explicit lambda instead of `dict.get`.

### 2. Fix `\b` word boundary failure on trailing punctuation
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** Keywords ending in non-word characters (e.g. `u.s.`, `u.s.a.`, `opec+`) caused `\b` at the end of the pattern to fail when followed by whitespace. `_build_pattern` now detects trailing non-alphanumeric characters and uses a `(?=\s|$)` lookahead instead of `\b`.

### 3. Fix `who` false positive in Healthcare keywords
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** `"who"` (weight 1.0) matched the English pronoun "who" in virtually every article, inflating Healthcare scores universally. Replaced with `"world health organization"` (weight 3.0) which is unambiguous and high-signal.

### 4. Remove noisy low-weight keywords causing misclassifications
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** Removed 16 keywords with weight 1.0 that were too generic and caused false category matches: `app`, `platform`, `fab`, `digital` (Technology); `listing` (Markets); `final`, `season` (Sports); `stores`, `shopping`, `target`, `production`, `supply`, `demand`, `stamps` (Economy); `primary` (Politics); `series`, `fame`, `band`, `gallery` (Entertainment). Reduced `shell` from 1.5→1.0 (Energy, ambiguous noun). Changed `bp` (1.5) to `bp plc` (2.0) to avoid matching the abbreviation in other contexts.

### 5. Increase Python import check timeout from 10s to 30s
**Files:** `electron/main.ts`
**Type:** fix
**Description:** The `execSync` call that verifies critical Python imports (fastapi, uvicorn, aiosqlite) had a 10-second timeout, which can be exceeded on cold starts (antivirus scanning, disk cache misses). Bumped to 30 seconds to match the backend startup timeout.

### 6. Pre-load S&P 500 and Russell 3000 universes before frontend connects
**Files:** `backend/main.py`
**Type:** fix
**Description:** `load_all_curated()` (DOW, S&P 500, Russell 3000) was running inside a background task alongside the slow hydration process, causing a race condition where the frontend could connect before the companies table was populated. Moved the curated universe load to the synchronous startup sequence so all ~3,000 tickers are in the database before the health check passes. Background hydration (market data fetch) remains async.

### 7. Fix dividend yield showing 40%+ due to Yahoo percentage format
**Files:** `backend/providers/yahoo_finance.py`, `backend/services/market_data_service.py`
**Type:** fix
**Description:** Yahoo Finance's `dividendYield` field is always in percentage format (0.4 = 0.4%, 2.72 = 2.72%), but the old normalization only divided by 100 when > 1.0 — so yields under 1% (like AAPL's 0.4%) were stored as-is and displayed 100x too high (e.g., 40% instead of 0.4%). Fixed at the provider level: now uses `trailingAnnualDividendYield` (already decimal) as primary source, falls back to `dividendYield / 100`. Removed the broken conditional normalization from market_data_service.

### 8. SEC EDGAR email enforcement (dynamic User-Agent)
**Files:** `backend/providers/sec_edgar.py`, `backend/main.py`, `backend/routers/research_router.py`, `backend/routers/companies_router.py`, `frontend/src/pages/Settings/sections/DataSourcesSection.tsx`, `frontend/src/pages/Research/Filings/FilingsTab.tsx`
**Type:** enhancement
**Description:** SEC EDGAR User-Agent is now built dynamically from the email configured in Settings (format: `Spectre <email>`). Removed hardcoded email. Added `SECEdgarEmailNotConfigured` exception that blocks requests when no email is set. Frontend shows a warning banner in the Filings tab and validates email format in Settings. All SEC-facing endpoints return `SEC_EMAIL_REQUIRED` error code when email is missing.

### 9. Fix SEC EDGAR "undeclared automated tool" blocking
**Files:** `backend/providers/sec_edgar.py`
**Type:** fix
**Description:** SEC was blocking requests due to missing `Host` header and incorrect User-Agent format (had version slash). Fixed: added per-request `Host` header matching the target domain, changed UA from `Spectre/2.1.0 email` to `Spectre email`. Added `_is_sec_blocked()` detection for SEC's block page (returns HTTP 200 with error HTML). Added 429 retry with backoff and fresh request headers.

### 10. Fix 10-Q filing parser returning 0 sections
**Files:** `backend/providers/sec_edgar.py`
**Type:** fix
**Description:** The `parse_10k_sections` method couldn't match 10-Q section headers because they use HTML entities (`&#160;`) instead of regular spaces. Added entity normalization before pattern matching and extended section patterns to cover 10-Q items (Financial Statements, MD&A, Controls and Procedures). Parser now finds 5 sections for both 10-K and 10-Q filings.

### 11. Add backend logging configuration
**Files:** `backend/main.py`
**Type:** enhancement
**Description:** The `finance_app` logger had no handler configured — all `logger.info()` calls were silently dropped. Added `logging.basicConfig()` with stderr output so backend log messages are visible through Electron's process pipes.

### 12. Research search autocomplete with ticker and company name
**Files:** `frontend/src/pages/Research/TickerSearch.tsx`, `frontend/src/pages/Research/TickerSearch.module.css`, `frontend/src/pages/Research/ResearchPage.tsx`, `backend/repositories/company_repo.py`
**Type:** enhancement
**Description:** Replaced the manual ticker-only input with a live autocomplete search. Suggestions appear after the first keystroke, matching both ticker symbols and full company names. Dropdown shows ticker in blue with the company name beside it. Supports keyboard navigation (arrow keys + Enter), 150ms debounce, and outside-click dismiss. Backend search improved to prioritize exact ticker matches, then ticker prefix, then name matches, returning only the fields needed (ticker, company_name, exchange).

### 13. Fix Portfolio hover card not populating and disappearing on mouse move
**Files:** `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.tsx`, `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.module.css`, `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx`
**Type:** fix
**Description:** The ticker hover popup in Holdings was broken in two ways: (1) it fetched from a non-existent API endpoint, returning no data, and (2) the card disappeared immediately when moving the mouse toward it because `handleTickerMouseLeave` unconditionally destroyed it after 200ms. Fixed the API calls to use `/api/v1/companies/{ticker}` and `/api/v1/companies/{ticker}/quote` in parallel. Added coordinated hover timing — `HoldingsTable` now uses a cancellable close timer (`hoverCloseRef`) that gets cleared when the mouse enters the card via `onMouseEnterCard`. Card also shows current price with day change percentage and has its own internal mouse leave timer for smooth dismissal.

### 14. Add 1Y price change to Portfolio hover card
**Files:** `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.tsx`
**Type:** enhancement
**Description:** Added 1-year price change percentage to the hover card metric grid (after Div Yield, before Beta). Fetches 1Y daily historical bars and computes the return internally from first and last close prices in the series, avoiding cross-source mismatches between live quote and historical data.

### 15. Overhaul CSV transaction import parser
**Files:** `backend/services/portfolio/csv_import.py`, `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx`, `.gitignore`
**Type:** fix + enhancement
**Description:** The CSV import parser failed on Fidelity transaction exports due to multiple issues: BOM character (`\ufeff`) at file start broke header detection, two leading blank lines skipped the header row, column names with unit suffixes like `Price ($)` and `Commission ($)` didn't match aliases, `Run Date` wasn't recognized as a date column, and trailing Fidelity disclaimer text created garbage rows. Fixed by adding: BOM stripping, leading blank line removal, trailing footer trimming, header normalization that strips `($)`/`(%)` suffixes before matching, `run date` to date aliases, and expanded transaction type inference (`YOU BOUGHT`/`YOU SOLD`, `REINVEST`, `DISTRIBUTION`). Improved error messages to show which columns matched vs didn't. Frontend manual column mapping now shows transaction-specific fields (Date, Action, Price, Fees) instead of position-only fields when importing transactions. Added `*.csv` to `.gitignore` to exclude user data files.

### 16. Add "Clear All" positions button
**Files:** `backend/repositories/portfolio_repo.py`, `backend/services/portfolio/portfolio_service.py`, `backend/routers/portfolio_router.py`, `frontend/src/pages/Portfolio/PortfolioPage.tsx`, `frontend/src/pages/Portfolio/PortfolioPage.module.css`
**Type:** enhancement
**Description:** Added a "Clear All" button to the Holdings toolbar that deletes all portfolio positions in one action. Requires confirmation dialog before executing. Button styled with red border, turns solid red on hover, and only appears when positions exist. Backend adds `DELETE /api/v1/portfolio/positions` endpoint with cascading lot deletion.

### 17. Add row removal to import preview
**Files:** `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx`, `frontend/src/pages/Portfolio/Holdings/ImportModal.module.css`
**Type:** enhancement
**Description:** Added an X button on the left of each row in the import preview (step 3) for both positions and transactions. Allows users to remove individual rows before executing the import. Button is subtle by default, turns red on hover.

### 18. Holographic HUD boot sequence with procedural visuals
**Files:** `frontend/src/components/BootSequence/BootSequence.tsx`, `frontend/src/components/BootSequence/BootHUD.tsx`, `frontend/src/components/BootSequence/BootSequence.module.css`, `frontend/src/App.tsx`, `electron/main.ts`, `frontend/src/styles/variables.css`, `frontend/src/pages/Dashboard/DashboardPage.tsx`, `frontend/src/pages/Dashboard/DashboardPage.module.css`, `frontend/src/components/Navigation/ModuleTabBar.module.css`
**Type:** feature
**Description:** Tony Stark / JARVIS-inspired holographic boot sequence. Five-phase animation: black → frame draw (clip-path reveal with corner brackets) → identity (typewriter "SPECTRE" title) → system checks (8 staggered check lines with animated checkmarks) → dissolve (fade-out with scale). Fixed Electron startup order — frontend loads before backend starts so boot sequence is visible immediately. Added resolved-flag guards to both Electron and React health poll loops to prevent exponential poll growth. Pages deferred until backend ready. Living UI effects added to dashboard (widget glow pulses) and tab bar (active tab glow).

### 19. Boot sound design — engine spool-up, turbo whine, and system idle
**Files:** `frontend/src/services/soundManager.ts`, `frontend/src/components/BootSequence/BootSequence.tsx`
**Type:** feature
**Description:** Complete procedural audio redesign for boot sequence using Web Audio API. Engine spool-up with 7 layers matching The Batman Batmobile frequency profile: dual detuned sawtooth sub-bass (30/32Hz) for V8 rumble, square wave exhaust growl, cross-plane crank LFO firing pulse, turbo compressor noise (bandpass-swept 400→2200Hz), distant air rush, and low-pass exhaust noise. High-frequency ticks are ascending digital pings (4000Hz+, 8-12ms) that step up 150Hz per ping across all 23 boot events (key ticks, boot ticks, check confirms), driving the spool-up. Engine reaches peak in 5s, holds ~1s on dashboard, then crossfades over 3s into a Star Wars-style system idle hum (55Hz + 110Hz sines with low-pass ventilation noise) that lingers 8s before fading to silence.

### 20. Dashboard widget boot cascade — 3-stage loading animation
**Files:** `frontend/src/pages/Dashboard/DashboardPage.tsx`, `frontend/src/pages/Dashboard/DashboardPage.module.css`
**Type:** feature
**Description:** Dashboard widgets now load in a cinematic 3-phase cascade on first boot. Phase 1: backplate shells pop in one by one (250ms stagger) after a 400ms blank screen. Phase 2: widget headers/names build top-to-bottom (200ms stagger). Phase 3: data populates in a fixed order (Market → Portfolio → Watchlist → Upcoming Events → Recent Models) with randomized timing gaps (150-500ms) so animations overlap naturally. Portfolio and Upcoming Events use a top-down reveal; other widgets use a left-to-right stepped typewriter effect (CSS `steps(20)` on `clip-path`). Dashboard header and error banner hidden during animation. Grid always renders so shells appear before API data loads. Animation state tracked in Zustand to skip on subsequent visits.

### 21. Boot sequence visual and sound refinements
**Files:** `frontend/src/components/BootSequence/BootSequence.module.css`, `frontend/src/components/BootSequence/BootHUD.tsx`, `frontend/src/services/soundManager.ts`
**Type:** refactor
**Description:** Simplified boot screen to just the SPECTRE title card — removed grid lines, system checks, and checkmarks. Title enlarged to 48px with 12px letter-spacing. Frame auto-sizes to fit title with version text absolutely positioned so it doesn't affect centering. Removed ascending `pingCounter` from all ping sounds — all dashboard pings now use the same fixed holographic tone (6800Hz crystal + 9200Hz harmonic tail). Removed boot screen typewriter sound. Replaced transition "wifi down" descending triangle sweep with subtle low-pass filtered noise fade. Widget backplates use glass styling (`rgba(20,20,20,0.85)` + `backdrop-filter: blur(8px)`) consistent across all stages. Hard cut from boot to dashboard instead of dissolve.

### 22. Sound engine master gain fix
**Files:** `frontend/src/services/soundManager.ts`
**Type:** fix
**Description:** Fixed `fadeOutBootHum()` which referenced removed variables (`noiseGain`, `noiseGains`, `noiseFilter`) causing the engine sound to never stop and the dashboard to not load. Replaced per-node fade logic with single `engineMaster.gain.setTargetAtTime(0, t, 1.2)` call that fades all engine layers through one GainNode. Fixed noise burst during transition caused by `washGain` defaulting to 1.0 for 300ms before its `setValueAtTime` fired — added explicit `setValueAtTime(0.0001, t)` at start.

### 23. Dashboard News widget and grid restructure
**Files:** `frontend/src/pages/Dashboard/News/NewsWidget.tsx`, `frontend/src/pages/Dashboard/News/NewsWidget.module.css`, `frontend/src/pages/Dashboard/DashboardPage.tsx`, `frontend/src/pages/Dashboard/DashboardPage.module.css`
**Type:** feature
**Description:** Added a News widget to the dashboard that fetches from the existing `/api/v1/news/top` endpoint, sorts by coverage count then recency, and shows the top 15 articles with source, time ago, category, and headline. "View All" navigates to the Research module. Restructured the dashboard grid from flat CSS Grid cells to a hybrid layout: two flex column containers (left: Market + News, right: Portfolio + Events) ensure widgets stack tightly without shared row heights, with Watchlist and Recent Models remaining full-width below. Responsive breakpoint collapses to single column at 1200px.

### 24. Dashboard grid height balancing
**Files:** `frontend/src/pages/Dashboard/DashboardPage.module.css`, `frontend/src/pages/Dashboard/News/NewsWidget.tsx`, `frontend/src/pages/Dashboard/News/NewsWidget.module.css`, `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.module.css`
**Type:** refactor
**Description:** Balanced left and right column heights on the dashboard. News widget reduced from 15 to 8 articles so left column (Market + News) matches right column (Portfolio + Events) height. Upcoming Events grid cell uses `flex: 1` to stretch its backplate down to match the left column, and its inner widget uses `display: flex; flex-direction: column; height: 100%` with `flex: 1` on the body so the grey interior fills the full backplate. Removed scroll overflow from News — content hugs naturally. This is the locked-in dashboard widget layout.

### 25. Live scrolling news ticker on dashboard
**Files:** `frontend/src/pages/Dashboard/News/NewsWidget.tsx`, `frontend/src/pages/Dashboard/News/NewsWidget.module.css`, `frontend/src/pages/Dashboard/DashboardPage.tsx`, `frontend/src/pages/Dashboard/DashboardPage.module.css`
**Type:** feature
**Description:** News widget now fetches all articles from the last 24 hours (up to 2000) sorted by time (newest first), matching the "All News" mode in Research. Articles auto-scroll upward using a CSS `translateY` animation for smooth GPU-accelerated gliding. Scroll pauses on hover so users can read and click articles. Scroll starts after boot cascade finishes (6s delay on fresh boot, immediate on tab switch). Added pulsing green "LIVE" tag in the widget header. Also added `.widgetReady` CSS class so post-boot widgets render without animation classes or `overflow: hidden`, preventing interference with the scroll and ensuring boot animations only play on app startup, not tab switches.

### 26. News widget manual scroll with auto-resume
**Files:** `frontend/src/pages/Dashboard/News/NewsWidget.tsx`
**Type:** enhancement
**Description:** Added mouse wheel scroll support to the live news ticker. Users can scroll up/down through articles manually while the CSS `translateY` animation stays as the core engine. On wheel event, the current computed `translateY` is captured and the animation is replaced with a static transform that responds to wheel delta. After 5 seconds of no interaction (hover leave or wheel idle), the auto-scroll resumes. Scroll position is clamped to content bounds.

### 27. News scroll loop and wheel interaction
**Files:** `frontend/src/pages/Dashboard/News/NewsWidget.tsx`
**Type:** enhancement
**Description:** News ticker now loops seamlessly by rendering articles twice — when the CSS animation scrolls past the first set, the second identical set fills in. Manual wheel scrolling wraps around at both ends. Wheel events are captured natively with `{ passive: false }` so scrolling over the news widget only moves the ticker, not the page. Scroll input is 1:1 with mouse wheel (no momentum/lerp). Auto-scroll resumes 5 seconds after last interaction.

### 28. Mini chart in Market Performance detail panel
**Files:** `frontend/src/pages/Research/MarketPerformance/MiniChart.tsx`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.module.css`
**Type:** feature
**Description:** Added a compact 3-month line chart widget to the Market Performance detail popup, positioned between the Price and Performance widgets in the left column. Uses `lightweight-charts` `LineSeries` with a minimal dark theme (transparent background, subtle grid, blue line). Fetches historical data from the existing `/api/v1/companies/{symbol}/historical` endpoint. No controls or toolbar — just a clean price line with crosshair.

### 29. Market Performance layout — two-column vertical design + data fix
**Files:** `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.module.css`, `frontend/src/pages/Research/MarketPerformance/MiniChart.tsx`
**Type:** fix / refactor
**Description:** Restructured the Market Performance main view from stacked horizontal sections to a side-by-side two-column layout — Indices on the left, Sectors on the right. Each column displays cards in a 2-wide grid with outlier cards centered at the bottom at matching width. Restored original button-style card design. Fixed data display: `day_change_pct` was a decimal ratio from the backend (e.g. `-0.0016`) but displayed without `*100` conversion, showing `0.00%` — now correctly shows `-0.16%`. Also fixed MiniChart not loading: the `api.get` wrapper unwraps the response envelope, so the fetch expected `res.bars` but data came back as a flat `PriceBar[]` array. Moved chart below Performance widget per user preference.

### 30. Global Markets column with continent tabs
**Files:** `backend/routers/market_router.py`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.module.css`
**Type:** feature
**Description:** Added international country market indices to the Market Performance tab. Backend defines 36 country ETFs across 5 continents (Europe, Asia, Americas, Middle East & Africa, Oceania) and fetches them in parallel alongside existing indices/sectors. Frontend adds a middle "Global Markets" column between Indices and Sectors with continent filter tabs. Layout expanded from 2-column to 3-column grid. Cards made more compact/square with reduced padding and font sizes to fit the tighter columns.

### 31. Interactive world map visualization for global markets
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `frontend/src/pages/Research/MarketPerformance/WorldMap.module.css`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`, `frontend/package.json`
**Type:** feature
**Description:** Added a 2D world map above the Global Markets card list in the middle column. Uses `react-simple-maps` with Mercator projection. Black background, grey country outlines. Countries with tracked market data are shaded green (positive) or red (negative) with intensity scaling based on percentage change magnitude. Includes hover tooltip showing country name and day change %. Clicking a country opens its detail panel. US is colored from SPY data. ISO 2→3 letter code mapping connects backend country codes to TopoJSON geometry.

### 32. Global markets — native indices swap + expanded country coverage
**Files:** `backend/routers/market_router.py`, `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`
**Type:** feature
**Description:** Replaced all ETF tickers with native country stock market indices (e.g. EWU→^FTSE, EWG→^GDAXI, FXI→000001.SS) for more accurate country-level market data. Added 5 new countries: Russia (IMOEX.ME), Lithuania (^OMXV), Latvia (^OMXR), Estonia (^OMXT), Venezuela (IBC.CR). Fixed 9 broken Yahoo Finance tickers by testing alternatives (Norway→OBX.OL, Poland→WIG20.WA, Greece→GD.AT, Portugal→PSI20.LS, Saudi→^TASI.SR, UAE→DFMGI.AE, Egypt→^EGX30.CA). Dropped Qatar (no working ticker). Vietnam and Pakistan fall back to ETFs (VNM, PAK). Global cards now show country name as primary label with index ticker below. Total coverage: 51 countries across 5 continents. Exhaustive testing confirmed Yahoo Finance has no data for remaining African, Middle Eastern, or Eastern European exchanges (Hungary, Czech Republic, Romania, Morocco, Kenya, Kuwait, etc.).

### 33. World Markets UI polish — unified widget, 5-wide cards, continent summary
**Files:** `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.module.css`, `frontend/src/pages/Research/MarketPerformance/WorldMap.module.css`
**Type:** refactor / feature
**Description:** Merged the World Map and Global Markets list into a single unified "World Markets" widget. Redesigned country cards: 5-wide flexbox grid with centered orphan rows, 2-line layout (country name + price/change on one row), removed ticker line. Adjusted column proportions (0.85fr / 1.3fr / 0.85fr) to give the map more room. Added "All" continent tab as default — shows 5 continent summary cards with averaged gain/loss across constituent countries. Clicking a continent card navigates to its detail view. Indices and Sectors columns unchanged.

### 34. Map zoom on continent filter
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `frontend/src/pages/Research/MarketPerformance/WorldMap.module.css`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`
**Type:** feature
**Description:** Selecting a continent filter now zooms and pans the world map to that region. Each continent has tuned center coordinates and zoom levels (e.g., Europe centers on [15, 52] at 3.5x zoom). "All" resets to the default world view. Smooth 0.5s ease-in-out CSS transition on the SVG group transform for animated zoom.

### 35. Enhanced zoomed map — high-detail TopoJSON, country labels, dev mode positioning
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `frontend/src/pages/Research/MarketPerformance/WorldMap.module.css`
**Type:** feature
**Description:** Zoomed continent views now load higher-resolution 50m TopoJSON (vs 110m for world view) for smoother coastlines and borders. Added full country name labels with dark stroke outlines on all tracked countries when zoomed. Small countries (Belgium, Netherlands, Israel, etc.) get white leader lines; large countries place labels in nearby grey space without lines. Built a reusable dev mode (toggle `DEV_MODE = true` in WorldMap.tsx) that makes labels draggable with a live offset panel — used to hand-position all 40+ labels, then hardcoded the values and disabled dev mode. Tuned continent zoom centers (Europe, Americas, Middle East & Africa). Added `LABEL_COORD_OVERRIDE` for France, Norway, US whose centroids are pulled by overseas territories.

### 36. World map polish — zoom tuning, label font-size sync, detail panel cleanup
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `frontend/src/pages/Research/MarketPerformance/WorldMap.module.css`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.tsx`, `frontend/src/pages/Research/MarketPerformance/MarketPerformanceTab.module.css`, `docs/DEV_MODE.md`
**Type:** feature / fix
**Description:** Hand-tuned all continent zoom/pan views using a new dev mode tool (zoom+drag captured to panel, values hardcoded, dev code stripped). Repositioned labels across all continents via draggable dev mode. Increased label font size from 5 to 7. Fixed font-size flash on continent switch — labels now CSS-transition font-size and stroke-width in sync with the 0.5s zoom animation. Hid Top Holdings widget for world market items (country indices don't have ETF holdings); news section expands to fill the right column. Dev mode workflows documented in `docs/DEV_MODE.md` as paste-in snippets — no dev code lives in the codebase.

### 37. 3D spinning globe with eDEX-inspired styling
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `frontend/src/pages/Research/MarketPerformance/WorldMap.module.css`
**Type:** feature
**Description:** Converted the 2D Mercator world map to a 3D orthographic globe. Auto-spins at ~0.12°/frame when on "All" view. Drag-to-rotate with 0.3 sensitivity and ±70° latitude clamp. Animated transitions (800ms ease-in-out via `requestAnimationFrame`) when switching continent filters. Labels only render on the visible hemisphere using spherical geometry. Removed ZoomableGroup — all zoom/pan handled in JS. Visual style: solid dark grey landmasses, subtle grey border wireframe, semi-transparent ocean with radial gradient (clear center, dark edges near coastlines), dot grid background visible through ocean, theme blue hover outlines on tracked countries, green/red country shading on continent zoom. Faint globe edge ring for definition. No neon/sci-fi colors — professional grey palette matching app theme.

### 38. Globe visual styling — wireframe aesthetic, dot grid, transparent ocean
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `frontend/src/pages/Research/MarketPerformance/WorldMap.module.css`
**Type:** refactor
**Description:** Restyled the 3D globe to a clean professional look. Solid dark grey landmasses with subtle grey border wireframe. Semi-transparent ocean with radial gradient (clear center, dark edges near coastlines) that reveals a faint dot grid background. Theme blue (`#3B82F6`) hover outlines on tracked countries. Removed all neon/sci-fi coloring. Single faint globe edge ring for definition. Removed country color shading on the "All" (spinning) view.

### 39. 3D towers replace country shading on zoomed views
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`
**Type:** feature
**Description:** Replaced green/red country fill shading with isometric 3D bar towers on zoomed continent views. Green towers grow upward for positive day change, red towers grow downward for negative. Tower height uses logarithmic scaling (`log(1+x)`) so outliers at 25% are visible but don't dominate the view. Each tower has front face, right side face, and top cap for 3D effect. Towers animate rising from the ground with a staggered cascade (60ms between each) using a spring bounce curve after the zoom transition completes. Labels follow towers — start at base, slide up to tower tip as towers grow.

### 40. Globe animation polish — smooth transitions, spin ramp, cubic easing
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`
**Type:** refactor
**Description:** Smoothed all globe animations. Replaced quadratic easing with cubic ease-in-out for smoother rotation transitions. Extended zoom duration to 1.5s. Auto-spin now ramps up over 2s instead of starting at full speed. Fixed mid-animation lag caused by switching TopoJSON resolution — now uses 110m consistently. Uniform label font size (~8.67px) across all continents regardless of zoom level. Removed dead code (`GEO_URL_HI`, `changeColor`, `strokeW`, `hoverStrokeW`).

### 41. Dev mode — draggable labels and towers with position output
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`, `docs/DEV_MODE.md`
**Type:** feature
**Description:** Built-in dev mode toggle (`DEV_MODE` flag) that enables draggable labels and towers on zoomed continent views, plus drag-to-rotate and scroll-to-zoom on all views. Three output panels: green (top-right) for label offsets, yellow (bottom-left) for tower offsets, blue (top-left) for rotation/scale values. All dev UI hidden when `DEV_MODE = false`. Hand-positioned all labels and towers across all 5 continents. Added `TOWER_OFFSETS` constant and `LABEL_COORD_OVERRIDE` for Russia (Moscow centroid instead of Siberia). Updated DEV_MODE.md documentation.

### 42. Globe intro animation — planet spins out of a line
**Files:** `frontend/src/pages/Research/MarketPerformance/WorldMap.tsx`
**Type:** feature
**Description:** Added a 3-phase intro animation when the Market Performance tab opens. Phase 1 (300ms): a horizontal scanline draws outward from center. Phase 2 (400ms): the line rotates to vertical. Phase 3 (1.2s): the vertical line becomes the globe viewed edge-on — a `scaleX(0→1)` transform widens the planet while the orthographic projection spins rapidly (0.8 deg/ms decelerating to cruise speed). The spin direction matches the post-intro auto-spin. Speed is tied to data loading: if market data hasn't arrived by 85% progress, the animation near-freezes until data loads, then bursts to finish. At completion, `startSpin(true)` hands off seamlessly at cruise speed with no pause or ramp — the fast intro spin smoothly decelerates into the gentle auto-rotation. Continent animation effect suppressed during intro to prevent conflicts. Moved refs and `startSpin` declaration above Phase 3 effect to fix temporal dead zone initialization error.

### 43. International news coverage expansion + country-level classification
**Files:** `backend/services/news_service.py`, `backend/repositories/news_repo.py`, `backend/db/init_cache_db.py`
**Type:** feature
**Description:** Expanded news feed coverage from 13 to 69 RSS feeds to provide stories for all 46 countries on the Market Performance globe. Added 8 BBC regional feeds (Europe, Asia, Middle East, Africa, Latin America, Australia), 8 Google News tier-1 country feeds (UK, Germany, France, Japan, China, India, Brazil, Australia), 14 tier-2 country feeds (Canada, South Korea, Italy, Spain, Mexico, Singapore, Hong Kong, Sweden, Switzerland, Netherlands, South Africa, Saudi Arabia, Turkey, New Zealand, Indonesia, Philippines, Taiwan, Malaysia, Pakistan, Nigeria, Egypt, UAE, Israel, Colombia, Argentina), and 17 tier-3 search-based feeds for smaller markets (Nordics, Baltics, Russia, Thailand, Vietnam, Chile/Peru, Venezuela, Kenya/Morocco, Kuwait/Qatar). Added country-level keyword classifier with 56 ISO2 country rule sets — each article now gets a `countries` field (list of up to 3 ISO2 codes) alongside the existing `region` field. Country scoring uses the same title-boost weighted system with a 2.5 minimum threshold. DB schema updated with `countries` TEXT column (comma-separated ISO2 codes) with migration for existing databases. Feed fetching changed from parallel-all to batched (15 at a time with 0.5s delay) to avoid Google News rate limiting. Fetch interval increased from 90s to 120s.

### 44. macOS cross-platform support — Phase 1 (core compatibility)
**Files:** `electron/main.ts`, `backend/db/connection.py`, `scripts/bundle-python.js`, `scripts/release.sh`, `package.json`, `electron/resources/icon.icns`
**Type:** feature
**Description:** Made the codebase fully cross-platform for macOS. `getEmbeddedPythonPath()` in main.ts now platform-branches the Python binary name (`python.exe` on Windows, `python3` on macOS) instead of hardcoding `.exe`. `_default_data_dir()` in connection.py now returns the macOS-idiomatic `~/Library/Application Support/FinanceApp` on Darwin instead of falling through to the `~/.finance-app` fallback. `bundle-python.js` has a platform guard that skips Windows-only Python bundling on macOS/Linux (dev builds use system Python). `release.sh` fixed from `--win` to `--mac`. Added `package:mac` and `release:mac` scripts to root package.json. Generated `icon.icns` from existing `icon.png` for macOS packaging. Full codebase audit (270+ files) confirmed zero other blocking issues.

### 45. macOS cross-platform support — Phase 2 (polish)
**Files:** `electron/main.ts`, `frontend/src/App.tsx`, `frontend/src/pages/Settings/sections/KeyboardShortcuts.tsx`
**Type:** enhancement
**Description:** macOS UX polish. `window-all-closed` handler now keeps the app alive in the dock on macOS (standard convention) while Windows/Linux still quit immediately. Dev gallery toggle shortcut (`Ctrl+Shift+D`) now also accepts `metaKey` so Cmd+Shift+D works on macOS. Keyboard shortcut labels in Settings detect the platform and display "Cmd" instead of "Ctrl" on macOS.

### 46. One-command dev environment setup scripts
**Files:** `scripts/setup-mac.sh`, `scripts/setup-win.bat`, `README.md`, `package.json`
**Type:** feature
**Description:** Added setup scripts for one-command dev environment provisioning. `setup-mac.sh` checks for Homebrew, installs Node.js and Python 3.11+ via Homebrew if missing, installs pip and npm dependencies, and verifies critical Python imports. `setup-win.bat` does the equivalent for Windows. Both print start commands on success. Added `npm run setup` convenience script that auto-detects the OS and runs the right script. README updated with Getting Started section pointing to the setup scripts.

### 47. Country-to-globe mapping — country hint system + feed expansion + dedup fix
**Files:** `backend/services/news_service.py`, `backend/db/init_cache_db.py`, `backend/repositories/news_repo.py`
**Type:** enhancement
**Description:** The world map on the Research page shows 56 countries, but many weren't lighting up because articles from country-specific Google News feeds (e.g. `gl=HK`, `gl=LV`) don't always mention the country name in the title or snippet — so the keyword classifier never tagged them. This was a multi-part fix:

**Problem 1 — Missing `countries` column in live DB:** The `ALTER TABLE` migration in `init_cache_db.py` ran against a local relative path (`data/market_cache.db`) but the running app stores the actual DB in `%LOCALAPPDATA%\FinanceApp\market_cache.db`. Manually added the column to the live DB and the migration now targets the correct path.

**Problem 2 — No fallback when keyword matching fails:** Added a `country_hint` field to all 38 country-specific feed configs (Tier 1 + Tier 2 feeds). During RSS parsing, the hint is passed through as `_country_hint` on each article dict. The classifier applies it as a minimum-score entry, guaranteeing the country tag even when no keywords match.

**Problem 3 — Dedup discarding country hints:** When duplicate articles are removed (exact title match + 45% fuzzy word overlap), the first article seen wins and others are discarded — including their country hints from different feeds. Fixed by adding a `key_to_hints` dict that merges all `_country_hint` values from duplicate articles. During fuzzy dedup, hints are also merged (`key_to_hints[k1] |= key_to_hints.get(k2, set())`). The surviving article gets a `_country_hints` set (plural) before classification, and the classifier iterates all merged hints.

**Problem 4 — Missing feeds for globe countries:** Added 5 new dedicated Google News country feeds: Lithuania (`gl=LT`), Latvia (`gl=LV`), Estonia (`gl=EE`), Chile (`gl=CL`), Kuwait (`gl=KW`). Split the combined Chile/Peru search feed into separate feeds. Added a dedicated Colombia search feed. Improved the Kuwait search feed query (`Kuwait+economy+OR+oil+OR+market`).

**DB schema:** Added `idx_news_countries` index on the `countries` column for future filtering queries.

**Result:** Coverage went from 48/56 (86%) to 52/56 (93%). Total feeds: 76. The remaining 4 countries (LV, EE, HK, CO) are low-volume markets where Google News returns mostly the same global headlines as the US feed — they'll populate as unique articles accumulate over time.

### 48. Article tagging system — full country name tags
**Files:** `backend/services/news_service.py`, `backend/db/init_cache_db.py`, `backend/repositories/news_repo.py`
**Type:** feature
**Description:** Added a `tags` field to each news article containing 1-3 human-readable tags derived from the country classification. Instead of ISO codes (e.g. `["CN", "TH"]`), articles now also carry full names (e.g. `["China", "Thailand"]`). Added `_COUNTRY_NAMES` lookup dict (56 entries) in `news_service.py`, populated in `_classify_article()` right after country codes are set. Added `tags TEXT DEFAULT ''` column to DB schema with migration for existing DBs. Updated `news_repo.py` to store/retrieve tags as comma-separated strings. API response now includes `tags` array alongside `countries`.

### 49. Country tag pills on news articles in frontend
**Files:** `frontend/src/pages/Research/types.ts`, `frontend/src/pages/Dashboard/News/NewsWidget.tsx`, `frontend/src/pages/Dashboard/News/NewsWidget.module.css`, `frontend/src/pages/Research/News/NewsTab.tsx`, `frontend/src/pages/Research/News/NewsTab.module.css`
**Type:** feature
**Description:** Added `countries` and `tags` fields to the `NewsArticle` TypeScript interface. Rendered tag pills inline on each article row, positioned right after the "time ago" text. Styled to match the existing filter pill aesthetic (mono font, rounded border, subtle background) but smaller for inline use. Applied to both the Dashboard scrolling news widget and the Research News tab.

---

## Release Notes

v2.2.0 delivers three major areas of work:

**Holographic Boot Sequence (entries 18–22, 42):** JARVIS-inspired startup with procedural audio, 3-phase dashboard widget cascade, and engine spool-up sound design via Web Audio API.

**World Markets Globe (entries 28–41):** Interactive 3D orthographic globe with 51 country indices, isometric performance towers, drag-to-rotate, continent zoom, and animated intro sequence. Full native index coverage replacing ETF proxies.

**International News Engine (entries 43–49):** Expanded from 13 to 76 RSS feeds covering 56 countries. Country-level keyword classifier with hint system, dedup-safe hint merging, human-readable tag pills on both Dashboard and Research views.

Additional work includes SEC EDGAR dynamic auth (8–10), CSV import overhaul (15), macOS cross-platform support (44–46), one-command setup scripts (46), and 16 bug fixes across dividend display, portfolio hover cards, boot sound timing, and more.

**Platforms:** Windows (primary), macOS (supported). Cross-platform DB paths, platform-branched Python binary resolution, macOS dock behavior, and Cmd-key shortcuts all verified.

---

## Version Bump Checklist
- [ ] All `package.json` versions updated
- [ ] TypeScript compiles clean
- [ ] App runs without errors
- [ ] Packaged build succeeds
- [ ] Git commit + push
- [ ] GitHub Release created
