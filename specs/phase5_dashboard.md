# Phase 5 — Dashboard Module
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 0A-0E (foundation), Phase 2 (Scanner), Phase 3 (Portfolio)

---

## Overview

The Dashboard is the home screen — the first thing you see after the boot
sequence. It's a snapshot of everything that matters: market conditions,
your portfolio, your watchlists, and your recent work.

**Key decisions:**
- Fixed widget layout for MVP, designed for the 90% case
- Widget-based architecture: each panel is an independent component
  that can be rearranged, added, or removed in future versions
- All widgets are real-time (prices update via WebSocket during market hours)
- Multiple named watchlists, clean and functional

---

## Part 1: Dashboard Layout

### 1.1 Fixed Widget Grid

```
┌─────────────────────────────────────────────────────────────────────┐
│  ▸DASHBOARD │ MODEL BUILDER │ SCANNER │ PORTFOLIO │ RESEARCH │ ... │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────┐  ┌────────────────────────┐│
│  │        MARKET OVERVIEW              │  │   PORTFOLIO SUMMARY    ││
│  │                                    │  │                        ││
│  │  S&P 500    5,842  +0.42%          │  │  Total: $81,509        ││
│  │  NASDAQ    18,234  +0.58%          │  │  Day:   +$342 (+0.42%)││
│  │  DOW      38,421  +0.31%          │  │  Total: +$21,368      ││
│  │  10Y TSY    3.82%  -0.02           │  │         (+35.5%)       ││
│  │  VIX        14.2   -0.8            │  │                        ││
│  │  USD/EUR    1.082  +0.15%          │  │  Top: META +75.8%     ││
│  │                                    │  │  Bot: JNJ  -3.4%      ││
│  │  Market Status: ● OPEN             │  │                        ││
│  │  Closes in: 2h 34m                 │  │  [Open Portfolio →]    ││
│  └────────────────────────────────────┘  └────────────────────────┘│
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    WATCHLIST                                   │  │
│  │  [Core Holdings ▼]  [Tech Picks]  [Dividend Candidates]  [+] │  │
│  │                                                               │  │
│  │  Ticker  Name           Price     Change    P/E    EV/EBITDA │  │
│  │  NVDA    NVIDIA Corp    $875.40   +2.3%     38.2   32.1x     │  │
│  │  AVGO    Broadcom       $168.50   +1.1%     28.5   21.4x     │  │
│  │  CRM     Salesforce     $312.80   -0.4%     42.1   28.8x     │  │
│  │  PLTR    Palantir       $82.40    +3.8%     125.0  78.2x     │  │
│  │  AMD     Advanced Micro $178.20   +1.5%     45.8   35.6x     │  │
│  │                                                               │  │
│  │  [Add Ticker...]                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐│
│  │     RECENT MODELS            │  │     UPCOMING EVENTS          ││
│  │                              │  │                              ││
│  │  AAPL  DCF    $172  -5.8%   │  │  Feb 27  AAPL Ex-Dividend   ││
│  │  MSFT  DCF    $385  -7.4%   │  │  Mar 01  MSFT Earnings      ││
│  │  JNJ   DDM    $168  +9.9%   │  │  Mar 05  VZ   Ex-Dividend   ││
│  │  META  Comps  $490  -12.9%  │  │  Mar 12  JNJ  Earnings      ││
│  │                              │  │  Mar 15  NVDA Earnings      ││
│  │  Updated 2h ago              │  │                              ││
│  │  [Open Model Builder →]      │  │  [View All →]               ││
│  └──────────────────────────────┘  └──────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Grid Specifications

```
Layout: CSS Grid
  Standard width (1200-1600px):
    Row 1: Market Overview (60%) | Portfolio Summary (40%)
    Row 2: Watchlist (100%)
    Row 3: Recent Models (50%) | Upcoming Events (50%)

  Wide width (>1600px):
    Same proportions, content expands

  Compact width (<1200px):
    All widgets stack to full width, single column

Widget sizing:
  Market Overview:    min-height 180px
  Portfolio Summary:  min-height 180px
  Watchlist:          min-height 240px, max-height 400px (scrollable)
  Recent Models:      min-height 200px
  Upcoming Events:    min-height 200px

Gaps: 16px between all widgets
Padding: 24px page padding

