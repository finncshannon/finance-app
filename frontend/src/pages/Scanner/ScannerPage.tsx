import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../../services/api';
import { downloadExport } from '../../services/exportService';
import { ExportDropdown } from '../../components/ui/ExportButton/ExportDropdown';
import { FilterPanel } from './FilterPanel/FilterPanel';
import { ResultsTable } from './ResultsTable/ResultsTable';
import styles from './ScannerPage.module.css';
import type {
  ScannerFilter,
  ScannerResult,
  MetricDefinition,
  MetricsCatalog,
  ScannerPreset,
} from './types';

const PAGE_SIZE = 100;

export function ScannerPage() {
  /* ── Catalog & presets (loaded once) ── */
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [categories, setCategories] = useState<Record<string, string[]>>({});
  const [presets, setPresets] = useState<ScannerPreset[]>([]);

  /* ── Filter state ── */
  const [filters, setFilters] = useState<ScannerFilter[]>([]);
  const [textQuery, setTextQuery] = useState('');
  const [formTypes, setFormTypes] = useState<string[]>(['10-K']);
  const [sectorFilter, setSectorFilter] = useState<string | null>(null);
  const [universe, setUniverse] = useState('all');

  /* ── Sort / pagination ── */
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortDesc, setSortDesc] = useState(true);
  const [page, setPage] = useState(0);

  /* ── Results ── */
  const [results, setResults] = useState<ScannerResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  /* ── Universe stats ── */
  const [universeStats, setUniverseStats] = useState<{
    total: number;
    with_financials: number;
    with_market_data: number;
  } | null>(null);

  /* ── Dynamic columns ── */
  const [manualColumns, setManualColumns] = useState<string[] | null>(null);

  const effectiveColumns = useMemo(() => {
    if (manualColumns) return manualColumns;

    const FIXED = ['current_price', 'market_cap'];
    const DEFAULT_VARIABLE = ['pe_trailing', 'ev_to_ebitda', 'roe', 'revenue_growth', 'dividend_yield'];
    const MAX_VARIABLE = 5;

    const filterMetrics = filters
      .map((f) => f.metric)
      .filter((m) => m && !FIXED.includes(m));
    const uniqueFilterMetrics = [...new Set(filterMetrics)];

    const variable: string[] = [];
    for (const m of uniqueFilterMetrics) {
      if (!variable.includes(m) && variable.length < MAX_VARIABLE) variable.push(m);
    }
    for (const m of DEFAULT_VARIABLE) {
      if (!variable.includes(m) && !FIXED.includes(m) && variable.length < MAX_VARIABLE) variable.push(m);
    }

    return [...FIXED, ...variable];
  }, [filters, manualColumns]);

  /* ── Save preset modal ── */
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [presetName, setPresetName] = useState('');

  /* ── Load catalogs on mount ── */
  useEffect(() => {
    api.get<MetricsCatalog>('/api/v1/scanner/metrics').then((data) => {
      setMetrics(data.metrics);
      setCategories(data.categories);
    });
    loadPresets();
    api
      .get<{ total: number; with_financials: number; with_market_data: number }>(
        '/api/v1/scanner/universe/stats',
      )
      .then(setUniverseStats);
  }, []);

  const loadPresets = useCallback(() => {
    api.get<{ presets: ScannerPreset[] }>('/api/v1/scanner/presets').then((d) => {
      setPresets(d.presets);
    });
  }, []);

  /* ── Run scan ── */
  const runScan = useCallback(async () => {
    setLoading(true);
    setScanError(null);
    try {
      const result = await api.post<ScannerResult>('/api/v1/scanner/screen', {
        filters,
        text_query: textQuery || null,
        form_types: formTypes,
        sector_filter: sectorFilter,
        universe,
        sort_by: sortBy,
        sort_desc: sortDesc,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      setResults(result);
    } catch (err) {
      setScanError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setLoading(false);
    }
  }, [filters, textQuery, formTypes, sectorFilter, universe, sortBy, sortDesc, page]);

  /* ── Debounced auto-scan on filter change ── */
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      runScan();
    }, 500);
    return () => clearTimeout(timerRef.current);
  }, [runScan]);

  /* ── Sort handler ── */
  const handleSort = useCallback(
    (metricKey: string) => {
      if (sortBy === metricKey) {
        setSortDesc((d) => !d);
      } else {
        setSortBy(metricKey);
        setSortDesc(true);
      }
      setPage(0);
    },
    [sortBy],
  );

  /* ── Preset selection ── */
  const handleSelectPreset = useCallback((preset: ScannerPreset) => {
    setFilters(preset.filters);
    setTextQuery(preset.text_query ?? '');
    setSectorFilter(preset.sector_filter ?? null);
    setUniverse(preset.universe ?? 'all');
    setFormTypes(preset.form_types ?? ['10-K']);
    setPage(0);
  }, []);

  /* ── Clear all ── */
  const handleClear = useCallback(() => {
    setFilters([]);
    setTextQuery('');
    setSectorFilter(null);
    setUniverse('all');
    setSortBy(null);
    setSortDesc(true);
    setPage(0);
    setResults(null);
  }, []);

  /* ── Save preset ── */
  const handleSavePreset = useCallback(async () => {
    if (!presetName.trim()) return;
    await api.post('/api/v1/scanner/presets', {
      name: presetName.trim(),
      filters: filters.map((f) => ({
        metric: f.metric,
        operator: f.operator,
        value: f.value,
        low: f.low,
        high: f.high,
        values: f.values,
        percentile: f.percentile,
      })),
      text_query: textQuery || null,
      sector_filter: sectorFilter,
      universe,
      form_types: formTypes,
    });
    setShowSaveModal(false);
    setPresetName('');
    loadPresets();
  }, [presetName, filters, textQuery, sectorFilter, universe, formTypes, loadPresets]);

  /* ── Delete preset ── */
  const handleDeletePreset = useCallback(
    async (id: number) => {
      await api.del(`/api/v1/scanner/presets/${id}`);
      loadPresets();
    },
    [loadPresets],
  );

  /* ── Build metrics lookup ── */
  const metricsMap = new Map(metrics.map((m) => [m.key, m]));

  return (
    <div className={styles.page}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <h2 className={styles.title}>Scanner</h2>
        <div className={styles.stats}>
          {universeStats && (
            <>
              <span>{universeStats.total.toLocaleString()} companies</span>
              <span className={styles.statDot} />
              <span>{universeStats.with_financials} w/ financials</span>
              <span className={styles.statDot} />
              <span>{universeStats.with_market_data} w/ market data</span>
            </>
          )}
        </div>
        <div className={styles.headerActions}>
          {results && results.rows && results.rows.length > 0 && (
            <ExportDropdown
              options={[
                {
                  label: 'Excel (.xlsx)',
                  format: 'excel',
                  onClick: async () => {
                    const date = new Date().toISOString().slice(0, 10);
                    await downloadExport(
                      '/api/v1/export/scanner/excel',
                      `scanner_results_${date}.xlsx`,
                      { results: results!.rows, config: { filters, textQuery, formTypes, sectorFilter, universe } },
                    );
                  },
                },
                {
                  label: 'CSV',
                  format: 'csv',
                  onClick: async () => {
                    const date = new Date().toISOString().slice(0, 10);
                    await downloadExport(
                      '/api/v1/export/scanner/csv',
                      `scanner_results_${date}.csv`,
                      { results: results!.rows },
                    );
                  },
                },
              ]}
            />
          )}
          <button className={styles.runBtn} onClick={runScan} disabled={loading}>
            {loading ? 'Scanning...' : 'Run Scan'}
          </button>
        </div>
      </div>

      {/* ── Body: Filter Panel + Results ── */}
      <div className={styles.body}>
        <div className={styles.filterSide}>
          <FilterPanel
            metrics={metrics}
            categories={categories}
            presets={presets}
            filters={filters}
            textQuery={textQuery}
            formTypes={formTypes}
            universe={universe}
            onUniverseChange={setUniverse}
            onFiltersChange={setFilters}
            onTextQueryChange={setTextQuery}
            onFormTypesChange={setFormTypes}
            onSelectPreset={handleSelectPreset}
            onDeletePreset={handleDeletePreset}
            onClear={handleClear}
            onSave={() => setShowSaveModal(true)}
          />
        </div>
        <div className={styles.resultsSide}>
          {scanError && (
            <div className={styles.errorBanner}>{scanError}</div>
          )}
          <ResultsTable
            results={results}
            loading={loading}
            metricsMap={metricsMap}
            sortBy={sortBy}
            sortDesc={sortDesc}
            onSort={handleSort}
            page={page}
            pageSize={PAGE_SIZE}
            onPageChange={setPage}
            columns={effectiveColumns}
            onColumnsChange={(cols) => setManualColumns(cols)}
            activeFilters={filters}
            universe={universe}
          />
        </div>
      </div>

      {/* ── Save Preset Modal ── */}
      {showSaveModal && (
        <div className={styles.modalOverlay} onClick={() => setShowSaveModal(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>Save Preset</h3>
            <input
              className={styles.modalInput}
              placeholder="Preset name"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSavePreset()}
              autoFocus
            />
            <p className={styles.modalSummary}>
              {filters.length} filter{filters.length !== 1 ? 's' : ''}
              {textQuery ? ` + text search "${textQuery}"` : ''}
            </p>
            <div className={styles.modalActions}>
              <button className={styles.modalBtn} onClick={() => setShowSaveModal(false)}>
                Cancel
              </button>
              <button
                className={styles.modalBtnPrimary}
                onClick={handleSavePreset}
                disabled={!presetName.trim()}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
