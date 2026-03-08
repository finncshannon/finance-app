import { useState } from 'react';
import { api } from '../../../services/api';
import type { Alert, AlertCreate } from '../types';
import styles from './CreateAlertModal.module.css';

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

const ALERT_TYPES = [
  { value: 'price_above', label: 'Price Above' },
  { value: 'price_below', label: 'Price Below' },
  { value: 'pct_change', label: '% Change' },
] as const;

export function CreateAlertModal({ onClose, onSuccess }: Props) {
  const [ticker, setTicker] = useState('');
  const [alertType, setAlertType] = useState('price_above');
  const [threshold, setThreshold] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedTicker = ticker.trim().toUpperCase();
    if (!trimmedTicker) { setError('Ticker is required'); return; }
    if (!threshold || isNaN(parseFloat(threshold))) { setError('Valid threshold is required'); return; }

    setSubmitting(true);
    setError('');

    const body: AlertCreate = {
      ticker: trimmedTicker,
      alert_type: alertType,
      threshold: parseFloat(threshold),
    };

    try {
      await api.post<Alert>('/api/v1/portfolio/alerts', body);
      onSuccess();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to create alert');
    } finally {
      setSubmitting(false);
    }
  };

  const isPctType = alertType === 'pct_change';

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3 className={styles.title}>New Price Alert</h3>

        <form onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.label}>Ticker</label>
            <input
              className={styles.input}
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="AAPL"
              autoFocus
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Alert Type</label>
            <select
              className={styles.select}
              value={alertType}
              onChange={(e) => setAlertType(e.target.value)}
            >
              {ALERT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>
              Threshold {isPctType ? '(%)' : '($)'}
            </label>
            <input
              className={styles.input}
              type="number"
              step={isPctType ? '0.1' : '0.01'}
              min="0"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              placeholder={isPctType ? '5.0' : '150.00'}
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <div className={styles.actions}>
            <button type="button" className={styles.btn} onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className={styles.btnPrimary}
              disabled={submitting}
            >
              {submitting ? 'Creating...' : 'Create Alert'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
