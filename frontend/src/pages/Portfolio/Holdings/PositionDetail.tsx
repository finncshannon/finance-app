import { useState, useEffect } from 'react';
import { useUIStore } from '../../../stores/uiStore';
import { api } from '../../../services/api';
import type { Position, Lot, Transaction } from '../types';
import {
  fmtDollar, fmtPct, fmtShares,
  fmtHoldingPeriod, gainColor,
} from '../types';
import styles from './PositionDetail.module.css';

interface Props {
  position: Position;
  onRecordTx: (ticker: string) => void;
  onEditPosition?: (position: Position) => void;
}

// ─── Transaction Type Badge ────────────────────────
function TxBadge({ type }: { type: string }) {
  const upper = type.toUpperCase();
  let cls = styles.badgeOther;
  if (upper === 'BUY') cls = styles.badgeBuy;
  else if (upper === 'SELL') cls = styles.badgeSell;
  else if (upper === 'DIVIDEND' || upper === 'DRIP') cls = styles.badgeDividend;
  return <span className={cls}>{upper}</span>;
}

export function PositionDetail({ position, onRecordTx, onEditPosition }: Props) {
  const setActiveModule = useUIStore((s) => s.setActiveModule);

  const [lots, setLots] = useState<Lot[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [lotsLoading, setLotsLoading] = useState(true);
  const [txLoading, setTxLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchLots() {
      setLotsLoading(true);
      try {
        const data = await api.get<{ lots: Lot[] }>(
          `/api/v1/portfolio/lots/${position.id}`
        );
        if (!cancelled) setLots(data.lots);
      } catch {
        if (!cancelled) setLots([]);
      } finally {
        if (!cancelled) setLotsLoading(false);
      }
    }

    async function fetchTx() {
      setTxLoading(true);
      try {
        const data = await api.get<{ transactions: Transaction[] }>(
          `/api/v1/portfolio/transactions?ticker=${position.ticker}`
        );
        if (!cancelled) setTransactions(data.transactions.slice(0, 5));
      } catch {
        if (!cancelled) setTransactions([]);
      } finally {
        if (!cancelled) setTxLoading(false);
      }
    }

    fetchLots();
    fetchTx();

    return () => { cancelled = true; };
  }, [position.id, position.ticker]);

  return (
    <div className={styles.container}>
      {/* ── Lots Table ── */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>Tax Lots</div>
        {lotsLoading ? (
          <div className={styles.loading}>Loading lots...</div>
        ) : lots.length === 0 ? (
          <div className={styles.empty}>No lots recorded</div>
        ) : (
          <table className={styles.innerTable}>
            <thead>
              <tr>
                <th className={styles.innerTh}>Date Acquired</th>
                <th className={styles.innerThRight}>Shares</th>
                <th className={styles.innerThRight}>Cost/Share</th>
                <th className={styles.innerThRight}>Total Cost</th>
                <th className={styles.innerThRight}>Gain %</th>
                <th className={styles.innerTh}>Holding Period</th>
                <th className={styles.innerTh}>Term</th>
              </tr>
            </thead>
            <tbody>
              {lots.map((lot, i) => {
                const totalCost = lot.shares * lot.cost_basis_per_share;
                const currentVal = lot.shares * (position.current_price ?? lot.cost_basis_per_share);
                const gainPct = totalCost > 0 ? (currentVal - totalCost) / totalCost : null;

                return (
                  <tr
                    key={lot.id}
                    className={i % 2 === 0 ? styles.innerTrEven : styles.innerTrOdd}
                  >
                    <td className={styles.innerTd}>
                      {new Date(lot.date_acquired).toLocaleDateString()}
                    </td>
                    <td className={styles.innerTdRight}>{fmtShares(lot.shares)}</td>
                    <td className={styles.innerTdRight}>{fmtDollar(lot.cost_basis_per_share)}</td>
                    <td className={styles.innerTdRight}>{fmtDollar(totalCost)}</td>
                    <td className={styles.innerTdRight} style={{ color: gainColor(gainPct) }}>
                      {fmtPct(gainPct)}
                    </td>
                    <td className={styles.innerTd}>
                      {fmtHoldingPeriod(lot.holding_period_days)}
                    </td>
                    <td className={styles.innerTd}>
                      {lot.is_long_term != null ? (
                        <span className={lot.is_long_term ? styles.ltLong : styles.ltShort}>
                          {lot.is_long_term ? 'Long' : 'Short'}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Recent Transactions ── */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>Recent Transactions</div>
        {txLoading ? (
          <div className={styles.loading}>Loading transactions...</div>
        ) : transactions.length === 0 ? (
          <div className={styles.empty}>No transactions recorded</div>
        ) : (
          <table className={styles.innerTable}>
            <thead>
              <tr>
                <th className={styles.innerTh}>Date</th>
                <th className={styles.innerTh}>Type</th>
                <th className={styles.innerThRight}>Shares</th>
                <th className={styles.innerThRight}>Price</th>
                <th className={styles.innerThRight}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx, i) => (
                <tr
                  key={tx.id}
                  className={i % 2 === 0 ? styles.innerTrEven : styles.innerTrOdd}
                >
                  <td className={styles.innerTd}>
                    {new Date(tx.transaction_date).toLocaleDateString()}
                  </td>
                  <td className={styles.innerTd}>
                    <TxBadge type={tx.transaction_type} />
                  </td>
                  <td className={styles.innerTdRight}>
                    {tx.shares != null ? fmtShares(tx.shares) : '—'}
                  </td>
                  <td className={styles.innerTdRight}>{fmtDollar(tx.price_per_share)}</td>
                  <td className={styles.innerTdRight}>{fmtDollar(tx.total_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Action Buttons ── */}
      <div className={styles.actions}>
        <button
          className={styles.actionBtnPrimary}
          onClick={() => onRecordTx(position.ticker)}
        >
          Record Transaction
        </button>
        {onEditPosition && (
          <button
            className={styles.actionBtn}
            onClick={() => onEditPosition(position)}
          >
            Edit Position
          </button>
        )}
        <button
          className={styles.actionBtn}
          onClick={() => setActiveModule('model-builder')}
        >
          Open in Model Builder
        </button>
      </div>
    </div>
  );
}
