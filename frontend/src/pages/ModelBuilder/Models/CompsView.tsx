import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import type { CompsResult, CompsTableRow, ImpliedValue, MultipleStats } from '../../../types/models';
import { ResultsCard } from './ResultsCard';
import { ExportDropdown } from '../../../components/ui/ExportButton/ExportDropdown';
import { useModelStore } from '../../../stores/modelStore';
import { downloadExport } from '../../../services/exportService';
import { api } from '../../../services/api';
import { navigationService } from '../../../services/navigationService';
import { displayLabel } from '../../../utils/displayNames';
import { fmtDollar, fmtPct, fmtMultiple, fmtNumber, fmtPrice } from './formatters';
import styles from './CompsView.module.css';

interface CompsViewProps {
  result: CompsResult;
  onRerun?: (peerTickers: string[]) => void;
}

interface SearchResult {
  ticker: string;
  company_name: string;
  exchange?: string;
}

/** Multiple column definitions for the peer table. */
interface MultipleDef {
  header: string;
  key: keyof CompsTableRow;
  flagKey: string;
  format: 'multiple' | 'pct' | 'dollar';
}

const MULTIPLE_COLS: MultipleDef[] = [
  { header: 'P/E', key: 'pe', flagKey: 'pe', format: 'multiple' },
  { header: 'EV/EBITDA', key: 'ev_ebitda', flagKey: 'ev_ebitda', format: 'multiple' },
  { header: 'EV/Rev', key: 'ev_revenue', flagKey: 'ev_revenue', format: 'multiple' },
  { header: 'P/B', key: 'pb', flagKey: 'pb', format: 'multiple' },
  { header: 'Rev Gr.', key: 'revenue_growth', flagKey: 'revenue_growth', format: 'pct' },
  { header: 'Op Margin', key: 'operating_margin', flagKey: 'operating_margin', format: 'pct' },
];

const AGG_KEYS = ['pe', 'ev_ebitda', 'ev_revenue', 'pb'] as const;

/** Proper display labels for implied value methods. */
const IMPLIED_VALUE_LABELS: Record<string, string> = {
  pe: 'P/E',
  ev_ebitda: 'EV/EBITDA',
  ev_revenue: 'EV/Revenue',
  pb: 'P/B',
  p_fcf: 'P/FCF',
};

function formatMultipleCell(value: number | null, format: 'multiple' | 'pct' | 'dollar'): string {
  if (value == null) return '—';
  switch (format) {
    case 'multiple':
      return fmtMultiple(value);
    case 'pct':
      return fmtPct(value);
    case 'dollar':
      return fmtDollar(value);
  }
}

/** Pick the first non-null implied value's quality-adjusted price for the results card. */
function pickPrimaryImplied(implied: Record<string, ImpliedValue | null> | undefined): ImpliedValue | null {
  if (!implied) return null;
  const preferredOrder = ['ev_ebitda', 'pe', 'ev_revenue', 'pb', 'p_fcf'];
  for (const key of preferredOrder) {
    if (implied[key] != null) return implied[key]!;
  }
  for (const val of Object.values(implied)) {
    if (val != null) return val;
  }
  return null;
}

function fmtMarketCap(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
  return fmtDollar(value);
}

