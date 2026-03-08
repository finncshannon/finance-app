import { useState, useEffect, useMemo } from 'react';
import { api } from '../../../services/api';
import { navigationService } from '../../../services/navigationService';
import { useUIStore } from '../../../stores/uiStore';
import type { UpcomingEvent, FilteredEventsResponse, WatchlistSummary } from '../types';
import styles from './UpcomingEventsWidget.module.css';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const SOURCE_OPTIONS: { key: 'portfolio' | 'watchlist' | 'market'; label: string }[] = [
  { key: 'portfolio', label: 'Portfolio' },
  { key: 'watchlist', label: 'Watchlist' },
  { key: 'market', label: 'Market' },
];

const EVENT_TYPE_OPTIONS = [
  { key: 'earnings', label: 'Earnings' },
  { key: 'ex_dividend', label: 'Dividends' },
];

function displayEventType(type: string): string {
  const map: Record<string, string> = {
    earnings: 'Earnings',
    ex_dividend: 'Ex-Dividend',
    dividend: 'Dividend',
    filing: 'Filing',
  };
  return map[type] ?? type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function eventDotColor(eventType: string): string {
  switch (eventType.toLowerCase()) {
    case 'earnings': return 'var(--accent-primary)';
    case 'ex_dividend':
    case 'dividend': return 'var(--color-positive)';
    case 'filing': return 'var(--text-tertiary)';
    default: return 'var(--text-tertiary)';
  }
}

function computeWeekRange(): { weekStart: string; weekEnd: string; weekLabel: string } {
  const now = new Date();
  const day = now.getDay(); // 0=Sun, 1=Mon...
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diffToMonday);
  monday.setHours(0, 0, 0, 0);

  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  const fmtLabel = (d: Date) => `${MONTHS[d.getMonth()]} ${d.getDate()}`;

  return {
    weekStart: fmt(monday),
    weekEnd: fmt(sunday),
    weekLabel: `${fmtLabel(monday)} – ${fmtLabel(sunday)}`,
  };
}

function parseDate(dateStr: string): { month: string; day: number } {
  const d = new Date(dateStr + 'T00:00:00');
  return { month: MONTHS[d.getMonth()] ?? 'Jan', day: d.getDate() };
}

