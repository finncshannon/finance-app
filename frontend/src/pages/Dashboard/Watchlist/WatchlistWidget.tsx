import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../../../services/api';
import { navigationService } from '../../../services/navigationService';
import {
  type WatchlistSummary,
  type WatchlistDetail,
  fmtDollar,
  fmtSignedPct,
  gainColor,
} from '../types';
import s from './WatchlistWidget.module.css';

interface Props {
  watchlists: WatchlistSummary[];
  onRefresh: () => void;
}

type SortCol = 'ticker' | 'name' | 'price' | 'change' | 'pe';
type SortDir = 'asc' | 'desc';

export function WatchlistWidget({ watchlists, onRefresh }: Props) {
  const [activeWatchlistId, setActiveWatchlistId] = useState<number | null>(null);
  const [detail, setDetail] = useState<WatchlistDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [newTicker, setNewTicker] = useState('');
  const [newWatchlistName, setNewWatchlistName] = useState('');
  const [creating, setCreating] = useState(false);
  const [sortCol, setSortCol] = useState<SortCol>('ticker');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [inlineError, setInlineError] = useState<string | null>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  function showError(msg: string) {
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    setInlineError(msg);
    errorTimerRef.current = setTimeout(() => setInlineError(null), 3000);
  }

  const loadDetail = useCallback(async (id: number) => {
    setLoadingDetail(true);
    try {
      const data = await api.get<WatchlistDetail>(`/api/v1/dashboard/watchlists/${id}`);
      setDetail(data);
    } catch {
      setDetail(null);
      showError('Failed to load watchlist');
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    if (watchlists.length > 0) {
      const first = watchlists[0]!.id;
      if (activeWatchlistId === null || !watchlists.some((w) => w.id === activeWatchlistId)) {
        setActiveWatchlistId(first);
        loadDetail(first);
      }
    } else {
      setActiveWatchlistId(null);
      setDetail(null);
    }
  }, [watchlists, activeWatchlistId, loadDetail]);

  const selectTab = (id: number) => {
    setActiveWatchlistId(id);
    loadDetail(id);
  };

  const handleAddTicker = async () => {
    if (!newTicker.trim() || activeWatchlistId === null) return;
    try {
      await api.post(`/api/v1/dashboard/watchlists/${activeWatchlistId}/items`, {
        ticker: newTicker.trim().toUpperCase(),
      });
      setInlineError(null);
      setNewTicker('');
      onRefresh();
      loadDetail(activeWatchlistId);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to add ticker');
    }
  };

  const handleRemoveItem = async (ticker: string) => {
    if (activeWatchlistId === null) return;
    try {
      await api.del(`/api/v1/dashboard/watchlists/${activeWatchlistId}/items/${ticker}`);
      setInlineError(null);
      onRefresh();
      loadDetail(activeWatchlistId);
    } catch {
      showError('Failed to remove ticker');
    }
  };

  const handleCreateWatchlist = async () => {
    if (!newWatchlistName.trim()) return;
    setCreating(true);
    try {
      await api.post('/api/v1/dashboard/watchlists', { name: newWatchlistName.trim() });
      setInlineError(null);
      setNewWatchlistName('');
      onRefresh();
    } catch {
      showError('Failed to create watchlist');
    }
    setCreating(false);
  };

  const handleDeleteWatchlist = async () => {
    if (activeWatchlistId === null) return;
    const name = watchlists.find((w) => w.id === activeWatchlistId)?.name ?? 'this watchlist';
    if (!window.confirm(`Delete "${name}" and all its tickers? This cannot be undone.`)) return;
    try {
      await api.del(`/api/v1/dashboard/watchlists/${activeWatchlistId}`);
      setInlineError(null);
      setActiveWatchlistId(null);
      setDetail(null);
      onRefresh();
    } catch {
      showError('Failed to delete watchlist');
    }
  };

  const handleSort = (col: SortCol) => {
    if (sortCol === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortCol(col);
      setSortDir(col === 'ticker' || col === 'name' ? 'asc' : 'desc');
    }
  };

  const arrow = (col: SortCol) => {
    if (sortCol !== col) return null;
    return <span className={s.sortArrow}>{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  };

  const sortedItems = useMemo(() => {
    if (!detail?.items) return [];
    const items = [...detail.items];
    items.sort((a, b) => {
      let aVal: string | number, bVal: string | number;
      switch (sortCol) {
        case 'ticker': aVal = a.ticker; bVal = b.ticker; break;
        case 'name': aVal = a.company_name ?? ''; bVal = b.company_name ?? ''; break;
        case 'price': aVal = a.current_price ?? 0; bVal = b.current_price ?? 0; break;
        case 'change': aVal = a.day_change_pct ?? 0; bVal = b.day_change_pct ?? 0; break;
        case 'pe': aVal = a.pe_ratio ?? 999; bVal = b.pe_ratio ?? 999; break;
        default: return 0;
      }
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return items;
  }, [detail?.items, sortCol, sortDir]);

  if (watchlists.length === 0) {
    return (
      <div className={s.widget}>
        <div className={s.header}>
          <span className={s.headerTitle}>Watchlists</span>
        </div>
        <div className={s.empty}>No watchlists yet</div>
        <div className={s.createRow}>
          <input
            className={s.addInput}
            placeholder="Watchlist name"
            value={newWatchlistName}
            onChange={(e) => setNewWatchlistName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreateWatchlist()}
          />
          <button
            className={s.addBtn}
            disabled={!newWatchlistName.trim() || creating}
            onClick={handleCreateWatchlist}
          >
            Create
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={s.widget}>
      <div className={s.header}>
        <span className={s.headerTitle}>Watchlists</span>
        <div className={s.headerActions}>
          <button className={s.actionBtn} onClick={() => setCreating((v) => !v)} title="New watchlist">+</button>
          <button className={s.actionBtn} onClick={handleDeleteWatchlist} title="Delete watchlist">&times;</button>
        </div>
      </div>

      {creating && (
        <div className={s.createRow}>
          <input
            className={s.addInput}
            placeholder="Watchlist name"
            value={newWatchlistName}
            onChange={(e) => setNewWatchlistName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateWatchlist();
              if (e.key === 'Escape') setCreating(false);
            }}
            autoFocus
          />
          <button
            className={s.addBtn}
            disabled={!newWatchlistName.trim()}
            onClick={handleCreateWatchlist}
          >
            Create
          </button>
        </div>
      )}

      <div className={s.tabBar}>
        {watchlists.map((wl) => (
          <button
            key={wl.id}
            className={`${s.tab} ${wl.id === activeWatchlistId ? s.tabActive : ''}`}
            onClick={() => selectTab(wl.id)}
          >
            {wl.name}
          </button>
        ))}
      </div>

      <div className={s.body}>
        {loadingDetail ? (
          <div className={s.loading}>Loading...</div>
        ) : sortedItems.length > 0 ? (
          <table className={s.table}>
            <thead>
              <tr>
                <th className={s.thSortable} onClick={() => handleSort('ticker')}>
                  Ticker{arrow('ticker')}
                </th>
                <th className={s.thSortable} onClick={() => handleSort('name')}>
                  Name{arrow('name')}
                </th>
                <th className={s.thRightSortable} onClick={() => handleSort('price')}>
                  Price{arrow('price')}
                </th>
                <th className={s.thRightSortable} onClick={() => handleSort('change')}>
                  Change %{arrow('change')}
                </th>
                <th className={s.thRightSortable} onClick={() => handleSort('pe')}>
                  P/E{arrow('pe')}
                </th>
                <th className={s.th} style={{ width: 20 }} />
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((item) => (
                <tr
                  key={item.ticker}
                  className={s.trHover}
                  onClick={() => navigationService.goToResearch(item.ticker)}
                  style={{ cursor: 'pointer' }}
                >
                  <td className={s.tdTicker}>{item.ticker}</td>
                  <td className={s.tdName}>{truncate(item.company_name, 20)}</td>
                  <td className={s.tdRight}>{fmtDollar(item.current_price)}</td>
                  <td className={s.tdRight} style={{ color: gainColor(item.day_change_pct) }}>
                    {fmtSignedPct(item.day_change_pct)}
                  </td>
                  <td className={s.tdRightMono}>
                    {item.pe_ratio != null ? item.pe_ratio.toFixed(1) : '--'}
                  </td>
                  <td className={s.td}>
                    <button
                      className={s.removeBtn}
                      onClick={(e) => { e.stopPropagation(); handleRemoveItem(item.ticker); }}
                      title="Remove"
                    >
                      &times;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className={s.empty}>No items in this watchlist</div>
        )}
      </div>

      {inlineError && <div className={s.inlineError}>{inlineError}</div>}

      <div className={s.addRow}>
        <input
          className={s.addInput}
          placeholder="Add ticker..."
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAddTicker()}
        />
        <button
          className={s.addBtn}
          disabled={!newTicker.trim()}
          onClick={handleAddTicker}
        >
          Add
        </button>
      </div>
    </div>
  );
}

function truncate(val: string | null, max: number): string {
  if (!val) return '--';
  return val.length > max ? val.slice(0, max) + '...' : val;
}
