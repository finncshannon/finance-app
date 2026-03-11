import type { CompanyProfile } from '../types';
import { fmtMillions, fmtPct, fmtDollar, gainColor } from '../types';
import styles from './FunctionGrid.module.css';

interface FunctionDef {
  id: string;
  code: string;
  label: string;
  description: string;
}

const FUNCTIONS: FunctionDef[] = [
  { id: 'chart', code: 'GP', label: 'Price Chart', description: 'Historical price, volume, moving averages' },
  { id: 'financials', code: 'FA', label: 'Financial Analysis', description: 'Income, balance sheet, cash flow' },
  { id: 'ratios', code: 'RV', label: 'Ratios & Valuation', description: 'Profitability, leverage, valuation multiples' },
  { id: 'filings', code: 'CACS', label: 'SEC Filings', description: '10-K, 10-Q, 8-K filings and sections' },
  { id: 'profile', code: 'DES', label: 'Description', description: 'Company overview, key stats, events' },
  { id: 'peers', code: 'COMP', label: 'Peer Comparison', description: 'Comparable companies and relative metrics' },
  { id: 'news', code: 'NEWS', label: 'News & Headlines', description: 'Top stories, company news, keyword search' },
  { id: 'market', code: 'MRKT', label: 'Market Performance', description: 'Index and sector performance overview' },
];

interface Props {
  ticker: string;
  profile: CompanyProfile | null;
  onSelectFunction: (id: string) => void;
}

export function FunctionGrid({ ticker, profile, onSelectFunction }: Props) {
  const quote = profile?.quote;

  return (
    <div className={styles.container}>
      {/* Terminal-style header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.ticker}>{ticker}</span>
          <span className={styles.exchange}>{profile?.exchange ?? ''}</span>
          <span className={styles.companyName}>{profile?.company_name ?? ''}</span>
        </div>
        <div className={styles.headerRight}>
          {profile?.sector && <span className={styles.tag}>{profile.sector}</span>}
          {profile?.industry && <span className={styles.tag}>{profile.industry}</span>}
        </div>
      </div>

      {/* Key metrics bar */}
      {quote && (
        <div className={styles.metricsBar}>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>Last</span>
            <span className={styles.metricValue}>${fmtDollar(quote.current_price)}</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>Chg</span>
            <span className={styles.metricValue} style={{ color: gainColor(quote.day_change) }}>
              {quote.day_change >= 0 ? '+' : ''}{fmtDollar(quote.day_change)}
            </span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>Chg %</span>
            <span className={styles.metricValue} style={{ color: gainColor(quote.day_change_pct) }}>
              {quote.day_change_pct >= 0 ? '+' : ''}{fmtPct(quote.day_change_pct)}
            </span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>Mkt Cap</span>
            <span className={styles.metricValue}>{fmtMillions(quote.market_cap)}</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>52W Hi</span>
            <span className={styles.metricValue}>${fmtDollar(quote.fifty_two_week_high)}</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>52W Lo</span>
            <span className={styles.metricValue}>${fmtDollar(quote.fifty_two_week_low)}</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>Vol</span>
            <span className={styles.metricValue}>{fmtMillions(quote.volume)}</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>Beta</span>
            <span className={styles.metricValue}>{quote.beta?.toFixed(2) ?? '--'}</span>
          </div>
        </div>
      )}

      {/* Function grid */}
      <div className={styles.grid}>
        {FUNCTIONS.map((fn) => (
          <button
            key={fn.id}
            className={styles.functionCard}
            onClick={() => onSelectFunction(fn.id)}
          >
            <div className={styles.fnCodeRow}>
              <span className={styles.fnCode}>{fn.code}</span>
              <span className={styles.fnArrow}>&raquo;</span>
            </div>
            <div className={styles.fnLabel}>{fn.label}</div>
            <div className={styles.fnDesc}>{fn.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