All widgets have:
  - Dark card background (--bg-card: #1A1A1A)
  - 1px border (--border-subtle: #2A2A2A)
  - 12px border-radius
  - 16px internal padding
  - Widget title: 13px Inter Semi-Bold UPPERCASE, --text-secondary
```

### 1.3 Future Widget Customization

Architecture supports adding/rearranging widgets post-MVP:

```
WIDGET SYSTEM (internal architecture):

Each widget is a self-contained React component:
  interface DashboardWidget {
    id: string
    title: string
    component: React.FC
    defaultPosition: GridPosition
    minWidth: number
    minHeight: number
    refreshInterval: number  // ms, 0 = no auto-refresh
  }

Widget registry:
  dashboard_widgets = [
    { id: "market_overview", ... },
    { id: "portfolio_summary", ... },
    { id: "watchlist", ... },
    { id: "recent_models", ... },
    { id: "upcoming_events", ... },
    // Future widgets:
    // { id: "sector_heatmap", ... },
    // { id: "scanner_alerts", ... },
    // { id: "news_feed", ... },
    // { id: "quick_chart", ... },
  ]

Layout stored in user_settings table as JSON:
  {
    "dashboard_layout": [
      { "widget": "market_overview", "x": 0, "y": 0, "w": 7, "h": 2 },
      { "widget": "portfolio_summary", "x": 7, "y": 0, "w": 5, "h": 2 },
      ...
    ]
  }

MVP: layout is hardcoded (default layout, not editable)
Post-MVP: add drag-and-drop rearrangement, widget add/remove
```

---

## Part 2: Widget Specifications

### 2.1 Market Overview Widget

```
PURPOSE: At-a-glance market conditions

DATA:
  S&P 500:     Index level + day change + day change %
  NASDAQ:      Index level + day change + day change %
  DOW:         Index level + day change + day change %
  10Y Treasury: Yield + day change (basis points)
  VIX:         Level + day change
  USD/EUR:     Rate + day change %

  Market Status indicator:
    ● Green "OPEN"        — during regular hours (9:30-4:00 ET)
    ● Yellow "PRE-MARKET" — 4:00-9:30 AM ET
    ● Yellow "AFTER-HOURS" — 4:00-8:00 PM ET
    ● Gray "CLOSED"       — outside all trading hours
    Countdown: "Opens in Xh Ym" or "Closes in Xh Ym"

REFRESH:
  During market hours: 60s via WebSocket (same as all prices)
  Outside hours: static (last close values)

DESIGN:
  Two-column grid of market indicators
  Each indicator:
    Name (12px Inter, --text-secondary)
    Value (16px JetBrains Mono, --text-primary)
    Change (12px JetBrains Mono, green/red)
  Market status: bottom row, with colored dot
```

### 2.2 Portfolio Summary Widget

```
PURPOSE: Portfolio health at a glance

DATA:
  Total portfolio value (large, prominent)
  Day change (dollars + percent, colored)
  Total gain/loss (dollars + percent, colored)
  Best performer (ticker + gain %)
  Worst performer (ticker + gain %)

INTERACTIONS:
  Click total value → opens Portfolio module
  Click best/worst performer → opens that position in Portfolio
  [Open Portfolio →] link at bottom

DESIGN:
  Total value: 24px JetBrains Mono, --text-primary
  Day change: 16px JetBrains Mono, green/red
  Total gain: 14px JetBrains Mono, green/red
  Best/Worst: 12px, ticker in --text-primary, gain in green/red
```

### 2.3 Watchlist Widget

```
PURPOSE: Track companies you're interested in

STRUCTURE:
  - Multiple named watchlists
  - Tab bar at top of widget showing watchlist names
  - Active watchlist displayed as a mini table
  - [+] button to create new watchlist

WATCHLIST MANAGEMENT:
  Create:
    [+] → "New Watchlist" → enter name → creates empty watchlist
    Default first watchlist: "Watchlist 1" (user can rename)

  Rename:
    Double-click watchlist tab name → inline edit
    Or right-click tab → Rename

  Delete:
    Right-click tab → Delete Watchlist
    Confirmation: "Delete 'Tech Picks' and all X tickers? This cannot be undone."

  Reorder:
    Drag tabs to rearrange

WATCHLIST TABLE:
  Columns: Ticker, Name, Price, Change (% and $), P/E, EV/EBITDA
  Columns configurable per watchlist (right-click header → toggle columns)
  Additional available columns: Market Cap, Div Yield, Volume, 52W Range,
    Revenue Growth, Operating Margin, any Scanner filter metric

  Row interactions:
    Click → expand inline detail (same as Scanner inline detail)
    Double-click → open in Model Builder
    Right-click → Open in Research, Open in Model Builder,
                   Move to [other watchlist], Remove from watchlist

ADDING TICKERS:
  [Add Ticker...] input at bottom of table
  Autocomplete from Scanner universe
  Also addable from: Scanner results, Research, Model Builder (right-click)

REFRESH:
  Prices: real-time via WebSocket (Tier 1 — same priority as portfolio)
  Metrics: refresh on app launch + when user opens watchlist

LIMITS:
  Max watchlists: 20
  Max tickers per watchlist: 100
  Practical sweet spot: 3-5 watchlists, 10-30 tickers each
```

### 2.4 Recent Models Widget

```
PURPOSE: Quick access to recent valuation work

DATA:
  Last 5 models built or modified, ordered by recency

  Per model:
    Ticker
    Model type (DCF, DDM, Comps, Rev-Based)
    Base case intrinsic value
    Upside/Downside vs. current price (colored)
    Last modified timestamp

INTERACTIONS:
  Click any row → opens that model in Model Builder
  [Open Model Builder →] → navigates to Model Builder module

DESIGN:
  Compact table, no zebra striping (too small)
  Model type shown as small badge (e.g., "DCF" in --accent-subtle pill)
  Upside green, downside red
```

### 2.5 Upcoming Events Widget

```
PURPOSE: Don't miss earnings dates and ex-dividend dates

DATA:
  Next 10 events for portfolio holdings + watchlist tickers
  Sorted chronologically

  Event types:
    Earnings:     "Mar 01  MSFT  Earnings  After Close"
    Ex-Dividend:  "Feb 27  AAPL  Ex-Div    $0.25/share"
    Filing:       "Nov 03  AAPL  10-K Filed"

INTERACTIONS:
  Click event → opens company in Research module
  [View All →] → opens full calendar view in Portfolio

DESIGN:
  Simple list, each event one row
  Date: 12px JetBrains Mono, --text-secondary (fixed width for alignment)
  Ticker: 12px Inter Semi-Bold, --text-primary
  Event type: 12px Inter, --text-secondary
  Detail: 12px Inter, --text-tertiary
  Colored dot by type: ● blue for earnings, ● green for dividends, ● gray for filings
```

---

## Part 3: Empty States

### 3.1 First Launch Dashboard

On first launch, widgets show inviting empty states (per Phase 0E):

```
MARKET OVERVIEW:
  → Loads immediately with live data. Always has content.
  This is intentional — makes the app feel alive on first launch.

PORTFOLIO SUMMARY:
  ┌────────────────────────────────┐
  │        📊                      │
  │   No portfolio yet             │
  │   Add your first position      │
  │   to track performance.        │
  │                                │
  │   [Add Position]               │
  └────────────────────────────────┘

WATCHLIST:
  ┌────────────────────────────────┐
  │        👁                      │
  │   Your watchlist is empty      │
  │   Add companies you're         │
  │   interested in tracking.      │
  │                                │
  │   [Add Ticker...]              │
  └────────────────────────────────┘

RECENT MODELS:
  ┌────────────────────────────────┐
  │        📐                      │
  │   No models yet                │
  │   Build your first valuation   │
  │   model to see it here.        │
  │                                │
  │   [Open Model Builder]         │
  └────────────────────────────────┘

UPCOMING EVENTS:
  ┌────────────────────────────────┐
  │        📅                      │
  │   No upcoming events           │
  │   Events appear when you add   │
  │   companies to your portfolio  │
  │   or watchlist.                │
  └────────────────────────────────┘

Empty state icons: minimal SVG line art, --text-tertiary
Headlines: 14px Inter Semi-Bold, --text-primary
Subtext: 12px Inter, --text-secondary
CTA: secondary button style (border, --accent-primary)
```

Note: Icons shown above (📊 👁 📐 📅) are placeholders — actual implementation
uses custom minimal SVG line icons matching the app's monochrome aesthetic.
No emoji in production UI.

---

## Part 4: Dashboard Data Flow

```
Dashboard data sources:

Market Overview:
  → WebSocket price stream (indices channel)
  → market_data table for last close values
  → Treasury API for 10Y yield

Portfolio Summary:
  → portfolio_holdings table
  → WebSocket price stream for live values
  → Calculated in real-time: total value, day change, gains

Watchlist:
  → watchlists table (user-created lists)
  → watchlist_items table (ticker assignments)
  → WebSocket price stream for live prices
  → market_data table for valuation metrics

Recent Models:
  → model_outputs table (latest 5 by modified_at)
  → market_data table for current prices (upside calc)

Upcoming Events:
  → earnings_calendar table (from Yahoo Finance)
  → dividend_calendar table (from Yahoo Finance)
  → Filtered to: portfolio tickers ∪ watchlist tickers
```

---

## Part 5: Performance Targets

```
Dashboard initial load (all widgets):     < 1s after boot sequence
Market price update (WebSocket push):     < 100ms to render
Portfolio value recalculation:            < 200ms
Watchlist tab switch:                     < 100ms
Widget interaction (click/expand):        < 100ms
```

---

*End of Phase 5 specification.*
