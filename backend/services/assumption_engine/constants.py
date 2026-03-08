"""All named constants for the Assumption Engine.

Single source of truth — no constants scattered across modules.
"""

# ---------------------------------------------------------------------------
# Revenue Growth (Design Section 2)
# ---------------------------------------------------------------------------

CAGR_WINDOWS = [3, 5, 10]

REGIME_HYPERGROWTH = 0.30
REGIME_HIGH = 0.15
REGIME_MODERATE = 0.05
REGIME_STABLE = 0.00

DEFAULT_TERMINAL_RATE = 0.025
TERMINAL_RATE_FLOOR = 0.00
TERMINAL_RATE_CEILING = 0.05

ANALYST_WEIGHT_DEFAULT = 0.40
ANALYST_WEIGHT_NO_DATA = 0.00

DIVERGENCE_THRESHOLD = 0.10
MIN_YEARS_LONG_WINDOW = 7

FADE_CURVE = "exponential_decay"

LAMBDA_BY_REGIME = {
    "hypergrowth": 0.65,
    "high": 0.50,
    "moderate": 0.35,
    "stable": 0.25,
    "decline": 0.40,
}

# ---------------------------------------------------------------------------
# Margin Projection (Design Section 3)
# ---------------------------------------------------------------------------

MIN_YEARS_FOR_REGRESSION = 5
OUTLIER_Z_THRESHOLD = 2.0
MEAN_REVERSION_YEARS = 5
MARGIN_FLOOR = -0.50
MARGIN_CEILING_GROSS = 0.95
MARGIN_CEILING_OPERATING = 0.70
MARGIN_CEILING_EBITDA = 0.75
MARGIN_CEILING_NET = 0.50
MARGIN_CEILING_FCF = 0.60
SECTOR_CONVERGENCE_YEARS = 7

MARGIN_CEILINGS = {
    "gross": 0.95,
    "operating": 0.70,
    "ebitda": 0.75,
    "net": 0.50,
    "fcf": 0.60,
}

WEIGHT_PROFILE_STABLE = {
    "trend": 0.30, "mean_reversion": 0.40, "sector": 0.30, "guidance": 0.00,
}
WEIGHT_PROFILE_GROWTH = {
    "trend": 0.50, "mean_reversion": 0.20, "sector": 0.30, "guidance": 0.00,
}
WEIGHT_PROFILE_TURNAROUND = {
    "trend": 0.35, "mean_reversion": 0.15, "sector": 0.50, "guidance": 0.00,
}
WEIGHT_PROFILE_LIMITED_DATA = {
    "trend": 0.20, "mean_reversion": 0.20, "sector": 0.60, "guidance": 0.00,
}

BROAD_MARKET_MEDIAN = {
    "gross": 0.40,
    "operating": 0.15,
    "ebitda": 0.20,
    "net": 0.10,
    "fcf": 0.08,
}

# ---------------------------------------------------------------------------
# WACC Calibration (Design Section 4)
# ---------------------------------------------------------------------------

DEFAULT_RISK_FREE_RATE = 0.04
DEFAULT_ERP = 0.055
DEFAULT_BETA = 1.0

BLUME_WEIGHT_RAW = 2 / 3
BLUME_WEIGHT_MARKET = 1 / 3

SIZE_PREMIUM_MICRO = 0.035   # <$300M
SIZE_PREMIUM_SMALL = 0.02    # $300M–$2B
SIZE_PREMIUM_MID = 0.01      # $2B–$10B
SIZE_PREMIUM_LARGE = 0.005   # $10B–$200B
SIZE_PREMIUM_MEGA = 0.00     # >$200B

WACC_FLOOR = 0.05
WACC_CEILING = 0.25

DEFAULT_TAX_RATE = 0.21

# ---------------------------------------------------------------------------
# Scenario Generation (Design Section 5)
# ---------------------------------------------------------------------------

MIN_SPREAD = 0.05
MAX_SPREAD = 0.30
DEFAULT_SPREAD = 0.10

