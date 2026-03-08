import { useState, useEffect, useCallback, useRef } from 'react';
import { navigationService } from '../../../services/navigationService';
import { WatchlistPicker } from '../../../components/ui/WatchlistPicker/WatchlistPicker';
import styles from './ContextMenu.module.css';

interface ContextMenuProps {
  x: number;
  y: number;
  ticker: string;
  onClose: () => void;
}

export function ContextMenu({ x, y, ticker, onClose }: ContextMenuProps) {
  const [showWatchlistPicker, setShowWatchlistPicker] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const [adjustedPos, setAdjustedPos] = useState({ x, y });

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Viewport boundary detection
  useEffect(() => {
    if (!menuRef.current) return;
    const rect = menuRef.current.getBoundingClientRect();
    let newX = x;
    let newY = y;
    if (y + rect.height > window.innerHeight) {
      newY = y - rect.height;
    }
    if (x + rect.width > window.innerWidth) {
      newX = x - rect.width;
    }
    if (newX < 0) newX = 0;
    if (newY < 0) newY = 0;
    setAdjustedPos({ x: newX, y: newY });
  }, [x, y]);

  const handleOpenModelBuilder = () => {
    navigationService.goToModelBuilder(ticker);
    onClose();
  };

  const handleOpenResearch = () => {
    navigationService.goToResearch(ticker);
    onClose();
  };

  const handleCopyTicker = () => {
    navigator.clipboard.writeText(ticker);
    onClose();
  };

  return (
    <>
      <div className={styles.overlay} onClick={onClose} />
      <div ref={menuRef} className={styles.menu} style={{ left: adjustedPos.x, top: adjustedPos.y }}>
        <button className={styles.item} onClick={handleOpenModelBuilder}>
          Open in Model Builder
        </button>
        <button className={styles.item} onClick={handleOpenResearch}>
          Open in Research
        </button>
        <button className={styles.item} onClick={() => setShowWatchlistPicker(true)}>
          Add to Watchlist
        </button>
        <div className={styles.separator} />
        <button className={styles.item} onClick={handleCopyTicker}>
          Copy Ticker
        </button>
      </div>
      {showWatchlistPicker && (
        <WatchlistPicker
          ticker={ticker}
          open={showWatchlistPicker}
          onClose={() => { setShowWatchlistPicker(false); onClose(); }}
        />
      )}
    </>
  );
}
