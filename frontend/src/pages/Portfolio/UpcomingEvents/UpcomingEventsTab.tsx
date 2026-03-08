import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import { navigationService } from '../../../services/navigationService';
import { useUIStore } from '../../../stores/uiStore';
import type { UpcomingEvent, FilteredEventsResponse, WatchlistSummary } from '../../Dashboard/types';
import styles from './UpcomingEventsTab.module.css';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const PAGE_SIZE = 50;

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

function getMonday(d: Date): Date {
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diff);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

function fmtISO(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function fmtRange(monday: Date): string {
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return `${MONTHS[monday.getMonth()]} ${monday.getDate()} – ${MONTHS[sunday.getMonth()]} ${sunday.getDate()}`;
}

interface WeekGroup {
  label: string;
  events: UpcomingEvent[];
}

function groupByWeek(events: UpcomingEvent[]): WeekGroup[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const thisMonday = getMonday(today);
  const nextMonday = new Date(thisMonday);
  nextMonday.setDate(thisMonday.getDate() + 7);

  const groups = new Map<string, { label: string; events: UpcomingEvent[]; sortKey: string }>();

  for (const ev of events) {
    const evDate = new Date(ev.date + 'T00:00:00');
    const evMonday = getMonday(evDate);
    const key = fmtISO(evMonday);

    if (!groups.has(key)) {
      let label: string;
      if (key === fmtISO(thisMonday)) {
        label = `THIS WEEK — ${fmtRange(evMonday)}`;
      } else if (key === fmtISO(nextMonday)) {
        label = `NEXT WEEK — ${fmtRange(evMonday)}`;
      } else {
        label = `WEEK OF ${fmtRange(evMonday)}`;
      }
      groups.set(key, { label, events: [], sortKey: key });
    }
    groups.get(key)!.events.push(ev);
  }

  return Array.from(groups.values())
    .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
    .map(({ label, events: evs }) => ({ label, events: evs }));
}

function parseDate(dateStr: string): { month: string; day: number } {
  const d = new Date(dateStr + 'T00:00:00');
  return { month: MONTHS[d.getMonth()] ?? 'Jan', day: d.getDate() };
}

export function UpcomingEventsTab() {
  const eventsSource = useUIStore((s) => s.eventsSource);
  const eventsWatchlistId = useUIStore((s) => s.eventsWatchlistId);
  const eventsTypes = useUIStore((s) => s.eventsTypes);
  const setEventsSource = useUIStore((s) => s.setEventsSource);
  const setEventsWatchlistId = useUIStore((s) => s.setEventsWatchlistId);
  const toggleEventType = useUIStore((s) => s.toggleEventType);

  const [events, setEvents] = useState<UpcomingEvent[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [watchlists, setWatchlists] = useState<WatchlistSummary[]>([]);

  // Fetch watchlist list once
  useEffect(() => {
    api.get<{ watchlists: WatchlistSummary[] }>('/api/v1/dashboard/watchlists')
      .then((res) => setWatchlists(res.watchlists))
      .catch(() => {});
  }, []);

  const dateFrom = fmtISO(getMonday(new Date()));

  const fetchEvents = useCallback(async (newOffset: number, append: boolean) => {
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }

    const params = new URLSearchParams({
      source: eventsSource,
      event_types: eventsTypes.join(','),
      date_from: dateFrom,
      limit: String(PAGE_SIZE),
      offset: String(newOffset),
    });
    if (eventsSource === 'watchlist' && eventsWatchlistId) {
      params.set('watchlist_id', String(eventsWatchlistId));
    }

    try {
      const result = await api.get<FilteredEventsResponse>(
        `/api/v1/dashboard/events?${params}`
      );
      if (append) {
        setEvents((prev) => [...prev, ...result.events]);
      } else {
        setEvents(result.events);
      }
      setHasMore(result.has_more);
    } catch {
      if (!append) {
        setEvents([]);
        setHasMore(false);
      }
    }

    setLoading(false);
    setLoadingMore(false);
  }, [eventsSource, eventsWatchlistId, eventsTypes, dateFrom]);

  // Reset and fetch on filter change
  useEffect(() => {
    setOffset(0);
    fetchEvents(0, false);
  }, [fetchEvents]);

  const handleLoadMore = () => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    fetchEvents(newOffset, true);
  };

  const weekGroups = groupByWeek(events);

  const emptyMessage = (): { title: string; text: string } => {
    switch (eventsSource) {
      case 'portfolio':
        return {
          title: 'No upcoming events for your portfolio',
          text: 'Events will appear as you add positions.',
        };
      case 'watchlist':
        return {
          title: 'No upcoming events for your watchlists',
          text: 'Add tickers to your watchlist to track their events.',
        };
      case 'market':
        return {
          title: 'No upcoming S&P 500 events',
          text: 'Events will appear as companies announce earnings or dividends.',
        };
    }
  };

  return (
    <div className={styles.container}>
      {/* Filter bar */}
      <div className={styles.filterBar}>
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
        {eventsSource === 'watchlist' && (
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
        )}
      </div>

      {/* Content */}
      {loading ? (
        <div className={styles.loadingWrap}>
          <div className={styles.spinner} />
          <span className={styles.loadingText}>Loading events...</span>
        </div>
      ) : events.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyTitle}>{emptyMessage().title}</div>
          <div className={styles.emptyText}>{emptyMessage().text}</div>
        </div>
      ) : (
        <div className={styles.weekList}>
          {weekGroups.map((group) => (
            <div key={group.label} className={styles.weekGroup}>
              <div className={styles.weekHeader}>
                <span className={styles.weekHeaderText}>{group.label}</span>
                <div className={styles.weekHeaderLine} />
              </div>
              {group.events.map((ev, i) => {
                const { month, day } = parseDate(ev.date);
                return (
                  <div
                    key={`${ev.date}-${ev.ticker}-${i}`}
                    className={styles.eventRow}
                    onClick={() => navigationService.goToResearch(ev.ticker)}
                  >
                    <div className={styles.dateBadge}>
                      <div className={styles.dateMonth}>{month}</div>
                      <div className={styles.dateDay}>{day}</div>
                    </div>
                    <div className={styles.eventContent}>
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
                    <button
                      className={styles.researchLink}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigationService.goToResearch(ev.ticker);
                      }}
                    >
                      &rarr;
                    </button>
                  </div>
                );
              })}
            </div>
          ))}

          {hasMore && (
            <div className={styles.loadMoreWrap}>
              <button
                className={styles.loadMoreBtn}
                onClick={handleLoadMore}
                disabled={loadingMore}
              >
                {loadingMore ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
