import { useState, useMemo } from 'react';
import type { DDMResult, DDMScenarioResult } from '../../../types/models';
import { ResultsCard } from './ResultsCard';
import { ExportDropdown } from '../../../components/ui/ExportButton/ExportDropdown';
import { useModelStore } from '../../../stores/modelStore';
import { downloadExport } from '../../../services/exportService';
import { displayStageName } from '../../../utils/displayNames';
import { fmtPrice, fmtPct, fmtFactor, fmtNumber } from './formatters';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import styles from './DDMView.module.css';

interface DDMViewProps {
  result: DDMResult;
}

type ScenarioKey = 'base' | 'bull' | 'bear';

const SCENARIO_LABELS: Record<ScenarioKey, string> = {
  base: 'Base',
  bull: 'Bull',
  bear: 'Bear',
};

/* ── Stage color mapping ── */
const STAGE_COLORS: Record<string, string> = {
  high_growth: '#3B82F6',
  transition: '#F59E0B',
  terminal: '#22C55E',
};

function stageClass(stage: string): string {
  if (stage === 'high_growth') return styles.stageHighGrowth ?? '';
  if (stage === 'transition') return styles.stageTransition ?? '';
  if (stage === 'terminal') return styles.stageTerminal ?? '';
  return '';
}

function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (s === 'healthy' || s === 'pass' || s === 'green' || s === 'good') return styles.statusGreen ?? '';
  if (s === 'caution' || s === 'yellow' || s === 'marginal' || s === 'warning')
    return styles.statusYellow ?? '';
  return styles.statusRed ?? '';
}

function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (s === 'healthy' || s === 'pass' || s === 'green' || s === 'good') return 'var(--color-positive)';
  if (s === 'caution' || s === 'yellow' || s === 'marginal' || s === 'warning') return 'var(--color-warning)';
  return 'var(--color-negative)';
}

function healthClass(health: string): string {
  const h = health.toLowerCase();
  if (h === 'healthy') return styles.healthHealthy ?? '';
  if (h === 'caution') return styles.healthCaution ?? '';
  return styles.healthAtRisk ?? '';
}

function healthLabel(health: string): string {
  const h = health.toLowerCase();
  if (h === 'healthy') return 'Healthy';
  if (h === 'caution') return 'Caution';
  return 'At Risk';
}

/** Convert underscored metric names to display labels */
function displayLabel(name: string): string {
  if (!name.includes('_')) return name;
  return name
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

/* ── Chart tooltip styles (dark theme) ── */
const CHART_TOOLTIP_STYLE = {
  background: '#1A1A1A',
  border: '1px solid #333',
  borderRadius: 4,
  fontSize: 12,
  fontFamily: 'var(--font-sans)',
  padding: '8px 12px',
};

/* ── Custom dot for trajectory chart ── */
function StageDot(props: any) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null) return null;
  const color = STAGE_COLORS[payload.stage] ?? '#A3A3A3';
  return <circle cx={cx} cy={cy} r={4} fill={color} stroke={color} strokeWidth={1} />;
}

/* ── Custom tooltip for trajectory chart ── */
function TrajectoryTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={CHART_TOOLTIP_STYLE}>
      <div style={{ color: '#E5E5E5', fontWeight: 600, marginBottom: 4 }}>Year {d.year}</div>
      <div style={{ color: '#A3A3A3' }}>DPS: <span style={{ color: '#E5E5E5' }}>{fmtPrice(d.dps)}</span></div>
      <div style={{ color: '#A3A3A3' }}>Growth: <span style={{ color: '#E5E5E5' }}>{fmtPct(d.growth_rate)}</span></div>
      <div style={{ color: '#A3A3A3' }}>Stage: <span style={{ color: STAGE_COLORS[d.stage] ?? '#E5E5E5' }}>{displayStageName(d.stage)}</span></div>
    </div>
  );
}

/* ── Custom tooltip for waterfall chart ── */
function WaterfallTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div style={CHART_TOOLTIP_STYLE}>
      <div style={{ color: '#E5E5E5', fontWeight: 600, marginBottom: 4 }}>{d.name}</div>
      <div style={{ color: '#A3A3A3' }}>Value: <span style={{ color: '#E5E5E5' }}>{fmtPrice(d.value)}</span></div>
      <div style={{ color: '#A3A3A3' }}>% of Total: <span style={{ color: '#E5E5E5' }}>{fmtPct(d.pctOfTotal)}</span></div>
    </div>
  );
}

