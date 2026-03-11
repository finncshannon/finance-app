import { useState, useEffect, useCallback } from 'react';
import { api } from '../../services/api';
import { useUIStore } from '../../stores/uiStore';
import { soundManager } from '../../services/soundManager';
import type { DashboardSummary } from './types';
import { MarketOverviewWidget } from './MarketOverview/MarketOverviewWidget';
import { PortfolioSummaryWidget } from './PortfolioSummary/PortfolioSummaryWidget';
import { NewsWidget } from './News/NewsWidget';
import { WatchlistWidget } from './Watchlist/WatchlistWidget';
import { RecentModelsWidget } from './RecentModels/RecentModelsWidget';
import { UpcomingEventsWidget } from './UpcomingEvents/UpcomingEventsWidget';
import styles from './DashboardPage.module.css';

const WIDGET_COUNT = 6;
const INITIAL_DELAY_MS = 400;
const SHELL_STAGGER_MS = 250;
const HEADER_DELAY_MS = 400;
const HEADER_STAGGER_MS = 200;
const DATA_DELAY_MS = 400;

// Widget indices: 0=Market, 1=Portfolio, 2=News, 3=Events, 4=Watchlist, 5=Models
const VERTICAL_WIDGETS = [1, 2, 3]; // portfolio, news, events — top-down reveal
const DATA_ORDER = [0, 1, 2, 3, 4, 5]; // Market → Portfolio → News → Events → Watchlist → Models

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [widgetStages, setWidgetStages] = useState<number[]>(
    Array(WIDGET_COUNT).fill(-1)
  );

  const justBooted = useUIStore((s) => s.justBooted);
  const dashboardAnimationPlayed = useUIStore((s) => s.dashboardAnimationPlayed);
  const setDashboardAnimationPlayed = useUIStore((s) => s.setDashboardAnimationPlayed);

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

  // Shell cascade — runs once on mount
  useEffect(() => {
    if (dashboardAnimationPlayed) {
      setWidgetStages(Array(WIDGET_COUNT).fill(2));
      return;
    }

    const timers: ReturnType<typeof setTimeout>[] = [];

    // Phase 1: Shells pop in
    for (let i = 0; i < WIDGET_COUNT; i++) {
      const shellTime = INITIAL_DELAY_MS + i * SHELL_STAGGER_MS;
      timers.push(
        setTimeout(() => {
          setWidgetStages((prev) => {
            const next = [...prev];
            next[i] = 0;
            return next;
          });
          soundManager.playWidgetOnline();
        }, shellTime)
      );
    }

    // Phase 2: Headers build in
    const shellsDone = INITIAL_DELAY_MS + (WIDGET_COUNT - 1) * SHELL_STAGGER_MS;
    const headerStart = shellsDone + HEADER_DELAY_MS;

    for (let i = 0; i < WIDGET_COUNT; i++) {
      const headerTime = headerStart + i * HEADER_STAGGER_MS;
      timers.push(
        setTimeout(() => {
          setWidgetStages((prev) => {
            const next = [...prev];
            next[i] = 1;
            return next;
          });
          soundManager.playWidgetOnline();
        }, headerTime)
      );
    }

    // Phase 3: Data populates with random gaps
    const headersDone = headerStart + (WIDGET_COUNT - 1) * HEADER_STAGGER_MS;
    const dataStart = headersDone + DATA_DELAY_MS;

    let cursor = dataStart;
    for (const idx of DATA_ORDER) {
      const t = cursor;
      timers.push(
        setTimeout(() => {
          setWidgetStages((prev) => {
            const next = [...prev];
            next[idx] = 2;
            return next;
          });
          soundManager.playWidgetOnline();
        }, t)
      );
      cursor += 150 + Math.random() * 350;
    }

    timers.push(
      setTimeout(() => {
        setDashboardAnimationPlayed(true);
      }, cursor + 400)
    );

    return () => timers.forEach(clearTimeout);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const widgetClass = (index: number): string => {
    const stage = widgetStages[index] ?? -1;
    if (stage < 0) return styles.widgetHidden ?? '';
    if (stage === 0) return styles.widgetShell ?? '';
    if (stage === 1) return styles.widgetHeaderOn ?? '';
    // Skip animation classes if already played (tab switch)
    if (dashboardAnimationPlayed) return styles.widgetReady ?? '';
    if (VERTICAL_WIDGETS.includes(index)) return styles.widgetFullOnVertical ?? '';
    return styles.widgetFullOn ?? '';
  };

  const animating = justBooted && !dashboardAnimationPlayed;

  return (
    <div className={styles.page}>
      {!animating && (
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
      )}

      {error && !animating && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.grid}>
        {/* Left column: Market + News */}
        <div className={styles.gridColLeft}>
          <div className={`${styles.gridMarket} ${widgetClass(0)}`}>
            {data && <MarketOverviewWidget market={data.market} />}
          </div>
          <div className={`${styles.gridNews} ${widgetClass(2)}`}>
            <NewsWidget />
          </div>
        </div>

        {/* Right column: Portfolio + Events */}
        <div className={styles.gridColRight}>
          <div className={`${styles.gridPortfolio} ${widgetClass(1)}`}>
            {data && <PortfolioSummaryWidget portfolio={data.portfolio} />}
          </div>
          <div className={`${styles.gridEvents} ${widgetClass(3)}`}>
            <UpcomingEventsWidget />
          </div>
        </div>

        {/* Full width: Watchlist */}
        <div className={`${styles.gridWatchlist} ${widgetClass(4)}`}>
          {data && (
            <WatchlistWidget
              watchlists={data.watchlists}
              onRefresh={fetchDashboard}
            />
          )}
        </div>

        {/* Full width: Recent Models */}
        <div className={`${styles.gridModels} ${widgetClass(5)}`}>
          {data && <RecentModelsWidget models={data.recent_models} />}
        </div>
      </div>
    </div>
  );
}
