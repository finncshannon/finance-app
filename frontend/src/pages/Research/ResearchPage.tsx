import { useState, useEffect, useCallback } from 'react';
import { useUIStore } from '../../stores/uiStore';
import { useResearchStore } from '../../stores/researchStore';
import { WatchlistPicker } from '../../components/ui/WatchlistPicker/WatchlistPicker';
import { useTickerNavigation } from '../../hooks/useTickerNavigation';
import { api } from '../../services/api';
import type { CompanyProfile } from './types';
import { TickerSearch } from './TickerSearch';
import { FunctionGrid } from './FunctionGrid/FunctionGrid';
import { FilingsTab } from './Filings/FilingsTab';
import { FinancialsTab } from './Financials/FinancialsTab';
import { RatiosTab } from './Ratios/RatiosTab';
import { ProfileTab } from './Profile/ProfileTab';
import { PeersTab } from './Peers/PeersTab';
import { NewsTab } from './News/NewsTab';
import { PriceChart } from './PriceChart/PriceChart';
import styles from './ResearchPage.module.css';

const VIEW_LABELS: Record<string, string> = {
  chart: 'GP  Price Chart',
  financials: 'FA  Financial Analysis',
  ratios: 'RV  Ratios & Valuation',
  filings: 'CACS  SEC Filings',
  profile: 'DES  Description',
  peers: 'COMP  Peer Comparison',
  news: 'NEWS  News & Headlines',
};

export function ResearchPage() {
  const activeSubTab = useUIStore((s) => s.activeSubTabs['research'] ?? 'home');
  const setSubTab = useUIStore((s) => s.setSubTab);
  const selectedTicker = useResearchStore((s) => s.selectedTicker);
  const setSelectedTicker = useResearchStore((s) => s.setSelectedTicker);

  const [tickerInput, setTickerInput] = useState(selectedTicker);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setTickerInput(selectedTicker);
  }, [selectedTicker]);

  const { showWatchlistPicker, setShowWatchlistPicker } =
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

  const handleSelect = (ticker: string) => {
    const t = ticker.trim().toUpperCase();
    if (t) {
      setSelectedTicker(t);
      setTickerInput(t);
      setSubTab('research', 'home');
    }
  };

  const goHome = () => setSubTab('research', 'home');
  const goToFunction = (id: string) => setSubTab('research', id);

  const isHome = activeSubTab === 'home';

  const renderView = () => {
    if (!selectedTicker) return null;
    switch (activeSubTab) {
      case 'home':
        return (
          <FunctionGrid
            ticker={selectedTicker}
            profile={profile}
            onSelectFunction={goToFunction}
          />
        );
      case 'chart':
        return <PriceChart ticker={selectedTicker} />;
      case 'financials':
        return <FinancialsTab ticker={selectedTicker} />;
      case 'ratios':
        return <RatiosTab ticker={selectedTicker} />;
      case 'filings':
        return <FilingsTab ticker={selectedTicker} />;
      case 'profile':
        return <ProfileTab ticker={selectedTicker} profile={profile} />;
      case 'peers':
        return <PeersTab ticker={selectedTicker} />;
      case 'news':
        return <NewsTab ticker={selectedTicker} />;
      default:
        return null;
    }
  };

  return (
    <div className={styles.page}>
      {/* Top bar */}
      <div className={styles.topBar}>
        <div className={styles.searchGroup}>
          <TickerSearch
            value={tickerInput}
            onChange={setTickerInput}
            onSelect={handleSelect}
          />
        </div>

        {!isHome && selectedTicker && (
          <div className={styles.navGroup}>
            <button className={styles.backBtn} onClick={goHome}>
              &larr; {selectedTicker}
            </button>
            <span className={styles.viewLabel}>{VIEW_LABELS[activeSubTab] ?? activeSubTab}</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className={styles.content}>
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
            <div className={styles.emptyTitle}>Enter a ticker to begin research</div>
          </div>
        ) : (
          renderView()
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
