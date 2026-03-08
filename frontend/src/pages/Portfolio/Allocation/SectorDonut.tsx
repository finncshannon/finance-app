import { useMemo } from 'react';
import type { Position } from '../types';
import { fmtDollar } from '../types';
import styles from './SectorDonut.module.css';

interface Props {
  positions: Position[];
}

interface SectorSlice {
  sector: string;
  value: number;
  pct: number;
  color: string;
}

const NAMED_SECTOR_COLORS: Record<string, string> = {
  'Technology': 'var(--accent-primary)',
  'Healthcare': '#6366F1',
  'Financial Services': '#F59E0B',
  'Consumer Cyclical': '#EF4444',
  'Consumer Defensive': '#10B981',
  'Industrials': '#F97316',
  'Energy': '#EC4899',
  'Utilities': '#14B8A6',
  'Real Estate': '#8B5CF6',
  'Communication Services': '#06B6D4',
  'Basic Materials': '#A855F7',
  'ETF': '#7C3AED',
  'Unknown': '#525252',
};

const FALLBACK_COLORS = [
  'var(--accent-primary)', '#6366F1', '#F59E0B', '#EF4444', '#10B981',
  '#F97316', '#EC4899', '#14B8A6', '#8B5CF6', '#06B6D4',
];

function sectorColor(sector: string, index: number): string {
  return NAMED_SECTOR_COLORS[sector] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length] ?? '#333333';
}

export function SectorDonut({ positions }: Props) {
  const { slices, total } = useMemo(() => {
    const sectorMap = new Map<string, number>();
    let totalVal = 0;

    for (const p of positions) {
      const sector = p.sector || 'Unknown';
      const val = p.market_value ?? 0;
      sectorMap.set(sector, (sectorMap.get(sector) ?? 0) + val);
      totalVal += val;
    }

    const sorted = [...sectorMap.entries()]
      .map(([sector, value]) => ({ sector, value }))
      .sort((a, b) => b.value - a.value);

    const result: SectorSlice[] = sorted.map((s, i) => ({
      sector: s.sector,
      value: s.value,
      pct: totalVal > 0 ? s.value / totalVal : 0,
      color: sectorColor(s.sector, i),
    }));

    return { slices: result, total: totalVal };
  }, [positions]);

  // Donut parameters
  const SIZE = 320;
  const CX = SIZE / 2;
  const CY = SIZE / 2;
  const R = 120;
  const STROKE_W = 30;
  const CIRCUMFERENCE = 2 * Math.PI * R;

  // Build donut segments using stroke-dasharray
  let accumulatedOffset = 0;

  return (
    <div className={styles.container}>
      {/* Donut */}
      <div className={styles.donutWrapper}>
        <svg
          width={SIZE}
          height={SIZE}
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className={styles.donut}
        >
          {/* Background ring */}
          <circle
            cx={CX}
            cy={CY}
            r={R}
            fill="none"
            stroke="var(--bg-tertiary)"
            strokeWidth={STROKE_W}
          />

          {/* Sector arcs */}
          {slices.map((slice) => {
            const dashLen = slice.pct * CIRCUMFERENCE;
            const gapLen = CIRCUMFERENCE - dashLen;
            const offset = -accumulatedOffset;
            accumulatedOffset += dashLen;

            return (
              <circle
                key={slice.sector}
                cx={CX}
                cy={CY}
                r={R}
                fill="none"
                stroke={slice.color}
                strokeWidth={STROKE_W}
                strokeDasharray={`${dashLen.toFixed(2)} ${gapLen.toFixed(2)}`}
                strokeDashoffset={offset.toFixed(2)}
                style={{
                  transform: 'rotate(-90deg)',
                  transformOrigin: `${CX}px ${CY}px`,
                }}
              />
            );
          })}

          {/* Center text */}
          <text
            x={CX}
            y={CY - 8}
            textAnchor="middle"
            className={styles.centerLabel}
            fill="var(--text-tertiary)"
          >
            Total Value
          </text>
          <text
            x={CX}
            y={CY + 14}
            textAnchor="middle"
            className={styles.centerValue}
            fill="var(--text-primary)"
          >
            {fmtDollar(total)}
          </text>
        </svg>
      </div>

      {/* Legend */}
      <div className={styles.legend}>
        {slices.map((slice) => (
          <div key={slice.sector} className={styles.legendRow}>
            <span
              className={styles.legendDot}
              style={{ background: slice.color }}
            />
            <span className={styles.legendName}>{slice.sector}</span>
            <span className={styles.legendValue}>{fmtDollar(slice.value)}</span>
            <span className={styles.legendPct}>{(slice.pct * 100).toFixed(1)}%</span>
            <div className={styles.legendBarTrack}>
              <div
                className={styles.legendBarFill}
                style={{
                  width: `${(slice.pct * 100).toFixed(1)}%`,
                  background: slice.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
