import { useMemo } from 'react';
import type { Transaction } from '../types';
import { fmtDollar } from '../types';
import styles from './DividendCalendar.module.css';

interface Props {
  divTxns: Transaction[];
}

const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

interface MonthData {
  monthIdx: number;
  monthLabel: string;
  total: number;
  tickers: { ticker: string; amount: number }[];
}

export function DividendCalendar({ divTxns }: Props) {
  const currentYear = new Date().getFullYear();

  const monthlyData = useMemo(() => {
    const months: Map<number, Map<string, number>> = new Map();

    for (const tx of divTxns) {
      const d = new Date(tx.transaction_date);
      if (d.getFullYear() !== currentYear) continue;
      const m = d.getMonth();
      const amount = tx.total_amount ?? 0;
      if (amount <= 0) continue;

      if (!months.has(m)) months.set(m, new Map());
      const tickerMap = months.get(m)!;
      tickerMap.set(tx.ticker, (tickerMap.get(tx.ticker) ?? 0) + amount);
    }

    const result: MonthData[] = [];
    for (let i = 0; i < 12; i++) {
      const tickerMap = months.get(i);
      if (!tickerMap || tickerMap.size === 0) continue;

      const tickers = [...tickerMap.entries()]
        .map(([ticker, amount]) => ({ ticker, amount }))
        .sort((a, b) => b.amount - a.amount);

      result.push({
        monthIdx: i,
        monthLabel: MONTH_LABELS[i] ?? '',
        total: tickers.reduce((s, t) => s + t.amount, 0),
        tickers,
      });
    }

    return result;
  }, [divTxns, currentYear]);

  if (monthlyData.length === 0) {
    return null;
  }

  return (
    <div className={styles.container}>
      {monthlyData.map((m) => (
        <div key={m.monthIdx} className={styles.row}>
          <span className={styles.month}>{m.monthLabel}</span>
          <span className={styles.total}>{fmtDollar(m.total)}</span>
          <span className={styles.detail}>
            {m.tickers.map((t) => `${t.ticker} (${fmtDollar(t.amount)})`).join(', ')}
          </span>
        </div>
      ))}
    </div>
  );
}
