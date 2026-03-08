# Phase 2F — Export & Reporting System
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 1A-1G (all models), Phase 2-5 (all modules)

---

## Overview

The Export system generates professional-grade Excel and PDF outputs from
any module in the app. These are the deliverables — what you'd send to an
advisor, attach to a research note, or archive for your own records.

**Key decisions:**
- Excel (.xlsx) as primary export format (editable, formulas preserved)
- PDF as secondary format (presentation-ready, non-editable)
- Export available from Model Builder, Scanner, Portfolio, and Research
- Excel exports include live formulas where applicable
- PDF exports are formatted for print (letter size, headers/footers)
- All exports include timestamp, data source, and assumption annotations

---

## Part 1: Model Builder Exports

### 1.1 Excel Export — Valuation Model

The most complex export. Produces a multi-sheet workbook that replicates
the full model in spreadsheet form.

```
FILENAME: AAPL_DCF_2026-02-26.xlsx

SHEETS:

Sheet 1: Summary
  - Company name, ticker, date, model type
  - Intrinsic value per share (base case)
  - Current price, upside/downside
  - Scenario summary table (Bear/Base/Bull values)
  - Key assumptions summary
  - Confidence score
  - Model overview paragraph (from engine reasoning)

Sheet 2: Historical Data
  - Full financial statements (IS/BS/CF) for all available years
  - Bloomberg-style layout: years across columns, line items down rows
  - Derived metrics (margins, growth, ratios) included
  - Formatted: headers bold, numbers right-aligned, margins as percentages

Sheet 3: Assumptions
  - Every assumption with:
    - Name, value, unit
    - Source: "Auto (Assumption Engine)" or "Manual Override"
    - Engine's suggested value (if overridden)
    - Reasoning summary
  - Organized by category (Revenue, Margins, WACC, Terminal, etc.)

Sheet 4: Projection Table
  - Full 10-year projection (or however many years configured)
  - Years across columns (Year 1 through Year N + Terminal)
  - All line items: Revenue, COGS, Gross Profit, OpEx, EBIT,
    Tax, NOPAT, D&A, CapEx, ΔNWC, FCF, Discount Factor, PV of FCF
  - Terminal value calculation shown separately
  - FORMULAS PRESERVED — cells reference each other, not hard-coded values
    e.g., Revenue Year 2 = Revenue Year 1 × (1 + Growth Rate Year 2)
  - User can change an assumption in the Assumptions sheet and see
    the projection table update automatically

Sheet 5: Valuation
  - DCF waterfall breakdown:
    PV of Stage 1 FCFs
    + PV of Terminal Value (Perpetuity method)
    + PV of Terminal Value (Exit Multiple method)
    = Enterprise Value
    - Net Debt
    + Cash
    = Equity Value
    ÷ Shares Outstanding
    = Intrinsic Value per Share
  - Both terminal value methods shown with delta

Sheet 6: Scenarios
  - Full assumption set for each scenario (Bear/Base/Bull)
  - Resulting intrinsic value per scenario
  - Probability-weighted composite value
  - Scenario delta table (what changed vs base)

Sheet 7: Sensitivity
  - 2D sensitivity tables (exported from Tables sub-module)
  - Default: WACC vs Terminal Growth Rate
  - Additional: Revenue Growth vs Operating Margin
  - Tornado chart data (top 10 variables by impact)
  - Monte Carlo distribution percentiles (P5, P10, P25, P50, P75, P90, P95)

FORMATTING:
  - Company name and model type in header row of each sheet
  - Date generated in footer
  - Number formatting matches app: $X,XXX.XX for currency, XX.X% for percentages
  - Conditional formatting: green/red for gains/losses
  - Frozen panes: first column and header row frozen on data sheets
  - Column widths auto-fitted to content
  - Print area set for each sheet (landscape, fit to page width)
```

### 1.2 Model-Specific Sheet Variations

**DDM Export:**
- Sheet 4 becomes "Dividend Projection" (Stage 1/2/Terminal dividends, PV)
- Sheet 5 shows DDM-specific waterfall (PV of each stage)
- Additional: Dividend History sheet with 10Y DPS, growth, payout ratio

**Comps Export:**
- Sheet 4 becomes "Comparable Companies" (full comps table with all multiples)
- Sheet 5 shows implied valuation from each multiple
- Additional: Peer Summary sheet with similarity scores

**Revenue-Based Export:**
- Sheet 4 shows revenue projection with multiple compression path
- Sheet 5 shows exit value discounting calculation
- Additional: Growth-Adjusted Metrics sheet (Rule of 40, EV/ARR, etc.)

### 1.3 PDF Export — Valuation Report

Professional one-pager + detail pages, suitable for printing or sharing.

