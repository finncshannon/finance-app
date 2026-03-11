import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import { useResearchStore } from '../../../stores/researchStore';
import { useUIStore } from '../../../stores/uiStore';
import { gainColor } from '../types';
import type { NewsArticle } from '../types';
import { MiniChart } from './MiniChart';
import { WorldMap } from './WorldMap';
import s from './MarketPerformanceTab.module.css';

/* ── Types ── */

interface MarketItem {
  symbol: string;
  name: string;
  current_price: number;
  day_change: number;
  day_change_pct: number;
  perf_1w: number | null;
  perf_1m: number | null;
  perf_3m: number | null;
  perf_6m: number | null;
  perf_ytd: number | null;
  perf_1y: number | null;
  country_code?: string;
}

interface MarketPerformanceData {
  indices: MarketItem[];
  sectors: MarketItem[];
  global: Record<string, MarketItem[]>;
}

const CONTINENTS = ['All', 'Europe', 'Asia', 'Americas', 'Middle East & Africa', 'Oceania'] as const;

interface Holding {
  ticker: string;
  name: string;
  weight_pct: number;
  current_price: number | null;
  day_change_pct: number | null;
}

/* ── Formatters ── */

function fmtPrice(val: number | null): string {
  if (val === null || val === undefined) return '--';
  if (val >= 1000) return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return val.toFixed(2);
}

