import { useState, useMemo } from 'react';
import type { Position, Account } from '../types';
import { fmtDollar, fmtPct, gainColor } from '../types';
import styles from './AccountBreakdown.module.css';

interface Props {
  positions: Position[];
  accounts: Account[];
}

interface AccountGroup {
  name: string;
  totalValue: number;
  weight: number;
  positions: Position[];
}

export function AccountBreakdown({ positions, accounts }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const groups = useMemo(() => {
    const portfolioTotal = positions.reduce(
      (sum, p) => sum + (p.market_value ?? 0),
      0,
    );

    const acctMap = new Map<string, Position[]>();
    for (const p of positions) {
      const acctName = p.account || 'Default';
      if (!acctMap.has(acctName)) {
        acctMap.set(acctName, []);
      }
      acctMap.get(acctName)!.push(p);
    }

    // Order by account list, then any extras
    const acctNames = accounts.map((a) => a.name);
    const allNames = new Set([...acctNames, ...acctMap.keys()]);

    const result: AccountGroup[] = [];
    for (const name of allNames) {
      const acctPositions = acctMap.get(name);
      if (!acctPositions || acctPositions.length === 0) continue;

      const totalValue = acctPositions.reduce(
        (sum, p) => sum + (p.market_value ?? 0),
        0,
      );

      // Sort positions by value descending
      const sorted = [...acctPositions].sort(
        (a, b) => (b.market_value ?? 0) - (a.market_value ?? 0),
      );

      result.push({
        name,
        totalValue,
        weight: portfolioTotal > 0 ? totalValue / portfolioTotal : 0,
        positions: sorted,
      });
    }

    // Sort groups by total value descending
    result.sort((a, b) => b.totalValue - a.totalValue);
    return result;
  }, [positions, accounts]);

  const toggle = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  if (groups.length === 0) {
    return <div className={styles.empty}>No account data available</div>;
  }

  return (
    <div className={styles.container}>
      {groups.map((group) => {
        const isOpen = expanded.has(group.name);
        const top5 = group.positions.slice(0, 5);
        const remaining = group.positions.length - 5;

        return (
          <div key={group.name} className={styles.section}>
            <button
              className={styles.sectionHeader}
              onClick={() => toggle(group.name)}
            >
              <span className={styles.chevron}>
                {isOpen ? '\u25BE' : '\u25B8'}
              </span>
              <span className={styles.acctName}>{group.name}</span>
              <span className={styles.acctValue}>{fmtDollar(group.totalValue)}</span>
              <span className={styles.acctWeight}>
                {(group.weight * 100).toFixed(1)}%
              </span>
            </button>

            {isOpen && (
              <div className={styles.positionList}>
                {top5.map((p) => (
                  <div key={p.id} className={styles.positionRow}>
                    <span className={styles.posTicker}>{p.ticker}</span>
                    <span className={styles.posShares}>
                      {p.shares_held.toLocaleString()} shr
                    </span>
                    <span className={styles.posValue}>
                      {fmtDollar(p.market_value)}
                    </span>
                    <span
                      className={styles.posGain}
                      style={{ color: gainColor(p.gain_loss_pct) }}
                    >
                      {fmtPct(p.gain_loss_pct)}
                    </span>
                  </div>
                ))}

                {remaining > 0 && (
                  <div className={styles.moreRow}>
                    + {remaining} more position{remaining !== 1 ? 's' : ''}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
