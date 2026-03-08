import { useState, useEffect, useCallback } from 'react';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import { AssumptionCard } from './AssumptionCard';
import { WACCBreakdownComponent } from './WACCBreakdown';
import type { AssumptionSet, ConfidenceDetail, ScenarioProjections } from '../../../types/models';
import styles from './AssumptionsTab.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ScenarioKey = 'base' | 'bull' | 'bear';

const SCENARIOS: { id: ScenarioKey; label: string }[] = [
  { id: 'bear', label: 'Bear' },
  { id: 'base', label: 'Base' },
  { id: 'bull', label: 'Bull' },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Match a confidence detail by category substring. */
function findConfidence(
  details: ConfidenceDetail[] | undefined,
  category: string,
): ConfidenceDetail | undefined {
  if (!details) return undefined;
  return details.find((d) => d.category.toLowerCase().includes(category.toLowerCase()));
}

/** Return CSS class for an overall confidence score. */
function overallConfClass(score: number): string {
  if (score >= 80) return styles.confGreen ?? '';
  if (score >= 60) return styles.confYellow ?? '';
  if (score >= 40) return styles.confOrange ?? '';
  return styles.confRed ?? '';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AssumptionsTab() {
  const ticker = useModelStore((s) => s.activeTicker);
  const pendingOverrides = useModelStore((s) => s.pendingSliderOverrides);
  const pushSliderToAssumptions = useModelStore((s) => s.pushSliderToAssumptions);
  const clearSliderOverrides = useModelStore((s) => s.clearSliderOverrides);
  const pendingCount = Object.keys(pendingOverrides).length;

  const [data, setData] = useState<AssumptionSet | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<ScenarioKey>('base');
  const [overrides, setOverrides] = useState<Record<string, number>>({});

  // -----------------------------------------------------------------------
  // Fetch / Generate
  // -----------------------------------------------------------------------

  const generate = useCallback(
    async (keepOverrides: boolean) => {
      if (!ticker) return;
      setLoading(true);
      setError(null);
      try {
        const result = await api.post<AssumptionSet>(
          `/api/v1/model-builder/${ticker}/generate`,
          {},
        );
        setData(result);
        if (!keepOverrides) setOverrides({});
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to generate assumptions';
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [ticker],
  );

  const reset = useCallback(async () => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.post<AssumptionSet>(
        `/api/v1/model-builder/${ticker}/assumptions/reset`,
      );
      setData(result);
      setOverrides({});
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reset assumptions';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  // On ticker change, generate
  useEffect(() => {
    if (ticker) {
      generate(false);
    } else {
      setData(null);
      setOverrides({});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  // -----------------------------------------------------------------------
  // Override handler
  // -----------------------------------------------------------------------

  const handleOverride = useCallback(
    (path: string, value: number) => {
      setOverrides((prev) => ({ ...prev, [path]: value }));

      // Optimistically update local data as well
      setData((prev) => {
        if (!prev) return prev;
        return applyOverrideLocally(prev, path, value);
      });
    },
    [],
  );

  // -----------------------------------------------------------------------
  // No ticker guard
  // -----------------------------------------------------------------------

  if (!ticker) {
    return (
      <div className={styles.emptyState}>
        <span className={styles.emptyTitle}>Assumptions</span>
        <span className={styles.emptyDesc}>
          Select a ticker to generate model assumptions.
        </span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Generating assumptions for {ticker}...</span>
      </div>
    );
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (!data || !data.scenarios) {
    return (
      <div className={styles.emptyState}>
        <span className={styles.emptyTitle}>No Assumptions</span>
        <span className={styles.emptyDesc}>
          Could not load assumptions for {ticker}.
        </span>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Derived data
  // -----------------------------------------------------------------------

  const scenarioData: ScenarioProjections = data.scenarios[scenario];
  const dcf = data.model_assumptions.dcf;
  const ddm = data.model_assumptions.ddm;
  const confidence = data.confidence;
  const overallScore = confidence?.overall_score ?? 0;
  const details = confidence?.details;
  const reasoning = data.reasoning;
  const warnings = data.metadata.warnings;

  const revenueConf = findConfidence(details, 'revenue_growth');
  const marginConf = findConfidence(details, 'margin');
  const waccConf = findConfidence(details, 'wacc') ?? findConfidence(details, 'cost_of_capital');
  const terminalConf = findConfidence(details, 'terminal');
  const capitalConf = findConfidence(details, 'capital') ?? findConfidence(details, 'capex');
  const ddmConf = findConfidence(details, 'ddm') ?? findConfidence(details, 'dividend');

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.title}>Assumptions for {ticker}</span>
        <span className={styles.headerSpacer} />
        {confidence && (
          <span
            className={`${styles.confidenceOverall} ${overallConfClass(overallScore)}`}
            title="Scores below 80 may indicate limited data or high uncertainty. Review and adjust assumptions manually."
          >
            Confidence: {overallScore}
          </span>
        )}
        <button
          className={styles.btnAccent}
          onClick={() => generate(true)}
          disabled={loading}
        >
          Regenerate
        </button>
        <button
          className={styles.btnDanger}
          onClick={reset}
          disabled={loading}
        >
          Reset
        </button>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className={styles.warnings}>
          {warnings.map((w) => (
            <span key={w} className={styles.warningTag}>{w}</span>
          ))}
        </div>
      )}

      {/* Scenario pills */}
      <div className={styles.scenarioBar}>
        <div className={styles.scenarioControl}>
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              className={[
                styles.scenarioBtn,
                scenario === s.id ? styles.scenarioBtnActive : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => setScenario(s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <span className={styles.scenarioWeight}>
          Weight: {(scenarioData.scenario_weight * 100).toFixed(0)}%
        </span>
      </div>

      {/* Body — scrollable sections */}
      <div className={styles.body}>
        {/* Pending slider overrides banner */}
        {pendingCount > 0 && (
          <div className={styles.syncBanner}>
            <span className={styles.syncBannerText}>
              You have {pendingCount} uncommitted change{pendingCount > 1 ? 's' : ''} from Sensitivity sliders.
            </span>
            <button className={styles.syncBannerApply} onClick={pushSliderToAssumptions}>
              Apply
            </button>
            <button className={styles.syncBannerDismiss} onClick={clearSliderOverrides}>
              Dismiss
            </button>
          </div>
        )}

        {/* Revenue Growth */}
        <Section
          title="Revenue Growth"
          confidence={revenueConf}
          reasoning={reasoning['revenue_growth']}
          overallScore={overallScore}
          collapsible
        >
          {scenarioData.revenue_growth_rates.map((rate, i) => {
            const path = `scenarios.${scenario}.revenue_growth_rates[${i}]`;
            return (
              <AssumptionCard
                key={path}
                label={`Year ${i + 1} Growth`}
                value={overrides[path] ?? rate}
                unit="pct"
                confidenceScore={revenueConf?.score}
                reasoning={revenueConf?.reasoning}
                isOverridden={path in overrides}
                onChange={(v) => handleOverride(path, v)}
              />
            );
          })}
        </Section>

        {/* Operating Margins */}
        <Section
          title="Operating Margins"
          confidence={marginConf}
          reasoning={reasoning['margins']}
          overallScore={overallScore}
          collapsible
        >
          {scenarioData.operating_margins.map((margin, i) => {
            const path = `scenarios.${scenario}.operating_margins[${i}]`;
            return (
              <AssumptionCard
                key={path}
                label={`Year ${i + 1} Op. Margin`}
                value={overrides[path] ?? margin}
                unit="pct"
                confidenceScore={marginConf?.score}
                reasoning={marginConf?.reasoning}
                isOverridden={path in overrides}
                onChange={(v) => handleOverride(path, v)}
              />
            );
          })}
        </Section>

        {/* WACC & Cost of Capital */}
        <Section
          title="WACC & Cost of Capital"
          confidence={waccConf}
          reasoning={reasoning['wacc']}
          overallScore={overallScore}
          collapsible
        >
          {data.wacc_breakdown ? (
            <WACCBreakdownComponent
              data={data.wacc_breakdown}
              overrides={overrides}
              onOverride={handleOverride}
              confidenceScore={waccConf?.score}
              reasoning={waccConf?.reasoning}
            />
          ) : (
            <>
              <AssumptionCard
                label="WACC"
                value={overrides[`scenarios.${scenario}.wacc`] ?? scenarioData.wacc}
                unit="pct"
                confidenceScore={waccConf?.score}
                reasoning={waccConf?.reasoning}
                isOverridden={`scenarios.${scenario}.wacc` in overrides}
                onChange={(v) => handleOverride(`scenarios.${scenario}.wacc`, v)}
              />
              <AssumptionCard
                label="Cost of Equity"
                value={overrides[`scenarios.${scenario}.cost_of_equity`] ?? scenarioData.cost_of_equity}
                unit="pct"
                confidenceScore={waccConf?.score}
                reasoning={waccConf?.reasoning}
                isOverridden={`scenarios.${scenario}.cost_of_equity` in overrides}
                onChange={(v) => handleOverride(`scenarios.${scenario}.cost_of_equity`, v)}
              />
              <AssumptionCard
                label="Tax Rate"
                value={overrides[`scenarios.${scenario}.tax_rate`] ?? scenarioData.tax_rate}
                unit="pct"
                confidenceScore={waccConf?.score}
                isOverridden={`scenarios.${scenario}.tax_rate` in overrides}
                onChange={(v) => handleOverride(`scenarios.${scenario}.tax_rate`, v)}
              />
            </>
          )}
        </Section>

        {/* Terminal Value */}
        <Section
          title="Terminal Value"
          confidence={terminalConf}
          reasoning={reasoning['terminal_value']}
          overallScore={overallScore}
          collapsible
        >
          <AssumptionCard
            label="Terminal Growth Rate"
            value={
              overrides[`scenarios.${scenario}.terminal_growth_rate`] ??
              scenarioData.terminal_growth_rate
            }
            unit="pct"
            confidenceScore={terminalConf?.score}
            reasoning={terminalConf?.reasoning}
            isOverridden={`scenarios.${scenario}.terminal_growth_rate` in overrides}
            onChange={(v) =>
              handleOverride(`scenarios.${scenario}.terminal_growth_rate`, v)
            }
          />
          {dcf?.terminal_exit_multiple != null && (
            <AssumptionCard
              label="Terminal Exit Multiple"
              value={
                overrides['model_assumptions.dcf.terminal_exit_multiple'] ??
                dcf.terminal_exit_multiple
              }
              unit="multiple"
              confidenceScore={terminalConf?.score}
              reasoning={terminalConf?.reasoning}
              isOverridden={'model_assumptions.dcf.terminal_exit_multiple' in overrides}
              onChange={(v) =>
                handleOverride('model_assumptions.dcf.terminal_exit_multiple', v)
              }
            />
          )}
        </Section>

        {/* Capital Structure */}
        {dcf && (
          <Section
            title="Capital Structure"
            confidence={capitalConf}
            reasoning={reasoning['capital_structure']}
            overallScore={overallScore}
          >
            <AssumptionCard
              label="CapEx / Revenue"
              value={
                overrides['model_assumptions.dcf.capex_to_revenue'] ?? dcf.capex_to_revenue
              }
              unit="ratio"
              confidenceScore={capitalConf?.score}
              reasoning={capitalConf?.reasoning}
              isOverridden={'model_assumptions.dcf.capex_to_revenue' in overrides}
              onChange={(v) =>
                handleOverride('model_assumptions.dcf.capex_to_revenue', v)
              }
            />
            <AssumptionCard
              label="D&A / Revenue"
              value={
                overrides['model_assumptions.dcf.depreciation_to_revenue'] ??
                dcf.depreciation_to_revenue
              }
              unit="ratio"
              confidenceScore={capitalConf?.score}
              isOverridden={'model_assumptions.dcf.depreciation_to_revenue' in overrides}
              onChange={(v) =>
                handleOverride('model_assumptions.dcf.depreciation_to_revenue', v)
              }
            />
            <AssumptionCard
              label="NWC Change / Revenue"
              value={
                overrides['model_assumptions.dcf.nwc_change_to_revenue'] ??
                dcf.nwc_change_to_revenue
              }
              unit="ratio"
              confidenceScore={capitalConf?.score}
              isOverridden={'model_assumptions.dcf.nwc_change_to_revenue' in overrides}
              onChange={(v) =>
                handleOverride('model_assumptions.dcf.nwc_change_to_revenue', v)
              }
            />
          </Section>
        )}

        {/* DDM Inputs */}
        {ddm && (
          <Section
            title="DDM Inputs"
            confidence={ddmConf}
            reasoning={reasoning['ddm']}
            overallScore={overallScore}
          >
            <AssumptionCard
              label="Current DPS"
              value={
                overrides['model_assumptions.ddm.current_annual_dividend_per_share'] ??
                ddm.current_annual_dividend_per_share
              }
              unit="abs"
              confidenceScore={ddmConf?.score}
              reasoning={ddmConf?.reasoning}
              isOverridden={
                'model_assumptions.ddm.current_annual_dividend_per_share' in overrides
              }
              onChange={(v) =>
                handleOverride(
                  'model_assumptions.ddm.current_annual_dividend_per_share',
                  v,
                )
              }
            />
            <AssumptionCard
              label="Near-term Div. Growth"
              value={
                overrides['model_assumptions.ddm.dividend_growth_rate_near_term'] ??
                ddm.dividend_growth_rate_near_term
              }
              unit="pct"
              confidenceScore={ddmConf?.score}
              isOverridden={
                'model_assumptions.ddm.dividend_growth_rate_near_term' in overrides
              }
              onChange={(v) =>
                handleOverride(
                  'model_assumptions.ddm.dividend_growth_rate_near_term',
                  v,
                )
              }
            />
            <AssumptionCard
              label="Terminal Div. Growth"
              value={
                overrides['model_assumptions.ddm.dividend_growth_rate_terminal'] ??
                ddm.dividend_growth_rate_terminal
              }
              unit="pct"
              confidenceScore={ddmConf?.score}
              isOverridden={
                'model_assumptions.ddm.dividend_growth_rate_terminal' in overrides
              }
              onChange={(v) =>
                handleOverride(
                  'model_assumptions.ddm.dividend_growth_rate_terminal',
                  v,
                )
              }
            />
            <AssumptionCard
              label="Cost of Equity"
              value={
                overrides['model_assumptions.ddm.cost_of_equity'] ?? ddm.cost_of_equity
              }
              unit="pct"
              confidenceScore={ddmConf?.score}
              isOverridden={'model_assumptions.ddm.cost_of_equity' in overrides}
              onChange={(v) =>
                handleOverride('model_assumptions.ddm.cost_of_equity', v)
              }
            />
            {ddm.payout_ratio_current != null && (
              <AssumptionCard
                label="Payout Ratio"
                value={
                  overrides['model_assumptions.ddm.payout_ratio_current'] ??
                  ddm.payout_ratio_current
                }
                unit="pct"
                confidenceScore={ddmConf?.score}
                isOverridden={'model_assumptions.ddm.payout_ratio_current' in overrides}
                onChange={(v) =>
                  handleOverride('model_assumptions.ddm.payout_ratio_current', v)
                }
              />
            )}
          </Section>
        )}
      </div>

      {/* Metadata footer */}
      <div className={styles.metaBar}>
        <span className={styles.metaItem}>
          <span className={styles.metaLabel}>Generated: </span>
          <span className={styles.metaValue}>
            {new Date(data.generated_at).toLocaleTimeString()}
          </span>
        </span>
        <span className={styles.metaItem}>
          <span className={styles.metaLabel}>Data Quality: </span>
          <span className={styles.metaValue}>{data.data_quality_score}/100</span>
        </span>
        <span className={styles.metaItem}>
          <span className={styles.metaLabel}>Years of Data: </span>
          <span className={styles.metaValue}>{data.years_of_data}</span>
        </span>
        <span className={styles.metaItem}>
          <span className={styles.metaLabel}>Regime: </span>
          <span className={styles.metaValue}>{data.metadata.regime}</span>
        </span>
        {Object.keys(overrides).length > 0 && (
          <span className={styles.metaItem}>
            <span className={styles.metaLabel}>Overrides: </span>
            <span className={styles.metaValue}>{Object.keys(overrides).length}</span>
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section sub-component
// ---------------------------------------------------------------------------

interface SectionProps {
  title: string;
  confidence?: ConfidenceDetail;
  reasoning?: string;
  overallScore: number;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  children: React.ReactNode;
}

function Section({ title, confidence, reasoning, overallScore, collapsible, defaultExpanded, children }: SectionProps) {
  const score = confidence?.score ?? overallScore;
  const confClass = overallConfClass(score);
  const [expanded, setExpanded] = useState(defaultExpanded ?? true);

  const headerClass = [
    styles.sectionHeader,
    collapsible ? styles.sectionHeaderClickable : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={styles.section}>
      <div
        className={headerClass}
        onClick={collapsible ? () => setExpanded((p) => !p) : undefined}
      >
        {collapsible && (
          <span className={`${styles.chevron} ${!expanded ? styles.chevronCollapsed : ''}`}>&#x25BC;</span>
        )}
        <span className={styles.sectionTitle}>{title}</span>
        <span className={`${styles.sectionConfidence} ${confClass}`}>{score}</span>
        {score < 80 && (
          <span className={styles.sectionWarning}>
            <span className={styles.warningIcon}>&#x26A0;</span>
            Review recommended
          </span>
        )}
        {reasoning && (
          <span className={styles.sectionReasoning} title={reasoning}>
            {reasoning}
          </span>
        )}
      </div>
      {expanded && <div className={styles.sectionBody}>{children}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Local override application (optimistic update)
// ---------------------------------------------------------------------------

function applyOverrideLocally(
  data: AssumptionSet,
  path: string,
  value: number,
): AssumptionSet {
  // Deep clone to avoid mutation
  const next = JSON.parse(JSON.stringify(data)) as AssumptionSet;

  // Parse path like "scenarios.base.revenue_growth_rates[2]"
  const scenarioMatch = path.match(
    /^scenarios\.(base|bull|bear)\.(\w+)(?:\[(\d+)\])?$/,
  );
  if (scenarioMatch && next.scenarios) {
    const scenarioKey = scenarioMatch[1] as 'base' | 'bull' | 'bear' | undefined;
    const field = scenarioMatch[2];
    const indexStr = scenarioMatch[3];
    if (!scenarioKey || !field) return next;
    const sc = next.scenarios[scenarioKey];
    if (typeof sc === 'object' && sc !== null && field in sc) {
      const target = sc as unknown as Record<string, unknown>;
      if (indexStr !== undefined) {
        const arr = target[field];
        if (Array.isArray(arr)) {
          arr[parseInt(indexStr, 10)] = value;
        }
      } else {
        target[field] = value;
      }
    }
    return next;
  }

  // Parse "model_assumptions.dcf.capex_to_revenue" style paths
  const maMatch = path.match(/^model_assumptions\.(dcf|ddm)\.(\w+)$/);
  if (maMatch) {
    const model = maMatch[1] as 'dcf' | 'ddm' | undefined;
    const field = maMatch[2];
    if (!model || !field) return next;
    const bucket = next.model_assumptions[model];
    if (bucket && typeof bucket === 'object') {
      (bucket as unknown as Record<string, unknown>)[field] = value;
    }
    return next;
  }

  // Parse "wacc_breakdown.risk_free_rate" style paths
  const waccMatch = path.match(/^wacc_breakdown\.(\w+)$/);
  if (waccMatch && next.wacc_breakdown) {
    const field = waccMatch[1];
    if (field && field in next.wacc_breakdown) {
      (next.wacc_breakdown as unknown as Record<string, unknown>)[field] = value;
    }
    return next;
  }

  return next;
}
