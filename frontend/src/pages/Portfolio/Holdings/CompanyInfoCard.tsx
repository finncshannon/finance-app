import { useState, useEffect, useRef } from 'react';
import { api } from '../../../services/api';
import { navigationService } from '../../../services/navigationService';
import { fmtDollar, fmtPct } from '../types';
import styles from './CompanyInfoCard.module.css';

interface CompanyInfoCardProps {
  ticker: string;
  x: number;
  y: number;
  onClose: () => void;
  onMouseEnterCard: () => void;
}

interface QuickInfo {
  ticker: string;
  company_name?: string;
  sector?: string;
  industry?: string;
  current_price?: number;
  day_change_pct?: number;
  market_cap?: number;
  pe_trailing?: number;
  ev_to_ebitda?: number;
  dividend_yield?: number;
  beta?: number;
  fifty_two_week_low?: number;
  fifty_two_week_high?: number;
  year_change_pct?: number;
}

function fmtMarketCap(n: number | null | undefined): string {
  if (n == null) return '—';
  if (n >= 1e12) return `$${(n / 1e12).toFixed(1)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return fmtDollar(n);
}

function fmtRatio(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toFixed(1) + 'x';
}

export function CompanyInfoCard({ ticker, x, y, onClose, onMouseEnterCard }: CompanyInfoCardProps) {
  const [info, setInfo] = useState<QuickInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const cardRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x, y });
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    // Fetch company info, quote, and 1Y historical in parallel
    const companyP = api.get<Record<string, unknown>>(`/api/v1/companies/${ticker}`).catch(() => null);
    const quoteP = api.get<Record<string, unknown>>(`/api/v1/companies/${ticker}/quote`).catch(() => null);
    const histP = api.get<Record<string, unknown>[]>(`/api/v1/companies/${ticker}/historical?period=1y&interval=1d`).catch(() => null);

    Promise.all([companyP, quoteP, histP]).then(([company, quote, hist]) => {
      if (cancelled) return;
      const curPrice = quote?.current_price as number | undefined;
      // Compute 1Y change from historical bars (last close vs first close)
      let yearChangePct: number | undefined;
      if (Array.isArray(hist) && hist.length > 1) {
        const firstClose = hist[0]?.close as number | undefined;
        const lastClose = hist[hist.length - 1]?.close as number | undefined;
        if (firstClose != null && firstClose > 0 && lastClose != null) {
          yearChangePct = (lastClose - firstClose) / firstClose;
        }
      }
      setInfo({
        ticker,
        company_name: (company?.company_name ?? quote?.company_name) as string | undefined,
        sector: company?.sector as string | undefined,
        industry: company?.industry as string | undefined,
        current_price: curPrice,
        day_change_pct: quote?.day_change_pct as number | undefined,
        market_cap: quote?.market_cap as number | undefined,
        pe_trailing: quote?.pe_trailing as number | undefined,
        ev_to_ebitda: quote?.ev_to_ebitda as number | undefined,
        dividend_yield: quote?.dividend_yield as number | undefined,
        beta: quote?.beta as number | undefined,
        fifty_two_week_low: quote?.fifty_two_week_low as number | undefined,
        fifty_two_week_high: quote?.fifty_two_week_high as number | undefined,
        year_change_pct: yearChangePct,
      });
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [ticker]);

  // Viewport boundary detection
  useEffect(() => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    let newX = x;
    let newY = y;
    if (y + rect.height > window.innerHeight) {
      newY = Math.max(0, y - rect.height);
    }
    if (x + rect.width > window.innerWidth) {
      newX = Math.max(0, x - rect.width - 16);
    }
    setPos({ x: newX, y: newY });
  }, [x, y, loading]);

  const handleMouseEnter = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    onMouseEnterCard();
  };

  const handleMouseLeave = () => {
    closeTimer.current = setTimeout(() => onClose(), 250);
  };

  const handleOpenResearch = () => {
    navigationService.goToResearch(ticker);
    onClose();
  };

  const priceColor = info?.day_change_pct != null
    ? info.day_change_pct >= 0 ? 'var(--color-positive)' : 'var(--color-negative)'
    : undefined;

  const yearColor = info?.year_change_pct != null
    ? info.year_change_pct >= 0 ? 'var(--color-positive)' : 'var(--color-negative)'
    : undefined;

  return (
    <div
      ref={cardRef}
      className={styles.card}
      style={{ left: pos.x, top: pos.y }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {loading ? (
        <div className={styles.loading}>Loading...</div>
      ) : info ? (
        <>
          <div className={styles.header}>
            <span className={styles.ticker}>{info.ticker}</span>
            {info.company_name && (
              <span className={styles.name}>{info.company_name}</span>
            )}
          </div>

          {(info.sector || info.industry) && (
            <div className={styles.meta}>
              {info.sector}{info.sector && info.industry ? ' · ' : ''}{info.industry}
            </div>
          )}

          {info.current_price != null && (
            <div className={styles.priceRow}>
              <span className={styles.price}>{fmtDollar(info.current_price)}</span>
              {info.day_change_pct != null && (
                <span style={{ color: priceColor, fontSize: 12 }}>
                  {info.day_change_pct >= 0 ? '+' : ''}{(info.day_change_pct * 100).toFixed(2)}%
                </span>
              )}
            </div>
          )}

          <div className={styles.grid}>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Mkt Cap</span>
              <span className={styles.metricValue}>{fmtMarketCap(info.market_cap)}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>P/E</span>
              <span className={styles.metricValue}>{fmtRatio(info.pe_trailing)}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>EV/EBITDA</span>
              <span className={styles.metricValue}>{fmtRatio(info.ev_to_ebitda)}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Div Yield</span>
              <span className={styles.metricValue}>{fmtPct(info.dividend_yield)}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>1Y Change</span>
              <span className={styles.metricValue} style={{ color: yearColor }}>
                {info.year_change_pct != null
                  ? `${info.year_change_pct >= 0 ? '+' : ''}${(info.year_change_pct * 100).toFixed(2)}%`
                  : '—'}
              </span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Beta</span>
              <span className={styles.metricValue}>
                {info.beta != null ? info.beta.toFixed(2) : '—'}
              </span>
            </div>
          </div>

          <div className={styles.metricWide}>
            <span className={styles.metricLabel}>52W Range</span>
            <span className={styles.metricValue}>
              {info.fifty_two_week_low != null && info.fifty_two_week_high != null
                ? `${fmtDollar(info.fifty_two_week_low)} – ${fmtDollar(info.fifty_two_week_high)}`
                : '—'}
            </span>
          </div>

          <button className={styles.researchLink} onClick={handleOpenResearch}>
            Open in Research &rarr;
          </button>
        </>
      ) : null}
    </div>
  );
}
