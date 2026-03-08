import type { FinancialRow } from '../types';
import type { LineItemDef } from './statementDefs';
import styles from './StatementTable.module.css';

interface StatementTableProps {
  data: FinancialRow[];
  definition: LineItemDef[];
}

function formatMillions(val: number | null): string {
  if (val == null) return '--';
  const m = val / 1e6;
  if (val < 0) return `(${Math.abs(m).toLocaleString('en-US', { maximumFractionDigits: 0 })})`;
  return m.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function formatPct(val: number | null): string {
  if (val == null) return '--';
  return `${(val * 100).toFixed(1)}%`;
}

function formatPerShare(val: number | null): string {
  if (val == null) return '--';
  if (val < 0) return `(${Math.abs(val).toFixed(2)})`;
  return val.toFixed(2);
}

function formatRatio(val: number | null): string {
  if (val == null) return '--';
  return val.toFixed(2);
}

function formatValue(val: number | null, format?: string): string {
  switch (format) {
    case 'millions': return formatMillions(val);
    case 'pct': return formatPct(val);
    case 'perShare': return formatPerShare(val);
    case 'ratio': return formatRatio(val);
    default: return val == null ? '--' : String(val);
  }
}

function isNegative(val: number | null, format?: string): boolean {
  if (val == null) return false;
  if (format === 'millions' || format === 'perShare') return val < 0;
  return false;
}

function getValue(def: LineItemDef, row: FinancialRow, prevRow?: FinancialRow): number | null {
  if (def.computeFn) return def.computeFn(row, prevRow);
  const v = row[def.key];
  if (v == null) return null;
  if (typeof v === 'string') return null;
  return v;
}

export function StatementTable({ data, definition }: StatementTableProps) {
  const sorted = [...data].sort((a, b) => b.fiscal_year - a.fiscal_year);
  const years = sorted.map((r) => r.fiscal_year);

  let zebraIndex = 0;

  return (
    <div className={styles.wrapper ?? ''}>
      <table className={styles.table ?? ''}>
        <thead>
          <tr className={styles.headerRow ?? ''}>
            <th className={styles.thLabel ?? ''}>Line Item</th>
            {years.map((y) => (
              <th key={y} className={styles.thYear ?? ''}>{y}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {definition.map((def) => {
            const isBold = def.isBold ?? false;
            let rowClass: string;

            if (isBold) {
              rowClass = styles.rowBold ?? '';
            } else {
              rowClass = zebraIndex % 2 === 0 ? styles.rowOdd ?? '' : styles.rowEven ?? '';
              zebraIndex++;
            }

            const labelClasses = [
              styles.tdLabel ?? '',
              def.isComputed ? styles.tdLabelComputed ?? '' : '',
            ].filter(Boolean).join(' ');

            return (
              <tr key={def.key} className={rowClass}>
                <td
                  className={labelClasses}
                  style={{ paddingLeft: 16 + (def.indent ?? 0) * 16 }}
                >
                  {def.label}
                </td>
                {sorted.map((row, colIdx) => {
                  const prevRow = colIdx < sorted.length - 1 ? sorted[colIdx + 1] : undefined;
                  const val = getValue(def, row, prevRow);
                  const formatted = formatValue(val, def.format);
                  const neg = isNegative(val, def.format);

                  return (
                    <td
                      key={row.fiscal_year}
                      className={`${styles.tdValue ?? ''} ${neg ? styles.tdValueNeg ?? '' : ''}`}
                    >
                      {formatted}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className={styles.footer ?? ''}>
        All values in $M except per-share data and ratios.
      </div>
    </div>
  );
}
