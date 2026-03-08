import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import { useUIStore } from '../../stores/uiStore';
import type { DashboardSummary } from './types';
import { MarketOverviewWidget } from './MarketOverview/MarketOverviewWidget';
import { PortfolioSummaryWidget } from './PortfolioSummary/PortfolioSummaryWidget';
import { WatchlistWidget } from './Watchlist/WatchlistWidget';
import { RecentModelsWidget } from './RecentModels/RecentModelsWidget';
import { UpcomingEventsWidget } from './UpcomingEvents/UpcomingEventsWidget';
import styles from './DashboardPage.module.css';

const WIDGET_COUNT = 5;
const CASCADE_INTERVAL_MS = 175;

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [animationPhase, setAnimationPhase] = useState(-1);

  const justBooted = useUIStore((s) => s.justBooted);
  const dashboardAnimationPlayed = useUIStore((s) => s.dashboardAnimationPlayed);
  const setDashboardAnimationPlayed = useUIStore((s) => s.setDashboardAnimationPlayed);

  const animationStarted = useRef(false);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<DashboardSummary>('/api/v1/dashboard/summary');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Widget entry animation cascade
  useEffect(() => {
    // Skip animation if not first boot or already played
    if (!justBooted || dashboardAnimationPlayed) {
      setAnimationPhase(WIDGET_COUNT - 1);
      return;
    }

    // Wait for data before animating
    if (!data || animationStarted.current) return;

    animationStarted.current = true;

    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 0; i < WIDGET_COUNT; i++) {
      timers.push(
        setTimeout(() => {
          setAnimationPhase(i);
        }, i * CASCADE_INTERVAL_MS)
      );
    }

    // Mark animation as played after cascade completes
    timers.push(
      setTimeout(() => {
        setDashboardAnimationPlayed(true);
      }, (WIDGET_COUNT - 1) * CASCADE_INTERVAL_MS + 300)
    );

    return () => timers.forEach(clearTimeout);
  }, [justBooted, dashboardAnimationPlayed, data, setDashboardAnimationPlayed]);

  const widgetClass = (index: number): string => {
    return (animationPhase >= index ? styles.widgetVisible : styles.widgetHidden) ?? '';
  };

  if (loading && !data) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.title}>Dashboard</h2>
        <button
          className={styles.refreshBtn}
          onClick={fetchDashboard}
          disabled={loading}
        >
          {loading && <span className={styles.spinner} />}
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      {/* Grid */}
      {data && (
        <div className={styles.grid}>
          {/* Row 1: Market (left) + Portfolio (right) */}
          <div className={`${styles.gridMarket} ${widgetClass(0)}`}>
            <MarketOverviewWidget market={data.market} />
          </div>
          <div className={`${styles.gridPortfolio} ${widgetClass(1)}`}>
            <PortfolioSummaryWidget portfolio={data.portfolio} />
          </div>

          {/* Row 2: Watchlist (full width) */}
          <div className={`${styles.gridWatchlist} ${widgetClass(2)}`}>
            <WatchlistWidget
              watchlists={data.watchlists}
              onRefresh={fetchDashboard}
            />
          </div>

          {/* Row 3: Models (left) + Events (right) */}
          <div className={`${styles.gridModels} ${widgetClass(3)}`}>
            <RecentModelsWidget models={data.recent_models} />
          </div>
          <div className={`${styles.gridEvents} ${widgetClass(4)}`}>
            <UpcomingEventsWidget />
          </div>
        </div>
      )}
    </div>
  );
}
