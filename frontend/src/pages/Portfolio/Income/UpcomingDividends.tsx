import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import type { UpcomingDividendEvent } from '../types';
import { fmtDollar } from '../types';
import styles from './UpcomingDividends.module.css';

interface Props {
  selectedAccount: string;
}

interface UpcomingResponse {
  upcoming: UpcomingDividendEvent[];
  message?: string;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function UpcomingDividends({ selectedAccount }: Props) {
  const [data, setData] = useState<UpcomingResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const accountParam = selectedAccount && selectedAccount !== 'all'
      ? `?account=${encodeURIComponent(selectedAccount)}`
      : '';

    api.get<UpcomingResponse>(`/api/v1/portfolio/income/upcoming-dividends${accountParam}`)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setData({ upcoming: [], message: 'Could not fetch events' });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedAccount]);

  if (loading) {
    return <div className={styles.loading}>Loading...</div>;
  }

  if (!data) return null;

  // Phase 7 fallback
  if (data.message === 'Events system not available') {
    return (
      <div className={styles.placeholder}>
        Enable events to see upcoming dividends.
      </div>
    );
  }

  if (data.upcoming.length === 0) {
    return (
      <div className={styles.empty}>
        {data.message || 'No upcoming dividend events found.'}
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {data.upcoming.map((event, i) => (
        <div key={i} className={styles.row}>
          <span className={styles.date}>{formatDate(event.event_date)}</span>
          <span className={styles.ticker}>{event.ticker}</span>
          <span className={styles.perShare}>
            {event.amount_per_share != null ? `${fmtDollar(event.amount_per_share)}/sh` : '—'}
          </span>
          <span className={styles.shares}>{event.shares_held} shares</span>
          <span className={styles.income}>
            {event.expected_income != null ? fmtDollar(event.expected_income) : '—'}
          </span>
        </div>
      ))}
    </div>
  );
}
