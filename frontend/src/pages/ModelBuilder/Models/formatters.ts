/**
 * Formatting helpers for model view components.
 * All monetary values assumed in raw numbers (not pre-formatted).
 */

/** Format a dollar value with M/B suffix for large numbers, or commas for small. */
export function fmtDollar(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';

  if (abs >= 1e12) {
    return `${sign}$${(abs / 1e12).toFixed(1)}T`;
  }
  if (abs >= 1e9) {
    return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  }
  if (abs >= 1e6) {
    return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  }
  if (abs >= 1e3) {
    return `${sign}$${abs.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  }
  return `${sign}$${abs.toFixed(2)}`;
}

/** Format a decimal as a percentage string. Input 0.052 → "5.2%" */
export function fmtPct(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return `${(v * 100).toFixed(1)}%`;
}

/** Format a multiple value. 25.5 → "25.5x" */
export function fmtMultiple(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return `${v.toFixed(1)}x`;
}

/** Format a number with commas and optional decimal places. */
export function fmtNumber(v: number | null | undefined, decimals = 1): string {
  if (v == null || isNaN(v)) return '—';
  return v.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Format a dollar price for display (e.g., $234.56). */
export function fmtPrice(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return `$${v.toFixed(2)}`;
}

/** Format a discount factor (e.g., 0.953). */
export function fmtFactor(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return v.toFixed(3);
}
