import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { api } from '../../../services/api';
import styles from './PriceChart.module.css';

interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const PERIODS = ['1D', '5D', '1M', '3M', '6M', 'YTD', '1Y', '5Y', 'MAX'] as const;
type Period = (typeof PERIODS)[number];

/** Map display period to API period + interval */
const PERIOD_API_MAP: Record<Period, { period: string; interval: string }> = {
  '1D': { period: '1d', interval: '5m' },
  '5D': { period: '5d', interval: '1h' },
  '1M': { period: '1mo', interval: '1d' },
  '3M': { period: '3mo', interval: '1d' },
  '6M': { period: '6mo', interval: '1d' },
  'YTD': { period: 'ytd', interval: '1d' },
  '1Y': { period: '1y', interval: '1d' },
  '5Y': { period: '5y', interval: '1mo' },
  'MAX': { period: 'max', interval: '3mo' },
};

/** Downsample data to at most `limit` points by taking every Nth bar. */
function downsample(bars: PriceBar[], limit: number): PriceBar[] {
  if (bars.length <= limit) return bars;
  const step = Math.ceil(bars.length / limit);
  const result: PriceBar[] = [];
  for (let i = 0; i < bars.length; i += step) {
    result.push(bars[i]!);
  }
  // Always include the last bar for current price accuracy
  if (result[result.length - 1] !== bars[bars.length - 1]) {
    result.push(bars[bars.length - 1]!);
  }
  return result;
}

function computeMA(bars: PriceBar[], window: number): Record<string, number> {
  const result: Record<string, number> = {};
  for (let i = window - 1; i < bars.length; i++) {
    let sum = 0;
    for (let j = i - window + 1; j <= i; j++) sum += (bars[j]?.close ?? 0);
    const bar = bars[i];
    if (bar) result[bar.date] = sum / window;
  }
  return result;
}

