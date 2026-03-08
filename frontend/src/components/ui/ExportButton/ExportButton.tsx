import { useState } from 'react';
import styles from './ExportButton.module.css';

interface ExportButtonProps {
  label?: string;
  onClick: () => Promise<void>;
}

export function ExportButton({ label = 'Export', onClick }: ExportButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      await onClick();
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      className={styles.btn ?? ''}
      onClick={handleClick}
      disabled={loading}
    >
      {loading ? 'Exporting...' : label}
    </button>
  );
}
