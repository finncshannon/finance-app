import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api } from '../../../services/api';
import { RATIO_CATEGORIES } from './ratioConfig';
import type { RatioMetricDef } from './ratioConfig';
import styles from './RatioTrendChart.module.css';

interface RatioTrendChartProps {
  ticker: string;
}

const LINE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#A78BFA', '#F472B6', '#06B6D4', '#EF4444', '#84CC16'];

const ALL_METRICS = RATIO_CATEGORIES.flatMap((c) => c.metrics);
const DEFAULT_KEYS = ['gross_margin', 'operating_margin', 'net_margin'];

/** Categories shown in the metric selector */
const SELECTOR_CATEGORIES = [
  { label: 'Profitability', metrics: ['gross_margin', 'operating_margin', 'net_margin', 'ebitda_margin'] },
  { label: 'Returns', metrics: ['roe', 'roa', 'roic'] },
  { label: 'Leverage', metrics: ['debt_to_equity', 'net_debt_to_ebitda'] },
  { label: 'Growth', metrics: ['revenue_growth_yoy', 'eps_growth_yoy'] },
  { label: 'Efficiency', metrics: ['asset_turnover', 'fcf_margin'] },
];

interface HistoryResponse {
  [metricKey: string]: Array<{ fiscal_year: number; value: number | null }>;
}

function formatForTooltip(val: number, key: string, lookup: Record<string, RatioMetricDef>): string {
  const def = lookup[key];
  if (!def) return val.toFixed(2);
  if (def.format === 'pct') return `${(val * 100).toFixed(1)}%`;
  return `${val.toFixed(2)}${def.suffix ?? 'x'}`;
}

