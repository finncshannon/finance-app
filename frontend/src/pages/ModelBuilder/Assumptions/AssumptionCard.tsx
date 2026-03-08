import { useState, useCallback, useRef, useEffect } from 'react';
import styles from './AssumptionCard.module.css';

type Unit = 'pct' | 'abs' | 'ratio' | 'multiple';

interface AssumptionCardProps {
  label: string;
  value: number;
  unit: Unit;
  confidenceScore?: number;
  reasoning?: string;
  isOverridden?: boolean;
  onChange: (newValue: number) => void;
}

/** Convert internal value to display string. */
function toDisplay(value: number, unit: Unit): string {
  switch (unit) {
    case 'pct':
      return (value * 100).toFixed(1);
    case 'ratio':
      return (value * 100).toFixed(1);
    case 'multiple':
      return value.toFixed(1);
    case 'abs':
    default:
      return value.toFixed(2);
  }
}

/** Convert display string back to internal value. */
function fromDisplay(display: string, unit: Unit): number | null {
  const num = parseFloat(display);
  if (isNaN(num)) return null;
  switch (unit) {
    case 'pct':
    case 'ratio':
      return num / 100;
    case 'multiple':
    case 'abs':
    default:
      return num;
  }
}

/** Unit suffix label */
function unitSuffix(unit: Unit): string {
  switch (unit) {
    case 'pct':
      return '%';
    case 'ratio':
      return '%';
    case 'multiple':
      return 'x';
    case 'abs':
      return '';
  }
}

/** Confidence badge class based on score. */
function confidenceClass(score: number): string {
  if (score >= 80) return styles.confidenceGreen ?? '';
  if (score >= 60) return styles.confidenceYellow ?? '';
  if (score >= 40) return styles.confidenceOrange ?? '';
  return styles.confidenceRed ?? '';
}

export function AssumptionCard({
  label,
  value,
  unit,
  confidenceScore,
  reasoning,
  isOverridden,
  onChange,
}: AssumptionCardProps) {
  const [displayValue, setDisplayValue] = useState(() => toDisplay(value, unit));
  const [showTooltip, setShowTooltip] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync display when external value changes (e.g. regenerate/reset)
  useEffect(() => {
    if (document.activeElement !== inputRef.current) {
      setDisplayValue(toDisplay(value, unit));
    }
  }, [value, unit]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      setDisplayValue(raw);

      const parsed = fromDisplay(raw, unit);
      if (parsed !== null) {
        onChange(parsed);
      }
    },
    [unit, onChange],
  );

  const handleBlur = useCallback(() => {
    // Re-format on blur
    const parsed = fromDisplay(displayValue, unit);
    if (parsed !== null) {
      setDisplayValue(toDisplay(parsed, unit));
    } else {
      // Revert to current value
      setDisplayValue(toDisplay(value, unit));
    }
  }, [displayValue, unit, value]);

  const rowClass = [styles.row, isOverridden ? styles.rowOverridden : '']
    .filter(Boolean)
    .join(' ');

  return (
    <div className={rowClass}>
      {/* Label */}
      <span className={styles.label}>
        {label}
        {isOverridden && <span className={styles.overrideBadge}>Manual</span>}
      </span>

      {/* Input + unit */}
      <div className={styles.inputWrapper}>
        <input
          ref={inputRef}
          className={styles.input}
          type="text"
          inputMode="decimal"
          value={displayValue}
          onChange={handleChange}
          onBlur={handleBlur}
        />
      </div>
      <span className={styles.unit}>{unitSuffix(unit)}</span>

      {/* Confidence badge */}
      {confidenceScore != null ? (
        <span className={`${styles.confidenceBadge} ${confidenceClass(confidenceScore)}`}>
          {confidenceScore}
        </span>
      ) : (
        <span />
      )}

      {/* Reasoning tooltip */}
      {reasoning ? (
        <span
          className={styles.reasoningWrapper}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <span className={styles.reasoningIcon}>i</span>
          {showTooltip && <span className={styles.tooltip}>{reasoning}</span>}
        </span>
      ) : (
        <span />
      )}
    </div>
  );
}
