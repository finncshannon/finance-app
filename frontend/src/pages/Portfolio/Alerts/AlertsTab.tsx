import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import type { Alert } from '../types';
import { fmtDollar, fmtPct } from '../types';
import { CreateAlertModal } from './CreateAlertModal';
import styles from './AlertsTab.module.css';

const ALERT_TYPE_LABELS: Record<string, string> = {
  price_above: 'Above',
  price_below: 'Below',
  pct_change: '% Change >',
  intrinsic_cross: 'Intrinsic Cross',
};

function formatThreshold(alert: Alert): string {
  if (alert.alert_type === 'pct_change') {
    return fmtPct(alert.threshold / 100);
  }
  return fmtDollar(alert.threshold);
}

function priceColor(alert: Alert): string {
  if (alert.current_price == null) return 'var(--text-secondary)';
  if (alert.alert_type === 'price_above') {
    return alert.current_price >= alert.threshold ? 'var(--color-positive)' : 'var(--text-primary)';
  }
  if (alert.alert_type === 'price_below') {
    return alert.current_price <= alert.threshold ? 'var(--color-negative)' : 'var(--text-primary)';
  }
  return 'var(--text-primary)';
}

export function AlertsTab() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<{ alerts: Alert[] }>('/api/v1/portfolio/alerts');
      setAlerts(data.alerts);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await api.del(`/api/v1/portfolio/alerts/${id}`);
      await fetchAlerts();
    } catch {
      // Silent fail — could add toast later
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreateSuccess = () => {
    setShowModal(false);
    fetchAlerts();
  };

  if (loading) {
    return <div className={styles.loading}>Loading alerts...</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h3 className={styles.headerTitle}>Price Alerts</h3>
        <button className={styles.btnPrimary} onClick={() => setShowModal(true)}>
          + New Alert
        </button>
      </div>

      {/* Table or Empty */}
      {alerts.length === 0 ? (
        <div className={styles.empty}>
          <span>No alerts configured</span>
          <button className={styles.emptyBtn} onClick={() => setShowModal(true)}>
            + New Alert
          </button>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Ticker</th>
                <th className={styles.th}>Type</th>
                <th className={styles.thRight}>Threshold</th>
                <th className={styles.thRight}>Current Price</th>
                <th className={styles.th}>Status</th>
                <th className={styles.th}>Created</th>
                <th className={styles.thCenter}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert, i) => (
                <tr key={alert.id} className={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  <td className={styles.td}>
                    <span className={styles.tickerMono}>{alert.ticker}</span>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.typeBadge}>
                      {ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
                    </span>
                  </td>
                  <td className={styles.tdRight}>{formatThreshold(alert)}</td>
                  <td className={styles.tdRight} style={{ color: priceColor(alert) }}>
                    {fmtDollar(alert.current_price)}
                  </td>
                  <td className={styles.td}>
                    {alert.is_active ? (
                      <span className={styles.statusActive}>
                        <span className={styles.dotActive} />
                        Active
                      </span>
                    ) : (
                      <span className={styles.statusTriggered}>
                        <span className={styles.dotTriggered} />
                        {alert.triggered_at
                          ? new Date(alert.triggered_at).toLocaleDateString()
                          : 'Triggered'}
                      </span>
                    )}
                  </td>
                  <td className={styles.td}>
                    {new Date(alert.created_at).toLocaleDateString()}
                  </td>
                  <td className={styles.tdCenter}>
                    <button
                      className={styles.deleteBtn}
                      onClick={() => handleDelete(alert.id)}
                      disabled={deletingId === alert.id}
                    >
                      {deletingId === alert.id ? '...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Alert Modal */}
      {showModal && (
        <CreateAlertModal
          onClose={() => setShowModal(false)}
          onSuccess={handleCreateSuccess}
        />
      )}
    </div>
  );
}
