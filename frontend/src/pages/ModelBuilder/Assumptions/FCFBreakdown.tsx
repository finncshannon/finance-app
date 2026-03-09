import { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import type { ScenarioProjections, DCFAssumptions } from '../../../types/models';
import styles from './FCFBreakdown.module.css';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface FCFBreakdownProps {
  scenario: ScenarioProjections;
  dcf: DCFAssumptions;
  scenarioKey: string;
  overrides: Record<string, number>;
  onOverride: (path: string, value: number) => void;
  confidenceScore?: number;
  reasoning?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtPct(v: number): string {
  return (v * 100).toFixed(2);
}

function fmtDollarCompact(v: number | null | undefined): string {
  if (v == null) return '\u2014';
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${abs.toLocaleString()}`;
}

// ---------------------------------------------------------------------------
// Inline editable input (matches WACC pattern)
// ---------------------------------------------------------------------------

interface InlineInputProps {
  value: number;
  unit: '%' | 'x' | '';
  isOverridden: boolean;
  onChange: (v: number) => void;
  displayFactor?: number;
  decimals?: number;
  sliderMin?: number;
  sliderMax?: number;
  sliderStep?: number;
}

function InlineInput({ value, unit, isOverridden, onChange, displayFactor = 100, decimals = 2, sliderMin, sliderMax, sliderStep }: InlineInputProps) {
  const displayVal = (value * displayFactor).toFixed(decimals);
  const [localVal, setLocalVal] = useState(displayVal);
  const inputRef = useRef<HTMLInputElement>(null);
  const showSlider = sliderMin != null && sliderMax != null;

  useEffect(() => {
    if (document.activeElement !== inputRef.current) {
      setLocalVal((value * displayFactor).toFixed(decimals));
    }
  }, [value, displayFactor, decimals]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      setLocalVal(raw);
      const num = parseFloat(raw);
      if (!isNaN(num)) {
        onChange(num / displayFactor);
      }
    },
    [onChange, displayFactor],
  );

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const internal = parseFloat(e.target.value);
      if (!isNaN(internal)) {
        setLocalVal((internal * displayFactor).toFixed(decimals));
        onChange(internal);
      }
    },
    [onChange, displayFactor, decimals],
  );

  const handleBlur = useCallback(() => {
    const num = parseFloat(localVal);
    if (!isNaN(num)) {
      setLocalVal(num.toFixed(decimals));
    } else {
      setLocalVal((value * displayFactor).toFixed(decimals));
    }
  }, [localVal, value, displayFactor, decimals]);

  return (
    <>
      {showSlider && (
        <input
          type="range"
          className={styles.fieldSlider}
          min={sliderMin}
          max={sliderMax}
          step={sliderStep ?? 0.001}
          value={value}
          onChange={handleSliderChange}
        />
      )}
      {!showSlider && <span className={styles.fieldSliderSpacer} />}
      <input
        ref={inputRef}
        className={styles.fieldInput}
        type="text"
        inputMode="decimal"
        value={localVal}
        onChange={handleChange}
        onBlur={handleBlur}
      />
      <span className={styles.fieldUnit}>{unit}</span>
      {isOverridden && <span className={styles.overrideBadge}>Manual</span>}
    </>
  );
}

// ---------------------------------------------------------------------------
// FCFBreakdownComponent
// ---------------------------------------------------------------------------

export function FCFBreakdownComponent({
  scenario,
  dcf,
  scenarioKey,
  overrides,
  onOverride,
}: FCFBreakdownProps) {
  // Read values: overrides first, then data
  const opMargin = overrides[`scenarios.${scenarioKey}.operating_margins[0]`] ?? scenario.operating_margins[0] ?? 0;
  const taxRate = overrides[`scenarios.${scenarioKey}.tax_rate`] ?? scenario.tax_rate;
  const capexRatio = overrides['model_assumptions.dcf.capex_to_revenue'] ?? dcf.capex_to_revenue;
  const deprRatio = overrides['model_assumptions.dcf.depreciation_to_revenue'] ?? dcf.depreciation_to_revenue;
  const nwcRatio = overrides['model_assumptions.dcf.nwc_change_to_revenue'] ?? dcf.nwc_change_to_revenue;
  const revenueGrowth = overrides[`scenarios.${scenarioKey}.revenue_growth_rates[0]`] ?? scenario.revenue_growth_rates[0] ?? 0;

  const baseRevenue = dcf.base_revenue ?? 0;

  // Computed values
  const yr1Revenue = useMemo(() => baseRevenue * (1 + revenueGrowth), [baseRevenue, revenueGrowth]);
  const ebit = useMemo(() => yr1Revenue * opMargin, [yr1Revenue, opMargin]);
  const nopat = useMemo(() => ebit * (1 - taxRate), [ebit, taxRate]);
  const da = useMemo(() => yr1Revenue * deprRatio, [yr1Revenue, deprRatio]);
  const capex = useMemo(() => yr1Revenue * capexRatio, [yr1Revenue, capexRatio]);
  const nwcChange = useMemo(() => yr1Revenue * nwcRatio, [yr1Revenue, nwcRatio]);
  const fcf = useMemo(() => nopat + da - capex - nwcChange, [nopat, da, capex, nwcChange]);
  const fcfMargin = useMemo(() => yr1Revenue > 0 ? fcf / yr1Revenue : 0, [fcf, yr1Revenue]);

  // Override check helper
  const isOvr = (key: string) => key in overrides;

  return (
    <div className={styles.container}>
      {/* FCF Margin — prominent display */}
      <div className={styles.formulaDisplay}>
        <span className={styles.formulaLabel}>Implied Free Cash Flow Margin (Year 1)</span>
        <span className={`${styles.formulaValue} ${fcfMargin < 0 ? styles.formulaValueNeg : ''}`}>
          {fmtPct(fcfMargin)}%
        </span>
        <span className={styles.formulaEquation}>
          FCF = NOPAT + D&A &minus; CapEx &minus; &Delta;NWC = {fmtDollarCompact(fcf)}
        </span>
      </div>

      {/* Sub-section 1: Revenue */}
      <div className={styles.subSection}>
        <div className={styles.subSectionTitle}>Revenue</div>

        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Base Revenue (LTM)</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly}`}>
            {fmtDollarCompact(baseRevenue)}
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From financials</span>
        </div>

        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Year 1 Growth</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly}`}>
            {fmtPct(revenueGrowth)}%
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From scenario</span>
        </div>

        <div className={styles.computedResult}>
          <span className={styles.computedPrefix}>&rarr;</span>
          <span className={styles.computedLabel}>Year 1 Revenue</span>
          <span className={styles.computedValue}>{fmtDollarCompact(yr1Revenue)}</span>
        </div>
      </div>

      {/* Sub-section 2: Profitability */}
      <div className={styles.subSection}>
        <div className={styles.subSectionTitle}>Profitability</div>

        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Operating Margin</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly}`}>
            {fmtPct(opMargin)}%
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From scenario</span>
        </div>

        <div className={styles.computedResult}>
          <span className={styles.computedPrefix}>&rarr;</span>
          <span className={styles.computedLabel}>EBIT</span>
          <span className={styles.computedValue}>{fmtDollarCompact(ebit)}</span>
          <span className={styles.computedFormula}>Revenue &times; Op Margin</span>
        </div>

        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Tax Rate</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly}`}>
            {fmtPct(taxRate)}%
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From scenario</span>
        </div>

        <div className={styles.computedResult}>
          <span className={styles.computedPrefix}>&rarr;</span>
          <span className={styles.computedLabel}>NOPAT</span>
          <span className={styles.computedValue}>{fmtDollarCompact(nopat)}</span>
          <span className={styles.computedFormula}>EBIT &times; (1 &minus; t)</span>
        </div>
      </div>

      {/* Sub-section 3: Cash Flow Adjustments */}
      <div className={styles.subSection}>
        <div className={styles.subSectionTitle}>Cash Flow Adjustments</div>

        {/* D&A / Revenue — editable */}
        <div className={`${styles.fieldRow} ${isOvr('model_assumptions.dcf.depreciation_to_revenue') ? styles.fieldRowOverridden : ''}`}>
          <span className={styles.fieldLabel}>D&A / Revenue</span>
          <InlineInput
            value={deprRatio}
            unit="%"
            isOverridden={isOvr('model_assumptions.dcf.depreciation_to_revenue')}
            onChange={(v) => onOverride('model_assumptions.dcf.depreciation_to_revenue', v)}
            sliderMin={0} sliderMax={0.20} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>+{fmtDollarCompact(da)}</span>
        </div>

        {/* CapEx / Revenue — editable */}
        <div className={`${styles.fieldRow} ${isOvr('model_assumptions.dcf.capex_to_revenue') ? styles.fieldRowOverridden : ''}`}>
          <span className={styles.fieldLabel}>CapEx / Revenue</span>
          <InlineInput
            value={capexRatio}
            unit="%"
            isOverridden={isOvr('model_assumptions.dcf.capex_to_revenue')}
            onChange={(v) => onOverride('model_assumptions.dcf.capex_to_revenue', v)}
            sliderMin={0} sliderMax={0.25} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>&minus;{fmtDollarCompact(capex)}</span>
        </div>

        {/* NWC Change / Revenue — editable */}
        <div className={`${styles.fieldRow} ${isOvr('model_assumptions.dcf.nwc_change_to_revenue') ? styles.fieldRowOverridden : ''}`}>
          <span className={styles.fieldLabel}>NWC Change / Revenue</span>
          <InlineInput
            value={nwcRatio}
            unit="%"
            isOverridden={isOvr('model_assumptions.dcf.nwc_change_to_revenue')}
            onChange={(v) => onOverride('model_assumptions.dcf.nwc_change_to_revenue', v)}
            sliderMin={-0.10} sliderMax={0.15} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>&minus;{fmtDollarCompact(nwcChange)}</span>
        </div>

        {/* → FCF — computed */}
        <div className={styles.computedResult}>
          <span className={styles.computedPrefix}>&rarr;</span>
          <span className={styles.computedLabel}>Free Cash Flow</span>
          <span className={`${styles.computedValue} ${fcf < 0 ? styles.computedValueNeg : ''}`}>
            {fmtDollarCompact(fcf)}
          </span>
          <span className={styles.computedFormula}>NOPAT + D&A &minus; CapEx &minus; &Delta;NWC</span>
        </div>

        {/* → FCF Margin — computed */}
        <div className={styles.computedResult}>
          <span className={styles.computedPrefix}>&rarr;</span>
          <span className={styles.computedLabel}>FCF Margin</span>
          <span className={`${styles.computedValue} ${fcfMargin < 0 ? styles.computedValueNeg : ''}`}>
            {fmtPct(fcfMargin)}%
          </span>
          <span className={styles.computedFormula}>FCF / Revenue</span>
        </div>
      </div>
    </div>
  );
}
