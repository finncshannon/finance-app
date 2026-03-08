"""
Model Checker -- determines which valuation models fit each company.

Checks compatibility with the user's existing valuation models:
  - DCF:      Needs positive Free Cash Flow
  - DDM:      Needs dividend payment history
  - RevBased: Needs revenue (works for pre-profit companies)
  - Comps:    Needs revenue + market cap for multiples (always fits)

Logic adapted from auto_detect_model.py's ModelDetector scoring engine,
simplified for screening use. The screener doesn't need to pick THE BEST
model -- it just needs to flag which models CAN work.

Usage:
    from core.model_checker import ModelChecker

    checker = ModelChecker()
    fit = checker.check_fit(financials)
    # {"DCF": True, "DDM": False, "RevBased": True, "Comps": True}
    # notes: "Strong FCF ($6.2B). No dividend history."
"""

import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


# Sector-based model recommendations (from ModelDetector's SECTOR_NUDGES)
SECTOR_MODEL_PREFERENCES = {
    "Utilities":                ["DDM", "DCF"],
    "Real Estate":              ["DDM", "DCF"],
    "Financials":               ["DDM", "DCF"],
    "Consumer Staples":         ["DCF", "DDM"],
    "Energy":                   ["DCF", "DDM"],
    "Materials":                ["DCF"],
    "Industrials":              ["DCF", "DDM"],
    "Health Care":              ["DCF", "RevBased"],
    "Information Technology":   ["DCF", "RevBased"],
    "Communication Services":   ["DCF", "RevBased"],
    "Consumer Discretionary":   ["DCF"],
}


