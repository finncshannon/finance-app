import type { ScenarioComparisonTable } from '../../../types/models';
import { displayModelName } from '../../../utils/displayNames';
import styles from './ScenarioTable.module.css';

interface ScenarioTableProps {
  data: ScenarioComparisonTable;
}

function formatPrice(v: number | null): string {
  if (v == null) return '--';
  return `$${v.toFixed(2)}`;
}

function formatPct(v: number | null): string {
  if (v == null) return '--';
  const pct = v * 100;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

function formatWeight(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

function formatConfidence(v: number | null): string {
  if (v == null) return '--';
  return `${v.toFixed(0)}`;
}

function getUpsideClass(v: number | null): string {
  if (v == null) return styles.neutral ?? '';
  if (v > 0.001) return styles.positive ?? '';
  if (v < -0.001) return styles.negative ?? '';
  return styles.neutral ?? '';
}

function isComposite(name: string): boolean {
  return name.toLowerCase() === 'composite';
}

export function ScenarioTable({ data }: ScenarioTableProps) {
  const { rows } = data;

  return (
    <div className={styles.container}>
      <h4 className={styles.title}>Scenario Comparison</h4>

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead className={styles.thead}>
            <tr>
              <th className={`${styles.th} ${styles.thLeft}`}>Model</th>
              <th className={styles.th}>Bear</th>
              <th className={styles.th}>Base</th>
              <th className={styles.th}>Bull</th>
              <th className={styles.th}>Weight</th>
              <th className={styles.th}>Confidence</th>
              <th className={styles.th}>Upside</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const composite = isComposite(row.model_name);
              const label = displayModelName(row.model_name);

              const rowCls = [
                styles.row,
                composite ? styles.rowComposite : (idx % 2 === 0 ? styles.rowOdd : styles.rowEven),
              ].filter(Boolean).join(' ');

              const modelCls = [
                styles.td,
                styles.tdModel,
                composite ? styles.tdModelComposite : '',
              ].filter(Boolean).join(' ');

              return (
                <tr key={row.model_name} className={rowCls}>
                  <td className={modelCls}>{label}</td>
                  <td className={styles.td}>{formatPrice(row.bear)}</td>
                  <td className={styles.td}>{formatPrice(row.base)}</td>
                  <td className={styles.td}>{formatPrice(row.bull)}</td>
                  <td className={`${styles.td} ${styles.weight}`}>{formatWeight(row.weight)}</td>
                  <td className={`${styles.td} ${styles.confidence}`}>{formatConfidence(row.confidence)}</td>
                  <td className={`${styles.td} ${getUpsideClass(row.upside_base)}`}>
                    {formatPct(row.upside_base)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
