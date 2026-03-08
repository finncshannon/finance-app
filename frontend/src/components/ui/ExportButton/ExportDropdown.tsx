import { useState, useRef, useEffect } from 'react';
import styles from './ExportDropdown.module.css';

interface ExportOption {
  label: string;
  format: string;
  onClick: () => Promise<void>;
}

interface ExportDropdownProps {
  options: ExportOption[];
}

export function ExportDropdown({ options }: ExportDropdownProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleOption = async (opt: ExportOption) => {
    setLoading(true);
    setOpen(false);
    try {
      await opt.onClick();
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper ?? ''} ref={ref}>
      <button
        className={styles.btn ?? ''}
        onClick={() => setOpen(!open)}
        disabled={loading}
      >
        {loading ? 'Exporting...' : 'Export ▾'}
      </button>
      {open && (
        <div className={styles.menu ?? ''}>
          {options.map((opt) => (
            <button
              key={opt.format}
              className={styles.option ?? ''}
              onClick={() => handleOption(opt)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
