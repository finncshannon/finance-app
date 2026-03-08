import { useState, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
  ReferenceLine,
} from 'recharts';
import type { DCFResult, DCFScenarioResult, DCFYearRow } from '../../../types/models';
import { ResultsCard } from './ResultsCard';
import { ExportDropdown } from '../../../components/ui/ExportButton/ExportDropdown';
import { useModelStore } from '../../../stores/modelStore';
import { downloadExport } from '../../../services/exportService';
import { fmtDollar, fmtPct, fmtFactor, fmtPrice, fmtMultiple, fmtNumber } from './formatters';
import styles from './DCFView.module.css';

interface DCFViewProps {
  result: DCFResult;
}

type ScenarioKey = 'base' | 'bull' | 'bear';

const SCENARIO_LABELS: Record<ScenarioKey, string> = {
  base: 'Base',
  bull: 'Bull',
  bear: 'Bear',
};

const STEP_COLORS: Record<string, string> = {
  start: '#3B82F6',
  subtotal: '#3B82F6',
  addition: '#22C55E',
  subtraction: '#EF4444',
  end: '#3B82F6',
};

/** Row definitions for the transposed projection table. */
interface RowDef {
  label: string;
  key: keyof DCFYearRow;
  format: 'dollar' | 'pct' | 'factor';
  separator?: boolean; // add separator after this row
}

const ROW_DEFS: RowDef[] = [
  { label: 'Revenue', key: 'revenue', format: 'dollar' },
  { label: 'Revenue Growth', key: 'revenue_growth', format: 'pct' },
  { label: 'COGS', key: 'cogs', format: 'dollar' },
  { label: 'Gross Profit', key: 'gross_profit', format: 'dollar' },
  { label: 'Gross Margin', key: 'gross_margin', format: 'pct', separator: true },
  { label: 'OpEx', key: 'opex', format: 'dollar' },
  { label: 'EBIT', key: 'ebit', format: 'dollar' },
  { label: 'Op Margin', key: 'operating_margin', format: 'pct' },
  { label: 'D&A', key: 'da', format: 'dollar' },
  { label: 'EBITDA', key: 'ebitda', format: 'dollar' },
  { label: 'EBITDA Margin', key: 'ebitda_margin', format: 'pct', separator: true },
  { label: 'Taxes', key: 'taxes', format: 'dollar' },
  { label: 'NOPAT', key: 'nopat', format: 'dollar' },
  { label: 'CapEx', key: 'capex', format: 'dollar' },
  { label: 'NWC Change', key: 'nwc_change', format: 'dollar', separator: true },
  { label: 'FCF', key: 'fcf', format: 'dollar' },
  { label: 'FCF Margin', key: 'fcf_margin', format: 'pct', separator: true },
  { label: 'Discount Factor', key: 'discount_factor', format: 'factor' },
  { label: 'PV(FCF)', key: 'pv_fcf', format: 'dollar' },
];

function formatCell(value: number, format: 'dollar' | 'pct' | 'factor'): string {
  switch (format) {
    case 'dollar':
      return fmtDollar(value);
    case 'pct':
      return fmtPct(value);
    case 'factor':
      return fmtFactor(value);
  }
}

