import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import type { SensitivityParameterDef, SliderResult } from '../../../types/models';
import styles from './SlidersPanel.module.css';

/** Parse Python-style format strings: {:.1%}, {:.2%}, {:.1f}x, etc. */
function formatParamValue(value: number, format: string): string {
  const pctMatch = format.match(/\{:\.(\d+)%\}/);
  if (pctMatch) {
    const decimals = parseInt(pctMatch[1]!, 10);
    return `${(value * 100).toFixed(decimals)}%`;
  }
  const floatMatch = format.match(/\{:\.(\d+)f\}(.*)/);
  if (floatMatch) {
    const decimals = parseInt(floatMatch[1]!, 10);
    const suffix = floatMatch[2] ?? '';
    return `${value.toFixed(decimals)}${suffix}`;
  }
  // Legacy fallback
  if (format === 'percentage' || format === 'pct') return `${(value * 100).toFixed(1)}%`;
  if (format === 'currency' || format === 'dollar') return `$${value.toFixed(2)}`;
  if (format === 'multiple' || format === 'x') return `${value.toFixed(1)}x`;
  return value.toFixed(2);
}

function getFormatDecimals(format: string): number {
  const match = format.match(/\.(\d+)/);
  return match ? parseInt(match[1]!, 10) : 1;
}

function isPercentFormat(format: string): boolean {
  return format.includes('%');
}

