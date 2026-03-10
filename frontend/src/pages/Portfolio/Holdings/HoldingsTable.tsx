import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../../../services/api';
import { navigationService } from '../../../services/navigationService';
import type { Position } from '../types';
import { fmtDollar, fmtSignedDollar, fmtPct, fmtShares, gainColor } from '../types';
import { PositionDetail } from './PositionDetail';
import { CompanyInfoCard } from './CompanyInfoCard';
import { EditPositionModal } from './EditPositionModal';
import styles from './HoldingsTable.module.css';

// ─── Column Definition ──────────────────────────────
type SortKey =
  | 'ticker' | 'company_name' | 'shares_held' | 'cost_basis_per_share'
  | 'current_price' | 'market_value' | 'total_cost' | 'gain_loss'
  | 'gain_loss_pct' | 'weight' | 'day_change' | 'implied_value' | 'model_upside';

interface ImpliedPrice {
  ticker: string;
  model_type: string;
  intrinsic_value: number;
  run_timestamp: string;
}

type GroupBy = 'none' | 'account' | 'sector' | 'industry';

interface ContextMenu {
  x: number;
  y: number;
  position: Position;
}

interface Props {
  positions: Position[];
  expandedId: number | null;
  onExpand: (id: number | null) => void;
  onRecordTx: (ticker: string) => void;
  onRefresh: () => void;
}

// ─── Helpers ────────────────────────────────────────
function compareValues(a: unknown, b: unknown, dir: 'asc' | 'desc'): number {
  const valA = a ?? -Infinity;
  const valB = b ?? -Infinity;
  if (typeof valA === 'string' && typeof valB === 'string') {
    const cmp = valA.localeCompare(valB);
    return dir === 'asc' ? cmp : -cmp;
  }
  const cmp = (valA as number) - (valB as number);
  return dir === 'asc' ? cmp : -cmp;
}

function groupPositions(positions: Position[], groupBy: GroupBy): Map<string, Position[]> {
  if (groupBy === 'none') return new Map([['', positions]]);
  const map = new Map<string, Position[]>();
  for (const p of positions) {
    let key: string;
    switch (groupBy) {
      case 'account': key = p.account ?? 'Unknown'; break;
      case 'sector': key = p.sector ?? 'Unknown'; break;
      case 'industry': key = p.industry ?? 'Unknown'; break;
    }
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(p);
  }
  return map;
}

