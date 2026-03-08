"""Monte Carlo simulation — correlated multi-parameter DCF simulation."""

from __future__ import annotations

import logging
import math
import time

import numpy as np

from engines.engine_utils import extend_to_10_years, clamp
from services.assumption_engine.models import AssumptionSet

from .models import (
    MonteCarloResult, MCStatistics, MCHistogram, HistogramBin,
    MCParameterConfig,
)

logger = logging.getLogger("finance_app")

# Named constants
MC_DEFAULT_ITERATIONS = 10_000
MC_HISTOGRAM_BINS = 50
MC_NAN_SKIP_THRESHOLD = 0.05

# Correlation matrix (6 correlated params; tax is independent)
# Order: WACC, TermGrowth, RevGrowth, OpMargin, CapEx, ExitMult
CORRELATION_MATRIX = np.array([
    [ 1.00, -0.10, -0.25, -0.15,  0.05, -0.20],
    [-0.10,  1.00,  0.30,  0.10,  0.05,  0.15],
    [-0.25,  0.30,  1.00,  0.40,  0.30,  0.35],
    [-0.15,  0.10,  0.40,  1.00,  0.00,  0.25],
    [ 0.05,  0.05,  0.30,  0.00,  1.00,  0.05],
    [-0.20,  0.15,  0.35,  0.25,  0.05,  1.00],
], dtype=np.float64)


