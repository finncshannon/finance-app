import { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import type { BenchmarkResult, DailySnapshot } from '../types';
import { fmtPct, gainColor } from '../types';
import styles from './BenchmarkChart.module.css';

interface Props {
  benchmark: BenchmarkResult | null;
}

function normalize(series: DailySnapshot[]): { date: string; value: number }[] {
  if (series.length === 0) return [];
  const first = series[0]!.portfolio_value;
  if (first === 0) return series.map((s) => ({ date: s.date, value: 100 }));
  return series.map((s) => ({
    date: s.date,
    value: 100 * (s.portfolio_value / first),
  }));
}

function formatDateTick(dateStr: string): string {
  if (!dateStr) return '';
  // Intraday format: "2026-03-06 14:30"
  if (dateStr.includes(' ')) {
    const [datePart, time] = dateStr.split(' ');
    const day = datePart?.split('-')[2];
    return `${day} ${time}`;
  }
  // Daily format
  const d = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[d.getMonth()]} ${d.getFullYear().toString().slice(2)}`;
}

function BenchmarkTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const port = payload.find((p: any) => p.dataKey === 'portfolio')?.value;
  const bench = payload.find((p: any) => p.dataKey === 'benchmark')?.value;
  const alpha = port != null && bench != null ? port - bench : null;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipDate}>{label}</div>
      {port != null && (
        <div className={styles.tooltipRow}>
          <span className={styles.tooltipDot} style={{ background: 'var(--accent-primary)' }} />
          <span>Portfolio:</span><span className={styles.tooltipValue}>{port.toFixed(1)}</span>
        </div>
      )}
      {bench != null && (
        <div className={styles.tooltipRow}>
          <span className={styles.tooltipDot} style={{ background: '#F59E0B' }} />
          <span>Benchmark:</span><span className={styles.tooltipValue}>{bench.toFixed(1)}</span>
        </div>
      )}
      {alpha != null && (
        <div className={styles.tooltipRow}>
          <span className={styles.tooltipDot} style={{ background: alpha >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }} />
          <span>Alpha:</span>
          <span className={styles.tooltipValue} style={{ color: alpha >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}>
            {alpha >= 0 ? '+' : ''}{alpha.toFixed(1)}
          </span>
        </div>
      )}
    </div>
  );
}

export function BenchmarkChart({ benchmark }: Props) {
  if (!benchmark) {
    return <div className={styles.empty}>No benchmark data available</div>;
  }

  const chartData = useMemo(() => {
    const portNorm = normalize(benchmark.portfolio_series);
    const benchNorm = normalize(benchmark.benchmark_series);

    // Merge by date key so both series align properly
    const dateMap = new Map<string, { portfolio: number | null; benchmark: number | null }>();
    for (const p of portNorm) {
      dateMap.set(p.date, { portfolio: p.value, benchmark: null });
    }
    for (const b of benchNorm) {
      const existing = dateMap.get(b.date);
      if (existing) {
        existing.benchmark = b.value;
      } else {
        dateMap.set(b.date, { portfolio: null, benchmark: b.value });
      }
    }

    return Array.from(dateMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([d, vals]) => ({ date: d, portfolio: vals.portfolio, benchmark: vals.benchmark }));
  }, [benchmark]);

  if (chartData.length === 0) {
    return <div className={styles.empty}>Insufficient data for chart</div>;
  }

  // Period summary table
  const periodEntries = Object.entries(benchmark.periods);

  return (
    <div className={styles.container}>
      <div className={styles.chartWrapper}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: '#A3A3A3', fontSize: 10 }}
              stroke="#333"
              tickFormatter={formatDateTick}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#A3A3A3', fontSize: 11 }}
              stroke="#333"
              tickFormatter={(v) => `${v.toFixed(0)}`}
              domain={['dataMin - 2', 'dataMax + 2']}
            />
            <Tooltip content={<BenchmarkTooltip />} />
            <Legend verticalAlign="top" height={30} />
            <ReferenceLine
              y={100}
              stroke="#555"
              strokeDasharray="3 3"
              label={{ value: 'Start', fill: '#666', fontSize: 10 }}
            />
            <Line
              type="monotone"
              dataKey="portfolio"
              name="Portfolio"
              stroke="var(--accent-primary)"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="benchmark"
              name={`${benchmark.benchmark_ticker} Benchmark`}
              stroke="#F59E0B"
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="4 4"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary table */}
      {periodEntries.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Period</th>
              <th className={styles.thRight}>Portfolio</th>
              <th className={styles.thRight}>Benchmark</th>
              <th className={styles.thRight}>Alpha</th>
            </tr>
          </thead>
          <tbody>
            {periodEntries.map(([key, p]) => (
              <tr key={key} className={styles.tr}>
                <td className={styles.td}>{key}</td>
                <td className={styles.tdRight} style={{ color: gainColor(p.portfolio) }}>
                  {fmtPct(p.portfolio)}
                </td>
                <td className={styles.tdRight} style={{ color: gainColor(p.benchmark) }}>
                  {fmtPct(p.benchmark)}
                </td>
                <td className={styles.tdRight} style={{ color: gainColor(p.alpha) }}>
                  {fmtPct(p.alpha)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
