import type { PerformanceResult } from '../types';
import { fmtPct } from '../types';
import styles from './RiskMetrics.module.css';

interface Props {
  performance: PerformanceResult | null;
}

type Sentiment = 'positive' | 'negative' | 'neutral';

interface MetricRow {
  label: string;
  value: string;
  interpretation: string;
  sentiment: Sentiment;
}

function fmt2(n: number | null): string {
  if (n == null) return '\u2014';
  return n.toFixed(2);
}

function betaInterpretation(beta: number | null): { text: string; sentiment: Sentiment } {
  if (beta == null) return { text: '\u2014', sentiment: 'neutral' };
  if (beta < 0.8) return { text: 'Defensive', sentiment: 'positive' };
  if (beta <= 1.2) return { text: 'Market-aligned', sentiment: 'neutral' };
  return { text: 'Aggressive', sentiment: 'negative' };
}

function sharpeInterpretation(val: number | null): { text: string; sentiment: Sentiment } {
  if (val == null) return { text: '\u2014', sentiment: 'neutral' };
  if (val >= 1.0) return { text: 'Strong risk-adjusted returns', sentiment: 'positive' };
  if (val >= 0.5) return { text: 'Adequate risk-adjusted returns', sentiment: 'neutral' };
  return { text: 'Poor risk-adjusted returns', sentiment: 'negative' };
}

function sortinoInterpretation(val: number | null): { text: string; sentiment: Sentiment } {
  if (val == null) return { text: '\u2014', sentiment: 'neutral' };
  if (val >= 2.0) return { text: 'Excellent downside protection', sentiment: 'positive' };
  if (val >= 1.0) return { text: 'Adequate downside protection', sentiment: 'neutral' };
  return { text: 'High downside risk', sentiment: 'negative' };
}

function drawdownInterpretation(val: number | null): { text: string; sentiment: Sentiment } {
  if (val == null) return { text: '\u2014', sentiment: 'neutral' };
  if (val < 0.1) return { text: 'Minimal drawdown', sentiment: 'positive' };
  if (val < 0.2) return { text: 'Moderate drawdown', sentiment: 'neutral' };
  return { text: 'Significant drawdown', sentiment: 'negative' };
}

function volInterpretation(val: number | null): { text: string; sentiment: Sentiment } {
  if (val == null) return { text: '\u2014', sentiment: 'neutral' };
  if (val < 0.12) return { text: 'Low volatility', sentiment: 'positive' };
  if (val < 0.20) return { text: 'Moderate volatility', sentiment: 'neutral' };
  return { text: 'High volatility', sentiment: 'negative' };
}

function irInterpretation(val: number | null): { text: string; sentiment: Sentiment } {
  if (val == null) return { text: '\u2014', sentiment: 'neutral' };
  if (val >= 0.5) return { text: 'Consistent outperformance', sentiment: 'positive' };
  if (val >= 0) return { text: 'Marginal outperformance', sentiment: 'neutral' };
  return { text: 'Underperforming benchmark', sentiment: 'negative' };
}

function buildRows(perf: PerformanceResult): MetricRow[] {
  const sharpe = sharpeInterpretation(perf.sharpe_ratio);
  const sortino = sortinoInterpretation(perf.sortino_ratio);
  const dd = drawdownInterpretation(perf.max_drawdown);
  const beta = betaInterpretation(perf.beta);
  const vol = volInterpretation(perf.volatility);
  const ir = irInterpretation(perf.information_ratio);

  return [
    {
      label: 'Sharpe Ratio',
      value: fmt2(perf.sharpe_ratio),
      interpretation: sharpe.text,
      sentiment: sharpe.sentiment,
    },
    {
      label: 'Sortino Ratio',
      value: fmt2(perf.sortino_ratio),
      interpretation: sortino.text,
      sentiment: sortino.sentiment,
    },
    {
      label: 'Max Drawdown',
      value: perf.max_drawdown != null ? fmtPct(-perf.max_drawdown) : '\u2014',
      interpretation: dd.text,
      sentiment: dd.sentiment,
    },
    {
      label: 'Beta',
      value: fmt2(perf.beta),
      interpretation: beta.text,
      sentiment: beta.sentiment,
    },
    {
      label: 'Volatility',
      value: fmtPct(perf.volatility),
      interpretation: vol.text,
      sentiment: vol.sentiment,
    },
    {
      label: 'Tracking Error',
      value: fmtPct(perf.tracking_error),
      interpretation: perf.tracking_error != null
        ? (perf.tracking_error < 0.05 ? 'Closely tracks benchmark' : 'Significant deviation from benchmark')
        : '\u2014',
      sentiment: perf.tracking_error != null
        ? (perf.tracking_error < 0.05 ? 'neutral' : 'neutral')
        : 'neutral',
    },
    {
      label: 'Information Ratio',
      value: fmt2(perf.information_ratio),
      interpretation: ir.text,
      sentiment: ir.sentiment,
    },
  ];
}

const DOT_COLOR: Record<Sentiment, string> = {
  positive: 'var(--color-positive)',
  negative: 'var(--color-negative)',
  neutral: 'var(--text-tertiary)',
};

export function RiskMetrics({ performance }: Props) {
  if (!performance) {
    return <div className={styles.empty}>No risk metrics available</div>;
  }

  const rows = buildRows(performance);

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th className={styles.th}>Metric</th>
          <th className={styles.thRight}>Value</th>
          <th className={styles.th}>Interpretation</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.label} className={styles.tr}>
            <td className={styles.td}>
              <span
                className={styles.dot}
                style={{ background: DOT_COLOR[row.sentiment] }}
              />
              {row.label}
            </td>
            <td className={styles.tdRight}>{row.value}</td>
            <td className={styles.tdInterp}>{row.interpretation}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