UNCERTAINTY_WEIGHTS = {
    "data_years": 0.20,
    "revenue_volatility": 0.20,
    "margin_volatility": 0.10,
    "growth_trend_consistency": 0.10,
    "analyst_coverage": 0.10,
    "regime_transition": 0.10,
    "leverage": 0.10,
    "divergence": 0.10,
}

DEFAULT_WEIGHTS_LOW_UNCERTAINTY = {"base": 0.50, "bull": 0.25, "bear": 0.25}
DEFAULT_WEIGHTS_MED_UNCERTAINTY = {"base": 0.45, "bull": 0.275, "bear": 0.275}
DEFAULT_WEIGHTS_HIGH_UNCERTAINTY = {"base": 0.40, "bull": 0.30, "bear": 0.30}

MARGIN_OPERATING_LEVERAGE = 0.30
WACC_BEAR_PREMIUM = 0.005
WACC_BULL_DISCOUNT = 0.0025

# ---------------------------------------------------------------------------
# Industry Benchmark Defaults
# ---------------------------------------------------------------------------

BROAD_MARKET_DEFAULTS = {
    "median_gross_margin": 0.40,
    "median_operating_margin": 0.15,
    "median_ebitda_margin": 0.20,
    "median_net_margin": 0.10,
    "median_fcf_margin": 0.08,
    "median_ev_ebitda": 12.0,
    "median_pe": 18.0,
    "median_ps": 2.5,
    "median_pb": 2.5,
    "median_beta": 1.0,
    "median_revenue_growth": 0.05,
}

