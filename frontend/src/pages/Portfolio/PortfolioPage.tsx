import { useState, useEffect, useCallback, useRef } from 'react';
import { useUIStore } from '../../stores/uiStore';
import { Tabs } from '../../components/ui/Tabs/Tabs';
import { ExportDropdown } from '../../components/ui/ExportButton/ExportDropdown';
import { api } from '../../services/api';
import { wsManager } from '../../services/websocket';
import { downloadExport } from '../../services/exportService';
import type { Position, Account, PortfolioSummary } from './types';
import { HoldingsTab } from './Holdings/HoldingsTab';
import { PerformanceTab } from './Performance/PerformanceTab';
import { AllocationTab } from './Allocation/AllocationTab';
import { IncomeTab } from './Income/IncomeTab';
import { TransactionsTab } from './Transactions/TransactionsTab';
import { AlertsTab } from './Alerts/AlertsTab';
import { UpcomingEventsTab } from './UpcomingEvents/UpcomingEventsTab';
import { AddPositionModal } from './Holdings/AddPositionModal';
import { ImportModal } from './Holdings/ImportModal';
import styles from './PortfolioPage.module.css';

const TABS = [
  { id: 'holdings', label: 'Holdings' },
  { id: 'performance', label: 'Performance' },
  { id: 'allocation', label: 'Allocation' },
  { id: 'income', label: 'Income' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'upcoming-events', label: 'Upcoming Events' },
];

export function PortfolioPage() {
  const activeSubTab = useUIStore((s) => s.activeSubTabs['portfolio'] ?? 'holdings');
  const setSubTab = useUIStore((s) => s.setSubTab);

  const [positions, setPositions] = useState<Position[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const prevTickerCountRef = useRef(0);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const acctParam = selectedAccount ? `?account=${selectedAccount}` : '';
      const [posData, sumData, acctData] = await Promise.all([
        api.get<{ positions: Position[] }>(`/api/v1/portfolio/positions${acctParam}`),
        api.get<PortfolioSummary>(`/api/v1/portfolio/summary${acctParam}`),
        api.get<{ accounts: Account[] }>('/api/v1/portfolio/accounts'),
      ]);
      setPositions(posData.positions);
      setSummary(sumData);
      setAccounts(acctData.accounts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load portfolio');
    } finally {
      setLoading(false);
    }
  }, [selectedAccount]);

  useEffect(() => { loadData(); }, [loadData]);

  // Subscribe portfolio tickers to WebSocket for live price updates
  useEffect(() => {
    if (positions.length === 0) return;
    if (positions.length === prevTickerCountRef.current) return;
    prevTickerCountRef.current = positions.length;

    const tickers = positions.map((p) => p.ticker);
    wsManager.subscribeTickers(tickers);
  }, [positions]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await loadData();
    } finally {
      setRefreshing(false);
    }
  }, [loadData]);

  const isEmpty = !loading && positions.length === 0;

  const renderTab = () => {
    if (isEmpty && activeSubTab === 'holdings') {
      return (
        <div className={styles.emptyState}>
          <div className={styles.emptyTitle}>No positions yet</div>
          <div className={styles.emptySubtitle}>
            Add your first position or import from your broker
          </div>
          <div className={styles.emptyActions}>
            <button className={styles.actionBtn} onClick={() => setShowAddModal(true)}>
              + Add Position
            </button>
            <button className={styles.secondaryBtn} onClick={() => setShowImportModal(true)}>
              Import CSV
            </button>
          </div>
        </div>
      );
    }

    switch (activeSubTab) {
      case 'holdings':
        return (
          <HoldingsTab
            positions={positions}
            summary={summary}
            accounts={accounts}
            selectedAccount={selectedAccount}
            onRefresh={handleRefresh}
          />
        );
      case 'performance':
        return <PerformanceTab selectedAccount={selectedAccount} />;
      case 'allocation':
        return <AllocationTab positions={positions} accounts={accounts} />;
      case 'income':
        return <IncomeTab selectedAccount={selectedAccount} />;
      case 'transactions':
        return <TransactionsTab accounts={accounts} onRefresh={handleRefresh} />;
      case 'alerts':
        return <AlertsTab />;
      case 'upcoming-events':
        return <UpcomingEventsTab />;
      default:
        return null;
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Portfolio</h2>
        <div className={styles.headerActions}>
          <select
            className={styles.accountSelect}
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
          >
            <option value="">All Accounts</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.name}>{a.name}</option>
            ))}
          </select>
          <button
            className={styles.secondaryBtn}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <ExportDropdown
            options={[
              {
                label: 'Excel (.xlsx)',
                format: 'excel',
                onClick: async () => {
                  const date = new Date().toISOString().slice(0, 10);
                  await downloadExport(
                    '/api/v1/export/portfolio/excel',
                    `portfolio_${date}.xlsx`,
                    {
                      holdings: positions.map((p) => ({
                        ticker: p.ticker,
                        company_name: p.company_name,
                        shares: p.shares_held,
                        cost_basis: p.cost_basis_per_share,
                        current_price: p.current_price,
                        market_value: p.market_value,
                        gain_loss: p.gain_loss,
                        gain_loss_pct: p.gain_loss_pct,
                      })),
                      transactions: [],
                      summary: summary ?? {},
                    },
                  );
                },
              },
              {
                label: 'PDF Report',
                format: 'pdf',
                onClick: async () => {
                  const date = new Date().toISOString().slice(0, 10);
                  await downloadExport(
                    '/api/v1/export/portfolio/pdf',
                    `portfolio_summary_${date}.pdf`,
                    {
                      holdings: positions.map((p) => ({
                        ticker: p.ticker,
                        company_name: p.company_name,
                        shares: p.shares_held,
                        cost_basis: p.cost_basis_per_share,
                        current_price: p.current_price,
                        market_value: p.market_value,
                        gain_loss: p.gain_loss,
                        gain_loss_pct: p.gain_loss_pct,
                      })),
                      summary: summary ?? {},
                    },
                  );
                },
              },
            ]}
          />
          <button className={styles.secondaryBtn} onClick={() => setShowImportModal(true)}>
            Import CSV
          </button>
          <button className={styles.actionBtn} onClick={() => setShowAddModal(true)}>
            + Add Position
          </button>
        </div>
      </div>

      <Tabs
        tabs={TABS}
        activeTab={activeSubTab}
        onTabChange={(id) => setSubTab('portfolio', id)}
      />

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.tabContent}>
        {loading && !positions.length ? (
          <div className={styles.loading}>Loading portfolio...</div>
        ) : (
          renderTab()
        )}
      </div>

      {showAddModal && (
        <AddPositionModal
          accounts={accounts}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => { setShowAddModal(false); handleRefresh(); }}
        />
      )}

      {showImportModal && (
        <ImportModal
          onClose={() => setShowImportModal(false)}
          onSuccess={() => { setShowImportModal(false); handleRefresh(); }}
        />
      )}
    </div>
  );
}