```
FILENAME: AAPL_DCF_Report_2026-02-26.pdf

PAGE 1: Executive Summary
  ┌─────────────────────────────────────────────────────────────┐
  │  VALUATION REPORT                                           │
  │  Apple Inc. (AAPL)                                          │
  │  Discounted Cash Flow Analysis                              │
  │  February 26, 2026                                          │
  │                                                             │
  │  INTRINSIC VALUE:  $172.00                                  │
  │  Current Price:    $182.52                                  │
  │  Upside/Downside:  -5.8%                                   │
  │  Confidence:       82/100                                   │
  │                                                             │
  │  SCENARIO RANGE                                             │
  │  Bear: $148  │  Base: $172  │  Bull: $198                   │
  │                                                             │
  │  KEY ASSUMPTIONS                                            │
  │  Revenue Growth (Yr 1):  8.2%                               │
  │  Operating Margin:       32.5%                              │
  │  WACC:                   9.2%                               │
  │  Terminal Growth:        2.5%                               │
  │                                                             │
  │  WATERFALL CHART                                            │
  │  [Rendered chart image]                                     │
  │                                                             │
  │  Generated by Finance App · Not investment advice           │
  └─────────────────────────────────────────────────────────────┘

PAGE 2: Projection Table
  Full 10-year projection in table format (landscape)

PAGE 3: Sensitivity Analysis
  2D sensitivity table + tornado chart (rendered as images)

PAGE 4: Assumption Detail
  Complete assumption list with reasoning summaries

FORMATTING:
  - Letter size (8.5" × 11"), portrait for summary, landscape for tables
  - Header: company name + model type + date on every page
  - Footer: page number + "Generated by Finance App"
  - Charts rendered as PNG images embedded in PDF
  - Clean typography: similar to app's Inter/JetBrains Mono aesthetic
  - No color except green/red for gains/losses and blue for charts
```

---

## Part 2: Scanner Exports

### 2.1 Excel Export — Screen Results

```
FILENAME: Screen_Value_Stocks_2026-02-26.xlsx

SHEETS:

Sheet 1: Results
  - All companies matching the screen, one row per company
  - Columns match what's displayed in the Scanner results table
  - Includes all visible metrics (P/E, growth, margins, etc.)
  - Sortable and filterable in Excel
  - Header row with filter dropdown auto-enabled

Sheet 2: Screen Configuration
  - Preset name (or "Custom")
  - All active filters with their values
  - Text search keywords (if any)
  - Universe used
  - Date and time of screen run
  - Total matches

FORMATTING:
  - Auto-fitted columns
  - Number formatting consistent with app
  - Conditional formatting on key metrics (green/red for growth)
  - Frozen header row
```

### 2.2 CSV Export — Screen Results

Simpler alternative for programmatic use:

```
FILENAME: Screen_Value_Stocks_2026-02-26.csv

FORMAT:
  - Standard CSV with headers
  - All visible columns from results table
  - Numbers as raw values (no formatting)
  - UTF-8 encoding
```

---

## Part 3: Portfolio Exports

### 3.1 Excel Export — Portfolio Holdings

```
FILENAME: Portfolio_2026-02-26.xlsx

SHEETS:

Sheet 1: Holdings
  - All positions with: Ticker, Name, Shares, Avg Cost, Market Price,
    Value, Cost Basis, Gain/Loss ($), Gain/Loss (%), Weight, Account
  - Summary row at bottom: total value, total cost, total gain/loss
  - Grouped by account (with subtotals per account)

Sheet 2: Performance
  - TWR and MWRR for all standard periods (1M, 3M, 6M, YTD, 1Y, etc.)
  - Benchmark comparison (portfolio vs S&P 500)
  - Risk metrics: Sharpe, Sortino, Max Drawdown, Beta, Volatility

Sheet 3: Allocation
  - Sector allocation table (sector, value, weight %)
  - Account allocation table (account, value, weight %)

Sheet 4: Transactions
  - Full transaction log for selected period
  - All fields: Date, Ticker, Type, Shares, Price, Amount, Account

Sheet 5: Dividends
  - Dividend income by ticker for current year
  - Monthly dividend totals
  - Projected annual income

FORMATTING:
  - Green/red conditional formatting on gains/losses
  - Currency formatting on all dollar values
  - Percentage formatting on weights and returns
  - Frozen header rows
```

### 3.2 PDF Export — Portfolio Summary

```
FILENAME: Portfolio_Summary_2026-02-26.pdf

PAGE 1: Portfolio Overview
  - Total value, total gain/loss, day change
  - Holdings table (condensed — top 10 positions)
  - Sector allocation pie/donut chart (rendered)
  - Performance vs benchmark chart (rendered)
  - Key risk metrics summary

PAGE 2: Full Holdings Detail
  - Complete holdings table with all positions

FORMATTING:
  - Same clean styling as model PDF reports
  - Portrait orientation
  - Charts as embedded images
```

---

## Part 4: Research Exports

### 4.1 Excel Export — Financial Statements

```
FILENAME: AAPL_Financials_2026-02-26.xlsx

SHEETS:

Sheet 1: Income Statement
  - Full IS for all available years, same layout as app
  - Computed metrics (margins, growth) included

Sheet 2: Balance Sheet
  - Full BS with computed ratios (Current Ratio, D/E, etc.)

Sheet 3: Cash Flow Statement
  - Full CF with FCF computed

Sheet 4: Ratios
  - Complete ratio dashboard data in table form
  - Profitability, Returns, Leverage, Liquidity, Valuation, Efficiency

Sheet 5: Segment Data
  - Revenue by segment (if available)
  - Geographic breakdown (if available)

FORMATTING:
  - Bloomberg-style: years across top, items down rows
  - Section headers bold
  - Negative values in parentheses and red
  - Margins and ratios as percentages
```

