import { useState, useRef, useEffect, useMemo } from 'react';
import type { MetricDefinition } from '../types';
import styles from './MetricPicker.module.css';

interface MetricPickerProps {
  metrics: MetricDefinition[];
  categories: Record<string, string[]>;
  value: string;
  onChange: (key: string) => void;
}

const FORMAT_BADGES: Record<string, string> = {
  percent: '%',
  currency: '$',
  ratio: 'x',
};

export function MetricPicker({ metrics, categories, value, onChange }: MetricPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const wrapperRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Focus search when dropdown opens
  useEffect(() => {
    if (open && searchRef.current) {
      searchRef.current.focus();
    }
  }, [open]);

  // Build lookup
  const metricsMap = useMemo(() => new Map(metrics.map((m) => [m.key, m])), [metrics]);

  // Filter by search term
  const lowerSearch = search.toLowerCase();
  const filtered = useMemo(() => {
    if (!lowerSearch) return metrics;
    return metrics.filter(
      (m) =>
        m.label.toLowerCase().includes(lowerSearch) ||
        m.key.toLowerCase().includes(lowerSearch) ||
        m.category.toLowerCase().includes(lowerSearch),
    );
  }, [metrics, lowerSearch]);

  // Group filtered metrics by category (preserving category order)
  const grouped = useMemo(() => {
    const filteredKeys = new Set(filtered.map((m) => m.key));
    const result: { category: string; items: MetricDefinition[] }[] = [];
    for (const [cat, keys] of Object.entries(categories)) {
      const items = keys.filter((k) => filteredKeys.has(k)).map((k) => metricsMap.get(k)!).filter(Boolean);
      if (items.length > 0) {
        result.push({ category: cat, items });
      }
    }
    return result;
  }, [filtered, categories, metricsMap]);

  const selectedLabel = value ? metricsMap.get(value)?.label : undefined;

  const handleSelect = (key: string) => {
    onChange(key);
    setOpen(false);
    setSearch('');
  };

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <button
        className={`${styles.trigger} ${!value ? styles.triggerEmpty : ''}`}
        onClick={() => setOpen(!open)}
        type="button"
      >
        {selectedLabel || 'Select metric...'}
      </button>

      {open && (
        <div className={styles.dropdown}>
          <input
            ref={searchRef}
            className={styles.searchInput}
            placeholder="Search metrics..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {grouped.map(({ category, items }) => (
            <div key={category}>
              <div className={styles.categoryHeader}>
                {category} <span className={styles.categoryCount}>({items.length})</span>
              </div>
              {items.map((m) => (
                <div
                  key={m.key}
                  className={`${styles.item} ${m.key === value ? styles.itemActive : ''}`}
                  onClick={() => handleSelect(m.key)}
                >
                  <span>{m.label}</span>
                  {FORMAT_BADGES[m.format] && (
                    <span className={styles.formatBadge}>{FORMAT_BADGES[m.format]}</span>
                  )}
                </div>
              ))}
            </div>
          ))}
          {grouped.length === 0 && (
            <div className={styles.item} style={{ color: 'var(--text-tertiary)', cursor: 'default' }}>
              No metrics found
            </div>
          )}
        </div>
      )}
    </div>
  );
}
