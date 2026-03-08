# Manual Test Checklist — Finance App v1.0

## Pre-requisites
- [ ] Python 3.11+ installed and on PATH
- [ ] `pip install -r backend/requirements.txt` completed
- [ ] Internet connection available (for Yahoo Finance / SEC EDGAR data)

## Installer & Launch
- [ ] Double-click `Finance App Setup 1.0.0.exe`
- [ ] Installer completes without errors
- [ ] App launches from Start Menu shortcut
- [ ] Boot animation plays (green terminal text)
- [ ] Backend starts (no Python error dialog)

## Dashboard
- [ ] Dashboard loads with all 5 widget cards
- [ ] Market overview shows data (or graceful empty state)
- [ ] Watchlist section visible

## Model Builder
- [ ] Type "AAPL" in ticker search — results appear
- [ ] Select AAPL — detection runs, model type badges show
- [ ] Click "Generate" — assumptions populate
- [ ] Click "Run DCF" — results card shows intrinsic value
- [ ] Switch to Sensitivity tab — tornado chart renders
- [ ] Switch to Overview tab — football field renders
- [ ] Click "Save Version" — version saved confirmation

## Scanner
- [ ] Navigate to Scanner tab
- [ ] Click "Run Scan" with default filters — results table populates
- [ ] Click a row — detail panel opens

## Portfolio
- [ ] Navigate to Portfolio tab
- [ ] Empty state shows "No holdings yet" with CTA
- [ ] Click "Add Position" — modal opens

## Research
- [ ] Navigate to Research tab
- [ ] Search for AAPL — profile loads
- [ ] Switch to Financials tab — statement table renders
- [ ] Switch to Ratios tab — ratio panels render
- [ ] Switch to Filings tab — filing list loads

## Settings
- [ ] Navigate to Settings tab
- [ ] System info section shows Python version + DB paths
- [ ] Database stats section shows table counts

## Window Behavior
- [ ] Resize window — layout adjusts (no clipping)
- [ ] Maximize — restore — window state preserved
- [ ] Close app — reopen — window position/size restored

## Shutdown
- [ ] Close app via window X button
- [ ] Backend process terminates (check Task Manager)
- [ ] No zombie Python processes remain
- [ ] Reopen app — databases intact, previous data persists

## Data Persistence
- [ ] Close app completely
- [ ] Reopen — saved model version still exists
- [ ] Watchlists preserved
- [ ] Settings preserved
