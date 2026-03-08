"""
Automatic Valuation Model Detection - v4.0 COMPLETE REWRITE

CHANGES IN v4.0:
- Complete scoring engine rewrite to fix DCF bias
- Model-specific signals as PRIMARY differentiators
- Shared signals contribute EQUALLY to all models
- Archetype detection (Dividend Aristocrat, Cash Flow Compounder, Growth Disruptor)
- Sector-based nudges (not overrides)
- Robust dividend data checks from multiple sources
- Disqualification caps for inappropriate models

SCORING ARCHITECTURE (approximate max points):
                          DCF    DDM    RevBased   Comps
    Model-specific:        50     55       50         0
    Shared signals:        30     30       30        30
    Archetype bonus:       15     15       15         0
    Sector nudge:          10     10       10        10
    Data availability:      0      0        0        40
    ─────────────────────────────────────────────────────
    MAX POSSIBLE:         105    110      105        80

Each model CAN reach 100+ in its ideal scenario.
"""

import logging
import pandas as pd
from typing import Dict, Any, List, Optional
import config
from excel_helpers import get_df_value

logger = logging.getLogger('StockValuation')


# ============================================================================
# SECTOR NUDGES - Small bonuses based on sector (5-10 points, not overrides)
# ============================================================================

SECTOR_NUDGES = {
    # Sectors where DDM is structurally appropriate
    'Utilities': {'DDM': 10, 'Standard DCF': 5},
    'Real Estate': {'DDM': 10},  # REITs
    'Financial Services': {'DDM': 8, 'Standard DCF': 5},

    # Sectors where DCF is structurally appropriate
    'Technology': {'Standard DCF': 8, 'Revenue-Based': 5},
    'Communication Services': {'Standard DCF': 5, 'Revenue-Based': 5},

    # Sectors where Revenue-Based may apply
    'Healthcare': {'Standard DCF': 5, 'Revenue-Based': 5},  # biotechs vs pharma

    # Neutral sectors
    'Consumer Defensive': {'Standard DCF': 5, 'DDM': 5},
    'Consumer Cyclical': {'Standard DCF': 5},
    'Industrials': {'Standard DCF': 5, 'DDM': 3},
    'Energy': {'Standard DCF': 5, 'DDM': 5},
    'Basic Materials': {'Standard DCF': 5},
}


