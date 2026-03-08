"""DDM Valuation Engine — Design Section 2.

Three-stage, two-stage, and Gordon Growth dividend discount models
with dividend sustainability analysis (6 metrics).
"""

from __future__ import annotations

import logging

from .models import (
    DDMResult, DDMScenarioResult, DividendYearRow,
    DDMMetadata, DividendSustainability, SustainabilityMetric,
)
from .engine_utils import upside_downside, safe_div
from services.assumption_engine.models import (
    AssumptionSet, ScenarioProjections, DDMAssumptions,
)
from .base_model import BaseValuationModel

logger = logging.getLogger("finance_app")


class DDMEngine(BaseValuationModel):
    """Dividend Discount Model valuation engine.

    Supports Gordon Growth, two-stage, and three-stage variants
    with per-scenario cost-of-equity and dividend growth adjustments.

    Entry point: ``DDMEngine.run(assumption_set, data, current_price)``
    """

    model_type = "ddm"
    display_name = "DDM"

    @staticmethod
    def get_required_assumptions() -> list[str]:
        return [
            "model_assumptions.ddm.current_annual_dividend_per_share",
            "model_assumptions.ddm.dividend_growth_rate_near_term",
            "model_assumptions.ddm.cost_of_equity",
        ]

    @staticmethod
    def validate_assumptions(assumption_set: AssumptionSet) -> list[str]:
        errors: list[str] = []
        ddm = assumption_set.model_assumptions.ddm
        if ddm is None:
            errors.append("DDM assumptions not set")
            return errors
        if ddm.current_annual_dividend_per_share <= 0:
            errors.append("Current dividend must be positive")
        if ddm.cost_of_equity <= 0:
            errors.append("Cost of equity must be positive")
        return errors

    @staticmethod
    def run(
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
    ) -> DDMResult:
        """Run DDM valuation across all scenarios."""
        ticker = assumption_set.ticker
        ddm = assumption_set.model_assumptions.ddm
        scenario_set = assumption_set.scenarios

        # --- Applicability check ---
        if ddm is None:
            return DDMResult(
                ticker=ticker,
                applicable=False,
                reason="Company does not pay dividends",
                current_price=current_price,
            )
        if scenario_set is None:
            return DDMResult(
                ticker=ticker,
                applicable=False,
                reason="No scenario data available",
                current_price=current_price,
            )

        # --- Run each scenario ---
        scenario_results: dict[str, DDMScenarioResult] = {}
        for name, scenario in [
            ("base", scenario_set.base),
            ("bull", scenario_set.bull),
            ("bear", scenario_set.bear),
        ]:
            scenario_results[name] = DDMEngine._run_scenario(
                name, scenario, ddm, current_price,
            )

        # --- Weighted average ---
        weighted_value = sum(
            r.intrinsic_value_per_share * r.scenario_weight
            for r in scenario_results.values()
        )
        weighted_ud = upside_downside(weighted_value, current_price)

        # --- Sustainability analysis ---
        sustainability = DDMEngine._analyze_sustainability(ddm, data)

        return DDMResult(
            ticker=ticker,
            applicable=True,
            current_price=current_price,
            scenarios=scenario_results,
            weighted_intrinsic_value=round(weighted_value, 2),
            weighted_upside_downside_pct=(
                round(weighted_ud, 4) if weighted_ud is not None else None
            ),
            sustainability=sustainability,
            metadata=DDMMetadata(
                ddm_variant=ddm.model_type,
                cost_of_equity=round(scenario_set.base.cost_of_equity, 4),
            ),
        )

    # ------------------------------------------------------------------
    # Scenario dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def _run_scenario(
        name: str,
        scenario: ScenarioProjections,
        ddm: DDMAssumptions,
        current_price: float,
    ) -> DDMScenarioResult:
        """Run DDM for a single scenario."""
        ke = scenario.cost_of_equity

        # Adjust near-term dividend growth per scenario
        base_near_g = ddm.dividend_growth_rate_near_term
        terminal_g = ddm.dividend_growth_rate_terminal

        if name == "bull":
            near_g = base_near_g * 1.15
        elif name == "bear":
            near_g = base_near_g * 0.85
        else:
            near_g = base_near_g

        # Ensure terminal_g < ke (perpetuity constraint)
        if terminal_g >= ke:
            terminal_g = ke * 0.80

        if ddm.model_type == "gordon":
            return DDMEngine._gordon_growth(
                name, scenario, ddm, ke, terminal_g, current_price,
            )
        elif ddm.model_type == "three_stage":
            return DDMEngine._three_stage(
                name, scenario, ddm, ke, near_g, terminal_g, current_price,
            )
        else:
            return DDMEngine._two_stage(
                name, scenario, ddm, ke, near_g, terminal_g, current_price,
            )

    # ------------------------------------------------------------------
    # Gordon Growth Model
    # ------------------------------------------------------------------

    @staticmethod
    def _gordon_growth(
        name: str,
        scenario: ScenarioProjections,
        ddm: DDMAssumptions,
        ke: float,
        terminal_g: float,
        current_price: float,
    ) -> DDMScenarioResult:
        """P = D1 / (ke - g)."""
        d0 = ddm.current_annual_dividend_per_share
        g = terminal_g
        d1 = d0 * (1 + g)

        if ke <= g:
            intrinsic = d1 * 100  # Fallback: very high
        else:
            intrinsic = d1 / (ke - g)

        schedule = [DividendYearRow(
            year=1, stage="terminal",
            dps=round(d1, 4),
            growth_rate=round(g, 4),
            discount_factor=round(1 / (1 + ke), 6),
            pv=round(d1 / (1 + ke), 4),
        )]

        ud = upside_downside(intrinsic, current_price)
        return DDMScenarioResult(
            scenario_name=name,
            scenario_weight=scenario.scenario_weight,
            intrinsic_value_per_share=round(intrinsic, 2),
            upside_downside_pct=round(ud, 4) if ud is not None else None,
            pv_stage1=0.0,
            pv_stage2=None,
            pv_terminal=round(intrinsic, 2),
            tv_pct_of_total=1.0,
            dividend_growth_near_term=round(g, 4),
            dividend_growth_terminal=round(g, 4),
            dividend_schedule=schedule,
        )

    # ------------------------------------------------------------------
    # Two-Stage DDM
    # ------------------------------------------------------------------

    @staticmethod
    def _two_stage(
        name: str,
        scenario: ScenarioProjections,
        ddm: DDMAssumptions,
        ke: float,
        near_g: float,
        terminal_g: float,
        current_price: float,
    ) -> DDMScenarioResult:
        """Stage 1: high growth (years 1-5), Stage 2: terminal perpetuity."""
        d0 = ddm.current_annual_dividend_per_share
        schedule: list[DividendYearRow] = []
        pv_stage1 = 0.0
        dps = d0

        # Stage 1: years 1-5
        for t in range(1, 6):
            dps = dps * (1 + near_g)
            df = 1.0 / (1 + ke) ** t
            pv = dps * df
            pv_stage1 += pv
            schedule.append(DividendYearRow(
                year=t, stage="high_growth",
                dps=round(dps, 4), growth_rate=round(near_g, 4),
                discount_factor=round(df, 6), pv=round(pv, 4),
            ))

        # Terminal value at end of year 5
        d6 = dps * (1 + terminal_g)
        if ke > terminal_g:
            tv = d6 / (ke - terminal_g)
        else:
            tv = d6 * 100
        pv_terminal = tv / (1 + ke) ** 5

        schedule.append(DividendYearRow(
            year=6, stage="terminal",
            dps=round(d6, 4), growth_rate=round(terminal_g, 4),
            discount_factor=round(1.0 / (1 + ke) ** 6, 6),
            pv=round(d6 / (1 + ke) ** 6, 4),
        ))

        intrinsic = pv_stage1 + pv_terminal
        tv_pct = safe_div(pv_terminal, intrinsic) or 0
        ud = upside_downside(intrinsic, current_price)

        return DDMScenarioResult(
            scenario_name=name,
            scenario_weight=scenario.scenario_weight,
            intrinsic_value_per_share=round(intrinsic, 2),
            upside_downside_pct=round(ud, 4) if ud is not None else None,
            pv_stage1=round(pv_stage1, 2),
            pv_stage2=None,
            pv_terminal=round(pv_terminal, 2),
            tv_pct_of_total=round(tv_pct, 4),
            dividend_growth_near_term=round(near_g, 4),
            dividend_growth_terminal=round(terminal_g, 4),
            dividend_schedule=schedule,
        )

    # ------------------------------------------------------------------
    # Three-Stage DDM
    # ------------------------------------------------------------------

    @staticmethod
    def _three_stage(
        name: str,
        scenario: ScenarioProjections,
        ddm: DDMAssumptions,
        ke: float,
        near_g: float,
        terminal_g: float,
        current_price: float,
    ) -> DDMScenarioResult:
        """Stage 1: high growth (1-5), Stage 2: transition (6-8), Stage 3: terminal (9+)."""
        d0 = ddm.current_annual_dividend_per_share
        schedule: list[DividendYearRow] = []
        pv_stage1 = 0.0
        pv_stage2 = 0.0
        dps = d0

        # Stage 1: years 1-5
        for t in range(1, 6):
            dps = dps * (1 + near_g)
            df = 1.0 / (1 + ke) ** t
            pv = dps * df
            pv_stage1 += pv
            schedule.append(DividendYearRow(
                year=t, stage="high_growth",
                dps=round(dps, 4), growth_rate=round(near_g, 4),
                discount_factor=round(df, 6), pv=round(pv, 4),
            ))

        # Stage 2: years 6-8, linear fade from near_g to terminal_g
        transition_years = 3
        for i in range(transition_years):
            t = 6 + i
            frac = (i + 1) / (transition_years + 1)
            g = near_g + (terminal_g - near_g) * frac
            dps = dps * (1 + g)
            df = 1.0 / (1 + ke) ** t
            pv = dps * df
            pv_stage2 += pv
            schedule.append(DividendYearRow(
                year=t, stage="transition",
                dps=round(dps, 4), growth_rate=round(g, 4),
                discount_factor=round(df, 6), pv=round(pv, 4),
            ))

        # Terminal value at end of year 8
        d9 = dps * (1 + terminal_g)
        if ke > terminal_g:
            tv = d9 / (ke - terminal_g)
        else:
            tv = d9 * 100
        pv_terminal = tv / (1 + ke) ** 8

        schedule.append(DividendYearRow(
            year=9, stage="terminal",
            dps=round(d9, 4), growth_rate=round(terminal_g, 4),
            discount_factor=round(1.0 / (1 + ke) ** 9, 6),
            pv=round(d9 / (1 + ke) ** 9, 4),
        ))

        intrinsic = pv_stage1 + pv_stage2 + pv_terminal
        tv_pct = safe_div(pv_terminal, intrinsic) or 0
        ud = upside_downside(intrinsic, current_price)

        return DDMScenarioResult(
            scenario_name=name,
            scenario_weight=scenario.scenario_weight,
            intrinsic_value_per_share=round(intrinsic, 2),
            upside_downside_pct=round(ud, 4) if ud is not None else None,
            pv_stage1=round(pv_stage1, 2),
            pv_stage2=round(pv_stage2, 2),
            pv_terminal=round(pv_terminal, 2),
            tv_pct_of_total=round(tv_pct, 4),
            dividend_growth_near_term=round(near_g, 4),
            dividend_growth_terminal=round(terminal_g, 4),
            dividend_schedule=schedule,
        )

    # ------------------------------------------------------------------
    # Sustainability analysis (6 metrics)
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_sustainability(
        ddm: DDMAssumptions,
        data: dict,
    ) -> DividendSustainability:
        """Analyze dividend sustainability using 6 metrics."""
        metrics: list[SustainabilityMetric] = []
        financials = data.get("annual_financials", [])
        latest = financials[-1] if financials else {}

        # 1. Payout ratio
        payout = ddm.payout_ratio_current
        if payout is not None:
            if payout < 0.60:
                status, desc = "green", f"Payout ratio {payout:.0%} is sustainable"
            elif payout < 0.85:
                status, desc = "yellow", f"Payout ratio {payout:.0%} is moderate"
            else:
                status, desc = "red", f"Payout ratio {payout:.0%} is unsustainably high"
            metrics.append(SustainabilityMetric(
                name="payout_ratio", value=round(payout, 4),
                status=status, description=desc,
            ))

        # 2. FCF coverage
        fcf = latest.get("free_cash_flow")
        divs = latest.get("dividends_paid")
        if fcf and divs and divs != 0:
            coverage = abs(fcf / divs)
            if coverage > 1.5:
                status, desc = "green", f"FCF covers dividends {coverage:.1f}x"
            elif coverage > 1.0:
                status, desc = "yellow", f"FCF covers dividends {coverage:.1f}x — tight"
            else:
                status, desc = "red", f"FCF does not cover dividends ({coverage:.1f}x)"
            metrics.append(SustainabilityMetric(
                name="fcf_coverage", value=round(coverage, 4),
                status=status, description=desc,
            ))

        # 3. Growth vs cost of equity
        g = ddm.dividend_growth_rate_near_term
        ke = ddm.cost_of_equity
        if g < ke:
            status = "green"
            desc = f"Growth ({g:.1%}) below cost of equity ({ke:.1%})"
        else:
            status = "red"
            desc = f"Growth ({g:.1%}) exceeds cost of equity ({ke:.1%})"
        metrics.append(SustainabilityMetric(
            name="growth_vs_ke", value=round(g, 4),
            status=status, description=desc,
        ))

        # 4. Dividend streak (consecutive years of payments)
        streak = 0
        for row in reversed(financials):
            d = row.get("dividends_paid")
            if d is not None and d != 0:
                streak += 1
            else:
                break
        if streak >= 10:
            status, desc = "green", f"{streak}-year dividend streak"
        elif streak >= 5:
            status, desc = "yellow", f"{streak}-year dividend streak"
        else:
            status, desc = "red", f"Only {streak}-year dividend streak"
        metrics.append(SustainabilityMetric(
            name="dividend_streak", value=float(streak),
            status=status, description=desc,
        ))

        # 5. Dividend consistency (count of YoY cuts)
        div_amounts: list[float] = []
        for row in financials:
            d = row.get("dividends_paid")
            if d is not None and d != 0:
                div_amounts.append(abs(d))

        cuts = 0
        if len(div_amounts) >= 2:
            for i in range(1, len(div_amounts)):
                if div_amounts[i] < div_amounts[i - 1] * 0.95:
                    cuts += 1

        if cuts == 0 and len(div_amounts) >= 3:
            status, desc = "green", "No dividend cuts in history"
        elif cuts <= 1:
            status, desc = "yellow", f"{cuts} dividend cut(s) in history"
        else:
            status, desc = "red", f"{cuts} dividend cuts in history"
        metrics.append(SustainabilityMetric(
            name="consistency", value=float(cuts),
            status=status, description=desc,
        ))

        # 6. Growth trend
        if len(div_amounts) >= 3:
            recent_growth = (
                (div_amounts[-1] / div_amounts[-2] - 1)
                if div_amounts[-2] > 0 else 0
            )
            if recent_growth > 0:
                status, desc = "green", f"Recent dividend growth of {recent_growth:.1%}"
            elif recent_growth > -0.05:
                status, desc = "yellow", f"Flat dividend growth ({recent_growth:.1%})"
            else:
                status, desc = "red", f"Recent dividend decline of {recent_growth:.1%}"
            metrics.append(SustainabilityMetric(
                name="growth_trend", value=round(recent_growth, 4),
                status=status, description=desc,
            ))

        # Overall health
        red_count = sum(1 for m in metrics if m.status == "red")
        green_count = sum(1 for m in metrics if m.status == "green")

        if red_count >= 2:
            overall = "at_risk"
        elif metrics and green_count >= len(metrics) * 0.6:
            overall = "healthy"
        else:
            overall = "caution"

        return DividendSustainability(metrics=metrics, overall_health=overall)
