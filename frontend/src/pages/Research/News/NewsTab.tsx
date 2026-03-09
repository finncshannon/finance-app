import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../../../services/api';
import type { NewsArticle } from '../types';
import styles from './NewsTab.module.css';

type NewsMode = 'company' | 'top' | 'all';
type TimeFilter = 'all' | '1h' | '6h' | '12h' | '24h' | '3d' | '7d';
type SortOrder = 'newest' | 'oldest';
type CategoryFilter = 'All' | 'Markets' | 'Energy' | 'Technology' | 'Healthcare' | 'Finance' | 'Economy' | 'Politics' | 'Defense' | 'World' | 'Sports' | 'Entertainment';
type RegionFilter = 'All' | 'US' | 'Europe' | 'Asia' | 'Middle East' | 'Americas' | 'Africa';

const BATCH_TOP = 12;
const BATCH_ALL = 20;

const TIME_FILTERS: { value: TimeFilter; label: string }[] = [
  { value: '1h', label: '1H' },
  { value: '6h', label: '6H' },
  { value: '12h', label: '12H' },
  { value: '24h', label: '24H' },
  { value: '3d', label: '3D' },
  { value: '7d', label: '7D' },
  { value: 'all', label: 'All' },
];

const CATEGORIES: CategoryFilter[] = [
  'All', 'Markets', 'Technology', 'Finance', 'Economy', 'Energy', 'Healthcare', 'Politics', 'Defense', 'World', 'Sports', 'Entertainment',
];

const REGIONS: RegionFilter[] = [
  'All', 'US', 'Europe', 'Asia', 'Middle East', 'Americas', 'Africa',
];

const TIME_FILTER_MS: Record<TimeFilter, number> = {
  all: Infinity,
  '1h': 60 * 60 * 1000,
  '6h': 6 * 60 * 60 * 1000,
  '12h': 12 * 60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
  '3d': 3 * 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
};

