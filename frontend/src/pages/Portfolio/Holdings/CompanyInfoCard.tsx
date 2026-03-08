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
}

interface QuickInfo {
  ticker: string;
  company_name?: string;
  sector?: string;
  industry?: string;
  current_price?: number;
  market_cap?: number;
  pe_trailing?: number;
  ev_to_ebitda?: number;
  revenue_growth?: number;
  operating_margin?: number;
  dividend_yield?: number;
  beta?: number;
  fifty_two_week_low?: number;
  fifty_two_week_high?: number;
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

export function CompanyInfoCard({ ticker, x, y, onClose }: CompanyInfoCardProps) {
  const [info, setInfo] = useState<QuickInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const cardRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x, y });
  const isHovering = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    // Try quote endpoint for quick data
    api.get<Record<string, unknown>>(`/api/v1/market-data/quote/${ticker}`)
      .then((data) => {
        if (cancelled) return;
        setInfo({
          ticker,
          company_name: data.company_name as string | undefined,
          sector: data.sector as string | undefined,
          industry: data.industry as string | undefined,
          current_price: data.current_price as number | undefined,
          market_cap: data.market_cap as number | undefined,
          pe_trailing: data.pe_trailing as number | undefined,
          ev_to_ebitda: data.ev_to_ebitda as number | undefined,
          revenue_growth: data.revenue_growth as number | undefined,
          operating_margin: data.operating_margin as number | undefined,
          dividend_yield: data.dividend_yield as number | undefined,
          beta: data.beta as number | undefined,
          fifty_two_week_low: data.fifty_two_week_low as number | undefined,
          fifty_two_week_high: data.fifty_two_week_high as number | undefined,
        });
      })
      .catch(() => {
        if (!cancelled) setInfo({ ticker });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
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
    isHovering.current = true;
  };

  const handleMouseLeave = () => {
    isHovering.current = false;
    setTimeout(() => {
      if (!isHovering.current) onClose();
    }, 200);
  };

  const handleOpenResearch = () => {
    navigationService.goToResearch(ticker);
    onClose();
  };

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
              <span className={styles.metricLabel}>Rev Growth</span>
              <span className={styles.metricValue}>{fmtPct(info.revenue_growth)}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Op Margin</span>
              <span className={styles.metricValue}>{fmtPct(info.operating_margin)}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Div Yield</span>
              <span className={styles.metricValue}>{fmtPct(info.dividend_yield)}</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Beta</span>
              <span className={styles.metricValue}>
                {info.beta != null ? info.beta.toFixed(2) : '—'}
              </span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>52W Range</span>
              <span className={styles.metricValue}>
                {info.fifty_two_week_low != null && info.fifty_two_week_high != null
                  ? `${fmtDollar(info.fifty_two_week_low)} – ${fmtDollar(info.fifty_two_week_high)}`
                  : '—'}
              </span>
            </div>
          </div>

          <button className={styles.researchLink} onClick={handleOpenResearch}>
            Open in Research &rarr;
          </button>
        </>
      ) : null}
    </div>
  );
}
