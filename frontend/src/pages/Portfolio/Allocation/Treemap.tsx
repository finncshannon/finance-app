import { useMemo } from 'react';
import type { Position } from '../types';
import { fmtPct, gainColor } from '../types';
import styles from './Treemap.module.css';

interface Props {
  positions: Position[];
}

interface TreemapItem {
  label: string;
  weight: number;
  gainPct: number | null;
  sector?: string;
}


function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

function gainBackground(gainPct: number | null): string {
  if (gainPct == null) return 'var(--bg-tertiary)';
  const intensity = clamp(Math.abs(gainPct) * 100, 5, 60) / 100;
  if (gainPct >= 0) {
    return `rgba(34, 197, 94, ${intensity.toFixed(2)})`;
  }
  return `rgba(239, 68, 68, ${intensity.toFixed(2)})`;
}

export function Treemap({ positions }: Props) {
  const items = useMemo(() => {
    const totalValue = positions.reduce((sum, p) => sum + (p.market_value ?? 0), 0);
    if (totalValue === 0) return [];

    const mapped: TreemapItem[] = positions.map((p) => ({
      label: p.ticker,
      weight: (p.market_value ?? 0) / totalValue,
      gainPct: p.gain_loss_pct,
      sector: p.sector || 'Unknown',
    }));

    // Sort by weight descending
    mapped.sort((a, b) => b.weight - a.weight);

    // Group small positions into "Other"
    const main: TreemapItem[] = [];
    let otherWeight = 0;
    let otherGainSum = 0;
    let otherCount = 0;

    for (const item of mapped) {
      if (item.weight < 0.02) {
        otherWeight += item.weight;
        otherGainSum += (item.gainPct ?? 0) * item.weight;
        otherCount++;
      } else {
        main.push(item);
      }
    }

    if (otherCount > 0) {
      main.push({
        label: `Other (${otherCount})`,
        weight: otherWeight,
        gainPct: otherWeight > 0 ? otherGainSum / otherWeight : 0,
      });
    }

    return main;
  }, [positions]);

  if (items.length === 0) {
    return <div className={styles.empty}>No position data for treemap</div>;
  }

  return (
    <div className={styles.grid}>
      {items.map((item) => (
        <div
          key={item.label}
          className={styles.cell}
          style={{
            flexBasis: `${Math.max(item.weight * 100, 8)}%`,
            flexGrow: item.weight * 100,
            background: gainBackground(item.gainPct),
          }}
        >
          <span className={styles.ticker}>{item.label}</span>
          <span className={styles.weight}>
            {(item.weight * 100).toFixed(1)}%
          </span>
          <span
            className={styles.gain}
            style={{ color: gainColor(item.gainPct) }}
          >
            {fmtPct(item.gainPct)}
          </span>
        </div>
      ))}
    </div>
  );
}
