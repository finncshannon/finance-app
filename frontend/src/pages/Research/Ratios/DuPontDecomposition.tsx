import { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { api } from '../../../services/api';
import type { FinancialRow } from '../types';
import styles from './DuPontDecomposition.module.css';

interface DuPontDecompositionProps {
  ticker: string;
  netMargin: number | null;
  assetTurnover: number | null;
}

interface SparkPoint { value: number | null }

export function DuPontDecomposition({ ticker, netMargin, assetTurnover }: DuPontDecompositionProps) {
  const [equityMultiplier, setEquityMultiplier] = useState<number | null>(null);
  const [equityIsNegative, setEquityIsNegative] = useState(false);
  const [history, setHistory] = useState<FinancialRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.get<{ financials: FinancialRow[] }>(
          `/api/v1/research/${ticker}/financials?period_type=annual&limit=5`,
        );
        const rows = data.financials ?? [];
        if (cancelled) return;
        setHistory(rows);
        const row = rows[0];
        if (row?.total_assets && row?.stockholders_equity && row.stockholders_equity !== 0) {
          setEquityMultiplier(row.total_assets / row.stockholders_equity);
          setEquityIsNegative(row.stockholders_equity < 0);
        } else if (row?.stockholders_equity != null && row.stockholders_equity <= 0) {
          setEquityMultiplier(null);
          setEquityIsNegative(true);
        } else {
          setEquityMultiplier(null);
          setEquityIsNegative(false);
        }
      } catch {
        if (!cancelled) { setEquityMultiplier(null); setHistory([]); }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [ticker]);

  const roe = netMargin != null && assetTurnover != null && equityMultiplier != null
    ? netMargin * assetTurnover * equityMultiplier
    : null;

  const fmtPct = (v: number | null) => v == null ? '--' : `${(v * 100).toFixed(1)}%`;
  const fmtX = (v: number | null) => v == null ? '--' : `${v.toFixed(2)}x`;

  // Color-code equity multiplier
  const emColor = equityMultiplier == null
    ? 'var(--text-primary)'
    : equityMultiplier < 2 ? 'var(--color-positive)'
    : equityMultiplier < 4 ? 'var(--color-warning)'
    : 'var(--color-negative)';

  // Sparkline data from history (oldest first)
  const sparkData = useMemo(() => {
    const sorted = [...history].sort((a, b) => a.fiscal_year - b.fiscal_year);
    const margin: SparkPoint[] = [];
    const turnover: SparkPoint[] = [];
    const multiplier: SparkPoint[] = [];
    for (const row of sorted) {
      const nm = row.revenue && row.net_income ? row.net_income / row.revenue : null;
      margin.push({ value: nm });
      const at = row.total_assets && row.revenue ? row.revenue / row.total_assets : null;
      turnover.push({ value: at });
      const em = row.total_assets && row.stockholders_equity && row.stockholders_equity !== 0
        ? row.total_assets / row.stockholders_equity : null;
      multiplier.push({ value: em });
    }
    return { margin, turnover, multiplier };
  }, [history]);

  const renderSparkline = (data: SparkPoint[], color: string) => {
    if (data.length < 2) return null;
    return (
      <div className={styles.sparkWrap}>
        <ResponsiveContainer width={50} height={20}>
          <LineChart data={data}>
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={1} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <div className={styles.container ?? ''}>
      <div className={styles.header ?? ''}>DUPONT DECOMPOSITION</div>
      <div className={styles.formula ?? ''}>
        <div className={styles.result ?? ''}>
          <div className={styles.resultLabel ?? ''}>ROE</div>
          <div className={styles.resultValue ?? ''}>{fmtPct(roe)}</div>
        </div>
        <div className={styles.operator ?? ''}>=</div>
        <div className={styles.component ?? ''}>
          <div className={styles.componentCategory ?? ''}>Profitability</div>
          <div className={styles.componentName ?? ''}>Net Margin</div>
          <div className={styles.componentValue ?? ''}>{fmtPct(netMargin)}</div>
          {renderSparkline(sparkData.margin, '#3B82F6')}
        </div>
        <div className={styles.operator ?? ''}>x</div>
        <div className={styles.component ?? ''}>
          <div className={styles.componentCategory ?? ''}>Efficiency</div>
          <div className={styles.componentName ?? ''}>Asset Turnover</div>
          <div className={styles.componentValue ?? ''}>{fmtX(assetTurnover)}</div>
          {renderSparkline(sparkData.turnover, '#10B981')}
        </div>
        <div className={styles.operator ?? ''}>x</div>
        <div className={styles.component ?? ''}>
          <div className={styles.componentCategory ?? ''}>Leverage</div>
          <div className={styles.componentName ?? ''}>Equity Multiplier</div>
          <div className={styles.componentValue ?? ''} style={{ color: emColor }}>{fmtX(equityMultiplier)}</div>
          {renderSparkline(sparkData.multiplier, emColor)}
        </div>
      </div>

      {/* Context notes */}
      {equityMultiplier != null && equityMultiplier > 4.0 && !equityIsNegative && (
        <div className={styles.contextNote ?? ''}>
          Elevated ROE driven by high financial leverage. {ticker.toUpperCase()}'s equity base is reduced
          by significant share buybacks, amplifying the equity multiplier. Common for mature
          companies with aggressive buyback programs.
        </div>
      )}
      {equityIsNegative && (
        <div className={styles.contextNote ?? ''}>
          <strong>Negative Equity:</strong> Traditional ROE is not meaningful when
          stockholders' equity is negative. This typically results from accumulated buybacks
          exceeding retained earnings.
        </div>
      )}
    </div>
  );
}
