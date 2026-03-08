import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import { downloadExport } from '../../../services/exportService';
import { ExportButton } from '../../../components/ui/ExportButton/ExportButton';
import type { FinancialRow } from '../types';
import { INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW_STATEMENT } from './statementDefs';
import { StatementTable } from './StatementTable';
import styles from './FinancialsTab.module.css';

type StatementType = 'income' | 'balance' | 'cashflow';
type PeriodType = 'annual' | 'quarterly';

const STATEMENT_BUTTONS: { id: StatementType; label: string }[] = [
  { id: 'income', label: 'Income Statement' },
  { id: 'balance', label: 'Balance Sheet' },
  { id: 'cashflow', label: 'Cash Flow' },
];

const STATEMENT_DEFS = {
  income: INCOME_STATEMENT,
  balance: BALANCE_SHEET,
  cashflow: CASH_FLOW_STATEMENT,
} as const;

interface FinancialsTabProps {
  ticker: string;
}

export function FinancialsTab({ ticker }: FinancialsTabProps) {
  const [statement, setStatement] = useState<StatementType>('income');
  const [periodType, setPeriodType] = useState<PeriodType>('annual');
  const [financials, setFinancials] = useState<FinancialRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await api.get<{ financials: FinancialRow[] }>(
          `/api/v1/research/${ticker}/financials?period_type=${periodType}&limit=10`,
        );
        if (!cancelled) setFinancials(data.financials);
      } catch {
        if (!cancelled) setFinancials([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [ticker, periodType]);

  return (
    <div className={styles.container ?? ''}>
      <div className={styles.topBar ?? ''}>
        {STATEMENT_BUTTONS.map((btn) => (
          <button
            key={btn.id}
            className={`${styles.stmtBtn ?? ''} ${statement === btn.id ? styles.stmtBtnActive ?? '' : ''}`}
            onClick={() => setStatement(btn.id)}
          >
            {btn.label}
          </button>
        ))}

        <div className={styles.separator ?? ''} />

        <div className={styles.toggleGroup ?? ''}>
          <button
            className={`${styles.toggleBtn ?? ''} ${periodType === 'annual' ? styles.toggleBtnActive ?? '' : ''}`}
            onClick={() => setPeriodType('annual')}
          >
            Annual
          </button>
          <button
            className={`${styles.toggleBtn ?? ''} ${periodType === 'quarterly' ? styles.toggleBtnActive ?? '' : ''}`}
            onClick={() => setPeriodType('quarterly')}
          >
            Quarterly
          </button>
        </div>

        <ExportButton
          label="Export Excel"
          onClick={async () => {
            const date = new Date().toISOString().slice(0, 10);
            await downloadExport(
              `/api/v1/export/research/${ticker}/excel`,
              `${ticker}_financials_${date}.xlsx`,
            );
          }}
        />
      </div>

      <div className={styles.content ?? ''}>
        {loading ? (
          <div className={styles.loading ?? ''}>Loading financials...</div>
        ) : financials.length === 0 ? (
          <div className={styles.empty ?? ''}>No financial data available</div>
        ) : (
          <StatementTable data={financials} definition={STATEMENT_DEFS[statement]} />
        )}
      </div>
    </div>
  );
}