function fmtChg(val: number | null): string {
  if (val === null || val === undefined) return '--';
  const sign = val >= 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}`;
}

function fmtPerfPct(val: number | null): string {
  if (val === null || val === undefined) return '--';
  const sign = val >= 0 ? '+' : '';
  return `${sign}${val.toFixed(1)}%`;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  if (isNaN(then)) return '';
  const diffMin = Math.floor((now - then) / 60000);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

/* ── Sector → News category mapping ── */
const SECTOR_NEWS_MAP: Record<string, string[]> = {
  'Technology': ['Technology'],
  'Financials': ['Finance', 'Markets'],
  'Healthcare': ['Healthcare'],
  'Energy': ['Energy'],
  'Consumer Discretionary': ['Economy'],
  'Consumer Staples': ['Economy'],
  'Industrials': ['Economy'],
  'Materials': ['Economy', 'Energy'],
  'Real Estate': ['Finance', 'Economy'],
  'Communications': ['Technology', 'Entertainment'],
  'Utilities': ['Energy'],
  // Index names
  'S&P 500': ['Markets'],
  'NASDAQ 100': ['Technology', 'Markets'],
  'Dow Jones': ['Markets'],
  'Russell 2000': ['Markets'],
  'S&P MidCap 400': ['Markets'],
  'Volatility': ['Markets'],
  '10Y Treasury': ['Finance', 'Markets'],
};

const PERF_KEYS = ['perf_1w', 'perf_1m', 'perf_3m', 'perf_6m', 'perf_ytd', 'perf_1y'] as const;
const PERF_LABELS = ['1 Week', '1 Month', '3 Months', '6 Months', 'Year to Date', '1 Year'];

/* ── Component ── */

export function MarketPerformanceTab() {
  const [data, setData] = useState<MarketPerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<MarketItem | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [holdingsLoading, setHoldingsLoading] = useState(false);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const [activeContinent, setActiveContinent] = useState<string>('All');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<MarketPerformanceData>('/api/v1/market/performance');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load market data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Fetch holdings + news when a symbol is selected
  useEffect(() => {
    if (!selected) {
      setHoldings([]);
      setNews([]);
      return;
    }

    // Fetch holdings
    setHoldingsLoading(true);
    api.get<{ holdings: Holding[] }>(`/api/v1/market/${selected.symbol}/holdings`)
      .then((res) => setHoldings(res.holdings ?? []))
      .catch(() => setHoldings([]))
      .finally(() => setHoldingsLoading(false));

    // Fetch news filtered by matching categories
    setNewsLoading(true);
    api.get<{ articles: NewsArticle[] }>('/api/v1/news/top?limit=2000&days=3')
      .then((res) => {
        const categories = SECTOR_NEWS_MAP[selected.name] ?? [];
        const filtered = (res.articles ?? [])
          .filter((a) => categories.includes(a.category ?? ''))
          .sort((a, b) => new Date(b.published).getTime() - new Date(a.published).getTime())
          .slice(0, 8);
        setNews(filtered);
      })
      .catch(() => setNews([]))
      .finally(() => setNewsLoading(false));
  }, [selected]);

  const openInChart = (symbol: string) => {
    setSelected(null);
    useResearchStore.getState().setSelectedTicker(symbol);
    useUIStore.getState().setSubTab('research', 'chart');
  };

  const openInResearch = (symbol: string) => {
    setSelected(null);
    useResearchStore.getState().setSelectedTicker(symbol);
    useUIStore.getState().setSubTab('research', 'home');
  };

  if (error) return <div className={s.error}>{error}</div>;
  if (!data && !loading) return null;

  return (
    <div className={s.container}>
      <div className={s.columnsLayout}>
        {/* Indices — Left Column */}
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <h3 className={s.sectionTitle}>Indices</h3>
            <span className={s.sectionBadge}>{data ? `${data.indices.length} tracked` : ''}</span>
          </div>
          <div className={s.cardsList}>
            {(data?.indices ?? []).map((item) => (
              <div
                key={item.symbol}
                className={`${s.card} ${selected?.symbol === item.symbol ? s.cardActive : ''}`}
                onClick={() => setSelected(selected?.symbol === item.symbol ? null : item)}
              >
                <div className={s.cardSymbol}>{item.symbol}</div>
                <div className={s.cardName}>{item.name}</div>
                <div className={s.cardPrice}>{fmtPrice(item.current_price)}</div>
                <div className={s.cardChange} style={{ color: gainColor(item.day_change) }}>
                  {fmtChg(item.day_change)} ({fmtChg(item.day_change_pct * 100)}%)
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Global — Middle Column */}
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <h3 className={s.sectionTitle}>World Markets</h3>
            <span className={s.sectionBadge}>
              {data ? `${Object.values(data.global ?? {}).reduce((a, b) => a + b.length, 0)} countries` : ''}
            </span>
          </div>
          <WorldMap
            items={Object.values(data?.global ?? {}).flat()}
            usChange={data?.indices.find((i) => i.symbol === 'SPY')?.day_change_pct}
            loading={loading}
            onCountryClick={(item) => setSelected(selected?.symbol === item.symbol ? null : item)}
            activeContinent={activeContinent}
          />
          <div className={s.continentTabs}>
            {CONTINENTS.map((c) => (
              <button
                key={c}
                className={`${s.continentTab} ${activeContinent === c ? s.continentTabActive : ''}`}
                onClick={() => setActiveContinent(c)}
              >
                {c}
              </button>
            ))}
          </div>
          <div className={s.worldCardsList}>
            {activeContinent === 'All'
              ? Object.entries(data?.global ?? {}).map(([continent, items]) => {
                  const valid = items.filter((i) => i.day_change_pct != null);
                  const avgPct = valid.length > 0
                    ? valid.reduce((sum, i) => sum + i.day_change_pct, 0) / valid.length
                    : 0;
                  return (
                    <div
                      key={continent}
                      className={s.worldCard}
                      onClick={() => setActiveContinent(continent)}
                    >
                      <div className={s.worldCardName}>{continent}</div>
                      <div className={s.worldCardRow}>
                        <span className={s.worldCardPrice}>{valid.length} mkts</span>
                        <span className={s.worldCardChange} style={{ color: gainColor(avgPct) }}>
                          {fmtChg(avgPct * 100)}%
                        </span>
                      </div>
                    </div>
                  );
                })
              : (data?.global?.[activeContinent] ?? []).map((item) => (
                  <div
                    key={item.symbol}
                    className={`${s.worldCard} ${selected?.symbol === item.symbol ? s.worldCardActive : ''}`}
                    onClick={() => setSelected(selected?.symbol === item.symbol ? null : item)}
                  >
                    <div className={s.worldCardName}>{item.name}</div>
                    <div className={s.worldCardRow}>
                      <span className={s.worldCardPrice}>{fmtPrice(item.current_price)}</span>
                      <span className={s.worldCardChange} style={{ color: gainColor(item.day_change) }}>
                        {fmtChg(item.day_change_pct * 100)}%
                      </span>
                    </div>
                  </div>
                ))
            }
          </div>
        </div>

        {/* Sectors — Right Column */}
        <div className={s.section}>
          <div className={s.sectionHeader}>
            <h3 className={s.sectionTitle}>Sectors</h3>
            <span className={s.sectionBadge}>{data ? `${data.sectors.length} sectors` : ''}</span>
          </div>
          <div className={s.cardsList}>
            {(data?.sectors ?? []).map((item) => (
              <div
                key={item.symbol}
                className={`${s.card} ${selected?.symbol === item.symbol ? s.cardActive : ''}`}
                onClick={() => setSelected(selected?.symbol === item.symbol ? null : item)}
              >
                <div className={s.cardSymbol}>{item.symbol}</div>
                <div className={s.cardName}>{item.name}</div>
                <div className={s.cardPrice}>{fmtPrice(item.current_price)}</div>
                <div className={s.cardChange} style={{ color: gainColor(item.day_change) }}>
                  {fmtChg(item.day_change)} ({fmtChg(item.day_change_pct * 100)}%)
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Detail Page */}
      {selected && (
        <div className={s.detailOverlay} onClick={() => setSelected(null)}>
          <div className={s.detailPanel} onClick={(e) => e.stopPropagation()}>

            {/* Header */}
            <div className={s.detailHeader}>
              <div>
                <span className={s.detailTicker}>{selected.symbol}</span>
                <span className={s.detailName}>{selected.name}</span>
              </div>
              <button className={s.detailClose} onClick={() => setSelected(null)}>
                &times;
              </button>
            </div>

            {/* Main content grid */}
            <div className={s.detailBody}>
              {/* Left column */}
              <div className={s.detailLeft}>
                {/* Price widget */}
                <div className={s.widget}>
                  <div className={s.widgetHeader}>Price</div>
                  <div className={s.detailPrice}>
                    <span className={s.detailPriceVal}>{fmtPrice(selected.current_price)}</span>
                    <span
                      className={s.detailPriceChange}
                      style={{ color: gainColor(selected.day_change) }}
                    >
                      {fmtChg(selected.day_change)} ({fmtChg(selected.day_change_pct * 100)}%)
                    </span>
                  </div>
                </div>

                {/* Performance widget */}
                <div className={s.widget}>
                  <div className={s.widgetHeader}>Performance</div>
                  <div className={s.perfGrid}>
                    {PERF_KEYS.map((key, i) => (
                      <div key={key} className={s.perfCell}>
                        <div className={s.perfLabel}>{PERF_LABELS[i]}</div>
                        <div
                          className={s.perfValue}
                          style={{ color: gainColor(selected[key]) }}
                        >
                          {fmtPerfPct(selected[key])}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Chart widget */}
                <div className={s.widget}>
                  <div className={s.widgetHeader}>3 Month Chart</div>
                  <div className={s.chartBody}>
                    <MiniChart symbol={selected.symbol} height={180} />
                  </div>
                </div>

                {/* Actions */}
                <div className={s.detailActions}>
                  <button className={s.detailActionBtn} onClick={() => openInChart(selected.symbol)}>
                    Open Chart
                  </button>
                  <button className={s.detailActionBtn} onClick={() => openInResearch(selected.symbol)}>
                    Research
                  </button>
                </div>
              </div>

              {/* Right column */}
              <div className={s.detailRight}>
                {/* Holdings widget — only for indices/sectors, not world markets */}
                {!selected.country_code && (
                  <div className={s.widget}>
                    <div className={s.widgetHeader}>Top Holdings</div>
                    <div className={s.holdingsList}>
                      {holdingsLoading && <div className={s.widgetEmpty}>Loading...</div>}
                      {!holdingsLoading && holdings.length === 0 && (
                        <div className={s.widgetEmpty}>No holdings data</div>
                      )}
                      {holdings.map((h, i) => (
                        <div
                          key={h.ticker}
                          className={s.holdingRow}
                          onClick={() => openInResearch(h.ticker)}
                        >
                          <span className={s.holdingRank}>{i + 1}</span>
                          <div className={s.holdingInfo}>
                            <span className={s.holdingTicker}>{h.ticker}</span>
                            <span className={s.holdingName}>{h.name}</span>
                          </div>
                          <span className={s.holdingWeight}>{h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : '--'}</span>
                          <div className={s.holdingPrice}>
                            <span>{h.current_price !== null ? fmtPrice(h.current_price) : '--'}</span>
                            {h.day_change_pct !== null && (
                              <span
                                className={s.holdingChg}
                                style={{ color: gainColor(h.day_change_pct) }}
                              >
                                {fmtChg(h.day_change_pct)}%
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* News widget */}
                <div className={s.widget}>
                  <div className={s.widgetHeader}>Related News</div>
                  <div className={s.newsList}>
                    {newsLoading && <div className={s.widgetEmpty}>Loading...</div>}
                    {!newsLoading && news.length === 0 && (
                      <div className={s.widgetEmpty}>No related news</div>
                    )}
                    {news.map((article, i) => (
                      <div
                        key={`${article.link}-${i}`}
                        className={s.newsRow}
                        onClick={() => window.open(article.link, '_blank', 'noopener')}
                      >
                        <div className={s.newsMeta}>
                          <span className={s.newsSource}>{article.source}</span>
                          <span className={s.newsDot}>&bull;</span>
                          <span>{timeAgo(article.published)}</span>
                        </div>
                        <div className={s.newsHeadline}>{article.title}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
