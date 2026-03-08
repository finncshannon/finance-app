import { useState } from 'react';
import { api } from '../../../services/api';
import type { Account, Position, PositionCreate } from '../types';
import styles from './AddPositionModal.module.css';

interface Props {
  accounts: Account[];
  onClose: () => void;
  onSuccess: () => void;
}

export function AddPositionModal({ accounts, onClose, onSuccess }: Props) {
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('');
  const [costBasis, setCostBasis] = useState('');
  const [dateAcquired, setDateAcquired] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [account, setAccount] = useState(
    accounts.find((a) => a.is_default)?.name ?? ''
  );
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const validate = (): string | null => {
    if (!ticker.trim()) return 'Ticker is required';
    const s = parseFloat(shares);
    if (isNaN(s) || s <= 0) return 'Shares must be greater than 0';
    const c = parseFloat(costBasis);
    if (isNaN(c) || c <= 0) return 'Cost basis must be greater than 0';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) { setError(err); return; }

    setSubmitting(true);
    setError('');

    const body: PositionCreate = {
      ticker: ticker.trim().toUpperCase(),
      shares: parseFloat(shares),
      cost_basis_per_share: parseFloat(costBasis),
      date_acquired: dateAcquired || undefined,
      account: account || undefined,
      notes: notes.trim() || null,
    };

    try {
      await api.post<Position>('/api/v1/portfolio/positions', body);
      onSuccess();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to add position');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3 className={styles.title}>Add Position</h3>

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

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Shares</label>
              <input
                className={styles.input}
                type="number"
                step="any"
                min="0"
                value={shares}
                onChange={(e) => setShares(e.target.value)}
                placeholder="100"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Cost Basis / Share</label>
              <input
                className={styles.input}
                type="number"
                step="0.01"
                min="0"
                value={costBasis}
                onChange={(e) => setCostBasis(e.target.value)}
                placeholder="150.00"
              />
            </div>
          </div>

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Date Acquired</label>
              <input
                className={styles.input}
                type="date"
                value={dateAcquired}
                onChange={(e) => setDateAcquired(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Account</label>
              <select
                className={styles.select}
                value={account}
                onChange={(e) => setAccount(e.target.value)}
              >
                <option value="">Select account</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.name}>{a.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Notes</label>
            <textarea
              className={styles.textarea}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes..."
              rows={2}
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
              {submitting ? 'Adding...' : 'Add Position'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
