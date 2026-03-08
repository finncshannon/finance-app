import type { CompanyProfile } from '../types';
import { fmtMillions, fmtPct, fmtDollar, fmtNumber } from '../types';
import styles from './KeyStatsCard.module.css';

interface KeyStatsCardProps {
  profile: CompanyProfile;
}

interface StatItem {
  label: string;
  value: string;
}

export function KeyStatsCard({ profile }: KeyStatsCardProps) {
  const quote = profile.quote;
  const metrics = profile.metrics;

  if (!quote) return null;

  const stats: StatItem[] = [
    {
      label: 'Market Cap',
      value: '$' + fmtMillions(quote.market_cap),
    },
    {
      label: 'Enterprise Value',
      value: metrics?.enterprise_value != null
        ? '$' + fmtMillions(metrics.enterprise_value)
        : '--',
    },
    {
      label: 'Shares Outstanding',
      value: metrics?.shares_outstanding != null
        ? fmtNumber(metrics.shares_outstanding)
        : '--',
    },
    {
      label: 'Avg Volume',
      value: fmtMillions(quote.volume),
    },
    {
      label: '52W High',
      value: '$' + fmtDollar(quote.fifty_two_week_high),
    },
    {
      label: '52W Low',
      value: '$' + fmtDollar(quote.fifty_two_week_low),
    },
    {
      label: 'Beta',
      value: quote.beta != null ? quote.beta.toFixed(2) : '--',
    },
    {
      label: 'Dividend Yield',
      value: metrics?.dividend_yield != null
        ? fmtPct(metrics.dividend_yield)
        : '--',
    },
    {
      label: 'P/E (TTM)',
      value: metrics?.pe_ratio != null
        ? metrics.pe_ratio.toFixed(1) + 'x'
        : '--',
    },
    {
      label: 'P/E (Forward)',
      value: metrics?.pe_forward != null
        ? metrics.pe_forward.toFixed(1) + 'x'
        : '--',
    },
  ];

  return (
    <div className={styles.card ?? ''}>
      <h3 className={styles.title ?? ''}>Key Statistics</h3>
      <div className={styles.grid ?? ''}>
        {stats.map((stat) => (
          <div key={stat.label} className={styles.statCell ?? ''}>
            <span className={styles.statLabel ?? ''}>{stat.label}</span>
            <span className={styles.statValue ?? ''}>{stat.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