export function UpcomingEventsWidget() {
  const eventsSource = useUIStore((s) => s.eventsSource);
  const eventsWatchlistId = useUIStore((s) => s.eventsWatchlistId);
  const eventsTypes = useUIStore((s) => s.eventsTypes);
  const setEventsSource = useUIStore((s) => s.setEventsSource);
  const setEventsWatchlistId = useUIStore((s) => s.setEventsWatchlistId);
  const toggleEventType = useUIStore((s) => s.toggleEventType);

  const [events, setEvents] = useState<UpcomingEvent[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [watchlists, setWatchlists] = useState<WatchlistSummary[]>([]);

  const { weekStart, weekEnd, weekLabel } = useMemo(() => computeWeekRange(), []);

  // Fetch watchlist list once for dropdown
  useEffect(() => {
    api.get<{ watchlists: WatchlistSummary[] }>('/api/v1/dashboard/watchlists')
      .then((res) => setWatchlists(res.watchlists))
      .catch(() => {});
  }, []);

  // Fetch events when filters change
  useEffect(() => {
    let cancelled = false;

    async function fetchEvents() {
      setLoading(true);
      const params = new URLSearchParams({
        source: eventsSource,
        event_types: eventsTypes.join(','),
        date_from: weekStart,
        date_to: weekEnd,
        limit: '10',
      });
      if (eventsSource === 'watchlist' && eventsWatchlistId) {
        params.set('watchlist_id', String(eventsWatchlistId));
      }
      try {
        const result = await api.get<FilteredEventsResponse>(
          `/api/v1/dashboard/events?${params}`
        );
        if (!cancelled) {
          setEvents(result.events);
          setTotalCount(result.total_count);
        }
      } catch {
        if (!cancelled) {
          setEvents([]);
          setTotalCount(0);
        }
      }
      if (!cancelled) setLoading(false);
    }

    fetchEvents();
    return () => { cancelled = true; };
  }, [eventsSource, eventsWatchlistId, eventsTypes, weekStart, weekEnd]);

  const emptyMessage = (): { title: string; text: string } => {
    switch (eventsSource) {
      case 'portfolio':
        return {
          title: 'No portfolio events this week',
          text: 'Events appear as companies in your portfolio announce earnings or dividends.',
        };
      case 'watchlist':
        return {
          title: 'No watchlist events this week',
          text: 'Add tickers to your watchlist to track their events.',
        };
      case 'market':
        return {
          title: 'No S&P 500 events this week',
          text: '',
        };
    }
  };

  return (
    <div className={styles.widget}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.headerTitle}>Upcoming Events</span>
        <button
          className={styles.navLink}
          onClick={() => navigationService.goToUpcomingEvents()}
        >
          View All &rarr;
        </button>
      </div>

      {/* Filter row */}
      <div className={styles.filterRow}>
        <div className={styles.sourceToggle}>
          {SOURCE_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              className={`${styles.sourcePill} ${eventsSource === opt.key ? styles.sourcePillActive : ''}`}
              onClick={() => setEventsSource(opt.key)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className={styles.typeChecks}>
          {EVENT_TYPE_OPTIONS.map((opt) => (
            <label key={opt.key} className={styles.checkLabel}>
              <input
                type="checkbox"
                className={styles.checkbox}
                checked={eventsTypes.includes(opt.key)}
                onChange={() => toggleEventType(opt.key)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>

      {/* Watchlist dropdown */}
      {eventsSource === 'watchlist' && (
        <div className={styles.watchlistRow}>
          <select
            className={styles.watchlistSelect}
            value={eventsWatchlistId ?? ''}
            onChange={(e) =>
              setEventsWatchlistId(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">All Watchlists</option>
            {watchlists.map((wl) => (
              <option key={wl.id} value={wl.id}>{wl.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Week label */}
      <div className={styles.weekLabel}>This Week: {weekLabel}</div>

      {/* Body */}
      <div className={styles.body}>
        {loading ? (
          <div className={styles.skeletonList}>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className={styles.skeletonRow}>
                <div className={styles.skeletonBadge} />
                <div className={styles.skeletonContent}>
                  <div className={styles.skeletonLineShort} />
                  <div className={styles.skeletonLineLong} />
                </div>
              </div>
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyTitle}>{emptyMessage().title}</div>
            {emptyMessage().text && (
              <div className={styles.emptyText}>{emptyMessage().text}</div>
            )}
          </div>
        ) : (
          <ul className={styles.eventList}>
            {events.map((ev, i) => {
              const { month, day } = parseDate(ev.date);
              return (
                <li
                  key={`${ev.date}-${ev.ticker}-${i}`}
                  className={styles.eventItem}
                  onClick={() => navigationService.goToResearch(ev.ticker)}
                >
                  <div className={styles.dateBadge}>
                    <div className={styles.dateMonth}>{month}</div>
                    <div className={styles.dateDay}>{day}</div>
                  </div>
                  <div className={styles.eventContent}>
                    <div className={styles.eventTop}>
                      <span className={styles.eventTicker}>{ev.ticker}</span>
                      <span
                        className={styles.eventDot}
                        style={{ backgroundColor: eventDotColor(ev.event_type) }}
                      />
                      <span className={styles.eventTypeLabel}>
                        {displayEventType(ev.event_type)}
                      </span>
                    </div>
                    <div className={styles.eventDetail}>{ev.detail}</div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Footer */}
      {!loading && totalCount > 10 && (
        <div className={styles.footer}>
          Showing {events.length} of {totalCount} this week
        </div>
      )}
    </div>
  );
}
