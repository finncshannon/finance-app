import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import type { PerformanceResult, BenchmarkResult, AttributionResult } from '../types';
import { ReturnMetrics } from './ReturnMetrics';
import { BenchmarkChart } from './BenchmarkChart';
import { RiskMetrics } from './RiskMetrics';
import { AttributionTable } from './AttributionTable';
import styles from './PerformanceTab.module.css';

const PERIODS = ['1D', '3D', '5D', '2W', '1M', '3M', '6M', 'YTD', '1Y', '3Y', 'ALL'] as const;
type Period = (typeof PERIODS)[number];

interface Props {
  selectedAccount: string;
}

export function PerformanceTab({ selectedAccount }: Props) {
  const [period, setPeriod] = useState<Period>('1Y');
  const [performance, setPerformance] = useState<PerformanceResult | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const acct = selectedAccount ? `&account=${selectedAccount}` : '';
      const [perfData, benchData, attrData] = await Promise.all([
        api.get<PerformanceResult>(`/api/v1/portfolio/performance?period=${period}${acct}`),
        api.get<BenchmarkResult>(`/api/v1/portfolio/benchmark?benchmark=SPY&period=${period}${acct}`),
        api.get<AttributionResult>(`/api/v1/portfolio/attribution?benchmark=SPY&period=${period}${acct}`),
      ]);
      setPerformance(perfData);
      setBenchmark(benchData);
      setAttribution(attrData);
    } catch {
      // Silently handle — components show empty state
    } finally {
      setLoading(false);
    }
  }, [period, selectedAccount]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className={styles.container}>
      <div className={styles.periodBar}>
        {PERIODS.map((p) => (
          <button
            key={p}
            className={`${styles.pill} ${p === period ? styles.pillActive : ''}`}
            onClick={() => setPeriod(p)}
          >
            {p}
          </button>
        ))}
      </div>

      {loading ? (
        <div className={styles.loading}>Loading performance data...</div>
      ) : (
        <>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Return Metrics</h3>
            <ReturnMetrics performance={performance} />
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Benchmark Comparison</h3>
            <BenchmarkChart benchmark={benchmark} />
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Risk Metrics</h3>
            <RiskMetrics performance={performance} />
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Performance Attribution</h3>
            <AttributionTable attribution={attribution} />
          </div>
        </>
      )}
    </div>
  );
}
