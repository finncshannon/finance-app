import { useState, useEffect, useMemo } from 'react';
import { api } from '../../../services/api';
import type { EnhancedIncomeResult, Transaction } from '../types';
import { fmtDollar, fmtPct, fmtShares } from '../types';
import { DividendChart } from './DividendChart';
import { DividendCalendar } from './DividendCalendar';
import { UpcomingDividends } from './UpcomingDividends';
import styles from './IncomeTab.module.css';

interface Props {
  selectedAccount: string;
}

type PositionSortKey = 'ticker' | 'annual_income' | 'yield_on_cost' | 'market_yield' | 'shares' | 'dividend_rate' | 'cost_basis_per_share';
type SortKey = 'transaction_date' | 'ticker' | 'total_amount';
type SortDir = 'asc' | 'desc';

export function IncomeTab({ selectedAccount }: Props) {
  const [incomeData, setIncomeData] = useState<EnhancedIncomeResult | null>(null);
  const [divTxns, setDivTxns] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('transaction_date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [posSortKey, setPosSortKey] = useState<PositionSortKey>('annual_income');
  const [posSortDir, setPosSortDir] = useState<SortDir>('desc');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    const accountParam = selectedAccount && selectedAccount !== 'all'
      ? `?account=${encodeURIComponent(selectedAccount)}`
      : '';

    Promise.all([
      api.get<EnhancedIncomeResult>(`/api/v1/portfolio/income${accountParam}`),
      api.get<{ transactions: Transaction[] }>('/api/v1/portfolio/transactions?type=DIVIDEND'),
    ])
      .then(([income, txData]) => {
        if (cancelled) return;
        setIncomeData(income);
        setDivTxns(txData.transactions);
      })
      .catch((ex) => {
        if (cancelled) return;
        setError(ex instanceof Error ? ex.message : 'Failed to load income data');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedAccount]);

  // YTD Income: sum dividend transactions from current year
  const currentYear = new Date().getFullYear();
  const ytdIncome = useMemo(() => {
    const startOfYear = `${currentYear}-01-01`;
    return divTxns
      .filter((tx) => tx.transaction_date >= startOfYear)
      .reduce((sum, tx) => sum + (tx.total_amount ?? 0), 0);
  }, [divTxns, currentYear]);

  // Sorted dividend transactions for history table
  const sortedTxns = useMemo(() => {
    const clone = [...divTxns];
    clone.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'transaction_date':
          cmp = a.transaction_date.localeCompare(b.transaction_date);
          break;
        case 'ticker':
          cmp = a.ticker.localeCompare(b.ticker);
          break;
        case 'total_amount':
          cmp = (a.total_amount ?? 0) - (b.total_amount ?? 0);
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return clone;
  }, [divTxns, sortKey, sortDir]);

  // Sorted positions for yield-on-cost table
  const sortedPositions = useMemo(() => {
    if (!incomeData?.positions) return [];
    const clone = [...incomeData.positions];
    clone.sort((a, b) => {
      const av = a[posSortKey];
      const bv = b[posSortKey];
      let cmp = 0;
      if (typeof av === 'string' && typeof bv === 'string') {
        cmp = av.localeCompare(bv);
      } else {
        cmp = ((av as number) ?? 0) - ((bv as number) ?? 0);
      }
      return posSortDir === 'asc' ? cmp : -cmp;
    });
    return clone;
  }, [incomeData, posSortKey, posSortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'ticker' ? 'asc' : 'desc');
    }
  };

  const handlePosSort = (key: PositionSortKey) => {
    if (posSortKey === key) {
      setPosSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setPosSortKey(key);
      setPosSortDir(key === 'ticker' ? 'asc' : 'desc');
    }
  };

  const arrow = (key: SortKey) => {
    if (sortKey !== key) return null;
    return <span style={{ fontSize: 9, marginLeft: 2 }}>{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  };

  const posArrow = (key: PositionSortKey) => {
    if (posSortKey !== key) return null;
    return <span style={{ fontSize: 9, marginLeft: 2 }}>{posSortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  };

  if (loading) {
    return <div className={styles.loading}>Loading income data...</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  const summary = incomeData?.summary;

  // Non-dividend empty state (Task 7)
  if (summary && summary.dividend_position_count === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>📈</div>
          <h3 className={styles.emptyTitle}>No Dividend Income</h3>
          <p className={styles.emptyText}>
            Your current holdings generate returns through capital appreciation.
            None of your {summary.total_position_count} position{summary.total_position_count !== 1 ? 's' : ''} currently pay dividends.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Enhanced Summary Header (Task 2) */}
      <div className={styles.card}>
        <div className={styles.summaryGrid}>
          <div>
            <div className={styles.metricLabel}>Annual Income</div>
            <div className={styles.metricValueLg}>{fmtDollar(summary?.total_annual_income ?? 0)}</div>
          </div>
          <div>
            <div className={styles.metricLabel}>Monthly Income</div>
            <div className={styles.metricValue}>{fmtDollar(summary?.total_monthly_income ?? 0)}</div>
          </div>
          <div>
            <div className={styles.metricLabel}>Yield on Cost</div>
            <div className={styles.metricValue}>{fmtPct(summary?.yield_on_cost ?? null)}</div>
          </div>
          <div>
            <div className={styles.metricLabel}>Yield on Market</div>
            <div className={styles.metricValue}>{fmtPct(summary?.yield_on_market ?? null)}</div>
          </div>
          <div>
            <div className={styles.metricLabel}>Dividend Positions</div>
            <div className={styles.metricValue}>
              {summary?.dividend_position_count ?? 0} / {summary?.total_position_count ?? 0}
            </div>
          </div>
          <div>
            <div className={styles.metricLabel}>YTD Income</div>
            <div className={styles.metricValue}>{fmtDollar(ytdIncome)}</div>
          </div>
        </div>
      </div>

      {/* Stacked Dividend Chart (Task 3) */}
      <div className={styles.card}>
        <h3 className={styles.chartTitle}>Monthly Dividend Income ({currentYear})</h3>
        <DividendChart transactions={divTxns} />
      </div>

      {/* Monthly Calendar Breakdown (Task 4) */}
      <div className={styles.card}>
        <h3 className={styles.chartTitle}>Monthly Breakdown</h3>
        <DividendCalendar divTxns={divTxns} />
      </div>

      {/* Yield-on-Cost Positions Table (Task 5) */}
      {sortedPositions.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.chartTitle}>Dividend Positions</h3>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th} onClick={() => handlePosSort('ticker')}>
                    Ticker{posArrow('ticker')}
                  </th>
                  <th className={styles.thRight} onClick={() => handlePosSort('shares')}>
                    Shares{posArrow('shares')}
                  </th>
                  <th className={styles.thRight} onClick={() => handlePosSort('dividend_rate')}>
                    Div Rate{posArrow('dividend_rate')}
                  </th>
                  <th className={styles.thRight} onClick={() => handlePosSort('annual_income')}>
                    Annual Income{posArrow('annual_income')}
                  </th>
                  <th className={styles.thRight} onClick={() => handlePosSort('cost_basis_per_share')}>
                    Cost Basis{posArrow('cost_basis_per_share')}
                  </th>
                  <th className={styles.thRight} onClick={() => handlePosSort('yield_on_cost')}>
                    Yield on Cost{posArrow('yield_on_cost')}
                  </th>
                  <th className={styles.thRight} onClick={() => handlePosSort('market_yield')}>
                    Market Yield{posArrow('market_yield')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedPositions.map((p, i) => (
                  <tr key={p.ticker} className={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                    <td className={styles.td}>
                      <span className={styles.tickerBadge}>{p.ticker}</span>
                    </td>
                    <td className={styles.tdRight}>{fmtShares(p.shares)}</td>
                    <td className={styles.tdRight}>{fmtDollar(p.dividend_rate)}</td>
                    <td className={styles.tdRight}>{fmtDollar(p.annual_income)}</td>
                    <td className={styles.tdRight}>{fmtDollar(p.cost_basis_per_share)}</td>
                    <td className={`${styles.tdRight} ${styles.yocValue}`}>
                      {p.yield_on_cost != null ? fmtPct(p.yield_on_cost) : '—'}
                    </td>
                    <td className={styles.tdRight}>
                      {p.market_yield != null ? fmtPct(p.market_yield) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Upcoming Dividends (Task 6) */}
      <div className={styles.card}>
        <h3 className={styles.chartTitle}>Upcoming Dividend Events</h3>
        <UpcomingDividends selectedAccount={selectedAccount} />
      </div>

      {/* Dividend History Table */}
      <div className={styles.card}>
        <h3 className={styles.chartTitle}>Dividend History</h3>
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th} onClick={() => handleSort('transaction_date')}>
                  Date{arrow('transaction_date')}
                </th>
                <th className={styles.th} onClick={() => handleSort('ticker')}>
                  Ticker{arrow('ticker')}
                </th>
                <th className={styles.thRight} onClick={() => handleSort('total_amount')}>
                  Amount{arrow('total_amount')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedTxns.length === 0 ? (
                <tr>
                  <td className={styles.td} colSpan={3} style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                    No dividend transactions recorded
                  </td>
                </tr>
              ) : (
                sortedTxns.map((tx, i) => (
                  <tr key={tx.id} className={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                    <td className={styles.td}>{tx.transaction_date}</td>
                    <td className={styles.td}>
                      <span className={styles.tickerBadge}>{tx.ticker}</span>
                    </td>
                    <td className={styles.tdRight}>{fmtDollar(tx.total_amount)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