class ModelFit:
    """Result of model compatibility check for a company."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.fits = {
            "DCF": False,
            "DDM": False,
            "RevBased": False,
            "Comps": False,
        }
        self.notes: List[str] = []
        self.recommended: str = ""       # Best model
        self.alternatives: List[str] = []  # Other viable models
        self.excluded: bool = False       # True if no model fits
        self.exclusion_reason: str = ""

    @property
    def fit_summary(self) -> str:
        """Short summary like 'DCF, DDM' or 'RevBased only'."""
        fitting = [m for m, ok in self.fits.items() if ok]
        if not fitting:
            return "None"
        return ", ".join(fitting)

    @property
    def any_fit(self) -> bool:
        """True if any model works."""
        return any(self.fits.values())

    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "fits": dict(self.fits),
            "recommended": self.recommended,
            "alternatives": self.alternatives,
            "notes": self.notes,
            "excluded": self.excluded,
            "exclusion_reason": self.exclusion_reason,
        }

    def __repr__(self):
        return f"ModelFit({self.ticker}: {self.fit_summary})"


class ModelChecker:
    """
    Checks valuation model compatibility using XBRL financial data.
    """

    def check_fit(self, financials: Dict, sector: str = "") -> ModelFit:
        """
        Check which valuation models work for a company.

        Args:
            financials: Dict from XBRLParser.get_financials() or CompanyStore
            sector: GICS sector for model preference hints

        Returns:
            ModelFit with compatibility flags and notes.
        """
        ticker = financials.get("ticker", "???")
        result = ModelFit(ticker)

        revenue = financials.get("revenue")
        net_income = financials.get("net_income")
        fcf = financials.get("fcf")
        ocf = financials.get("operating_cash_flow")
        capex = financials.get("capex")
        dividends = financials.get("dividends_paid")
        total_assets = financials.get("total_assets")

        # --- Pre-checks for exclusion ---
        if revenue is None and net_income is None and total_assets is None:
            result.excluded = True
            result.exclusion_reason = "No financial data available"
            result.notes.append("No XBRL financial data found")
            return result

        # --- DCF Check ---
        self._check_dcf(result, fcf, ocf, capex, revenue)

        # --- DDM Check ---
        self._check_ddm(result, dividends, net_income)

        # --- RevBased Check ---
        self._check_revbased(result, revenue, net_income, fcf)

        # --- Comps Check ---
        self._check_comps(result, revenue, total_assets)

        # --- Determine recommendation ---
        self._recommend(result, financials, sector)

        # --- Check if excluded (no model fits) ---
        if not result.any_fit:
            result.excluded = True
            result.exclusion_reason = "No valuation model fits the available data"

        return result

    def _check_dcf(self, result: ModelFit, fcf, ocf, capex, revenue):
        """Check DCF compatibility."""
        if fcf is not None and fcf > 0:
            result.fits["DCF"] = True
            # Characterize FCF quality
            if revenue and revenue > 0:
                fcf_margin = fcf / revenue
                if fcf_margin > 0.15:
                    result.notes.append(f"Strong FCF margin ({fcf_margin*100:.0f}%)")
                elif fcf_margin > 0.05:
                    result.notes.append(f"Positive FCF margin ({fcf_margin*100:.0f}%)")
        elif ocf is not None and ocf > 0:
            # OCF positive but FCF negative -- might work with adjustments
            result.fits["DCF"] = True
            result.notes.append("Positive operating cash flow but FCF may be negative after CapEx")
        else:
            result.notes.append("No positive FCF or operating cash flow for DCF")

    def _check_ddm(self, result: ModelFit, dividends, net_income):
        """Check DDM compatibility."""
        if dividends is not None and dividends > 0:
            result.fits["DDM"] = True

            # Check payout ratio sustainability
            if net_income is not None and net_income > 0:
                payout_ratio = dividends / net_income
                if 0.20 <= payout_ratio <= 0.75:
                    result.notes.append(f"Sustainable payout ratio ({payout_ratio*100:.0f}%)")
                elif payout_ratio > 0.90:
                    result.notes.append(f"High payout ratio ({payout_ratio*100:.0f}%) -- DDM risky")
                elif payout_ratio < 0.15:
                    result.notes.append(f"Low payout ratio ({payout_ratio*100:.0f}%)")
        else:
            result.notes.append("No dividend history for DDM")

    def _check_revbased(self, result: ModelFit, revenue, net_income, fcf):
        """Check Revenue-Based model compatibility."""
        if revenue is not None and revenue > 0:
            result.fits["RevBased"] = True

            # RevBased is especially appropriate for pre-profit companies
            if net_income is not None and net_income <= 0:
                result.notes.append("Pre-profit company -- RevBased is primary model")
            elif fcf is not None and fcf <= 0:
                result.notes.append("Negative FCF -- RevBased may be more appropriate than DCF")
        else:
            result.notes.append("No revenue data for Revenue-Based model")

    def _check_comps(self, result: ModelFit, revenue, total_assets):
        """Check Comps compatibility."""
        # Comps works for almost any company with financial data
        if revenue is not None and revenue > 0:
            result.fits["Comps"] = True
        elif total_assets is not None and total_assets > 0:
            result.fits["Comps"] = True
            result.notes.append("Comps using asset-based multiples (no revenue)")
        else:
            result.notes.append("Insufficient data for Comps analysis")

    def _recommend(self, result: ModelFit, financials: Dict, sector: str):
        """Determine the recommended model and alternatives."""
        fitting = [m for m, ok in result.fits.items() if ok]

        if not fitting:
            return

        revenue = financials.get("revenue")
        net_income = financials.get("net_income")
        fcf = financials.get("fcf")
        dividends = financials.get("dividends_paid")

        # Score each fitting model
        scores = {}

        for model in fitting:
            score = 0

            if model == "DCF" and fcf is not None:
                score = 50
                if fcf > 0 and revenue and revenue > 0:
                    fcf_margin = fcf / revenue
                    score += min(fcf_margin * 100, 30)

            elif model == "DDM" and dividends is not None:
                score = 40
                if net_income and net_income > 0:
                    payout = dividends / net_income
                    if 0.20 <= payout <= 0.75:
                        score += 20

            elif model == "RevBased":
                score = 30
                if net_income is not None and net_income <= 0:
                    score += 30  # RevBased is primary for unprofitable
                elif fcf is not None and fcf <= 0:
                    score += 20

            elif model == "Comps":
                score = 25  # Baseline for Comps

            # Apply sector preference
            prefs = SECTOR_MODEL_PREFERENCES.get(sector, [])
            if model in prefs:
                idx = prefs.index(model)
                score += 10 - (idx * 3)  # +10 for first, +7 for second

            scores[model] = score

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        result.recommended = ranked[0][0]
        result.alternatives = [m for m, s in ranked[1:] if s > 25]

    def check_fit_batch(self, companies: List[Dict],
                         sector: str = "") -> List[ModelFit]:
        """
        Check model fit for multiple companies.

        Args:
            companies: List of financials dicts
            sector: GICS sector filter

        Returns:
            List of ModelFit results.
        """
        results = []
        for financials in companies:
            fit = self.check_fit(financials, sector)
            results.append(fit)
        return results

    def format_fit_summary(self, fit: ModelFit) -> str:
        """Format a human-readable summary of model compatibility."""
        lines = [f"  {fit.ticker}: "]

        if fit.excluded:
            lines[0] += f"EXCLUDED -- {fit.exclusion_reason}"
        else:
            models = []
            for model, ok in fit.fits.items():
                if ok:
                    marker = "*" if model == fit.recommended else ""
                    models.append(f"{model}{marker}")
            lines[0] += " | ".join(models)

            if fit.recommended:
                lines.append(f"    Recommended: {fit.recommended}")
            if fit.alternatives:
                lines.append(f"    Alternatives: {', '.join(fit.alternatives)}")

        for note in fit.notes:
            lines.append(f"    - {note}")

        return "\n".join(lines)
