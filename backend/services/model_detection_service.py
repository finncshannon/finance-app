"""Model detection service — analyzes financial characteristics to recommend
valuation model(s).

Scores four model types (DCF, DDM, Comps, Revenue-Based) from 0-100 based on
a company's profitability, growth profile, dividend history, data quality, and
sector. Returns a ranked list with reasoning and confidence level.
"""

import logging
import statistics
from pydantic import BaseModel

from db.connection import DatabaseConnection
from repositories.company_repo import CompanyRepo
from repositories.market_data_repo import MarketDataRepo
from services.data_extraction_service import DataExtractionService

logger = logging.getLogger("finance_app")


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class ModelScore(BaseModel):
    model_type: str            # "dcf", "ddm", "comps", "revenue_based"
    score: int                 # 0-100
    applicable: bool           # score >= 40
    reasoning: str             # human-readable explanation


class ModelDetectionResult(BaseModel):
    ticker: str
    recommended_model: str     # model_type with highest score
    confidence: str            # "High" / "Medium" / "Low"
    confidence_percentage: int  # 90, 75, or 60
    scores: list[ModelScore]   # all 4 models, sorted by score desc
    characteristics: dict      # the 7 booleans


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ModelDetectionService:
    """Analyzes a company's financial characteristics and recommends which
    valuation model(s) to use."""

    def __init__(self, db: DatabaseConnection, data_extraction: DataExtractionService):
        self.db = db
        self.data_extraction = data_extraction
        self.company_repo = CompanyRepo(db)
        self.market_data_repo = MarketDataRepo(db)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def detect(self, ticker: str) -> ModelDetectionResult:
        """Detect the best valuation model for *ticker*.

        Steps:
            1. Pull computed metrics from DataExtractionService
            2. Pull company info (sector) from CompanyRepo
            3. Pull financial history from MarketDataRepo
            4. Analyse company characteristics (7 booleans)
            5. Score each model type 0-100
            6. Generate reasoning text
            7. Determine confidence from score gap
            8. Return ModelDetectionResult
        """
        ticker = ticker.upper()

        try:
            # 1. Metrics --------------------------------------------------
            metrics = await self.data_extraction.compute_all_metrics(ticker)

            # 2. Company info (sector) ------------------------------------
            company = await self.company_repo.get_by_ticker(ticker)
            sector = (company.get("sector") or "Unknown") if company else "Unknown"

            # 3. Financial history ----------------------------------------
            financials = await self.market_data_repo.get_financials(ticker)

            # 4. Characteristics ------------------------------------------
            characteristics = self._analyse_characteristics(metrics, financials)

            # 5. Score each model -----------------------------------------
            dcf_score, dcf_reasons = self._score_dcf(metrics, characteristics, sector)
            ddm_score, ddm_reasons = self._score_ddm(characteristics, sector)
            comps_score, comps_reasons = self._score_comps(characteristics)
            rev_score, rev_reasons = self._score_revenue_based(metrics, characteristics, sector)

            raw_scores = {
                "dcf": dcf_score,
                "ddm": ddm_score,
                "comps": comps_score,
                "revenue_based": rev_score,
            }
            reason_map = {
                "dcf": dcf_reasons,
                "ddm": ddm_reasons,
                "comps": comps_reasons,
                "revenue_based": rev_reasons,
            }

            # Clamp to 0-100
            clamped: dict[str, int] = {
                k: max(0, min(100, v)) for k, v in raw_scores.items()
            }

            # 6. Reasoning ------------------------------------------------
            model_scores: list[ModelScore] = []
            for model_type in ("dcf", "ddm", "comps", "revenue_based"):
                score = clamped[model_type]
                reasoning = self._build_reasoning(ticker, model_type, reason_map[model_type])
                model_scores.append(ModelScore(
                    model_type=model_type,
                    score=score,
                    applicable=score >= 40,
                    reasoning=reasoning,
                ))

            # Sort descending by score
            model_scores.sort(key=lambda ms: ms.score, reverse=True)

            # 7. Confidence -----------------------------------------------
            sorted_values = [ms.score for ms in model_scores]
            gap = sorted_values[0] - sorted_values[1]
            if gap >= 20:
                confidence = "High"
                confidence_pct = 90
            elif gap >= 10:
                confidence = "Medium"
                confidence_pct = 75
            else:
                confidence = "Low"
                confidence_pct = 60

            return ModelDetectionResult(
                ticker=ticker,
                recommended_model=model_scores[0].model_type,
                confidence=confidence,
                confidence_percentage=confidence_pct,
                scores=model_scores,
                characteristics=characteristics,
            )

        except Exception as exc:
            logger.error("Model detection failed for %s: %s", ticker, exc, exc_info=True)
            # Fallback: recommend DCF with low confidence
            return ModelDetectionResult(
                ticker=ticker,
                recommended_model="dcf",
                confidence="Low",
                confidence_percentage=60,
                scores=[
                    ModelScore(model_type="dcf", score=50, applicable=True,
                              reasoning=f"DCF selected as default for {ticker} — insufficient data for detailed analysis."),
                    ModelScore(model_type="comps", score=40, applicable=True,
                              reasoning=f"Comparable company analysis may be viable for {ticker} pending more data."),
                    ModelScore(model_type="revenue_based", score=30, applicable=False,
                              reasoning=f"Revenue-based valuation has limited applicability for {ticker} without more data."),
                    ModelScore(model_type="ddm", score=20, applicable=False,
                              reasoning=f"DDM cannot be evaluated for {ticker} without dividend data."),
                ],
                characteristics={
                    "is_dividend_payer": False,
                    "is_profitable": False,
                    "is_high_growth": False,
                    "is_asset_heavy": False,
                    "has_stable_margins": False,
                    "is_pre_revenue": False,
                    "has_sufficient_data": False,
                },
            )

    # ------------------------------------------------------------------
    # Characteristic analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _analyse_characteristics(
        metrics: dict[str, float | None],
        financials: list[dict],
    ) -> dict[str, bool]:
        """Derive 7 boolean characteristics from metrics and financial rows."""

        # --- is_dividend_payer ---
        dividend_yield = metrics.get("dividend_yield")
        # Payout ratio: try to derive from financials if available
        payout_ratio: float | None = None
        if financials:
            latest = financials[0]
            dividends_paid = latest.get("dividends_paid")
            net_income = latest.get("net_income")
            if dividends_paid is not None and net_income is not None and net_income != 0:
                payout_ratio = abs(dividends_paid) / abs(net_income)

        is_dividend_payer = (
            dividend_yield is not None
            and dividend_yield > 0
            and payout_ratio is not None
            and 0.1 <= payout_ratio <= 1.5
        )

        # --- is_profitable ---
        net_margin = metrics.get("net_margin")
        is_profitable = net_margin is not None and net_margin > 0

        # --- is_high_growth ---
        rev_growth_yoy = metrics.get("revenue_growth_yoy")
        rev_cagr_3y = metrics.get("revenue_cagr_3y")
        is_high_growth = (
            (rev_growth_yoy is not None and rev_growth_yoy > 0.15)
            or (rev_cagr_3y is not None and rev_cagr_3y > 0.12)
        )

        # --- is_asset_heavy ---
        is_asset_heavy = False
        if financials:
            latest = financials[0]
            total_assets = latest.get("total_assets")
            revenue = latest.get("revenue")
            if total_assets is not None and revenue is not None and revenue > 0:
                is_asset_heavy = (total_assets / revenue) > 3.0

        # --- has_stable_margins ---
        has_stable_margins = False
        if len(financials) >= 3:
            gross_margins: list[float] = []
            for row in financials:
                gp = row.get("gross_profit")
                rev = row.get("revenue")
                if gp is not None and rev is not None and rev != 0:
                    gross_margins.append(gp / rev)
            if len(gross_margins) >= 3:
                has_stable_margins = statistics.stdev(gross_margins) < 0.05

        # --- is_pre_revenue ---
        is_pre_revenue = True  # default if no data
        if financials:
            latest = financials[0]
            revenue = latest.get("revenue")
            is_pre_revenue = revenue is None or revenue < 1_000_000

        # --- has_sufficient_data ---
        has_sufficient_data = len(financials) >= 3

        return {
            "is_dividend_payer": is_dividend_payer,
            "is_profitable": is_profitable,
            "is_high_growth": is_high_growth,
            "is_asset_heavy": is_asset_heavy,
            "has_stable_margins": has_stable_margins,
            "is_pre_revenue": is_pre_revenue,
            "has_sufficient_data": has_sufficient_data,
        }

    # ------------------------------------------------------------------
    # Scoring functions
    # ------------------------------------------------------------------

    @staticmethod
    def _score_dcf(
        metrics: dict[str, float | None],
        chars: dict[str, bool],
        sector: str,
    ) -> tuple[int, list[str]]:
        """Score DCF model suitability. Returns (raw_score, list_of_reason_fragments)."""
        score = 50
        reasons: list[str] = []

        if chars["is_profitable"]:
            score += 20
            reasons.append("consistent profitability")
        if chars["has_stable_margins"]:
            score += 15
            reasons.append("stable operating margins")
        if chars["has_sufficient_data"]:
            score += 10
            reasons.append("sufficient historical data for projection")
        if chars["is_pre_revenue"]:
            score -= 20
            reasons.append("pre-revenue stage limits cash-flow forecasting")
        if chars["is_asset_heavy"]:
            score -= 10
            reasons.append("asset-heavy balance sheet complicates FCF modelling")
        if sector in ("Technology", "Communication Services"):
            score += 5
            reasons.append(f"{sector} sector aligns well with DCF")

        # Cap at 15 if no FCF data
        fcf_margin = metrics.get("fcf_margin")
        if fcf_margin is None:
            score = min(score, 15)
            reasons.append("lack of positive free cash flow data")

        return score, reasons

    @staticmethod
    def _score_ddm(
        chars: dict[str, bool],
        sector: str,
    ) -> tuple[int, list[str]]:
        """Score DDM model suitability."""
        score = 20
        reasons: list[str] = []

        if chars["is_dividend_payer"]:
            score += 40
            reasons.append("consistent dividend history with a sustainable payout ratio")
        if chars["has_stable_margins"]:
            score += 20
            reasons.append("stable margins support reliable dividend forecasts")
        if chars["is_profitable"]:
            score += 15
            reasons.append("positive earnings underpin dividend coverage")
        if chars["is_high_growth"]:
            score -= 30
            reasons.append("high-growth profile suggests dividends are less relevant")
        if sector in ("Utilities", "Real Estate", "Financial Services"):
            score += 10
            reasons.append(f"{sector} sector has strong dividend orientation")

        # Cap at 10 if not a dividend payer
        if not chars["is_dividend_payer"]:
            score = min(score, 10)
            reasons.append("does not pay dividends")

        return score, reasons

    @staticmethod
    def _score_comps(
        chars: dict[str, bool],
    ) -> tuple[int, list[str]]:
        """Score Comparable Company Analysis suitability."""
        score = 40
        reasons: list[str] = []

        if chars["has_sufficient_data"]:
            score += 20
            reasons.append("sufficient data for peer benchmarking")
        if chars["is_profitable"]:
            score += 15
            reasons.append("established profitability enables meaningful multiples")
        if not chars["is_pre_revenue"]:
            score += 10
            reasons.append("revenue base allows standard multiple comparisons")
        if chars["has_sufficient_data"]:
            score += 5
            reasons.append("data completeness supports robust comps analysis")
        if chars["is_pre_revenue"]:
            score -= 15
            reasons.append("pre-revenue status limits comparable multiple selection")

        return score, reasons

    @staticmethod
    def _score_revenue_based(
        metrics: dict[str, float | None],
        chars: dict[str, bool],
        sector: str,
    ) -> tuple[int, list[str]]:
        """Score Revenue-Based valuation suitability."""
        score = 30
        reasons: list[str] = []

        if chars["is_high_growth"]:
            score += 30
            reasons.append("high growth profile suits revenue-based valuation")
        if chars["is_pre_revenue"] or (metrics.get("net_margin") is not None and metrics["net_margin"] < 0):
            score += 20
            reasons.append("early-stage or negative margins make revenue the primary anchor")
        if sector in ("Technology", "Healthcare", "Communication Services"):
            score += 15
            reasons.append(f"{sector} sector commonly valued on revenue multiples")
        if chars["is_asset_heavy"]:
            score -= 20
            reasons.append("asset-heavy structure is better captured by other methods")
        if chars["has_stable_margins"] and not chars["is_high_growth"]:
            score -= 15
            reasons.append("stable margins and moderate growth favour earnings-based models")

        # Cap at 10 if no revenue data at all
        rev_growth = metrics.get("revenue_growth_yoy")
        net_margin = metrics.get("net_margin")
        # No revenue data means both revenue-derived metrics are None
        if rev_growth is None and net_margin is None:
            score = min(score, 10)
            reasons.append("no revenue data available")

        return score, reasons

    # ------------------------------------------------------------------
    # Reasoning builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_reasoning(ticker: str, model_type: str, reasons: list[str]) -> str:
        """Build a human-readable 1-2 sentence reasoning string."""
        if not reasons:
            return f"Insufficient data to evaluate {model_type.upper()} for {ticker}."

        label_map = {
            "dcf": "DCF",
            "ddm": "DDM",
            "comps": "Comparable company analysis",
            "revenue_based": "Revenue-based valuation",
        }
        label = label_map.get(model_type, model_type.upper())

        # Separate positive and negative factors
        # Negative reasons typically contain words like "not", "lack", "less",
        # "limits", "pre-revenue", "complicates"
        negative_keywords = (
            "not ", "lack", "less ", "limit", "pre-revenue", "complicat",
            "does not", "no ", "negative", "better captured", "favour",
        )
        positives = [r for r in reasons if not any(kw in r.lower() for kw in negative_keywords)]
        negatives = [r for r in reasons if any(kw in r.lower() for kw in negative_keywords)]

        if positives and not negatives:
            joined = ", ".join(positives)
            return f"{label} is well-suited for {ticker} due to {joined}."
        elif negatives and not positives:
            joined = ", ".join(negatives)
            return f"{label} is less suitable for {ticker} due to {joined}."
        elif positives and negatives:
            pos_joined = ", ".join(positives)
            neg_joined = ", ".join(negatives)
            return (
                f"{label} has some applicability for {ticker} given {pos_joined}, "
                f"but is tempered by {neg_joined}."
            )
        else:
            return f"Insufficient data to evaluate {label} for {ticker}."
