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

/** Map display period to API period string */
const PERIOD_API_MAP: Record<Period, string> = {
  '1D': '1d', '5D': '5d', '1M': '1mo', '3M': '3mo', '6M': '6mo',
  'YTD': 'ytd', '1Y': '1y', '5Y': '5y', 'MAX': 'max',
};

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
      const apiPeriod = PERIOD_API_MAP[period];
      const bars = await api.get<PriceBar[]>(
        `/api/v1/companies/${ticker}/historical?period=${apiPeriod}`,
      );
      setData(Array.isArray(bars) ? bars : []);
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

  // Candlestick custom shape
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CandlestickShape = useCallback((props: any) => {
    const { x, width, payload } = props;
    if (!payload) return null;
    const { open, high, low, close } = payload;
    if (open == null || close == null || high == null || low == null) return null;

    const yScale = props.yAxis?.scale;
    if (!yScale) return null;

    const isUp = close >= open;
    const color = isUp ? 'var(--color-positive)' : 'var(--color-negative)';
    const bodyTop = yScale(Math.max(open, close));
    const bodyBottom = yScale(Math.min(open, close));
    const bodyHeight = Math.max(bodyBottom - bodyTop, 1);
    const wickTop = yScale(high);
    const wickBottom = yScale(low);
    const midX = x + width / 2;

    return (
      <g>
        <line x1={midX} y1={wickTop} x2={midX} y2={wickBottom} stroke={color} strokeWidth={1} />
        <rect x={x + 1} y={bodyTop} width={Math.max(width - 2, 2)} height={bodyHeight} fill={color} />
      </g>
    );
  }, []);

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
                domain={['auto', 'auto']}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              />
              <YAxis
                yAxisId="volume"
                orientation="right"
                tick={false}
                stroke="transparent"
                domain={[0, (max: number) => max * 4]}
              />
              <Tooltip content={<PriceTooltip />} />

              {/* Volume bars */}
              <Bar yAxisId="volume" dataKey="volume" fill="#333" fillOpacity={0.4} />

              {/* Price line or candlestick */}
              {chartType === 'line' ? (
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="close"
                  stroke="var(--accent-primary)"
                  strokeWidth={1.5}
                  dot={false}
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
