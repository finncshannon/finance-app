import { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import type { WACCBreakdown } from '../../../types/models';
import styles from './WACCBreakdown.module.css';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WACCBreakdownProps {
  data: WACCBreakdown;
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

function fmtDollarCompact(v: number | null): string {
  if (v == null) return '\u2014';
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  return `${sign}$${abs.toLocaleString()}`;
}

function getSizeTierLabel(marketCap: number | null): string {
  if (!marketCap) return 'Unknown';
  if (marketCap > 200e9) return 'Mega cap (>$200B)';
  if (marketCap > 10e9) return 'Large cap ($10B\u2013$200B)';
  if (marketCap > 2e9) return 'Mid cap ($2B\u2013$10B)';
  if (marketCap > 300e6) return 'Small cap ($300M\u2013$2B)';
  return 'Micro cap (<$300M)';
}

// ---------------------------------------------------------------------------
// Inline editable input
// ---------------------------------------------------------------------------

interface InlineInputProps {
  value: number;
  unit: '%' | 'x' | '';
  isOverridden: boolean;
  onChange: (v: number) => void;
  /** Multiply/divide factor for display (e.g. 100 for percentages) */
  displayFactor?: number;
  decimals?: number;
  /** Slider range (in internal units, not display). Omit to hide slider. */
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
      setLocalVal((num).toFixed(decimals));
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
// WACCBreakdownComponent
// ---------------------------------------------------------------------------

export function WACCBreakdownComponent({
  data,
  overrides,
  onOverride,
}: WACCBreakdownProps) {
  // Read values: overrides first, then data
  const rf = overrides['wacc_breakdown.risk_free_rate'] ?? data.risk_free_rate;
  const rawBeta = overrides['wacc_breakdown.raw_beta'] ?? data.raw_beta;
  const erp = overrides['wacc_breakdown.erp'] ?? data.erp;
  const sizePremium = overrides['wacc_breakdown.size_premium'] ?? data.size_premium;
  const kdPre = overrides['wacc_breakdown.cost_of_debt_pre_tax'] ?? data.cost_of_debt_pre_tax;
  const taxRate = overrides['wacc_breakdown.effective_tax_rate'] ?? data.effective_tax_rate;
  const we = overrides['wacc_breakdown.weight_equity'] ?? data.weight_equity;
  const wd = overrides['wacc_breakdown.weight_debt'] ?? data.weight_debt;

  // Computed values
  const adjustedBeta = useMemo(() => Math.min((2 / 3) * rawBeta + (1 / 3) * 1.0, 2.5), [rawBeta]);
  const costOfEquity = useMemo(() => rf + (adjustedBeta * erp) + sizePremium, [rf, adjustedBeta, erp, sizePremium]);
  const kdAfter = useMemo(() => kdPre * (1 - taxRate), [kdPre, taxRate]);
  const finalWacc = useMemo(() => {
    if (wd === 0) return costOfEquity;
    return (we * costOfEquity) + (wd * kdAfter);
  }, [we, wd, costOfEquity, kdAfter]);

  // Override check helper
  const isOvr = (key: string) => `wacc_breakdown.${key}` in overrides;

  // Linked weight handler
  const handleWeightEquity = useCallback(
    (v: number) => {
      onOverride('wacc_breakdown.weight_equity', v);
      onOverride('wacc_breakdown.weight_debt', 1 - v);
    },
    [onOverride],
  );

  const handleWeightDebt = useCallback(
    (v: number) => {
      onOverride('wacc_breakdown.weight_debt', v);
      onOverride('wacc_breakdown.weight_equity', 1 - v);
    },
    [onOverride],
  );

  // Interest expense (read-only from financial data — not in wacc_breakdown, derive from total_debt × kd_pre)
  const interestExpenseEstimate =
    data.total_debt != null && data.cost_of_debt_pre_tax > 0
      ? data.total_debt * data.cost_of_debt_pre_tax
      : null;

  return (
    <div className={styles.container}>
      {/* Final WACC — prominent display */}
      <div className={styles.formulaDisplay}>
        <span className={styles.formulaLabel}>Weighted Average Cost of Capital</span>
        <span className={styles.formulaValue}>{fmtPct(finalWacc)}%</span>
        <span className={styles.formulaEquation}>
          WACC = ({fmtPct(we)}% &times; {fmtPct(costOfEquity)}%) + ({fmtPct(wd)}% &times; {fmtPct(kdAfter)}%) = {fmtPct(finalWacc)}%
        </span>
      </div>

      {/* Sub-section 1: Cost of Equity (CAPM) */}
      <div className={styles.subSection}>
        <div className={styles.subSectionTitle}>Cost of Equity (CAPM)</div>

        {/* Risk-Free Rate */}
        <div className={`${styles.fieldRow} ${isOvr('risk_free_rate') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Risk-Free Rate</span>
          <InlineInput
            value={rf}
            unit="%"
            isOverridden={isOvr('risk_free_rate')}
            onChange={(v) => onOverride('wacc_breakdown.risk_free_rate', v)}
            sliderMin={0} sliderMax={0.10} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>Current 10Y Treasury</span>
        </div>

        {/* ERP */}
        <div className={`${styles.fieldRow} ${isOvr('erp') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Equity Risk Premium</span>
          <InlineInput
            value={erp}
            unit="%"
            isOverridden={isOvr('erp')}
            onChange={(v) => onOverride('wacc_breakdown.erp', v)}
            sliderMin={0.02} sliderMax={0.10} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>Market consensus</span>
        </div>

        {/* Raw Beta */}
        <div className={`${styles.fieldRow} ${isOvr('raw_beta') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Raw Beta</span>
          <InlineInput
            value={rawBeta}
            unit=""
            isOverridden={isOvr('raw_beta')}
            onChange={(v) => onOverride('wacc_breakdown.raw_beta', v)}
            displayFactor={1}
            sliderMin={0} sliderMax={3} sliderStep={0.01}
          />
          <span className={styles.fieldSource}>From Yahoo Finance</span>
        </div>

        {/* Blume Adjusted Beta — computed, read-only */}
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Blume Adjusted Beta</span>
          <span className={styles.fieldSpacer} />
          <span className={styles.fieldValue}>{adjustedBeta.toFixed(4)}</span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>(2/3 &times; raw + 1/3 &times; 1.0)</span>
        </div>

        {/* Size Premium */}
        <div className={`${styles.fieldRow} ${isOvr('size_premium') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Size Premium</span>
          <InlineInput
            value={sizePremium}
            unit="%"
            isOverridden={isOvr('size_premium')}
            onChange={(v) => onOverride('wacc_breakdown.size_premium', v)}
            sliderMin={0} sliderMax={0.06} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>{getSizeTierLabel(data.market_cap)}</span>
        </div>

        {/* → Cost of Equity — computed result */}
        <div className={styles.computedResult}>
          <span className={styles.computedPrefix}>&rarr;</span>
          <span className={styles.computedLabel}>Cost of Equity</span>
          <span className={styles.computedValue}>{fmtPct(costOfEquity)}%</span>
          <span className={styles.computedFormula}>Rf + &beta;(ERP) + SP</span>
        </div>
      </div>

      {/* Sub-section 2: Cost of Debt */}
      <div className={styles.subSection}>
        <div className={styles.subSectionTitle}>Cost of Debt</div>

        {/* Interest Expense — read-only */}
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Interest Expense</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly ?? ''}`}>
            {fmtDollarCompact(interestExpenseEstimate)}
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From financials</span>
        </div>

        {/* Total Debt — read-only */}
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Total Debt</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly ?? ''}`}>
            {fmtDollarCompact(data.total_debt)}
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From balance sheet</span>
        </div>

        {/* Pre-Tax Cost of Debt */}
        <div className={`${styles.fieldRow} ${isOvr('cost_of_debt_pre_tax') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Pre-Tax Cost of Debt</span>
          <InlineInput
            value={kdPre}
            unit="%"
            isOverridden={isOvr('cost_of_debt_pre_tax')}
            onChange={(v) => onOverride('wacc_breakdown.cost_of_debt_pre_tax', v)}
            sliderMin={0} sliderMax={0.15} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>Interest / Debt</span>
        </div>

        {/* Tax Rate */}
        <div className={`${styles.fieldRow} ${isOvr('effective_tax_rate') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Effective Tax Rate</span>
          <InlineInput
            value={taxRate}
            unit="%"
            isOverridden={isOvr('effective_tax_rate')}
            onChange={(v) => onOverride('wacc_breakdown.effective_tax_rate', v)}
            sliderMin={0} sliderMax={0.50} sliderStep={0.001}
          />
          <span className={styles.fieldSource}>From tax provision</span>
        </div>

        {/* → After-Tax Cost of Debt — computed */}
        <div className={styles.computedResult}>
          <span className={styles.computedPrefix}>&rarr;</span>
          <span className={styles.computedLabel}>After-Tax Cost of Debt</span>
          <span className={styles.computedValue}>{fmtPct(kdAfter)}%</span>
          <span className={styles.computedFormula}>Kd &times; (1 - t)</span>
        </div>
      </div>

      {/* Sub-section 3: Capital Structure */}
      <div className={styles.subSection}>
        <div className={styles.subSectionTitle}>Capital Structure</div>

        {/* Market Cap — read-only */}
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Market Cap</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly ?? ''}`}>
            {fmtDollarCompact(data.market_cap)}
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From market data</span>
        </div>

        {/* Total Debt — read-only */}
        <div className={styles.fieldRow}>
          <span className={styles.fieldLabel}>Total Debt</span>
          <span className={styles.fieldSpacer} />
          <span className={`${styles.fieldValue} ${styles.fieldValueReadonly ?? ''}`}>
            {fmtDollarCompact(data.total_debt)}
          </span>
          <span className={styles.fieldUnit} />
          <span className={styles.fieldSource}>From balance sheet</span>
        </div>

        {/* Equity Weight — editable, linked */}
        <div className={`${styles.fieldRow} ${isOvr('weight_equity') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Equity Weight (E/V)</span>
          <InlineInput
            value={we}
            unit="%"
            isOverridden={isOvr('weight_equity')}
            onChange={handleWeightEquity}
            sliderMin={0} sliderMax={1} sliderStep={0.01}
          />
          <span className={styles.fieldSource} />
        </div>

        {/* Debt Weight — editable, linked */}
        <div className={`${styles.fieldRow} ${isOvr('weight_debt') ? styles.fieldRowOverridden ?? '' : ''}`}>
          <span className={styles.fieldLabel}>Debt Weight (D/V)</span>
          <InlineInput
            value={wd}
            unit="%"
            isOverridden={isOvr('weight_debt')}
            onChange={handleWeightDebt}
            sliderMin={0} sliderMax={1} sliderStep={0.01}
          />
          <span className={styles.fieldSource} />
        </div>

        <div className={styles.linkedNote}>
          Equity and debt weights must sum to 100%
        </div>
      </div>

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className={styles.warningsList}>
          {data.warnings.map((w, i) => (
            <span key={i} className={styles.warningItem}>
              <span className={styles.warningIcon}>&#x26A0;</span>
              {w}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