// ─── Component ──────────────────────────────────────
export function HoldingsTable({ positions, expandedId, onExpand, onRecordTx, onRefresh }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('market_value');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [groupBy, setGroupBy] = useState<GroupBy>('none');
  const [ctxMenu, setCtxMenu] = useState<ContextMenu | null>(null);
  const [impliedPrices, setImpliedPrices] = useState<Map<string, ImpliedPrice>>(new Map());
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);
  const [hoverCard, setHoverCard] = useState<{ ticker: string; x: number; y: number } | null>(null);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const hoverCloseRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const ctxMenuRef = useRef<HTMLDivElement>(null);
  const [ctxMenuAdjusted, setCtxMenuAdjusted] = useState<{ x: number; y: number } | null>(null);

  // Load implied prices from models
  useEffect(() => {
    api.get<{ implied_prices: ImpliedPrice[] }>('/api/v1/portfolio/implied-prices')
      .then((d) => {
        const map = new Map<string, ImpliedPrice>();
        for (const ip of d.implied_prices) map.set(ip.ticker, ip);
        setImpliedPrices(map);
      })
      .catch(() => setImpliedPrices(new Map()));
  }, [positions]);

  // Close context menu on click-away
  useEffect(() => {
    if (!ctxMenu) return;
    const handler = () => setCtxMenu(null);
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [ctxMenu]);

  // Context menu viewport boundary detection
  useEffect(() => {
    if (!ctxMenu || !ctxMenuRef.current) {
      setCtxMenuAdjusted(null);
      return;
    }
    const rect = ctxMenuRef.current.getBoundingClientRect();
    let newX = ctxMenu.x;
    let newY = ctxMenu.y;
    if (newY + rect.height > window.innerHeight) {
      newY = ctxMenu.y - rect.height;
    }
    if (newX + rect.width > window.innerWidth) {
      newX = ctxMenu.x - rect.width;
    }
    if (newX < 0) newX = 0;
    if (newY < 0) newY = 0;
    setCtxMenuAdjusted({ x: newX, y: newY });
  }, [ctxMenu]);

  // Sort positions
  const sorted = useMemo(() => {
    const clone = [...positions];
    clone.sort((a, b) => {
      if (sortKey === 'implied_value') {
        const aIp = impliedPrices.get(a.ticker)?.intrinsic_value ?? -Infinity;
        const bIp = impliedPrices.get(b.ticker)?.intrinsic_value ?? -Infinity;
        return compareValues(aIp, bIp, sortDir);
      }
      if (sortKey === 'model_upside') {
        const aUp = (() => { const ip = impliedPrices.get(a.ticker); return ip && a.current_price ? (ip.intrinsic_value - a.current_price) / a.current_price : -Infinity; })();
        const bUp = (() => { const ip = impliedPrices.get(b.ticker); return ip && b.current_price ? (ip.intrinsic_value - b.current_price) / b.current_price : -Infinity; })();
        return compareValues(aUp, bUp, sortDir);
      }
      return compareValues(a[sortKey], b[sortKey], sortDir);
    });
    return clone;
  }, [positions, sortKey, sortDir, impliedPrices]);

  // Group them
  const groups = useMemo(() => groupPositions(sorted, groupBy), [sorted, groupBy]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'ticker' || key === 'company_name' ? 'asc' : 'desc');
    }
  };

  const handleRowClick = (id: number) => {
    onExpand(id);
  };

  const handleRowDoubleClick = (ticker: string) => {
    navigationService.goToModelBuilder(ticker);
  };

  const handleContextMenu = useCallback((e: React.MouseEvent, position: Position) => {
    e.preventDefault();
    setCtxMenu({ x: e.clientX, y: e.clientY, position });
  }, []);

  const handleRemove = async (pos: Position) => {
    setCtxMenu(null);
    try {
      await api.del(`/api/v1/portfolio/positions/${pos.id}`);
      onRefresh();
    } catch {
      // Silently fail
    }
  };

  const handleEditPosition = useCallback((pos: Position) => {
    setEditingPosition(pos);
  }, []);

  // Hover card handlers
  const handleTickerMouseEnter = (ticker: string, e: React.MouseEvent) => {
    clearTimeout(hoverCloseRef.current);
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    hoverTimerRef.current = setTimeout(() => {
      setHoverCard({ ticker, x: rect.right + 8, y: rect.top });
    }, 500);
  };

  const handleTickerMouseLeave = () => {
    clearTimeout(hoverTimerRef.current);
    hoverCloseRef.current = setTimeout(() => {
      setHoverCard(null);
    }, 300);
  };

  const handleCardMouseEnter = () => {
    clearTimeout(hoverCloseRef.current);
  };

  // Arrow indicator
  const arrow = (key: SortKey) => {
    if (sortKey !== key) return null;
    return <span className={styles.sortArrow}>{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  };

  // Totals
  const totals = useMemo(() => {
    let totalValue = 0;
    let totalCost = 0;
    let totalGain = 0;
    let totalDayChg = 0;
    for (const p of positions) {
      totalValue += p.market_value ?? 0;
      totalCost += p.total_cost ?? 0;
      totalGain += p.gain_loss ?? 0;
      totalDayChg += p.day_change ?? 0;
    }
    return { totalValue, totalCost, totalGain, totalDayChg };
  }, [positions]);

  let rowIndex = 0;

  return (
    <div className={styles.wrapper}>
      {/* Toolbar */}
      <div className={styles.toolbar}>
        <span className={styles.groupLabel}>Group by</span>
        <select
          className={styles.groupSelect}
          value={groupBy}
          onChange={(e) => setGroupBy(e.target.value as GroupBy)}
        >
          <option value="none">None</option>
          <option value="account">Account</option>
          <option value="sector">Sector</option>
          <option value="industry">Industry</option>
        </select>
      </div>

      {/* Table */}
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th} onClick={() => handleSort('ticker')}>
              Ticker{arrow('ticker')}
            </th>
            <th className={styles.th} onClick={() => handleSort('company_name')}>
              Name{arrow('company_name')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('shares_held')}>
              Shares{arrow('shares_held')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('cost_basis_per_share')}>
              Avg Cost{arrow('cost_basis_per_share')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('current_price')}>
              Mkt Price{arrow('current_price')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('market_value')}>
              Value{arrow('market_value')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('total_cost')}>
              Cost Basis{arrow('total_cost')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('gain_loss')}>
              Gain/Loss{arrow('gain_loss')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('gain_loss_pct')}>
              Gain %{arrow('gain_loss_pct')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('weight')}>
              Weight{arrow('weight')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('day_change')}>
              Day Chg{arrow('day_change')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('implied_value')}>
              Implied{arrow('implied_value')}
            </th>
            <th className={styles.thRight} onClick={() => handleSort('model_upside')}>
              Upside{arrow('model_upside')}
            </th>
          </tr>
        </thead>

        <tbody>
          {Array.from(groups.entries()).map(([groupName, groupPositions]) => {
            const rows: React.ReactNode[] = [];

            // Group header row
            if (groupBy !== 'none') {
              rows.push(
                <tr key={`group-${groupName}`} className={styles.groupRow}>
                  <td className={styles.groupCell} colSpan={13}>
                    {groupName} ({groupPositions.length})
                  </td>
                </tr>
              );
            }

            for (const pos of groupPositions) {
              const isExpanded = expandedId === pos.id;
              const rowClass = rowIndex % 2 === 0 ? styles.trEven : styles.trOdd;
              rowIndex++;

              rows.push(
                <tr
                  key={pos.id}
                  className={`${rowClass} ${isExpanded ? styles.trExpanded : ''}`}
                  onClick={() => handleRowClick(pos.id)}
                  onDoubleClick={() => handleRowDoubleClick(pos.ticker)}
                  onContextMenu={(e) => handleContextMenu(e, pos)}
                >
                  <td
                    className={styles.ticker}
                    onMouseEnter={(e) => handleTickerMouseEnter(pos.ticker, e)}
                    onMouseLeave={handleTickerMouseLeave}
                  >
                    {pos.ticker}
                  </td>
                  <td className={styles.name}>{pos.company_name ?? '—'}</td>
                  <td className={styles.tdRight}>{fmtShares(pos.shares_held)}</td>
                  <td className={styles.tdRight}>{fmtDollar(pos.cost_basis_per_share)}</td>
                  <td className={styles.tdRight}>{fmtDollar(pos.current_price)}</td>
                  <td className={styles.tdRight}>{fmtDollar(pos.market_value)}</td>
                  <td className={styles.tdRight}>{fmtDollar(pos.total_cost)}</td>
                  <td className={styles.tdRight} style={{ color: gainColor(pos.gain_loss) }}>
                    {fmtSignedDollar(pos.gain_loss)}
                  </td>
                  <td className={styles.tdRight} style={{ color: gainColor(pos.gain_loss_pct) }}>
                    {fmtPct(pos.gain_loss_pct)}
                  </td>
                  <td className={styles.tdRight}>
                    {pos.weight != null ? `${(pos.weight * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className={styles.tdRight} style={{ color: gainColor(pos.day_change) }}>
                    {fmtSignedDollar(pos.day_change)}
                  </td>
                  <td className={styles.tdRight}>
                    {impliedPrices.has(pos.ticker)
                      ? fmtDollar(impliedPrices.get(pos.ticker)!.intrinsic_value)
                      : '—'}
                  </td>
                  <td className={styles.tdRight}>
                    {(() => {
                      const ip = impliedPrices.get(pos.ticker);
                      if (!ip || !pos.current_price) return '—';
                      const upside = (ip.intrinsic_value - pos.current_price) / pos.current_price;
                      return (
                        <span style={{ color: gainColor(upside) }}>
                          {fmtPct(upside)}
                        </span>
                      );
                    })()}
                  </td>
                </tr>
              );

              // Expanded detail
              if (isExpanded) {
                rows.push(
                  <tr key={`detail-${pos.id}`} className={styles.detailRow}>
                    <td className={styles.detailCell} colSpan={13}>
                      <PositionDetail
                        position={pos}
                        onRecordTx={onRecordTx}
                        onEditPosition={handleEditPosition}
                      />
                    </td>
                  </tr>
                );
              }
            }

            return rows;
          })}
        </tbody>

        {/* Footer totals */}
        <tfoot>
          <tr>
            <td className={styles.td} colSpan={5} style={{ fontWeight: 600 }}>Total</td>
            <td className={styles.tdRight} style={{ fontWeight: 600 }}>
              {fmtDollar(totals.totalValue)}
            </td>
            <td className={styles.tdRight} style={{ fontWeight: 600 }}>
              {fmtDollar(totals.totalCost)}
            </td>
            <td className={styles.tdRight} style={{ fontWeight: 600, color: gainColor(totals.totalGain) }}>
              {fmtSignedDollar(totals.totalGain)}
            </td>
            <td className={styles.tdRight} style={{ fontWeight: 600, color: gainColor(totals.totalGain) }}>
              {totals.totalCost > 0
                ? fmtPct(totals.totalGain / totals.totalCost)
                : '—'}
            </td>
            <td className={styles.tdRight} style={{ fontWeight: 600 }}>100.0%</td>
            <td className={styles.tdRight} style={{ fontWeight: 600, color: gainColor(totals.totalDayChg) }}>
              {fmtSignedDollar(totals.totalDayChg)}
            </td>
            <td className={styles.tdRight} />
            <td className={styles.tdRight} />
          </tr>
        </tfoot>
      </table>

      {/* Context Menu */}
      {ctxMenu && (
        <div
          ref={ctxMenuRef}
          className={styles.contextMenu}
          style={{
            left: ctxMenuAdjusted?.x ?? ctxMenu.x,
            top: ctxMenuAdjusted?.y ?? ctxMenu.y,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className={styles.contextItem}
            onClick={() => { setCtxMenu(null); navigationService.goToModelBuilder(ctxMenu.position.ticker); }}
          >
            Open in Model Builder
          </button>
          <button
            className={styles.contextItem}
            onClick={() => { setCtxMenu(null); navigationService.goToResearch(ctxMenu.position.ticker); }}
          >
            Open in Research
          </button>
          <button
            className={styles.contextItem}
            onClick={() => { setCtxMenu(null); setHoverCard({ ticker: ctxMenu.position.ticker, x: ctxMenu.x, y: ctxMenu.y }); }}
          >
            Company Info
          </button>
          <button
            className={styles.contextItem}
            onClick={() => { setCtxMenu(null); onRecordTx(ctxMenu.position.ticker); }}
          >
            Record Transaction
          </button>
          <button
            className={styles.contextItem}
            onClick={() => { setCtxMenu(null); setEditingPosition(ctxMenu.position); }}
          >
            Edit Position
          </button>
          <button
            className={styles.contextItem}
            onClick={() => { setCtxMenu(null); onExpand(ctxMenu.position.id); }}
          >
            {expandedId === ctxMenu.position.id ? 'Collapse Details' : 'Expand Details'}
          </button>
          <button
            className={styles.contextDanger}
            onClick={() => handleRemove(ctxMenu.position)}
          >
            Remove Position
          </button>
        </div>
      )}

      {/* Hover Card */}
      {hoverCard && (
        <CompanyInfoCard
          ticker={hoverCard.ticker}
          x={hoverCard.x}
          y={hoverCard.y}
          onClose={() => setHoverCard(null)}
          onMouseEnterCard={handleCardMouseEnter}
        />
      )}

      {/* Edit Position Modal */}
      {editingPosition && (
        <EditPositionModal
          position={editingPosition}
          onClose={() => setEditingPosition(null)}
          onSuccess={() => { setEditingPosition(null); onRefresh(); }}
        />
      )}
    </div>
  );
}