interface Props {
  ticker: string;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  if (isNaN(then)) return '';

  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay === 1) return 'yesterday';
  if (diffDay < 30) return `${diffDay}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function NewsTab({ ticker }: Props) {
  // General news state
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Company news state
  const [companyArticles, setCompanyArticles] = useState<NewsArticle[]>([]);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [companyError, setCompanyError] = useState<string | null>(null);
  const [companyTicker, setCompanyTicker] = useState<string>('');

  // UI state
  const [mode, setMode] = useState<NewsMode>(ticker ? 'company' : 'top');
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('1h');
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('All');
  const [regionFilter, setRegionFilter] = useState<RegionFilter>('All');
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest');
  const [visibleCount, setVisibleCount] = useState(BATCH_TOP);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const batchSize = mode === 'top' ? BATCH_TOP : BATCH_ALL;

  // Fetch general news
  const fetchNews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<{ articles: NewsArticle[] }>('/api/v1/news/top');
      setArticles(data.articles);
    } catch (err) {
      setArticles([]);
      setError(err instanceof Error ? err.message : 'Failed to load news');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch company-specific news
  const fetchCompanyNews = useCallback(async (t: string) => {
    if (!t) return;
    setCompanyLoading(true);
    setCompanyError(null);
    try {
      const data = await api.get<{ articles: NewsArticle[] }>(`/api/v1/news/company/${t}`);
      setCompanyArticles(data.articles);
      setCompanyTicker(t);
    } catch (err) {
      setCompanyArticles([]);
      setCompanyError(err instanceof Error ? err.message : 'Failed to load company news');
    } finally {
      setCompanyLoading(false);
    }
  }, []);

  // Fetch general news on mount
  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  // Fetch company news when ticker changes or company mode is activated
  useEffect(() => {
    if (mode === 'company' && ticker && ticker !== companyTicker) {
      fetchCompanyNews(ticker);
    }
  }, [mode, ticker, companyTicker, fetchCompanyNews]);

  // Switch to company mode and fetch if needed when mode changes
  const handleModeChange = useCallback((newMode: NewsMode) => {
    setMode(newMode);
  }, []);

  // Determine which articles to use based on mode
  const sourceArticles = mode === 'company' ? companyArticles : articles;
  const isLoading = mode === 'company' ? companyLoading : loading;
  const currentError = mode === 'company' ? companyError : error;

  // Filter and sort
  const filtered = useMemo(() => {
    let result = sourceArticles;

    // Apply time filter
    const now = Date.now();
    const cutoff = TIME_FILTER_MS[timeFilter];
    if (cutoff !== Infinity) {
      result = result.filter((a) => {
        const t = new Date(a.published).getTime();
        return !isNaN(t) && (now - t) <= cutoff;
      });
    }

    // Apply category filter (only for general news modes)
    if (mode !== 'company' && categoryFilter !== 'All') {
      result = result.filter((a) => a.category === categoryFilter);
    }

    // Apply region filter (only for general news modes)
    if (mode !== 'company' && regionFilter !== 'All') {
      result = result.filter((a) => a.region === regionFilter);
    }

    if (mode === 'top') {
      // Top Stories: rank by coverage count (most sources first), then by time
      const sorted = [...result].sort((a, b) => {
        const ca = a.coverage_count ?? 1;
        const cb = b.coverage_count ?? 1;
        if (cb !== ca) return cb - ca;
        const ta = new Date(a.published).getTime() || 0;
        const tb = new Date(b.published).getTime() || 0;
        return sortOrder === 'newest' ? tb - ta : ta - tb;
      });
      return sorted.slice(0, 20);
    }

    // All News + Company: sort by time
    const sorted = [...result].sort((a, b) => {
      const ta = new Date(a.published).getTime() || 0;
      const tb = new Date(b.published).getTime() || 0;
      return sortOrder === 'newest' ? tb - ta : ta - tb;
    });
    return sorted;
  }, [sourceArticles, mode, timeFilter, categoryFilter, regionFilter, sortOrder]);

  // Reset visible count on mode/filter change
  useEffect(() => {
    setVisibleCount(mode === 'top' ? BATCH_TOP : BATCH_ALL);
  }, [mode, timeFilter, categoryFilter, regionFilter, sortOrder]);

  // Infinite scroll
  useEffect(() => {
    if (visibleCount >= filtered.length) return;
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setVisibleCount((prev) => Math.min(prev + batchSize, filtered.length));
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [visibleCount, filtered.length, batchSize]);

  const handleArticleClick = useCallback((article: NewsArticle) => {
    window.open(article.link, '_blank', 'noopener,noreferrer');
  }, []);

  const visibleArticles = useMemo(() => filtered.slice(0, visibleCount), [filtered, visibleCount]);
  const hasMore = visibleCount < filtered.length;

  // Loading skeleton
  if (isLoading && filtered.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <div className={styles.modeToggle}>
            {ticker && (
              <button className={`${styles.modeBtn} ${styles.modeBtnActive}`}>{ticker}</button>
            )}
            <button className={styles.modeBtn}>Top Stories</button>
            <button className={styles.modeBtn}>All News</button>
          </div>
        </div>
        <div className={styles.filterBar}>
          <div className={styles.filterGroup}>
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className={`${styles.skeletonLine} ${styles.skeletonPill}`} />
            ))}
          </div>
          <div className={styles.sortGroup}>
            <div className={`${styles.skeletonLine} ${styles.skeletonPill}`} />
            <div className={`${styles.skeletonLine} ${styles.skeletonPill}`} />
          </div>
        </div>
        <div className={styles.skeletonList}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className={styles.skeletonCard}>
              <div className={`${styles.skeletonLine} ${styles.skeletonMeta}`} />
              <div className={`${styles.skeletonLine} ${styles.skeletonHeadline}`} />
              <div className={`${styles.skeletonLine} ${styles.skeletonSnippet1}`} />
              <div className={`${styles.skeletonLine} ${styles.skeletonSnippet2}`} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (currentError && filtered.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <span className={styles.headerTitle}>NEWS</span>
        </div>
        <div className={styles.emptyState}>
          <span className={styles.emptyText}>{currentError}</span>
          <button
            className={styles.retryBtn}
            onClick={() => mode === 'company' ? fetchCompanyNews(ticker) : fetchNews()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header with mode toggle */}
      <div className={styles.header}>
        <div className={styles.modeToggle}>
          {ticker && (
            <button
              className={`${styles.modeBtn} ${mode === 'company' ? styles.modeBtnCompany : ''}`}
              onClick={() => handleModeChange('company')}
            >
              {ticker}
            </button>
          )}
          <button
            className={`${styles.modeBtn} ${mode === 'top' ? styles.modeBtnActive : ''}`}
            onClick={() => handleModeChange('top')}
          >
            Top Stories
          </button>
          <button
            className={`${styles.modeBtn} ${mode === 'all' ? styles.modeBtnActive : ''}`}
            onClick={() => handleModeChange('all')}
          >
            All News
          </button>
        </div>
        <span className={styles.headerCount}>
          {filtered.length} article{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Time + Sort filters (shown for all modes) */}
      <div className={styles.filterBar}>
          <div className={styles.filterGroup}>
            {TIME_FILTERS.map((f) => (
              <button
                key={f.value}
                className={`${styles.filterPill} ${timeFilter === f.value ? styles.filterPillActive : ''}`}
                onClick={() => setTimeFilter(f.value)}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className={styles.sortGroup}>
            <button
              className={`${styles.sortBtn} ${sortOrder === 'newest' ? styles.sortBtnActive : ''}`}
              onClick={() => setSortOrder('newest')}
            >
              Newest
            </button>
            <button
              className={`${styles.sortBtn} ${sortOrder === 'oldest' ? styles.sortBtnActive : ''}`}
              onClick={() => setSortOrder('oldest')}
            >
              Oldest
            </button>
          </div>
      </div>

      {/* Category + Region filters (hidden in company mode) */}
      {mode !== 'company' && (
        <div className={styles.filterRow}>
          <div className={styles.filterRowGroup}>
            <span className={styles.filterLabel}>Sector</span>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                className={`${styles.filterPill} ${categoryFilter === cat ? styles.filterPillActive : ''}`}
                onClick={() => setCategoryFilter(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
          <div className={styles.filterRowGroup}>
            <span className={styles.filterLabel}>Region</span>
            {REGIONS.map((reg) => (
              <button
                key={reg}
                className={`${styles.filterPill} ${regionFilter === reg ? styles.filterPillActive : ''}`}
                onClick={() => setRegionFilter(reg)}
              >
                {reg}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Article list */}
      {filtered.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyText}>
            {mode === 'company'
              ? `No news found for ${ticker}`
              : mode === 'top'
                ? 'No articles match this filter'
                : 'No articles available'}
          </span>
          {sourceArticles.length > 0 && timeFilter !== 'all' && (
            <button
              className={styles.retryBtn}
              onClick={() => setTimeFilter('all')}
            >
              Show all time periods
            </button>
          )}
        </div>
      ) : (
        <div className={styles.articleList}>
          {visibleArticles.map((article, idx) => (
            <div
              key={`${article.link}-${idx}`}
              className={styles.articleCard}
              onClick={() => handleArticleClick(article)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleArticleClick(article); } }}
            >
              <div className={styles.articleMeta}>
                <span className={styles.source}>{article.source}</span>
                <span className={styles.dot}>&bull;</span>
                <span className={styles.timeAgo}>{timeAgo(article.published)}</span>
                {article.category && article.category !== 'General' && (
                  <>
                    <span className={styles.dot}>&bull;</span>
                    <span className={styles.categoryBadge}>{article.category}</span>
                  </>
                )}
                {(article.coverage_count ?? 0) > 1 && (
                  <>
                    <span className={styles.dot}>&bull;</span>
                    <span className={styles.coverageBadge}>{article.coverage_count} sources</span>
                  </>
                )}
              </div>
              <div className={styles.headline}>{article.title}</div>
              {article.snippet && (
                <div className={styles.snippet}>{article.snippet}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {hasMore && (
        <>
          <div ref={sentinelRef} className={styles.sentinel} />
          <div className={styles.loadingMore}>Loading more...</div>
        </>
      )}
    </div>
  );
}
