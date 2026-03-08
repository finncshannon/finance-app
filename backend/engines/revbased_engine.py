"""Revenue-Based Valuation Engine — Design Section 4.

Multiple trajectory (compression/expansion), exit multiple approach,
Rule of 40, growth-adjusted metrics, multi-scenario.
"""

from __future__ import annotations

import logging

from .models import (
    RevBasedResult, RevBasedScenarioResult, ExitYearResult,
    RuleOf40, GrowthMetrics, RevBasedMetadata,
)
from .engine_utils import (
    discount_factor, equity_bridge, upside_downside,
    extend_to_10_years, safe_div, clamp,
)
from services.assumption_engine.models import (
    AssumptionSet, ScenarioProjections, RevenueBasedAssumptions,
)
from .base_model import BaseValuationModel

logger = logging.getLogger("finance_app")


class RevBasedEngine(BaseValuationModel):
    """Revenue-Based valuation engine.

    Projects revenue, applies an EV/Revenue multiple trajectory,
    and computes exit valuations at multiple horizons.

    Entry point: ``RevBasedEngine.run(assumption_set, data, current_price)``
    """

    model_type = "revenue_based"
    display_name = "Revenue-Based"

    @staticmethod
    def get_required_assumptions() -> list[str]:
        return [
            "model_assumptions.revenue_based",
            "scenarios.base.revenue_growth_rates",
        ]

    @staticmethod
    def validate_assumptions(assumption_set: AssumptionSet) -> list[str]:
        errors: list[str] = []
        if assumption_set.model_assumptions.revenue_based is None:
            errors.append("Revenue-Based assumptions not set")
        if not assumption_set.scenarios:
            errors.append("Scenario projections required")
        return errors

    @staticmethod
    def run(
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
    ) -> RevBasedResult:
        """Run revenue-based valuation across all scenarios."""
        ticker = assumption_set.ticker
        rev_assumptions = assumption_set.model_assumptions.revenue_based
        scenario_set = assumption_set.scenarios
        warnings: list[str] = []

        if rev_assumptions is None or scenario_set is None:
            return RevBasedResult(
                ticker=ticker, current_price=current_price,
                metadata=RevBasedMetadata(warnings=["Missing revenue-based assumptions"]),
            )

        # --- Run each scenario ---
        scenario_results: dict[str, RevBasedScenarioResult] = {}
        for name, scenario in [
            ("base", scenario_set.base),
            ("bull", scenario_set.bull),
            ("bear", scenario_set.bear),
        ]:
            scenario_results[name] = RevBasedEngine._run_scenario(
                name, scenario, rev_assumptions, current_price, warnings,
            )

        # --- Weighted averages ---
        weighted_price = sum(
            r.primary_implied_price * r.scenario_weight
            for r in scenario_results.values()
        )
        weighted_ud = upside_downside(weighted_price, current_price)

        # --- Growth metrics ---
        growth_metrics = RevBasedEngine._compute_growth_metrics(
            data, rev_assumptions, scenario_set.base,
        )

        # --- Profitability trajectory ---
        prof_traj = RevBasedEngine._profitability_trajectory(scenario_set.base)

        # --- Multiple direction ---
        current_ev_rev = rev_assumptions.current_ev_revenue or 0
        terminal_ev_rev = rev_assumptions.terminal_ev_revenue or 0
        if terminal_ev_rev > current_ev_rev * 1.05:
            direction = "expanding"
        elif terminal_ev_rev < current_ev_rev * 0.95:
            direction = "compressing"
        else:
            direction = "stable"

        return RevBasedResult(
            ticker=ticker,
            current_price=current_price,
            scenarios=scenario_results,
            weighted_implied_price=round(weighted_price, 2),
            weighted_upside_downside_pct=(
                round(weighted_ud, 4) if weighted_ud is not None else None
            ),
            growth_metrics=growth_metrics,
            profitability_trajectory=prof_traj,
            metadata=RevBasedMetadata(
                multiple_direction=direction,
                warnings=warnings,
            ),
        )

    # ------------------------------------------------------------------
    # Single scenario
    # ------------------------------------------------------------------

    @staticmethod
    def _run_scenario(
        name: str,
        scenario: ScenarioProjections,
        rev: RevenueBasedAssumptions,
        current_price: float,
        warnings: list[str],
    ) -> RevBasedScenarioResult:
        """Project revenue, build multiple trajectory, compute exit valuations."""
        wacc = scenario.wacc
        base_revenue = rev.base_revenue or 0
        shares = rev.shares_outstanding or 1
        net_debt = rev.net_debt or 0

        if base_revenue <= 0:
            warnings.append(f"No base revenue for {name} scenario")
            return RevBasedScenarioResult(
                scenario_name=name,
                scenario_weight=scenario.scenario_weight,
            )

        # --- Revenue projection (5 years) ---
        growth_rates = list(scenario.revenue_growth_rates[:5])
        while len(growth_rates) < 5:
            growth_rates.append(growth_rates[-1] if growth_rates else 0.05)

        projected_revenue: list[float] = []
        prev_rev = base_revenue
        for g in growth_rates:
            rev_val = prev_rev * (1 + g)
            projected_revenue.append(round(rev_val, 2))
            prev_rev = rev_val

        # --- Multiple trajectory (fade from current to terminal) ---
        current_multiple = rev.current_ev_revenue or 2.0
        terminal_multiple = rev.terminal_ev_revenue or current_multiple
        multiples: list[float] = []
        for t in range(5):
            frac = (t + 1) / 5
            m = current_multiple + (terminal_multiple - current_multiple) * frac
            multiples.append(round(m, 4))

        # --- Exit valuations at each year ---
        exits: list[ExitYearResult] = []
        for t in range(5):
            year = t + 1
            exit_rev = projected_revenue[t]
            exit_mult = multiples[t]
            exit_ev = exit_rev * exit_mult
            df = discount_factor(wacc, year)
            pv_ev = exit_ev * df
            pv_equity = pv_ev - net_debt * df
            imp_price = max(0, pv_equity / shares)

            exits.append(ExitYearResult(
                exit_year=year,
                exit_revenue=round(exit_rev, 2),
                exit_multiple=round(exit_mult, 4),
                exit_ev=round(exit_ev, 2),
                discount_factor=round(df, 6),
                pv_exit_ev=round(pv_ev, 2),
                pv_equity=round(pv_equity, 2),
                implied_price=round(imp_price, 2),
            ))

        # --- Primary implied price: terminal year exit ---
        primary_price = exits[-1].implied_price if exits else 0

        # --- Average exit price across all years ---
        avg_exit = (
            round(sum(e.implied_price for e in exits) / len(exits), 2)
            if exits else 0
        )

        # --- Current multiple implied price ---
        current_mult_price = None
        if current_multiple > 0:
            current_ev = base_revenue * current_multiple
            current_equity = current_ev - net_debt
            current_mult_price = round(max(0, current_equity / shares), 2)

        ud = upside_downside(primary_price, current_price)

        return RevBasedScenarioResult(
            scenario_name=name,
            scenario_weight=scenario.scenario_weight,
            projected_revenue=projected_revenue,
            revenue_growth_rates=[round(g, 4) for g in growth_rates],
            multiples_by_year=[round(m, 4) for m in multiples],
            terminal_ev_revenue=round(terminal_multiple, 4),
            exit_valuations=exits,
            primary_implied_price=round(primary_price, 2),
            avg_exit_price=avg_exit,
            current_multiple_price=current_mult_price,
            upside_downside_pct=round(ud, 4) if ud is not None else None,
        )

    # ------------------------------------------------------------------
    # Growth metrics
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_growth_metrics(
        data: dict,
        rev: RevenueBasedAssumptions,
        base_scenario: ScenarioProjections,
    ) -> GrowthMetrics:
        """Compute Rule of 40, EV/ARR, magic number, PSG ratio."""
        latest = {}
        financials = data.get("annual_financials", [])
        if financials:
            latest = financials[-1]

        growth_rate = (
            base_scenario.revenue_growth_rates[0]
            if base_scenario.revenue_growth_rates else 0
        )
        op_margin = (
            base_scenario.operating_margins[0]
            if base_scenario.operating_margins else 0
        )

        # Rule of 40
        growth_pct = growth_rate * 100
        margin_pct = op_margin * 100
        r40_score = growth_pct + margin_pct
        r40_status = "pass" if r40_score >= 40 else "fail"
        rule_of_40 = RuleOf40(
            score=round(r40_score, 2),
            status=r40_status,
            revenue_growth_component=round(growth_pct, 2),
            margin_component=round(margin_pct, 2),
        )

        # EV/ARR (annual recurring revenue — use revenue as proxy)
        ev = rev.enterprise_value
        base_revenue = rev.base_revenue or 0
        ev_arr = round(ev / base_revenue, 2) if ev and base_revenue > 0 else None

        # Magic number: net new ARR / S&M spend (simplified: revenue growth $ / opex)
        magic_number = None
        magic_status = None
        if len(financials) >= 2:
            prev_rev = financials[-2].get("revenue")
            curr_rev = latest.get("revenue")
            opex = latest.get("operating_expense")
            if prev_rev and curr_rev and opex and opex > 0:
                net_new = curr_rev - prev_rev
                magic_number = round(net_new / abs(opex), 4)
                if magic_number > 0.75:
                    magic_status = "efficient"
                elif magic_number > 0.50:
                    magic_status = "moderate"
                else:
                    magic_status = "inefficient"

        # PSG ratio: P/S divided by growth rate
        psg = None
        if rev.current_ev_revenue and growth_rate > 0.01:
            psg = round(rev.current_ev_revenue / (growth_rate * 100), 4)

        return GrowthMetrics(
            rule_of_40=rule_of_40,
            ev_arr=ev_arr,
            magic_number=magic_number,
            magic_number_status=magic_status,
            psg_ratio=psg,
        )

    # ------------------------------------------------------------------
    # Profitability trajectory
    # ------------------------------------------------------------------

    @staticmethod
    def _profitability_trajectory(
        base_scenario: ScenarioProjections,
    ) -> dict:
        """Map margin trajectory over projection period."""
        margins = base_scenario.operating_margins or []
        fcf_margins = base_scenario.fcf_margins or []

        trajectory = {
            "operating_margins": [round(m, 4) for m in margins],
            "fcf_margins": [round(m, 4) for m in fcf_margins],
        }

        # Check if path to profitability
        if margins:
            if margins[0] < 0 and margins[-1] > 0:
                trajectory["path_to_profitability"] = True
                # Find crossover year
                for i, m in enumerate(margins):
                    if m > 0:
                        trajectory["breakeven_year"] = i + 1
                        break
            else:
                trajectory["path_to_profitability"] = margins[0] < 0

        return trajectory
