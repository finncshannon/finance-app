import { useState, useRef, useEffect, useMemo } from 'react';
import type { ScannerPreset } from '../types';
import styles from './PresetSelector.module.css';

interface PresetSelectorProps {
  presets: ScannerPreset[];
  onSelect: (preset: ScannerPreset) => void;
  onDelete: (id: number) => void;
}

export function PresetSelector({ presets, onSelect, onDelete }: PresetSelectorProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const builtIn = useMemo(() => presets.filter((p) => p.is_built_in), [presets]);
  const userPresets = useMemo(() => presets.filter((p) => !p.is_built_in), [presets]);

  const handleSelect = (preset: ScannerPreset) => {
    onSelect(preset);
    setOpen(false);
  };

  const handleDelete = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    onDelete(id);
  };

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <button
        className={`${styles.trigger} ${styles.triggerEmpty}`}
        onClick={() => setOpen(!open)}
        type="button"
      >
        Load Preset...
      </button>

      {open && (
        <div className={styles.dropdown}>
          {/* Built-in presets */}
          {builtIn.length > 0 && (
            <>
              <div className={styles.sectionHeader}>Built-in</div>
              {builtIn.map((p) => (
                <div
                  key={`builtin-${p.id ?? p.name}`}
                  className={styles.item}
                  onClick={() => handleSelect(p)}
                  title={p.description || undefined}
                >
                  <span className={styles.itemName}>{p.name}</span>
                  <span className={styles.filterCount}>{p.filters.length}</span>
                </div>
              ))}
            </>
          )}

          {/* User presets */}
          <div className={styles.sectionHeader}>My Presets</div>
          {userPresets.length > 0 ? (
            userPresets.map((p) => (
              <div
                key={`user-${p.id ?? p.name}`}
                className={styles.item}
                onClick={() => handleSelect(p)}
              >
                <span className={styles.itemName}>{p.name}</span>
                <span className={styles.filterCount}>{p.filters.length}</span>
                {p.id != null && (
                  <button
                    className={styles.deleteBtn}
                    onClick={(e) => handleDelete(e, p.id!)}
                    type="button"
                    title="Delete preset"
                  >
                    &#x2715;
                  </button>
                )}
              </div>
            ))
          ) : (
            <div className={styles.emptyState}>No saved presets</div>
          )}
        </div>
      )}
    </div>
  );
}
