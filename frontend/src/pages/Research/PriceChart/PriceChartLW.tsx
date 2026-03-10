import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
  type CandlestickData,
  type LineData,
  type HistogramData,
  type Time,
  type MouseEventParams,
  ColorType,
  CrosshairMode,
  LineStyle,
} from 'lightweight-charts';
import { api } from '../../../services/api';
import styles from './PriceChartLW.module.css';

/* ── Types ── */

interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

type Period = '1D' | '5D' | '1M' | '3M' | '6M' | 'YTD' | '1Y' | '5Y' | 'MAX';
type ChartMode = 'line' | 'candlestick';

const PERIODS: Period[] = ['1D', '5D', '1M', '3M', '6M', 'YTD', '1Y', '5Y', 'MAX'];

const PERIOD_API_MAP: Record<Period, { period: string; interval: string }> = {
  '1D': { period: '1d', interval: '1m' },
  '5D': { period: '5d', interval: '5m' },
  '1M': { period: '1mo', interval: '30m' },
  '3M': { period: '3mo', interval: '1h' },
  '6M': { period: '6mo', interval: '1d' },
  'YTD': { period: 'ytd', interval: '1d' },
  '1Y': { period: '1y', interval: '1d' },
  '5Y': { period: '5y', interval: '1wk' },
  'MAX': { period: 'max', interval: '1mo' },
};

const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

/* ── Helpers ── */

function parseTime(dateStr: string): Time {
  if (dateStr.includes(' ')) {
    return Math.floor(new Date(dateStr.replace(' ', 'T')).getTime() / 1000) as Time;
  }
  return dateStr as Time;
}

function formatDateLabel(raw: string): string {
  if (!raw) return '';
  const [datePart, timePart] = raw.split(' ');
  const parts = (datePart ?? '').split('-');
  if (parts.length < 3) return raw;
  const month = MONTH_NAMES[parseInt(parts[1]!, 10) - 1] ?? parts[1];
  const day = parseInt(parts[2]!, 10);
  const year = parts[0];
  const base = `${month} ${day}, ${year}`;
  if (timePart) return `${base} ${timePart}`;
  return base;
}

function computeSMA(bars: PriceBar[], window: number): { date: string; value: number }[] {
  const result: { date: string; value: number }[] = [];
  for (let i = window - 1; i < bars.length; i++) {
    let sum = 0;
    for (let j = i - window + 1; j <= i; j++) sum += (bars[j]?.close ?? 0);
    result.push({ date: bars[i]!.date, value: sum / window });
  }
  return result;
}

/* ── Measure ── */

interface MeasurePoint {
  price: number;
  time: Time;   // stored so we can reproject on zoom/pan
  x: number;    // pixel coords (snapshot, may go stale)
  y: number;
}

const DEAD_ZONE = 5;      // px — ignore movements smaller than this
const SNAP_DISTANCE = 30;  // px — snap to line if cursor is within this distance

/* ── Component ── */

interface Props {
  ticker: string;
}

