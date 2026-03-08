import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import type { MonteCarloResult, SensitivityParameterDef } from '../../../types/models';
import styles from './MonteCarloPanel.module.css';

const ITERATION_OPTIONS = [1000, 5000, 10000, 25000, 50000];

function fmtPrice(v: number): string {
  return `$${v.toFixed(2)}`;
}

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function formatParamValue(value: number, format: string): string {
  const pctMatch = format.match(/\{:\.(\d+)%\}/);
  if (pctMatch) {
    const decimals = parseInt(pctMatch[1]!, 10);
    return `${(value * 100).toFixed(decimals)}%`;
  }
  const floatMatch = format.match(/\{:\.(\d+)f\}(.*)/);
  if (floatMatch) {
    const decimals = parseInt(floatMatch[1]!, 10);
    const suffix = floatMatch[2] ?? '';
    return `${value.toFixed(decimals)}${suffix}`;
  }
  if (format === 'percentage' || format === 'pct') return `${(value * 100).toFixed(1)}%`;
  return value.toFixed(2);
}

export function MonteCarloPanel() {
  const ticker = useModelStore((s) => s.activeTicker);
  const currentPrice = useModelStore((s) => s.output?.current_price ?? null);
  const sliderOverrides = useModelStore((s) => s.sliderOverrides);

  const [iterations, setIterations] = useState(10000);
  const [data, setData] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useSliders, setUseSliders] = useState(false);
  const [showParams, setShowParams] = useState(false);
  const [paramDefs, setParamDefs] = useState<SensitivityParameterDef[]>([]);

  const fetchMC = useCallback(
    (iters: number) => {
      if (!ticker) return;
      setLoading(true);
      setError(null);

      api
        .post<MonteCarloResult>(
          `/api/v1/model-builder/${ticker}/sensitivity/monte-carlo`,
          {
            iterations: iters,
            ...(useSliders && Object.keys(sliderOverrides).length > 0 ? { overrides: sliderOverrides } : {}),
          },
        )
        .then((result) => {
          setData(result);
          setLoading(false);
        })
        .catch((err: unknown) => {
          const msg =
            err instanceof Error ? err.message : 'Monte Carlo simulation failed';
          setError(msg);
          setLoading(false);
        });
    },
    [ticker, useSliders, sliderOverrides],
  );

  // Auto-run on mount / ticker change
  useEffect(() => {
    if (ticker) {
      fetchMC(iterations);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  // Fetch parameter definitions for collapsible table
  useEffect(() => {
    if (!ticker) return;
    api.get<SensitivityParameterDef[]>(`/api/v1/model-builder/${ticker}/sensitivity/parameters`)
      .then(setParamDefs).catch(() => {});
  }, [ticker]);

  const handleRun = useCallback(() => {
    fetchMC(iterations);
  }, [fetchMC, iterations]);

  // Histogram chart data
  const histogramData = useMemo(() => {
    if (!data?.histogram) return [];
    return data.histogram.bins.map((bin) => ({
      label: `$${((bin.bin_start + bin.bin_end) / 2).toFixed(0)}`,
      binMid: (bin.bin_start + bin.bin_end) / 2,
      count: bin.count,
      frequency: bin.frequency,
      binStart: bin.bin_start,
      binEnd: bin.bin_end,
    }));
  }, [data]);

  if (!ticker) return null;

  const stats = data?.statistics ?? null;

  return (
    <div className={styles.container}>
      {/* Header with iteration control */}
      <div className={styles.header}>
        <span className={styles.title}>Monte Carlo Simulation</span>
        <div className={styles.iterationControl}>
          <span className={styles.iterationLabel}>Iterations:</span>
          <select
            className={styles.iterationSelect}
            value={iterations}
            onChange={(e) => setIterations(Number(e.target.value))}
          >
            {ITERATION_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n.toLocaleString()}
              </option>
            ))}
          </select>
          <label className={styles.sliderToggle}>
            <input type="checkbox" checked={useSliders} onChange={(e) => setUseSliders(e.target.checked)} />
            <span>Use slider assumptions</span>
          </label>
          <button
            className={styles.runBtn}
            onClick={handleRun}
            disabled={loading}
          >
            {loading ? 'Running...' : 'Run'}
          </button>
        </div>
      </div>

      {/* Collapsible parameter definitions */}
      <button className={styles.paramToggle} onClick={() => setShowParams(!showParams)}>
        {showParams ? '\u25BE' : '\u25B8'} Simulation Parameters
      </button>
      {showParams && paramDefs.length > 0 && (
        <div className={styles.paramTable}>
          <div className={styles.paramHeader}><span>Variable</span><span>Base</span><span>Range</span></div>
          {paramDefs.map((p) => (
            <div key={p.key_path} className={styles.paramRow}>
              <span>{p.name}</span>
              <span>{formatParamValue(p.current_value ?? 0, p.display_format)}</span>
              <span>{formatParamValue(p.min_val, p.display_format)} – {formatParamValue(p.max_val, p.display_format)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className={styles.loadingContainer}>
          <LoadingSpinner />
          <span className={styles.loadingText}>
            Running {iterations.toLocaleString()} iterations...
          </span>
        </div>
      )}

      {/* Error state */}
      {error && !loading && <div className={styles.error}>{error}</div>}

      {/* Data display */}
      {data && !loading && !error && (
        <>
          {!data.success && data.error && (
            <div className={styles.error}>{data.error}</div>
          )}

          {data.success && (
            <div className={styles.content}>
              {/* Histogram */}
              <div className={styles.histogramWrapper}>
                <span className={styles.histogramTitle}>
                  Distribution of Implied Prices
                </span>
                <div className={styles.chartContainer}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={histogramData}
                      margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                      style={{ background: 'transparent' }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#262626"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: '#A3A3A3', fontSize: 10 }}
                        stroke="#333"
                        interval="preserveStartEnd"
                        angle={-45}
                        textAnchor="end"
                        height={50}
                      />
                      <YAxis
                        tick={{ fill: '#A3A3A3', fontSize: 11 }}
                        stroke="#333"
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--bg-tertiary)',
                          border: '1px solid var(--border-medium)',
                          borderRadius: 4,
                        }}
                        labelStyle={{ color: 'var(--text-primary)' }}
                        formatter={(value: number | undefined) => [
                          value ?? 0,
                          'Count',
                        ]}
                        labelFormatter={(label: unknown) => `Price: ${String(label)}`}
                      />
                      {currentPrice != null && (
                        <ReferenceLine
                          x={
                            // find closest bin label to current price
                            histogramData.reduce(
                              (closest, d) =>
                                Math.abs(d.binMid - (currentPrice ?? 0)) <
                                Math.abs(closest.binMid - (currentPrice ?? 0))
                                  ? d
                                  : closest,
                              histogramData[0]!,
                            ).label
                          }
                          stroke="#F5F5F5"
                          strokeDasharray="4 4"
                          strokeWidth={1}
                          label={{
                            value: 'Current',
                            position: 'top',
                            fill: '#A3A3A3',
                            fontSize: 10,
                          }}
                        />
                      )}
                      {stats && histogramData.length > 0 && (
                        <ReferenceLine
                          x={
                            histogramData.reduce(
                              (closest, d) =>
                                Math.abs(d.binMid - stats.median) <
                                Math.abs(closest.binMid - stats.median)
                                  ? d
                                  : closest,
                              histogramData[0]!,
                            ).label
                          }
                          stroke="#F59E0B"
                          strokeDasharray="4 4"
                          strokeWidth={1}
                          label={{
                            value: `Median: $${stats.median.toFixed(2)}`,
                            position: 'top',
                            fill: '#F59E0B',
                            fontSize: 10,
                          }}
                        />
                      )}
                      <Bar dataKey="count" barSize={undefined}>
                        {histogramData.map((entry, index) => (
                          <Cell
                            key={`bin-${index}`}
                            fill={
                              currentPrice != null &&
                              entry.binMid >= currentPrice
                                ? '#22C55E'
                                : '#EF4444'
                            }
                            fillOpacity={0.85}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Statistics panel */}
              <div className={styles.statsPanel}>
                <span className={styles.statsTitle}>Central Tendency</span>

                {stats && (
                  <>
                    <div className={styles.statsGrid}>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Mean</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.mean)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Median</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.median)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Std Dev</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.std_dev)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>VaR 5%</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.var_5pct)}
                        </span>
                      </div>
                    </div>

                    <div className={styles.statsDivider} />
                    <span className={styles.statsTitle}>Distribution</span>

                    <div className={styles.statsGrid}>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>P5</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.p5)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>P25</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.p25)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>P50</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.p50)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>P75</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.p75)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>P90</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.p90)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>P95</span>
                        <span className={styles.statValue}>
                          {fmtPrice(stats.p95)}
                        </span>
                      </div>
                    </div>

                    <div className={styles.statsDivider} />
                    <span className={styles.statsTitle}>Risk Assessment</span>

                    <div className={styles.statsGrid}>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Prob Upside</span>
                        <span
                          className={`${styles.statValue} ${
                            stats.prob_upside > 0.5
                              ? styles.statValuePositive
                              : styles.statValueNegative
                          }`}
                        >
                          {fmtPct(stats.prob_upside)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Upside 15%+</span>
                        <span className={styles.statValue}>
                          {fmtPct(stats.prob_upside_15pct)}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Downside 15%+</span>
                        <span
                          className={`${styles.statValue} ${styles.statValueNegative}`}
                        >
                          {fmtPct(stats.prob_downside_15pct)}
                        </span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Footer: iteration counts + timing */}
          <div className={styles.footer}>
            <span className={styles.footerItem}>
              Valid:{' '}
              <span className={styles.footerValue}>
                {data.valid_iterations.toLocaleString()}
              </span>{' '}
              / {data.iteration_count.toLocaleString()}
            </span>
            {data.skipped_iterations > 0 && (
              <span className={styles.footerItem}>
                Skipped:{' '}
                <span className={styles.footerValue}>
                  {data.skipped_iterations.toLocaleString()}
                </span>
              </span>
            )}
            <span className={styles.footerItem}>
              Time:{' '}
              <span className={styles.footerValue}>
                {data.computation_time_ms.toFixed(0)}ms
              </span>
            </span>
            {data.seed != null && (
              <span className={styles.footerItem}>
                Seed: <span className={styles.footerValue}>{data.seed}</span>
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