def run_monte_carlo(
    assumption_set: AssumptionSet,
    data: dict,
    current_price: float,
    iterations: int = MC_DEFAULT_ITERATIONS,
    seed: int | None = None,
) -> MonteCarloResult:
    """Run Monte Carlo simulation on DCF model.

    Draws 8 correlated/independent parameters from calibrated
    distributions, runs fast_dcf per iteration, computes statistics.
    """
    t0 = time.perf_counter()
    scenarios = assumption_set.scenarios
    dcf = assumption_set.model_assumptions.dcf

    if scenarios is None or dcf is None:
        return MonteCarloResult(
            success=False,
            error="Missing scenarios or DCF assumptions",
            iteration_count=0,
            valid_iterations=0,
            skipped_iterations=0,
            computation_time_ms=0,
        )

    base = scenarios.base
    bull = scenarios.bull
    bear = scenarios.bear

    # --- Extract base parameters ---
    base_wacc = base.wacc
    base_tg = base.terminal_growth_rate
    base_rg = list(base.revenue_growth_rates[:5])
    base_om = list(base.operating_margins[:5])
    base_tax = base.tax_rate
    base_capex = dcf.capex_to_revenue
    base_da = dcf.depreciation_to_revenue
    base_nwc = dcf.nwc_change_to_revenue
    base_exit = dcf.terminal_exit_multiple or 12.0
    base_revenue = dcf.base_revenue or 0
    net_debt = dcf.net_debt or 0
    shares = dcf.shares_outstanding or 1
    terminal_method = dcf.terminal_method

    # Pad arrays to 5
    while len(base_rg) < 5:
        base_rg.append(base_rg[-1] if base_rg else 0.05)
    while len(base_om) < 5:
        base_om.append(base_om[-1] if base_om else 0.15)

    bull_rg = list(bull.revenue_growth_rates[:5])
    bear_rg = list(bear.revenue_growth_rates[:5])
    bull_om = list(bull.operating_margins[:5])
    bear_om = list(bear.operating_margins[:5])
    while len(bull_rg) < 5:
        bull_rg.append(bull_rg[-1] if bull_rg else 0.05)
    while len(bear_rg) < 5:
        bear_rg.append(bear_rg[-1] if bear_rg else 0.05)
    while len(bull_om) < 5:
        bull_om.append(bull_om[-1] if bull_om else 0.15)
    while len(bear_om) < 5:
        bear_om.append(bear_om[-1] if bear_om else 0.15)

    # --- Derive standard deviations (bull-bear spread / 4) ---
    sigma_wacc = max(abs(bear.wacc - bull.wacc) / 4, 0.005)
    sigma_tg = max(base_tg * 0.25, 0.002)
    sigma_rg0 = max(abs(bull_rg[0] - bear_rg[0]) / 4, 0.01)
    sigma_rg1 = max(abs(bull_rg[1] - bear_rg[1]) / 4, 0.01)
    sigma_om0 = max(abs(bull_om[0] - bear_om[0]) / 4, 0.01)
    sigma_capex = max(base_capex * 0.20, 0.005)

    # Log-normal for exit multiple
    sigma_ln_exit = 0.20
    mu_ln_exit = math.log(max(base_exit, 1)) - 0.5 * sigma_ln_exit ** 2

    # Record parameter configs
    distributions = [
        MCParameterConfig(name="WACC", distribution="normal", mean=base_wacc, std_dev=sigma_wacc),
        MCParameterConfig(name="Terminal Growth", distribution="normal", mean=base_tg, std_dev=sigma_tg),
        MCParameterConfig(name="Revenue Growth Y1", distribution="normal", mean=base_rg[0], std_dev=sigma_rg0),
        MCParameterConfig(name="Revenue Growth Y2", distribution="normal", mean=base_rg[1], std_dev=sigma_rg1),
        MCParameterConfig(name="Operating Margin Y1", distribution="normal", mean=base_om[0], std_dev=sigma_om0),
        MCParameterConfig(name="Tax Rate", distribution="triangular", mode=base_tax,
                          min_val=base_tax * 0.80, max_val=base_tax * 1.20),
        MCParameterConfig(name="CapEx / Revenue", distribution="normal", mean=base_capex, std_dev=sigma_capex),
        MCParameterConfig(name="Exit Multiple", distribution="lognormal", mean=mu_ln_exit, std_dev=sigma_ln_exit),
    ]

    # --- Generate correlated draws ---
    rng = np.random.default_rng(seed)

    # Cholesky decomposition of correlation matrix
    try:
        L = np.linalg.cholesky(CORRELATION_MATRIX)
    except np.linalg.LinAlgError:
        # Fallback: use identity (uncorrelated)
        L = np.eye(6)

    # Draw standard normals: (iterations, 6) for correlated params
    Z = rng.standard_normal((iterations, 6))
    correlated_Z = Z @ L.T

    # Independent draws for tax (triangular) and revenue growth Y2
    tax_draws = rng.triangular(
        max(base_tax * 0.80, 0), base_tax, min(base_tax * 1.20, 0.45),
        size=iterations,
    )
    rg1_Z = rng.standard_normal(iterations)

    # --- Transform to target distributions ---
    wacc_draws = np.clip(base_wacc + correlated_Z[:, 0] * sigma_wacc, 0.01, 0.30)
    tg_draws = np.clip(base_tg + correlated_Z[:, 1] * sigma_tg, 0.0, 0.05)
    rg0_draws = np.clip(base_rg[0] + correlated_Z[:, 2] * sigma_rg0, -0.30, 1.00)
    om0_draws = np.clip(base_om[0] + correlated_Z[:, 3] * sigma_om0, -0.50, 0.70)
    capex_draws = np.clip(base_capex + correlated_Z[:, 4] * sigma_capex, 0.005, 0.30)
    exit_draws = np.clip(np.exp(mu_ln_exit + correlated_Z[:, 5] * sigma_ln_exit), 2.0, 50.0)

    rg1_draws = np.clip(base_rg[1] + rg1_Z * sigma_rg1, -0.30, 1.00)
    tax_draws = np.clip(tax_draws, 0.0, 0.45)

    # Cap terminal growth at wacc - 0.01
    tg_draws = np.minimum(tg_draws, wacc_draws - 0.01)

    # --- Run fast DCF for each iteration ---
    prices = np.empty(iterations, dtype=np.float64)
    valid = 0
    skipped = 0

    for i in range(iterations):
        wacc_i = float(wacc_draws[i])
        tg_i = float(tg_draws[i])
        rg0_i = float(rg0_draws[i])
        rg1_i = float(rg1_draws[i])
        om0_i = float(om0_draws[i])
        tax_i = float(tax_draws[i])
        capex_i = float(capex_draws[i])
        exit_i = float(exit_draws[i])

        # Build 5-year curves from draws
        rg_5 = _build_growth_curve(base_rg, rg0_i, rg1_i)
        om_5 = _build_margin_curve(base_om, om0_i)

        price_i = _fast_dcf(
            base_revenue=base_revenue,
            rev_growth_5yr=rg_5,
            terminal_growth=tg_i,
            op_margins_5yr=om_5,
            tax_rate=tax_i,
            capex_ratio=capex_i,
            da_ratio=base_da,
            nwc_ratio=base_nwc,
            wacc=wacc_i,
            exit_multiple=exit_i,
            terminal_method=terminal_method,
            net_debt=net_debt,
            shares=shares,
        )

        if math.isnan(price_i) or math.isinf(price_i):
            skipped += 1
            prices[i] = np.nan
        else:
            prices[i] = price_i
            valid += 1

    # --- Check skip threshold ---
    if iterations > 0 and skipped / iterations > MC_NAN_SKIP_THRESHOLD:
        elapsed = (time.perf_counter() - t0) * 1000
        return MonteCarloResult(
            success=False,
            error=f"Too many invalid iterations: {skipped}/{iterations} ({skipped/iterations:.1%})",
            iteration_count=iterations,
            valid_iterations=valid,
            skipped_iterations=skipped,
            seed=seed,
            computation_time_ms=round(elapsed, 1),
        )

    # --- Compute statistics on valid prices ---
    valid_prices = prices[~np.isnan(prices)]

    if len(valid_prices) == 0:
        elapsed = (time.perf_counter() - t0) * 1000
        return MonteCarloResult(
            success=False,
            error="No valid iterations",
            iteration_count=iterations,
            valid_iterations=0,
            skipped_iterations=skipped,
            computation_time_ms=round(elapsed, 1),
        )

    stats = _compute_statistics(valid_prices, current_price)
    histogram = _build_histogram(valid_prices)

    elapsed = (time.perf_counter() - t0) * 1000

    return MonteCarloResult(
        success=True,
        statistics=stats,
        histogram=histogram,
        distributions_used=distributions,
        correlation_matrix=CORRELATION_MATRIX.tolist(),
        iteration_count=iterations,
        valid_iterations=valid,
        skipped_iterations=skipped,
        seed=seed,
        computation_time_ms=round(elapsed, 1),
    )


