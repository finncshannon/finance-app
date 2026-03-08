import { useState, useEffect, useCallback, useRef } from 'react';
import { Tabs } from '../components/ui/Tabs/Tabs';
import { TickerHeaderBar } from '../components/ui/TickerHeaderBar/TickerHeaderBar';
import { ErrorBoundary } from '../components/ui/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../components/ui/ExportButton/ExportDropdown';
import { WatchlistPicker } from '../components/ui/WatchlistPicker/WatchlistPicker';
import { useModelStore, type ModelType } from '../stores/modelStore';
import { useMarketStore } from '../stores/marketStore';
import { useUIStore } from '../stores/uiStore';
import { useTickerNavigation } from '../hooks/useTickerNavigation';
import { api } from '../services/api';
import { downloadExport } from '../services/exportService';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface SaveVersionResponse {}
import { OverviewTab } from './ModelBuilder/OverviewTab';
import { HistoricalDataTab } from './ModelBuilder/HistoricalDataTab';
import { AssumptionsTab } from './ModelBuilder/AssumptionsTab';
import { ModelTab } from './ModelBuilder/ModelTab';
import { SensitivityTab } from './ModelBuilder/SensitivityTab';
import { HistoryTab } from './ModelBuilder/HistoryTab';
import styles from './ModelBuilder/ModelBuilder.module.css';

const MODEL_TYPE_LABELS: Record<string, string> = {
  dcf: 'DCF',
  ddm: 'DDM',
  comps: 'Comps',
  revenue_based: 'Revenue-Based',
};

const MODEL_TAB_LABELS: Record<string, string> = {
  dcf: 'DCF Model',
  ddm: 'DDM Model',
  comps: 'Comps Model',
  revenue_based: 'Revenue Model',
};

const MODEL_TYPES: ModelType[] = ['dcf', 'ddm', 'comps', 'revenue_based'];

interface SearchResult {
  ticker: string;
  company_name: string;
  exchange?: string;
}

interface CompanyProfile {
  ticker: string;
  company_name: string;
  sector?: string;
  industry?: string;
  exchange?: string;
}

