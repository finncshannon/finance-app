# Phase 0D — UI/UX Framework & Component Library
> Designer Agent | February 23, 2026
> Status: COMPLETE — APPROVED BY FINN
> Updated March 2026 to match implemented codebase.
> Depends on: Phase 0A (Foundation), Phase 0C (API Layer)

---

## Overview

This document defines the complete visual system for the Finance App.
Every screen, component, and interaction follows these rules.

**Key decisions:**
- Dark mode only (#0D0D0D to #1A1A1A background range)
- Monochrome + blue accent (#3B82F6) + green/red for gains/losses
- Bloomberg FA-style thin navigation — three tiers, all horizontal at top
- Balanced density (Apple Stocks feel, not Bloomberg density)
- Mixed typography: monospace for numbers, sans-serif for labels
- Sharp corners on data tables, subtle rounding (4-6px) on cards/buttons
- Alternating row shading (zebra stripes) on all data tables

---

## Design Philosophy

**Apple Stocks meets Bloomberg Terminal, minus the ugly.**

- Bloomberg's functional layout and information architecture
- Apple's restraint, spacing, and polish
- Monochrome palette keeps focus on data, not decoration
- One accent color (blue) for interactivity — nothing else competes
- Financial numbers always in monospace for column alignment
- Every pixel serves a purpose — no decorative elements

---

## Color System

### Backgrounds
```
--bg-primary:      #0D0D0D    Base background (deepest)
--bg-secondary:    #141414    Card/panel background
--bg-tertiary:     #1A1A1A    Elevated surfaces, modals
--bg-hover:        #1F1F1F    Hover state on interactive areas
--bg-active:       #262626    Active/pressed state
--bg-table-odd:    #111111    Zebra stripe odd rows
--bg-table-even:   #161616    Zebra stripe even rows
--bg-table-header: #0D0D0D    Table header row
```

### Text
```
--text-primary:    #F5F5F5    Primary text (high emphasis)
--text-secondary:  #A3A3A3    Secondary text (labels, captions)
--text-tertiary:   #737373    Tertiary text (placeholders, disabled)
--text-inverse:    #0D0D0D    Text on light backgrounds (rare)
```

### Accent (Blue — the ONE color)
```
--accent-primary:  #3B82F6    Active tabs, primary buttons, links, interactive elements
--accent-hover:    #2563EB    Hover state on accent elements
--accent-pressed:  #1D4ED8    Pressed state
--accent-subtle:   #3B82F620  10% opacity — subtle highlight backgrounds
--accent-muted:    #3B82F640  25% opacity — selected row background
```

### Semantic Colors
```
--color-positive:  #22C55E    Gains, positive change, bull scenarios
--color-negative:  #EF4444    Losses, negative change, bear scenarios
--color-warning:   #F59E0B    Warnings, stale data indicators
--color-neutral:   #A3A3A3    Unchanged, flat, no movement
```

### Borders & Dividers
```
--border-subtle:   #262626    Thin lines between tab tiers, table borders
--border-medium:   #333333    Card borders, section dividers
--border-strong:   #404040    Focus rings, high-emphasis dividers
```

### Usage Rules
1. Green and red are ONLY for financial gains/losses. Never for success/error states.
2. Blue accent is ONLY for interactive elements. Never decorative.
3. Warning amber is ONLY for data staleness or system alerts.
4. No gradients anywhere. Flat colors only.
5. No shadows on dark theme — use border-subtle for depth instead.
6. Opacity variations of accent blue create selection/highlight states.

---

## Typography

### Font Families
```
--font-sans:       'Inter', -apple-system, BlinkMacSystemFont, sans-serif
--font-mono:       'JetBrains Mono', 'SF Mono', 'Fira Code', monospace
```

**Inter** — Primary UI font. Clean, highly legible at small sizes, excellent
for dense information displays. Supports tabular figures as an OpenType feature.

**JetBrains Mono** — All financial numbers, prices, percentages, table data.
Fixed-width ensures perfect column alignment. Ligatures disabled.

### Type Scale
```
Module Tab:        13px  Inter Semi-Bold     uppercase, letter-spacing 0.5px
Tab:               12px  Inter Medium        normal case
Sub-Tab:           11px  Inter Regular       normal case
Page Title:        20px  Inter Semi-Bold     used sparingly (ticker headers)
Section Header:    14px  Inter Semi-Bold
Body Text:         13px  Inter Regular
Caption/Label:     11px  Inter Regular       --text-secondary color
Table Header:      11px  Inter Semi-Bold     uppercase, letter-spacing 0.5px
Table Data:        13px  JetBrains Mono      numbers, prices, percentages
Table Label:       12px  Inter Regular       row labels in first column
Large Number:      24px  JetBrains Mono      hero metrics (intrinsic value, portfolio total)
Price Display:     18px  JetBrains Mono      current price in ticker header
Change Display:    14px  JetBrains Mono      day change with green/red coloring
```

### Number Formatting
```
Currency:          $1,234.56       (comma thousands, 2 decimal)
Large Currency:    $1.23T / $456.7B / $12.3M   (abbreviated with suffix)
Percentage:        12.45%          (2 decimal, always show sign for changes: +12.45%)
Growth Rate:       +15.2% / -3.8%  (always show sign, colored green/red)
Ratio:             1.23x           (lowercase x suffix)
Integer:           1,234,567       (comma thousands)
Share Price:       $182.52         (2 decimal always)
Shares:            15.234B         (abbreviated)
```

---

## Navigation System

### Three-Tier Horizontal Navigation

All navigation is horizontal across the top of the window.
Each tier is separated by a thin 1px line (--border-subtle).

```
┌─────────────────────────────────────────────────────────────────┐
│  DASHBOARD   MODEL BUILDER   SCANNER   PORTFOLIO   RESEARCH    │ Tier 1: Module Tabs
│─────────────────────────────────────────────────────────────────│ ← 1px line
│  Overview   Assumptions   Projections   Sensitivity   History   │ Tier 2: Tabs
│─────────────────────────────────────────────────────────────────│ ← 1px line
│  Sliders   Tornado   Monte Carlo   Tables                      │ Tier 3: Sub-Tabs
│─────────────────────────────────────────────────────────────────│ ← 1px line
│                                                                 │
│                        Content Area                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tier 1: Module Tabs
- 13px Inter Semi-Bold, UPPERCASE
- Letter-spacing 0.5px
- Inactive: --text-secondary color
- Active: --text-primary color with 2px --accent-primary underline
- Hover: --text-primary color (no underline until clicked)
- Height: 36px
- Background: --bg-primary
- Spacing between tabs: 32px

### Tier 2: Tabs (contextual per module)
- 12px Inter Medium, normal case
- Inactive: --text-tertiary color
- Active: --text-primary with 2px --accent-primary underline
- Hover: --text-secondary
- Height: 32px
- Background: --bg-secondary
- Spacing between tabs: 24px
- Only visible when the active module has sub-sections

### Tier 3: Sub-Tabs (contextual per tab)
- 11px Inter Regular, normal case
- Same active/inactive pattern as Tier 2 but smaller
- Height: 28px
- Background: --bg-secondary
- Spacing between tabs: 20px
- Only visible when the active tab has sub-sections
- Currently used by: Sensitivity tab (Sliders | Tornado | Monte Carlo | Tables)

### Tab Maps Per Module

**Dashboard:**
- No Tier 2 tabs (single view)

**Model Builder:**
- Tier 2: Overview | Assumptions | Projections | Sensitivity | History
- Tier 3 (under Sensitivity): Sliders | Tornado | Monte Carlo | Tables

**Scanner:**
- Tier 2: Screens | Filters | Results | Universe

**Portfolio:**
- Tier 2: Holdings | Performance | Allocation | Income | Transactions | Alerts

**Research:**
- Tier 2: Profile | Financials | Ratios | Filings | Segments | Peers

**Settings:**
- Tier 2: General | Data Sources | Defaults | About

---

## Ticker Header Bar

When a company is selected (in Model Builder, Research, or any company-specific view),
a ticker header bar appears below the navigation tiers.

```
┌─────────────────────────────────────────────────────────────────┐
│  AAPL  Apple Inc.  Technology · Consumer Electronics · NASDAQ   │
│  $182.52  +$1.23 (+0.68%)  │  Vol 52.3M  │  MCap $2.83T      │
│  ▲ As of 2:30 PM EST         [Model] [Research] [+ Watchlist]  │
└─────────────────────────────────────────────────────────────────┘
```

- Ticker: 18px Inter Bold, --text-primary
- Company name: 14px Inter Regular, --text-secondary
- Tags (sector, industry, exchange): 11px Inter Regular, --text-tertiary
- Price: 18px JetBrains Mono, --text-primary
- Change: 14px JetBrains Mono, --color-positive or --color-negative
- Supplementary metrics: 12px JetBrains Mono, --text-secondary
- Timestamp: 11px Inter Regular, --text-tertiary
- Background: --bg-secondary
- Bottom border: 1px --border-subtle
- Height: ~64px (two lines of information)

**Cross-Module Navigation Shortcuts (right-aligned on bottom row):**
- [Model] — navigates to this company in Model Builder (hidden if already in Model Builder)
- [Research] — navigates to this company in Research (hidden if already in Research)
- [+ Watchlist] — opens dropdown to add to a named watchlist
- Styled as secondary buttons (11px Inter Medium, --text-secondary, --border-subtle border)
- These shortcuts provide universal cross-module navigation from any context
  where a company is loaded, eliminating the need to manually switch tabs
  and re-enter a ticker

---

## Core Components

### Data Tables
The most used component. All financial data displayed in tables.

```
┌────────────────┬──────────┬──────────┬──────────┬──────────┐
│                │   2021   │   2022   │   2023   │   2024   │ Header row
├────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Revenue        │  365.8B  │  394.3B  │  383.3B  │  391.0B  │ Odd row
│ Revenue Growth │  +33.3%  │   +7.8%  │   -2.8%  │   +2.0%  │ Even row
│ Gross Profit   │  152.8B  │  170.8B  │  166.5B  │  171.0B  │ Odd row
│ Gross Margin   │  41.8%   │  43.3%   │  43.4%   │  43.7%   │ Even row
└────────────────┴──────────┴──────────┴──────────┴──────────┘
```

**Styling:**
- Header row: --bg-table-header, 11px Inter Semi-Bold UPPERCASE, --text-secondary
- Odd rows: --bg-table-odd (#111111)
- Even rows: --bg-table-even (#161616)
- Row height: 28px
- Cell padding: 8px horizontal, 4px vertical
- First column (labels): 12px Inter Regular, --text-secondary, left-aligned
- Data cells: 13px JetBrains Mono, --text-primary, right-aligned
- Growth rates / changes: colored --color-positive or --color-negative
- Column borders: 1px --border-subtle (vertical lines between years)
- Row borders: none (zebra striping provides visual separation)
- Header bottom border: 1px --border-medium
- Hover row: --bg-hover background

**Years across top, metrics down rows (Bloomberg-style, locked in 0B).**
Oldest year on left, most recent on right (locked in 1A).

### Cards
Used for summary panels on Dashboard, model overview cards.

```
┌─────────────────────────────────┐
│  DCF Model                  ▶   │
│  Intrinsic Value: $195.30       │
│  Upside: +7.0%  ▲              │
│  Last run: 2h ago               │
└─────────────────────────────────┘
```

- Background: --bg-secondary
- Border: 1px --border-subtle
- Border radius: 6px
- Padding: 16px
- Hover: border changes to --border-medium
- Click: entire card is clickable where appropriate

### Buttons

**Primary Button:**
- Background: --accent-primary
- Text: white, 13px Inter Semi-Bold
- Border radius: 4px
- Padding: 8px 16px
- Hover: --accent-hover
- Active: --accent-pressed
- Used for: "Run Model", "Save Version", "Apply"

**Secondary Button:**
- Background: transparent
- Border: 1px --border-medium
- Text: --text-secondary, 13px Inter Medium
- Border radius: 4px
- Hover: --bg-hover background
- Used for: "Cancel", "Reset", "Export"

**Danger Button:**
- Background: transparent
- Border: 1px --color-negative at 40% opacity
- Text: --color-negative, 13px Inter Medium
- Hover: --color-negative at 10% background
- Used for: "Delete Version", "Remove Position"

**Icon Button:**
- 32x32px, no background
- Icon in --text-secondary
- Hover: --bg-hover circle
- Used for: refresh, settings gear, close

### Input Fields

- Background: --bg-primary
- Border: 1px --border-medium
- Border radius: 4px
- Text: 13px JetBrains Mono (for numeric inputs) or Inter (for text)
- Padding: 8px 12px
- Focus: border becomes --accent-primary
- Placeholder: --text-tertiary
- Label above: 11px Inter Regular, --text-secondary

### Dropdown / Select

- Same styling as input fields
- Dropdown menu: --bg-tertiary background
- Menu items: 13px Inter Regular
- Hover item: --bg-hover
- Selected item: --accent-subtle background
- Border radius on menu: 4px

### Toggle Switch

- Off: --bg-hover track, --text-tertiary circle
- On: --accent-primary track, white circle
- Width: 36px, Height: 20px
- Transition: 150ms ease

### Tooltip

- Background: --bg-tertiary
- Border: 1px --border-medium
- Text: 12px Inter Regular, --text-primary
- Border radius: 4px
- Padding: 6px 10px
- Appears after 500ms hover delay
- Max width: 280px

---

## Layout Patterns

### Spacing System
Base unit: 4px. All spacing is multiples of 4.

```
--space-1:    4px     Tight: within compact elements
--space-2:    8px     Default: cell padding, small gaps
--space-3:    12px    Medium: between related elements
--space-4:    16px    Standard: card padding, section gaps
--space-5:    20px    Large: between sections
--space-6:    24px    XL: between major content blocks
--space-8:    32px    XXL: page margins, major separations
```

### Content Layout
- Page margins: 24px (--space-6) on left and right
- Top margin below navigation: 16px (--space-4)
- Between sections: 20px (--space-5)
- Max content width: none (fills available space)
- Minimum window width: 1024px
- Minimum window height: 680px

### Panel Layout
Modules often have a primary content area with a side panel.

```
┌─────────────────────────────────┬───────────────┐
│                                 │               │
│        Primary Content          │  Side Panel   │
│        (70-75% width)           │  (25-30%)     │
│                                 │               │
│                                 │               │
└─────────────────────────────────┴───────────────┘
```

- Side panels used for: assumption overrides, model summary, company info
- Resizable with drag handle: 1px --border-medium with 4px hover zone
- Collapsible: click arrow to hide/show
- Min side panel width: 240px
- Max side panel width: 400px

---

## Charts & Visualizations

### Waterfall Chart (DCF Valuation Bridge)
```
 PV of       Terminal     Enterprise    Net       Equity      Per
 Cash Flows   Value        Value        Debt      Value       Share
 ┌──────┐   ┌──────┐
 │      │   │      │   ┌──────────┐              ┌──────┐   ┌──────┐
 │ Blue │   │ Blue │   │  Gray    │   ┌──────┐   │ Blue │   │ Blue │
 │      │   │      │   │          │   │ Red  │   │      │   │      │
 └──────┘   └──────┘   └──────────┘   └──────┘   └──────┘   └──────┘
```

- Additive bars: --accent-primary (blue)
- Subtractive bars: --color-negative (red)
- Connector lines: --border-subtle (dashed)
- Labels: 11px Inter Regular above bars
- Values: 13px JetBrains Mono below bars
- Background: transparent (inherits from container)

### Tornado Chart (Sensitivity)
```
                    ◄── Bear ──┤── Base ──┤── Bull ──►
 WACC              ████████████│          │████████████
 Revenue Growth    ███████████ │          │ ██████████
 Terminal Growth   ████████    │          │    ████████
 Tax Rate          ███████     │          │     ██████
```

- Left bars (negative impact): --color-negative at 60% opacity
- Right bars (positive impact): --color-positive at 60% opacity
- Center line: --border-medium
- Labels: 12px Inter Regular, left-aligned
- Values at bar ends: 11px JetBrains Mono

### Monte Carlo Distribution
- Histogram bars: --accent-primary at 40% opacity
- Distribution curve overlay: --accent-primary solid line
- Mean line: --text-primary dashed
- Current price line: --color-warning dashed
- Percentile markers (10th, 25th, 75th, 90th): --text-tertiary dotted
- Axis labels: 11px JetBrains Mono

### Line Charts (Portfolio performance, etc.)
- Line: 2px --accent-primary
- Fill below line: --accent-subtle gradient to transparent
- Grid lines: --border-subtle at 50% opacity
- Axis labels: 11px JetBrains Mono, --text-tertiary

### Color Usage in Charts
- Primary data: --accent-primary (blue)
- Positive/gain: --color-positive (green)
- Negative/loss: --color-negative (red)
- Secondary data: --text-tertiary (gray)
- If multiple series needed: use opacity variations of blue (100%, 60%, 30%)
  before introducing new hues

---

## Loading States

### Full Loading Screen (Model Calculation)
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                                                                 │
│                                                                 │
│              Running DCF Model...                               │
│              AAPL — Apple Inc.                                  │
│                                                                 │
│         ████████████████████░░░░░░░░░░  62%                     │
│                                                                 │
│              Building projections...                            │
│                                                                 │
│                                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

- Overlays entire content area (below navigation)
- Background: --bg-primary at 95% opacity
- Title: 16px Inter Semi-Bold, --text-primary
- Subtitle: 13px Inter Regular, --text-secondary
- Progress bar: 4px height, --accent-primary fill, --bg-hover track
- Progress bar width: 320px, centered
- Progress bar border radius: 2px
- Status text below bar: 12px Inter Regular, --text-tertiary
- No cancel button (calculations are fast enough)

### Skeleton Loading (Quick data loads)
- Placeholder shapes matching expected content layout
- Animated shimmer: subtle left-to-right gradient sweep
- Color: --bg-hover with --bg-active shimmer
- Duration: 1.5s loop

### Inline Spinner
- 16px circular spinner for small loading indicators
- Color: --accent-primary
- Used next to "Last updated" timestamps during refresh

---

## Animations & Transitions

### Principles
- Fast and purposeful — no animation for decoration
- 150ms for micro-interactions (hover, focus, toggle)
- 200ms for panel transitions (tab switch, sidebar collapse)
- 300ms for page-level transitions (module switch)
- Easing: ease-out for enters, ease-in for exits

### Specific Transitions
```
Tab switch:           200ms opacity crossfade
Module switch:        300ms opacity crossfade (no slide)
Sidebar collapse:     200ms width + opacity
Dropdown open:        150ms opacity + translateY(4px → 0)
Tooltip appear:       150ms opacity (after 500ms delay)
Button press:         100ms background-color
Loading screen:       200ms opacity fade in/out
Table row hover:      100ms background-color
Card hover:           150ms border-color
Price update flash:   Green/red flash on number, 800ms fade to normal
```

### Price Update Animation
When a price changes via WebSocket:
1. Number updates immediately
2. Brief flash: text color becomes --color-positive or --color-negative
3. 800ms transition back to --text-primary
4. This draws the eye to changed values without being distracting

---

## Responsive Behavior

### Window Sizing
- Default: 1400 × 900 (remembered from last session)
- Minimum: 1024 × 680
- Full screen: supported
- Windowed: freely resizable

### Breakpoints (within the Electron window)
```
Compact:   < 1200px   Side panels collapse, tables scroll horizontally
Standard:  1200-1600px Default layout, side panels visible
Wide:      > 1600px    Extra space for wider tables, larger charts
```

### Compact mode behavior:
- Side panels auto-collapse (toggle button to show)
- Table columns may hide less-important metrics
- Charts maintain minimum useful size
- Navigation unchanged (always three tiers at top)

---

## Accessibility

- All interactive elements keyboard-navigable (Tab, Enter, Escape)
- Focus rings: 2px --accent-primary outline, 2px offset
- Minimum contrast ratio: 4.5:1 for text on backgrounds
- Green/red gains/losses also indicated by ▲/▼ arrows (not color alone)
- Screen reader labels on all interactive elements
- No information conveyed by color alone

---

## Component Inventory (Implemented)

### Shared UI Components (`components/ui/`)

| Component | Purpose |
|-----------|---------|
| Button | Standard button (primary, secondary, danger variants) |
| Card | Content card container |
| DataTable | Sortable, scrollable data table with zebra stripes |
| EmptyState | Empty data placeholder with call-to-action |
| ErrorBoundary | React class error boundary (per module) |
| ErrorState | Error display with retry action |
| ExportButton / ExportDropdown | Export action menus |
| Input | Form input (text and numeric) |
| Loading / LoadingSpinner | Loading indicators |
| Modal | Dialog overlay |
| Tabs | Tab navigation (Tier 2 / Tier 3) |
| TickerHeaderBar | Ticker + price + change header with cross-module nav |
| Tooltip | Hover tooltip |
| WatchlistPicker | Add-to-watchlist popover |

### Navigation

| Component | Purpose |
|-----------|---------|
| ModuleTabBar | Top-level 6-module tab navigation (Tier 1) |
| BootSequence | Boot animation overlay (green terminal text) |

### Pages (6 modules)

| Module | Page | Sub-pages/Tabs |
|--------|------|----------------|
| Dashboard | DashboardPage | MarketOverview, PortfolioSummary, Watchlist, RecentModels, UpcomingEvents widgets |
| Model Builder | ModelBuilderPage | Overview, Historical, Assumptions, Model (DCF/DDM/Comps/RevBased views), Sensitivity (Sliders/Tornado/MonteCarlo/DataTable), History |
| Scanner | ScannerPage | FilterPanel (FilterRow, MetricPicker, PresetSelector, TextSearchInput), ResultsTable (ResultsHeader, ContextMenu, DetailPanel) |
| Portfolio | PortfolioPage | Holdings (HoldingsTable, AddPosition, Import, PositionDetail, RecordTransaction, SummaryHeader), Performance (BenchmarkChart, ReturnMetrics, RiskMetrics, AttributionTable), Allocation (SectorDonut, Treemap, AccountBreakdown), Income (DividendChart), Transactions, Alerts (CreateAlertModal) |
| Research | ResearchPage | Profile (CompanyOverview, KeyStatsCard, ResearchNotes, UpcomingEvents), Financials (StatementTable), Ratios (RatioPanel, RatioTrendChart, DuPontDecomposition), Filings (FilingList, FilingSectionViewer, SectionNav, FilingComparison), Peers (PeerSelector, PeerTable) |
| Settings | SettingsPage | General, DataSources, ModelDefaults, Portfolio, Scanner, CacheManagement, DatabaseStats, KeyboardShortcuts, About |

### Stores (Zustand)

| Store | Purpose |
|-------|---------|
| uiStore | Active module, sub-tabs, sidebar state |
| modelStore | Active ticker, model type, detection, assumptions, outputs |
| researchStore | Selected ticker, profile, financials, ratios |
| marketStore | Live prices, WebSocket subscriptions |
| portfolioStore | Positions, transactions, performance |
| scannerStore | Filters, results, presets |
| settingsStore | User preferences, hydration |

### Services

| Service | Purpose |
|---------|---------|
| api.ts | HTTP client wrapper (get/post/put/delete with response envelope) |
| websocket.ts | WebSocket manager (prices + status channels) |
| exportService.ts | Download trigger for export endpoints |
| navigationService.ts | Cross-module navigation (ticker hand-off) |

### Design Tokens (`styles/variables.css`)

| Category | Tokens |
|----------|--------|
| Backgrounds | bg-primary (#0D0D0D), bg-secondary, bg-tertiary, bg-hover, bg-active, bg-table-odd/even/header |
| Text | text-primary (#F5F5F5), text-secondary (#A3A3A3), text-tertiary (#737373), text-inverse |
| Accent | accent-primary (#3B82F6), accent-hover, accent-pressed, accent-subtle, accent-muted |
| Semantic | color-positive (#22C55E), color-negative (#EF4444), color-warning (#F59E0B), color-neutral + subtle variants |
| UI Surfaces | text-on-accent, overlay-backdrop, shadow-elevated |
| Borders | border-subtle (#262626), border-medium (#333333), border-strong (#404040) |
| Typography | font-sans (Inter), font-mono (JetBrains Mono) |
| Spacing | space-1 (4px) through space-8 (32px) |
| Radius | radius-sm (2px), radius-md (4px), radius-lg (6px) |
| Transitions | transition-micro (150ms), transition-panel (200ms), transition-page (300ms) |

---

## File Structure

```
frontend/src/
├── styles/
│   ├── variables.css        ← All CSS custom properties (design tokens)
│   ├── reset.css            ← Normalize / reset
│   ├── fonts.css            ← Font face declarations (Inter, JetBrains Mono)
│   └── global.css           ← Global styles + animations
├── components/
│   └── ui/
│       ├── Button/           (Button.tsx + .module.css)
│       ├── Card/             (Card.tsx + .module.css)
│       ├── DataTable/        (DataTable.tsx + .module.css)
│       ├── EmptyState/       (EmptyState.tsx + .module.css)
│       ├── ErrorBoundary/    (ErrorBoundary.tsx)
│       ├── ErrorState/       (ErrorState.tsx + .module.css)
│       ├── ExportButton/     (ExportButton.tsx + ExportDropdown.tsx)
│       ├── Input/            (Input.tsx + .module.css)
│       ├── Loading/          (Loading.tsx + LoadingSpinner.tsx)
│       ├── Modal/            (Modal.tsx + .module.css)
│       ├── Tabs/             (Tabs.tsx + .module.css)
│       ├── TickerHeaderBar/  (TickerHeaderBar.tsx + .module.css)
│       ├── Tooltip/          (Tooltip.tsx + .module.css)
│       └── WatchlistPicker/  (WatchlistPicker.tsx + .module.css)
├── pages/
│   ├── Dashboard/           (DashboardPage + widget components)
│   ├── ModelBuilder/        (ModelBuilderPage + sub-pages)
│   ├── Scanner/             (ScannerPage + FilterPanel + ResultsTable)
│   ├── Portfolio/           (PortfolioPage + sub-pages)
│   ├── Research/            (ResearchPage + sub-pages)
│   └── Settings/            (SettingsPage + section components)
├── hooks/                   (useApi, useWebSocket, useLayout, etc.)
├── services/                (api.ts, websocket.ts, exportService.ts, navigationService.ts)
├── stores/                  (uiStore, modelStore, researchStore, etc.)
└── App.tsx                  (Root + ModuleTabBar + BootSequence)
```

---

## Implementation Notes for Architect

1. **CSS Custom Properties** — all design tokens defined as CSS variables
   in tokens.css. Components reference variables, never hard-coded values.
   This makes future theme adjustments trivial.

2. **No CSS framework** — no Tailwind, no Material UI. Custom CSS only.
   This gives full control over the Bloomberg-meets-Apple aesthetic.
   Component styles are co-located with component files.

3. **Chart library** — use Recharts or D3 for chart components. Charts
   must respect the color system (use CSS variables, not hard-coded colors).

4. **Font loading** — Inter and JetBrains Mono bundled with the Electron
   app (no network requests for fonts). Declared via @font-face in
   typography.css.

5. **Number formatting** — create a shared `formatNumber()` utility that
   handles all formatting rules (currency, percentage, abbreviated, etc.)
   and is used consistently across all components.

6. **Animation performance** — only animate `opacity` and `transform`
   properties for smooth 60fps. Never animate `width`, `height`, or `margin`.

7. **Table virtualization** — for tables with 100+ rows (scanner results),
   use virtual scrolling (react-window or similar) to maintain performance.
   Only render visible rows.
