import type { MarketOverview } from '../types';
import { fmtDollar, fmtSignedPct, gainColor, statusColor } from '../types';
import styles from './MarketOverviewWidget.module.css';

interface Props {
  market: MarketOverview;
}

export function MarketOverviewWidget({ market }: Props) {
  const { indices, status } = market;

  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <h3 className={styles.headerTitle}>Market Overview</h3>
        <div className={styles.statusBadge}>
          <span
            className={styles.statusDot}
            style={{ backgroundColor: statusColor(status) }}
          />
          <span className={styles.statusLabel}>{status.label}</span>
          {status.countdown && (
            <span className={styles.statusCountdown}>{status.countdown}</span>
          )}
        </div>
      </div>
      <div className={styles.indicesRow}>
        {indices.map((idx) => (
          <div key={idx.symbol} className={styles.indexCard}>
            <div className={styles.indexSymbol}>{idx.symbol}</div>
            <div className={styles.indexName}>{idx.name}</div>
            <div className={styles.indexValue}>{fmtDollar(idx.value)}</div>
            <div
              className={styles.indexChange}
              style={{ color: gainColor(idx.change) }}
            >
              {idx.change >= 0 ? '+' : ''}
              {idx.change.toFixed(2)} ({fmtSignedPct(idx.change_pct)})
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