export function PriceChartLW({ ticker }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const ma50SeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const ma200SeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);

  const [period, setPeriod] = useState<Period>('1Y');
  const [chartMode, setChartMode] = useState<ChartMode>('line');
  const [showMA50, setShowMA50] = useState(false);
  const [showMA200, setShowMA200] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rawData, setRawData] = useState<PriceBar[]>([]);

  // Measure tool state
  const [measureActive, setMeasureActive] = useState(false);
  const [measurePointA, setMeasurePointA] = useState<MeasurePoint | null>(null);
  const [measureLocked, setMeasureLocked] = useState(false); // final result locked in
  const [measureASnapped, setMeasureASnapped] = useState(true);
  const measureOverlayRef = useRef<HTMLCanvasElement>(null);
  const lastDrawnRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const lastResolvedRef = useRef<{ point: MeasurePoint; snapped: boolean } | null>(null);
  // Stored locked measurement for redrawing on zoom/pan
  const lockedMeasureRef = useRef<{
    from: MeasurePoint; to: MeasurePoint;
    fromSnapped: boolean; toSnapped: boolean;
  } | null>(null);
  // Stable ref to the redraw function (avoids closure issues in ResizeObserver)
  const redrawLockedRef = useRef<(() => void) | null>(null);
  // Date range
  const dateRange = useMemo(() => {
    if (rawData.length === 0) return '';
    const first = rawData[0]!.date;
    const last = rawData[rawData.length - 1]!.date;
    return `${formatDateLabel(first)}  —  ${formatDateLabel(last)}`;
  }, [rawData]);

  /* ── Create chart ── */
  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: '#141414' },
        textColor: '#A3A3A3',
        fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1E1E1E' },
        horzLines: { color: '#1E1E1E' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#555', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#333' },
        horzLine: { color: '#555', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#333' },
      },
      rightPriceScale: {
        borderColor: '#262626',
        scaleMargins: { top: 0.05, bottom: 0.15 },
      },
      timeScale: {
        borderColor: '#262626',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 5,
        barSpacing: 6,
        minBarSpacing: 2,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });

    chartRef.current = chart;

    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0]!.contentRect;
      chart.applyOptions({ width, height });
      const canvas = measureOverlayRef.current;
      if (canvas) {
        canvas.width = width;
        canvas.height = height;
      }
      // Redraw locked measurement after resize (canvas clear wipes it)
      requestAnimationFrame(() => {
        if (redrawLockedRef.current) redrawLockedRef.current();
      });
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      mainSeriesRef.current = null;
      volumeSeriesRef.current = null;
      ma50SeriesRef.current = null;
      ma200SeriesRef.current = null;
    };
  }, []);

  /* ── Fetch data ── */
  const fetchData = useCallback(async () => {
    if (!ticker) return;
    setLoading(true);
    try {
      const { period: apiPeriod, interval } = PERIOD_API_MAP[period];
      const bars = await api.get<PriceBar[]>(
        `/api/v1/companies/${ticker}/historical?period=${apiPeriod}&interval=${interval}`,
      );
      setRawData(Array.isArray(bars) ? bars : []);
    } catch {
      setRawData([]);
    } finally {
      setLoading(false);
    }
  }, [ticker, period]);

  useEffect(() => { fetchData(); }, [fetchData]);

  /* ── Update series when data or mode changes ── */
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || rawData.length === 0) return;

    // Remove existing series
    try {
      if (mainSeriesRef.current) chart.removeSeries(mainSeriesRef.current);
      if (volumeSeriesRef.current) chart.removeSeries(volumeSeriesRef.current);
      if (ma50SeriesRef.current) chart.removeSeries(ma50SeriesRef.current);
      if (ma200SeriesRef.current) chart.removeSeries(ma200SeriesRef.current);
    } catch { /* series might already be removed */ }
    mainSeriesRef.current = null;
    volumeSeriesRef.current = null;
    ma50SeriesRef.current = null;
    ma200SeriesRef.current = null;

    // Main series
    if (chartMode === 'candlestick') {
      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#22C55E',
        downColor: '#EF4444',
        borderUpColor: '#22C55E',
        borderDownColor: '#EF4444',
        wickUpColor: '#22C55E',
        wickDownColor: '#EF4444',
      });
      const candleData: CandlestickData[] = rawData.map((b) => ({
        time: parseTime(b.date),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }));
      series.setData(candleData);

      const lastBar = rawData[rawData.length - 1]!;
      series.createPriceLine({
        price: lastBar.close,
        color: '#555',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '',
      });

      mainSeriesRef.current = series as ISeriesApi<SeriesType>;
    } else {
      const series = chart.addSeries(LineSeries, {
        color: '#3B82F6',
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        crosshairMarkerBackgroundColor: '#3B82F6',
      });
      const lineData: LineData[] = rawData.map((b) => ({
        time: parseTime(b.date),
        value: b.close,
      }));
      series.setData(lineData);

      const lastBar = rawData[rawData.length - 1]!;
      series.createPriceLine({
        price: lastBar.close,
        color: '#555',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '',
      });

      mainSeriesRef.current = series as ISeriesApi<SeriesType>;
    }

    // Volume histogram
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    const volData: HistogramData[] = rawData.map((b) => ({
      time: parseTime(b.date),
      value: b.volume,
      color: b.close >= b.open ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.25)',
    }));
    volumeSeries.setData(volData);
    volumeSeriesRef.current = volumeSeries as ISeriesApi<SeriesType>;

    // MA50
    if (showMA50) {
      const sma50 = computeSMA(rawData, 50);
      if (sma50.length > 0) {
        const ma50Series = chart.addSeries(LineSeries, {
          color: '#F59E0B',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          crosshairMarkerVisible: false,
        });
        ma50Series.setData(sma50.map((s) => ({ time: parseTime(s.date), value: s.value })));
        ma50SeriesRef.current = ma50Series as ISeriesApi<SeriesType>;
      }
    }

    // MA200
    if (showMA200) {
      const sma200 = computeSMA(rawData, 200);
      if (sma200.length > 0) {
        const ma200Series = chart.addSeries(LineSeries, {
          color: '#EF4444',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          crosshairMarkerVisible: false,
        });
        ma200Series.setData(sma200.map((s) => ({ time: parseTime(s.date), value: s.value })));
        ma200SeriesRef.current = ma200Series as ISeriesApi<SeriesType>;
      }
    }

    chart.timeScale().fitContent();

    // Clear measure state on data change
    setMeasurePointA(null);
    setMeasureLocked(false);
    lockedMeasureRef.current = null;
    clearMeasureOverlay();
  }, [rawData, chartMode, showMA50, showMA200]);

  /* ── Measure Tool ── */

  // Change crosshair marker color during measure mode to indicate placement
  useEffect(() => {
    const series = mainSeriesRef.current;
    if (!series) return;
    try {
      if (measureActive) {
        series.applyOptions({
          crosshairMarkerVisible: true,
          crosshairMarkerRadius: 6,
          crosshairMarkerBackgroundColor: measurePointA ? '#F59E0B' : '#3B82F6',
          crosshairMarkerBorderColor: '#fff',
        });
      } else {
        series.applyOptions({
          crosshairMarkerVisible: true,
          crosshairMarkerRadius: 4,
          crosshairMarkerBackgroundColor: '#3B82F6',
          crosshairMarkerBorderColor: undefined,
        });
      }
    } catch { /* candlestick series may not support all options */ }
  }, [measureActive, measurePointA]);

  /**
   * Resolve a crosshair/click event into a MeasurePoint.
   * If the cursor is within SNAP_DISTANCE px of the line, snap to the
   * line's exact price & Y coordinate. Otherwise use raw cursor position.
   * Returns { point, snapped }.
   */
  const resolvePoint = useCallback((param: MouseEventParams<Time>): { point: MeasurePoint; snapped: boolean } | null => {
    if (!param.point) return null;
    const series = mainSeriesRef.current;
    if (!series) return null;

    const eventTime = (param.time ?? 0) as Time;
    const seriesData = param.seriesData.get(series);
    const rawY = param.point.y;
    const rawX = param.point.x;

    if (seriesData) {
      const linePrice = 'close' in seriesData
        ? (seriesData as CandlestickData).close
        : (seriesData as LineData).value;

      const snappedY = series.priceToCoordinate(linePrice);
      if (snappedY != null) {
        const dist = Math.abs(rawY - snappedY);
        if (dist <= SNAP_DISTANCE) {
          return { point: { price: linePrice, time: eventTime, x: rawX, y: snappedY }, snapped: true };
        }
      }
    }

    const offPrice = series.coordinateToPrice(rawY);
    if (offPrice == null) return null;
    return { point: { price: offPrice as number, time: eventTime, x: rawX, y: rawY }, snapped: false };
  }, []);

  /** Draw just the starting point dot immediately on first click. */
  const drawStartPoint = useCallback((pt: MeasurePoint, snapped: boolean) => {
    const canvas = measureOverlayRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (snapped) {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#3B82F6';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.8)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    } else {
      const sz = 7;
      ctx.beginPath();
      ctx.moveTo(pt.x - sz, pt.y);
      ctx.lineTo(pt.x + sz, pt.y);
      ctx.moveTo(pt.x, pt.y - sz);
      ctx.lineTo(pt.x, pt.y + sz);
      ctx.strokeStyle = 'rgba(255,255,255,0.35)';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
      ctx.strokeStyle = '#3B82F6';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Price label next to the dot
    const label = `$${pt.price.toFixed(2)}`;
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, pt.x + 10, pt.y);
  }, []);

  /** Reproject a MeasurePoint's pixel coords from its stored time/price. */
  const reprojectPoint = useCallback((pt: MeasurePoint): MeasurePoint | null => {
    const chart = chartRef.current;
    const series = mainSeriesRef.current;
    if (!chart || !series) return null;
    const newX = chart.timeScale().timeToCoordinate(pt.time);
    const newY = series.priceToCoordinate(pt.price);
    if (newX == null || newY == null) return null;
    return { ...pt, x: newX, y: newY };
  }, []);

  const clearMeasureOverlay = useCallback(() => {
    const canvas = measureOverlayRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

  /** Draw measure line + label. `preview` = live tracking (thinner, no bg pill).
   *  `toSnapped` indicates if the end point is snapped to the line. */
  const drawMeasure = useCallback((from: MeasurePoint, to: MeasurePoint, preview: boolean, fromSnapped = true, toSnapped = true) => {
    const canvas = measureOverlayRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const dollarChange = to.price - from.price;
    const pctChange = from.price !== 0 ? (dollarChange / from.price) * 100 : 0;
    const isPositive = dollarChange >= 0;
    const accentColor = isPositive ? '#22C55E' : '#EF4444';

    // Line
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.strokeStyle = preview ? 'rgba(59, 130, 246, 0.6)' : accentColor;
    ctx.lineWidth = preview ? 1 : 1.5;
    ctx.setLineDash(preview ? [6, 4] : [4, 3]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Helper: draw a snapped dot (filled circle with ring) or off-line crosshair
    const drawPoint = (pt: MeasurePoint, snapped: boolean, color: string) => {
      if (snapped) {
        // Solid dot on line with white ring
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.8)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        // Open-space indicator: small crosshair + hollow circle
        const sz = 7;
        ctx.beginPath();
        ctx.moveTo(pt.x - sz, pt.y);
        ctx.lineTo(pt.x + sz, pt.y);
        ctx.moveTo(pt.x, pt.y - sz);
        ctx.lineTo(pt.x, pt.y + sz);
        ctx.strokeStyle = 'rgba(255,255,255,0.35)';
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    };

    // Draw points
    drawPoint(from, fromSnapped, '#3B82F6');
    if (!preview) {
      drawPoint(to, toSnapped, accentColor);
    } else {
      drawPoint(to, toSnapped, 'rgba(59, 130, 246, 0.7)');
    }

    // Label — always show, but different styling for preview vs final
    const sign = dollarChange >= 0 ? '+' : '';
    const label = `${sign}$${dollarChange.toFixed(2)}  (${sign}${pctChange.toFixed(2)}%)`;

    ctx.font = '11px "JetBrains Mono", monospace';
    const metrics = ctx.measureText(label);
    const padX = 10;
    const padY = 6;
    const boxW = metrics.width + padX * 2;
    const boxH = 18 + padY * 2;

    // Position label at midpoint, offset above the line
    const midX = (from.x + to.x) / 2;
    const midY = Math.min(from.y, to.y) - 24;
    // Clamp so it doesn't go off-screen
    const clampedX = Math.max(boxW / 2 + 4, Math.min(canvas.width - boxW / 2 - 4, midX));
    const clampedY = Math.max(boxH / 2 + 4, midY);

    const bx = clampedX - boxW / 2;
    const by = clampedY - boxH / 2;

    if (preview) {
      // Subtle semi-transparent bg
      ctx.fillStyle = 'rgba(30, 30, 30, 0.85)';
      ctx.beginPath();
      ctx.roundRect(bx, by, boxW, boxH, 6);
      ctx.fill();
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
      ctx.lineWidth = 1;
      ctx.stroke();
    } else {
      // Solid bg with accent color
      ctx.fillStyle = isPositive ? 'rgba(34, 197, 94, 0.92)' : 'rgba(239, 68, 68, 0.92)';
      ctx.beginPath();
      ctx.roundRect(bx, by, boxW, boxH, 6);
      ctx.fill();
    }

    // Text
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, clampedX, clampedY);
  }, []);

  // Live preview: draw line from point A to cursor on crosshair move
  // Also continuously resolves & stores the current snap state for click to use
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const handler = (param: MouseEventParams<Time>) => {
      if (!measureActive || measureLocked) return;
      if (!param.point) return;

      const resolved = resolvePoint(param);
      if (!resolved) return;

      // Always store latest resolved position (click handler uses this)
      lastResolvedRef.current = resolved;

      // Only draw preview if point A is set
      if (!measurePointA) return;

      // Dead zone — skip redraw if cursor hasn't moved enough
      const dx = param.point.x - lastDrawnRef.current.x;
      const dy = param.point.y - lastDrawnRef.current.y;
      if (Math.abs(dx) < DEAD_ZONE && Math.abs(dy) < DEAD_ZONE) return;
      lastDrawnRef.current = { x: param.point.x, y: param.point.y };

      // Reproject point A so it tracks zoom/pan
      const currentA = reprojectPoint(measurePointA);
      if (!currentA) return;
      drawMeasure(currentA, resolved.point, true, measureASnapped, resolved.snapped);
    };

    chart.subscribeCrosshairMove(handler);
    return () => chart.unsubscribeCrosshairMove(handler);
  }, [measureActive, measurePointA, measureASnapped, measureLocked, drawMeasure, resolvePoint, reprojectPoint]);

  // Click handler for setting point A and point B
  // Uses lastResolvedRef from crosshair move (most accurate snap state)
  // Falls back to resolvePoint from click event if crosshair hasn't fired
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const handler = (param: MouseEventParams<Time>) => {
      if (!measureActive) return;
      if (!param.point || !param.time) return;

      // Prefer the last crosshair-resolved point (has accurate snap/Y)
      const resolved = lastResolvedRef.current ?? resolvePoint(param);
      if (!resolved) return;

      if (!measurePointA) {
        // First click — set point A, draw it immediately
        setMeasurePointA(resolved.point);
        setMeasureASnapped(resolved.snapped);
        drawStartPoint(resolved.point, resolved.snapped);
        lastDrawnRef.current = { x: resolved.point.x, y: resolved.point.y };
        setMeasureLocked(false);
      } else {
        // Second click — lock result and store for reprojection on zoom/pan
        const currentA = reprojectPoint(measurePointA) ?? measurePointA;
        drawMeasure(currentA, resolved.point, false, measureASnapped, resolved.snapped);
        lockedMeasureRef.current = {
          from: currentA, to: resolved.point,
          fromSnapped: measureASnapped, toSnapped: resolved.snapped,
        };
        setMeasurePointA(null);
        setMeasureActive(false);
        setMeasureLocked(true);
      }
    };

    chart.subscribeClick(handler);
    return () => chart.unsubscribeClick(handler);
  }, [measureActive, measurePointA, measureASnapped, drawMeasure, drawStartPoint, resolvePoint, reprojectPoint]);

  // Redraw locked measurement when chart is zoomed/panned/resized
  const redrawLocked = useCallback(() => {
    const locked = lockedMeasureRef.current;
    if (!locked) return;

    const newFrom = reprojectPoint(locked.from);
    const newTo = reprojectPoint(locked.to);
    if (newFrom && newTo) {
      drawMeasure(newFrom, newTo, false, locked.fromSnapped, locked.toSnapped);
    } else {
      clearMeasureOverlay();
    }
  }, [reprojectPoint, drawMeasure, clearMeasureOverlay]);

  // Keep the ref current so ResizeObserver can call it without stale closures
  redrawLockedRef.current = redrawLocked;

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    let rafId = 0;
    const onRangeChange = () => {
      // Use rAF so price scale has finished auto-adjusting after time range change
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(redrawLocked);
    };

    chart.timeScale().subscribeVisibleLogicalRangeChange(onRangeChange);
    return () => {
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRangeChange);
      cancelAnimationFrame(rafId);
    };
  }, [redrawLocked]);

  // Escape to cancel measure
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMeasureActive(false);
        setMeasurePointA(null);
        setMeasureLocked(false);
        lockedMeasureRef.current = null;
        lastResolvedRef.current = null;
        clearMeasureOverlay();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [clearMeasureOverlay]);

  const toggleMeasure = () => {
    if (measureActive) {
      setMeasureActive(false);
      setMeasurePointA(null);
      lastResolvedRef.current = null;
    } else {
      setMeasureLocked(false);
      lockedMeasureRef.current = null;
      lastResolvedRef.current = null;
      clearMeasureOverlay();
      setMeasureActive(true);
    }
  };

  return (
    <div className={styles.wrapper}>
      {/* Controls */}
      <div className={styles.controlsBar}>
        <div className={styles.periodGroup}>
          {PERIODS.map((p) => (
            <button
              key={p}
              className={`${styles.periodPill} ${period === p ? styles.periodPillActive : ''}`}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>

        <div className={styles.chartTypeToggle}>
          <button
            className={`${styles.typeBtn} ${chartMode === 'line' ? styles.typeBtnActive : ''}`}
            onClick={() => setChartMode('line')}
          >Line</button>
          <button
            className={`${styles.typeBtn} ${chartMode === 'candlestick' ? styles.typeBtnActive : ''}`}
            onClick={() => setChartMode('candlestick')}
          >Candle</button>
        </div>

        <label className={styles.maCheckbox}>
          <input type="checkbox" checked={showMA50} onChange={(e) => setShowMA50(e.target.checked)} />
          <span>50 MA</span>
        </label>
        <label className={styles.maCheckbox}>
          <input type="checkbox" checked={showMA200} onChange={(e) => setShowMA200(e.target.checked)} />
          <span>200 MA</span>
        </label>

        <button
          className={`${styles.measureBtn} ${measureActive ? styles.measureBtnActive : ''}`}
          onClick={toggleMeasure}
          title="Measure: click two points to see $ and % change"
        >
          {measureActive ? (measurePointA ? 'Click end point' : 'Click start point') : 'Measure'}
        </button>

        {dateRange && <span className={styles.dateRange}>{dateRange}</span>}

        <button
          className={styles.resetBtn}
          onClick={() => chartRef.current?.timeScale().fitContent()}
          title="Reset zoom"
        >
          Reset
        </button>
      </div>

      {/* Chart area */}
      <div className={styles.chartArea}>
        {loading && <div className={styles.loadingOverlay}>Loading...</div>}
        <div
          ref={chartContainerRef}
          className={`${styles.chartContainer} ${measureActive ? styles.chartMeasuring : ''}`}
        />
        <canvas
          ref={measureOverlayRef}
          className={styles.measureCanvas}
        />
      </div>
    </div>
  );
}
