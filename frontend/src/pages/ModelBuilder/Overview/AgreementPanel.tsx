import type { AgreementAnalysis } from '../../../types/models';
import { displayModelName, displayAgreementLevel } from '../../../utils/displayNames';
import styles from './AgreementPanel.module.css';

interface AgreementPanelProps {
  data: AgreementAnalysis;
}

function formatPrice(v: number | null): string {
  if (v == null) return '--';
  return `$${v.toFixed(2)}`;
}

function formatPct(v: number | null): string {
  if (v == null) return '--';
  return `${(v * 100).toFixed(0)}%`;
}

function getBadgeClass(level: string): string {
  const normalized = level.toUpperCase();
  if (normalized.includes('STRONG') && !normalized.includes('DISAGREE')) return styles.badgeStrong ?? '';
  if (normalized.includes('MODERATE')) return styles.badgeModerate ?? '';
  if (normalized.includes('WEAK')) return styles.badgeWeak ?? '';
  if (normalized.includes('SIGNIFICANT') || normalized.includes('DISAGREE')) return styles.badgeSignificant ?? '';
  return styles.badgeModerate ?? '';
}

export function AgreementPanel({ data }: AgreementPanelProps) {
  const {
    level,
    max_spread,
    max_spread_pct,
    highest_model,
    highest_price,
    lowest_model,
    lowest_price,
    reasoning,
    divergence_matrix,
  } = data;

  return (
    <div className={styles.container}>
      {/* Header with badge */}
      <div className={styles.header}>
        <h4 className={styles.title}>Model Agreement</h4>
        <span className={`${styles.badge} ${getBadgeClass(level)}`}>
          {displayAgreementLevel(level)}
        </span>
      </div>

      {/* Key stats */}
      <div className={styles.stats}>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Spread</span>
          <span className={styles.statValue}>
            {formatPrice(max_spread)} ({formatPct(max_spread_pct)})
          </span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Highest</span>
          <span className={styles.statValue}>
            {highest_model ? displayModelName(highest_model) : '--'} {formatPrice(highest_price)}
          </span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Lowest</span>
          <span className={styles.statValue}>
            {lowest_model ? displayModelName(lowest_model) : '--'} {formatPrice(lowest_price)}
          </span>
        </div>
      </div>

      {/* Reasoning */}
      {reasoning && <p className={styles.reasoning}>{reasoning}</p>}

      {/* Divergence pairs */}
      {divergence_matrix && (divergence_matrix.closest_pair || divergence_matrix.most_divergent_pair) && (
        <div className={styles.divergenceSection}>
          <span className={styles.divergenceTitle}>Divergence</span>

          {divergence_matrix.closest_pair && (
            <div className={styles.divergencePair}>
              <span className={styles.pairLabel}>Closest pair</span>
              <span className={styles.pairModels}>
                {displayModelName(divergence_matrix.closest_pair.model_a)}
                {' / '}
                {displayModelName(divergence_matrix.closest_pair.model_b)}
              </span>
              <span className={`${styles.pairDivergence} ${styles.pairDivergenceClose}`}>
                {(divergence_matrix.closest_pair.divergence_pct * 100).toFixed(1)}%
              </span>
            </div>
          )}

          {divergence_matrix.most_divergent_pair && (
            <div className={styles.divergencePair}>
              <span className={styles.pairLabel}>Most divergent</span>
              <span className={styles.pairModels}>
                {displayModelName(divergence_matrix.most_divergent_pair.model_a)}
                {' / '}
                {displayModelName(divergence_matrix.most_divergent_pair.model_b)}
              </span>
              <span className={`${styles.pairDivergence} ${styles.pairDivergenceFar}`}>
                {(divergence_matrix.most_divergent_pair.divergence_pct * 100).toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
