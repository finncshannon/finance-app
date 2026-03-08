import { useState, useEffect, useCallback } from 'react';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import type { ModelOverviewResult } from '../../../types/models';
import { displayModelName } from '../../../utils/displayNames';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import { FootballField } from './FootballField';
import { WeightsPanel } from './WeightsPanel';
import { AgreementPanel } from './AgreementPanel';
import { ScenarioTable } from './ScenarioTable';
import styles from './OverviewTab.module.css';

function formatPrice(v: number): string {
  return `$${v.toFixed(2)}`;
}

function formatUpside(v: number | null): string {
  if (v == null) return '--';
  const pct = v * 100;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

export function OverviewTab() {
  const activeTicker = useModelStore((s) => s.activeTicker);

  const [data, setData] = useState<ModelOverviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async (ticker: string) => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await api.post<ModelOverviewResult>(
        `/api/v1/model-builder/${ticker}/overview`,
        {},
      );
      setData(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load overview';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTicker) {
      void fetchOverview(activeTicker);
    } else {
      setData(null);
      setError(null);
    }
  }, [activeTicker, fetchOverview]);

  // No ticker
  if (!activeTicker) {
    return (
      <div className={styles.empty}>
        Select a ticker to view the model overview.
      </div>
    );
  }

  // Loading
  if (loading) {
    return (
      <div className={styles.loading}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Loading overview for {activeTicker}...</span>
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <div className={styles.error}>
        <span className={styles.errorText}>{error}</span>
        <button
          className={styles.retryBtn}
          onClick={() => void fetchOverview(activeTicker)}
        >
          Retry
        </button>
      </div>
    );
  }

  // No data
  if (!data) return null;

  const upsidePct = data.composite_upside_pct;
  const upsideClass = upsidePct != null && upsidePct >= 0 ? styles.upsidePositive : styles.upsideNegative;

  return (
    <div className={styles.container}>
      {/* Composite summary bar */}
      <div className={styles.compositeSummary}>
        <span className={styles.compositeLabel}>Composite</span>
        <span className={styles.compositePrice}>{formatPrice(data.composite_base)}</span>
        <span className={`${styles.compositeUpside} ${upsideClass}`}>
          {formatUpside(upsidePct)}
        </span>

        <div className={styles.compositeRange}>
          <span className={styles.rangeLabel}>Bear</span>
          {formatPrice(data.composite_bear)}
          <span className={styles.rangeSeparator}>/</span>
          <span className={styles.rangeLabel}>Bull</span>
          {formatPrice(data.composite_bull)}
        </div>

        <div className={styles.currentPrice}>
          <span className={styles.rangeLabel}>Price</span>
          <span className={styles.currentPriceValue}>{formatPrice(data.current_price)}</span>
        </div>
      </div>

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className={styles.warnings}>
          {data.warnings.map((w, i) => (
            <div key={i} className={styles.warning}>
              <span className={styles.warningIcon}>!</span>
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Models included */}
      <div className={styles.modelsList}>
        <span>Models:</span>
        {data.included_models.map((m) => (
          <span key={m} className={styles.modelTag}>{displayModelName(m)}</span>
        ))}
        {data.excluded_models.length > 0 && (
          <span style={{ color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
            ({data.excluded_models.map((m) => displayModelName(m)).join(', ')} excluded)
          </span>
        )}
      </div>

      {/* Scenario table (full width) */}
      <div className={`${styles.gridRow} ${styles.gridFull}`}>
        <div className={styles.card}>
          <ScenarioTable data={data.scenario_table} />
        </div>
      </div>

      {/* Weights (40%) + Agreement (60%) */}
      <div className={`${styles.gridRow} ${styles.gridMiddle}`}>
        <div className={styles.card}>
          <WeightsPanel data={data.model_weights} />
        </div>
        <div className={styles.card}>
          <AgreementPanel data={data.agreement} />
        </div>
      </div>

      {/* Football Field (full width, bottom) */}
      <div className={`${styles.gridRow} ${styles.gridFull}`}>
        <div className={styles.card}>
          <FootballField
            data={data.football_field}
            currentPrice={data.current_price}
            compositeUpsidePct={data.composite_upside_pct}
            agreement={{
              level: data.agreement.level,
              highest_model: data.agreement.highest_model,
              highest_price: data.agreement.highest_price,
              lowest_model: data.agreement.lowest_model,
              lowest_price: data.agreement.lowest_price,
            }}
          />
        </div>
      </div>
    </div>
  );
}
