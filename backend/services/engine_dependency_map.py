"""Engine dependency map — defines what financial fields each valuation engine requires.

Single source of truth. Referenced by DataReadinessService and diagnostic overlay.
Field names must exactly match cache.financial_data column names.
"""

ENGINE_DEPENDENCIES: dict[str, dict[str, list[dict]]] = {
    "dcf": {
        "critical": [
            {"field": "revenue", "label": "Revenue", "reason": "Base for 10-year projection"},
            {"field": "operating_cash_flow", "label": "Operating Cash Flow", "reason": "FCF derivation"},
            {"field": "capital_expenditure", "label": "Capital Expenditures", "reason": "FCF derivation"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share price calculation"},
        ],
        "important": [
            {"field": "net_debt", "label": "Net Debt", "reason": "Equity bridge (EV to equity)"},
            {"field": "total_debt", "label": "Total Debt", "reason": "WACC calculation"},
            {"field": "cash_and_equivalents", "label": "Cash", "reason": "Net debt derivation"},
            {"field": "ebit", "label": "EBIT", "reason": "Operating margin projection"},
            {"field": "gross_profit", "label": "Gross Profit", "reason": "Margin analysis"},
            {"field": "stockholders_equity", "label": "Equity", "reason": "WACC via CAPM"},
            {"field": "depreciation_amortization", "label": "D&A", "reason": "EBITDA and non-cash add-back"},
            {"field": "tax_provision", "label": "Tax Provision", "reason": "Effective tax rate"},
        ],
        "helpful": [
            {"field": "ebitda", "label": "EBITDA", "reason": "Terminal value exit multiple"},
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "Cross-check vs derived FCF"},
            {"field": "net_income", "label": "Net Income", "reason": "Profitability validation"},
        ],
    },
    "ddm": {
        "critical": [
            {"field": "dividends_paid", "label": "Dividends Paid", "reason": "Core DDM input — model impossible without dividend history"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Dividend per share calculation"},
        ],
        "important": [
            {"field": "net_income", "label": "Net Income", "reason": "Payout ratio and sustainability"},
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "Dividend coverage ratio"},
            {"field": "stockholders_equity", "label": "Equity", "reason": "ROE for sustainable growth"},
        ],
        "helpful": [
            {"field": "revenue", "label": "Revenue", "reason": "Growth context"},
            {"field": "operating_cash_flow", "label": "Operating Cash Flow", "reason": "Cash coverage validation"},
        ],
    },
    "comps": {
        "critical": [
            {"field": "revenue", "label": "Revenue", "reason": "EV/Revenue multiple"},
            {"field": "ebitda", "label": "EBITDA", "reason": "EV/EBITDA multiple"},
            {"field": "net_income", "label": "Net Income", "reason": "P/E multiple"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share metrics"},
        ],
        "important": [
            {"field": "total_debt", "label": "Total Debt", "reason": "Enterprise value calculation"},
            {"field": "cash_and_equivalents", "label": "Cash", "reason": "Enterprise value calculation"},
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "P/FCF multiple"},
            {"field": "stockholders_equity", "label": "Equity", "reason": "P/B multiple"},
        ],
        "helpful": [
            {"field": "gross_profit", "label": "Gross Profit", "reason": "Quality assessment"},
            {"field": "operating_margin", "label": "Operating Margin", "reason": "Quality premium/discount"},
        ],
    },
    "revenue_based": {
        "critical": [
            {"field": "revenue", "label": "Revenue", "reason": "Core input — model is entirely revenue-driven"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share price calculation"},
        ],
        "important": [
            {"field": "operating_margin", "label": "Operating Margin", "reason": "Rule of 40 calculation"},
            {"field": "gross_profit", "label": "Gross Profit", "reason": "Margin profile for multiple selection"},
            {"field": "ebitda", "label": "EBITDA", "reason": "Margin component of Rule of 40"},
        ],
        "helpful": [
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "FCF margin for growth-quality assessment"},
            {"field": "net_income", "label": "Net Income", "reason": "Profitability cross-check"},
        ],
    },
}

# Known field derivations (computed from other fields)
KNOWN_DERIVATIONS: dict[str, str] = {
    "free_cash_flow": "operating_cash_flow + capital_expenditure",
    "net_debt": "total_debt - cash_and_equivalents",
    "working_capital": "current_assets - current_liabilities",
    "gross_margin": "gross_profit / revenue",
    "operating_margin": "ebit / revenue",
    "net_margin": "net_income / revenue",
    "fcf_margin": "free_cash_flow / revenue",
    "ebitda_margin": "ebitda / revenue",
    "roe": "net_income / stockholders_equity",
    "debt_to_equity": "total_debt / stockholders_equity",
    "payout_ratio": "dividends_paid / net_income",
    "ebitda": "ebit + depreciation_amortization",
}

# Financial columns (excluding metadata columns)
FINANCIAL_COLUMNS: list[str] = [
    "revenue", "cost_of_revenue", "gross_profit", "operating_expense",
    "rd_expense", "sga_expense", "ebit", "interest_expense", "tax_provision",
    "net_income", "ebitda", "depreciation_amortization", "eps_basic", "eps_diluted",
    "total_assets", "current_assets", "cash_and_equivalents", "total_liabilities",
    "current_liabilities", "long_term_debt", "short_term_debt", "total_debt",
    "stockholders_equity", "working_capital", "net_debt", "operating_cash_flow",
    "capital_expenditure", "free_cash_flow", "dividends_paid",
    "change_in_working_capital", "investing_cash_flow", "financing_cash_flow",
    "shares_outstanding", "market_cap_at_period", "beta_at_period",
    "dividend_per_share", "gross_margin", "operating_margin", "net_margin",
    "fcf_margin", "revenue_growth", "ebitda_margin", "roe", "debt_to_equity",
    "payout_ratio",
]
