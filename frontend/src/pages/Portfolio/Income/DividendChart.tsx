import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import type { Transaction } from '../types';
import { fmtDollar } from '../types';
import styles from './DividendChart.module.css';

interface Props {
  transactions: Transaction[];
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const TICKER_COLORS = [
  'var(--accent-primary)', '#6366F1', '#F59E0B', '#EF4444',
  '#10B981', '#F97316', '#EC4899', '#14B8A6',
];

function MonthlyTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((s: number, p: any) => s + (p.value || 0), 0);
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipMonth}>{label}</div>
      {payload.map((p: any) => (
        p.value > 0 && (
          <div key={p.dataKey} className={styles.tooltipRow}>
            <span className={styles.tooltipDot} style={{ background: p.fill }} />
            <span className={styles.tooltipLabel}>{p.dataKey}</span>
            <span className={styles.tooltipValue}>{fmtDollar(p.value)}</span>
          </div>
        )
      ))}
      <div className={styles.tooltipTotal}>Total: {fmtDollar(total)}</div>
    </div>
  );
}

export function DividendChart({ transactions }: Props) {
  const currentYear = new Date().getFullYear();

  // Get top 8 tickers by annual income contribution
  const topTickers = useMemo(() => {
    const totals = new Map<string, number>();
    for (const tx of transactions) {
      const d = new Date(tx.transaction_date);
      if (d.getFullYear() === currentYear) {
        totals.set(tx.ticker, (totals.get(tx.ticker) ?? 0) + (tx.total_amount ?? 0));
      }
    }
    return [...totals.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([ticker]) => ticker);
  }, [transactions, currentYear]);

  const hasOther = useMemo(() => {
    const allTickers = new Set<string>();
    for (const tx of transactions) {
      const d = new Date(tx.transaction_date);
      if (d.getFullYear() === currentYear && (tx.total_amount ?? 0) > 0) {
        allTickers.add(tx.ticker);
      }
    }
    return allTickers.size > topTickers.length;
  }, [transactions, currentYear, topTickers]);

  const chartData = useMemo(() => {
    const months = MONTHS.map((month) => {
      const row: Record<string, any> = { month };
      for (const t of topTickers) row[t] = 0;
      row.Other = 0;
      return row;
    });

    for (const tx of transactions) {
      const d = new Date(tx.transaction_date);
      if (d.getFullYear() !== currentYear) continue;
      const monthIdx = d.getMonth();
      const amount = tx.total_amount ?? 0;
      if (amount <= 0) continue;

      const row = months[monthIdx];
      if (!row) continue;
      if (topTickers.includes(tx.ticker)) {
        row[tx.ticker] += amount;
      } else {
        row.Other += amount;
      }
    }
    return months;
  }, [transactions, currentYear, topTickers]);

  const hasData = chartData.some((m) =>
    topTickers.some((t) => m[t] > 0) || m.Other > 0
  );

  if (!hasData) {
    return <div className={styles.empty}>No dividend income recorded this year</div>;
  }

  return (
    <div className={styles.container}>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#333" />
          <YAxis tickFormatter={(v) => `$${v}`} tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#333" />
          <Tooltip content={<MonthlyTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11, color: '#A3A3A3' }}
          />
          {topTickers.map((ticker, i) => (
            <Bar
              key={ticker}
              dataKey={ticker}
              stackId="income"
              fill={TICKER_COLORS[i % TICKER_COLORS.length]}
              radius={i === topTickers.length - 1 && !hasOther ? [2, 2, 0, 0] : undefined}
            />
          ))}
          {hasOther && (
            <Bar
              dataKey="Other"
              stackId="income"
              name="Other"
              fill="#666"
              radius={[2, 2, 0, 0]}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
