# Spectre v2.2.0 — Release Notes

---

## New Features

---

### Interactive 3D World Markets Globe

A fully interactive 3D orthographic globe is now the centerpiece of the Market Performance tab in Research. Tracks 51 country stock market indices across 5 continents using native exchange data — no ETF proxies.

**Globe Visualization**
- 3D orthographic projection with auto-spin on the default "All" view, rotating gently at ~0.12°/frame
- Drag-to-rotate with 0.3 sensitivity and ±70° latitude clamp for manual exploration
- Professional visual style: solid dark grey landmasses, subtle wireframe borders, semi-transparent ocean with radial gradient, faint dot grid background visible through the ocean, and theme blue hover outlines on tracked countries
- Globe edge ring for definition against the dark UI

**Continent Zoom & 3D Performance Towers**
- Selecting a continent filter (Europe, Asia, Americas, Middle East & Africa, Oceania) smoothly zooms and pans to that region with a 1.5s cubic ease-in-out animated transition
- Zoomed views display isometric 3D bar towers on each country — green towers rise for positive daily change, red towers extend downward for negative. Tower height uses logarithmic scaling so outliers are visible without dominating the view
- Towers animate with a staggered cascade (60ms between each) using a spring bounce curve after zoom completes. Country labels slide from base to tower tip as towers grow
- "All" continent tab shows 5 summary cards with averaged gain/loss per continent. Clicking a continent card navigates to its detail view

**Country Coverage & Data**
- 51 countries across 5 continents, all using native stock market indices (^FTSE, ^GDAXI, ^N225, ^BVSP, 000001.SS, etc.) for accurate country-level performance data
- Full country name labels with dark stroke outlines on zoomed views, hand-positioned with white leader lines for small countries (Belgium, Netherlands, Israel, etc.)
- Country cards display name as primary label with index ticker and daily price change below in a 5-wide responsive grid

**Globe Intro Animation**
- 3-phase cinematic intro when the Market Performance tab opens: a horizontal scanline draws outward from center (300ms), rotates to vertical (400ms), then expands into the full globe with a rapid spin that decelerates smoothly into the auto-rotation cruise speed (1.2s)
- Animation speed is data-aware: if market data hasn't arrived by 85% progress, the animation near-freezes until data loads, then bursts to finish

**3-Month Mini Chart**
- Compact line chart in the Market Performance detail panel for any selected index, positioned between the Price and Performance summary widgets
- Minimal dark theme with subtle grid and blue price line using `lightweight-charts`

**Market Performance Layout**
- Restructured from stacked horizontal sections to a 3-column vertical layout: Indices (left), World Markets with globe (center), Sectors (right)
- Fixed day change percentage display that was showing 0.00% due to missing decimal-to-percentage conversion from the backend

---

### International News Engine

Expanded from 13 to 76 RSS feeds, covering 56 countries. Every article is now classified at the country level and tagged with human-readable labels that appear as inline pills across the UI.

**Feed Coverage**
- 8 BBC regional feeds (Europe, Asia, Middle East, Africa, Latin America, Australia)
- 8 Google News tier-1 country feeds (UK, Germany, France, Japan, China, India, Brazil, Australia)
- 19 tier-2 dedicated country feeds (Canada, South Korea, Italy, Spain, Mexico, Singapore, Hong Kong, Sweden, Switzerland, Netherlands, South Africa, Saudi Arabia, Turkey, New Zealand, Lithuania, Latvia, Estonia, Chile, Kuwait)
- 17 tier-3 search-based feeds for smaller markets (Nordics, Baltics, Russia, Thailand, Vietnam, Peru, Venezuela, Colombia, Kenya, Morocco, Egypt, UAE, Israel, and others)
- Feed fetching now batched (15 at a time with 0.5s delay) to avoid Google News rate limiting. Fetch interval increased from 90s to 120s

**Country-Level Classification**
- 56 ISO2 country rule sets using weighted keyword matching with the same title-boost scoring system as the category classifier (2.5 minimum threshold)
- Each article receives a `countries` field (up to 3 ISO2 codes) alongside the existing `region` field
- Country hint system for feeds where articles don't mention the country name in the title or snippet (common with country-specific Google News feeds like `gl=HK`, `gl=LV`). Hints are passed through from feed config and applied as minimum-score entries during classification
- Dedup-safe hint merging: when duplicate articles are removed (exact title match + 45% fuzzy word overlap), country hints from all duplicate sources are merged before the surviving article is classified

**Article Tags**
- Human-readable tags derived from country classification (e.g., "China", "Thailand" instead of "CN", "TH")
- 56-entry country name lookup, populated during classification
- Tags stored as comma-separated strings in the database and returned as arrays in the API response
- Tag pills rendered inline on each article row (after "time ago" text) in both the Dashboard scrolling news widget and the Research News tab, styled to match the existing filter pill aesthetic

