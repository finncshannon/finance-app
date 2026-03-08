import { useState, useEffect, useRef } from 'react';
import { api } from '../../../services/api';
import { navigationService } from '../../../services/navigationService';
import styles from './WatchlistPicker.module.css';

interface WatchlistSummary {
  id: number;
  name: string;
  item_count: number;
}

interface WatchlistPickerProps {
  ticker: string;
  open: boolean;
  onClose: () => void;
}

export function WatchlistPicker({ ticker, open, onClose }: WatchlistPickerProps) {
  const [watchlists, setWatchlists] = useState<WatchlistSummary[]>([]);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');
  const [newName, setNewName] = useState('');
  const errorTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  function showMessage(msg: string, type: 'success' | 'error' = 'success') {
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    setMessage(msg);
    setMessageType(type);
    if (type === 'error') {
      errorTimerRef.current = setTimeout(() => setMessage(''), 3000);
    }
  }

  useEffect(() => {
    if (!open) return;
    api
      .get<{ watchlists: WatchlistSummary[] }>('/api/v1/dashboard/watchlists')
      .then((d) => setWatchlists(d.watchlists))
      .catch(() => {
        setWatchlists([]);
        showMessage('Failed to load watchlists', 'error');
      });
  }, [open]);

  const handleAdd = async (watchlistId: number) => {
    try {
      const ok = await navigationService.addToWatchlist(ticker, watchlistId);
      if (ok) {
        showMessage(`Added ${ticker} to watchlist`, 'success');
        setTimeout(onClose, 800);
      } else {
        showMessage(`${ticker} may already be in this watchlist`, 'error');
      }
    } catch {
      showMessage('Failed to add ticker', 'error');
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await api.post('/api/v1/dashboard/watchlists', { name: newName.trim() });
      setNewName('');
      const d = await api.get<{ watchlists: WatchlistSummary[] }>('/api/v1/dashboard/watchlists');
      setWatchlists(d.watchlists);
    } catch {
      showMessage('Failed to create watchlist', 'error');
    }
  };

  if (!open) return null;

  return (
    <>
      <div className={styles.overlay ?? ''} onClick={onClose} />
      <div className={styles.modal ?? ''}>
        <div className={styles.header ?? ''}>
          <span className={styles.title ?? ''}>Add {ticker} to Watchlist</span>
          <button className={styles.closeBtn ?? ''} onClick={onClose}>&times;</button>
        </div>
        <div className={styles.body ?? ''}>
          {watchlists.length === 0 ? (
            <div className={styles.empty ?? ''}>No watchlists yet — create one below</div>
          ) : (
            <ul className={styles.list ?? ''}>
              {watchlists.map((wl) => (
                <li key={wl.id}>
                  <button className={styles.listItem ?? ''} onClick={() => handleAdd(wl.id)}>
                    <span className={styles.listName ?? ''}>{wl.name}</span>
                    <span className={styles.listCount ?? ''}>{wl.item_count} items</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className={styles.createRow ?? ''}>
            <input
              className={styles.createInput ?? ''}
              placeholder="New watchlist name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <button
              className={styles.createBtn ?? ''}
              onClick={handleCreate}
              disabled={!newName.trim()}
            >
              Create
            </button>
          </div>
          {message && (
            <div className={`${styles.message ?? ''} ${messageType === 'error' ? styles.messageError ?? '' : ''}`}>
              {message}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
