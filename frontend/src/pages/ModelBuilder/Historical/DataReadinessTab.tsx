import { useState, useEffect, useCallback, useMemo } from 'react';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { displayModelName } from '../../../utils/displayNames';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import type { DataReadinessResult, FieldReadiness } from '../../../types/models';
import styles from './DataReadinessTab.module.css';

const ENGINE_ORDER = ['dcf', 'ddm', 'comps', 'revenue_based'] as const;

function statusIcon(status: string): { char: string; cls: string } {
  switch (status) {
    case 'present': return { char: '\u2713', cls: styles.iconPresent ?? '' };
    case 'derived': return { char: '~', cls: styles.iconDerived ?? '' };
    default:        return { char: '\u2717', cls: styles.iconMissing ?? '' };
  }
}

function sourceText(field: FieldReadiness): string {
  if (field.status === 'missing') return 'MISSING';
  if (field.source?.startsWith('computed')) return field.source;
  return 'Yahoo Finance';
}

function coverageColor(pct: number): string {
  if (pct < 0.5) return 'var(--color-negative)';
  if (pct < 0.8) return 'var(--color-warning)';
  return 'var(--color-positive)';
}

function verdictBadgeClass(verdict: string): string {
  switch (verdict) {
    case 'ready': return styles.badgeReady ?? '';
    case 'partial': return styles.badgePartial ?? '';
    default: return styles.badgeNotPossible ?? '';
  }
}

export function DataReadinessTab() {
  const activeTicker = useModelStore((s) => s.activeTicker);
  const [data, setData] = useState<DataReadinessResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReadiness = useCallback(async (ticker: string) => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const result = await api.get<DataReadinessResult>(
        `/api/v1/model-builder/${ticker}/data-readiness`,
      );
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data readiness');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTicker) {
      void fetchReadiness(activeTicker);
    } else {
      setData(null);
      setError(null);
    }
  }, [activeTicker, fetchReadiness]);

  // Default: expand non-ready engines
  const defaultExpanded = useMemo(() => {
    if (!data) return new Set<string>();
    const set = new Set<string>();
    for (const [key, eng] of Object.entries(data.engines)) {
      if (eng.verdict !== 'ready') set.add(key);
    }
    return set;
  }, [data]);

  const [expandedEngines, setExpandedEngines] = useState<Set<string>>(new Set());
  const [expandedInitialized, setExpandedInitialized] = useState(false);

  useEffect(() => {
    if (data && !expandedInitialized) {
      setExpandedEngines(defaultExpanded);
      setExpandedInitialized(true);
    }
  }, [data, defaultExpanded, expandedInitialized]);

  // Reset initialization when ticker changes
  useEffect(() => {
    setExpandedInitialized(false);
  }, [activeTicker]);

  const [collapsedTiers, setCollapsedTiers] = useState<Set<string>>(new Set());

  function toggleEngine(key: string) {
    setExpandedEngines((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleTier(tierId: string) {
    setCollapsedTiers((prev) => {
      const next = new Set(prev);
      if (next.has(tierId)) next.delete(tierId);
      else next.add(tierId);
      return next;
    });
  }

  if (!activeTicker) {
    return <div className={styles.empty}>Select a ticker to view data readiness.</div>;
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Analyzing data readiness for {activeTicker}...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.error}>
        <span className={styles.errorText}>{error}</span>
        <button className={styles.retryBtn} onClick={() => void fetchReadiness(activeTicker)}>
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const coverageFillPct = Math.min(data.coverage_pct * 100, 100);

  function renderFieldRow(field: FieldReadiness) {
    const icon = statusIcon(field.status);
    return (
      <div key={field.field} className={styles.fieldRow}>
        <span className={`${styles.fieldIcon} ${icon.cls}`}>{icon.char}</span>
        <span className={styles.fieldLabel}>{field.label}</span>
        <span className={styles.fieldYears}>{field.years_available}y</span>
        <span className={`${styles.fieldSource} ${field.status === 'missing' ? styles.fieldSourceMissing : ''}`}>
          {sourceText(field)}
        </span>
      </div>
    );
  }

  function renderTier(engineKey: string, tierName: string, tierLabel: string, fields: FieldReadiness[], defaultCollapsed: boolean) {
    const tierId = `${engineKey}-${tierName}`;
    const isCollapsed = defaultCollapsed ? !collapsedTiers.has(tierId) : collapsedTiers.has(tierId);
    const presentCount = fields.filter((f) => f.status !== 'missing').length;

    return (
      <div key={tierName} className={styles.tierSection}>
        <div className={styles.tierHeader} onClick={() => toggleTier(tierId)}>
          <span className={styles.tierLabel}>
            <span className={`${styles.chevron} ${!isCollapsed ? styles.chevronExpanded : ''}`}>&#x25B6;</span>
            {' '}{tierLabel}
          </span>
          <span className={styles.tierCount}>{presentCount}/{fields.length} present</span>
        </div>
        {!isCollapsed && fields.map(renderFieldRow)}
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Coverage */}
      <div className={styles.coverageSection}>
        <span className={styles.coverageHeader}>Data Coverage</span>
        <span className={styles.coverageStats}>
          {data.data_years_available} years available &middot; {data.populated_fields}/{data.total_fields} fields populated ({(data.coverage_pct * 100).toFixed(0)}%)
        </span>
        <div className={styles.coverageBarTrack}>
          <div
            className={styles.coverageBarFill}
            style={{
              width: `${coverageFillPct}%`,
              background: coverageColor(data.coverage_pct),
            }}
          />
        </div>
      </div>

      {/* Detection summary */}
      {data.detection_result && (
        <div className={styles.detectionRow}>
          <span className={styles.detectionLabel}>Recommended</span>
          <span className={styles.detectionModel}>{displayModelName(data.detection_result.recommended_model)}</span>
          <span className={styles.detectionConfidence}>
            {data.detection_result.confidence} ({data.detection_result.confidence_percentage}%)
          </span>
        </div>
      )}

      {/* Engine cards */}
      <div className={styles.engineCards}>
        {ENGINE_ORDER.map((engineKey) => {
          const eng = data.engines[engineKey];
          if (!eng) return null;
          const isExpanded = expandedEngines.has(engineKey);

          return (
            <div key={engineKey} className={styles.engineCard}>
              <div className={styles.engineHeader} onClick={() => toggleEngine(engineKey)}>
                <div className={styles.engineHeaderLeft}>
                  <span className={styles.engineName}>{displayModelName(engineKey)}</span>
                  <span className={`${styles.verdictBadge} ${verdictBadgeClass(eng.verdict)}`}>
                    {eng.verdict_label}
                  </span>
                </div>
                <div className={styles.engineHeaderRight}>
                  {eng.detection_score != null && (
                    <span className={styles.detectionScore}>{eng.detection_score}/100</span>
                  )}
                  <span className={`${styles.chevron} ${isExpanded ? styles.chevronExpanded : ''}`}>&#x25B6;</span>
                </div>
              </div>

              {isExpanded && (
                <div className={styles.engineBody}>
                  {eng.missing_impact && (
                    <div className={`${styles.impactNote} ${eng.verdict === 'partial' ? styles.impactNotePartial : ''}`}>
                      {eng.missing_impact}
                    </div>
                  )}
                  {renderTier(engineKey, 'critical', 'Critical', eng.critical_fields, false)}
                  {renderTier(engineKey, 'important', 'Important', eng.important_fields, false)}
                  {renderTier(engineKey, 'helpful', 'Helpful', eng.helpful_fields, true)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
