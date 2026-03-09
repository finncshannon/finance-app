import { Fragment, useState, useCallback, useRef, useEffect } from 'react';
import { navigationService } from '../../../services/navigationService';
import { api } from '../../../services/api';
import type { ScannerResult, ScannerFilter, MetricDefinition } from '../types';
import { formatMetricValue } from '../types';
import { ResultsHeader } from './ResultsHeader';
import { DetailPanel } from './DetailPanel';
import { ContextMenu } from './ContextMenu';
import styles from './ResultsTable.module.css';

interface ResultsTableProps {
  results: ScannerResult | null;
  loading: boolean;
  metricsMap: Map<string, MetricDefinition>;
  sortBy: string | null;
  sortDesc: boolean;
  onSort: (metricKey: string) => void;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  columns: string[];
  onColumnsChange: (cols: string[]) => void;
  activeFilters?: ScannerFilter[];
  universe?: string;
}

const UNIVERSE_LABELS: Record<string, string> = {
  all: 'All Companies',
  dow: 'DOW 30',
  sp500: 'S&P 500',
  r3000: 'Russell 3000',
};

export function ResultsTable({
  results,
  loading,
  metricsMap,
  sortBy,
  sortDesc,
  onSort,
  page,
  pageSize,
  onPageChange,
  columns,
  onColumnsChange,
  activeFilters,
  universe,
}: ResultsTableProps) {
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    ticker: string;
  } | null>(null);
  const [textHitsOpen, setTextHitsOpen] = useState(false);
  const [hoveredTicker, setHoveredTicker] = useState<string | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [companyDesc, setCompanyDesc] = useState<Record<string, string>>({});
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleTickerMouseEnter = useCallback((e: React.MouseEvent, ticker: string) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setHoverPos({ x: rect.left, y: rect.bottom + 4 });
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    hoverTimeout.current = setTimeout(() => {
      setHoveredTicker(ticker);
      // Fetch description if not cached
      if (!companyDesc[ticker]) {
        api.get<{ data?: { description?: string; company_name?: string; sector?: string; industry?: string } }>(`/api/v1/companies/${ticker}`)
          .then((res) => {
            const d = (res as any)?.data ?? res;
            const desc = d?.description || d?.company_name || 'No description available';
            const sector = d?.sector || '';
            const industry = d?.industry || '';
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
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setHoveredTicker(null);
  }, []);

  const handleTickerClick = useCallback((e: React.MouseEvent, ticker: string) => {
    e.stopPropagation();
    navigationService.goToResearch(ticker);
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); };
  }, []);

  const handleRowClick = useCallback((ticker: string) => {
    setExpandedTicker((prev) => (prev === ticker ? null : ticker));
  }, []);

  const handleRowDoubleClick = useCallback((ticker: string) => {
    navigationService.goToModelBuilder(ticker);
  }, []);

  const handleRowContextMenu = useCallback(
    (e: React.MouseEvent, ticker: string) => {
      e.preventDefault();
      setContextMenu({ x: e.clientX, y: e.clientY, ticker });
    },
    [],
  );

  /* ── Empty / null states ── */
  if (!results && !loading) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>Run a scan to see results</div>
      </div>
    );
  }

  if (results && results.rows.length === 0 && !loading) {
    return (
      <div className={styles.container}>
        <ResultsHeader
          totalMatches={0}
          computationTimeMs={results.computation_time_ms}
          universeSize={results.universe_size}
          appliedFilters={results.applied_filters}
          visibleColumns={columns}
          metricsMap={metricsMap}
          onColumnsChange={onColumnsChange}
          activeFilters={activeFilters}
          universeName={universe ? UNIVERSE_LABELS[universe] : undefined}
          page={page}
          pageSize={pageSize}
        />
        <div className={styles.empty}>No matches found</div>
      </div>
    );
  }

  const rows = results?.rows ?? [];
  const totalMatches = results?.total_matches ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalMatches / pageSize));
  const startIdx = page * pageSize + 1;
  const endIdx = Math.min((page + 1) * pageSize, totalMatches);
  const textHits = results?.text_hits ?? [];

  /* Build ordered column defs for visible metrics */
  const columnDefs = columns
    .map((key) => metricsMap.get(key))
    .filter((d): d is MetricDefinition => d != null);

  return (
    <div className={styles.container}>
      {/* ── Header ── */}
      {results && (
        <ResultsHeader
          totalMatches={results.total_matches}
          computationTimeMs={results.computation_time_ms}
          universeSize={results.universe_size}
          appliedFilters={results.applied_filters}
          visibleColumns={columns}
          metricsMap={metricsMap}
          onColumnsChange={onColumnsChange}
          activeFilters={activeFilters}
          universeName={universe ? UNIVERSE_LABELS[universe] : undefined}
          page={page}
          pageSize={pageSize}
        />
      )}

      {/* ── Table ── */}
      <div className={`${styles.tableWrap} ${loading ? styles.loading : ''}`}>
        <table className={styles.table}>
          <thead className={styles.thead}>
            <tr>
              <th
                className={`${styles.th} ${styles.thTicker}`}
                onClick={() => onSort('ticker')}
              >
                Ticker
                {sortBy === 'ticker' && (
                  <span className={styles.sortArrow}>
                    {sortDesc ? '\u25BC' : '\u25B2'}
                  </span>
                )}
              </th>
              <th className={styles.th}>Company</th>
              <th className={styles.th}>Sector</th>
              {columnDefs.map((def) => (
                <th
                  key={def.key}
                  className={`${styles.th} ${sortBy === def.key ? styles.thActive : ''}`}
                  onClick={() => onSort(def.key)}
                >
                  {def.label}
                  {sortBy === def.key && (
                    <span className={styles.sortArrow}>
                      {sortDesc ? '\u25BC' : '\u25B2'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const isExpanded = expandedTicker === row.ticker;
              const rowClass = [
                styles.tr,
                idx % 2 === 0 ? styles.trEven : styles.trOdd,
                isExpanded ? styles.trExpanded : '',
              ]
                .filter(Boolean)
                .join(' ');

              return (
                <Fragment key={row.ticker}>
                  <tr
                    className={rowClass}
                    onClick={() => handleRowClick(row.ticker)}
                    onDoubleClick={() => handleRowDoubleClick(row.ticker)}
                    onContextMenu={(e) => handleRowContextMenu(e, row.ticker)}
                  >
                    <td className={`${styles.td} ${styles.tdTicker}`}>
                      <span
                        className={styles.tickerLink}
                        onClick={(e) => handleTickerClick(e, row.ticker)}
                        onMouseEnter={(e) => handleTickerMouseEnter(e, row.ticker)}
                        onMouseLeave={handleTickerMouseLeave}
                      >
                        {row.ticker}
                      </span>
                    </td>
                    <td className={`${styles.td} ${styles.tdCompany}`}>
                      {row.company_name ?? '\u2014'}
                    </td>
                    <td className={`${styles.td} ${styles.tdSector}`}>
                      {row.sector ?? '\u2014'}
                    </td>
                    {columnDefs.map((def) => {
                      const val = row.metrics[def.key];
                      return (
                        <td
                          key={def.key}
                          className={`${styles.td} ${styles.tdNumeric} ${val != null && val < 0 ? styles.cellNegative : ''}`}
                        >
                          {formatMetricValue(val, def.format)}
                        </td>
                      );
                    })}
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={3 + columnDefs.length}>
                        <DetailPanel row={row} metricsMap={metricsMap} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ── */}
      {totalMatches > 0 && (
        <div className={styles.pagination}>
          <span className={styles.pageInfo}>
            {startIdx}&ndash;{endIdx} of {totalMatches.toLocaleString()}
          </span>
          <div className={styles.pageBtns}>
            <button
              className={styles.pageBtn}
              disabled={page === 0}
              onClick={() => onPageChange(page - 1)}
            >
              Prev
            </button>
            <span className={styles.pageInfo}>
              {page + 1} / {totalPages}
            </span>
            <button
              className={styles.pageBtn}
              disabled={page >= totalPages - 1}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* ── Text Search Hits ── */}
      {textHits.length > 0 && (
        <div className={styles.textHitsSection}>
          <div
            className={styles.textHitsHeader}
            onClick={() => setTextHitsOpen((v) => !v)}
          >
            {textHitsOpen ? '\u25BC' : '\u25B6'} Text Matches ({results?.text_hit_count ?? textHits.length})
          </div>
          {textHitsOpen && (
            <div className={styles.textHitsList}>
              {textHits.map((hit, i) => (
                <div key={`${hit.ticker}-${i}`} className={styles.textHit}>
                  <div className={styles.textHitMeta}>
                    <span className={styles.textHitTicker}>{hit.ticker}</span>
                    {hit.company_name && <> &mdash; {hit.company_name}</>}
                    {hit.form_type && <> &middot; {hit.form_type}</>}
                    {hit.filing_date && <> &middot; {hit.filing_date}</>}
                    {hit.section_title && <> &middot; {hit.section_title}</>}
                  </div>
                  <div className={styles.textHitSnippet}>{hit.snippet}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Ticker Hover Popup ── */}
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

      {/* ── Context Menu ── */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          ticker={contextMenu.ticker}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
}
