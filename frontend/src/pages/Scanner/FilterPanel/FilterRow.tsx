import type { ScannerFilter, MetricDefinition } from '../types';
import { OPERATOR_OPTIONS } from '../types';
import { MetricPicker } from './MetricPicker';
import styles from './FilterRow.module.css';

interface FilterRowProps {
  filter: ScannerFilter;
  metrics: MetricDefinition[];
  categories: Record<string, string[]>;
  onChange: (updated: ScannerFilter) => void;
  onRemove: () => void;
}

function toDisplayValue(internal: number | null | undefined, format: string): string {
  if (internal == null) return '';
  if (format === 'percent') return (internal * 100).toFixed(1);
  return String(internal);
}

function fromDisplayValue(display: string, format: string): number | null {
  if (display === '') return null;
  const num = parseFloat(display);
  if (isNaN(num)) return null;
  if (format === 'percent') return num / 100;
  return num;
}

export function FilterRow({ filter, metrics, categories, onChange, onRemove }: FilterRowProps) {
  const selectedMetric = metrics.find((m) => m.key === filter.metric);
  const metricFormat = selectedMetric?.format ?? 'number';

  const handleMetricChange = (key: string) => {
    onChange({ ...filter, metric: key });
  };

  const handleOperatorChange = (op: string) => {
    const updated: ScannerFilter = { ...filter, operator: op as ScannerFilter['operator'] };
    // Reset value fields when switching operator type
    if (op === 'between') {
      updated.value = null;
      updated.percentile = null;
      updated.low = updated.low ?? null;
      updated.high = updated.high ?? null;
    } else if (op === 'top_pct' || op === 'bot_pct') {
      updated.value = null;
      updated.low = null;
      updated.high = null;
      updated.percentile = updated.percentile ?? null;
    } else {
      updated.low = null;
      updated.high = null;
      updated.percentile = null;
      updated.value = updated.value ?? null;
    }
    onChange(updated);
  };

  const handleValueChange = (raw: string) => {
    onChange({ ...filter, value: fromDisplayValue(raw, metricFormat) });
  };

  const handleLowChange = (raw: string) => {
    onChange({ ...filter, low: fromDisplayValue(raw, metricFormat) });
  };

  const handleHighChange = (raw: string) => {
    onChange({ ...filter, high: fromDisplayValue(raw, metricFormat) });
  };

  const handlePercentileChange = (raw: string) => {
    const val = raw === '' ? null : Math.max(0, Math.min(100, parseFloat(raw) || 0));
    onChange({ ...filter, percentile: val });
  };

  const valuePlaceholder =
    metricFormat === 'percent' ? '15' : metricFormat === 'ratio' ? '12.0' : 'Value';
  const valueTitle =
    metricFormat === 'percent' ? 'Enter 15 for 15%' : undefined;

  const renderValueInputs = () => {
    if (filter.operator === 'between') {
      return (
        <div className={styles.betweenGroup}>
          {metricFormat === 'currency' && <span className={styles.valueSuffix}>$</span>}
          <input
            className={styles.valueInput}
            type="number"
            value={toDisplayValue(filter.low, metricFormat)}
            onChange={(e) => handleLowChange(e.target.value)}
            placeholder="Low"
            title={valueTitle}
            style={{ width: 52 }}
          />
          <span className={styles.betweenSep}>&ndash;</span>
          <input
            className={styles.valueInput}
            type="number"
            value={toDisplayValue(filter.high, metricFormat)}
            onChange={(e) => handleHighChange(e.target.value)}
            placeholder="High"
            title={valueTitle}
            style={{ width: 52 }}
          />
          {metricFormat === 'percent' && <span className={styles.valueSuffix}>%</span>}
          {metricFormat === 'ratio' && <span className={styles.valueSuffix}>x</span>}
        </div>
      );
    }

    if (filter.operator === 'top_pct' || filter.operator === 'bot_pct') {
      return (
        <input
          className={styles.valueInput}
          type="number"
          value={filter.percentile ?? ''}
          onChange={(e) => handlePercentileChange(e.target.value)}
          placeholder="%"
          min={0}
          max={100}
        />
      );
    }

    return (
      <div className={styles.valueGroup}>
        {metricFormat === 'currency' && <span className={styles.valueSuffix}>$</span>}
        <input
          className={styles.valueInput}
          type="number"
          value={toDisplayValue(filter.value, metricFormat)}
          onChange={(e) => handleValueChange(e.target.value)}
          placeholder={valuePlaceholder}
          title={valueTitle}
        />
        {metricFormat === 'percent' && <span className={styles.valueSuffix}>%</span>}
        {metricFormat === 'ratio' && <span className={styles.valueSuffix}>x</span>}
      </div>
    );
  };

  return (
    <div className={styles.row}>
      <div className={styles.metricCol}>
        <MetricPicker
          metrics={metrics}
          categories={categories}
          value={filter.metric}
          onChange={handleMetricChange}
        />
      </div>

      <select
        className={styles.opSelect}
        value={filter.operator}
        onChange={(e) => handleOperatorChange(e.target.value)}
      >
        {OPERATOR_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {renderValueInputs()}

      <button className={styles.removeBtn} onClick={onRemove} type="button" title="Remove filter">
        &#x2715;
      </button>
    </div>
  );
}