# Sector-level benchmark overrides (supplement BROAD_MARKET_DEFAULTS)
SECTOR_BENCHMARKS: dict[str, dict[str, float]] = {
    "Technology": {
        "median_gross_margin": 0.55,
        "median_operating_margin": 0.20,
        "median_ebitda_margin": 0.25,
        "median_net_margin": 0.15,
        "median_fcf_margin": 0.15,
        "median_ev_ebitda": 18.0,
        "median_pe": 25.0,
        "median_ps": 5.0,
        "median_pb": 5.0,
        "median_beta": 1.15,
        "median_revenue_growth": 0.10,
    },
    "Healthcare": {
        "median_gross_margin": 0.55,
        "median_operating_margin": 0.12,
        "median_ebitda_margin": 0.18,
        "median_net_margin": 0.08,
        "median_fcf_margin": 0.10,
        "median_ev_ebitda": 15.0,
        "median_pe": 22.0,
        "median_ps": 4.0,
        "median_pb": 3.5,
        "median_beta": 0.90,
        "median_revenue_growth": 0.08,
    },
    "Financial Services": {
        "median_gross_margin": 0.60,
        "median_operating_margin": 0.25,
        "median_ebitda_margin": 0.30,
        "median_net_margin": 0.20,
        "median_fcf_margin": 0.15,
        "median_ev_ebitda": 10.0,
        "median_pe": 12.0,
        "median_ps": 3.0,
        "median_pb": 1.2,
        "median_beta": 1.05,
        "median_revenue_growth": 0.05,
    },
    "Consumer Cyclical": {
        "median_gross_margin": 0.35,
        "median_operating_margin": 0.10,
        "median_ebitda_margin": 0.15,
        "median_net_margin": 0.06,
        "median_fcf_margin": 0.06,
        "median_ev_ebitda": 12.0,
        "median_pe": 18.0,
        "median_ps": 1.5,
        "median_pb": 3.0,
        "median_beta": 1.10,
        "median_revenue_growth": 0.06,
    },
    "Consumer Defensive": {
        "median_gross_margin": 0.35,
        "median_operating_margin": 0.12,
        "median_ebitda_margin": 0.16,
        "median_net_margin": 0.08,
        "median_fcf_margin": 0.08,
        "median_ev_ebitda": 14.0,
        "median_pe": 20.0,
        "median_ps": 2.0,
        "median_pb": 4.0,
        "median_beta": 0.70,
        "median_revenue_growth": 0.04,
    },
    "Industrials": {
        "median_gross_margin": 0.30,
        "median_operating_margin": 0.12,
        "median_ebitda_margin": 0.16,
        "median_net_margin": 0.08,
        "median_fcf_margin": 0.07,
        "median_ev_ebitda": 13.0,
        "median_pe": 18.0,
        "median_ps": 2.0,
        "median_pb": 3.0,
        "median_beta": 1.00,
        "median_revenue_growth": 0.05,
    },
    "Energy": {
        "median_gross_margin": 0.40,
        "median_operating_margin": 0.12,
        "median_ebitda_margin": 0.20,
        "median_net_margin": 0.08,
        "median_fcf_margin": 0.06,
        "median_ev_ebitda": 6.0,
        "median_pe": 10.0,
        "median_ps": 1.0,
        "median_pb": 1.5,
        "median_beta": 1.20,
        "median_revenue_growth": 0.03,
    },
    "Utilities": {
        "median_gross_margin": 0.40,
        "median_operating_margin": 0.20,
        "median_ebitda_margin": 0.35,
        "median_net_margin": 0.12,
        "median_fcf_margin": 0.05,
        "median_ev_ebitda": 12.0,
        "median_pe": 16.0,
        "median_ps": 2.5,
        "median_pb": 1.8,
        "median_beta": 0.55,
        "median_revenue_growth": 0.03,
    },
    "Real Estate": {
        "median_gross_margin": 0.55,
        "median_operating_margin": 0.25,
        "median_ebitda_margin": 0.50,
        "median_net_margin": 0.15,
        "median_fcf_margin": 0.10,
        "median_ev_ebitda": 18.0,
        "median_pe": 30.0,
        "median_ps": 6.0,
        "median_pb": 1.5,
        "median_beta": 0.80,
        "median_revenue_growth": 0.04,
    },
    "Communication Services": {
        "median_gross_margin": 0.50,
        "median_operating_margin": 0.15,
        "median_ebitda_margin": 0.25,
        "median_net_margin": 0.10,
        "median_fcf_margin": 0.12,
        "median_ev_ebitda": 12.0,
        "median_pe": 18.0,
        "median_ps": 3.0,
        "median_pb": 2.5,
        "median_beta": 1.00,
        "median_revenue_growth": 0.06,
    },
    "Basic Materials": {
        "median_gross_margin": 0.30,
        "median_operating_margin": 0.12,
        "median_ebitda_margin": 0.18,
        "median_net_margin": 0.08,
        "median_fcf_margin": 0.06,
        "median_ev_ebitda": 8.0,
        "median_pe": 14.0,
        "median_ps": 1.5,
        "median_pb": 1.8,
        "median_beta": 1.10,
        "median_revenue_growth": 0.04,
    },
}

# High-growth industries for terminal growth adjustment
HIGH_GROWTH_INDUSTRIES = {
    "Software—Application", "Software—Infrastructure",
    "Semiconductors", "Internet Content & Information",
    "Biotechnology", "Medical Devices",
    "Solar", "Specialty Industrial Machinery",
}

# Declining industries for terminal growth adjustment
DECLINING_INDUSTRIES = {
    "Thermal Coal", "Tobacco", "Department Stores",
    "Broadcasting", "Publishing",
}

# ---------------------------------------------------------------------------
# Monte Carlo Defaults (Session 8G)
# ---------------------------------------------------------------------------
MC_DEFAULT_TRIALS = 100
MC_MIN_YEARS_FOR_MC = 3  # below this, fall back to deterministic
MC_INDUSTRY_WEIGHT_MIN = 0.15
MC_INDUSTRY_WEIGHT_MAX = 0.45
MC_INDUSTRY_WEIGHT_DEFAULT = 0.30
MC_FADE_LAMBDA_STD = 0.15
MC_MARGIN_CONVERGENCE_MIN = 3
MC_MARGIN_CONVERGENCE_MAX = 10
MC_MARGIN_CONVERGENCE_DEFAULT = 5
MC_ERP_JITTER_STD = 0.005
MC_BETA_JITTER_STD = 0.10
MC_SIZE_PREMIUM_JITTER_STD = 0.0025
