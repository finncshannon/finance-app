import { useState, useEffect, useCallback } from 'react';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import type { ModelVersion } from '../../../types/models';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import styles from './HistoryTab.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ModelListItem {
  id: number;
  model_type: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }) + ' ' + d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function formatSize(bytes: number | null): string {
  if (bytes == null) return '\u2014';
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HistoryTab() {
  const activeTicker = useModelStore((s) => s.activeTicker);
  const activeModelId = useModelStore((s) => s.activeModelId);

  const [modelId, setModelId] = useState<number | null>(activeModelId);
  const [versions, setVersions] = useState<ModelVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noModel, setNoModel] = useState(false);

  // Save dialog state
  const [showSave, setShowSave] = useState(false);
  const [annotation, setAnnotation] = useState('');
  const [saving, setSaving] = useState(false);

  // Snapshot viewer state
  const [viewingVersion, setViewingVersion] = useState<ModelVersion | null>(null);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);

  // --- Fetch models for ticker to find model_id ---
  const resolveModelId = useCallback(async (ticker: string): Promise<number | null> => {
    try {
      const models = await api.get<ModelListItem[]>(
        `/api/v1/model-builder/${ticker}/models`,
      );
      const first = models[0];
      if (!first) return null;
      return first.id;
    } catch {
      return null;
    }
  }, []);

  // --- Fetch versions for a model ---
  const fetchVersions = useCallback(async (mId: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<ModelVersion[]>(
        `/api/v1/model-builder/model/${mId}/versions`,
      );
      // Newest first
      const sorted = [...result].sort((a, b) => b.version_number - a.version_number);
      setVersions(sorted);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load versions';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  // --- Initialize ---
  useEffect(() => {
    if (!activeTicker) {
      setVersions([]);
      setModelId(null);
      setNoModel(false);
      return;
    }

    // Use activeModelId from store if available
    if (activeModelId) {
      setModelId(activeModelId);
      setNoModel(false);
      void fetchVersions(activeModelId);
      return;
    }

    // Otherwise resolve from API
    setLoading(true);
    void resolveModelId(activeTicker).then((mId) => {
      if (mId == null) {
        setNoModel(true);
        setModelId(null);
        setLoading(false);
      } else {
        setModelId(mId);
        setNoModel(false);
        void fetchVersions(mId);
      }
    });
  }, [activeTicker, activeModelId, resolveModelId, fetchVersions]);

  // --- Save new version ---
  const handleSave = useCallback(async () => {
    if (!modelId) return;
    setSaving(true);
    try {
      await api.post<ModelVersion>(
        `/api/v1/model-builder/model/${modelId}/save-version`,
        { annotation: annotation.trim() || null },
      );
      setShowSave(false);
      setAnnotation('');
      void fetchVersions(modelId);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save version';
      setError(message);
    } finally {
      setSaving(false);
    }
  }, [modelId, annotation, fetchVersions]);

  // --- View snapshot ---
  const handleView = useCallback(async (version: ModelVersion) => {
    if (!modelId) return;
    setLoadingSnapshot(true);
    try {
      const full = await api.get<ModelVersion>(
        `/api/v1/model-builder/model/${modelId}/version/${version.id}`,
      );
      setViewingVersion(full);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load snapshot';
      setError(message);
    } finally {
      setLoadingSnapshot(false);
    }
  }, [modelId]);

  // --- Load version (restore assumptions) ---
  const handleLoad = useCallback(async (version: ModelVersion) => {
    if (!modelId) return;
    try {
      const full = await api.get<ModelVersion>(
        `/api/v1/model-builder/model/${modelId}/version/${version.id}`,
      );
      // Restore assumptions to modelStore
      const snapshot = full.snapshot as Record<string, unknown> | undefined;
      if (snapshot?.assumptions) {
        useModelStore.getState().setAssumptions(snapshot.assumptions as Record<string, unknown>);
      }
      setViewingVersion(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load version';
      setError(message);
    }
  }, [modelId]);

  // --- No ticker ---
  if (!activeTicker) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyText}>Select a ticker to view version history.</div>
      </div>
    );
  }

  // --- Loading ---
  if (loading) {
    return (
      <div className={styles.loading}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Loading version history...</span>
      </div>
    );
  }

  // --- Error ---
  if (error) {
    return (
      <div className={styles.error}>
        <span className={styles.errorText}>{error}</span>
        <button
          className={styles.retryBtn}
          onClick={() => {
            setError(null);
            if (modelId) void fetchVersions(modelId);
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // --- No model for ticker ---
  if (noModel) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>{'\u25A0'}</div>
        <div className={styles.emptyText}>
          No model found for {activeTicker}. Run a valuation first.
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.title}>Version History</h2>
        <div className={styles.actions}>
          <button
            className={styles.saveBtn}
            onClick={() => setShowSave(true)}
            disabled={showSave || !modelId}
          >
            Save Current
          </button>
          <button className={styles.compareBtn} disabled title="Compare versions — coming soon">
            Compare
          </button>
        </div>
      </div>

      {/* Save dialog */}
      {showSave && (
        <div className={styles.saveDialog}>
          <input
            className={styles.annotationInput}
            type="text"
            placeholder="Add an annotation (optional)..."
            value={annotation}
            onChange={(e) => setAnnotation(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void handleSave();
              if (e.key === 'Escape') {
                setShowSave(false);
                setAnnotation('');
              }
            }}
            autoFocus
          />
          <button
            className={styles.confirmBtn}
            onClick={() => void handleSave()}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            className={styles.cancelBtn}
            onClick={() => {
              setShowSave(false);
              setAnnotation('');
            }}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Version table or empty state */}
      {versions.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>{'\u25A0'}</div>
          <div className={styles.emptyText}>
            No versions saved yet. Save your first version to start tracking changes.
          </div>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Version</th>
                <th>Date</th>
                <th>Annotation</th>
                <th>Size</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>
                    <span className={styles.versionNum}>v{v.version_number}</span>
                  </td>
                  <td className={styles.dateCell}>{formatDate(v.created_at)}</td>
                  <td className={styles.annotationCell}>
                    {v.annotation || '\u2014'}
                  </td>
                  <td className={styles.sizeCell}>
                    {formatSize(v.snapshot_size_bytes)}
                  </td>
                  <td>
                    <div className={styles.actions}>
                      <button
                        className={styles.actionBtn}
                        onClick={() => void handleLoad(v)}
                      >
                        Load
                      </button>
                      <button
                        className={styles.actionBtn}
                        onClick={() => void handleView(v)}
                        disabled={loadingSnapshot}
                      >
                        View
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Snapshot viewer modal */}
      {viewingVersion && (
        <div
          className={styles.snapshotOverlay}
          onClick={() => setViewingVersion(null)}
        >
          <div
            className={styles.snapshotModal}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.snapshotHeader}>
              <h3 className={styles.snapshotTitle}>
                Version {viewingVersion.version_number}
                {viewingVersion.annotation ? ` \u2014 ${viewingVersion.annotation}` : ''}
              </h3>
              <button
                className={styles.closeBtn}
                onClick={() => setViewingVersion(null)}
              >
                Close
              </button>
            </div>
            <div className={styles.snapshotBody}>
              {(() => {
                const snapshot = viewingVersion.snapshot as Record<string, any> | undefined;
                const output = snapshot?.output;
                const modelInfo = snapshot?.model;
                if (!snapshot) {
                  return (
                    <pre className={styles.snapshotJson}>
                      {viewingVersion.snapshot_blob ?? 'No snapshot data available.'}
                    </pre>
                  );
                }
                return (
                  <div className={styles.snapshotFormatted}>
                    <div className={styles.snapshotSection}>
                      <span className={styles.snapshotSectionTitle}>Model</span>
                      <div className={styles.snapshotRow}>
                        <span>Type:</span><span>{modelInfo?.model_type ?? '\u2014'}</span>
                      </div>
                      <div className={styles.snapshotRow}>
                        <span>Ticker:</span><span>{modelInfo?.ticker ?? '\u2014'}</span>
                      </div>
                    </div>
                    {output && (
                      <div className={styles.snapshotSection}>
                        <span className={styles.snapshotSectionTitle}>Key Outputs</span>
                        <div className={styles.snapshotRow}>
                          <span>Implied Price:</span>
                          <span>${(output.intrinsic_value_per_share ?? 0).toFixed(2)}</span>
                        </div>
                        <div className={styles.snapshotRow}>
                          <span>Enterprise Value:</span>
                          <span>${((output.enterprise_value ?? 0) / 1e9).toFixed(2)}B</span>
                        </div>
                      </div>
                    )}
                    <details className={styles.rawDetails}>
                      <summary>Raw JSON</summary>
                      <pre className={styles.snapshotJson}>
                        {JSON.stringify(snapshot, null, 2)}
                      </pre>
                    </details>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
