import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import type { Position, Lot } from '../types';
import styles from './EditPositionModal.module.css';

interface Props {
  position: Position;
  onClose: () => void;
  onSuccess: () => void;
}

interface LotEdit {
  id: number;
  shares: string;
  cost_basis_per_share: string;
  date_acquired: string;
  dirty: boolean;
}

export function EditPositionModal({ position, onClose, onSuccess }: Props) {
  const [shares, setShares] = useState(String(position.shares_held));
  const [costBasis, setCostBasis] = useState(
    position.cost_basis_per_share != null ? String(position.cost_basis_per_share) : ''
  );
  const [account, setAccount] = useState(position.account ?? 'Manual');
  const [notes, setNotes] = useState('');
  const [lots, setLots] = useState<LotEdit[]>([]);
  const [lotsLoading, setLotsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Load lots
  useEffect(() => {
    let cancelled = false;
    api.get<{ lots: Lot[] }>(`/api/v1/portfolio/lots/${position.id}`)
      .then((data) => {
        if (cancelled) return;
        setLots(data.lots.map((l) => ({
          id: l.id,
          shares: String(l.shares),
          cost_basis_per_share: String(l.cost_basis_per_share),
          date_acquired: l.date_acquired,
          dirty: false,
        })));
      })
      .catch(() => {
        if (!cancelled) setLots([]);
      })
      .finally(() => {
        if (!cancelled) setLotsLoading(false);
      });
    return () => { cancelled = true; };
  }, [position.id]);

  const handleLotChange = (idx: number, field: keyof LotEdit, value: string) => {
    setLots((prev) => prev.map((l, i) =>
      i === idx ? { ...l, [field]: value, dirty: true } : l
    ));
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');

    try {
      // Build position update (only changed fields)
      const updates: Record<string, unknown> = {};
      const newShares = parseFloat(shares);
      if (!isNaN(newShares) && newShares !== position.shares_held) {
        updates.shares_held = newShares;
      }
      const newCost = parseFloat(costBasis);
      if (!isNaN(newCost) && newCost !== position.cost_basis_per_share) {
        updates.cost_basis_per_share = newCost;
      }
      if (account !== position.account) {
        updates.account = account;
      }
      if (notes.trim()) {
        updates.notes = notes.trim();
      }

      if (Object.keys(updates).length > 0) {
        await api.put(`/api/v1/portfolio/positions/${position.id}`, updates);
      }

      // Save dirty lots
      for (const lot of lots) {
        if (!lot.dirty) continue;
        const lotUpdates: Record<string, unknown> = {};
        const lotShares = parseFloat(lot.shares);
        if (!isNaN(lotShares)) lotUpdates.shares = lotShares;
        const lotCost = parseFloat(lot.cost_basis_per_share);
        if (!isNaN(lotCost)) lotUpdates.cost_basis_per_share = lotCost;
        if (Object.keys(lotUpdates).length > 0) {
          await api.put(`/api/v1/portfolio/lots/${lot.id}`, lotUpdates);
        }
      }

      onSuccess();
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3 className={styles.title}>Edit Position — {position.ticker}</h3>

        {/* Position fields */}
        <div className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>Shares</label>
            <input
              className={styles.input}
              type="number"
              value={shares}
              onChange={(e) => setShares(e.target.value)}
              step="any"
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Cost Basis / Share</label>
            <input
              className={styles.input}
              type="number"
              value={costBasis}
              onChange={(e) => setCostBasis(e.target.value)}
              step="any"
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Account</label>
            <input
              className={styles.input}
              type="text"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Notes</label>
            <input
              className={styles.input}
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional"
            />
          </div>
        </div>

        {/* Lot-level editing */}
        {lots.length > 1 && (
          <div className={styles.lotsSection}>
            <div className={styles.lotsTitle}>Tax Lots ({lots.length})</div>
            {lotsLoading ? (
              <div className={styles.loading}>Loading lots...</div>
            ) : (
              <table className={styles.lotsTable}>
                <thead>
                  <tr>
                    <th className={styles.lotTh}>Date</th>
                    <th className={styles.lotThRight}>Shares</th>
                    <th className={styles.lotThRight}>Cost/Share</th>
                  </tr>
                </thead>
                <tbody>
                  {lots.map((lot, i) => (
                    <tr key={lot.id} className={i % 2 === 0 ? styles.lotTrEven : styles.lotTrOdd}>
                      <td className={styles.lotTd}>
                        {new Date(lot.date_acquired).toLocaleDateString()}
                      </td>
                      <td className={styles.lotTdRight}>
                        <input
                          className={styles.lotInput}
                          type="number"
                          value={lot.shares}
                          onChange={(e) => handleLotChange(i, 'shares', e.target.value)}
                          step="any"
                        />
                      </td>
                      <td className={styles.lotTdRight}>
                        <input
                          className={styles.lotInput}
                          type="number"
                          value={lot.cost_basis_per_share}
                          onChange={(e) => handleLotChange(i, 'cost_basis_per_share', e.target.value)}
                          step="any"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.actions}>
          <button className={styles.btn} onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className={styles.btnPrimary} onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
