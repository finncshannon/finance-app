import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import { Card } from '../../../components/ui/Card/Card';
import styles from './CacheManagement.module.css';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function CacheManagement() {
  const [cacheSize, setCacheSize] = useState<number>(0);
  const [clearing, setClearing] = useState(false);
  const [message, setMessage] = useState('');

  const loadSize = async () => {
    try {
      const data = await api.get<{ cache_size_bytes: number }>('/api/v1/settings/cache-size');
      setCacheSize(data.cache_size_bytes);
    } catch {
      // silently handle
    }
  };

  useEffect(() => { loadSize(); }, []);

  const handleClear = async () => {
    if (!window.confirm('Clear all cached market data? This will require re-fetching.')) return;
    setClearing(true);
    setMessage('');
    try {
      await api.post('/api/v1/settings/clear-cache', {});
      setMessage('Cache cleared successfully');
      await loadSize();
    } catch {
      setMessage('Failed to clear cache');
    } finally {
      setClearing(false);
    }
  };

  return (
    <Card>
      <p className={styles.title ?? ''}>Cache Management</p>
      <div className={styles.row ?? ''}>
        <span className={styles.label ?? ''}>Market data cache</span>
        <span className={styles.value ?? ''}>{formatBytes(cacheSize)}</span>
      </div>
      <div className={styles.actions ?? ''}>
        <button
          className={styles.clearBtn ?? ''}
          onClick={handleClear}
          disabled={clearing}
        >
          {clearing ? 'Clearing...' : 'Clear Cache'}
        </button>
      </div>
      {message && <p className={styles.message ?? ''}>{message}</p>}
    </Card>
  );
}