export function DCFView({ result }: DCFViewProps) {
  const [activeScenario, setActiveScenario] = useState<ScenarioKey>('base');

  const availableScenarios = useMemo(() => {
    return (['bear', 'base', 'bull'] as ScenarioKey[]).filter(
      (k) => result.scenarios[k] != null,
    );
  }, [result.scenarios]);

  const scenario: DCFScenarioResult | undefined = result.scenarios[activeScenario];
  const projectionTable: DCFYearRow[] = scenario?.projection_table ?? [];

  // Derived values for step-down
  const netDebt = useMemo(() => {
    if (scenario) return scenario.enterprise_value - scenario.equity_value;
    return null;
  }, [scenario]);

  const sharesOutstanding = useMemo(() => {
    if (scenario && scenario.implied_price > 0) {
      return scenario.equity_value / scenario.implied_price;
    }
    return null;
  }, [scenario]);

  const marketCap = useMemo(() => {
    if (sharesOutstanding != null && result.current_price > 0) {
      return result.current_price * sharesOutstanding;
    }
    return null;
  }, [sharesOutstanding, result.current_price]);

  // Waterfall chart data (enriched with running totals and % of EV)
  const waterfallData = useMemo(() => {
    let runningTotal = 0;
    const steps = result.waterfall?.steps ?? [];
    const ev = steps[0]?.value ?? 1;
    return steps.map((step) => {
      if (step.step_type === 'start' || step.step_type === 'subtotal' || step.step_type === 'end') {
        runningTotal = step.value;
      } else {
        runningTotal += step.value;
      }
      return {
        label: step.label,
        value: step.value,
        stepType: step.step_type,
        runningTotal,
        pctOfEV: ev > 0 ? step.value / ev : 0,
        displayValue: fmtDollar(step.value),
      };
    });
  }, [result.waterfall]);

  // Secondary values for the ResultsCard
  const secondaryValues = useMemo(() => {
    const vals: { label: string; value: string }[] = [];
    if (scenario) {
      vals.push({ label: 'WACC', value: fmtPct(scenario.wacc) });
      vals.push({ label: 'Terminal Growth', value: fmtPct(scenario.terminal_growth_rate) });
    }
    if (result.metadata?.terminal_method) {
      vals.push({ label: 'Terminal Method', value: result.metadata.terminal_method });
    }
    if (scenario) {
      vals.push({ label: 'TV % of EV', value: fmtPct(scenario.tv_pct_of_ev) });
    }
    return vals;
  }, [scenario, result.metadata]);

  return (
    <div className={styles.container}>
      {/* a) Results Card */}
      <ResultsCard
        impliedPrice={result.weighted_implied_price}
        currentPrice={result.current_price}
        upsidePct={result.weighted_upside_downside_pct}
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
                    await downloadExport(`/api/v1/export/model/${modelId}/excel`, `${result.ticker}_dcf_${date}.xlsx`);
                  },
                },
                {
                  label: 'PDF Report',
                  format: 'pdf',
                  onClick: async () => {
                    const modelId = useModelStore.getState().activeModelId;
                    if (!modelId) return;
                    const date = new Date().toISOString().slice(0, 10);
                    await downloadExport(`/api/v1/export/model/${modelId}/pdf`, `${result.ticker}_dcf_${date}.pdf`);
                  },
                },
              ]}
            />
          ) : (
            <button disabled title="Run and save model first to enable export" className={styles.exportDisabled ?? ''}>
              Export ▾
            </button>
          )
        }
      />

      {/* b) Scenario Tabs */}
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

      {/* c) Projection Table */}
      {projectionTable.length > 0 && (
        <div className={styles.tableSection}>
          <div className={styles.sectionTitle}>Projection Table</div>
          <div className={styles.tableWrapper}>
            <table className={styles.projectionTable}>
              <thead>
                <tr>
                  <th></th>
                  {projectionTable.map((yr) => (
                    <th key={yr.year}>Year {yr.year}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROW_DEFS.map((row) => (
                  <>
                    <tr key={row.key}>
                      <td>{row.label}</td>
                      {projectionTable.map((yr) => {
                        const val = yr[row.key] as number;
                        const isNeg = val < 0;
                        return (
                          <td
                            key={yr.year}
                            className={isNeg ? styles.negativeValue : undefined}
                          >
                            {formatCell(val, row.format)}
                          </td>
                        );
                      })}
                    </tr>
                    {row.separator && (
                      <tr key={`sep-${row.key}`} className={styles.sectionSeparator}>
                        <td colSpan={projectionTable.length + 1} />
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* d) Key Outputs Panel — Storytelling Layout */}
      {scenario && (
        <div className={styles.keyOutputsPanel}>
          <div className={styles.sectionTitle}>Key Outputs</div>

          {/* Headline cards */}
          <div className={styles.headlineCards}>
            <div className={styles.headlineCard}>
              <span className={styles.headlineLabel}>Enterprise Value</span>
              <span className={styles.headlineValue}>{fmtDollar(scenario.enterprise_value)}</span>
            </div>
            <div className={styles.headlineCard}>
              <span className={styles.headlineLabel}>Equity Value</span>
              <span className={styles.headlineValue}>{fmtDollar(scenario.equity_value)}</span>
            </div>
            <div className={`${styles.headlineCard} ${styles.headlineCardAccent}`}>
              <span className={styles.headlineLabel}>Implied Price</span>
              <span className={styles.headlineValue}>{fmtPrice(scenario.implied_price)}</span>
              {scenario.upside_downside_pct != null && (
                <span className={scenario.upside_downside_pct >= 0 ? styles.upsideTag : styles.downsideTag}>
                  {scenario.upside_downside_pct >= 0 ? '+' : ''}{fmtPct(scenario.upside_downside_pct)} upside
                </span>
              )}
            </div>
          </div>

          {/* Step-down calculation */}
          <div className={styles.stepDown}>
            <div className={styles.stepRow}>
              <span className={styles.stepLabel}>PV of FCFs</span>
              <span className={styles.stepValue}>{fmtDollar(scenario.pv_fcf_total)}</span>
              <span className={styles.stepAnnotation}>
                {scenario.enterprise_value > 0 ? fmtPct(scenario.pv_fcf_total / scenario.enterprise_value) : '\u2014'} of EV
              </span>
            </div>
            <div className={styles.stepRow}>
              <span className={styles.stepLabel}>PV of Terminal Value</span>
              <span className={styles.stepValue}>{fmtDollar(scenario.pv_terminal_value)}</span>
              <span className={styles.stepAnnotation}>{fmtPct(scenario.tv_pct_of_ev)} of EV</span>
            </div>
            <div className={styles.stepRowSubtotal}>
              <span className={styles.stepLabel}>= Enterprise Value</span>
              <span className={styles.stepValue}>{fmtDollar(scenario.enterprise_value)}</span>
            </div>
            {netDebt != null && (
              <div className={styles.stepRow}>
                <span className={styles.stepLabel}>Less: Net Debt</span>
                <span className={styles.stepValue}>{fmtDollar(-netDebt)}</span>
              </div>
            )}
            <div className={styles.stepRowSubtotal}>
              <span className={styles.stepLabel}>= Equity Value</span>
              <span className={styles.stepValue}>{fmtDollar(scenario.equity_value)}</span>
            </div>
            {sharesOutstanding != null && (
              <div className={styles.stepRow}>
                <span className={styles.stepLabel}>&divide; Shares Outstanding</span>
                <span className={styles.stepValue}>{fmtNumber(sharesOutstanding / 1e9, 2)}B</span>
              </div>
            )}
            <div className={styles.stepRowFinal}>
              <span className={styles.stepLabel}>= Implied Price</span>
              <span className={styles.stepValue}>{fmtPrice(scenario.implied_price)}</span>
            </div>
          </div>

          {/* Reference bar */}
          <div className={styles.refBar}>
            <div className={styles.refItem}>
              <span className={styles.refLabel}>WACC</span>
              <span className={styles.refValue}>{fmtPct(scenario.wacc)}</span>
            </div>
            <div className={styles.refItem}>
              <span className={styles.refLabel}>Terminal Growth</span>
              <span className={styles.refValue}>{fmtPct(scenario.terminal_growth_rate)}</span>
            </div>
            <div className={styles.refItem}>
              <span className={styles.refLabel}>TV % of EV</span>
              <span className={styles.refValue}>{fmtPct(scenario.tv_pct_of_ev)}</span>
            </div>
            {scenario.terminal_exit_multiple != null && (
              <div className={styles.refItem}>
                <span className={styles.refLabel}>Exit Multiple</span>
                <span className={styles.refValue}>{fmtMultiple(scenario.terminal_exit_multiple)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* e) Waterfall Chart — Enhanced */}
      {waterfallData.length > 0 && (
        <div className={styles.waterfallSection}>
          <div className={styles.waterfallTitle}>EV Bridge (Waterfall)</div>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={waterfallData}
              margin={{ top: 24, right: 16, left: 16, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                interval={0}
                angle={-30}
                textAnchor="end"
                height={50}
              />
              <YAxis
                tick={{ fill: '#A3A3A3', fontSize: 11 }}
                stroke="#333"
                tickFormatter={(v: number) => fmtDollar(v)}
                width={70}
              />
              <Tooltip
                content={({ active, payload, label }: any) => {
                  if (!active || !payload?.length) return null;
                  const data = payload[0]?.payload;
                  if (!data) return null;
                  return (
                    <div className={styles.waterfallTooltip}>
                      <div className={styles.tooltipLabel}>{label}</div>
                      <div className={styles.tooltipRow}>
                        <span>Value:</span><span>{fmtDollar(data.value)}</span>
                      </div>
                      <div className={styles.tooltipRow}>
                        <span>Running Total:</span><span>{fmtDollar(data.runningTotal)}</span>
                      </div>
                      {data.pctOfEV !== 0 && data.stepType !== 'start' && (
                        <div className={styles.tooltipRow}>
                          <span>% of EV:</span><span>{fmtPct(Math.abs(data.pctOfEV))}</span>
                        </div>
                      )}
                    </div>
                  );
                }}
              />
              {marketCap != null && (
                <ReferenceLine
                  y={marketCap}
                  stroke="#F59E0B"
                  strokeDasharray="5 5"
                  strokeWidth={1}
                  label={{
                    value: `Market Cap: ${fmtDollar(marketCap)}`,
                    fill: '#F59E0B',
                    fontSize: 10,
                    position: 'right',
                  }}
                />
              )}
              <Bar dataKey="value" barSize={36}>
                {waterfallData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={STEP_COLORS[entry.stepType] ?? '#3B82F6'}
                  />
                ))}
                <LabelList
                  dataKey="displayValue"
                  position="top"
                  fill="#E5E5E5"
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                />
                <LabelList
                  content={(props: any) => {
                    const { x, y, width, index } = props;
                    const entry = waterfallData[index];
                    if (!entry || entry.stepType === 'start' || entry.stepType === 'end' || entry.stepType === 'subtotal') return null;
                    return (
                      <text
                        x={x + width / 2}
                        y={y - 16}
                        fill="#A3A3A3"
                        fontSize={9}
                        textAnchor="middle"
                        fontFamily="var(--font-mono)"
                      >
                        {fmtPct(Math.abs(entry.pctOfEV))} of EV
                      </text>
                    );
                  }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
