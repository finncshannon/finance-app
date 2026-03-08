import { useUIStore } from '../../../stores/uiStore';
import type { ScannerRow, MetricDefinition } from '../types';
import { formatMetricValue } from '../types';
import styles from './DetailPanel.module.css';

interface DetailPanelProps {
  row: ScannerRow;
  metricsMap: Map<string, MetricDefinition>;
}

const KEY_METRICS = [
  'current_price',
  'market_cap',
  'enterprise_value',
  'pe_trailing',
  'ev_to_ebitda',
  'roe',
  'revenue_growth',
  'operating_margin',
  'free_cash_flow',
];

const KEY_METRIC_LABELS: Record<string, string> = {
  current_price: 'Price',
  market_cap: 'Market Cap',
  enterprise_value: 'EV',
  pe_trailing: 'P/E',
  ev_to_ebitda: 'EV/EBITDA',
  roe: 'ROE',
  revenue_growth: 'Rev Growth',
  operating_margin: 'Op Margin',
  free_cash_flow: 'FCF',
};

export function DetailPanel({ row, metricsMap }: DetailPanelProps) {
  const setActiveModule = useUIStore((s) => s.setActiveModule);

  return (
    <div className={styles.panel}>
      <div className={styles.headerLine}>
        <span className={styles.tickerName}>{row.ticker}</span>
        {row.company_name && <> &mdash; {row.company_name}</>}
        {(row.sector || row.industry) && (
          <span className={styles.sectorTag}>
            {' '}
            &middot; {row.sector}
            {row.industry && <> &middot; {row.industry}</>}
          </span>
        )}
      </div>

      <div className={styles.metricsGrid}>
        {KEY_METRICS.map((key) => {
          const def = metricsMap.get(key);
          const value = row.metrics[key];
          const format = def?.format ?? 'default';
          const label = KEY_METRIC_LABELS[key] ?? def?.label ?? key;

          return (
            <div key={key} className={styles.metricItem}>
              <span className={styles.metricLabel}>{label}</span>
              <span className={styles.metricValue}>
                {formatMetricValue(value, format)}
              </span>
            </div>
          );
        })}
      </div>

      <div className={styles.actions}>
        <button
          className={styles.actionBtn}
          onClick={() => setActiveModule('model-builder')}
        >
          Open in Model Builder
        </button>
        <button
          className={styles.actionBtn}
          onClick={() => setActiveModule('research')}
        >
          Open in Research
        </button>
      </div>
    </div>
  );
}
