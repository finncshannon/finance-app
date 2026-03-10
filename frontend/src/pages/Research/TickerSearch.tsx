import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../../services/api';
import styles from './TickerSearch.module.css';

interface SearchResult {
  ticker: string;
  company_name: string;
  exchange?: string;
  type?: string;
}

interface TickerSearchProps {
  value: string;
  onChange: (value: string) => void;
  onSelect: (ticker: string) => void;
}

export function TickerSearch({ value, onChange, onSelect }: TickerSearchProps) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.get<SearchResult[]>(`/api/v1/companies/search?q=${encodeURIComponent(q)}`);
      const items = Array.isArray(data) ? data : [];
      setResults(items.slice(0, 12));
      setOpen(items.length > 0);
      setActiveIdx(-1);
    } catch {
      setResults([]);
      setOpen(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    onChange(v);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(v.trim()), 150);
  };

  const handleSelect = (ticker: string) => {
    setOpen(false);
    setResults([]);
    onSelect(ticker);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) {
      if (e.key === 'Enter') {
        const t = value.trim().toUpperCase();
        if (t) handleSelect(t);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIdx((i) => (i < results.length - 1 ? i + 1 : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIdx((i) => (i > 0 ? i - 1 : results.length - 1));
        break;
      case 'Enter':
        e.preventDefault();
        if (activeIdx >= 0 && activeIdx < results.length) {
          handleSelect(results[activeIdx]!.ticker);
        } else {
          const t = value.trim().toUpperCase();
          if (t) handleSelect(t);
        }
        break;
      case 'Escape':
        setOpen(false);
        setActiveIdx(-1);
        break;
    }
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <input
        ref={inputRef}
        className={`${styles.input} ${open ? styles.inputOpen : ''}`}
        type="text"
        placeholder="Search ticker or company..."
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => { if (results.length > 0) setOpen(true); }}
      />

      {open && (
        <div className={styles.dropdown}>
          {loading && results.length === 0 ? (
            <div className={styles.loading}>Searching...</div>
          ) : results.length === 0 ? (
            <div className={styles.empty}>No results</div>
          ) : (
            results.map((r, i) => (
              <button
                key={r.ticker}
                className={`${styles.item} ${i === activeIdx ? styles.itemActive : ''}`}
                onMouseDown={(e) => { e.preventDefault(); handleSelect(r.ticker); }}
                onMouseEnter={() => setActiveIdx(i)}
              >
                <span className={styles.ticker}>{r.ticker}</span>
                <span className={styles.name}>{r.company_name}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
