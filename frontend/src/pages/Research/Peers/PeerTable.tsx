import { fmtMillions, fmtPct } from '../types';
import styles from './PeerTable.module.css';

export interface PeerRow {
  ticker: string;
  company_name: string;
  isTarget: boolean;
  market_cap: number | null;
  revenue_growth: number | null;
  operating_margin: number | null;
  roe: number | null;
  pe_ratio: number | null;
  ev_to_ebitda: number | null;
}

interface PeerTableProps {
  rows: PeerRow[];
  onRemove: (ticker: string) => void;
  onNavigate: (ticker: string) => void;
}

/** Compute median of non-null values. Returns null if no values. */
function median(values: (number | null)[]): number | null {
  const nums = values.filter((v): v is number => v != null);
  if (nums.length === 0) return null;
  nums.sort((a, b) => a - b);
  const mid = Math.floor(nums.length / 2);
  return nums.length % 2 === 0 ? (nums[mid - 1]! + nums[mid]!) / 2 : nums[mid]!;
}

function fmtMultiple(val: number | null): string {
  if (val == null) return '--';
  return `${val.toFixed(1)}x`;
}

type MetricKey = 'market_cap' | 'revenue_growth' | 'operating_margin' | 'roe' | 'pe_ratio' | 'ev_to_ebitda';

/** Returns 'positive' if target is better than median, 'negative' if worse, '' if neutral/null. */
function highlightClass(metric: MetricKey, targetVal: number | null, medianVal: number | null): string {
  if (targetVal == null || medianVal == null) return '';
  // Higher is better
  const higherBetter: MetricKey[] = ['revenue_growth', 'operating_margin', 'roe'];
  // Lower is better
  const lowerBetter: MetricKey[] = ['pe_ratio', 'ev_to_ebitda'];

  if (higherBetter.includes(metric)) {
    return targetVal > medianVal ? 'positive' : targetVal < medianVal ? 'negative' : '';
  }
  if (lowerBetter.includes(metric)) {
    return targetVal < medianVal ? 'positive' : targetVal > medianVal ? 'negative' : '';
  }
  // market_cap: neutral
  return '';
}

const COLUMNS: { key: MetricKey; label: string; fmt: (v: number | null) => string }[] = [
  { key: 'market_cap', label: 'Market Cap', fmt: (v) => v == null ? '--' : `$${fmtMillions(v)}` },
  { key: 'revenue_growth', label: 'Rev Growth', fmt: fmtPct },
  { key: 'operating_margin', label: 'Op Margin', fmt: fmtPct },
  { key: 'roe', label: 'ROE', fmt: fmtPct },
  { key: 'pe_ratio', label: 'P/E', fmt: fmtMultiple },
  { key: 'ev_to_ebitda', label: 'EV/EBITDA', fmt: fmtMultiple },
];

export function PeerTable({ rows, onRemove, onNavigate }: PeerTableProps) {
  // Compute medians across ALL rows
  const medians: Record<MetricKey, number | null> = {
    market_cap: median(rows.map((r) => r.market_cap)),
    revenue_growth: median(rows.map((r) => r.revenue_growth)),
    operating_margin: median(rows.map((r) => r.operating_margin)),
    roe: median(rows.map((r) => r.roe)),
    pe_ratio: median(rows.map((r) => r.pe_ratio)),
    ev_to_ebitda: median(rows.map((r) => r.ev_to_ebitda)),
  };

  function getValueClass(metric: MetricKey, row: PeerRow): string {
    if (!row.isTarget) return '';
    const hl = highlightClass(metric, row[metric], medians[metric]);
    if (hl === 'positive') return styles.positive ?? '';
    if (hl === 'negative') return styles.negative ?? '';
    return '';
  }

  return (
    <div className={styles.wrapper ?? ''}>
      <table className={styles.table ?? ''}>
        <thead>
          <tr className={styles.headerRow ?? ''}>
            <th className={`${styles.th ?? ''} ${styles.companyCol ?? ''}`}>Company</th>
            {COLUMNS.map((col) => (
              <th key={col.key} className={`${styles.th ?? ''} ${styles.numCol ?? ''}`}>
                {col.label}
              </th>
            ))}
            <th className={`${styles.th ?? ''} ${styles.actionCol ?? ''}`} />
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const isOdd = idx % 2 === 1;
            const rowClass = [
              styles.bodyRow ?? '',
              row.isTarget ? (styles.targetRow ?? '') : '',
              !row.isTarget && isOdd ? (styles.zebraRow ?? '') : '',
            ].filter(Boolean).join(' ');

            return (
              <tr key={row.ticker} className={rowClass}>
                <td className={`${styles.td ?? ''} ${styles.companyCol ?? ''}`}>
                  {row.isTarget ? (
                    <span className={styles.companyName ?? ''}>
                      <span className={styles.marker ?? ''}>&#9658;</span>
                      {row.company_name} ({row.ticker})
                    </span>
                  ) : (
                    <span className={styles.companyName ?? ''}>
                      <button
                        type="button"
                        className={styles.tickerLink ?? ''}
                        onClick={() => onNavigate(row.ticker)}
                      >
                        {row.ticker}
                      </button>
                      <span className={styles.peerName ?? ''}>{row.company_name}</span>
                    </span>
                  )}
                </td>
                {COLUMNS.map((col) => (
                  <td
                    key={col.key}
                    className={`${styles.td ?? ''} ${styles.numCol ?? ''} ${getValueClass(col.key, row)}`}
                  >
                    {col.fmt(row[col.key])}
                  </td>
                ))}
                <td className={`${styles.td ?? ''} ${styles.actionCol ?? ''}`}>
                  {!row.isTarget && (
                    <button
                      type="button"
                      className={styles.removeBtn ?? ''}
                      onClick={() => onRemove(row.ticker)}
                      title={`Remove ${row.ticker}`}
                    >
                      &times;
                    </button>
                  )}
                </td>
              </tr>
            );
          })}

          {/* Median row */}
          <tr className={styles.medianRow ?? ''}>
            <td className={`${styles.td ?? ''} ${styles.companyCol ?? ''} ${styles.medianLabel ?? ''}`}>
              Median
            </td>
            {COLUMNS.map((col) => (
              <td key={col.key} className={`${styles.td ?? ''} ${styles.numCol ?? ''} ${styles.medianVal ?? ''}`}>
                {col.fmt(medians[col.key])}
              </td>
            ))}
            <td className={`${styles.td ?? ''} ${styles.actionCol ?? ''}`} />
          </tr>
        </tbody>
      </table>
    </div>
  );
}