function formatDateTick(date: string): string {
  if (!date) return '';
  // Intraday format: "2026-03-06 14:30"
  if (date.includes(' ')) {
    const time = date.split(' ')[1];
    return time ?? date;
  }
  // Daily format: "2026-03-06"
  const parts = date.split('-');
  if (parts.length < 2) return date;
  const month = parts[1];
  const year = parts[0]?.slice(2);
  return `${month}/${year}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function PriceTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className={styles.priceTooltip}>
      <div className={styles.tooltipDate}>{d.date}</div>
      <div className={styles.tooltipRow}><span>Open</span><span>${d.open?.toFixed(2)}</span></div>
      <div className={styles.tooltipRow}><span>High</span><span>${d.high?.toFixed(2)}</span></div>
      <div className={styles.tooltipRow}><span>Low</span><span>${d.low?.toFixed(2)}</span></div>
      <div className={styles.tooltipRow}><span>Close</span><span>${d.close?.toFixed(2)}</span></div>
      <div className={styles.tooltipRow}><span>Volume</span><span>{d.volume?.toLocaleString()}</span></div>
    </div>
  );
}

interface Props {
  ticker: string;
}

export function PriceChart({ ticker }: Props) {
  const [period, setPeriod] = useState<Period>('1Y');
  const [showMA50, setShowMA50] = useState(false);
  const [showMA200, setShowMA200] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [data, setData] = useState<PriceBar[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!ticker) return;
    setLoading(true);
    try {
      const { period: apiPeriod, interval } = PERIOD_API_MAP[period];
      const bars = await api.get<PriceBar[]>(
        `/api/v1/companies/${ticker}/historical?period=${apiPeriod}&interval=${interval}`,
      );
      // Cap data points: 250 for long periods, 500 otherwise
      const limit = period === 'MAX' || period === '5Y' ? 250 : 500;
      setData(Array.isArray(bars) ? downsample(bars, limit) : []);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [ticker, period]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const ma50Map = useMemo(() => computeMA(data, 50), [data]);
  const ma200Map = useMemo(() => computeMA(data, 200), [data]);

  const currentPrice = data.length > 0 ? data[data.length - 1]?.close ?? 0 : 0;

  // Merge price data with MA values
  const chartData = useMemo(() => {
    return data.map((bar) => ({
      ...bar,
      ma50: ma50Map[bar.date] ?? undefined,
      ma200: ma200Map[bar.date] ?? undefined,
    }));
  }, [data, ma50Map, ma200Map]);

  // Price domain for candlestick scale
  const CHART_TOP = 8;
  const CHART_BOTTOM = 300; // ResponsiveContainer height
  const priceDomain = useMemo(() => {
    if (data.length === 0) return { min: 0, max: 1 };
    let min = Infinity;
    let max = -Infinity;
    for (const bar of data) {
      if (bar.low != null && bar.low < min) min = bar.low;
      if (bar.high != null && bar.high > max) max = bar.high;
    }
    // Add padding (~5%)
    const range = max - min || 1;
    return { min: min - range * 0.05, max: max + range * 0.05 };
  }, [data]);

  // Map price value → Y pixel (linear scale, top = max price, bottom = min price)
  const priceToY = useCallback((price: number) => {
    const { min, max } = priceDomain;
    const ratio = (price - min) / (max - min);
    return CHART_BOTTOM - CHART_TOP - (ratio * (CHART_BOTTOM - CHART_TOP)) + CHART_TOP;
  }, [priceDomain]);

  // Candlestick custom shape
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CandlestickShape = useCallback((props: any) => {
    const { x, width, payload } = props;
    if (!payload) return null;
    const { open, high, low, close } = payload;
    if (open == null || close == null || high == null || low == null) return null;

    const isUp = close >= open;
    const color = isUp ? 'var(--color-positive)' : 'var(--color-negative)';
    const bodyTop = priceToY(Math.max(open, close));
    const bodyBottom = priceToY(Math.min(open, close));
    const bodyHeight = Math.max(bodyBottom - bodyTop, 1);
    const wickTop = priceToY(high);
    const wickBottom = priceToY(low);
    const midX = x + width / 2;

    return (
      <g>
        <line x1={midX} y1={wickTop} x2={midX} y2={wickBottom} stroke={color} strokeWidth={1} />
        <rect x={x + 1} y={bodyTop} width={Math.max(width - 2, 2)} height={bodyHeight} fill={color} />
      </g>
    );
  }, [priceToY]);

  const [chartType, setChartType] = useState<'line' | 'candlestick'>('line');

  if (collapsed) {
    return (
      <div className={styles.collapsedBar ?? ''}>
        <span className={styles.collapsedLabel ?? ''}>Price Chart</span>
        <button className={styles.collapseBtn ?? ''} onClick={() => setCollapsed(false)}>Expand</button>
      </div>
    );
  }

  return (
    <div className={styles.container ?? ''}>
      {/* Controls */}
      <div className={styles.controlsBar ?? ''}>
        <div className={styles.periodGroup ?? ''}>
          {PERIODS.map((p) => (
            <button
              key={p}
              className={`${styles.periodPill ?? ''} ${period === p ? styles.periodPillActive ?? '' : ''}`}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>

        <div className={styles.chartTypeToggle ?? ''}>
          <button
            className={`${styles.typeBtn ?? ''} ${chartType === 'line' ? styles.typeBtnActive ?? '' : ''}`}
            onClick={() => setChartType('line')}
          >Line</button>
          <button
            className={`${styles.typeBtn ?? ''} ${chartType === 'candlestick' ? styles.typeBtnActive ?? '' : ''}`}
            onClick={() => setChartType('candlestick')}
          >Candle</button>
        </div>

        <label className={styles.maCheckbox ?? ''}>
          <input type="checkbox" checked={showMA50} onChange={(e) => setShowMA50(e.target.checked)} />
          <span>50 MA</span>
        </label>
        <label className={styles.maCheckbox ?? ''}>
          <input type="checkbox" checked={showMA200} onChange={(e) => setShowMA200(e.target.checked)} />
          <span>200 MA</span>
        </label>

        <button className={styles.collapseBtn ?? ''} onClick={() => setCollapsed(true)}>Collapse</button>
      </div>

      {/* Chart */}
      <div className={styles.chartWrap ?? ''}>
        {loading ? (
          <div className={styles.loading ?? ''}>Loading chart...</div>
        ) : chartData.length === 0 ? (
          <div className={styles.loading ?? ''}>No price data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#333"
                fontSize={10}
                fontFamily="var(--font-mono)"
                tickFormatter={formatDateTick}
                interval="preserveStartEnd"
              />
              <YAxis
                yAxisId="price"
                stroke="#333"
                fontSize={11}
                fontFamily="var(--font-mono)"
                domain={chartType === 'candlestick' ? [priceDomain.min, priceDomain.max] : ['auto', 'auto']}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              />
              <YAxis
                yAxisId="volume"
                orientation="right"
                tick={false}
                stroke="transparent"
                domain={[0, (max: number) => max * 4]}
              />
              <Tooltip content={<PriceTooltip />} isAnimationActive={false} />

              {/* Volume bars */}
              <Bar yAxisId="volume" dataKey="volume" fill="#333" fillOpacity={0.4} isAnimationActive={false} />

              {/* Price line or candlestick */}
              {chartType === 'line' ? (
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="close"
                  stroke="var(--accent-primary)"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              ) : (
                <Bar
                  yAxisId="price"
                  dataKey="close"
                  shape={<CandlestickShape />}
                  isAnimationActive={false}
                />
              )}

              {/* Moving averages */}
              {showMA50 && (
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="ma50"
                  stroke="#F59E0B"
                  strokeWidth={1}
                  dot={false}
                  strokeDasharray="4 4"
                  connectNulls
                  isAnimationActive={false}
                />
              )}
              {showMA200 && (
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="ma200"
                  stroke="#EF4444"
                  strokeWidth={1}
                  dot={false}
                  strokeDasharray="4 4"
                  connectNulls
                  isAnimationActive={false}
                />
              )}

              {/* Current price reference */}
              {currentPrice > 0 && (
                <ReferenceLine yAxisId="price" y={currentPrice} stroke="#555" strokeDasharray="2 2" />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