export function ModelBuilderPage() {
  const activeTicker = useModelStore((s) => s.activeTicker);
  const activeModelType = useModelStore((s) => s.activeModelType);
  const detectionResult = useModelStore((s) => s.detectionResult);
  const loading = useModelStore((s) => s.loading);
  const setTicker = useModelStore((s) => s.setTicker);
  const setModelType = useModelStore((s) => s.setModelType);

  const activeModelId = useModelStore((s) => s.activeModelId);

  const activeSubTab = useUIStore((s) => s.activeSubTabs['model-builder'] ?? 'overview');
  const setSubTab = useUIStore((s) => s.setSubTab);

  // Save macro state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveAnnotation, setSaveAnnotation] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = useCallback(async () => {
    if (!activeModelId) return;
    setSaving(true);
    try {
      await api.post<SaveVersionResponse>(`/api/v1/model-builder/model/${activeModelId}/save-version`, {
        annotation: saveAnnotation.trim() || null,
      });
      setShowSaveDialog(false);
      setSaveAnnotation('');
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch {
      // Keep simple
    } finally {
      setSaving(false);
    }
  }, [activeModelId, saveAnnotation]);

  const prices = useMarketStore((s) => s.prices);

  const { handleHeaderNavigate, showWatchlistPicker, setShowWatchlistPicker } =
    useTickerNavigation(activeTicker ?? '');

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [companyProfile, setCompanyProfile] = useState<CompanyProfile | null>(null);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Build dynamic tab list — [Model] tab label changes based on model type
  const modelTabLabel: string = activeModelType ? MODEL_TAB_LABELS[activeModelType] ?? 'Model' : 'Model';
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'historical', label: 'Historical Data' },
    { id: 'assumptions', label: 'Assumptions' },
    { id: 'model', label: modelTabLabel },
    { id: 'sensitivity', label: 'Sensitivity' },
    { id: 'history', label: 'History' },
  ];

  // Auto-complete search
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchQuery(value);
      if (searchTimeout.current) clearTimeout(searchTimeout.current);

      if (value.length < 1) {
        setSearchResults([]);
        setShowDropdown(false);
        return;
      }

      searchTimeout.current = setTimeout(async () => {
        try {
          const results = await api.get<SearchResult[]>(
            `/api/v1/companies/search?q=${encodeURIComponent(value)}`,
          );
          setSearchResults(results);
          setShowDropdown(results.length > 0);
        } catch {
          setSearchResults([]);
          setShowDropdown(false);
        }
      }, 200);
    },
    [],
  );

  // Select ticker from dropdown or direct entry
  const selectTicker = useCallback(
    (ticker: string) => {
      setSearchQuery(ticker.toUpperCase());
      setShowDropdown(false);
      setTicker(ticker);

      // Fetch company profile for header bar
      api
        .get<CompanyProfile>(`/api/v1/companies/${ticker.toUpperCase()}`)
        .then(setCompanyProfile)
        .catch(() => setCompanyProfile(null));
    },
    [setTicker],
  );

  // Handle Enter key in search
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && searchQuery.trim()) {
        selectTicker(searchQuery.trim());
      }
      if (e.key === 'Escape') {
        setShowDropdown(false);
      }
    },
    [searchQuery, selectTicker],
  );

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Get price data for ticker header
  const priceData = activeTicker ? prices[activeTicker] : undefined;

  const tabContent = () => {
    switch (activeSubTab) {
      case 'overview':
        return <OverviewTab />;
      case 'historical':
        return <HistoricalDataTab />;
      case 'assumptions':
        return <AssumptionsTab />;
      case 'model':
        return <ModelTab modelType={activeModelType} />;
      case 'sensitivity':
        return <SensitivityTab />;
      case 'history':
        return <HistoryTab />;
      default:
        return <OverviewTab />;
    }
  };

  return (
    <div className={styles.page}>
      {/* Ticker search + model type selector */}
      <div className={styles.searchBar}>
        <div className={styles.searchWrapper} ref={dropdownRef}>
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Enter ticker..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (searchResults.length > 0) setShowDropdown(true);
            }}
          />
          {showDropdown && (
            <div className={styles.dropdown}>
              {searchResults.map((r) => (
                <div
                  key={r.ticker}
                  className={styles.dropdownItem}
                  onClick={() => selectTicker(r.ticker)}
                >
                  <span className={styles.dropdownTicker}>{r.ticker}</span>
                  <span className={styles.dropdownName}>{r.company_name}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {activeTicker && activeModelId && (
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
                    `${activeTicker}_${activeModelType}_${date}.xlsx`,
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
                    `${activeTicker}_${activeModelType}_${date}.pdf`,
                  );
                },
              },
            ]}
          />
        )}

        {activeTicker && (
          <button
            className={styles.pageSaveBtn}
            onClick={() => setShowSaveDialog(true)}
            disabled={!activeModelId}
            title={!activeModelId ? 'Run a model first to enable saving' : 'Save current model to version history'}
          >
            Save
          </button>
        )}
        {saveSuccess && <span className={styles.saveFlash}>Version saved</span>}

        {showSaveDialog && (
          <div className={styles.saveDialog}>
            <input
              className={styles.saveInput}
              type="text"
              placeholder="Add annotation (optional)..."
              value={saveAnnotation}
              onChange={(e) => setSaveAnnotation(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleSave();
                if (e.key === 'Escape') { setShowSaveDialog(false); setSaveAnnotation(''); }
              }}
              autoFocus
            />
            <button className={styles.saveConfirmBtn} onClick={() => void handleSave()} disabled={saving}>
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button className={styles.saveCancelBtn} onClick={() => { setShowSaveDialog(false); setSaveAnnotation(''); }}>
              Cancel
            </button>
          </div>
        )}

        {loading && <span className={styles.loadingText}>Detecting model...</span>}

        {activeTicker && !loading && (
          <div className={styles.modelSelector}>
            {MODEL_TYPES.map((type) => {
              const isActive = activeModelType === type;
              const isRecommended =
                detectionResult?.recommended_model === type;
              const cls = [
                styles.modelPill,
                isActive ? styles.modelPillActive : '',
                isRecommended && !isActive ? styles.modelPillRecommended : '',
              ]
                .filter(Boolean)
                .join(' ');
              return (
                <button
                  key={type}
                  className={cls}
                  onClick={() => setModelType(type)}
                  title={
                    isRecommended ? 'Recommended by detection engine' : undefined
                  }
                >
                  {MODEL_TYPE_LABELS[type]}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Ticker header bar (when ticker selected and data available) */}
      {activeTicker && companyProfile && priceData && (
        <TickerHeaderBar
          ticker={activeTicker}
          companyName={companyProfile.company_name}
          sector={companyProfile.sector}
          industry={companyProfile.industry}
          exchange={companyProfile.exchange}
          price={priceData.current_price}
          dayChange={priceData.day_change}
          dayChangePct={priceData.day_change_pct}
          volume={priceData.volume}
          onNavigate={handleHeaderNavigate}
        />
      )}

      {/* Detection confidence bar */}
      {detectionResult && !loading && (
        <div className={styles.detectionBar}>
          <span className={styles.detectionLabel}>Detection:</span>
          <span className={styles.detectionValue}>
            {MODEL_TYPE_LABELS[detectionResult.recommended_model] ?? detectionResult.recommended_model} recommended
          </span>
          <span
            className={`${styles.confidenceBadge} ${
              detectionResult.confidence === 'High'
                ? styles.confidenceHigh
                : detectionResult.confidence === 'Medium'
                  ? styles.confidenceMedium
                  : styles.confidenceLow
            }`}
          >
            {detectionResult.confidence} ({detectionResult.confidence_percentage}%)
          </span>
          {detectionResult.scores
            .filter((s) => s.model_type !== detectionResult.recommended_model)
            .slice(0, 2)
            .map((s) => (
              <span key={s.model_type} className={styles.detectionLabel}>
                {MODEL_TYPE_LABELS[s.model_type]}: {s.score}
              </span>
            ))}
        </div>
      )}

      {/* Tier 2 sub-tab bar */}
      {activeTicker && (
        <Tabs
          tabs={tabs}
          activeTab={activeSubTab}
          onTabChange={(id) => setSubTab('model-builder', id)}
        />
      )}

      {/* Tab content or empty state */}
      <div className={styles.tabContent}>
        <ErrorBoundary
          key={`${activeTicker}-${activeSubTab}-${activeModelType}`}
          moduleName={activeSubTab}
        >
          {activeTicker ? (
            tabContent()
          ) : (
            <div className={styles.emptyState}>
              <div className={styles.emptyTitle}>Model Builder</div>
              <div className={styles.emptyDesc}>
                Enter a ticker symbol above to start building a valuation model.
              </div>
            </div>
          )}
        </ErrorBoundary>
      </div>

      {showWatchlistPicker && activeTicker && (
        <WatchlistPicker
          ticker={activeTicker}
          open={showWatchlistPicker}
          onClose={() => setShowWatchlistPicker(false)}
        />
      )}
    </div>
  );
}
