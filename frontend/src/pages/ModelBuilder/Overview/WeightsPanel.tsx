import type { ModelWeightResult } from '../../../types/models';
import { displayModelName } from '../../../utils/displayNames';
import styles from './WeightsPanel.module.css';

interface WeightsPanelProps {
  data: ModelWeightResult;
}

export function WeightsPanel({ data }: WeightsPanelProps) {
  const { weights, multipliers, excluded_models, included_model_count } = data;

  // Sort by weight descending
  const sortedEntries = Object.entries(weights).sort(([, a], [, b]) => b - a);

  // Find max weight for relative bar scaling (always show at max = 100% of track width)
  const maxWeight = sortedEntries.length > 0 ? sortedEntries[0]![1]! : 1;

  return (
    <div className={styles.container}>
      <h4 className={styles.title}>Model Weights</h4>

      <div className={styles.rows}>
        {sortedEntries.map(([key, weight]) => {
          const label = displayModelName(key);
          const pct = (weight * 100).toFixed(0);
          const fillPct = maxWeight > 0 ? (weight / maxWeight) * 100 : 0;
          const mult = multipliers[key];

          return (
            <div key={key} className={styles.row}>
              <span className={styles.label}>{label}</span>
              <div className={styles.barTrack}>
                <div
                  className={styles.barFill}
                  style={{ width: `${fillPct}%` }}
                />
              </div>
              <span className={styles.value}>{pct}%</span>
              {mult != null && (
                <span className={styles.multiplier}>{mult.toFixed(1)}x</span>
              )}
            </div>
          );
        })}
      </div>

      <div className={styles.summary}>
        <span>
          Models included: <span className={styles.summaryCount}>{included_model_count}</span>
        </span>
        {excluded_models.length > 0 && (
          <span className={styles.excluded}>
            Excluded: {excluded_models.map((m) => displayModelName(m)).join(', ')}
          </span>
        )}
      </div>
    </div>
  );
}