# ---------------------------------------------------------------------------
# Fast-path DCF (no Pydantic, no waterfall, pure math)
# ---------------------------------------------------------------------------

def _fast_dcf(
    base_revenue: float,
    rev_growth_5yr: list[float],
    terminal_growth: float,
    op_margins_5yr: list[float],
    tax_rate: float,
    capex_ratio: float,
    da_ratio: float,
    nwc_ratio: float,
    wacc: float,
    exit_multiple: float,
    terminal_method: str,
    net_debt: float,
    shares: float,
) -> float:
    """Minimal DCF calculation for Monte Carlo. <0.1ms per call."""
    rev_growth_10 = extend_to_10_years(rev_growth_5yr, terminal_growth)
    om_10 = extend_to_10_years(op_margins_5yr, op_margins_5yr[-1] if op_margins_5yr else 0.15)

    revenue = base_revenue
    pv_fcf = 0.0
    ebitda_final = 0.0
    final_fcf = 0.0

    for t in range(10):
        revenue *= (1 + rev_growth_10[t])
        ebit = revenue * om_10[t]
        da = revenue * da_ratio
        ebitda = ebit + da
        taxes = max(ebit * tax_rate, 0)
        nopat = ebit - taxes
        capex = revenue * capex_ratio
        nwc_change = revenue * nwc_ratio
        fcf = nopat + da - capex - nwc_change

        # Mid-year convention
        pv_fcf += fcf / (1 + wacc) ** (t + 0.5)

        if t == 9:
            ebitda_final = ebitda
            final_fcf = fcf

    # Terminal value
    if wacc <= terminal_growth:
        wacc = terminal_growth + 0.01

    tv_perp = (final_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)

    if terminal_method == "exit_multiple" and exit_multiple > 0:
        tv = ebitda_final * exit_multiple
    elif terminal_method == "both" and exit_multiple > 0:
        tv = (tv_perp + ebitda_final * exit_multiple) / 2
    else:
        tv = tv_perp

    pv_tv = tv / (1 + wacc) ** 10
    equity = pv_fcf + pv_tv - net_debt
    return max(equity / max(shares, 1), 0)