**Country Coverage Result:** 52 of 56 globe countries (93%) actively populate with tagged articles. The remaining 4 (Latvia, Estonia, Hong Kong, Colombia) are low-volume markets where dedicated articles accumulate over time.

---

### Holographic Boot Sequence

A cinematic startup experience inspired by JARVIS and sci-fi HUD interfaces, with fully procedural audio.

**Visual Sequence**
- Five-phase animation: black screen → frame draw (clip-path reveal with corner brackets) → identity (typewriter "SPECTRE" title at 48px with 12px letter-spacing) → system initialization → hard cut to dashboard
- Frontend loads before the backend starts so the boot sequence is visible immediately. Pages are deferred until the backend health check passes

**Procedural Audio**
- Engine spool-up with 7 audio layers via Web Audio API: dual detuned sawtooth sub-bass (30/32Hz) for V8 rumble, square wave exhaust growl, cross-plane crank LFO firing pulse, turbo compressor noise (bandpass-swept 400→2200Hz), distant air rush, and low-pass exhaust noise
- High-frequency ascending digital pings (4000Hz+, 8-12ms) step up 150Hz per ping across all 23 boot events, driving the spool-up
- Engine reaches peak in 5 seconds, holds briefly on dashboard, then crossfades over 3 seconds into a system idle hum (55Hz + 110Hz sines with low-pass ventilation noise) that lingers 8 seconds before fading to silence
- All audio layers managed through a single `engineMaster` GainNode for clean fade-out

**Dashboard Widget Cascade**
- 3-phase loading animation on first boot: backplate shells pop in one by one (250ms stagger), widget headers build top-to-bottom (200ms stagger), then data populates in a fixed order (Market → Portfolio → Watchlist → Upcoming Events → Recent Models) with randomized timing gaps (150–500ms) for natural overlap
- Glass-styled backplates (`rgba(20,20,20,0.85)` + `backdrop-filter: blur(8px)`) consistent across all stages
- Living UI effects: dashboard widget glow pulses and active tab glow on the module tab bar
- Animation state tracked in Zustand to skip on subsequent visits within the same session

---

### Dashboard Live News Ticker

A real-time scrolling news feed integrated directly into the Dashboard.

- Fetches all articles from the last 24 hours (up to 2,000) sorted newest-first, matching the "All News" mode in Research
- Auto-scrolls upward using GPU-accelerated CSS `translateY` animation. Scroll pauses on hover so users can read and click articles
- Mouse wheel support for manual scrolling with 1:1 input. Auto-scroll resumes after 5 seconds of inactivity
- Seamless infinite loop: articles render twice so the second set fills in as the first scrolls past. Manual wheel scrolling wraps at both ends
- Pulsing green "LIVE" indicator in the widget header
- Dashboard grid restructured to a hybrid flex layout: left column (Market + News), right column (Portfolio + Events), with Watchlist and Recent Models full-width below. Responsive breakpoint collapses to single column at 1200px. Column heights balanced so both sides match

---

### macOS Cross-Platform Support

Spectre now runs natively on macOS alongside Windows from a single codebase. Full codebase audit of 270+ files confirmed zero blocking compatibility issues in the backend or frontend.

**Core Compatibility**
- `getEmbeddedPythonPath()` in the Electron main process now platform-branches the Python binary name (`python.exe` on Windows, `python3` on macOS) instead of hardcoding `.exe`
- Database storage uses the macOS-idiomatic path `~/Library/Application Support/FinanceApp` on Darwin, `%LOCALAPPDATA%\FinanceApp` on Windows
- Python bundler (`bundle-python.js`) has a platform guard — macOS dev builds use system Python via the existing fallback logic in `electron/main.ts`
- Build scripts: `package:mac` and `release:mac` added to `package.json`. `release.sh` corrected to target `--mac`
- macOS `.icns` icon generated from existing `.png` for Electron Builder DMG packaging
- `electron-builder.yml` already had `mac` and `dmg` targets configured for x64 + arm64

**macOS UX Polish**
- `window-all-closed` handler keeps the app alive in the dock on macOS (standard convention) while Windows/Linux still quit immediately
- Dev gallery toggle shortcut accepts both `Ctrl+Shift+D` (Windows) and `Cmd+Shift+D` (macOS)
- Keyboard shortcut labels in Settings detect the platform and display "Cmd" on macOS, "Ctrl" on Windows

**One-Command Developer Setup**
- `scripts/setup-mac.sh`: checks for Homebrew, installs Node.js 18+ and Python 3.11+ via Homebrew if missing, installs all pip and npm dependencies, verifies critical Python imports, and prints start commands
- `scripts/setup-win.bat`: equivalent for Windows
- `npm run setup`: cross-platform convenience script that auto-detects the OS and runs the appropriate setup script
- README updated with Getting Started section

---

## Enhancements

---

### Research Module

