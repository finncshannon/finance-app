import { useState, useEffect, useCallback } from 'react';
import { useModelStore, type ModelType } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import type { DCFResult, DDMResult, CompsResult, RevBasedResult } from '../../../types/models';
import { DCFView } from './DCFView';
import { DDMView } from './DDMView';
import { CompsView } from './CompsView';
import { RevBasedView } from './RevBasedView';
import styles from './ModelTab.module.css';

interface ModelTabProps {
  modelType: ModelType | null;
}

/** Map model type to its API endpoint suffix. */
const MODEL_ENDPOINTS: Record<ModelType, string> = {
  dcf: 'dcf',
  ddm: 'ddm',
  comps: 'comps',
  revenue_based: 'revbased',
};

type ModelResult = DCFResult | DDMResult | CompsResult | RevBasedResult;

export function ModelTab({ modelType }: ModelTabProps) {
  const activeTicker = useModelStore((s) => s.activeTicker);

  // Restore cached result on mount if it matches current ticker+model
  const [result, setResultLocal] = useState<ModelResult | null>(() => {
    const { cachedModelResult, cachedModelMeta } = useModelStore.getState();
    if (
      cachedModelMeta &&
      cachedModelMeta.ticker === useModelStore.getState().activeTicker &&
      cachedModelMeta.modelType === modelType &&
      cachedModelResult
    ) {
      return cachedModelResult as ModelResult;
    }
    return null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Wrap setResult to also cache in store
  const setResult = useCallback(
    (r: ModelResult | null) => {
      setResultLocal(r);
      if (r && activeTicker && modelType) {
        useModelStore.getState().setCachedModelResult(activeTicker, modelType, r);
      }
    },
    [activeTicker, modelType],
  );

  const runModel = useCallback(
    async (ticker: string, type: ModelType, body?: Record<string, unknown>) => {
      setLoading(true);
      setError(null);
      setResult(null);

      const endpoint = MODEL_ENDPOINTS[type];
      // Include assumption overrides from the store so model uses user's changes
      const storeOverrides = useModelStore.getState().assumptionOverrides;
      const overridesPayload = storeOverrides && Object.keys(storeOverrides).length > 0
        ? storeOverrides
        : undefined;
      try {
        const data = await api.post<ModelResult & { model_id?: number }>(
          `/api/v1/model-builder/${ticker}/run/${endpoint}`,
          { overrides: overridesPayload, ...body },
        );
        setResult(data);
        // Set activeModelId from response so History/Export work immediately
        if (data.model_id) {
          useModelStore.getState().setActiveModelId(data.model_id);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to run model';
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Re-run when ticker or model type changes (skip if cache matches)
  useEffect(() => {
    if (!activeTicker || !modelType) {
      setResultLocal(null);
      setError(null);
      return;
    }
    const { cachedModelMeta, cachedModelResult } = useModelStore.getState();
    if (
      cachedModelMeta &&
      cachedModelMeta.ticker === activeTicker &&
      cachedModelMeta.modelType === modelType &&
      cachedModelResult
    ) {
      setResultLocal(cachedModelResult as ModelResult);
      return;
    }
    runModel(activeTicker, modelType);
  }, [activeTicker, modelType, runModel]);

  // Comps rerun with peer tickers
  const handleCompsRerun = useCallback(
    (peerTickers: string[]) => {
      if (!activeTicker) return;
      runModel(activeTicker, 'comps', { peer_tickers: peerTickers });
    },
    [activeTicker, runModel],
  );

  // Empty state: no model type selected
  if (!modelType) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>&#9632;</div>
        <span>Select a model type to begin.</span>
      </div>
    );
  }

  // Empty state: no ticker
  if (!activeTicker) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>&#9632;</div>
        <span>Enter a ticker to run the model.</span>
      </div>
    );
  }

  // Loading
  if (loading) {
    return (
      <div className={styles.loading}>
        <LoadingSpinner />
        <span className={styles.loadingText}>
          Running {modelType.toUpperCase()} model for {activeTicker}...
        </span>
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
          onClick={() => runModel(activeTicker, modelType)}
        >
          Retry
        </button>
      </div>
    );
  }

  // No result yet
  if (!result) {
    return (
      <div className={styles.empty}>
        <span>No results available.</span>
      </div>
    );
  }

  // Route to the correct view
  return (
    <div className={styles.container}>
      {modelType === 'dcf' && <DCFView result={result as DCFResult} />}
      {modelType === 'ddm' && <DDMView result={result as DDMResult} />}
      {modelType === 'comps' && (
        <CompsView result={result as CompsResult} onRerun={handleCompsRerun} />
      )}
      {modelType === 'revenue_based' && <RevBasedView result={result as RevBasedResult} />}
    </div>
  );
}