/* ── Custom bar label for waterfall ── */
function WaterfallLabel(props: any) {
  const { x, y, width, value } = props;
  if (value == null || value === 0) return null;
  return (
    <text
      x={x + width / 2}
      y={y - 6}
      fill="#A3A3A3"
      textAnchor="middle"
      fontSize={10}
      fontFamily="var(--font-mono)"
    >
      {fmtPrice(value)}
    </text>
  );
}

export function DDMView({ result }: DDMViewProps) {
  const [activeScenario, setActiveScenario] = useState<ScenarioKey>('base');

  // a) Not-applicable guard
  if (!result.applicable) {
    return (
      <div className={styles.notApplicable}>
        <div className={styles.notApplicableIcon}>&#x2298;</div>
        <div className={styles.notApplicableText}>
          {result.reason || 'DDM not applicable for this company (no dividends).'}
        </div>
      </div>
    );
  }

  const availableScenarios = (['bear', 'base', 'bull'] as ScenarioKey[]).filter(
    (k) => result.scenarios[k] != null,
  );

  const scenario: DDMScenarioResult | undefined = result.scenarios[activeScenario];
  const schedule = scenario?.dividend_schedule ?? [];

  // b) Secondary values
  const secondaryValues = useMemo(() => {
    const vals: { label: string; value: string }[] = [];
    if (result.metadata?.cost_of_equity != null) {
      vals.push({ label: 'Cost of Equity', value: fmtPct(result.metadata.cost_of_equity) });
    }
    if (result.metadata?.ddm_variant) {
      vals.push({ label: 'DDM Variant', value: result.metadata.ddm_variant });
    }
    if (scenario) {
      vals.push({
        label: 'Terminal Growth',
        value: fmtPct(scenario.dividend_growth_terminal),
      });
    }
    return vals;
  }, [result.metadata, scenario]);

  // ── Chart data: trajectory ──
  const trajectoryData = useMemo(() => {
    return schedule.map((row) => ({
      year: row.year,
      dps: row.dps,
      stage: row.stage,
      growth_rate: row.growth_rate,
    }));
  }, [schedule]);

  // ── Chart data: waterfall ──
  const waterfallData = useMemo(() => {
    if (!scenario) return [];
    const total = scenario.intrinsic_value_per_share;
    const items: { name: string; value: number; base: number; color: string; pctOfTotal: number }[] = [];

    let cumulative = 0;

    // PV Stage 1
    items.push({
      name: 'PV Stage 1',
      value: scenario.pv_stage1,
      base: cumulative,
      color: '#3B82F6',
      pctOfTotal: total > 0 ? scenario.pv_stage1 / total : 0,
    });
    cumulative += scenario.pv_stage1;

    // PV Stage 2 (if exists)
    if (scenario.pv_stage2 != null && scenario.pv_stage2 > 0) {
      items.push({
        name: 'PV Stage 2',
        value: scenario.pv_stage2,
        base: cumulative,
        color: '#F59E0B',
        pctOfTotal: total > 0 ? scenario.pv_stage2 / total : 0,
      });
      cumulative += scenario.pv_stage2;
    }

    // PV Terminal
    items.push({
      name: 'PV Terminal',
      value: scenario.pv_terminal,
      base: cumulative,
      color: '#22C55E',
      pctOfTotal: total > 0 ? scenario.pv_terminal / total : 0,
    });

    // Total bar (from 0)
    items.push({
      name: 'Total',
      value: total,
      base: 0,
      color: '#6366F1',
      pctOfTotal: 1,
    });

    return items;
  }, [scenario]);

  // ── Key outputs computed values ──
  const currentDivYield = useMemo(() => {
    const first = schedule[0];
    if (!first || !result.current_price) return null;
    return first.dps / result.current_price;
  }, [schedule, result.current_price]);

  const impliedDivYield = useMemo(() => {
    const first = schedule[0];
    if (!first || !scenario?.intrinsic_value_per_share) return null;
    return first.dps / scenario.intrinsic_value_per_share;
  }, [schedule, scenario]);

  return (
    <div className={styles.container}>
      {/* b) Results Card */}
      <ResultsCard
        impliedPrice={result.weighted_intrinsic_value}
        currentPrice={result.current_price}
        upsidePct={result.weighted_upside_downside_pct}
        label="Intrinsic Value"
        secondaryValues={secondaryValues}
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
                    await downloadExport(`/api/v1/export/model/${modelId}/excel`, `${result.ticker}_ddm_${date}.xlsx`);
                  },
                },
                {
                  label: 'PDF Report',
                  format: 'pdf',
                  onClick: async () => {
                    const modelId = useModelStore.getState().activeModelId;
                    if (!modelId) return;
                    const date = new Date().toISOString().slice(0, 10);
                    await downloadExport(`/api/v1/export/model/${modelId}/pdf`, `${result.ticker}_ddm_${date}.pdf`);
                  },
                },
              ]}
            />
          ) : (
            <button disabled title="Run and save model first to enable export" className={styles.exportDisabled ?? ''}>
              Export &#x25BE;
            </button>
          )
        }
      />

      {/* c) Scenario Tabs */}
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

      {/* ── NEW: Dividend Growth Trajectory Chart ── */}
      {trajectoryData.length > 0 && (
        <div className={styles.chartSection}>
          <div className={styles.chartTitle}>Dividend Growth Trajectory</div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={trajectoryData} margin={{ top: 10, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
              <XAxis
                dataKey="year"
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                tickLine={false}
                tickFormatter={(v: number) => `$${v.toFixed(2)}`}
                width={60}
              />
              <Tooltip content={<TrajectoryTooltip />} cursor={{ stroke: '#444', strokeDasharray: '3 3' }} />
              <Line
                type="monotone"
                dataKey="dps"
                stroke="#555"
                strokeWidth={2}
                dot={<StageDot />}
                activeDot={{ r: 6, strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── NEW: Value Decomposition Waterfall Chart ── */}
      {waterfallData.length > 0 && (
        <div className={styles.chartSection}>
          <div className={styles.chartTitle}>Value Decomposition</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={waterfallData} margin={{ top: 20, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                tickLine={false}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                width={55}
              />
              <Tooltip content={<WaterfallTooltip />} cursor={false} />
              {/* Invisible base bar */}
              <Bar dataKey="base" stackId="waterfall" fill="transparent" isAnimationActive={false} />
              {/* Visible value bar */}
              <Bar
                dataKey="value"
                stackId="waterfall"
                isAnimationActive={true}
                label={<WaterfallLabel />}
                radius={[3, 3, 0, 0]}
              >
                {waterfallData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* d) Dividend Schedule Table */}
      {schedule.length > 0 && (
        <div className={styles.tableSection}>
          <div className={styles.sectionTitle}>Dividend Schedule</div>
          <div className={styles.tableWrapper}>
            <table className={styles.scheduleTable}>
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Stage</th>
                  <th>DPS ($)</th>
                  <th>Growth (%)</th>
                  <th>Disc. Factor</th>
                  <th>PV ($)</th>
                </tr>
              </thead>
              <tbody>
                {schedule.map((row) => (
                  <tr key={row.year}>
                    <td>{row.year}</td>
                    <td style={{ textAlign: 'left' }}>
                      <span className={`${styles.stageBadge} ${stageClass(row.stage)}`}>
                        {displayStageName(row.stage)}
                      </span>
                    </td>
                    <td>{fmtPrice(row.dps)}</td>
                    <td>{fmtPct(row.growth_rate)}</td>
                    <td>{fmtFactor(row.discount_factor)}</td>
                    <td>{fmtPrice(row.pv)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── NEW: Expanded Key Outputs Panel (replaces old decomposition) ── */}
      {scenario && (
        <div className={styles.keyOutputsPanel}>
          <div className={styles.sectionTitle}>Key Outputs</div>

          {/* Top: 3 large cards */}
          <div className={styles.keyCardsRow}>
            <div className={styles.keyCard}>
              <span className={styles.keyCardLabel}>Intrinsic Value</span>
              <span className={styles.keyCardValue}>{fmtPrice(scenario.intrinsic_value_per_share)}</span>
            </div>
            <div className={styles.keyCard}>
              <span className={styles.keyCardLabel}>Current Div Yield</span>
              <span className={styles.keyCardValue}>
                {currentDivYield != null ? fmtPct(currentDivYield) : '\u2014'}
              </span>
            </div>
            <div className={styles.keyCard}>
              <span className={styles.keyCardLabel}>Implied Div Yield</span>
              <span className={styles.keyCardValue}>
                {impliedDivYield != null ? fmtPct(impliedDivYield) : '\u2014'}
              </span>
            </div>
          </div>

          {/* Step-down decomposition */}
          <div className={styles.stepDown}>
            <div className={styles.stepDownRow}>
              <span className={styles.stepDownLabel}>PV Stage 1</span>
              <span className={styles.stepDownDots} />
              <span className={styles.stepDownValue}>
                {fmtPrice(scenario.pv_stage1)}
                <span className={styles.stepDownPct}>
                  ({fmtPct(scenario.intrinsic_value_per_share > 0 ? scenario.pv_stage1 / scenario.intrinsic_value_per_share : 0)})
                </span>
              </span>
            </div>
            {scenario.pv_stage2 != null && scenario.pv_stage2 > 0 && (
              <div className={styles.stepDownRow}>
                <span className={styles.stepDownLabel}>PV Stage 2</span>
                <span className={styles.stepDownDots} />
                <span className={styles.stepDownValue}>
                  {fmtPrice(scenario.pv_stage2)}
                  <span className={styles.stepDownPct}>
                    ({fmtPct(scenario.intrinsic_value_per_share > 0 ? scenario.pv_stage2 / scenario.intrinsic_value_per_share : 0)})
                  </span>
                </span>
              </div>
            )}
            <div className={styles.stepDownRow}>
              <span className={styles.stepDownLabel}>PV Terminal</span>
              <span className={styles.stepDownDots} />
              <span className={styles.stepDownValue}>
                {fmtPrice(scenario.pv_terminal)}
                <span className={styles.stepDownPct}>
                  ({fmtPct(scenario.tv_pct_of_total)})
                </span>
              </span>
            </div>
            <div className={styles.stepDownSeparator} />
            <div className={styles.stepDownRow}>
              <span className={styles.stepDownLabel} style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Total</span>
              <span className={styles.stepDownDots} />
              <span className={styles.stepDownValue} style={{ fontWeight: 700 }}>
                {fmtPrice(scenario.intrinsic_value_per_share)}
              </span>
            </div>
          </div>

          {/* Reference bar */}
          <div className={styles.referenceBar}>
            <div className={styles.referenceItem}>
              <span className={styles.referenceLabel}>Cost of Equity</span>
              <span className={styles.referenceValue}>{fmtPct(result.metadata?.cost_of_equity)}</span>
            </div>
            <div className={styles.referenceItem}>
              <span className={styles.referenceLabel}>Terminal Growth</span>
              <span className={styles.referenceValue}>{fmtPct(scenario.dividend_growth_terminal)}</span>
            </div>
            <div className={styles.referenceItem}>
              <span className={styles.referenceLabel}>TV % of Total</span>
              <span className={styles.referenceValue}>{fmtPct(scenario.tv_pct_of_total)}</span>
            </div>
          </div>
        </div>
      )}

      {/* f) Sustainability Panel (with progress bars + tooltips) */}
      {result.sustainability && (
        <div className={styles.sustainabilityPanel}>
          <div className={styles.sectionTitle}>Dividend Sustainability</div>
          <div className={styles.healthBadgeRow}>
            <span className={`${styles.healthBadge} ${healthClass(result.sustainability.overall_health)}`}>
              {healthLabel(result.sustainability.overall_health)}
            </span>
          </div>
          <div className={styles.metricsList}>
            {result.sustainability.metrics.map((metric) => {
              const clampedValue = metric.value != null ? Math.min(Math.max(metric.value, 0), 1) : 0;
              return (
                <div key={metric.name} className={styles.metricRow}>
                  <span
                    className={`${styles.metricName} ${styles.metricTooltip}`}
                    title={metric.description}
                  >
                    {displayLabel(metric.name)}
                  </span>
                  <span className={styles.metricValue}>
                    {metric.value != null ? fmtNumber(metric.value, 2) : '\u2014'}
                  </span>
                  <span className={styles.progressBarBg}>
                    <span
                      className={styles.progressBarFill}
                      style={{
                        width: `${clampedValue * 100}%`,
                        backgroundColor: statusColor(metric.status),
                      }}
                    />
                  </span>
                  <span className={`${styles.statusBadge} ${statusClass(metric.status)}`} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
