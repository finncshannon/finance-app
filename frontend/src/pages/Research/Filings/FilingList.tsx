import { type FilingSummary } from '../types';
import styles from './FilingList.module.css';

interface FilingListProps {
  filings: FilingSummary[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function extractYear(dateStr: string): string {
  return new Date(dateStr).getFullYear().toString();
}

function formBadgeClass(formType: string): string {
  const base = styles.formBadge ?? '';
  if (formType === '10-K') return `${base} ${styles.form10K ?? ''}`;
  if (formType === '10-Q') return `${base} ${styles.form10Q ?? ''}`;
  if (formType === '8-K') return `${base} ${styles.form8K ?? ''}`;
  return base;
}

export function FilingList({ filings, selectedId, onSelect }: FilingListProps) {
  if (filings.length === 0) {
    return <div className={styles.empty ?? ''}>No filings found</div>;
  }

  return (
    <div className={styles.list ?? ''}>
      <table className={styles.table ?? ''}>
        <thead>
          <tr>
            <th className={styles.th ?? ''}>Form</th>
            <th className={styles.th ?? ''}>Period</th>
            <th className={styles.th ?? ''}>Filed</th>
          </tr>
        </thead>
        <tbody>
          {filings.map((f) => (
            <tr
              key={f.id}
              className={`${styles.tr ?? ''} ${f.id === selectedId ? styles.trActive ?? '' : ''}`}
              onClick={() => onSelect(f.id)}
            >
              <td className={styles.td ?? ''}>
                <span className={formBadgeClass(f.form_type)}>{f.form_type}</span>
              </td>
              <td className={styles.td ?? ''}>{extractYear(f.filing_date)}</td>
              <td className={styles.td ?? ''}>{formatDate(f.filing_date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
