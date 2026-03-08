import type { ReactNode } from 'react';
import { fmtPrice, fmtPct } from './formatters';
import styles from './ResultsCard.module.css';

export interface ResultsCardProps {
  impliedPrice: number;
  currentPrice: number;
  upsidePct: number | null;
  label?: string;
  secondaryValues?: { label: string; value: string }[];
  exportSlot?: ReactNode;
}

export function ResultsCard({
  impliedPrice,
  currentPrice,
  upsidePct,
  label = 'Implied Price',
  secondaryValues,
  exportSlot,
}: ResultsCardProps) {
  const isPositive = upsidePct != null && upsidePct >= 0;

  return (
    <div className={styles.card}>
      <div className={styles.topRow}>
        <div className={styles.priceGroup}>
          <span className={styles.label}>{label}</span>
          <span className={styles.impliedPrice}>{fmtPrice(impliedPrice)}</span>
        </div>

        {upsidePct != null && (
          <span
            className={`${styles.upsideBadge} ${
              isPositive ? styles.upsidePositive : styles.upsideNegative
            }`}
          >
            {isPositive ? '+' : ''}
            {fmtPct(upsidePct)}
          </span>
        )}

        <div className={styles.currentRef}>
          <span>Current:</span>
          <span className={styles.currentRefValue}>{fmtPrice(currentPrice)}</span>
        </div>

        {exportSlot && <div className={styles.exportSlot}>{exportSlot}</div>}
      </div>

      {secondaryValues && secondaryValues.length > 0 && (
        <div className={styles.secondaryGrid}>
          {secondaryValues.map((sv) => (
            <div key={sv.label} className={styles.secondaryItem}>
              <span className={styles.secondaryLabel}>{sv.label}</span>
              <span className={styles.secondaryValue}>{sv.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
