import type { PortfolioSummary } from '../types';
import { fmtDollar, fmtSignedDollar, fmtSignedPct, gainColor } from '../types';
import { useUIStore } from '../../../stores/uiStore';
import styles from './PortfolioSummaryWidget.module.css';

interface Props {
  portfolio: PortfolioSummary | null;
}

export function PortfolioSummaryWidget({ portfolio }: Props) {
  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <h3 className={styles.headerTitle}>Portfolio</h3>
        <button
          className={styles.navLink}
          onClick={() => useUIStore.getState().setActiveModule('portfolio')}
        >
          Open Portfolio &rarr;
        </button>
      </div>
      {portfolio === null ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyTitle}>No portfolio yet</div>
          <div className={styles.emptyText}>Add your first position to track performance.</div>
          <button
            className={styles.emptyBtn}
            onClick={() => useUIStore.getState().setActiveModule('portfolio')}
          >
            Add Position
          </button>
        </div>
      ) : (
        <div className={styles.body}>
          <div className={styles.mainValue}>{fmtDollar(portfolio.total_value)}</div>
          <div className={styles.changeRow}>
            <div className={styles.changeItem}>
              <span className={styles.changeLabel}>Day Change</span>
              <span
                className={styles.changeValue}
                style={{ color: gainColor(portfolio.day_change) }}
              >
                {fmtSignedDollar(portfolio.day_change)} ({fmtSignedPct(portfolio.day_change_pct)})
              </span>
            </div>
            <div className={styles.changeItem}>
              <span className={styles.changeLabel}>Total Gain/Loss</span>
              <span
                className={styles.changeValue}
                style={{ color: gainColor(portfolio.total_gain_loss) }}
              >
                {fmtSignedDollar(portfolio.total_gain_loss)} ({fmtSignedPct(portfolio.total_gain_loss_pct)})
              </span>
            </div>
            <div className={styles.changeItem}>
              <span className={styles.changeLabel}>Positions</span>
              <span className={styles.changeValue} style={{ color: 'var(--text-primary)' }}>
                {portfolio.position_count}
              </span>
            </div>
          </div>
          <hr className={styles.divider} />
          <div className={styles.performers}>
            <div className={styles.performer}>
              <div className={styles.performerLabel}>Best Performer</div>
              {portfolio.best_performer ? (
                <>
                  <div className={styles.performerTicker}>
                    {portfolio.best_performer.ticker}
                  </div>
                  <div
                    className={styles.performerGain}
                    style={{ color: gainColor(portfolio.best_performer.gain_pct) }}
                  >
                    {fmtSignedPct(portfolio.best_performer.gain_pct)}
                  </div>
                </>
              ) : (
                <div className={styles.performerTicker}>--</div>
              )}
            </div>
            <div className={styles.performer}>
              <div className={styles.performerLabel}>Worst Performer</div>
              {portfolio.worst_performer ? (
                <>
                  <div className={styles.performerTicker}>
                    {portfolio.worst_performer.ticker}
                  </div>
                  <div
                    className={styles.performerGain}
                    style={{ color: gainColor(portfolio.worst_performer.gain_pct) }}
                  >
                    {fmtSignedPct(portfolio.worst_performer.gain_pct)}
                  </div>
                </>
              ) : (
                <div className={styles.performerTicker}>--</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
