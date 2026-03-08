import { type RecentModel, fmtDollar, fmtSignedPct } from '../types';
import { navigationService } from '../../../services/navigationService';
import { useUIStore } from '../../../stores/uiStore';
import styles from './RecentModelsWidget.module.css';

interface RecentModelsWidgetProps {
  models: RecentModel[];
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

export function RecentModelsWidget({ models }: RecentModelsWidgetProps) {
  const goToModule = () => useUIStore.getState().setActiveModule('model-builder');

  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <span className={styles.headerTitle}>Recent Models</span>
        <button className={styles.navLink} onClick={goToModule}>
          Open Model Builder &rarr;
        </button>
      </div>
      <div className={styles.body}>
        {models.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyTitle}>No models yet</div>
            <div className={styles.emptyText}>Build your first valuation model to see it here.</div>
            <button className={styles.emptyBtn} onClick={goToModule}>
              Open Model Builder
            </button>
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Ticker</th>
                <th className={styles.th}>Model</th>
                <th className={styles.thRight}>Intrinsic Value</th>
                <th className={styles.thRight}>Current Price</th>
                <th className={styles.thRight}>Upside</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr
                  key={`${m.ticker}-${m.model_type}-${m.last_run_at}`}
                  className={styles.trHover}
                  onClick={() => navigationService.goToModelBuilder(m.ticker, m.model_type)}
                  style={{ cursor: 'pointer' }}
                >
                  <td className={styles.td}>
                    <div className={styles.ticker}>{m.ticker}</div>
                    <div className={styles.timestamp}>{formatRelativeTime(m.last_run_at)}</div>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.modelBadge}>{m.model_type.toUpperCase()}</span>
                  </td>
                  <td className={styles.tdRight}>{fmtDollar(m.intrinsic_value)}</td>
                  <td className={styles.tdRight}>{fmtDollar(m.current_price)}</td>
                  <td className={styles.tdRight}>
                    {m.upside_pct != null ? (
                      <span
                        className={`${styles.upsideBadge} ${
                          m.upside_pct >= 0 ? styles.upsidePositive : styles.upsideNegative
                        }`}
                      >
                        {fmtSignedPct(m.upside_pct)}
                      </span>
                    ) : (
                      '--'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