# ---------------------------------------------------------------------------
# Curve builders
# ---------------------------------------------------------------------------

def _build_growth_curve(base_curve: list[float], y1: float, y2: float) -> list[float]:
    """Build 5-year growth curve from Y1/Y2 draws with decay."""
    d1 = y1 - base_curve[0]
    d2 = y2 - base_curve[1]
    return [
        y1,
        y2,
        base_curve[2] + d1 * 0.6 + d2 * 0.2,
        base_curve[3] + d1 * 0.3 + d2 * 0.1,
        base_curve[4] + d1 * 0.1,
    ]


def _build_margin_curve(base_curve: list[float], y1: float) -> list[float]:
    """Build 5-year margin curve from Y1 draw with decay."""
    d = y1 - base_curve[0]
    return [
        y1,
        base_curve[1] + d * 0.8,
        base_curve[2] + d * 0.6,
        base_curve[3] + d * 0.4,
        base_curve[4] + d * 0.2,
    ]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def _compute_statistics(prices: np.ndarray, current_price: float) -> MCStatistics:
    """Compute summary statistics from valid price array."""
    mean_val = float(np.mean(prices))
    median_val = float(np.median(prices))
    std_val = float(np.std(prices))

    pcts = np.percentile(prices, [5, 10, 25, 50, 75, 90, 95])

    n = len(prices)
    prob_upside = float(np.sum(prices > current_price) / n) if current_price > 0 else 0
    prob_up15 = float(np.sum(prices > current_price * 1.15) / n) if current_price > 0 else 0
    prob_dn15 = float(np.sum(prices < current_price * 0.85) / n) if current_price > 0 else 0

    return MCStatistics(
        mean=round(mean_val, 2),
        median=round(median_val, 2),
        std_dev=round(std_val, 2),
        p5=round(float(pcts[0]), 2),
        p10=round(float(pcts[1]), 2),
        p25=round(float(pcts[2]), 2),
        p50=round(float(pcts[3]), 2),
        p75=round(float(pcts[4]), 2),
        p90=round(float(pcts[5]), 2),
        p95=round(float(pcts[6]), 2),
        prob_upside=round(prob_upside, 4),
        prob_upside_15pct=round(prob_up15, 4),
        prob_downside_15pct=round(prob_dn15, 4),
        var_5pct=round(float(pcts[0]), 2),  # VaR at 5th percentile
    )


def _build_histogram(prices: np.ndarray) -> MCHistogram:
    """Build histogram with 50 bins in P1-P99 range."""
    p1, p99 = float(np.percentile(prices, 1)), float(np.percentile(prices, 99))

    # Count outliers
    outlier_low = int(np.sum(prices < p1))
    outlier_high = int(np.sum(prices > p99))

    # Clip to P1-P99 for binning
    clipped = prices[(prices >= p1) & (prices <= p99)]
    if len(clipped) == 0:
        return MCHistogram(range_min=p1, range_max=p99)

    n_bins = MC_HISTOGRAM_BINS
    bin_edges = np.linspace(p1, p99, n_bins + 1)
    counts, _ = np.histogram(clipped, bins=bin_edges)
    total = len(clipped)

    bins = []
    for j in range(n_bins):
        bins.append(HistogramBin(
            bin_start=round(float(bin_edges[j]), 2),
            bin_end=round(float(bin_edges[j + 1]), 2),
            count=int(counts[j]),
            frequency=round(int(counts[j]) / total, 6) if total > 0 else 0,
        ))

    return MCHistogram(
        bins=bins,
        bin_count=n_bins,
        range_min=round(p1, 2),
        range_max=round(p99, 2),
        outlier_count_low=outlier_low,
        outlier_count_high=outlier_high,
    )
