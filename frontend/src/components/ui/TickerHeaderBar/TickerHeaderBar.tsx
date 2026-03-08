import React from 'react';
import styles from './TickerHeaderBar.module.css';

interface TickerHeaderBarProps {
  ticker: string;
  companyName: string;
  sector?: string;
  industry?: string;
  exchange?: string;
  price: number;
  dayChange: number;
  dayChangePct: number;
  volume?: number;
  marketCap?: number;
  onNavigate?: (target: string) => void;
}

function formatCompact(value: number): string {
  if (value >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

export function TickerHeaderBar({
  ticker,
  companyName,
  sector,
  industry,
  exchange,
  price,
  dayChange,
  dayChangePct,
  volume,
  marketCap,
  onNavigate,
}: TickerHeaderBarProps) {
  const isPositive = dayChange >= 0;
  const changeColorClass = isPositive ? styles.positive : styles.negative;
  const arrow = isPositive ? '\u25B2' : '\u25BC';
  const sign = isPositive ? '+' : '';

  const tagParts = [sector, industry, exchange].filter(Boolean);

  return (
    <div className={styles.bar}>
      {/* Identity */}
      <div className={styles.identity}>
        <div className={styles.topRow}>
          <span className={styles.ticker}>{ticker}</span>
          <span className={styles.companyName}>{companyName}</span>
        </div>
        {tagParts.length > 0 && (
          <div className={styles.tags}>
            {tagParts.map((tag, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span className={styles.tagSeparator}>&middot;</span>}
                <span>{tag}</span>
              </React.Fragment>
            ))}
          </div>
        )}
      </div>

      <div className={styles.divider} />

      {/* Price */}
      <div className={styles.priceBlock}>
        <span className={styles.price}>{price.toFixed(2)}</span>
        <span className={`${styles.change} ${changeColorClass}`}>
          {arrow} {sign}{dayChange.toFixed(2)} ({sign}{dayChangePct.toFixed(2)}%)
        </span>
      </div>

      {/* Optional stats */}
      {(volume != null || marketCap != null) && (
        <>
          <div className={styles.divider} />
          <div className={styles.stats}>
            {volume != null && (
              <div className={styles.stat}>
                <span className={styles.statLabel}>Vol</span>
                <span className={styles.statValue}>{formatCompact(volume)}</span>
              </div>
            )}
            {marketCap != null && (
              <div className={styles.stat}>
                <span className={styles.statLabel}>Mkt Cap</span>
                <span className={styles.statValue}>{formatCompact(marketCap)}</span>
              </div>
            )}
          </div>
        </>
      )}

      <div className={styles.divider} />

      {/* Nav buttons */}
      <div className={styles.nav}>
        <button className={styles.navButton} onClick={() => onNavigate?.('model')}>
          Model
        </button>
        <button className={styles.navButton} onClick={() => onNavigate?.('research')}>
          Research
        </button>
        <button className={styles.navButton} onClick={() => onNavigate?.('watchlist')}>
          + Watchlist
        </button>
      </div>
    </div>
  );
}