**Search Autocomplete**
- Replaced the manual ticker-only input with a live autocomplete search that matches both ticker symbols and full company names. Suggestions appear after the first keystroke with ticker shown in blue alongside the company name. Supports keyboard navigation (arrow keys + Enter), 150ms debounce, and outside-click dismiss. Backend search prioritizes exact ticker matches, then ticker prefix, then name substring

**SEC EDGAR Integration**
- User-Agent is now built dynamically from the email configured in Settings (format: `Spectre <email>`). Hardcoded email removed. Frontend shows a warning banner in the Filings tab and validates email format in Settings when no email is configured. All SEC-facing endpoints return a clear `SEC_EMAIL_REQUIRED` error code
- Fixed "undeclared automated tool" blocking from SEC: added per-request `Host` header matching the target domain, corrected User-Agent format, added detection for SEC's block page (HTTP 200 with error HTML), and 429 retry with backoff
- 10-Q filing parser now correctly matches section headers that use HTML entities (`&#160;`) instead of regular spaces. Extended section patterns to cover 10-Q items (Financial Statements, MD&A, Controls and Procedures). Parser finds 5 sections for both 10-K and 10-Q filings

---

### Portfolio Module

**Hover Card**
- Fixed the ticker hover popup in Holdings that was broken in two ways: it fetched from a non-existent API endpoint (returning no data), and it disappeared immediately when moving the mouse toward it. Now fetches from the correct company and quote endpoints in parallel, with coordinated hover timing using cancellable close timers. Card shows current price with day change percentage
- Added 1-year price change percentage to the hover card metric grid, computed internally from first and last close prices in 1Y daily historical bars to avoid cross-source mismatches

**CSV Import**
- Overhauled the transaction import parser to handle Fidelity exports and other real-world CSV formats. Fixes include: BOM character stripping, leading blank line removal, trailing footer trimming, header normalization that strips unit suffixes like `($)` and `(%)`, `Run Date` recognition as a date column, and expanded transaction type inference (`YOU BOUGHT`/`YOU SOLD`, `REINVEST`, `DISTRIBUTION`). Error messages now show which columns matched vs didn't. Frontend manual column mapping shows transaction-specific fields when importing transactions

**Import Preview**
- Added per-row removal in the import preview (step 3) for both positions and transactions, allowing users to exclude individual rows before executing the import

**Clear All**
- Added a "Clear All" button to the Holdings toolbar that deletes all portfolio positions in one action with confirmation dialog. Backend adds a cascading delete endpoint

---

### News Classifier

- Fixed title boost double-counting: title keywords were scored at 3x instead of the documented 2x. Refactored to score title and snippet separately with proper weighting
- Fixed `\b` word boundary failure on keywords ending in non-word characters (e.g., `u.s.`, `opec+`). Pattern builder now uses a `(?=\s|$)` lookahead for these cases
- Removed `"who"` from Healthcare keywords (matched the English pronoun in every article) and replaced with `"world health organization"` at higher weight
- Removed 16 generic keywords with weight 1.0 that caused false category matches across Technology, Markets, Sports, Economy, Politics, and Entertainment. Disambiguated `"bp"` to `"bp plc"` and reduced `"shell"` weight

---

## Bug Fixes

---

### Electron / Startup
- Python import verification timeout increased from 10 seconds to 30 seconds to handle cold starts with antivirus scanning or disk cache misses
- S&P 500 and Russell 3000 curated universes now pre-load synchronously before the health check passes, fixing a race condition where the frontend could connect before the companies table was populated
- Backend logging configuration added — `finance_app` logger output was silently dropped due to missing handler. Now routes through stderr for visibility in Electron's process pipes
- Sound engine master gain fix: `fadeOutBootHum()` referenced removed variables causing the engine sound to never stop and the dashboard to not load. Replaced with single-node fade through `engineMaster` GainNode. Fixed noise burst during transition caused by uninitialized gain value

### Data Providers
- Dividend yield display fixed: Yahoo Finance's `dividendYield` field was being stored raw for yields under 1%, causing display values 100x too high (e.g., 40% instead of 0.4%). Now uses `trailingAnnualDividendYield` as primary source with proper fallback normalization
- Market Performance day change percentage was displaying 0.00% due to missing decimal-to-percentage conversion (`-0.0016` displayed as `0.00%` instead of `-0.16%`)
- MiniChart data loading fixed: the API wrapper unwraps the response envelope, so the fetch was looking for `res.bars` on a flat array

### Database
- News `countries` column migration now targets the correct live database path (`%LOCALAPPDATA%\FinanceApp\market_cache.db`) instead of the relative dev path (`data/market_cache.db`)

---

## Technical Notes

- **Platforms:** Windows (primary), macOS (supported). Single codebase builds for both via Electron Builder
- **Python:** 3.11+ required. Windows uses bundled embeddable Python; macOS uses system Python (Homebrew recommended)
- **Total RSS Feeds:** 76 (up from 13)
- **Country Coverage:** 51 native stock market indices, 56 news classification rule sets
- **Codebase Audit:** 270+ files verified cross-platform compatible