export function RatioTrendChart({ ticker }: RatioTrendChartProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set(DEFAULT_KEYS));
  const [historyData, setHistoryData] = useState<HistoryResponse>({});

  const selectedArr = useMemo(() => Array.from(selected), [selected]);

  const metricLookup = useMemo(() => {
    const map: Record<string, RatioMetricDef> = {};
    for (const m of ALL_METRICS) map[m.key] = m;
    return map;
  }, []);

  const fetchHistory = useCallback(async () => {
    if (selectedArr.length === 0) { setHistoryData({}); return; }
    const params = selectedArr.map((m) => `metric=${m}`).join('&');
    try {
      const data = await api.get<HistoryResponse>(
        `/api/v1/research/${ticker}/ratios/history?${params}&years=10`,
      );
      setHistoryData(data);
    } catch {
      setHistoryData({});
    }
  }, [ticker, selectedArr]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Build chart data: merge all selected metrics by fiscal_year
  const chartData = useMemo(() => {
    const yearMap: Record<number, Record<string, number | null>> = {};
    for (const key of selectedArr) {
      const pts = historyData[key] ?? [];
      for (const pt of pts) {
        if (!yearMap[pt.fiscal_year]) yearMap[pt.fiscal_year] = {};
        yearMap[pt.fiscal_year]![key] = pt.value;
      }
    }
    return Object.entries(yearMap)
      .map(([yr, vals]) => ({ fiscal_year: Number(yr), ...vals }))
      .sort((a, b) => a.fiscal_year - b.fiscal_year);
  }, [historyData, selectedArr]);

  // Determine axis configuration
  const hasPercent = selectedArr.some((k) => metricLookup[k]?.format === 'pct');
  const hasRatio = selectedArr.some((k) => metricLookup[k]?.format !== 'pct');
  const useDualAxis = hasPercent && hasRatio;

  // Dynamic chart title
  const chartTitle = useMemo(() => {
    const activeCategories = SELECTOR_CATEGORIES
      .filter((cat) => cat.metrics.some((m) => selected.has(m)))
      .map((cat) => cat.label);
    if (activeCategories.length === 0) return 'Trend Analysis (10Y)';
    if (activeCategories.length === 1) return `${activeCategories[0]} Trends (10Y)`;
    if (activeCategories.length === 2) return `${activeCategories[0]} vs ${activeCategories[1]} (10Y)`;
    return 'Multi-Category Trends (10Y)';
  }, [selected]);

  // Color map for selected metrics
  const colorMap = useMemo(() => {
    const map: Record<string, string> = {};
    selectedArr.forEach((key, i) => {
      map[key] = LINE_COLORS[i % LINE_COLORS.length] ?? '#3B82F6';
    });
    return map;
  }, [selectedArr]);

  // Custom tooltip with YoY change
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const renderTooltip = useCallback(({ active, payload, label }: any) => {
    if (!active || !payload?.length || label == null) return null;
    return (
      <div className={styles.trendTooltip}>
        <div className={styles.tooltipYear}>{label}</div>
        {payload.map((p: any) => {
          const prevYear = chartData.find((d) => d.fiscal_year === (label as number) - 1);
          const prevVal = prevYear?.[p.dataKey as keyof typeof prevYear] as number | null | undefined;
          const yoyChange = prevVal != null && p.value != null ? p.value - (prevVal as number) : null;
          const def = metricLookup[p.dataKey];
          return (
            <div key={p.dataKey} className={styles.tooltipRow}>
              <span style={{ color: p.color }}>&#9679;</span>
              <span className={styles.tooltipLabel}>{def?.label ?? p.dataKey}:</span>
              <span className={styles.tooltipValue}>{formatForTooltip(p.value, p.dataKey, metricLookup)}</span>
              {yoyChange != null && (
                <span className={yoyChange >= 0 ? styles.yoyPositive : styles.yoyNegative}>
                  ({yoyChange >= 0 ? '+' : ''}{formatForTooltip(yoyChange, p.dataKey, metricLookup)})
                </span>
              )}
            </div>
          );
        })}
      </div>
    );
  }, [chartData, metricLookup]);

  return (
    <div className={styles.container ?? ''}>
      <div className={styles.chartTitle ?? ''}>{chartTitle}</div>

      {/* Categorized metric selector */}
      <div className={styles.selectorWrap ?? ''}>
        {SELECTOR_CATEGORIES.map((cat) => (
          <div key={cat.label} className={styles.selectorCategory ?? ''}>
            <span className={styles.selectorLabel ?? ''}>{cat.label}</span>
            <div className={styles.selectorPills ?? ''}>
              {cat.metrics.map((key) => {
                const def = metricLookup[key];
                if (!def) return null;
                const isActive = selected.has(key);
                return (
                  <button
                    key={key}
                    className={`${styles.metricPill ?? ''} ${isActive ? styles.metricPillActive ?? '' : ''}`}
                    onClick={() => toggle(key)}
                  >
                    {isActive && <span className={styles.metricDot ?? ''} style={{ background: colorMap[key] }} />}
                    {def.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className={styles.chartWrap ?? ''}>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={420}>
            <LineChart data={chartData} margin={{ top: 10, right: 30, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
              <XAxis
                dataKey="fiscal_year"
                stroke="var(--text-tertiary)"
                fontSize={11}
                fontFamily="var(--font-mono)"
              />
              <YAxis
                yAxisId="left"
                stroke="var(--text-tertiary)"
                fontSize={10}
                fontFamily="var(--font-mono)"
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                hide={!hasPercent}
              />
              {useDualAxis && (
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="var(--text-tertiary)"
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  tickFormatter={(v: number) => `${v.toFixed(1)}x`}
                />
              )}
              <Tooltip content={renderTooltip} />
              {selectedArr.map((key) => {
                const def = metricLookup[key];
                const isPct = def?.format === 'pct';
                const axisId = useDualAxis ? (isPct ? 'left' : 'right') : 'left';
                return (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    yAxisId={axisId}
                    stroke={colorMap[key]}
                    strokeWidth={2}
                    dot={{ r: 3, fill: colorMap[key] }}
                    activeDot={{ r: 5, strokeWidth: 2, stroke: 'var(--bg-primary)' }}
                    connectNulls
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className={styles.empty ?? ''}>Select metrics above to view trends</div>
        )}
      </div>
    </div>
  );
}
