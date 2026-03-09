import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { RevBasedResult, RevBasedScenarioResult } from '../../../types/models';
import { ResultsCard } from './ResultsCard';
import { ExportDropdown } from '../../../components/ui/ExportButton/ExportDropdown';
import { useModelStore } from '../../../stores/modelStore';
import { downloadExport } from '../../../services/exportService';
import { fmtDollar, fmtPct, fmtMultiple, fmtNumber, fmtPrice } from './formatters';
import styles from './RevBasedView.module.css';

interface RevBasedViewProps {
  result: RevBasedResult;
}

type ScenarioKey = 'base' | 'bull' | 'bear';

const SCENARIO_LABELS: Record<ScenarioKey, string> = {
  base: 'Base',
  bull: 'Bull',
  bear: 'Bear',
};

const SCENARIO_COLORS: Record<ScenarioKey, string> = {
  bear: '#60A5FA',
  base: '#6366F1',
  bull: '#22C55E',
};

/** Compact dollar format for chart Y-axis ($XXB / $XXM). */
function fmtCompactDollar(v: number): string {
  if (v == null || isNaN(v)) return '';
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(0)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

function statusBadgeClass(status: string | null): string {
  if (!status) return styles.badgeFail ?? '';
  const s = status.toLowerCase();
  if (s === 'pass' || s === 'healthy' || s === 'good') return styles.badgePass ?? '';
  if (s === 'marginal' || s === 'caution' || s === 'warning') return styles.badgeMarginal ?? '';
  return styles.badgeFail ?? '';
}

function statusLabel(status: string | null): string {
  if (!status) return '\u2014';
  return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
}

const DARK_TOOLTIP_STYLE = {
  backgroundColor: '#1A1A1A',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#E5E5E5',
};

export function RevBasedView({ result }: RevBasedViewProps) {
  const [activeScenario, setActiveScenario] = useState<ScenarioKey>('base');

  const availableScenarios = useMemo(() => {
    return (['bear', 'base', 'bull'] as ScenarioKey[]).filter(
      (k) => result.scenarios[k] != null,
    );
  }, [result.scenarios]);

  const scenario: RevBasedScenarioResult | undefined = result.scenarios[activeScenario];
  const gm = result.growth_metrics;

  // All scenarios for comparison
  const allScenarios = useMemo(() => {
    return (['bear', 'base', 'bull'] as ScenarioKey[])
      .map((k) => ({ key: k, data: result.scenarios[k] as RevBasedScenarioResult | undefined }))
      .filter((s) => s.data != null);
  }, [result.scenarios]);

  // Revenue projection years
  const projYears = scenario?.projected_revenue?.length ?? 0;

  // ---------- Chart data ----------

  // Revenue Growth Trajectory: merge all scenario revenues into [{year, bear, base, bull}, ...]
  const revenueChartData = useMemo(() => {
    const maxLen = Math.max(
      ...allScenarios.map((s) => s.data?.projected_revenue?.length ?? 0),
    );
    if (maxLen === 0) return [];
    const rows: Record<string, unknown>[] = [];
    for (let i = 0; i < maxLen; i++) {
      const row: Record<string, unknown> = { year: `Year ${i + 1}` };
      for (const s of allScenarios) {
        if (s.data?.projected_revenue?.[i] != null) {
          row[s.key] = s.data.projected_revenue[i];
        }
      }
      rows.push(row);
    }
    return rows;
  }, [allScenarios]);

  // Multiple Evolution: merge multiples_by_year per scenario
  const multipleChartData = useMemo(() => {
    const maxLen = Math.max(
      ...allScenarios.map((s) => s.data?.multiples_by_year?.length ?? 0),
    );
    if (maxLen === 0) return [];
    const rows: Record<string, unknown>[] = [];
    for (let i = 0; i < maxLen; i++) {
      const row: Record<string, unknown> = { year: `Year ${i + 1}` };
      for (const s of allScenarios) {
        if (s.data?.multiples_by_year?.[i] != null) {
          row[s.key] = s.data.multiples_by_year[i];
        }
      }
      rows.push(row);
    }
    return rows;
  }, [allScenarios]);

  // ---------- Football field data ----------
  const footballData = useMemo(() => {
    const prices = allScenarios
      .map((s) => ({ key: s.key, price: s.data?.primary_implied_price ?? 0 }))
      .filter((p) => p.price > 0);
    if (prices.length === 0) return null;

    const firstPrice = prices[0]!.price;
    const lastPrice = prices[prices.length - 1]!.price;
    const bearPrice = prices.find((p) => p.key === 'bear')?.price ?? firstPrice;
    const basePrice = prices.find((p) => p.key === 'base')?.price ?? firstPrice;
    const bullPrice = prices.find((p) => p.key === 'bull')?.price ?? lastPrice;
    const currentPrice = result.current_price;

    const allPrices = [...prices.map((p) => p.price), currentPrice];
    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const range = max - min || 1;
    const padding = range * 0.1;
    const fieldMin = min - padding;
    const fieldMax = max + padding;
    const fieldRange = fieldMax - fieldMin;

    return {
      bearPrice,
      basePrice,
      bullPrice,
      currentPrice,
      fieldMin,
      fieldMax,
      fieldRange,
      bearPct: ((bearPrice - fieldMin) / fieldRange) * 100,
      basePct: ((basePrice - fieldMin) / fieldRange) * 100,
      bullPct: ((bullPrice - fieldMin) / fieldRange) * 100,
      currentPct: ((currentPrice - fieldMin) / fieldRange) * 100,
      barLeftPct: ((bearPrice - fieldMin) / fieldRange) * 100,
      barWidthPct: ((bullPrice - bearPrice) / fieldRange) * 100,
    };
  }, [allScenarios, result.current_price]);

  return (
    <div className={styles.container}>
      {/* a) ResultsCard */}
      <ResultsCard
        impliedPrice={scenario?.primary_implied_price ?? result.weighted_implied_price}
        currentPrice={result.current_price}
        upsidePct={scenario?.upside_downside_pct ?? result.weighted_upside_downside_pct}
        scenarioLabel={activeScenario !== 'base' ? SCENARIO_LABELS[activeScenario] : undefined}
        exportSlot={
          useModelStore.getState().activeModelId ? (
            <ExportDropdown
              options={[
                {
                  label: 'Excel (.xlsx)',
                  format: 'excel',
                  onClick: async () => {
                    const modelId = useModelStore.getState().activeModelId;
                    if (!modelId) return;
                    const date = new Date().toISOString().slice(0, 10);
                    await downloadExport(`/api/v1/export/model/${modelId}/excel`, `${result.ticker}_revenue_based_${date}.xlsx`);
                  },
                },
                {
                  label: 'PDF Report',
                  format: 'pdf',
                  onClick: async () => {
                    const modelId = useModelStore.getState().activeModelId;
                    if (!modelId) return;
                    const date = new Date().toISOString().slice(0, 10);
                    await downloadExport(`/api/v1/export/model/${modelId}/pdf`, `${result.ticker}_revenue_based_${date}.pdf`);
                  },
                },
              ]}
            />
          ) : (
            <button disabled title="Run and save model first to enable export" className={styles.exportDisabled ?? ''}>
              Export &#9662;
            </button>
          )
        }
      />

      {/* b) Key Outputs Section */}
      <div className={styles.keyOutputsSection}>
        <div className={styles.keyCardsRow}>
          <div className={styles.keyCard}>
            <span className={styles.keyCardLabel}>Weighted Implied Price</span>
            <span className={styles.keyCardValue}>{fmtPrice(result.weighted_implied_price)}</span>
          </div>
          <div className={styles.keyCard}>
            <span className={styles.keyCardLabel}>Current Price</span>
            <span className={styles.keyCardValue}>{fmtPrice(result.current_price)}</span>
          </div>
          <div
            className={`${styles.keyCard} ${styles.upsideCard} ${
              result.weighted_upside_downside_pct != null && result.weighted_upside_downside_pct >= 0
                ? styles.upsideCardPositive
                : styles.upsideCardNegative
            }`}
          >
            <span className={styles.keyCardLabel}>Upside / Downside</span>
            <span className={styles.keyCardValue}>
              {result.weighted_upside_downside_pct != null
                ? `${result.weighted_upside_downside_pct >= 0 ? '+' : ''}${fmtPct(result.weighted_upside_downside_pct)}`
                : '\u2014'}
            </span>
          </div>
        </div>
      </div>

      {/* c) Growth Metrics Panel */}
      {gm && (
        <div className={`${styles.section} ${styles.sectionPadded}`}>
          <div className={styles.sectionTitle}>Growth Metrics</div>
          <div className={styles.metricsGrid}>
            {/* Rule of 40 */}
            <div className={styles.metricCard}>
              <div className={styles.metricHeader}>
                <span className={styles.metricName}>Rule of 40</span>
                <span className={`${styles.metricBadge} ${statusBadgeClass(gm.rule_of_40.status)}`}>
                  {statusLabel(gm.rule_of_40.status)}
                </span>
              </div>
              <span className={styles.metricValue}>{fmtNumber(gm.rule_of_40.score, 1)}</span>
              <span className={styles.metricSub}>
                Rev Growth: {fmtPct(gm.rule_of_40.revenue_growth_component)} + Margin:{' '}
                {fmtPct(gm.rule_of_40.margin_component)}
              </span>
            </div>

            {/* EV/ARR */}
            <div className={styles.metricCard}>
              <div className={styles.metricHeader}>
                <span className={styles.metricName}>EV / ARR</span>
              </div>
              <span className={styles.metricValue}>
                {gm.ev_arr != null ? fmtMultiple(gm.ev_arr) : 'N/A'}
              </span>
            </div>

            {/* Magic Number */}
            <div className={styles.metricCard}>
              <div className={styles.metricHeader}>
                <span className={styles.metricName}>Magic Number</span>
                {gm.magic_number_status && (
                  <span
                    className={`${styles.metricBadge} ${statusBadgeClass(gm.magic_number_status)}`}
                  >
                    {statusLabel(gm.magic_number_status)}
                  </span>
                )}
              </div>
              <span className={styles.metricValue}>
                {gm.magic_number != null ? fmtNumber(gm.magic_number, 2) : 'N/A'}
              </span>
            </div>

            {/* PSG Ratio */}
            <div className={styles.metricCard}>
              <div className={styles.metricHeader}>
                <span className={styles.metricName}>PSG Ratio</span>
              </div>
              <span className={styles.metricValue}>
                {gm.psg_ratio != null ? fmtMultiple(gm.psg_ratio) : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* d) Revenue Growth Trajectory Chart */}
      {revenueChartData.length > 0 && (
        <div className={`${styles.section} ${styles.sectionPadded} ${styles.chartSection}`}>
          <div className={styles.chartTitle}>Revenue Growth Trajectory</div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={revenueChartData} margin={{ top: 8, right: 16, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
              <XAxis
                dataKey="year"
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                axisLine={{ stroke: '#333' }}
                tickLine={{ stroke: '#333' }}
              />
              <YAxis
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                axisLine={{ stroke: '#333' }}
                tickLine={{ stroke: '#333' }}
                tickFormatter={(v: number) => fmtCompactDollar(v)}
                width={60}
              />
              <Tooltip
                contentStyle={DARK_TOOLTIP_STYLE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((value: any, name: string) => [
                  fmtDollar(value ?? 0),
                  SCENARIO_LABELS[name as ScenarioKey] ?? name,
                ]) as any}
                labelStyle={{ color: '#A3A3A3', fontWeight: 600 }}
              />
              <Legend
                formatter={(value: string) => SCENARIO_LABELS[value as ScenarioKey] ?? value}
                wrapperStyle={{ fontSize: 11, color: '#A3A3A3' }}
              />
              {allScenarios.map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  stroke={SCENARIO_COLORS[s.key]}
                  strokeWidth={2}
                  dot={{ r: 3, fill: SCENARIO_COLORS[s.key] }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* e) Multiple Evolution Chart */}
      {multipleChartData.length > 0 && (
        <div className={`${styles.section} ${styles.sectionPadded} ${styles.chartSection}`}>
          <div className={styles.chartTitle}>Multiple Evolution (EV/Revenue)</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={multipleChartData} margin={{ top: 8, right: 16, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
              <XAxis
                dataKey="year"
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                axisLine={{ stroke: '#333' }}
                tickLine={{ stroke: '#333' }}
              />
              <YAxis
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                axisLine={{ stroke: '#333' }}
                tickLine={{ stroke: '#333' }}
                tickFormatter={(v: number) => `${v.toFixed(1)}x`}
                width={48}
              />
              <Tooltip
                contentStyle={DARK_TOOLTIP_STYLE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((value: any, name: string) => [
                  fmtMultiple(value ?? 0),
                  SCENARIO_LABELS[name as ScenarioKey] ?? name,
                ]) as any}
                labelStyle={{ color: '#A3A3A3', fontWeight: 600 }}
              />
              <Legend
                formatter={(value: string) => SCENARIO_LABELS[value as ScenarioKey] ?? value}
                wrapperStyle={{ fontSize: 11, color: '#A3A3A3' }}
              />
              {allScenarios.map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  stroke={SCENARIO_COLORS[s.key]}
                  strokeWidth={2}
                  dot={{ r: 3, fill: SCENARIO_COLORS[s.key] }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* f) Scenario Tabs */}
      {availableScenarios.length > 1 && (
        <div className={styles.scenarioTabs}>
          {availableScenarios.map((key) => (
            <button
              key={key}
              className={`${styles.scenarioBtn} ${
                activeScenario === key ? styles.scenarioBtnActive : ''
              }`}
              onClick={() => setActiveScenario(key)}
            >
              {SCENARIO_LABELS[key]}
            </button>
          ))}
        </div>
      )}

      {/* g) Revenue Projection Table */}
      {scenario && projYears > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Revenue Projections</div>
          <div className={styles.tableWrapper}>
            <table className={styles.projTable}>
              <thead>
                <tr>
                  <th></th>
                  {Array.from({ length: projYears }, (_, i) => (
                    <th key={i}>Year {i + 1}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Revenue</td>
                  {scenario.projected_revenue.map((rev, i) => (
                    <td key={i}>{fmtDollar(rev)}</td>
                  ))}
                </tr>
                {scenario.revenue_growth_rates && (
                  <tr>
                    <td>Growth Rate</td>
                    {scenario.revenue_growth_rates.map((gr, i) => (
                      <td key={i}>{fmtPct(gr)}</td>
                    ))}
                  </tr>
                )}
                {scenario.multiples_by_year && (
                  <tr>
                    <td>EV/Revenue</td>
                    {scenario.multiples_by_year.map((m, i) => (
                      <td key={i}>{fmtMultiple(m)}</td>
                    ))}
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* h) Scenario Comparison — Table + Football Field */}
      {allScenarios.length > 1 && (
        <div className={`${styles.section} ${styles.sectionPadded}`}>
          <div className={styles.sectionTitle}>Scenario Comparison</div>

          {/* Comparison Table */}
          <div className={styles.tableWrapper}>
            <table className={`${styles.projTable} ${styles.comparisonTable}`}>
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>Implied Price</th>
                  <th>Upside</th>
                  <th>Weight</th>
                  <th>Entry Multiple</th>
                  <th>Exit Revenue</th>
                </tr>
              </thead>
              <tbody>
                {allScenarios.map(({ key, data }) => {
                  if (!data) return null;
                  const entryMultiple = data.multiples_by_year?.[0] ?? null;
                  const exitRevenue =
                    data.projected_revenue?.length > 0
                      ? data.projected_revenue[data.projected_revenue.length - 1]
                      : null;
                  const pct = data.upside_downside_pct;
                  const isPos = pct != null && pct >= 0;
                  return (
                    <tr key={key}>
                      <td style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                        <span
                          className={styles.scenarioDot}
                          style={{ background: SCENARIO_COLORS[key] }}
                        />
                        {SCENARIO_LABELS[key]}
                      </td>
                      <td>{fmtPrice(data.primary_implied_price)}</td>
                      <td>
                        {pct != null ? (
                          <span className={isPos ? styles.positive : styles.negative}>
                            {isPos ? '+' : ''}
                            {fmtPct(pct)}
                          </span>
                        ) : (
                          '\u2014'
                        )}
                      </td>
                      <td>{fmtPct(data.scenario_weight)}</td>
                      <td>{entryMultiple != null ? fmtMultiple(entryMultiple) : '\u2014'}</td>
                      <td>{exitRevenue != null ? fmtDollar(exitRevenue) : '\u2014'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mini Football Field */}
          {footballData && (
            <div className={styles.footballFieldContainer}>
              <div className={styles.footballFieldTrack}>
                {/* Gradient bar from bear to bull */}
                <div
                  className={styles.footballFieldBar}
                  style={{
                    left: `${footballData.barLeftPct}%`,
                    width: `${footballData.barWidthPct}%`,
                  }}
                />

                {/* Current price dashed line */}
                <div
                  className={styles.footballFieldCurrentLine}
                  style={{ left: `${footballData.currentPct}%` }}
                >
                  <span className={styles.footballFieldCurrentLabel}>
                    Current {fmtPrice(footballData.currentPrice)}
                  </span>
                </div>

                {/* Bear marker */}
                <div
                  className={`${styles.footballFieldMarker} ${styles.footballFieldMarkerBear}`}
                  style={{ left: `${footballData.bearPct}%` }}
                >
                  <span className={styles.footballFieldLabel}>
                    Bear {fmtPrice(footballData.bearPrice)}
                  </span>
                </div>

                {/* Base marker */}
                <div
                  className={`${styles.footballFieldMarker} ${styles.footballFieldMarkerBase}`}
                  style={{ left: `${footballData.basePct}%` }}
                >
                  <span className={styles.footballFieldLabel}>
                    Base {fmtPrice(footballData.basePrice)}
                  </span>
                </div>

                {/* Bull marker */}
                <div
                  className={`${styles.footballFieldMarker} ${styles.footballFieldMarkerBull}`}
                  style={{ left: `${footballData.bullPct}%` }}
                >
                  <span className={styles.footballFieldLabel}>
                    Bull {fmtPrice(footballData.bullPrice)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
