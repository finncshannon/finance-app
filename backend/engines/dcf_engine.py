"""DCF Valuation Engine — Design Section 1.

10-year discounted cash flow with line-item projection,
terminal value (perpetuity growth + exit multiple),
mid-year convention, equity bridge, waterfall, multi-scenario.
"""

from __future__ import annotations

import logging

from .models import (
    DCFResult, DCFScenarioResult, DCFYearRow,
    DCFWaterfall, WaterfallStep, DCFMetadata,
)
from .engine_utils import (
    discount_factor, equity_bridge, upside_downside,
    extend_to_10_years, safe_div,
)
from services.assumption_engine.models import (
    AssumptionSet, ScenarioProjections, DCFAssumptions,
)
from .base_model import BaseValuationModel

logger = logging.getLogger("finance_app")


class DCFEngine(BaseValuationModel):
    """Discounted Cash Flow valuation engine.

    Entry point: ``DCFEngine.run(assumption_set, data, current_price)``
    """

    model_type = "dcf"
    display_name = "DCF"

    @staticmethod
    def get_required_assumptions() -> list[str]:
        return [
            "model_assumptions.dcf.wacc",
            "model_assumptions.dcf.terminal_growth_rate",
            "scenarios.base.revenue_growth_rates",
            "scenarios.base.operating_margins",
        ]

    @staticmethod
    def validate_assumptions(assumption_set: AssumptionSet) -> list[str]:
        errors: list[str] = []
        dcf = assumption_set.model_assumptions.dcf
        if dcf is None:
            errors.append("DCF assumptions not set")
            return errors
        if dcf.wacc <= 0:
            errors.append("WACC must be positive")
        if dcf.terminal_growth_rate >= dcf.wacc:
            errors.append("Terminal growth must be less than WACC")
        if not assumption_set.scenarios:
            errors.append("Scenario projections required")
        return errors

    @staticmethod
    def run(
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
    ) -> DCFResult:
        """Run DCF valuation across base / bull / bear scenarios."""
        ticker = assumption_set.ticker
        dcf = assumption_set.model_assumptions.dcf
        scenario_set = assumption_set.scenarios
        warnings: list[str] = []

        if dcf is None or scenario_set is None:
            return DCFResult(
                ticker=ticker,
                current_price=current_price,
                metadata=DCFMetadata(warnings=["Missing DCF assumptions or scenarios"]),
            )

        # --- Run each scenario ---
        scenario_results: dict[str, DCFScenarioResult] = {}
        tv_perpetuity_base = 0.0
        tv_exit_base: float | None = None

        for name, scenario in [
            ("base", scenario_set.base),
            ("bull", scenario_set.bull),
            ("bear", scenario_set.bear),
        ]:
            result, tv_perp, tv_exit = DCFEngine._run_scenario(
                name, scenario, dcf, current_price, warnings,
            )
            scenario_results[name] = result
            if name == "base":
                tv_perpetuity_base = tv_perp
                tv_exit_base = tv_exit

        # --- Weighted averages ---
        weighted_price = sum(
            r.implied_price * r.scenario_weight
            for r in scenario_results.values()
        )
        weighted_ev = sum(
            r.enterprise_value * r.scenario_weight
            for r in scenario_results.values()
        )
        weighted_ud = upside_downside(weighted_price, current_price)

        # --- Waterfall from base scenario ---
        waterfall = DCFEngine._build_waterfall(scenario_results["base"], dcf)

        # --- Metadata ---
        tv_delta = None
        tv_delta_pct = None
        if tv_exit_base is not None and tv_perpetuity_base > 0:
            tv_delta = tv_exit_base - tv_perpetuity_base
            tv_delta_pct = safe_div(tv_delta, tv_perpetuity_base)

        metadata = DCFMetadata(
            projection_years=10,
            terminal_method=dcf.terminal_method,
            tv_perpetuity=round(tv_perpetuity_base, 2),
            tv_exit_multiple=round(tv_exit_base, 2) if tv_exit_base is not None else None,
            tv_delta=round(tv_delta, 2) if tv_delta is not None else None,
            tv_delta_pct=round(tv_delta_pct, 4) if tv_delta_pct is not None else None,
            warnings=warnings,
        )

        return DCFResult(
            ticker=ticker,
            current_price=current_price,
            scenarios=scenario_results,
            weighted_implied_price=round(weighted_price, 2),
            weighted_enterprise_value=round(weighted_ev, 2),
            weighted_upside_downside_pct=(
                round(weighted_ud, 4) if weighted_ud is not None else None
            ),
            waterfall=waterfall,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Single scenario
    # ------------------------------------------------------------------

    @staticmethod
    def _run_scenario(
        name: str,
        scenario: ScenarioProjections,
        dcf: DCFAssumptions,
        current_price: float,
        warnings: list[str],
    ) -> tuple[DCFScenarioResult, float, float | None]:
        """Project 10-year FCF, compute TV, discount, equity bridge.

        Returns ``(scenario_result, tv_perpetuity, tv_exit_or_None)``.
        """
        wacc = scenario.wacc
        terminal_g = scenario.terminal_growth_rate
        tax_rate = scenario.tax_rate

        # --- Extend 5-year assumptions to 10 years ---
        growth_10 = extend_to_10_years(
            scenario.revenue_growth_rates, terminal_g,
        )
        gross_margins_10 = extend_to_10_years(
            scenario.gross_margins,
            scenario.gross_margins[-1] if scenario.gross_margins else 0.30,
        )
        operating_margins_10 = extend_to_10_years(
            scenario.operating_margins,
            scenario.operating_margins[-1] if scenario.operating_margins else 0.15,
        )

        # Ratios (constant over projection)
        depr_ratio = dcf.depreciation_to_revenue
        capex_ratio = scenario.capex_to_revenue
        nwc_ratio = scenario.nwc_change_to_revenue

        base_revenue = dcf.base_revenue or 0
        if base_revenue <= 0:
            warnings.append(f"Base revenue missing for {name} scenario")
            base_revenue = 1.0

        # --- Year-by-year line-item projection ---
        rows: list[DCFYearRow] = []
        prev_revenue = base_revenue

        for t in range(10):
            year = t + 1
            growth = growth_10[t]
            revenue = prev_revenue * (1 + growth)

            gross_margin = gross_margins_10[t]
            gross_profit = revenue * gross_margin
            cogs = revenue - gross_profit

            op_margin = operating_margins_10[t]
            ebit = revenue * op_margin
            opex = gross_profit - ebit

            da = revenue * depr_ratio
            ebitda = ebit + da
            ebitda_margin = safe_div(ebitda, revenue) or 0

            taxes = max(0.0, ebit * tax_rate)
            nopat = ebit - taxes

            capex = revenue * capex_ratio
            nwc_change = revenue * nwc_ratio
            fcf = nopat + da - capex - nwc_change
            fcf_margin = safe_div(fcf, revenue) or 0

            # Mid-year convention: discount at (year - 0.5)
            df = discount_factor(wacc, year - 0.5)
            pv = fcf * df

            rows.append(DCFYearRow(
                year=year,
                revenue=round(revenue, 2),
                revenue_growth=round(growth, 4),
                cogs=round(cogs, 2),
                gross_profit=round(gross_profit, 2),
                gross_margin=round(gross_margin, 4),
                opex=round(opex, 2),
                ebit=round(ebit, 2),
                operating_margin=round(op_margin, 4),
                da=round(da, 2),
                ebitda=round(ebitda, 2),
                ebitda_margin=round(ebitda_margin, 4),
                taxes=round(taxes, 2),
                nopat=round(nopat, 2),
                capex=round(capex, 2),
                nwc_change=round(nwc_change, 2),
                fcf=round(fcf, 2),
                fcf_margin=round(fcf_margin, 4),
                discount_factor=round(df, 6),
                pv_fcf=round(pv, 2),
            ))
            prev_revenue = revenue

        # --- Terminal value: perpetuity growth ---
        last_fcf = rows[-1].fcf
        terminal_fcf = last_fcf * (1 + terminal_g)

        if wacc > terminal_g:
            tv_perpetuity = terminal_fcf / (wacc - terminal_g)
        else:
            tv_perpetuity = last_fcf * 20  # Fallback cap
            warnings.append(
                f"{name}: WACC ({wacc:.2%}) <= terminal growth ({terminal_g:.2%}), TV capped"
            )

        # --- Terminal value: exit multiple ---
        tv_exit: float | None = None
        if dcf.terminal_exit_multiple is not None and dcf.terminal_exit_multiple > 0:
            tv_exit = rows[-1].ebitda * dcf.terminal_exit_multiple

        # Choose based on configured method
        if dcf.terminal_method == "exit_multiple" and tv_exit is not None:
            tv = tv_exit
        else:
            tv = tv_perpetuity

        # Discount TV at end of year 10 (NOT mid-year)
        pv_tv = tv * discount_factor(wacc, 10)

        # --- Aggregate ---
        pv_fcf_total = sum(row.pv_fcf for row in rows)
        ev = pv_fcf_total + pv_tv

        # Equity bridge
        net_debt = dcf.net_debt or 0
        equity_val = equity_bridge(ev, net_debt)

        # Implied share price
        shares = dcf.shares_outstanding
        if not shares or shares <= 0:
            warnings.append(f"{name}: Missing shares outstanding")
            shares = 1.0
        implied_price = max(0.0, equity_val / shares)

        ud = upside_downside(implied_price, current_price)
        tv_pct = safe_div(pv_tv, ev) or 0

        result = DCFScenarioResult(
            scenario_name=name,
            scenario_weight=scenario.scenario_weight,
            projection_table=rows,
            enterprise_value=round(ev, 2),
            pv_fcf_total=round(pv_fcf_total, 2),
            pv_terminal_value=round(pv_tv, 2),
            tv_pct_of_ev=round(tv_pct, 4),
            equity_value=round(equity_val, 2),
            implied_price=round(implied_price, 2),
            upside_downside_pct=round(ud, 4) if ud is not None else None,
            wacc=round(wacc, 4),
            terminal_growth_rate=round(terminal_g, 4),
            terminal_exit_multiple=dcf.terminal_exit_multiple,
        )
        return result, tv_perpetuity, tv_exit

    # ------------------------------------------------------------------
    # Waterfall
    # ------------------------------------------------------------------

    @staticmethod
    def _build_waterfall(
        base: DCFScenarioResult,
        dcf: DCFAssumptions,
    ) -> DCFWaterfall:
        """Build waterfall chart data from the base scenario."""
        net_debt = dcf.net_debt or 0

        steps = [
            WaterfallStep(
                label="PV of Free Cash Flows",
                value=round(base.pv_fcf_total, 2),
                step_type="start",
            ),
            WaterfallStep(
                label="PV of Terminal Value",
                value=round(base.pv_terminal_value, 2),
                step_type="addition",
            ),
            WaterfallStep(
                label="Enterprise Value",
                value=round(base.enterprise_value, 2),
                step_type="subtotal",
            ),
        ]

        if net_debt > 0:
            steps.append(WaterfallStep(
                label="Less: Net Debt",
                value=round(-net_debt, 2),
                step_type="subtraction",
            ))
        elif net_debt < 0:
            # Net cash position
            steps.append(WaterfallStep(
                label="Plus: Net Cash",
                value=round(-net_debt, 2),
                step_type="addition",
            ))

        steps.append(WaterfallStep(
            label="Equity Value",
            value=round(base.equity_value, 2),
            step_type="end",
        ))

        return DCFWaterfall(steps=steps)
