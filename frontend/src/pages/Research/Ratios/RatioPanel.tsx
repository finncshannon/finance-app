import type { RatioCategoryDef } from './ratioConfig';
import { formatMetricValue, metricColor } from './ratioConfig';
import styles from './RatioPanel.module.css';

interface RatioPanelProps {
  category: RatioCategoryDef;
  values: Record<string, number | null>;
}

export function RatioPanel({ category, values }: RatioPanelProps) {
  return (
    <div className={styles.card ?? ''}>
      <div className={styles.header ?? ''}>{category.label}</div>
      <div className={styles.rows ?? ''}>
        {category.metrics.map((m) => {
          const val = values[m.key] ?? null;
          return (
            <div key={m.key} className={styles.row ?? ''}>
              <span className={styles.label ?? ''}>{m.label}</span>
              <div>
                <span
                  className={styles.value ?? ''}
                  style={{ color: metricColor(val, m) }}
                >
                  {formatMetricValue(val, m)}
                </span>
                {m.key === 'roe' && val != null && Math.abs(val) > 1.0 && (
                  <span className={styles.extremeNote ?? ''}>
                    Elevated due to {val > 0 ? 'low' : 'negative'} equity (buybacks)
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
