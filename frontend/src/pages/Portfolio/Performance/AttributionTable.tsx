import { useMemo } from 'react';
import type { AttributionResult, SectorAttribution } from '../types';
import { fmtPct, gainColor } from '../types';
import styles from './AttributionTable.module.css';

interface Props {
  attribution: AttributionResult | null;
  onRefreshProfiles?: () => void;
}

function fmtWeight(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function fmtEffect(n: number): string {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${(n * 100).toFixed(2)}%`;
}

export function AttributionTable({ attribution, onRefreshProfiles }: Props) {
  const sorted = useMemo(() => {
    if (!attribution) return [];
    return [...attribution.sectors].sort(
      (a, b) => Math.abs(b.allocation_effect) - Math.abs(a.allocation_effect),
    );
  }, [attribution]);

  const unknownCount = useMemo(() => {
    if (!attribution) return 0;
    const unknownSector = attribution.sectors.find(
      (s) => s.sector === 'Unknown' || s.sector === 'unknown',
    );
    return unknownSector ? Math.round(unknownSector.port_weight * 100) : 0;
  }, [attribution]);

  if (!attribution) {
    return <div className={styles.empty}>No attribution data available</div>;
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Sector</th>
            <th className={styles.thRight}>Port Wt</th>
            <th className={styles.thRight}>Bench Wt</th>
            <th className={styles.thRight}>Port Ret</th>
            <th className={styles.thRight}>Bench Ret</th>
            <th className={styles.thRight}>Allocation</th>
            <th className={styles.thRight}>Selection</th>
            <th className={styles.thRight}>Interaction</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row: SectorAttribution) => (
            <tr key={row.sector} className={styles.tr}>
              <td className={styles.td}>{row.sector}</td>
              <td className={styles.tdRight}>{fmtWeight(row.port_weight)}</td>
              <td className={styles.tdRight}>{fmtWeight(row.bench_weight)}</td>
              <td
                className={styles.tdRight}
                style={{ color: gainColor(row.port_return) }}
              >
                {fmtPct(row.port_return)}
              </td>
              <td
                className={styles.tdRight}
                style={{ color: gainColor(row.bench_return) }}
              >
                {fmtPct(row.bench_return)}
              </td>
              <td
                className={styles.tdRight}
                style={{ color: gainColor(row.allocation_effect) }}
              >
                {fmtEffect(row.allocation_effect)}
              </td>
              <td
                className={styles.tdRight}
                style={{ color: gainColor(row.selection_effect) }}
              >
                {fmtEffect(row.selection_effect)}
              </td>
              <td
                className={styles.tdRight}
                style={{ color: gainColor(row.interaction_effect) }}
              >
                {fmtEffect(row.interaction_effect)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className={styles.footerRow}>
            <td className={styles.footerLabel} colSpan={5}>
              Total
            </td>
            <td
              className={styles.footerValue}
              style={{ color: gainColor(attribution.total_allocation) }}
            >
              {fmtEffect(attribution.total_allocation)}
            </td>
            <td
              className={styles.footerValue}
              style={{ color: gainColor(attribution.total_selection) }}
            >
              {fmtEffect(attribution.total_selection)}
            </td>
            <td
              className={styles.footerValue}
              style={{ color: gainColor(attribution.total_interaction) }}
            >
              {fmtEffect(attribution.total_interaction)}
            </td>
          </tr>
          <tr className={styles.alphaRow}>
            <td className={styles.alphaLabel} colSpan={5}>
              Total Alpha
            </td>
            <td
              className={styles.alphaValue}
              colSpan={3}
              style={{ color: gainColor(attribution.total_alpha) }}
            >
              {fmtEffect(attribution.total_alpha)}
            </td>
          </tr>
        </tfoot>
      </table>

      {unknownCount > 0 && (
        <div className={styles.unknownNote}>
          Positions with unknown sector detected.
          {onRefreshProfiles && (
            <>
              {' '}
              <button className={styles.refreshLink} onClick={onRefreshProfiles}>
                Refresh company data
              </button>{' '}
              to classify.
            </>
          )}
        </div>
      )}
    </div>
  );
}
