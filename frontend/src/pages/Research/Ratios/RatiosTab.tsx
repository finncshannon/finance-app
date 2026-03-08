import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import type { RatioData } from '../types';
import { RATIO_CATEGORIES } from './ratioConfig';
import { RatioPanel } from './RatioPanel';
import { RatioTrendChart } from './RatioTrendChart';
import { DuPontDecomposition } from './DuPontDecomposition';
import styles from './RatiosTab.module.css';

interface RatiosTabProps {
  ticker: string;
}

export function RatiosTab({ ticker }: RatiosTabProps) {
  const [ratios, setRatios] = useState<RatioData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await api.get<RatioData>(`/api/v1/research/${ticker}/ratios`);
        if (!cancelled) setRatios(data);
      } catch {
        if (!cancelled) setRatios(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [ticker]);

  if (loading) {
    return <div className={styles.loading ?? ''}>Loading ratios...</div>;
  }

  if (!ratios) {
    return <div className={styles.loading ?? ''}>No ratio data available</div>;
  }

  // Map category id -> values from ratios response
  const getValues = (catId: string): Record<string, number | null> => {
    return (ratios as unknown as Record<string, Record<string, number | null>>)[catId] ?? {};
  };

  const netMargin = ratios.profitability?.net_margin ?? null;
  const assetTurnover = ratios.efficiency?.asset_turnover ?? null;

  return (
    <div className={styles.container ?? ''}>
      <div className={styles.grid ?? ''}>
        {RATIO_CATEGORIES.map((cat) => (
          <RatioPanel key={cat.id} category={cat} values={getValues(cat.id)} />
        ))}
      </div>
      <RatioTrendChart ticker={ticker} />
      <DuPontDecomposition ticker={ticker} netMargin={netMargin} assetTurnover={assetTurnover} />
    </div>
  );
}
