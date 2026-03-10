# Price Chart Upgrade — Design Doc

## Goal
Replace the Recharts-based PriceChart with a TradingView-quality interactive chart using `lightweight-charts`, plus an optional full TradingView widget embed. The chart becomes a full-page view within the GP tab.

## Architecture

### Components
- `PriceChart.tsx` — wrapper that switches between LW and TV modes
- `PriceChartLW.tsx` — lightweight-charts implementation (default)
- `PriceChartTV.tsx` — TradingView Advanced Chart widget embed (isolated, removable)
- `MeasureTool.ts` — measure overlay logic (click two points → $ and % change label)

### Layout
- Chart fills the entire `.content` area in ResearchPage (full height/width below top bar)
- Controls bar stays at top: period pills, Line/Candle, MA toggles, Measure button, date range, LW/TV toggle, Collapse

### PriceChartLW (lightweight-charts)
- Themed to match existing dark UI (bg, accent, candle colors, fonts)
- Line + Candlestick modes via `addLineSeries()` / `addCandlestickSeries()`
- Volume as histogram series on secondary pane
- 50/200 MA as line series overlays
- Native scroll-to-zoom, click-drag pan
- Current price reference line via `createPriceLine()`
- Same period/interval map as current implementation
- Date range label computed from visible range

### MeasureTool
- Toggle button in controls bar ("Measure")
- Active state: cursor changes, click point A on chart, click point B
- Draws a line between points with floating label: `+$12.40 (+3.2%)`
- Click anywhere or press Escape to dismiss
- Uses lightweight-charts `subscribeCrosshairMove` + canvas overlay

### PriceChartTV (TradingView embed)
- Loads TradingView Advanced Chart widget via script tag
- Uses TradingView's own data (not our backend)
- Themed to dark mode
- Single isolated file — remove file + toggle to roll back
- No interaction with our backend/stores beyond receiving the ticker

### Rollback Plan
PriceChartTV.tsx is fully self-contained. To remove:
1. Delete `PriceChartTV.tsx`
2. Remove the "TradingView" toggle option from PriceChart.tsx
3. No other files affected

## Implementation Steps
1. Install `lightweight-charts` package
2. Build PriceChartLW.tsx with theme + all series types
3. Build MeasureTool overlay
4. Build PriceChartTV.tsx embed
5. Update PriceChart.tsx wrapper with mode toggle
6. Update ResearchPage CSS so chart tab fills full content area
7. Test all periods, zoom/pan, measure tool, TV embed, window resize