class ModelDetector:
    """
    Valuation model detector with balanced scoring architecture.

    Version 4.0 - Complete rewrite to fix DCF bias.

    Key changes:
    - Model-specific signals are the PRIMARY differentiators
    - Shared signals contribute EQUALLY to applicable models
    - Archetype detection acts as tiebreaker
    - Sector nudges provide small bonuses (not overrides)
    - Robust dividend checks from multiple data sources
    """

    def __init__(self, data: Dict[str, Any]):
        """Initialize detector with pre-extracted financial data."""
        self.data = data
        self.ticker = data.get('ticker', 'Unknown')
        self.availability = data.get('data_availability', {})
        self.company_info = data.get('company_info', {})
        self.key_metrics = data.get('key_metrics', {})
        self.dividends = data.get('dividends', {})
        self._metrics_cache = None

        # Score tracking
        self.scores = {
            'Standard DCF': 0,
            'DDM': 0,
            'Revenue-Based': 0,
            'Comps': 0
        }
        self.score_breakdown = {
            'Standard DCF': {},
            'DDM': {},
            'Revenue-Based': {},
            'Comps': {}
        }

    def detect_model(self) -> Dict[str, Any]:
        """
        Main detection logic using balanced scoring.

        Scoring order:
        1. Model-specific signals (primary differentiator)
        2. Shared signals (equal contribution)
        3. Archetype detection (tiebreaker)
        4. Sector nudges (small bonuses)
        5. Data availability (Comps fallback)
        6. Apply disqualifiers (caps)
        7. Calculate final scores
        """
        metrics = self._extract_all_metrics()
        self._log_company_profile(metrics)

        logger.info("RUNNING BALANCED SCORING ENGINE (v4.0)")

        # Reset scores
        for model in self.scores:
            self.scores[model] = 0
            self.score_breakdown[model] = {}

        # Step 1: Model-specific signals (PRIMARY)
        logger.debug("[STEP 1] Analyzing model-specific signals...")
        self._analyze_model_specific_signals(metrics)
        self._log_scores("After model-specific signals")

        # Step 2: Shared signals (EQUAL contribution)
        logger.debug("[STEP 2] Analyzing shared signals...")
        self._analyze_shared_signals(metrics)
        self._log_scores("After shared signals")

        # Step 3: Archetype detection (TIEBREAKER)
        logger.debug("[STEP 3] Detecting company archetype...")
        archetype = self._analyze_archetype(metrics)
        self._log_scores("After archetype detection")

        # Step 4: Sector nudges
        logger.debug("[STEP 4] Applying sector nudges...")
        self._analyze_sector(metrics)
        self._log_scores("After sector nudges")

        # Step 5: Data availability (Comps support)
        logger.debug("[STEP 5] Checking data availability...")
        self._analyze_data_availability(metrics)
        self._log_scores("After data availability")

        # Step 6: Apply disqualifiers
        logger.debug("[STEP 6] Applying disqualifiers...")
        self._apply_disqualifiers(metrics)
        self._log_scores("After disqualifiers")

        # Step 7: Calculate final result
        logger.debug("[STEP 7] Calculating final result...")
        result = self._calculate_final_result(metrics, archetype)

        return result

    # ========================================================================
    # STEP 1: MODEL-SPECIFIC SIGNALS (Primary Differentiator)
    # ========================================================================

    def _analyze_model_specific_signals(self, metrics: Dict):
        """
        Analyze signals UNIQUE to each model.
        This is the PRIMARY differentiator.

        DCF-specific (max ~50): FCF yield, FCF consistency, FCF stability, FCF growth
        DDM-specific (max ~55): Dividend yield, consistency, growth, payout sustainability
        Revenue-Based specific (max ~50): High growth, negative FCF, unprofitable
        """

        # === DCF-SPECIFIC SIGNALS (max ~50) ===
        logger.debug("  DCF-Specific Signals:")
        dcf_points = 0

        # FCF Yield (FCF / Market Cap) — use cached value
        market_cap = metrics['market_cap']
        fcf = metrics['fcf_ttm']
        fcf_yield = metrics['fcf_yield']
        if market_cap <= 0:
            logger.warning(f"Market cap is zero for {self.ticker} — FCF yield scoring suppressed")

        if fcf_yield > 0.05:  # >5% FCF yield
            dcf_points += 15
            logger.debug(f"    [+15] FCF yield {fcf_yield:.1%} > 5%")
        elif fcf_yield > 0.03:  # >3% FCF yield
            dcf_points += 10
            logger.debug(f"    [+10] FCF yield {fcf_yield:.1%} > 3%")
        elif fcf_yield > 0.01:  # >1% FCF yield
            dcf_points += 5
            logger.debug(f"    [+5] FCF yield {fcf_yield:.1%} > 1%")
        else:
            logger.debug(f"    [+0] FCF yield {fcf_yield:.1%} (too low)")

        # FCF Consistency (positive years)
        positive_fcf_years = metrics.get('positive_fcf_years', 0)
        if positive_fcf_years >= 4:
            dcf_points += 15
            logger.debug(f"    [+15] {positive_fcf_years} years positive FCF (>=4)")
        elif positive_fcf_years >= 3:
            dcf_points += 10
            logger.debug(f"    [+10] {positive_fcf_years} years positive FCF (>=3)")
        elif positive_fcf_years >= 2:
            dcf_points += 5
            logger.debug(f"    [+5] {positive_fcf_years} years positive FCF (>=2)")
        else:
            logger.debug(f"    [+0] {positive_fcf_years} years positive FCF (too few)")

        # FCF Margin stability
        fcf_margin = metrics['fcf_margin']
        if fcf_margin > 0.15:  # Very strong margin
            dcf_points += 10
            logger.debug(f"    [+10] FCF margin {fcf_margin:.1%} > 15%")
        elif fcf_margin > 0.08:  # Good margin
            dcf_points += 7
            logger.debug(f"    [+7] FCF margin {fcf_margin:.1%} > 8%")
        elif fcf_margin > 0.03:  # Acceptable
            dcf_points += 3
            logger.debug(f"    [+3] FCF margin {fcf_margin:.1%} > 3%")
        else:
            logger.debug(f"    [+0] FCF margin {fcf_margin:.1%} (weak or negative)")

        # FCF Growth
        fcf_growth = metrics.get('fcf_growth', 0)
        if fcf_growth > 0.10:
            dcf_points += 10
            logger.debug(f"    [+10] FCF growth {fcf_growth:.1%} > 10%")
        elif fcf_growth > 0:
            dcf_points += 5
            logger.debug(f"    [+5] FCF growth {fcf_growth:.1%} positive")
        else:
            logger.debug(f"    [+0] FCF growth {fcf_growth:.1%} (flat or declining)")

        self.scores['Standard DCF'] += dcf_points
        self.score_breakdown['Standard DCF']['model_specific'] = dcf_points
        logger.debug(f"    DCF model-specific total: +{dcf_points}")

        # === DDM-SPECIFIC SIGNALS (max ~55) ===
        logger.debug("  DDM-Specific Signals:")
        ddm_points = 0

        # Dividend Yield (from key_metrics - more reliable)
        div_yield = metrics['dividend_yield']
        if div_yield > 0.035:  # >3.5% yield
            ddm_points += 15
            logger.debug(f"    [+15] Dividend yield {div_yield:.2%} > 3.5%")
        elif div_yield > 0.02:  # >2% yield
            ddm_points += 10
            logger.debug(f"    [+10] Dividend yield {div_yield:.2%} > 2%")
        elif div_yield > 0.01:  # >1% yield
            ddm_points += 5
            logger.debug(f"    [+5] Dividend yield {div_yield:.2%} > 1%")
        else:
            logger.debug(f"    [+0] Dividend yield {div_yield:.2%} (too low for DDM)")

        # Dividend consistency (years of payments)
        div_years = metrics.get('dividend_paying_years', 0)
        if div_years >= 4:
            ddm_points += 15
            logger.debug(f"    [+15] {div_years} years of dividend payments (>=4)")
        elif div_years >= 3:
            ddm_points += 10
            logger.debug(f"    [+10] {div_years} years of dividend payments (>=3)")
        elif div_years >= 2:
            ddm_points += 5
            logger.debug(f"    [+5] {div_years} years of dividend payments (>=2)")
        elif div_years >= 1:
            ddm_points += 2
            logger.debug(f"    [+2] {div_years} year of dividend payments")
        else:
            logger.debug("    [+0] No dividend payment history")

        # Dividend growth
        div_growth = metrics.get('dividend_growth', 0)
        if div_growth > 0.05:  # Growing dividends >5%
            ddm_points += 10
            logger.debug(f"    [+10] Dividend growth {div_growth:.1%} > 5%")
        elif div_growth > 0:  # Any positive growth
            ddm_points += 5
            logger.debug(f"    [+5] Dividend growth {div_growth:.1%} positive")
        else:
            logger.debug(f"    [+0] Dividend growth {div_growth:.1%} (flat or declining)")

        # Sustainable payout ratio (25-75% is healthy)
        payout_ratio = metrics['payout_ratio']
        if 0.25 <= payout_ratio <= 0.75:
            ddm_points += 10
            logger.debug(f"    [+10] Payout ratio {payout_ratio:.1%} in healthy range (25-75%)")
        elif 0.15 <= payout_ratio <= 0.85:
            ddm_points += 5
            logger.debug(f"    [+5] Payout ratio {payout_ratio:.1%} acceptable (15-85%)")
        elif payout_ratio > 0:
            ddm_points += 2
            logger.debug(f"    [+2] Payout ratio {payout_ratio:.1%} (exists but outside optimal)")
        else:
            logger.debug(f"    [+0] Payout ratio {payout_ratio:.1%} (no data or zero)")

        # Consecutive increases bonus
        consecutive_increases = metrics.get('consecutive_div_increases', 0)
        if consecutive_increases >= 3:
            ddm_points += 5
            logger.debug(f"    [+5] {consecutive_increases} consecutive years of increases")
        elif consecutive_increases >= 1:
            ddm_points += 2
            logger.debug(f"    [+2] {consecutive_increases} year(s) of increases")
        else:
            logger.debug("    [+0] No consecutive dividend increases detected")

        self.scores['DDM'] += ddm_points
        self.score_breakdown['DDM']['model_specific'] = ddm_points
        logger.debug(f"    DDM model-specific total: +{ddm_points}")

        # === REVENUE-BASED SPECIFIC SIGNALS (max ~50) ===
        logger.debug("  Revenue-Based Specific Signals:")
        rev_points = 0

        # High revenue growth
        revenue_growth = metrics['revenue_growth']
        if revenue_growth > 0.25:  # Hypergrowth
            rev_points += 20
            logger.debug(f"    [+20] Revenue growth {revenue_growth:.1%} > 25% (hypergrowth)")
        elif revenue_growth > 0.15:  # High growth
            rev_points += 15
            logger.debug(f"    [+15] Revenue growth {revenue_growth:.1%} > 15% (high growth)")
        elif revenue_growth > 0.10:  # Moderate growth
            rev_points += 8
            logger.debug(f"    [+8] Revenue growth {revenue_growth:.1%} > 10% (moderate)")
        else:
            logger.debug(f"    [+0] Revenue growth {revenue_growth:.1%} (not high enough)")

        # Negative/zero FCF (can't use DCF effectively)
        if fcf <= 0:
            rev_points += 15
            logger.debug(f"    [+15] Negative/zero FCF (${fcf/1e6:.1f}M) - DCF problematic")
        elif fcf_margin < 0.03:
            rev_points += 8
            logger.debug(f"    [+8] Very low FCF margin ({fcf_margin:.1%}) - DCF challenging")
        else:
            logger.debug("    [+0] FCF is positive and healthy")

        # Unprofitable (negative net income)
        net_margin = metrics['net_margin']
        if net_margin < 0:
            rev_points += 10
            logger.debug(f"    [+10] Unprofitable (net margin {net_margin:.1%})")
        elif net_margin < 0.05:
            rev_points += 5
            logger.debug(f"    [+5] Low profitability (net margin {net_margin:.1%})")
        else:
            logger.debug("    [+0] Profitable company")

        # High revenue, low earnings combination
        revenue = metrics['revenue_ttm']
        net_income = metrics['net_income_ttm']
        if revenue > 1e9 and (net_income <= 0 or net_margin < 0.05):
            rev_points += 5
            logger.debug(f"    [+5] Large revenue (${revenue/1e9:.1f}B) with low/no earnings")
        else:
            logger.debug("    [+0] Revenue/earnings ratio normal")

        self.scores['Revenue-Based'] += rev_points
        self.score_breakdown['Revenue-Based']['model_specific'] = rev_points
        logger.debug(f"    Revenue-Based model-specific total: +{rev_points}")

        # Comps gets no model-specific signals (it's the fallback)
        logger.debug("  Comps Specific Signals:")
        logger.debug("    [+0] Comps is fallback model - no specific signals")
        self.score_breakdown['Comps']['model_specific'] = 0

    # ========================================================================
    # STEP 2: SHARED SIGNALS (Equal Contribution)
    # ========================================================================

    def _analyze_shared_signals(self, metrics: Dict):
        """
        Analyze signals that indicate general model viability.
        These contribute EQUALLY to all applicable models.
        """
        logger.debug("  Shared Signal Analysis:")

        # Profitable company (+10 to all intrinsic models equally)
        net_margin = metrics['net_margin']
        if net_margin > 0:
            logger.debug(f"    [+10 all] Profitable (net margin {net_margin:.1%})")
            self.scores['Standard DCF'] += 10
            self.scores['DDM'] += 10
            self.scores['Revenue-Based'] += 10
            self.scores['Comps'] += 10
            for model in self.scores:
                self.score_breakdown[model]['profitable'] = 10
        else:
            logger.debug(f"    [+0] Not profitable (net margin {net_margin:.1%})")

        # Revenue stability (no declining years)
        revenue_stable = metrics.get('revenue_stable', True)
        if revenue_stable:
            logger.debug("    [+5 all] Revenue stable (no major declines)")
            self.scores['Standard DCF'] += 5
            self.scores['DDM'] += 5
            self.scores['Revenue-Based'] += 5
            self.scores['Comps'] += 5
            for model in self.scores:
                self.score_breakdown[model]['revenue_stable'] = 5
        else:
            logger.debug("    [+0] Revenue volatility detected")

        # Balance sheet health (D/E < 2, positive equity)
        de_ratio = metrics.get('de_ratio', 0)
        equity = metrics.get('equity', 0)
        if de_ratio < 2 and equity > 0:
            logger.debug(f"    [+5 all] Healthy balance sheet (D/E {de_ratio:.1f}, equity ${equity/1e6:.0f}M)")
            self.scores['Standard DCF'] += 5
            self.scores['DDM'] += 5
            self.scores['Revenue-Based'] += 5
            self.scores['Comps'] += 5
            for model in self.scores:
                self.score_breakdown[model]['balance_sheet'] = 5
        else:
            logger.debug(f"    [+0] Balance sheet concerns (D/E {de_ratio:.1f})")

        # Multiple years of data
        data_years = metrics.get('data_years', 0)
        if data_years >= 4:
            logger.debug(f"    [+10 all] {data_years} years of financial data")
            self.scores['Standard DCF'] += 10
            self.scores['DDM'] += 10
            self.scores['Revenue-Based'] += 10
            self.scores['Comps'] += 10
            for model in self.scores:
                self.score_breakdown[model]['data_years'] = 10
        elif data_years >= 2:
            logger.debug(f"    [+5 all] {data_years} years of financial data")
            self.scores['Standard DCF'] += 5
            self.scores['DDM'] += 5
            self.scores['Revenue-Based'] += 5
            self.scores['Comps'] += 5
            for model in self.scores:
                self.score_breakdown[model]['data_years'] = 5
        else:
            logger.debug(f"    [+0] Limited financial history ({data_years} years)")

    # ========================================================================
    # STEP 3: ARCHETYPE DETECTION (Tiebreaker)
    # ========================================================================

    def _analyze_archetype(self, metrics: Dict) -> Optional[str]:
        """
        Detect company archetypes and apply bonuses.
        Only ONE archetype can match - this is the tiebreaker.

        Archetypes:
        - Dividend Aristocrat: DDM +15
        - Cash Flow Compounder: DCF +15
        - Growth Disruptor: Revenue-Based +15
        """
        logger.debug("  Archetype Detection:")

        div_yield = metrics['dividend_yield']
        div_years = metrics.get('dividend_paying_years', 0)
        payout_ratio = metrics['payout_ratio']
        revenue_growth = metrics['revenue_growth']
        fcf_yield = metrics['fcf_yield']
        fcf = metrics['fcf_ttm']
        net_margin = metrics['net_margin']
        sector = metrics['sector']
        market_cap = metrics['market_cap']

        # === DIVIDEND ARISTOCRAT ARCHETYPE ===
        # Triggers when: yield > 1.5% AND 4+ years payments AND payout 20-80% AND growth < 10%
        is_div_aristocrat = (
            div_yield > 0.015 and
            div_years >= 4 and
            0.20 <= payout_ratio <= 0.80 and
            revenue_growth < 0.10
        )

        if is_div_aristocrat:
            logger.debug("    >>> DIVIDEND ARISTOCRAT ARCHETYPE DETECTED <<<")
            logger.debug(f"        Yield: {div_yield:.2%} (>1.5%)")
            logger.debug(f"        Payment years: {div_years} (>=4)")
            logger.debug(f"        Payout ratio: {payout_ratio:.1%} (20-80%)")
            logger.debug(f"        Revenue growth: {revenue_growth:.1%} (<10%)")
            logger.debug("    [+15 DDM] Archetype bonus")
            self.scores['DDM'] += 15
            self.score_breakdown['DDM']['archetype'] = 15
            return 'Dividend Aristocrat'

        # === CASH FLOW COMPOUNDER ARCHETYPE ===
        # Triggers when: (FCF yield > 4% OR FCF margin > 15%) AND dividend yield < 1.5% AND not utility/REIT
        # Also requires some positive FCF history
        is_utility_reit = sector.lower() in ['utilities', 'real estate']
        fcf_growth = metrics.get('fcf_growth', 0)
        fcf_margin = metrics['fcf_margin']
        positive_fcf_years = metrics.get('positive_fcf_years', 0)

        is_cashflow_compounder = (
            (fcf_yield > 0.04 or fcf_margin > 0.15) and
            positive_fcf_years >= 3 and
            div_yield < 0.015 and
            not is_utility_reit
        )

        if is_cashflow_compounder:
            logger.debug("    >>> CASH FLOW COMPOUNDER ARCHETYPE DETECTED <<<")
            logger.debug(f"        FCF yield: {fcf_yield:.1%} (>4%)")
            logger.debug(f"        FCF growth: {fcf_growth:.1%} (positive)")
            logger.debug(f"        Dividend yield: {div_yield:.2%} (<1.5%)")
            logger.debug(f"        Not utility/REIT: {not is_utility_reit}")
            logger.debug("    [+15 DCF] Archetype bonus")
            self.scores['Standard DCF'] += 15
            self.score_breakdown['Standard DCF']['archetype'] = 15
            return 'Cash Flow Compounder'

        # === GROWTH DISRUPTOR ARCHETYPE ===
        # Triggers when: revenue growth > 20% AND (negative FCF OR negative net income) AND not giant
        is_growth_disruptor = (
            revenue_growth > 0.20 and
            (fcf <= 0 or net_margin < 0) and
            market_cap < 500e9  # Not mega-cap
        )

        if is_growth_disruptor:
            logger.debug("    >>> GROWTH DISRUPTOR ARCHETYPE DETECTED <<<")
            logger.debug(f"        Revenue growth: {revenue_growth:.1%} (>20%)")
            logger.debug(f"        FCF: ${fcf/1e6:.1f}M (negative or net margin < 0)")
            logger.debug(f"        Market cap: ${market_cap/1e9:.1f}B (< $500B)")
            logger.debug("    [+15 Revenue-Based] Archetype bonus")
            self.scores['Revenue-Based'] += 15
            self.score_breakdown['Revenue-Based']['archetype'] = 15
            return 'Growth Disruptor'

        logger.debug("    No archetype matched")
        logger.debug(f"      - Dividend Aristocrat: yield={div_yield:.2%}, years={div_years}, payout={payout_ratio:.1%}, growth={revenue_growth:.1%}")
        logger.debug(f"      - Cash Flow Compounder: fcf_yield={fcf_yield:.1%}, fcf_growth={fcf_growth:.1%}, div_yield={div_yield:.2%}")
        logger.debug(f"      - Growth Disruptor: growth={revenue_growth:.1%}, fcf=${fcf/1e6:.1f}M, margin={net_margin:.1%}")

        return None

    # ========================================================================
    # STEP 4: SECTOR NUDGES
    # ========================================================================

    def _analyze_sector(self, metrics: Dict):
        """Apply sector-based nudges (small bonuses, not overrides)."""
        sector = metrics['sector']

        nudges = SECTOR_NUDGES.get(sector, {})

        if nudges:
            logger.debug(f"    Sector '{sector}' nudges:")
            for model, points in nudges.items():
                self.scores[model] += points
                self.score_breakdown[model]['sector'] = points
                logger.debug(f"      [+{points} {model}]")
        else:
            logger.debug(f"    Sector '{sector}' - no specific nudges")

    # ========================================================================
    # STEP 5: DATA AVAILABILITY
    # ========================================================================

    def _analyze_data_availability(self, metrics: Dict):
        """
        Check data availability for Comps fallback support.

        Also performs ROBUST dividend check from multiple sources.
        """
        # Robust dividend check - multiple sources
        has_dividends = self._check_dividend_availability()

        if not has_dividends:
            logger.debug("    [NOTE] No dividend data detected from any source")
            logger.debug("           DDM will be penalized in disqualifiers")
        else:
            logger.debug("    [OK] Dividend data available")

        # Comps gets points for data availability (reduced to prevent over-selection)
        completeness = self._calculate_completeness()
        if completeness >= 80:
            self.scores['Comps'] += 20
            self.score_breakdown['Comps']['data_availability'] = 20
            logger.debug(f"    [+20 Comps] High data completeness ({completeness:.0f}%)")
        elif completeness >= 60:
            self.scores['Comps'] += 15
            self.score_breakdown['Comps']['data_availability'] = 15
            logger.debug(f"    [+15 Comps] Moderate data completeness ({completeness:.0f}%)")
        else:
            self.scores['Comps'] += 10
            self.score_breakdown['Comps']['data_availability'] = 10
            logger.debug(f"    [+10 Comps] Limited data ({completeness:.0f}%)")

    def _check_dividend_availability(self) -> bool:
        """
        Robust dividend check from MULTIPLE sources.

        Checks:
        1. data['dividends']['most_recent'] > 0
        2. key_metrics['dividendYield'] > 0
        3. key_metrics['dividendRate'] > 0
        4. Any positive value in dividends['annual']
        """
        # Source 1: dividends dict
        if self.dividends.get('most_recent', 0) > 0:
            return True

        # Source 2: key_metrics dividendYield
        if self.key_metrics.get('dividendYield', 0) > 0:
            return True

        # Source 3: key_metrics dividendRate
        if self.key_metrics.get('dividendRate', 0) > 0:
            return True

        # Source 4: annual dividend totals
        annual = self.dividends.get('annual', {})
        if any(v > 0 for v in annual.values()):
            return True

        return False

    # ========================================================================
    # STEP 6: DISQUALIFIERS
    # ========================================================================

    def _apply_disqualifiers(self, metrics: Dict):
        """
        Apply hard disqualifications (caps, not zeroing).

        - DDM capped at 10 if no dividend history at all
        - DCF capped at 15 if no FCF data
        - Revenue-Based capped at 10 if no revenue data
        """

        # DDM disqualification: no dividend history
        has_dividends = self._check_dividend_availability()
        div_years = metrics.get('dividend_paying_years', 0)

        if not has_dividends and div_years == 0:
            old_score = self.scores['DDM']
            self.scores['DDM'] = min(self.scores['DDM'], 10)
            if old_score > 10:
                logger.debug(f"    [CAP] DDM capped at 10 (was {old_score}) - no dividend history")
                self.score_breakdown['DDM']['disqualified'] = f"capped from {old_score}"

        # DCF disqualification: no FCF data
        has_fcf_data = self.availability.get('fcf', False) or metrics.get('has_fcf_data', False)

        if not has_fcf_data:
            old_score = self.scores['Standard DCF']
            self.scores['Standard DCF'] = min(self.scores['Standard DCF'], 15)
            if old_score > 15:
                logger.debug(f"    [CAP] DCF capped at 15 (was {old_score}) - no FCF data")
                self.score_breakdown['Standard DCF']['disqualified'] = f"capped from {old_score}"

        # Revenue-Based disqualification: no revenue data
        revenue = metrics['revenue_ttm']
        if revenue <= 0:
            old_score = self.scores['Revenue-Based']
            self.scores['Revenue-Based'] = min(self.scores['Revenue-Based'], 10)
            if old_score > 10:
                logger.debug(f"    [CAP] Revenue-Based capped at 10 (was {old_score}) - no revenue data")
                self.score_breakdown['Revenue-Based']['disqualified'] = f"capped from {old_score}"

    # ========================================================================
    # STEP 7: FINAL RESULT CALCULATION
    # ========================================================================

    def _calculate_final_result(self, metrics: Dict, archetype: Optional[str]) -> Dict[str, Any]:
        """Calculate final result from scores."""

        # Ensure minimum scores
        for model in self.scores:
            self.scores[model] = max(0, self.scores[model])

        # Comps minimum
        self.scores['Comps'] = max(self.scores['Comps'], 25)

        # Find winner
        sorted_models = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        winner_model, winner_score = sorted_models[0]
        runner_up_model, runner_up_score = sorted_models[1]

        # Calculate confidence
        score_gap = winner_score - runner_up_score
        if score_gap >= 20:
            confidence = 'High'
            confidence_pct = 90
        elif score_gap >= 10:
            confidence = 'Medium'
            confidence_pct = 75
        else:
            confidence = 'Low'
            confidence_pct = 60

        # Build reasoning
        reasoning_parts = []
        if archetype:
            reasoning_parts.append(f"{archetype} archetype")

        breakdown = self.score_breakdown[winner_model]
        if breakdown.get('model_specific', 0) >= 30:
            reasoning_parts.append("strong model-specific signals")
        if breakdown.get('archetype'):
            reasoning_parts.append("archetype match")
        if breakdown.get('sector'):
            reasoning_parts.append(f"{metrics['sector']} sector alignment")

        reasoning = f"{winner_model} selected (score: {winner_score})"
        if reasoning_parts:
            reasoning += f" - {', '.join(reasoning_parts)}"

        # Determine alternative
        alternative = runner_up_model if runner_up_score > 40 else None

        # Log final decision
        self._log_final_decision(winner_model, winner_score, runner_up_model, runner_up_score, archetype)

        return {
            'recommended_model': winner_model,
            'confidence': confidence,
            'confidence_percentage': confidence_pct,
            'reasoning': reasoning,
            'alternative': alternative,
            'model_scores': dict(self.scores),
            'score_breakdown': dict(self.score_breakdown),
            'archetype': archetype,
            'alternative_models': [runner_up_model] if alternative else [],
            'sotp_flag': self._check_sotp_needed(),
            'data_completeness': self._calculate_completeness(),
            'warnings': self._generate_warnings(),
            'tier_used': 'v4.0 balanced scoring'
        }

    # ========================================================================
    # DATA EXTRACTION
    # ========================================================================

    def _extract_all_metrics(self) -> Dict:
        """Extract all metrics from data sources."""
        if self._metrics_cache is not None:
            return self._metrics_cache

        company_info = self.company_info
        key_metrics = self.key_metrics
        income_stmt = self.data.get('income_statement', pd.DataFrame())
        balance_sheet = self.data.get('balance_sheet', pd.DataFrame())
        cash_flow = self.data.get('cash_flow', pd.DataFrame())
        dividends = self.dividends

        # Basic company info
        sector = company_info.get('sector', 'Unknown')
        industry = company_info.get('industry', 'Unknown')
        market_cap = company_info.get('market_cap', 0) or key_metrics.get('marketCap', 0)

        # Revenue metrics
        revenue_ttm = self._safe_get_df_value(income_stmt, 'Total Revenue', 0, 0)
        if revenue_ttm == 0:
            revenue_ttm = self._safe_get_df_value(income_stmt, 'Operating Revenue', 0, 0)
        if revenue_ttm == 0:
            revenue_ttm = key_metrics.get('totalRevenue', 0)

        revenue_y1 = self._safe_get_df_value(income_stmt, 'Total Revenue', 1, 0)
        if revenue_y1 == 0:
            revenue_y1 = self._safe_get_df_value(income_stmt, 'Operating Revenue', 1, 0)

        # Only fall back to API value when denominator was unavailable
        if revenue_y1 <= 0:
            revenue_growth = key_metrics.get('revenueGrowth', 0) or 0
        else:
            revenue_growth = (revenue_ttm - revenue_y1) / revenue_y1

        # Revenue stability
        revenue_stable = True
        for i in range(1, 4):
            rev_i = self._safe_get_df_value(income_stmt, 'Total Revenue', i, 0)
            rev_i1 = self._safe_get_df_value(income_stmt, 'Total Revenue', i+1, 0)
            if rev_i1 > 0 and rev_i < rev_i1 * 0.85:  # >15% decline
                revenue_stable = False
                break

        # Net income metrics
        net_income_ttm = self._safe_get_df_value(income_stmt, 'Net Income', 0, 0)
        net_margin = net_income_ttm / revenue_ttm if revenue_ttm > 0 else 0

        # Also check key_metrics
        if net_margin == 0:
            net_margin = key_metrics.get('profitMargins', 0) or 0

        # FCF metrics — track data presence separately to avoid sentinel values
        fcf_from_df = self._safe_get_df_value(cash_flow, 'Free Cash Flow', 0, None)
        fcf_from_api = key_metrics.get('freeCashflow')
        has_fcf_data = fcf_from_df is not None or fcf_from_api is not None
        fcf_ttm = fcf_from_df if fcf_from_df is not None else (fcf_from_api if fcf_from_api is not None else 0)

        fcf_margin = fcf_ttm / revenue_ttm if revenue_ttm > 0 else -1

        # FCF consistency (positive years)
        positive_fcf_years = 0
        for i in range(5):
            fcf_i = self._safe_get_df_value(cash_flow, 'Free Cash Flow', i, None)
            if fcf_i is not None and fcf_i > 0:
                positive_fcf_years += 1

        # FCF growth
        fcf_y1 = self._safe_get_df_value(cash_flow, 'Free Cash Flow', 1, 0)
        fcf_growth = (fcf_ttm - fcf_y1) / abs(fcf_y1) if fcf_y1 != 0 else 0

        # Dividend metrics - USE MULTIPLE SOURCES
        # Get raw values
        dividend_rate = key_metrics.get('dividendRate', 0) or 0
        payout_ratio = key_metrics.get('payoutRatio', 0) or 0
        current_price = key_metrics.get('currentPrice', 0) or key_metrics.get('regularMarketPrice', 0)

        # CRITICAL: Calculate dividend yield ourselves for reliability
        # Prefer dividendRate / currentPrice as it avoids any format ambiguity
        if dividend_rate > 0 and current_price > 0:
            dividend_yield = dividend_rate / current_price
        else:
            # yfinance dividendYield: 0.02 = 2% yield — already decimal, no conversion needed
            dividend_yield = key_metrics.get('dividendYield', 0) or 0

        # Normalize payout ratio if needed (yfinance returns 0.13 for 13%)
        # payout ratio is typically between 0 and 1, so no conversion needed
        # But if > 1, it might be in percentage form
        if payout_ratio > 1:
            payout_ratio = payout_ratio / 100

        # Secondary: dividends dict
        annual_divs = dividends.get('annual', {})

        # Count dividend paying years
        dividend_paying_years = sum(1 for v in annual_divs.values() if v and v > 0)

        # Dividend growth
        div_y0 = annual_divs.get('year_0', 0) or 0
        div_y1 = annual_divs.get('year_1', 0) or 0
        dividend_growth = (div_y0 - div_y1) / div_y1 if div_y1 > 0 else 0

        # Consecutive increases
        consecutive_increases = 0
        prev_div = 0
        for i in range(4, -1, -1):  # Start from oldest
            curr_div = annual_divs.get(f'year_{i}', 0) or 0
            if curr_div > prev_div and prev_div > 0:
                consecutive_increases += 1
            elif curr_div < prev_div and prev_div > 0:
                consecutive_increases = 0  # Reset on decrease
            prev_div = curr_div

        # Balance sheet metrics
        de_ratio = key_metrics.get('debtToEquity', 0) or 0
        if de_ratio == 0:
            total_debt = self._safe_get_df_value(balance_sheet, 'Total Debt', 0, 0)
            equity = self._safe_get_df_value(balance_sheet, 'Stockholders Equity', 0, 0)
            if equity > 0:
                de_ratio = total_debt / equity

        equity = self._safe_get_df_value(balance_sheet, 'Stockholders Equity', 0, 0)

        # Data years available
        data_years = len(income_stmt.columns) if not income_stmt.empty else 0

        # Pre-compute FCF yield for reuse (avoid duplicate computation)
        fcf_yield = fcf_ttm / market_cap if market_cap > 0 else 0

        self._metrics_cache = {
            'sector': sector,
            'industry': industry,
            'market_cap': market_cap,
            'revenue_ttm': revenue_ttm,
            'revenue_growth': revenue_growth,
            'revenue_stable': revenue_stable,
            'net_income_ttm': net_income_ttm,
            'net_margin': net_margin,
            'fcf_ttm': fcf_ttm,
            'fcf_margin': fcf_margin,
            'fcf_growth': fcf_growth,
            'fcf_yield': fcf_yield,
            'positive_fcf_years': positive_fcf_years,
            'has_fcf_data': has_fcf_data,
            'dividend_yield': dividend_yield,
            'dividend_rate': dividend_rate,
            'payout_ratio': payout_ratio,
            'dividend_paying_years': dividend_paying_years,
            'dividend_growth': dividend_growth,
            'consecutive_div_increases': consecutive_increases,
            'de_ratio': de_ratio,
            'equity': equity,
            'data_years': data_years,
        }

        return self._metrics_cache

    def _safe_get_df_value(self, df: pd.DataFrame, row_name: str, col_index: int, default=0):
        """Delegate to excel_helpers.get_df_value."""
        return get_df_value(df, row_name, col_index, default)

    # ========================================================================
    # LOGGING & HELPERS
    # ========================================================================

    def _log_scores(self, label: str):
        """Log current scores."""
        logger.debug(f"  Scores {label}:")
        for model, score in sorted(self.scores.items(), key=lambda x: x[1], reverse=True):
            logger.debug(f"    {model}: {score}")

    def _log_company_profile(self, metrics: Dict):
        """Log company profile."""
        logger.info(f"AUTO-DETECTION ANALYSIS v4.0 FOR: {self.ticker}")

        logger.debug("COMPANY PROFILE:")
        logger.debug(f"  Sector: {metrics['sector']}")
        logger.debug(f"  Industry: {metrics['industry']}")
        if metrics['market_cap'] > 0:
            logger.debug(f"  Market Cap: ${metrics['market_cap']/1e9:.2f}B")

        logger.debug("FINANCIAL METRICS (TTM):")
        if metrics['revenue_ttm'] > 0:
            logger.debug(f"  Revenue: ${metrics['revenue_ttm']/1e9:.2f}B")
        logger.debug(f"  Revenue Growth: {metrics['revenue_growth']:.1%}")
        logger.debug(f"  Net Margin: {metrics['net_margin']:.1%}")
        logger.debug(f"  FCF: ${metrics['fcf_ttm']/1e6:.1f}M")
        logger.debug(f"  FCF Margin: {metrics['fcf_margin']:.1%}")

        logger.debug("DIVIDEND PROFILE:")
        logger.debug(f"  Dividend Yield: {metrics['dividend_yield']:.2%}")
        logger.debug(f"  Payout Ratio: {metrics['payout_ratio']:.1%}")
        logger.debug(f"  Dividend Years: {metrics['dividend_paying_years']}")
        logger.debug(f"  Consecutive Increases: {metrics['consecutive_div_increases']}")

    def _log_final_decision(self, winner: str, winner_score: int,
                           runner_up: str, runner_up_score: int, archetype: Optional[str]):
        """Log final decision."""
        logger.info("*** FINAL DECISION ***")
        logger.info(f"  Winner: {winner} (score: {winner_score})")
        logger.info(f"  Runner-up: {runner_up} (score: {runner_up_score})")
        logger.info(f"  Gap: {winner_score - runner_up_score} points")
        if archetype:
            logger.info(f"  Archetype: {archetype}")
        logger.info("  Full Scores:")
        for model, score in sorted(self.scores.items(), key=lambda x: x[1], reverse=True):
            breakdown = self.score_breakdown.get(model, {})
            parts = [f"{k}:{v}" for k, v in breakdown.items() if v and v != 0]
            logger.info(f"    {model}: {score} ({', '.join(parts) if parts else 'base'})")

    def _calculate_completeness(self) -> float:
        """Calculate data completeness."""
        total = 5
        available = sum([
            self.availability.get('revenue', False),
            self.availability.get('fcf', False),
            self.availability.get('dividends', False) or self._check_dividend_availability(),
            self.availability.get('balance_sheet', False),
            self.availability.get('income_statement', False),
        ])
        return (available / total) * 100.0

    def _check_sotp_needed(self) -> bool:
        """Check if SOTP analysis needed."""
        industry = self.company_info.get('industry', '').lower()
        sotp_keywords = ['conglomerates', 'diversified', 'holding companies']
        return any(kw in industry for kw in sotp_keywords)

    def _generate_warnings(self) -> List[str]:
        """Generate warnings."""
        warnings = []

        if not self.availability.get('revenue'):
            warnings.append("Revenue data not available")
        if not self.availability.get('fcf'):
            warnings.append("Free Cash Flow data not available")
        if not self.availability.get('balance_sheet'):
            warnings.append("Balance sheet data missing")

        completeness = self._calculate_completeness()
        if completeness < 60:
            warnings.append(f"Data completeness only {completeness:.0f}%")

        return warnings


# ============================================================================
# MODULE METADATA
# ============================================================================

__version__ = '4.0'
__all__ = ['ModelDetector']