---

## Part 5: Export System Architecture

### 5.1 Backend Generation

All exports are generated server-side (Python backend):

```python
# backend/services/export_service.py

class ExportService:

    def export_model_excel(self, model_id: int, options: ExportOptions) -> str:
        """
        Generate Excel workbook for a valuation model.
        Returns file path to generated .xlsx file.

        Uses openpyxl library for Excel generation.
        """

    def export_model_pdf(self, model_id: int, options: ExportOptions) -> str:
        """
        Generate PDF report for a valuation model.
        Returns file path to generated .pdf file.

        Uses reportlab or weasyprint for PDF generation.
        Charts rendered as PNG via matplotlib, embedded in PDF.
        """

    def export_scanner_excel(self, results: list, config: ScreenConfig) -> str:
        """Generate Excel for scanner results."""

    def export_scanner_csv(self, results: list) -> str:
        """Generate CSV for scanner results."""

    def export_portfolio_excel(self, options: ExportOptions) -> str:
        """Generate Excel for portfolio holdings + performance."""

    def export_portfolio_pdf(self, options: ExportOptions) -> str:
        """Generate PDF portfolio summary."""

    def export_financials_excel(self, ticker: str, options: ExportOptions) -> str:
        """Generate Excel for financial statements."""
```

### 5.2 Export Options

```python
class ExportOptions(BaseModel):
    include_sensitivity: bool = True
    include_scenarios: bool = True
    include_historical: bool = True
    include_charts: bool = True        # For PDF: embed chart images
    include_reasoning: bool = False    # Include engine reasoning text
    date_range: Optional[str] = None   # For portfolio: "ytd", "1y", "all"
    file_format: str = "xlsx"          # "xlsx", "csv", "pdf"
```

### 5.3 Export Flow

```
1. User clicks [Export ▼] button in any module
2. Dropdown shows available formats: Excel, PDF, CSV (where applicable)
3. User selects format
4. (Optional) Export options dialog for complex exports (model, portfolio)
5. Frontend calls POST /api/v1/export/{type}
6. Backend generates file, returns file path
7. Electron main process opens native Save dialog
8. File copied to user's chosen location
9. Toast notification: "Exported to [filename]"

For quick exports (scanner CSV, simple tables): skip step 4, use defaults.
For complex exports (model Excel with all sheets): show options dialog.
```

### 5.4 Export Trigger Points

Where export buttons appear across the app:

```
Model Builder:
  - Toolbar button in model view: [Export ▼] → Excel / PDF
  - Available when any model has been run

Scanner:
  - Results header: [Export ▼] → Excel / CSV
  - Available when results are displayed

Portfolio:
  - Holdings header: [Export ▼] → Excel / PDF
  - Transactions tab: [Export ▼] → Excel / CSV

Research:
  - Financials tab: [Export ▼] → Excel
  - Available per company
```

---

## Part 6: Excel Formula Preservation

The key differentiator of the Excel export — models are LIVE in Excel.

```
FORMULA EXAMPLES (DCF Projection Sheet):

Cell C4 (Revenue Year 2):
  = B4 * (1 + Assumptions!B3)
  Where B4 = Revenue Year 1, Assumptions!B3 = Revenue Growth Year 2

Cell C8 (Gross Profit Year 2):
  = C4 - C5
  Where C4 = Revenue, C5 = COGS

Cell C12 (FCF Year 2):
  = C9 - C10 + C7 - C11
  Where C9 = NOPAT, C10 = CapEx, C7 = D&A, C11 = ΔNWC

Cell C14 (PV of FCF Year 2):
  = C12 / (1 + Assumptions!B15) ^ 2
  Where Assumptions!B15 = WACC

Cell B20 (Terminal Value — Perpetuity):
  = K12 * (1 + Assumptions!B16) / (Assumptions!B15 - Assumptions!B16)
  Where K12 = Terminal Year FCF, B16 = Terminal Growth, B15 = WACC

This means if you change WACC on the Assumptions sheet,
every PV calculation and the final intrinsic value update automatically.
```

Named ranges used for key assumptions to make formulas readable:
```
WACC, TerminalGrowth, TaxRate, SharesOutstanding, NetDebt, Cash
```

---

## Part 7: Performance Targets

```
Model Excel export (full 7-sheet workbook):    < 5 seconds
Model PDF export (4-page report):              < 8 seconds (chart rendering)
Scanner Excel export (500 results):            < 3 seconds
Scanner CSV export:                            < 1 second
Portfolio Excel export:                        < 3 seconds
Portfolio PDF export:                          < 5 seconds
Research financials Excel:                     < 2 seconds
```

---

*End of Phase 2F specification.*
