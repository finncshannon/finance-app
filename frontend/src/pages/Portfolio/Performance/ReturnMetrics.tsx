import type { PerformanceResult } from '../types';
import { fmtPct, gainColor } from '../types';
import styles from './ReturnMetrics.module.css';

interface Props {
  performance: PerformanceResult | null;
}

const TWR_LABELS: Record<string, string> = {
  '1D': '1D',
  '3D': '3D',
  '5D': '5D',
  '2W': '2W',
  '1M': '1M',
  '3M': '3M',
  '6M': '6M',
  'YTD': 'YTD',
  '1Y': '1Y',
  '3Y': '3Y',
  'ALL': 'All',
};

export function ReturnMetrics({ performance }: Props) {
  if (!performance) {
    return <div className={styles.empty}>No performance data available</div>;
  }

  const twrEntries = Object.entries(performance.twr);

  return (
    <div className={styles.container}>
      {/* TWR row */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>Time-Weighted Return (TWR)</div>
        <div className={styles.twrRow}>
          {twrEntries.map(([key, value]) => (
            <div key={key} className={styles.twrItem}>
              <span className={styles.twrPeriod}>{TWR_LABELS[key] ?? key}</span>
              <span
                className={styles.twrValue}
                style={{ color: gainColor(value) }}
              >
                {fmtPct(value)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* MWRR section */}
      {performance.mwrr != null && (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>Money-Weighted Return (MWRR)</div>
          <div className={styles.mwrrRow}>
            <span className={styles.mwrrLabel}>Since Inception:</span>
            <span
              className={styles.mwrrValue}
              style={{ color: gainColor(performance.mwrr) }}
            >
              {fmtPct(performance.mwrr)}
            </span>
            {performance.mwrr_annualized != null && (
              <>
                <span className={styles.mwrrSep}>(annualized:</span>
                <span
                  className={styles.mwrrValue}
                  style={{ color: gainColor(performance.mwrr_annualized) }}
                >
                  {fmtPct(performance.mwrr_annualized)}
                </span>
                <span className={styles.mwrrSep}>)</span>
              </>
            )}
          </div>

          {/* Comparison note */}
          {performance.twr['1Y'] != null && (
            <div className={styles.note}>
              {Math.abs((performance.mwrr ?? 0) - (performance.twr['1Y'] ?? 0)) > 0.01
                ? 'TWR and MWRR differ due to the timing and size of cash flows. '
                  + 'TWR removes the impact of deposits/withdrawals; MWRR reflects actual investor experience.'
                : 'TWR and MWRR are closely aligned, indicating cash flow timing had minimal impact on returns.'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
