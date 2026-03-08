import type { Position, Account } from '../types';
import { SectorDonut } from './SectorDonut';
import { Treemap } from './Treemap';
import { AccountBreakdown } from './AccountBreakdown';
import styles from './AllocationTab.module.css';

interface Props {
  positions: Position[];
  accounts: Account[];
}

export function AllocationTab({ positions, accounts }: Props) {
  if (positions.length === 0) {
    return (
      <div className={styles.empty}>
        No positions to display. Add holdings to see allocation breakdown.
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Sector Allocation</h3>
        <SectorDonut positions={positions} />
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Position Treemap</h3>
        <Treemap positions={positions} />
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Account Breakdown</h3>
        <AccountBreakdown positions={positions} accounts={accounts} />
      </div>
    </div>
  );
}
