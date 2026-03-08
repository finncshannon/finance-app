import type { PortfolioSummary } from '../types';
import { fmtDollar, fmtSignedDollar, fmtPct, gainColor } from '../types';
import styles from './SummaryHeader.module.css';

interface Props {
  summary: PortfolioSummary | null;
}

export function SummaryHeader({ summary }: Props) {
  if (!summary) return null;

  return (
    <div className={styles.bar}>
      {/* Total Value */}
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Total Value</span>
        <span className={styles.totalValue}>{fmtDollar(summary.total_value)}</span>
      </div>

      {/* Day Change */}
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Day Change</span>
        <span
          className={styles.changeValue}
          style={{ color: gainColor(summary.day_change) }}
        >
          {fmtSignedDollar(summary.day_change)} ({fmtPct(summary.day_change_pct)})
        </span>
      </div>

      {/* Total Gain/Loss */}
      <div className={styles.metric}>
        <span className={styles.metricLabel}>Total Gain/Loss</span>
        <span
          className={styles.changeValue}
          style={{ color: gainColor(summary.total_gain_loss) }}
        >
          {fmtSignedDollar(summary.total_gain_loss)} ({fmtPct(summary.total_gain_loss_pct)})
        </span>
      </div>

      {/* Secondary info */}
      <div className={styles.secondary}>
        Positions: {summary.position_count} &middot; Accounts: {summary.account_count}
        {summary.weighted_dividend_yield != null && (
          <> &middot; Dividend Yield: {(summary.weighted_dividend_yield * 100).toFixed(2)}%</>
        )}
      </div>
    </div>
  );
}
