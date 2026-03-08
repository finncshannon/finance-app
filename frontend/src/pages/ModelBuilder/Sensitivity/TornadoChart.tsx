import { useState, useEffect, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import type { TornadoResult } from '../../../types/models';
import styles from './TornadoChart.module.css';

/** Transform TornadoBar[] into the shape recharts needs for a horizontal diverging bar. */
interface TornadoChartDatum {
  name: string;
  rank: number;
  lowSpread: number;
  highSpread: number;
  spread: number;
  spreadFmt: string;
  priceAtLow: number;
  priceAtHigh: number;
  priceAtLowFmt: string;
  priceAtHighFmt: string;
  inputRange: string;
  lowInput: number;
  highInput: number;
  basePrice: number;
}

/** Format an input value – percentages if < 1, otherwise plain with suffix. */
function formatInputValue(value: number, key: string): string {
  if (value < 1) {
    return (value * 100).toFixed(1) + '%';
  }
  const suffix = key.toLowerCase().includes('multiple') ? 'x' : '';
  return value.toFixed(1) + suffix;
}

const TornadoTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className={styles.tooltip ?? ''}>
      <div className={styles.tooltipTitle ?? ''}>{d.name}</div>
      <div className={styles.tooltipRow ?? ''}><span>Low:</span><span>${d.priceAtLow.toFixed(2)}</span></div>
      <div className={styles.tooltipRow ?? ''}><span>High:</span><span>${d.priceAtHigh.toFixed(2)}</span></div>
      <div className={styles.tooltipRow ?? ''}><span>Spread:</span><span>{d.spreadFmt}</span></div>
      <div className={styles.tooltipRow ?? ''}><span>Input Range:</span><span>{d.inputRange}</span></div>
    </div>
  );
};

// Color constants
const COLOR_DOWN = '#EF4444'; // red – price decrease
const COLOR_UP = '#22C55E'; // green – price increase

export function TornadoChart() {
  const ticker = useModelStore((s) => s.activeTicker);

  const [data, setData] = useState<TornadoResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);

    api
      .post<TornadoResult>(
        `/api/v1/model-builder/${ticker}/sensitivity/tornado`,
        {},
      )
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load tornado data';
        setError(msg);
        setLoading(false);
      });
  }, [ticker]);

  // Transform bars for recharts
  const chartData = useMemo<TornadoChartDatum[]>(() => {
    if (!data) return [];
    return data.bars.map((bar, idx) => {
      const low = bar.price_at_low_input - bar.base_price;
      const high = bar.price_at_high_input - bar.base_price;
      // Always place the smaller deviation on left, larger on right
      return {
        name: '#' + (idx + 1) + ' ' + bar.variable_name,
        rank: idx + 1,
        lowSpread: Math.min(low, high),
        highSpread: Math.max(low, high),
        spread: bar.spread,
        spreadFmt: '$' + bar.spread.toFixed(2),
        priceAtLow: bar.price_at_low_input,
        priceAtHigh: bar.price_at_high_input,
        priceAtLowFmt: '$' + bar.price_at_low_input.toFixed(2),
        priceAtHighFmt: '$' + bar.price_at_high_input.toFixed(2),
        inputRange: formatInputValue(bar.low_input, bar.variable_key) + ' → ' + formatInputValue(bar.high_input, bar.variable_key),
        lowInput: bar.low_input,
        highInput: bar.high_input,
        basePrice: bar.base_price,
      };
    });
  }, [data]);

  if (!ticker) return null;

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Computing tornado analysis...</span>
      </div>
    );
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (!data || data.bars.length === 0) {
    return <div className={styles.empty}>No tornado data available.</div>;
  }

  const chartHeight = Math.max(300, data.bars.length * 40 + 60);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>Tornado Chart</span>
        <div className={styles.meta}>
          <span className={styles.metaItem}>
            Base Price: <span className={styles.metaValue}>${data.base_price.toFixed(2)}</span>
          </span>
          <span className={styles.metaItem}>
            Current: <span className={styles.metaValue}>${data.current_price.toFixed(2)}</span>
          </span>
          <span className={styles.metaItem}>
            {data.computation_time_ms.toFixed(0)}ms
          </span>
        </div>
      </div>

      <div className={styles.chartWrapper}>
        <div className={styles.legend}>
          <div className={styles.legendItem}>
            <div
              className={styles.legendSwatch}
              style={{ backgroundColor: COLOR_DOWN }}
            />
            <span>Downside</span>
          </div>
          <div className={styles.legendItem}>
            <div
              className={styles.legendSwatch}
              style={{ backgroundColor: COLOR_UP }}
            />
            <span>Upside</span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 8, right: 80, left: 8, bottom: 8 }}
            style={{ background: 'transparent' }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#262626"
              horizontal={false}
            />
            <XAxis
              type="number"
              tick={{ fill: '#A3A3A3', fontSize: 11 }}
              stroke="#333"
              tickFormatter={(v: number) =>
                `${v >= 0 ? '+' : ''}$${v.toFixed(0)}`
              }
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: '#A3A3A3', fontSize: 11 }}
              stroke="#333"
              width={180}
            />
            <Tooltip content={<TornadoTooltip />} cursor={false} />
            <ReferenceLine
              x={0}
              stroke="#F5F5F5"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              label={{ value: 'Base: $' + data.base_price.toFixed(2), fill: '#F5F5F5', fontSize: 10, position: 'top' }}
            />

            {/* Downside bars (negative side) */}
            <Bar dataKey="lowSpread" stackId="tornado" barSize={20}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`low-${index}`}
                  fill={entry.lowSpread < 0 ? COLOR_DOWN : COLOR_UP}
                />
              ))}
            </Bar>

            {/* Upside bars (positive side) */}
            <Bar dataKey="highSpread" stackId="tornado" barSize={20}>
              <LabelList
                dataKey="spreadFmt"
                position="right"
                fill="#A3A3A3"
                fontSize={10}
                fontFamily="var(--font-mono)"
              />
              {chartData.map((entry, index) => (
                <Cell
                  key={`high-${index}`}
                  fill={entry.highSpread > 0 ? COLOR_UP : COLOR_DOWN}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {chartData.length > 0 && data && (
        <div className={styles.summaryBar ?? ''}>
          Most sensitive to <strong>{data.bars[0]?.variable_name}</strong> ({chartData[0]?.spreadFmt} spread)
          {' \u00b7 '}
          Least sensitive to <strong>{data.bars[data.bars.length - 1]?.variable_name}</strong> ({chartData[chartData.length - 1]?.spreadFmt} spread)
        </div>
      )}
    </div>
  );
}
