import { useMemo, useState, useRef } from 'react';
import type { FootballFieldResult } from '../../../types/models';
import { displayModelName, displayAgreementLevel } from '../../../utils/displayNames';
import styles from './FootballField.module.css';

interface FootballFieldProps {
  data: FootballFieldResult;
  currentPrice?: number;
  compositeUpsidePct?: number | null;
  agreement?: {
    level: string;
    highest_model: string | null;
    highest_price: number | null;
    lowest_model: string | null;
    lowest_price: number | null;
  };
}

function formatPrice(v: number): string {
  return `$${v.toFixed(2)}`;
}

function formatCompactPrice(v: number): string {
  return `$${v.toFixed(0)}`;
}

function formatUpside(current: number, target: number): string {
  if (current <= 0) return '--';
  const pct = ((target - current) / current) * 100;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

function pctPosition(value: number, min: number, max: number): number {
  const range = max - min;
  if (range <= 0) return 0;
  return ((value - min) / range) * 100;
}

function generateTicks(min: number, max: number): number[] {
  const range = max - min;
  if (range <= 0) return [min];
  const step = range / 4;
  const ticks: number[] = [];
  for (let i = 0; i <= 4; i++) {
    ticks.push(min + step * i);
  }
  return ticks;
}

function getBadgeClass(level: string): string {
  const normalized = level.toUpperCase();
  if (normalized.includes('STRONG') && !normalized.includes('DISAGREE')) return styles.badgeStrong ?? '';
  if (normalized.includes('MODERATE')) return styles.badgeModerate ?? '';
  if (normalized.includes('WEAK')) return styles.badgeWeak ?? '';
  if (normalized.includes('SIGNIFICANT') || normalized.includes('DISAGREE')) return styles.badgeSignificant ?? '';
  return styles.badgeModerate ?? '';
}

export function FootballField({ data, currentPrice, compositeUpsidePct, agreement }: FootballFieldProps) {
  const { models, composite, current_price, chart_min, chart_max } = data;
  const price = currentPrice ?? current_price;

  const ticks = useMemo(() => generateTicks(chart_min, chart_max), [chart_min, chart_max]);
  const priceLineLeft = pctPosition(price, chart_min, chart_max);

  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [mouseX, setMouseX] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const COLLISION_THRESHOLD = 8; // percentage points

  function shouldHideLabel(labelLeft: number, baseLeft: number): boolean {
    return Math.abs(labelLeft - baseLeft) < COLLISION_THRESHOLD;
  }

  function renderTooltip(
    modelName: string,
    bear: number,
    base: number,
    bull: number,
    weight?: number,
    confidence?: number | null,
    isComposite?: boolean,
  ) {
    if (hoveredRow !== modelName) return null;
    const containerWidth = containerRef.current?.offsetWidth ?? 800;
    const tooltipWidth = 200;
    const clampedX = Math.max(tooltipWidth / 2, Math.min(mouseX, containerWidth - tooltipWidth / 2));

    return (
      <div
        className={styles.tooltip}
        style={{ left: clampedX }}
      >
        <div className={styles.tooltipTitle}>
          {isComposite ? 'Composite (Weighted Blend)' : `${displayModelName(modelName)} Model`}
        </div>
        <div className={styles.tooltipDivider} />
        <div className={styles.tooltipRow}>
          <span>Bear:</span>
          <span>{formatPrice(bear)} ({formatUpside(price, bear)})</span>
        </div>
        <div className={styles.tooltipRow}>
          <span>Base:</span>
          <span>{formatPrice(base)} ({formatUpside(price, base)})</span>
        </div>
        <div className={styles.tooltipRow}>
          <span>Bull:</span>
          <span>{formatPrice(bull)} ({formatUpside(price, bull)})</span>
        </div>
        {weight != null && (
          <div className={styles.tooltipRow}>
            <span>Weight:</span>
            <span>{(weight * 100).toFixed(0)}%</span>
          </div>
        )}
        {confidence != null && (
          <div className={styles.tooltipRow}>
            <span>Confidence:</span>
            <span>{confidence.toFixed(0)}</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={styles.container} ref={containerRef}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.title}>Football Field</span>
        <div className={styles.legend}>
          <span>
            <span className={`${styles.legendDot} ${styles.legendDotBear}`} />
            Bear
          </span>
          <span>
            <span className={`${styles.legendDot} ${styles.legendDotBase}`} />
            Base
          </span>
          <span>
            <span className={`${styles.legendDot} ${styles.legendDotBull}`} />
            Bull
          </span>
          <span>
            <span className={`${styles.legendDot} ${styles.legendDotPrice}`} />
            Current
          </span>
        </div>
      </div>

      {/* Scale ticks */}
      <div className={styles.scaleRow}>
        {ticks.map((tick) => (
          <span
            key={tick}
            className={styles.scaleTick}
            style={{ left: `${pctPosition(tick, chart_min, chart_max)}%` }}
          >
            {formatCompactPrice(tick)}
          </span>
        ))}
      </div>

      {/* Chart body with gridlines */}
      <div className={styles.chartBody}>
        {/* Gridlines */}
        {ticks.map((tick) => (
          <div
            key={`gl-${tick}`}
            className={styles.gridline}
            style={{ left: `calc(160px + (100% - 160px - 90px) * ${pctPosition(tick, chart_min, chart_max) / 100})` }}
          />
        ))}

        {/* Model rows */}
        {models.map((row) => {
          const bearLeft = pctPosition(row.bear_price, chart_min, chart_max);
          const baseLeft = pctPosition(row.base_price, chart_min, chart_max);
          const bullLeft = pctPosition(row.bull_price, chart_min, chart_max);
          const barLeft = bearLeft;
          const barWidth = bullLeft - bearLeft;
          const label = displayModelName(row.model_name);
          const weightPct = (row.weight * 100).toFixed(0);
          const hideBear = shouldHideLabel(bearLeft, baseLeft);
          const hideBull = shouldHideLabel(bullLeft, baseLeft);

          return (
            <div key={row.model_name} className={styles.row}>
              <div className={styles.label}>
                <span className={styles.labelName}>{label}</span>
                <span className={styles.labelWeight}>{weightPct}% wt</span>
              </div>
              <div
                className={styles.track}
                onMouseEnter={() => setHoveredRow(row.model_name)}
                onMouseMove={(e) => {
                  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                  setMouseX(e.clientX - rect.left);
                }}
                onMouseLeave={() => setHoveredRow(null)}
              >
                <div
                  className={styles.bar}
                  style={{ left: `${barLeft}%`, width: `${Math.max(barWidth, 0.5)}%` }}
                />
                <div className={styles.baseMarker} style={{ left: `${baseLeft}%` }} />
                <div className={styles.priceLine} style={{ left: `${priceLineLeft}%` }} />

                {/* Price labels on bar */}
                {!hideBear && (
                  <span className={styles.priceOnBar} style={{ left: `${bearLeft}%` }}>
                    {formatCompactPrice(row.bear_price)}
                  </span>
                )}
                <span className={styles.priceOnBarBase} style={{ left: `${baseLeft}%` }}>
                  {formatCompactPrice(row.base_price)}
                </span>
                {!hideBull && (
                  <span className={styles.priceOnBar} style={{ left: `${bullLeft}%` }}>
                    {formatCompactPrice(row.bull_price)}
                  </span>
                )}

                {renderTooltip(row.model_name, row.bear_price, row.base_price, row.bull_price, row.weight, row.confidence_score)}
              </div>
              <div className={styles.priceText}>
                <span className={parseFloat(formatUpside(price, row.base_price)) >= 0 ? styles.upsidePos : styles.upsideNeg}>
                  {formatUpside(price, row.base_price)}
                </span>
              </div>
            </div>
          );
        })}

        {/* Composite row */}
        {composite && (() => {
          const bearLeft = pctPosition(composite.bear_price, chart_min, chart_max);
          const baseLeft = pctPosition(composite.base_price, chart_min, chart_max);
          const bullLeft = pctPosition(composite.bull_price, chart_min, chart_max);
          const barLeft = bearLeft;
          const barWidth = bullLeft - bearLeft;
          const hideBear = shouldHideLabel(bearLeft, baseLeft);
          const hideBull = shouldHideLabel(bullLeft, baseLeft);

          return (
            <div className={`${styles.row} ${styles.rowComposite}`}>
              <div className={styles.label}>
                <span className={`${styles.labelName} ${styles.labelNameComposite}`}>
                  Composite
                </span>
                <span className={styles.labelWeight}>blended</span>
              </div>
              <div
                className={`${styles.track} ${styles.trackComposite}`}
                onMouseEnter={() => setHoveredRow('Composite')}
                onMouseMove={(e) => {
                  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                  setMouseX(e.clientX - rect.left);
                }}
                onMouseLeave={() => setHoveredRow(null)}
              >
                <div
                  className={`${styles.bar} ${styles.barComposite}`}
                  style={{ left: `${barLeft}%`, width: `${Math.max(barWidth, 0.5)}%` }}
                />
                <div
                  className={`${styles.baseMarker} ${styles.baseMarkerComposite}`}
                  style={{ left: `${baseLeft}%` }}
                />
                <div className={styles.priceLine} style={{ left: `${priceLineLeft}%` }} />

                {!hideBear && (
                  <span className={styles.priceOnBar} style={{ left: `${bearLeft}%` }}>
                    {formatCompactPrice(composite.bear_price)}
                  </span>
                )}
                <span className={styles.priceOnBarBase} style={{ left: `${baseLeft}%` }}>
                  {formatCompactPrice(composite.base_price)}
                </span>
                {!hideBull && (
                  <span className={styles.priceOnBar} style={{ left: `${bullLeft}%` }}>
                    {formatCompactPrice(composite.bull_price)}
                  </span>
                )}

                {renderTooltip('Composite', composite.bear_price, composite.base_price, composite.bull_price, undefined, undefined, true)}
              </div>
              <div className={`${styles.priceText} ${styles.priceTextComposite}`}>
                <span className={compositeUpsidePct != null && compositeUpsidePct >= 0 ? styles.upsidePos : styles.upsideNeg}>
                  {compositeUpsidePct != null ? `${compositeUpsidePct >= 0 ? '+' : ''}${(compositeUpsidePct * 100).toFixed(1)}%` : '--'}
                </span>
              </div>
            </div>
          );
        })()}
      </div>

      {/* Current price label at bottom */}
      <div className={styles.currentLabel}>
        <div
          className={styles.currentLabelInner}
          style={{ marginLeft: `calc(160px + (100% - 160px - 90px) * ${priceLineLeft / 100})` }}
        >
          Current: {formatPrice(price)}
        </div>
      </div>

      {/* Composite detail summary */}
      {composite && agreement && (
        <div className={styles.compositeSummary}>
          <div className={styles.summaryRow}>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Bear</span>
              <span className={styles.summaryValue}>{formatPrice(composite.bear_price)}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Base</span>
              <span className={styles.summaryValueBold}>{formatPrice(composite.base_price)}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Bull</span>
              <span className={styles.summaryValue}>{formatPrice(composite.bull_price)}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Current</span>
              <span className={styles.summaryValueWarning}>{formatPrice(price)}</span>
            </div>
            <div className={styles.summarySeparator} />
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Spread</span>
              <span className={styles.summaryValue}>
                {formatPrice(composite.bull_price - composite.bear_price)}
                {' '}
                ({price > 0 ? `${(((composite.bull_price - composite.bear_price) / price) * 100).toFixed(1)}%` : '--'})
              </span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Upside</span>
              <span className={compositeUpsidePct != null && compositeUpsidePct >= 0 ? styles.upsidePos : styles.upsideNeg}>
                {compositeUpsidePct != null ? `${compositeUpsidePct >= 0 ? '+' : ''}${(compositeUpsidePct * 100).toFixed(1)}%` : '--'}
              </span>
            </div>
          </div>
          <div className={styles.summaryRow}>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Agreement</span>
              <span className={`${styles.summaryBadge} ${getBadgeClass(agreement.level)}`}>
                {displayAgreementLevel(agreement.level)}
              </span>
            </div>
            {agreement.highest_model && (
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Highest</span>
                <span className={styles.summaryValue}>
                  {displayModelName(agreement.highest_model)}
                  {agreement.highest_price != null ? ` (${formatPrice(agreement.highest_price)})` : ''}
                </span>
              </div>
            )}
            {agreement.lowest_model && (
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Lowest</span>
                <span className={styles.summaryValue}>
                  {displayModelName(agreement.lowest_model)}
                  {agreement.lowest_price != null ? ` (${formatPrice(agreement.lowest_price)})` : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
