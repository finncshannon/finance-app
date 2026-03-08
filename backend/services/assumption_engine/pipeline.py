"""AssumptionEngine — orchestrates GATHER → ANALYZE → SYNTHESIZE → OUTPUT.

This is the main entry point for generating valuation assumptions.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone

from db.connection import DatabaseConnection
from repositories.company_repo import CompanyRepo
from repositories.market_data_repo import MarketDataRepo
from services.market_data_service import MarketDataService

from .confidence import score_confidence
from .config import EngineConfig
from .data_package import InsufficientDataError, gather_company_data
from .helpers import clamp, compute_nwc_changes
from .margins import project_margins
from .model_mappers import map_all_models
from .models import (
    AssumptionMetadata,
    AssumptionSet,
    CompanyDataPackage,
    ScenarioSet,
    TrialParameters,
)
from .reasoning import generate_reasoning
from .revenue import project_revenue
from .scenarios import generate_scenarios
from .wacc import calculate_wacc

logger = logging.getLogger("finance_app")


class AssumptionEngine:
    """Main engine class — generates complete assumption sets.

    Usage:
        engine = AssumptionEngine(db, market_data_svc)
        result = await engine.generate_assumptions("AAPL", "dcf")
    """

    def __init__(
        self,
        db: DatabaseConnection,
        market_data_svc: MarketDataService,
        settings_service=None,
    ):
        self.db = db
        self.market_data_svc = market_data_svc
        self.company_repo = CompanyRepo(db)
        self.market_data_repo = MarketDataRepo(db)
        self._settings_service = settings_service

    async def generate_assumptions(
        self,
        ticker: str,
        model_type: str | None = None,
        overrides: dict | None = None,
        trial_params: TrialParameters | None = None,
    ) -> AssumptionSet:
        """Generate a complete assumption set for a ticker.

        Args:
            ticker: Stock ticker symbol.
            model_type: Optional model type hint ("dcf", "ddm", etc.).
            overrides: Optional dict of user overrides (dotted keys).

        Returns:
            AssumptionSet with scenarios, model assumptions, confidence,
            and reasoning.
        """
        ticker = ticker.upper()
        overrides = overrides or {}
        warnings: list[str] = []
        data_gaps: list[str] = []

        # Load config
        config = await EngineConfig.from_settings(self._settings_service)

        # ---- GATHER ----
        logger.info("GATHER: assembling data package for %s", ticker)
        try:
            data = await gather_company_data(
                ticker,
                company_repo=self.company_repo,
                market_data_repo=self.market_data_repo,
                market_data_svc=self.market_data_svc,
            )
        except InsufficientDataError as exc:
            logger.warning("Insufficient data for %s: %s", ticker, exc)
            return self._fallback_result(ticker, str(exc))

        # Track data gaps
        data_gaps = self._identify_data_gaps(data)

        # ---- ANALYZE ----
        logger.info(
            "ANALYZE: %s — %d years, sector=%s, regime detection...",
            ticker, data.years_available, data.company_profile.sector,
        )

        # Revenue projection
        revenue = project_revenue(data, trial_params=trial_params)
        logger.info(
            "Revenue: regime=%s, starting=%.2f%%, terminal=%.2f%%",
            revenue.regime,
            revenue.starting_growth_rate * 100,
            revenue.terminal_growth_rate * 100,
        )

        # Margin projections
        margin_results = project_margins(data, revenue.regime, trial_params=trial_params)

        # WACC
        wacc_result = calculate_wacc(data, trial_params=trial_params)
        logger.info("WACC: %.2f%% (Ke=%.2f%%)", wacc_result.wacc * 100, wacc_result.cost_of_equity * 100)
        warnings.extend(wacc_result.warnings)

        # Check for WACC component overrides
        wacc_overrides = {
            k.replace("wacc_breakdown.", ""): v
            for k, v in overrides.items()
            if k.startswith("wacc_breakdown.")
        }
        if wacc_overrides:
            from .wacc import calculate_wacc_from_overrides
            wacc_result = calculate_wacc_from_overrides(wacc_result, wacc_overrides)
            logger.info("WACC recomputed from %d override(s)", len(wacc_overrides))
            warnings.append(f"WACC computed from {len(wacc_overrides)} user override(s)")

        # ---- SYNTHESIZE ----
        logger.info("SYNTHESIZE: building scenarios for %s", ticker)

        # Compute CapEx and NWC ratios
        capex_ratio = self._compute_capex_ratio(data)
        nwc_ratio = self._compute_nwc_ratio(data)

        # Scenario generation
        scenarios = generate_scenarios(
            data, revenue, margin_results, wacc_result, capex_ratio, nwc_ratio,
        )
        logger.info(
            "Scenarios: uncertainty=%.2f, spread=%.2f%%",
            scenarios.uncertainty_score, scenarios.spread * 100,
        )

        # Model-specific mappings
        model_assumptions = map_all_models(data, scenarios.base, revenue, wacc_result)

        # Confidence scoring
        confidence = score_confidence(data, revenue, margin_results, wacc_result)
        logger.info("Confidence: overall=%.1f/100", confidence.overall_score)

        # Reasoning
        reasoning = generate_reasoning(data, revenue, margin_results, wacc_result, scenarios)

        # ---- OUTPUT ----
        # Apply user overrides (post-synthesis)
        overrides_applied = self._apply_overrides(scenarios, overrides)

        # Track WACC component overrides
        for k in overrides:
            if k.startswith("wacc_breakdown."):
                overrides_applied.append(k)

        # Data quality score (0–1)
        dq_score = confidence.overall_score / 100.0

        result = AssumptionSet(
            ticker=ticker,
            generated_at=datetime.now(timezone.utc),
            data_quality_score=round(dq_score, 3),
            years_of_data=data.years_available,
            overrides_applied=overrides_applied,
            scenarios=scenarios,
            model_assumptions=model_assumptions,
            wacc_breakdown=wacc_result,
            confidence=confidence,
            reasoning=reasoning,
            metadata=AssumptionMetadata(
                regime=revenue.regime,
                uncertainty_score=scenarios.uncertainty_score,
                data_gaps=data_gaps,
                warnings=warnings,
            ),
        )

        logger.info(
            "OUTPUT: %s assumption set complete — %d years, regime=%s, "
            "confidence=%.1f, %d overrides",
            ticker, data.years_available, revenue.regime,
            confidence.overall_score, len(overrides_applied),
        )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_capex_ratio(data: CompanyDataPackage) -> float:
        """Average capex/revenue over last 3 years."""
        ratios: list[float] = []
        for row in data.annual_financials[-3:]:
            capex = row.get("capex") or row.get("capital_expenditure")
            revenue = row.get("revenue")
            if capex is not None and revenue and revenue > 0:
                ratios.append(abs(capex) / revenue)
        return round(statistics.mean(ratios), 4) if ratios else 0.05

    @staticmethod
    def _compute_nwc_ratio(data: CompanyDataPackage) -> float:
        """Average NWC change / revenue."""
        changes = compute_nwc_changes(data.annual_financials)
        if changes:
            return round(statistics.mean(changes), 4)
        return 0.02

    @staticmethod
    def _identify_data_gaps(data: CompanyDataPackage) -> list[str]:
        """Identify missing data fields for metadata."""
        gaps: list[str] = []

        if data.quote_data.beta is None:
            gaps.append("beta")
        if data.quote_data.enterprise_value is None:
            gaps.append("enterprise_value")
        if data.analyst_estimates.revenue_growth_estimate is None:
            gaps.append("analyst_estimates")

        # Check latest financial row
        if data.annual_financials:
            latest = data.annual_financials[-1]
            for field in ("free_cash_flow", "dividends_paid", "interest_expense"):
                if latest.get(field) is None:
                    gaps.append(field)

        return gaps

    @staticmethod
    def _apply_overrides(
        scenarios: ScenarioSet,
        overrides: dict,
    ) -> list[str]:
        """Apply user overrides to scenarios. Returns list of applied keys."""
        applied: list[str] = []

        for key, value in overrides.items():
            if key.startswith("wacc_breakdown."):
                continue  # handled in pipeline before scenario generation
            parts = key.split(".", 1)
            if len(parts) == 2:
                scenario_name, field = parts
                scenario = getattr(scenarios, scenario_name, None)
                if scenario and hasattr(scenario, field):
                    setattr(scenario, field, value)
                    applied.append(key)
                    logger.info("Override applied: %s = %s", key, value)
            elif hasattr(scenarios.base, key):
                # Apply to base scenario
                setattr(scenarios.base, key, value)
                applied.append(key)
                logger.info("Override applied to base: %s = %s", key, value)

        return applied

    @staticmethod
    def _fallback_result(ticker: str, error_msg: str) -> AssumptionSet:
        """Return a minimal AssumptionSet when data is insufficient."""
        return AssumptionSet(
            ticker=ticker,
            generated_at=datetime.now(timezone.utc),
            data_quality_score=0.0,
            years_of_data=0,
            metadata=AssumptionMetadata(
                regime="unknown",
                uncertainty_score=1.0,
                data_gaps=["insufficient_data"],
                warnings=[error_msg],
            ),
        )

    async def generate_assumptions_mc(
        self,
        ticker: str,
        n_trials: int = 100,
        seed: int | None = None,
        overrides: dict | None = None,
    ) -> AssumptionSet:
        """Generate assumptions using Monte Carlo method.

        Falls back to deterministic if MC fails or insufficient data.
        """
        from .monte_carlo import generate_assumptions_monte_carlo
        from .constants import MC_MIN_YEARS_FOR_MC

        ticker = ticker.upper()

        # Check if MC is viable by doing a quick data check
        try:
            data = await gather_company_data(
                ticker,
                company_repo=self.company_repo,
                market_data_repo=self.market_data_repo,
                market_data_svc=self.market_data_svc,
            )
            if data.years_available < MC_MIN_YEARS_FOR_MC:
                logger.info(
                    "MC skipped for %s: only %d years of data",
                    ticker, data.years_available,
                )
                return await self.generate_assumptions(ticker, overrides=overrides)
        except Exception:
            logger.warning("MC data check failed for %s, falling back", ticker)
            return await self.generate_assumptions(ticker, overrides=overrides)

        try:
            mc_result = await generate_assumptions_monte_carlo(
                engine=self,
                ticker=ticker,
                n_trials=n_trials,
                seed=seed,
                overrides=overrides,
            )
            return mc_result.final_assumptions
        except Exception as exc:
            logger.warning(
                "MC failed for %s, falling back to deterministic: %s",
                ticker, exc,
            )
            return await self.generate_assumptions(ticker, overrides=overrides)
