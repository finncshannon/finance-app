import { useState, useRef, useEffect, useMemo } from 'react';
import type { MetricDefinition, ScannerFilter } from '../types';
import { formatMetricValue } from '../types';
import styles from './ResultsTable.module.css';

interface ResultsHeaderProps {
  totalMatches: number;
  computationTimeMs: number;
  universeSize: number;
  appliedFilters: number;
  visibleColumns: string[];
  metricsMap: Map<string, MetricDefinition>;
  onColumnsChange: (cols: string[]) => void;
  activeFilters?: ScannerFilter[];
  universeName?: string;
  page?: number;
  pageSize?: number;
}

function buildFilterLabel(metric: MetricDefinition, f: ScannerFilter): string {
  const name = metric.label;
  const fmtVal = (v: number | null | undefined) => formatMetricValue(v ?? null, metric.format);
  switch (f.operator) {
    case 'gt': return `${name} > ${fmtVal(f.value)}`;
    case 'gte': return `${name} \u2265 ${fmtVal(f.value)}`;
    case 'lt': return `${name} < ${fmtVal(f.value)}`;
    case 'lte': return `${name} \u2264 ${fmtVal(f.value)}`;
    case 'eq': return `${name} = ${fmtVal(f.value)}`;
    case 'neq': return `${name} \u2260 ${fmtVal(f.value)}`;
    case 'between': return `${name}: ${fmtVal(f.low)} \u2013 ${fmtVal(f.high)}`;
    case 'top_pct': return `${name}: Top ${f.percentile}%`;
    case 'bot_pct': return `${name}: Bottom ${f.percentile}%`;
    default: return name;
  }
}

export function ResultsHeader({
  totalMatches,
  computationTimeMs,
  universeSize,
  appliedFilters,
  visibleColumns,
  metricsMap,
  onColumnsChange,
  activeFilters,
  universeName,
  page,
  pageSize,
}: ResultsHeaderProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  /* Close dropdown on outside click */
  useEffect(() => {
    if (!showDropdown) return;
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showDropdown]);

  /* Group metrics by category */
  const grouped = useMemo(() => {
    const map = new Map<string, MetricDefinition[]>();
    for (const def of metricsMap.values()) {
      const list = map.get(def.category) ?? [];
      list.push(def);
      map.set(def.category, list);
    }
    return map;
  }, [metricsMap]);

  const toggleColumn = (key: string) => {
    if (visibleColumns.includes(key)) {
      onColumnsChange(visibleColumns.filter((c) => c !== key));
    } else {
      onColumnsChange([...visibleColumns, key]);
    }
  };

  const startRow = page != null && pageSize ? page * pageSize + 1 : 1;
  const endRow = page != null && pageSize ? Math.min((page + 1) * pageSize, totalMatches) : totalMatches;

  return (
    <div className={styles.resultsHeader}>
      <div>
        {/* Filter summary tags */}
        {activeFilters && activeFilters.length > 0 && (
          <div className={styles.filterTags}>
            {activeFilters.map((f, i) => {
              const metric = metricsMap.get(f.metric);
              if (!metric) return null;
              const label = buildFilterLabel(metric, f);
              return (
                <span key={i} className={styles.filterTag}>{label}</span>
              );
            })}
          </div>
        )}

        {/* Stats text */}
        <div className={styles.statsText}>
          Showing {startRow}&ndash;{endRow} of {totalMatches.toLocaleString()} matches
          {universeName && <> from {universeName}</>}
          {' '}({universeSize.toLocaleString()} scanned)
          <span className={styles.statSep}>&middot;</span>
          {appliedFilters} filter{appliedFilters !== 1 ? 's' : ''}
          <span className={styles.statSep}>&middot;</span>
          {computationTimeMs}ms
        </div>
      </div>

      <div className={styles.colConfigWrap} ref={dropdownRef}>
        <button
          className={styles.colConfigBtn}
          onClick={() => setShowDropdown((v) => !v)}
        >
          Columns {showDropdown ? '\u25B2' : '\u25BC'}
        </button>

        {showDropdown && (
          <div className={styles.colDropdown}>
            {Array.from(grouped.entries()).map(([category, defs]) => (
              <div key={category}>
                <div className={styles.colCategory}>{category}</div>
                {defs.map((def) => (
                  <label
                    key={def.key}
                    className={styles.colItem}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      className={styles.colCheckbox}
                      checked={visibleColumns.includes(def.key)}
                      onChange={() => toggleColumn(def.key)}
                    />
                    {def.label}
                  </label>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
