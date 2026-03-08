import { useState, useEffect, useCallback } from 'react';
import { useUIStore } from '../../stores/uiStore';
import { useResearchStore } from '../../stores/researchStore';
import { Tabs } from '../../components/ui/Tabs/Tabs';
import { TickerHeaderBar } from '../../components/ui/TickerHeaderBar/TickerHeaderBar';
import { WatchlistPicker } from '../../components/ui/WatchlistPicker/WatchlistPicker';
import { useTickerNavigation } from '../../hooks/useTickerNavigation';
import { api } from '../../services/api';
import type { CompanyProfile } from './types';
import { FilingsTab } from './Filings/FilingsTab';
import { FinancialsTab } from './Financials/FinancialsTab';
import { RatiosTab } from './Ratios/RatiosTab';
import { ProfileTab } from './Profile/ProfileTab';
import { PeersTab } from './Peers/PeersTab';
import { PriceChart } from './PriceChart/PriceChart';
import styles from './ResearchPage.module.css';

const TABS = [
  { id: 'filings', label: 'Filings' },
  { id: 'financials', label: 'Financials' },
  { id: 'ratios', label: 'Ratios' },
  { id: 'profile', label: 'Profile' },
  { id: 'peers', label: 'Peers' },
];

export function ResearchPage() {
  const activeSubTab = useUIStore((s) => s.activeSubTabs['research'] ?? 'filings');
  const setSubTab = useUIStore((s) => s.setSubTab);
  const selectedTicker = useResearchStore((s) => s.selectedTicker);
  const setSelectedTicker = useResearchStore((s) => s.setSelectedTicker);

  const [tickerInput, setTickerInput] = useState(selectedTicker);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Sync input when store changes externally (e.g. navigation from Scanner/Dashboard)
  useEffect(() => {
    setTickerInput(selectedTicker);
  }, [selectedTicker]);

  const { handleHeaderNavigate, showWatchlistPicker, setShowWatchlistPicker, openInModelBuilder } =
    useTickerNavigation(selectedTicker);

  const loadProfile = useCallback(async (ticker: string) => {
    if (!ticker) return;
    setLoading(true);
    setLoadError(null);
    try {
      const data = await api.get<CompanyProfile>(`/api/v1/research/${ticker}/profile`);
      setProfile(data);
    } catch (err) {
      setProfile(null);
      setLoadError(err instanceof Error ? err.message : 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedTicker) {
      loadProfile(selectedTicker);
    }
  }, [selectedTicker, loadProfile]);

  const handleSearch = () => {
    const t = tickerInput.trim().toUpperCase();
    if (t) {
      setSelectedTicker(t);
      setTickerInput(t);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const renderTab = () => {
    if (!selectedTicker) return null;
    switch (activeSubTab) {
      case 'filings': return <FilingsTab ticker={selectedTicker} />;
      case 'financials': return <FinancialsTab ticker={selectedTicker} />;
      case 'ratios': return <RatiosTab ticker={selectedTicker} />;
      case 'profile': return <ProfileTab ticker={selectedTicker} profile={profile} />;
      case 'peers': return <PeersTab ticker={selectedTicker} />;
      default: return null;
    }
  };

  const quote = profile?.quote;

  return (
    <div className={styles.page}>
      {/* Search Bar */}
      <div className={styles.searchBar}>
        <input
          className={styles.searchInput}
          type="text"
          placeholder="Enter ticker..."
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className={styles.searchBtn} onClick={handleSearch}>Go</button>
      </div>

      {/* Ticker Header */}
      {selectedTicker && profile && quote && (
        <TickerHeaderBar
          ticker={selectedTicker}
          companyName={profile.company_name}
          sector={profile.sector}
          industry={profile.industry}
          exchange={profile.exchange}
          price={quote.current_price ?? 0}
          dayChange={quote.day_change ?? 0}
          dayChangePct={quote.day_change_pct ?? 0}
          volume={quote.volume}
          onNavigate={handleHeaderNavigate}
        />
      )}

      {/* Price Chart */}
      {selectedTicker && <PriceChart ticker={selectedTicker} />}

      {/* Build Model button */}
      {selectedTicker && (
        <div className={styles.searchBar} style={{ borderBottom: 'none', paddingTop: 0 }}>
          <button className={styles.searchBtn} onClick={openInModelBuilder}>
            Build Model
          </button>
        </div>
      )}

      {/* Tabs */}
      {selectedTicker && (
        <Tabs
          tabs={TABS}
          activeTab={activeSubTab}
          onTabChange={(id) => setSubTab('research', id)}
        />
      )}

      {/* Content */}
      <div className={styles.tabContent}>
        {loading && !profile ? (
          <div className={styles.loading}>Loading...</div>
        ) : loadError ? (
          <div className={styles.errorState}>
            <div className={styles.errorText}>{loadError}</div>
            <button className={styles.retryBtn} onClick={() => loadProfile(selectedTicker)}>
              Retry
            </button>
          </div>
        ) : !selectedTicker ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyTitle}>Enter a ticker above to begin research</div>
            <div className={styles.emptySubtitle}>
              Search for a company to view filings, financial statements, ratios, and more.
            </div>
          </div>
        ) : (
          renderTab()
        )}
      </div>

      {showWatchlistPicker && selectedTicker && (
        <WatchlistPicker
          ticker={selectedTicker}
          open={showWatchlistPicker}
          onClose={() => setShowWatchlistPicker(false)}
        />
      )}
    </div>
  );
}