export function CompsView({ result, onRerun }: CompsViewProps) {
  // Determine status with backward compat
  const status = result.status ?? ((result.peer_group?.peers ?? []).length > 0 ? 'ready' : 'no_peers');
  const peers = result.peer_group?.peers ?? [];

  // Peer management state
  const [peerTickers, setPeerTickers] = useState<string[]>(() =>
    peers.map((p: CompsTableRow) => p.ticker),
  );
  const [peerSearch, setPeerSearch] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [panelCollapsed, setPanelCollapsed] = useState(status === 'ready');

  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  // Ticker hover popup state
  const [hoveredTicker, setHoveredTicker] = useState<string | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [companyDesc, setCompanyDesc] = useState<Record<string, string>>({});
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleTickerMouseEnter = useCallback((e: React.MouseEvent, ticker: string) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setHoverPos({ x: rect.left, y: rect.bottom + 4 });
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      setHoveredTicker(ticker);
      if (!companyDesc[ticker]) {
        api.get<{ data?: { description?: string; company_name?: string; sector?: string; industry?: string } }>(`/api/v1/companies/${ticker}`)
          .then((res) => {
            const d = (res as Record<string, unknown>)?.data ?? res;
            const data = d as Record<string, string>;
            const desc = data?.description || data?.company_name || 'No description available';
            const sector = data?.sector || '';
            const industry = data?.industry || '';
            const summary = [sector, industry].filter(Boolean).join(' · ');
            setCompanyDesc((prev) => ({ ...prev, [ticker]: summary ? `${summary}\n${desc}` : desc }));
          })
          .catch(() => {
            setCompanyDesc((prev) => ({ ...prev, [ticker]: 'Description unavailable' }));
          });
      }
    }, 300);
  }, [companyDesc]);

  const handleTickerMouseLeave = useCallback(() => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setHoveredTicker(null);
  }, []);

  const handleTickerClick = useCallback((ticker: string) => {
    navigationService.goToResearch(ticker, 'profile');
  }, []);

  // Sync peer list when results update
  useEffect(() => {
    const p = result.peer_group?.peers ?? [];
    if (p.length > 0) {
      setPeerTickers(p.map((peer: CompsTableRow) => peer.ticker));
      setPanelCollapsed(true);
    }
  }, [result.peer_group]);

  // Debounced peer search
  const handleSearchChange = useCallback((value: string) => {
    setPeerSearch(value);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (value.length < 1) {
      setSearchResults([]);
      setShowSearchDropdown(false);
      return;
    }
    searchTimeout.current = setTimeout(async () => {
      try {
        const results = await api.get<SearchResult[]>(
          `/api/v1/companies/search?q=${encodeURIComponent(value)}`,
        );
        setSearchResults(results);
        setShowSearchDropdown(results.length > 0);
      } catch {
        setSearchResults([]);
        setShowSearchDropdown(false);
      }
    }, 200);
  }, []);

  const addPeer = useCallback(
    (ticker: string) => {
      const t = ticker.toUpperCase();
      if (!peerTickers.includes(t)) {
        setPeerTickers((prev) => [...prev, t]);
      }
      setPeerSearch('');
      setShowSearchDropdown(false);
    },
    [peerTickers],
  );

  const removePeer = useCallback((ticker: string) => {
    setPeerTickers((prev) => prev.filter((t) => t !== ticker));
  }, []);

  // Close search dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSearchDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleRunComps = useCallback(() => {
    onRerun?.(peerTickers);
  }, [onRerun, peerTickers]);

  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && peerSearch.trim()) {
        addPeer(peerSearch.trim());
      }
      if (e.key === 'Escape') {
        setShowSearchDropdown(false);
      }
    },
    [peerSearch, addPeer],
  );

  // Sort peers by peer_score descending (null safe)
  const sortedPeers = useMemo(() => {
    return [...peers].sort(
      (a: CompsTableRow, b: CompsTableRow) => (b.peer_score ?? 0) - (a.peer_score ?? 0),
    );
  }, [peers]);

  // Primary implied for results card
  const primaryImplied = useMemo(
    () => pickPrimaryImplied(result.implied_values),
    [result.implied_values],
  );

  // Implied values sorted for table
  const impliedEntries = useMemo(() => {
    return Object.entries(result.implied_values ?? {})
      .filter(([, v]) => v != null)
      .map(([key, v]) => ({ key, value: v as ImpliedValue }));
  }, [result.implied_values]);

  // Find row closest to current price
  const closestKey = useMemo(() => {
    const first = impliedEntries[0];
    if (!first) return null;
    let best = first.key;
    let bestDist = Math.abs(first.value.quality_adjusted_price - result.current_price);
    for (const entry of impliedEntries) {
      const dist = Math.abs(entry.value.quality_adjusted_price - result.current_price);
      if (dist < bestDist) {
        bestDist = dist;
        best = entry.key;
      }
    }
    return best;
  }, [impliedEntries, result.current_price]);

  // Quality assessment
  const qualityFactors = result.quality_assessment?.factor_scores ?? {};
  const compositeAdj = result.quality_assessment?.composite_adjustment ?? 0;

  // Peer panel component
  const peerPanel = (
    <div className={styles.peerPanel}>
      <div className={styles.peerPanelHeader}>
        <span className={styles.peerPanelTitle}>PEER GROUP</span>
        {status === 'ready' && (
          <button
            className={styles.collapseToggle}
            onClick={() => setPanelCollapsed(!panelCollapsed)}
          >
            {panelCollapsed ? `${peers.length} peers ▸` : '▾ Collapse'}
          </button>
        )}
      </div>

      {!panelCollapsed && (
        <>
          <div className={styles.peerSearch} ref={searchRef}>
            <input
              className={styles.peerSearchInput}
              type="text"
              placeholder="Enter ticker..."
              value={peerSearch}
              onChange={(e) => handleSearchChange(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              onFocus={() => {
                if (searchResults.length > 0) setShowSearchDropdown(true);
              }}
            />
            <button
              className={styles.addBtn}
              onClick={() => {
                if (peerSearch.trim()) addPeer(peerSearch.trim());
              }}
              disabled={!peerSearch.trim()}
            >
              Add
            </button>
            {showSearchDropdown && (
              <div className={styles.searchDropdown}>
                {searchResults.map((r) => (
                  <div
                    key={r.ticker}
                    className={styles.searchDropdownItem}
                    onClick={() => addPeer(r.ticker)}
                  >
                    <span className={styles.searchDropdownTicker}>{r.ticker}</span>
                    <span className={styles.searchDropdownName}>{r.company_name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {peerTickers.length > 0 && (
            <div className={styles.peerList}>
              {peerTickers.map((ticker) => {
                const peerInfo = peers.find((p: CompsTableRow) => p.ticker === ticker);
                return (
                  <div key={ticker} className={styles.peerListItem}>
                    <span className={styles.peerListTicker}>{ticker}</span>
                    <span className={styles.peerListName}>
                      {peerInfo?.company_name ?? ''}
                    </span>
                    <span className={styles.peerListCap}>
                      {peerInfo?.market_cap ? fmtMarketCap(peerInfo.market_cap) : ''}
                    </span>
                    <button
                      className={styles.peerRemoveBtn}
                      onClick={() => removePeer(ticker)}
                      title="Remove peer"
                    >
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          <div className={styles.peerPanelFooter}>
            <button className={styles.runBtn} onClick={handleRunComps}>
              Run Comps Analysis
            </button>
            {peers.length > 0 && (
              <span className={styles.autoDiscoverNote}>
                Auto-discovered: {peers.length} peers
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );

  // Export slot
  const exportSlot = useModelStore.getState().activeModelId ? (
    <ExportDropdown
      options={[
        {
          label: 'Excel (.xlsx)',
          format: 'excel',
          onClick: async () => {
            const modelId = useModelStore.getState().activeModelId;
            if (!modelId) return;
            const date = new Date().toISOString().slice(0, 10);
            await downloadExport(
              `/api/v1/export/model/${modelId}/excel`,
              `${result.ticker}_comps_${date}.xlsx`,
            );
          },
        },
        {
          label: 'PDF Report',
          format: 'pdf',
          onClick: async () => {
            const modelId = useModelStore.getState().activeModelId;
            if (!modelId) return;
            const date = new Date().toISOString().slice(0, 10);
            await downloadExport(
              `/api/v1/export/model/${modelId}/pdf`,
              `${result.ticker}_comps_${date}.pdf`,
            );
          },
        },
      ]}
    />
  ) : (
    <button disabled title="Run and save model first to enable export" className={styles.exportDisabled ?? ''}>
      Export ▾
    </button>
  );

  // Error state
  if (status === 'error') {
    const warnings = result.metadata?.warnings ?? [];
    return (
      <div className={styles.container}>
        {peerPanel}
        <div className={styles.errorState}>
          <div className={styles.errorIcon}>!</div>
          <div className={styles.errorText}>
            {warnings[0] ?? 'Comps analysis encountered an error.'}
          </div>
        </div>
      </div>
    );
  }

  // Setup state (no peers)
  if (status === 'no_peers') {
    return (
      <div className={styles.container}>
        <div className={styles.setupState}>
          {peerPanel}
          <div className={styles.setupHint}>
            Add peer companies above to run comparisons, or click &quot;Run Comps Analysis&quot; to
            use auto-discovered peers.
          </div>
        </div>
      </div>
    );
  }

  // Results state
  return (
    <div className={styles.container}>
      {/* Peer panel (collapsed) */}
      {peerPanel}

      {/* a) ResultsCard */}
      <ResultsCard
        impliedPrice={primaryImplied?.quality_adjusted_price ?? result.current_price}
        currentPrice={result.current_price}
        upsidePct={primaryImplied?.upside_downside_pct ?? null}
        label="Implied Price (Quality-Adj.)"
        exportSlot={exportSlot}
      />

      {/* b) Peer Comparison Table */}
      {sortedPeers.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Peer Comparison</div>
          <div className={styles.tableWrapper}>
            <table className={styles.compsTable}>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th>Mkt Cap</th>
                  <th>EV</th>
                  {MULTIPLE_COLS.map((col) => (
                    <th key={col.header}>{col.header}</th>
                  ))}
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {sortedPeers.map((peer) => (
                  <tr key={peer.ticker}>
                    <td>
                      <span
                        className={styles.tickerLink}
                        onClick={() => handleTickerClick(peer.ticker)}
                        onMouseEnter={(e) => handleTickerMouseEnter(e, peer.ticker)}
                        onMouseLeave={handleTickerMouseLeave}
                      >
                        {peer.ticker}
                      </span>
                    </td>
                    <td>{peer.company_name}</td>
                    <td>{fmtDollar(peer.market_cap)}</td>
                    <td>{fmtDollar(peer.enterprise_value)}</td>
                    {MULTIPLE_COLS.map((col) => {
                      const val = peer[col.key] as number | null;
                      const isOutlier = peer.outlier_flags?.[col.flagKey] === true;
                      return (
                        <td
                          key={col.header}
                          className={isOutlier ? styles.outlierCell : undefined}
                        >
                          {formatMultipleCell(val, col.format)}
                        </td>
                      );
                    })}
                    <td>{fmtNumber(peer.peer_score ?? 0, 1)}</td>
                  </tr>
                ))}

                {/* c) Aggregate Multiples Rows */}
                {(result.aggregate_multiples && Object.keys(result.aggregate_multiples).length > 0) && (
                  <>
                    {(['mean', 'median', 'trimmed_mean'] as const).map((stat) => (
                      <tr key={stat} className={styles.aggregateRow}>
                        <td>
                          {stat === 'trimmed_mean' ? 'Trimmed Mean' : stat.charAt(0).toUpperCase() + stat.slice(1)}
                        </td>
                        <td></td>
                        <td></td>
                        <td></td>
                        {AGG_KEYS.map((mk) => {
                          const agg = result.aggregate_multiples ?? {};
                          const ms = agg[mk] as MultipleStats | null | undefined;
                          return (
                            <td key={mk}>
                              {ms != null ? fmtMultiple(ms[stat]) : '—'}
                            </td>
                          );
                        })}
                        {/* revenue_growth and op_margin aggregate aren't multiples */}
                        <td></td>
                        <td></td>
                        <td></td>
                      </tr>
                    ))}
                  </>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* d) Implied Values Panel */}
      {impliedEntries.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Implied Values</div>
          <div className={styles.tableWrapper}>
            <table className={styles.impliedTable}>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Multiple</th>
                  <th>Raw Price</th>
                  <th>Adj. Price</th>
                  <th>Upside</th>
                </tr>
              </thead>
              <tbody>
                {impliedEntries.map(({ key, value }) => {
                  const isClosest = key === closestKey;
                  const upPct = value.upside_downside_pct;
                  return (
                    <tr key={key} className={isClosest ? styles.highlightRow : undefined}>
                      <td>{IMPLIED_VALUE_LABELS[key] ?? displayLabel(key)}</td>
                      <td>{fmtMultiple(value.multiple_used)}</td>
                      <td>{fmtPrice(value.raw_implied_price)}</td>
                      <td>{fmtPrice(value.quality_adjusted_price)}</td>
                      <td className={upPct != null && upPct >= 0 ? styles.positive : styles.negative}>
                        {upPct != null ? `${upPct >= 0 ? '+' : ''}${fmtPct(upPct)}` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* e) Quality Adjustment */}
      {Object.keys(qualityFactors).length > 0 && (
        <div className={`${styles.section} ${styles.sectionPadded}`}>
          <div className={styles.sectionTitle}>Quality Assessment</div>
          <div className={styles.qualityPanel}>
            {Object.entries(qualityFactors).map(([name, score]) => (
              <div key={name} className={styles.factorRow}>
                <span className={styles.factorName}>{displayLabel(name)}</span>
                <div className={styles.factorBarBg}>
                  <div
                    className={styles.factorBarFill}
                    style={{
                      width: `${Math.min(Math.max(score * 100, 0), 100)}%`,
                      backgroundColor:
                        score >= 0.7 ? '#22C55E' : score >= 0.4 ? '#F59E0B' : '#EF4444',
                    }}
                  />
                </div>
                <span className={styles.factorScore}>{fmtNumber(score, 2)}</span>
              </div>
            ))}
            <div>
              <span
                className={`${styles.compositeAdj} ${
                  compositeAdj >= 0 ? styles.adjPositive : styles.adjNegative
                }`}
              >
                Composite: {compositeAdj >= 0 ? '+' : ''}
                {fmtPct(compositeAdj)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Ticker Hover Popup */}
      {hoveredTicker && (
        <div
          className={styles.tickerPopup}
          style={{ left: hoverPos.x, top: hoverPos.y }}
        >
          <div className={styles.popupTicker}>{hoveredTicker}</div>
          <div className={styles.popupDesc}>
            {companyDesc[hoveredTicker] ?? 'Loading...'}
          </div>
        </div>
      )}
    </div>
  );
}
