import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../../services/api';
import type { Account, Transaction } from '../types';
import { fmtDollar, fmtShares } from '../types';
import { RecordTransactionModal } from '../Holdings/RecordTransactionModal';
import { ImportModal } from '../Holdings/ImportModal';
import styles from './TransactionsTab.module.css';

interface Props {
  accounts: Account[];
  onRefresh: () => void;
}

const TX_TYPES = ['BUY', 'SELL', 'DIVIDEND', 'DRIP', 'SPLIT', 'ADJUSTMENT'] as const;
const PAGE_SIZE = 50;

type SortKey = 'transaction_date' | 'transaction_type' | 'ticker' | 'shares' | 'price_per_share' | 'total_amount' | 'fees' | 'account';
type SortDir = 'asc' | 'desc';

function typeBadgeClass(txType: string): string {
  switch (txType) {
    case 'BUY': return styles.badgeBuy ?? '';
    case 'SELL': return styles.badgeSell ?? '';
    case 'DIVIDEND': return styles.badgeDividend ?? '';
    case 'DRIP': return styles.badgeDrip ?? '';
    case 'SPLIT': return styles.badgeSplit ?? '';
    default: return styles.badgeDefault ?? '';
  }
}

export function TransactionsTab({ accounts, onRefresh }: Props) {
  // Filter state
  const [tickerFilter, setTickerFilter] = useState('');
  const [typeFilters, setTypeFilters] = useState<Set<string>>(new Set());
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [accountFilter, setAccountFilter] = useState('');

  // Applied filters (only applied on button click)
  const [appliedFilters, setAppliedFilters] = useState({
    ticker: '',
    types: new Set<string>(),
    startDate: '',
    endDate: '',
    account: '',
  });

  // Data
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>('transaction_date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(0);
  const [showTxModal, setShowTxModal] = useState(false);
  const [showImport, setShowImport] = useState(false);

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (appliedFilters.ticker) params.set('ticker', appliedFilters.ticker);
    if (appliedFilters.types.size > 0) {
      for (const t of appliedFilters.types) params.append('type', t);
    }
    if (appliedFilters.startDate) params.set('start_date', appliedFilters.startDate);
    if (appliedFilters.endDate) params.set('end_date', appliedFilters.endDate);
    if (appliedFilters.account) params.set('account', appliedFilters.account);

    const qs = params.toString();
    const url = `/api/v1/portfolio/transactions${qs ? `?${qs}` : ''}`;

    try {
      const data = await api.get<{ transactions: Transaction[] }>(url);
      setTransactions(data.transactions);
    } catch {
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [appliedFilters]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const handleApplyFilter = () => {
    setAppliedFilters({
      ticker: tickerFilter.trim().toUpperCase(),
      types: new Set(typeFilters),
      startDate,
      endDate,
      account: accountFilter,
    });
    setPage(0);
  };

  const handleClearFilters = () => {
    setTickerFilter('');
    setTypeFilters(new Set());
    setStartDate('');
    setEndDate('');
    setAccountFilter('');
    setAppliedFilters({ ticker: '', types: new Set(), startDate: '', endDate: '', account: '' });
    setPage(0);
  };

  const toggleTypeFilter = (t: string) => {
    setTypeFilters((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleApplyFilter();
  };

  // Sort
  const sorted = useMemo(() => {
    const clone = [...transactions];
    clone.sort((a, b) => {
      let cmp = 0;
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'string' && typeof bv === 'string') {
        cmp = av.localeCompare(bv);
      } else {
        cmp = ((av as number) ?? 0) - ((bv as number) ?? 0);
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return clone;
  }, [transactions, sortKey, sortDir]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const paginated = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'ticker' || key === 'transaction_type' || key === 'account' ? 'asc' : 'desc');
    }
  };

  const arrow = (key: SortKey) => {
    if (sortKey !== key) return null;
    return <span className={styles.sortArrow}>{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  };

  const handleTxSuccess = () => {
    setShowTxModal(false);
    fetchTransactions();
    onRefresh();
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h3 className={styles.headerTitle}>Transactions</h3>
        <div className={styles.headerActions}>
          <button className={styles.btnSecondary} onClick={() => setShowImport(true)}>
            Import Transactions
          </button>
          <button className={styles.btnPrimary} onClick={() => setShowTxModal(true)}>
            + Record Transaction
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className={styles.filterBar}>
        <input
          className={styles.filterInput}
          type="text"
          placeholder="Ticker..."
          value={tickerFilter}
          onChange={(e) => setTickerFilter(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        <div className={styles.filterSep} />

        <div className={styles.checkboxGroup}>
          {TX_TYPES.map((t) => (
            <label key={t} className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={typeFilters.has(t)}
                onChange={() => toggleTypeFilter(t)}
              />
              {t}
            </label>
          ))}
        </div>

        <div className={styles.filterSep} />

        <input
          className={styles.dateInput}
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          title="Start date"
        />
        <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>to</span>
        <input
          className={styles.dateInput}
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          title="End date"
        />

        <div className={styles.filterSep} />

        <select
          className={styles.filterSelect}
          value={accountFilter}
          onChange={(e) => setAccountFilter(e.target.value)}
        >
          <option value="">All Accounts</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.name}>{a.name}</option>
          ))}
        </select>

        <button className={styles.filterBtn} onClick={handleApplyFilter}>Filter</button>
        <button className={styles.clearLink} onClick={handleClearFilters}>Clear</button>
      </div>

      {/* Table */}
      <div className={styles.tableWrapper}>
        {loading ? (
          <div className={styles.loading}>Loading transactions...</div>
        ) : paginated.length === 0 ? (
          <div className={styles.empty}>No transactions found</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th} onClick={() => handleSort('transaction_date')}>
                  Date{arrow('transaction_date')}
                </th>
                <th className={styles.th} onClick={() => handleSort('transaction_type')}>
                  Type{arrow('transaction_type')}
                </th>
                <th className={styles.th} onClick={() => handleSort('ticker')}>
                  Ticker{arrow('ticker')}
                </th>
                <th className={styles.thRight} onClick={() => handleSort('shares')}>
                  Shares{arrow('shares')}
                </th>
                <th className={styles.thRight} onClick={() => handleSort('price_per_share')}>
                  Price{arrow('price_per_share')}
                </th>
                <th className={styles.thRight} onClick={() => handleSort('total_amount')}>
                  Amount{arrow('total_amount')}
                </th>
                <th className={styles.thRight} onClick={() => handleSort('fees')}>
                  Fees{arrow('fees')}
                </th>
                <th className={styles.th} onClick={() => handleSort('account')}>
                  Account{arrow('account')}
                </th>
                <th className={styles.th}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {paginated.map((tx, i) => (
                <tr key={tx.id} className={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  <td className={styles.td}>{tx.transaction_date}</td>
                  <td className={styles.td}>
                    <span className={typeBadgeClass(tx.transaction_type)}>
                      {tx.transaction_type}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.tickerMono}>{tx.ticker}</span>
                  </td>
                  <td className={styles.tdRight}>
                    {tx.shares != null ? fmtShares(tx.shares) : '--'}
                  </td>
                  <td className={styles.tdRight}>{fmtDollar(tx.price_per_share)}</td>
                  <td className={styles.tdRight}>{fmtDollar(tx.total_amount)}</td>
                  <td className={styles.tdRight}>{tx.fees > 0 ? fmtDollar(tx.fees) : '--'}</td>
                  <td className={styles.td}>{tx.account ?? '--'}</td>
                  <td className={styles.tdNotes} title={tx.notes ?? undefined}>
                    {tx.notes ?? '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {!loading && sorted.length > PAGE_SIZE && (
        <div className={styles.pagination}>
          <button
            className={styles.pageBtn}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Previous
          </button>
          <span className={styles.pageInfo}>
            Page {page + 1} of {totalPages} ({sorted.length} transactions)
          </span>
          <button
            className={styles.pageBtn}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            Next
          </button>
        </div>
      )}

      {/* Record Transaction Modal */}
      {showTxModal && (
        <RecordTransactionModal
          accounts={accounts}
          onClose={() => setShowTxModal(false)}
          onSuccess={handleTxSuccess}
        />
      )}

      {/* Import Transactions Modal */}
      {showImport && (
        <ImportModal
          onClose={() => setShowImport(false)}
          onSuccess={() => { setShowImport(false); fetchTransactions(); onRefresh(); }}
          defaultImportType="transactions"
        />
      )}
    </div>
  );
}
