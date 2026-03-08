"""DCF sensitivity parameter definitions — the 8 slider parameters."""

from __future__ import annotations

from .models import SensitivityParameterDef

# fmt: off
DCF_PARAMETERS: list[SensitivityParameterDef] = [
    SensitivityParameterDef(
        name="WACC", key_path="scenarios.{s}.wacc",
        param_type="float_pct", min_val=0.04, max_val=0.20,
        step=0.001, display_format="{:.2%}",
    ),
    SensitivityParameterDef(
        name="Terminal Growth Rate", key_path="scenarios.{s}.terminal_growth_rate",
        param_type="float_pct", min_val=0.00, max_val=0.05,
        step=0.001, display_format="{:.2%}",
    ),
    SensitivityParameterDef(
        name="Revenue Growth Y1", key_path="scenarios.{s}.revenue_growth_rates[0]",
        param_type="float_pct", min_val=-0.10, max_val=0.60,
        step=0.005, display_format="{:.1%}",
    ),
    SensitivityParameterDef(
        name="Operating Margin Y1", key_path="scenarios.{s}.operating_margins[0]",
        param_type="float_pct", min_val=-0.20, max_val=0.60,
        step=0.005, display_format="{:.1%}",
    ),
    SensitivityParameterDef(
        name="CapEx / Revenue", key_path="model_assumptions.dcf.capex_to_revenue",
        param_type="float_ratio", min_val=0.01, max_val=0.25,
        step=0.001, display_format="{:.2%}",
    ),
    SensitivityParameterDef(
        name="Tax Rate", key_path="model_assumptions.dcf.tax_rate",
        param_type="float_pct", min_val=0.00, max_val=0.40,
        step=0.005, display_format="{:.1%}",
    ),
    SensitivityParameterDef(
        name="Exit Multiple (EV/EBITDA)", key_path="model_assumptions.dcf.terminal_exit_multiple",
        param_type="float_abs", min_val=4.0, max_val=30.0,
        step=0.1, display_format="{:.1f}x",
    ),
    SensitivityParameterDef(
        name="NWC Change / Revenue", key_path="model_assumptions.dcf.nwc_change_to_revenue",
        param_type="float_ratio", min_val=-0.05, max_val=0.10,
        step=0.001, display_format="{:.2%}",
    ),
]
# fmt: on


def get_dcf_parameter_defs() -> list[SensitivityParameterDef]:
    """Return DCF parameter definitions."""
    return DCF_PARAMETERS