export function SlidersPanel() {
  const ticker = useModelStore((s) => s.activeTicker);

  // Store-backed state
  const sliderOverrides = useModelStore((s) => s.sliderOverrides);
  const sliderResult = useModelStore((s) => s.sliderResult);
  const setSliderOverride = useModelStore((s) => s.setSliderOverride);
  const setSliderOverrides = useModelStore((s) => s.setSliderOverrides);
  const setSliderResult = useModelStore((s) => s.setSliderResult);

  // Sync methods (from 8D)
  const pushSliderToAssumptions = useModelStore((s) => s.pushSliderToAssumptions);

  // Local-only state
  const [params, setParams] = useState<SensitivityParameterDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [computing, setComputing] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch parameter definitions
  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);

    api
      .get<SensitivityParameterDef[]>(
        `/api/v1/model-builder/${ticker}/sensitivity/parameters`,
      )
      .then((data) => {
        setParams(data);
        // Only seed if store is empty (first load or ticker change)
        if (Object.keys(sliderOverrides).length === 0) {
          const initial: Record<string, number> = {};
          for (const p of data) {
            if (p.current_value != null) {
              initial[p.key_path] = p.current_value;
            }
          }
          setSliderOverrides(initial);
        }
        setLoading(false);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load parameters';
        setError(msg);
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  // Fire slider API call (debounced)
  const fireSlider = useCallback(
    (newOverrides: Record<string, number>) => {
      if (!ticker) return;
      if (debounceRef.current) clearTimeout(debounceRef.current);

      debounceRef.current = setTimeout(() => {
        setComputing(true);
        api
          .post<SliderResult>(
            `/api/v1/model-builder/${ticker}/sensitivity/slider`,
            { overrides: newOverrides },
          )
          .then((data) => {
            setSliderResult(data);
            setComputing(false);
          })
          .catch(() => {
            setComputing(false);
          });
      }, 300);
    },
    [ticker, setSliderResult],
  );

  // Handle slider change
  const handleSliderChange = useCallback(
    (keyPath: string, value: number) => {
      setSliderOverride(keyPath, value);
      fireSlider({ ...sliderOverrides, [keyPath]: value });
    },
    [sliderOverrides, setSliderOverride, fireSlider],
  );

  // Drift detection
  const hasDrift = useMemo(() => {
    return params.some((p) => {
      const override = sliderOverrides[p.key_path];
      return override != null && p.current_value != null && Math.abs(override - p.current_value) > 1e-8;
    });
  }, [params, sliderOverrides]);

  if (!ticker) return null;

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Loading parameters...</span>
      </div>
    );
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  const result = sliderResult;

  const deltaClass =
    result == null
      ? styles.resultDeltaZero
      : result.delta_from_base > 0
        ? styles.resultDeltaPositive
        : result.delta_from_base < 0
          ? styles.resultDeltaNegative
          : styles.resultDeltaZero;

  return (
    <div className={styles.container}>
      {/* Result banner */}
      <div className={styles.resultBanner}>
        <span className={styles.resultLabel}>Implied Price</span>
        <span className={styles.resultPrice}>
          {result ? `$${result.implied_price.toFixed(2)}` : '--'}
        </span>
        <div className={styles.resultDivider} />
        <span className={styles.resultLabel}>Delta</span>
        <span className={`${styles.resultDelta} ${deltaClass}`}>
          {result
            ? `${result.delta_from_base >= 0 ? '+' : ''}$${result.delta_from_base.toFixed(2)} (${result.delta_pct >= 0 ? '+' : ''}${result.delta_pct.toFixed(1)}%)`
            : '--'}
        </span>
        {computing && <LoadingSpinner />}
        {result && (
          <span className={styles.computeTime}>
            {result.computation_time_ms.toFixed(0)}ms
          </span>
        )}
      </div>

      {/* Sync banner */}
      {hasDrift && (
        <div className={styles.syncBanner}>
          <span>Sliders differ from model assumptions.</span>
          <button className={styles.applyBtn} onClick={() => pushSliderToAssumptions()}>
            Apply to Model
          </button>
          <button
            className={styles.resetBtn}
            onClick={() => {
              const current: Record<string, number> = {};
              params.forEach((p) => {
                if (p.current_value != null) current[p.key_path] = p.current_value;
              });
              setSliderOverrides(current);
              setSliderResult(null);
            }}
          >
            Reset to Model
          </button>
        </div>
      )}

      {/* Constraints */}
      {result && result.constraints_enforced.length > 0 && (
        <div className={styles.constraints}>
          {result.constraints_enforced.map((c) => (
            <span key={c} className={styles.constraintTag}>
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Sliders */}
      <div className={styles.slidersList}>
        {params.map((p) => {
          const value = sliderOverrides[p.key_path] ?? p.current_value ?? p.min_val;
          const isPct = isPercentFormat(p.display_format);
          const decimals = getFormatDecimals(p.display_format);
          const displayVal = isPct ? value * 100 : value;
          const stepDisplay = isPct ? p.step * 100 : p.step;

          return (
            <div key={p.key_path} className={styles.sliderRow}>
              <span className={styles.sliderLabel} title={p.key_path}>
                {p.name}
              </span>
              <div className={styles.sliderTrack}>
                {p.current_value != null && (
                  <div
                    className={styles.currentMarker}
                    style={{
                      left: `${((p.current_value - p.min_val) / (p.max_val - p.min_val)) * 100}%`,
                    }}
                    title={`Current: ${formatParamValue(p.current_value, p.display_format)}`}
                  />
                )}
                <input
                  type="range"
                  className={styles.slider}
                  min={p.min_val}
                  max={p.max_val}
                  step={p.step}
                  value={value}
                  onChange={(e) =>
                    handleSliderChange(p.key_path, parseFloat(e.target.value))
                  }
                />
                <div className={styles.sliderRange}>
                  <span>{formatParamValue(p.min_val, p.display_format)}</span>
                  <span>{formatParamValue(p.max_val, p.display_format)}</span>
                </div>
              </div>
              <input
                type="number"
                className={styles.numberInput}
                value={displayVal.toFixed(decimals)}
                step={stepDisplay}
                onChange={(e) => {
                  const raw = parseFloat(e.target.value);
                  if (isNaN(raw)) return;
                  const decimal = isPct ? raw / 100 : raw;
                  const clamped = Math.max(p.min_val, Math.min(p.max_val, decimal));
                  handleSliderChange(p.key_path, clamped);
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
