# ============================================
# FILENAME: config.py
# PURPOSE: Configuration and named ranges for Excel integration
# VERSION: 2.6 - All-4-Models, Model Comparison, Price Grid
# ============================================

"""
Configuration file for Stock Valuation System.

Contains:
- Configuration constants for data extraction and calculations
- Named ranges mapping (Python keys -> Excel names)
- Model prefixes for routing
- Model sheet names and ALL_MODELS list
- Intrinsic value range maps (INTRINSIC_RANGE_MAP, HOME_SCENARIO_RANGES)
- Model Comparison named ranges (ModelComp_* prefix)
- Scenario configuration (SCENARIO_LABELS, NUM_SCENARIOS)
- Market-implied calculation defaults (CAPM, DDM, Comps)
- System defaults and version info
"""

# ============================================================================
# PATH CONFIGURATION (derived from this file's location)
# ============================================================================

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent  # StockValuation/
SCRIPTS_DIR = PROJECT_ROOT / 'python_scripts'
LOG_DIR = PROJECT_ROOT / 'logs'
DATA_DIR = PROJECT_ROOT / 'data'

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Historical data periods
HISTORICAL_YEARS = 5  # Number of years of historical data to extract
PROJECTION_YEARS = 10  # Number of years for forward projections

# Data extraction settings
DEFAULT_WACC = 0.085  # 8.5% default WACC
DEFAULT_TERMINAL_GROWTH = 0.025  # 2.5% default terminal growth
DEFAULT_FCF_MARGIN = 0.20  # 20% default FCF margin
DEFAULT_REQUIRED_RETURN = 0.10  # 10% default required return for DDM
DEFAULT_TAX_RATE = 0.21  # 21% default corporate tax rate

# Market-implied calculation settings
REVERSE_DCF_MAX_ITERATIONS = 100
REVERSE_DCF_TOLERANCE = 0.005  # 0.5% tolerance for convergence
REVERSE_DCF_MIN_GROWTH = -0.10  # Minimum growth rate to search (-10%)
REVERSE_DCF_MAX_GROWTH = 0.60   # Maximum growth rate to search (60%)

# DDM CAPM defaults (used by market_implied_calculator.py)
DDM_RISK_FREE_RATE = 0.04   # 4% risk-free rate assumption
DDM_MARKET_RETURN = 0.10    # 10% expected market return
DDM_MAX_GROWTH_RATIO = 0.8  # Cap implied growth at 80% of required return
DDM_MIN_IMPLIED_GROWTH = -0.20  # Floor implied growth at -20%

# Comps defaults
DEFAULT_INDUSTRY_PE = 20.0  # Cross-sector average P/E; override per sector if needed

# Auto-detect model thresholds
ALTERNATIVE_MODEL_MIN_SCORE = 40  # Minimum score for alternative model suggestion
COMPS_MINIMUM_SCORE = 25  # Floor score for Comps model

# API Configuration
YAHOO_FINANCE_API_DELAY = 0.5  # Seconds between API calls to avoid rate limiting

# Cache Configuration
CACHE_ENABLED = True           # Set False to always fetch fresh data from Yahoo
CACHE_PRICE_TTL = 300          # 5 minutes for price/info data
CACHE_FINANCIAL_TTL = 86400    # 24 hours for financial statements and dividends

# Data Validation thresholds
MIN_REVENUE_THRESHOLD = 1_000_000  # $1M minimum revenue
MIN_MARKET_CAP_THRESHOLD = 10_000_000  # $10M minimum market cap

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FILE = 'stock_valuation.log'


# ============================================================================
# NAMED RANGES - Excel Integration (CORRECTED TO MATCH ACTUAL EXCEL FILE)
# ============================================================================

NAMED_RANGES = {
    # ========================================================================
    # HOME SHEET - Input
    # ========================================================================
    'ticker': 'TickerInput',  # CORRECTED from 'Ticker'
    
    # ========================================================================
    # HOME SHEET - Company Info & Key Metrics
    # ========================================================================
    'company_name': 'CompanyName',
    'sector': 'Sector',  # If exists in Excel, otherwise will be skipped
    'industry': 'Industry',  # If exists in Excel, otherwise will be skipped
    'market_cap': 'MarketCap',  # If exists in Excel, otherwise will be skipped
    'beta': 'Beta',  # If exists in Excel, otherwise will be skipped
    'shares_outstanding': 'SharesOutstanding',  # If exists in Excel, otherwise will be skipped
    'current_price': 'Current_Price',  # CONFIRMED
    'market_price': 'MarketPrice',  # If exists in Excel, otherwise will be skipped
    
    # ========================================================================
    # HOME SHEET - Model Selection & Detection
    # ========================================================================
    'selected_model': 'SelectedModel',  # CONFIRMED
    'recommended_model': 'AutoDetectedModel',  # CONFIRMED - Auto-detected model
    'confidence_level': 'DetectionConfidence',  # CONFIRMED
    'detection_reasoning': 'DetectionReasoning',  # CONFIRMED
    'alternative_suggestion': 'AlternativeModelSuggestion',  # CONFIRMED
    'data_completeness': 'DataCompleteness',  # If exists in Excel, otherwise will be skipped
    'sotp_flag': 'SOTPFlag',  # If exists in Excel, otherwise will be skipped
    
    # ========================================================================
    # HOME SHEET - Status & Timestamps
    # ========================================================================
    'connection_status': 'ConnectionStatus',  # CONFIRMED
    'last_updated': 'LastRefreshTime',  # CONFIRMED - maps to LastRefreshTime
    
    # ========================================================================
    # HOME SHEET - Data Availability Flags (optional)
    # ========================================================================
    'status_revenue': 'Status_Revenue',  # If exists in Excel, otherwise will be skipped
    'status_fcf': 'Status_FCF',  # If exists in Excel, otherwise will be skipped
    'status_dividends': 'Status_Dividends',  # If exists in Excel, otherwise will be skipped
    'status_estimates': 'Status_Estimates',  # If exists in Excel, otherwise will be skipped
    'status_balance_sheet': 'Status_BalanceSheet',  # If exists in Excel, otherwise will be skipped
    
    # ========================================================================
    # HOME SHEET - Valuation Results (8 Scenarios)
    # ========================================================================
    'intrinsic_value_cons': 'IntrinsicValue_Cons',  # CONFIRMED - Scenario 1
    'intrinsic_value_base': 'IntrinsicValue_Base',  # CONFIRMED - Scenario 2
    'intrinsic_value_opt': 'IntrinsicValue_Opt',  # CONFIRMED - Scenario 3
    'intrinsic_value_ai_cons': 'IntrinsicValue_AI_Cons',  # CONFIRMED - Scenario 4
    'intrinsic_value_ai_base': 'IntrinsicValue_AI_Base',  # CONFIRMED - Scenario 5
    'intrinsic_value_ai_opt': 'IntrinsicValue_AI_Opt',  # CONFIRMED - Scenario 6
    'market_intrinsic_value': 'Market_IntrinsicValue',  # CONFIRMED - Scenario 7
    'market_ai_intrinsic_value': 'MarketAI_IntrinsicValue',  # CONFIRMED - Scenario 8
    
    # Summary Results
    'best_case': 'BestCase',  # CONFIRMED
    'upside_potential': 'UpsidePotential',  # CONFIRMED
    
    # ========================================================================
    # MARKET-IMPLIED SCENARIO INPUTS (Python writes, Excel formulas read)
    # ========================================================================
    'market_implied_growth': 'MarketImplied_Growth',  # CONFIRMED - DCF revenue growth
    'market_implied_divgrowth': 'MarketImplied_DivGrowth',  # CONFIRMED - DDM dividend growth
    'market_implied_multiple': 'MarketImplied_Multiple',  # CONFIRMED - Revenue-Based EV/Rev multiple
    'market_implied_premium': 'MarketImplied_Premium',  # CONFIRMED - Comps quality premium

    # Per-model market-implied values (written to each model's own sheet)
    'dcf_market_implied_growth': 'DCF_MarketImplied_Growth',
    'ddm_market_implied_divgrowth': 'DDM_MarketImplied_DivGrowth',
    'revbased_market_implied_multiple': 'RevBased_MarketImplied_Multiple',
    'comps_market_implied_premium': 'Comps_MarketImplied_Premium',
    
    # ========================================================================
    # DCF MODEL - Yahoo Data (5 years historical)
    # NOTE: These are examples - adjust to match your actual Excel named ranges
    # ========================================================================
    
    # Income Statement (5 years: yr0=TTM, yr1=Y-1, yr2=Y-2, yr3=Y-3, yr4=Y-4)
    'dcf_revenue_yr0': 'DCF_Revenue_Yr0',
    'dcf_revenue_yr1': 'DCF_Revenue_Yr1',
    'dcf_revenue_yr2': 'DCF_Revenue_Yr2',
    'dcf_revenue_yr3': 'DCF_Revenue_Yr3',
    'dcf_revenue_yr4': 'DCF_Revenue_Yr4',
    
    'dcf_cost_of_revenue_yr0': 'DCF_CostOfRevenue_Yr0',
    'dcf_cost_of_revenue_yr1': 'DCF_CostOfRevenue_Yr1',
    'dcf_cost_of_revenue_yr2': 'DCF_CostOfRevenue_Yr2',
    'dcf_cost_of_revenue_yr3': 'DCF_CostOfRevenue_Yr3',
    'dcf_cost_of_revenue_yr4': 'DCF_CostOfRevenue_Yr4',
    
    'dcf_gross_profit_yr0': 'DCF_GrossProfit_Yr0',
    'dcf_gross_profit_yr1': 'DCF_GrossProfit_Yr1',
    'dcf_gross_profit_yr2': 'DCF_GrossProfit_Yr2',
    'dcf_gross_profit_yr3': 'DCF_GrossProfit_Yr3',
    'dcf_gross_profit_yr4': 'DCF_GrossProfit_Yr4',
    
    'dcf_opex_yr0': 'DCF_OpEx_Yr0',
    'dcf_opex_yr1': 'DCF_OpEx_Yr1',
    'dcf_opex_yr2': 'DCF_OpEx_Yr2',
    'dcf_opex_yr3': 'DCF_OpEx_Yr3',
    'dcf_opex_yr4': 'DCF_OpEx_Yr4',
    
    'dcf_ebit_yr0': 'DCF_EBIT_Yr0',
    'dcf_ebit_yr1': 'DCF_EBIT_Yr1',
    'dcf_ebit_yr2': 'DCF_EBIT_Yr2',
    'dcf_ebit_yr3': 'DCF_EBIT_Yr3',
    'dcf_ebit_yr4': 'DCF_EBIT_Yr4',
    
    'dcf_interest_expense_yr0': 'DCF_InterestExpense_Yr0',
    'dcf_interest_expense_yr1': 'DCF_InterestExpense_Yr1',
    'dcf_interest_expense_yr2': 'DCF_InterestExpense_Yr2',
    'dcf_interest_expense_yr3': 'DCF_InterestExpense_Yr3',
    'dcf_interest_expense_yr4': 'DCF_InterestExpense_Yr4',
    
    'dcf_taxes_yr0': 'DCF_Taxes_Yr0',
    'dcf_taxes_yr1': 'DCF_Taxes_Yr1',
    'dcf_taxes_yr2': 'DCF_Taxes_Yr2',
    'dcf_taxes_yr3': 'DCF_Taxes_Yr3',
    'dcf_taxes_yr4': 'DCF_Taxes_Yr4',
    
    'dcf_net_income_yr0': 'DCF_NetIncome_Yr0',
    'dcf_net_income_yr1': 'DCF_NetIncome_Yr1',
    'dcf_net_income_yr2': 'DCF_NetIncome_Yr2',
    'dcf_net_income_yr3': 'DCF_NetIncome_Yr3',
    'dcf_net_income_yr4': 'DCF_NetIncome_Yr4',
    
    'dcf_ebitda_yr0': 'DCF_EBITDA_Yr0',
    'dcf_ebitda_yr1': 'DCF_EBITDA_Yr1',
    'dcf_ebitda_yr2': 'DCF_EBITDA_Yr2',
    'dcf_ebitda_yr3': 'DCF_EBITDA_Yr3',
    'dcf_ebitda_yr4': 'DCF_EBITDA_Yr4',
    
    'dcf_da_yr0': 'DCF_DA_Yr0',
    'dcf_da_yr1': 'DCF_DA_Yr1',
    'dcf_da_yr2': 'DCF_DA_Yr2',
    'dcf_da_yr3': 'DCF_DA_Yr3',
    'dcf_da_yr4': 'DCF_DA_Yr4',
    
    # Balance Sheet (5 years)
    'dcf_total_assets_yr0': 'DCF_TotalAssets_Yr0',
    'dcf_total_assets_yr1': 'DCF_TotalAssets_Yr1',
    'dcf_total_assets_yr2': 'DCF_TotalAssets_Yr2',
    'dcf_total_assets_yr3': 'DCF_TotalAssets_Yr3',
    'dcf_total_assets_yr4': 'DCF_TotalAssets_Yr4',
    
    'dcf_current_assets_yr0': 'DCF_CurrentAssets_Yr0',
    'dcf_current_assets_yr1': 'DCF_CurrentAssets_Yr1',
    'dcf_current_assets_yr2': 'DCF_CurrentAssets_Yr2',
    'dcf_current_assets_yr3': 'DCF_CurrentAssets_Yr3',
    'dcf_current_assets_yr4': 'DCF_CurrentAssets_Yr4',
    
    'dcf_cash_yr0': 'DCF_Cash_Yr0',
    'dcf_cash_yr1': 'DCF_Cash_Yr1',
    'dcf_cash_yr2': 'DCF_Cash_Yr2',
    'dcf_cash_yr3': 'DCF_Cash_Yr3',
    'dcf_cash_yr4': 'DCF_Cash_Yr4',
    
    'dcf_total_liabilities_yr0': 'DCF_TotalLiabilities_Yr0',
    'dcf_total_liabilities_yr1': 'DCF_TotalLiabilities_Yr1',
    'dcf_total_liabilities_yr2': 'DCF_TotalLiabilities_Yr2',
    'dcf_total_liabilities_yr3': 'DCF_TotalLiabilities_Yr3',
    'dcf_total_liabilities_yr4': 'DCF_TotalLiabilities_Yr4',
    
    'dcf_current_liabilities_yr0': 'DCF_CurrentLiabilities_Yr0',
    'dcf_current_liabilities_yr1': 'DCF_CurrentLiabilities_Yr1',
    'dcf_current_liabilities_yr2': 'DCF_CurrentLiabilities_Yr2',
    'dcf_current_liabilities_yr3': 'DCF_CurrentLiabilities_Yr3',
    'dcf_current_liabilities_yr4': 'DCF_CurrentLiabilities_Yr4',
    
    'dcf_long_term_debt_yr0': 'DCF_LongTermDebt_Yr0',
    'dcf_long_term_debt_yr1': 'DCF_LongTermDebt_Yr1',
    'dcf_long_term_debt_yr2': 'DCF_LongTermDebt_Yr2',
    'dcf_long_term_debt_yr3': 'DCF_LongTermDebt_Yr3',
    'dcf_long_term_debt_yr4': 'DCF_LongTermDebt_Yr4',
    
    'dcf_short_term_debt_yr0': 'DCF_ShortTermDebt_Yr0',
    'dcf_short_term_debt_yr1': 'DCF_ShortTermDebt_Yr1',
    'dcf_short_term_debt_yr2': 'DCF_ShortTermDebt_Yr2',
    'dcf_short_term_debt_yr3': 'DCF_ShortTermDebt_Yr3',
    'dcf_short_term_debt_yr4': 'DCF_ShortTermDebt_Yr4',
    
    'dcf_total_debt_yr0': 'DCF_TotalDebt_Yr0',
    'dcf_total_debt_yr1': 'DCF_TotalDebt_Yr1',
    'dcf_total_debt_yr2': 'DCF_TotalDebt_Yr2',
    'dcf_total_debt_yr3': 'DCF_TotalDebt_Yr3',
    'dcf_total_debt_yr4': 'DCF_TotalDebt_Yr4',
    
    'dcf_equity_yr0': 'DCF_Equity_Yr0',
    'dcf_equity_yr1': 'DCF_Equity_Yr1',
    'dcf_equity_yr2': 'DCF_Equity_Yr2',
    'dcf_equity_yr3': 'DCF_Equity_Yr3',
    'dcf_equity_yr4': 'DCF_Equity_Yr4',
    
    # Cash Flow (5 years)
    'dcf_ocf_yr0': 'DCF_OCF_Yr0',
    'dcf_ocf_yr1': 'DCF_OCF_Yr1',
    'dcf_ocf_yr2': 'DCF_OCF_Yr2',
    'dcf_ocf_yr3': 'DCF_OCF_Yr3',
    'dcf_ocf_yr4': 'DCF_OCF_Yr4',
    
    'dcf_investing_cf_yr0': 'DCF_InvestingCF_Yr0',
    'dcf_investing_cf_yr1': 'DCF_InvestingCF_Yr1',
    'dcf_investing_cf_yr2': 'DCF_InvestingCF_Yr2',
    'dcf_investing_cf_yr3': 'DCF_InvestingCF_Yr3',
    'dcf_investing_cf_yr4': 'DCF_InvestingCF_Yr4',
    
    'dcf_financing_cf_yr0': 'DCF_FinancingCF_Yr0',
    'dcf_financing_cf_yr1': 'DCF_FinancingCF_Yr1',
    'dcf_financing_cf_yr2': 'DCF_FinancingCF_Yr2',
    'dcf_financing_cf_yr3': 'DCF_FinancingCF_Yr3',
    'dcf_financing_cf_yr4': 'DCF_FinancingCF_Yr4',
    
    'dcf_capex_yr0': 'DCF_CapEx_Yr0',
    'dcf_capex_yr1': 'DCF_CapEx_Yr1',
    'dcf_capex_yr2': 'DCF_CapEx_Yr2',
    'dcf_capex_yr3': 'DCF_CapEx_Yr3',
    'dcf_capex_yr4': 'DCF_CapEx_Yr4',
    
    'dcf_fcf_yr0': 'DCF_FCF_Yr0',
    'dcf_fcf_yr1': 'DCF_FCF_Yr1',
    'dcf_fcf_yr2': 'DCF_FCF_Yr2',
    'dcf_fcf_yr3': 'DCF_FCF_Yr3',
    'dcf_fcf_yr4': 'DCF_FCF_Yr4',
    
    'dcf_change_nwc_yr0': 'DCF_ChangeNWC_Yr0',
    'dcf_change_nwc_yr1': 'DCF_ChangeNWC_Yr1',
    'dcf_change_nwc_yr2': 'DCF_ChangeNWC_Yr2',
    'dcf_change_nwc_yr3': 'DCF_ChangeNWC_Yr3',
    'dcf_change_nwc_yr4': 'DCF_ChangeNWC_Yr4',
    
    # Key Metrics
    'dcf_current_price': 'DCF_CurrentPrice',
    'dcf_shares_out': 'DCF_SharesOut',
    'dcf_market_cap': 'DCF_MarketCap',
    'dcf_enterprise_value': 'DCF_EnterpriseValue',
    'dcf_beta': 'DCF_Beta',
    
    # ========================================================================
    # DDM MODEL - Yahoo Data (5 years historical)
    # NOTE: Excel uses DDM_Data_* naming convention
    # ========================================================================

    # Earnings & Dividends (5 years)
    'ddm_net_income_yr0': 'DDM_Data_NetIncome_Yr0',
    'ddm_net_income_yr1': 'DDM_Data_NetIncome_Yr1',
    'ddm_net_income_yr2': 'DDM_Data_NetIncome_Yr2',
    'ddm_net_income_yr3': 'DDM_Data_NetIncome_Yr3',
    'ddm_net_income_yr4': 'DDM_Data_NetIncome_Yr4',

    'ddm_eps_yr0': 'DDM_Data_EPS_Yr0',
    'ddm_eps_yr1': 'DDM_Data_EPS_Yr1',
    'ddm_eps_yr2': 'DDM_Data_EPS_Yr2',
    'ddm_eps_yr3': 'DDM_Data_EPS_Yr3',
    'ddm_eps_yr4': 'DDM_Data_EPS_Yr4',

    'ddm_dps_yr0': 'DDM_Data_DPS_Yr0',
    'ddm_dps_yr1': 'DDM_Data_DPS_Yr1',
    'ddm_dps_yr2': 'DDM_Data_DPS_Yr2',
    'ddm_dps_yr3': 'DDM_Data_DPS_Yr3',
    'ddm_dps_yr4': 'DDM_Data_DPS_Yr4',

    'ddm_total_div_yr0': 'DDM_Data_TotalDiv_Yr0',
    'ddm_total_div_yr1': 'DDM_Data_TotalDiv_Yr1',
    'ddm_total_div_yr2': 'DDM_Data_TotalDiv_Yr2',
    'ddm_total_div_yr3': 'DDM_Data_TotalDiv_Yr3',
    'ddm_total_div_yr4': 'DDM_Data_TotalDiv_Yr4',

    # Key Metrics
    'ddm_current_price': 'DDM_Data_CurrentPrice',
    'ddm_shares_out': 'DDM_Data_SharesOut',
    'ddm_market_cap': 'DDM_Data_MarketCap',
    'ddm_beta': 'DDM_Data_Beta',

    # Computed Metrics (calculated by Python from raw data)
    'ddm_payout_ratio_yr0': 'DDM_Data_PayoutRatio_Yr0',
    'ddm_payout_ratio_yr1': 'DDM_Data_PayoutRatio_Yr1',
    'ddm_payout_ratio_yr2': 'DDM_Data_PayoutRatio_Yr2',
    'ddm_payout_ratio_yr3': 'DDM_Data_PayoutRatio_Yr3',
    'ddm_payout_ratio_yr4': 'DDM_Data_PayoutRatio_Yr4',

    'ddm_div_growth_yr0': 'DDM_Data_DivGrowth_Yr0',
    'ddm_div_growth_yr1': 'DDM_Data_DivGrowth_Yr1',
    'ddm_div_growth_yr2': 'DDM_Data_DivGrowth_Yr2',
    'ddm_div_growth_yr3': 'DDM_Data_DivGrowth_Yr3',

    'ddm_current_yield': 'DDM_Data_CurrentYield',
    'ddm_div_cagr': 'DDM_Data_DivCAGR',

    # ========================================================================
    # REVENUE-BASED MODEL - Yahoo Data (5 years historical)
    # NOTE: Excel uses RevBased_Data_* naming convention
    # ========================================================================

    # Income Statement (5 years)
    'revbased_revenue_yr0': 'RevBased_Data_Revenue_Yr0',
    'revbased_revenue_yr1': 'RevBased_Data_Revenue_Yr1',
    'revbased_revenue_yr2': 'RevBased_Data_Revenue_Yr2',
    'revbased_revenue_yr3': 'RevBased_Data_Revenue_Yr3',
    'revbased_revenue_yr4': 'RevBased_Data_Revenue_Yr4',

    'revbased_gross_profit_yr0': 'RevBased_Data_GrossProfit_Yr0',
    'revbased_gross_profit_yr1': 'RevBased_Data_GrossProfit_Yr1',
    'revbased_gross_profit_yr2': 'RevBased_Data_GrossProfit_Yr2',
    'revbased_gross_profit_yr3': 'RevBased_Data_GrossProfit_Yr3',
    'revbased_gross_profit_yr4': 'RevBased_Data_GrossProfit_Yr4',

    'revbased_ebit_yr0': 'RevBased_Data_EBIT_Yr0',
    'revbased_ebit_yr1': 'RevBased_Data_EBIT_Yr1',
    'revbased_ebit_yr2': 'RevBased_Data_EBIT_Yr2',
    'revbased_ebit_yr3': 'RevBased_Data_EBIT_Yr3',
    'revbased_ebit_yr4': 'RevBased_Data_EBIT_Yr4',

    'revbased_net_income_yr0': 'RevBased_Data_NetIncome_Yr0',
    'revbased_net_income_yr1': 'RevBased_Data_NetIncome_Yr1',
    'revbased_net_income_yr2': 'RevBased_Data_NetIncome_Yr2',
    'revbased_net_income_yr3': 'RevBased_Data_NetIncome_Yr3',
    'revbased_net_income_yr4': 'RevBased_Data_NetIncome_Yr4',

    # Balance Sheet (5 years)
    'revbased_cash_yr0': 'RevBased_Data_Cash_Yr0',
    'revbased_cash_yr1': 'RevBased_Data_Cash_Yr1',
    'revbased_cash_yr2': 'RevBased_Data_Cash_Yr2',
    'revbased_cash_yr3': 'RevBased_Data_Cash_Yr3',
    'revbased_cash_yr4': 'RevBased_Data_Cash_Yr4',

    'revbased_total_debt_yr0': 'RevBased_Data_TotalDebt_Yr0',
    'revbased_total_debt_yr1': 'RevBased_Data_TotalDebt_Yr1',
    'revbased_total_debt_yr2': 'RevBased_Data_TotalDebt_Yr2',
    'revbased_total_debt_yr3': 'RevBased_Data_TotalDebt_Yr3',
    'revbased_total_debt_yr4': 'RevBased_Data_TotalDebt_Yr4',

    # Key Metrics
    'revbased_current_price': 'RevBased_Data_CurrentPrice',
    'revbased_shares_out': 'RevBased_Data_SharesOut',
    'revbased_market_cap': 'RevBased_Data_MarketCap',
    'revbased_beta': 'RevBased_Data_Beta',

    # Computed Margins (calculated by Python from raw data)
    'revbased_gross_margin_yr0': 'RevBased_Data_GrossMargin_Yr0',
    'revbased_gross_margin_yr1': 'RevBased_Data_GrossMargin_Yr1',
    'revbased_gross_margin_yr2': 'RevBased_Data_GrossMargin_Yr2',
    'revbased_gross_margin_yr3': 'RevBased_Data_GrossMargin_Yr3',
    'revbased_gross_margin_yr4': 'RevBased_Data_GrossMargin_Yr4',

    'revbased_op_margin_yr0': 'RevBased_Data_OpMargin_Yr0',
    'revbased_op_margin_yr1': 'RevBased_Data_OpMargin_Yr1',
    'revbased_op_margin_yr2': 'RevBased_Data_OpMargin_Yr2',
    'revbased_op_margin_yr3': 'RevBased_Data_OpMargin_Yr3',
    'revbased_op_margin_yr4': 'RevBased_Data_OpMargin_Yr4',

    'revbased_net_margin_yr0': 'RevBased_Data_NetMargin_Yr0',
    'revbased_net_margin_yr1': 'RevBased_Data_NetMargin_Yr1',
    'revbased_net_margin_yr2': 'RevBased_Data_NetMargin_Yr2',
    'revbased_net_margin_yr3': 'RevBased_Data_NetMargin_Yr3',
    'revbased_net_margin_yr4': 'RevBased_Data_NetMargin_Yr4',

    # ========================================================================
    # COMPS MODEL - Yahoo Data (TTM only)
    # NOTE: Excel uses Comps_Data_* naming convention
    # ========================================================================

    # Company Info
    'comps_company_name': 'Comps_Data_CompanyName',
    'comps_ticker': 'Comps_Data_Ticker',
    'comps_sector': 'Comps_Data_Sector',
    'comps_industry': 'Comps_Data_Industry',

    # Financial Data (TTM)
    'comps_revenue': 'Comps_Data_Revenue',
    'comps_ebitda': 'Comps_Data_EBITDA',
    'comps_ebit': 'Comps_Data_EBIT',
    'comps_net_income': 'Comps_Data_NetIncome',
    'comps_eps': 'Comps_Data_EPS',
    'comps_book_value': 'Comps_Data_BookValue',

    # Calculated Metrics
    'comps_rev_growth': 'Comps_Data_RevGrowth',
    'comps_ebitda_margin': 'Comps_Data_EBITDAMargin',
    'comps_net_margin': 'Comps_Data_NetMargin',
    'comps_roe': 'Comps_Data_ROE',
    'comps_debt_equity': 'Comps_Data_DebtEquity',

    # Valuation Multiples (extracted from Yahoo but previously not mapped)
    'comps_pe': 'Comps_Data_PE',
    'comps_pb': 'Comps_Data_PB',
    'comps_ps': 'Comps_Data_PS',
    'comps_ev_revenue': 'Comps_Data_EVRevenue',
    'comps_ev_ebitda': 'Comps_Data_EVEBITDA',
    'comps_ev_ebit': 'Comps_Data_EVEBIT',
    'comps_forward_pe': 'Comps_Data_ForwardPE',
    'comps_enterprise_value': 'Comps_Data_EnterpriseValue',

    # Market Data
    'comps_current_price': 'Comps_Data_CurrentPrice',
    'comps_shares_out': 'Comps_Data_SharesOut',
    'comps_market_cap': 'Comps_Data_MarketCap',
    'comps_total_debt': 'Comps_Data_TotalDebt',
    'comps_cash': 'Comps_Data_Cash',
    'comps_beta': 'Comps_Data_Beta',

    # ========================================================================
    # MODEL COMPARISON SHEET (populated by refresh_all_models)
    # ========================================================================

    # Header info
    'modelcomp_ticker': 'ModelComp_Ticker',
    'modelcomp_company_name': 'ModelComp_CompanyName',
    'modelcomp_current_price': 'ModelComp_CurrentPrice',
    'modelcomp_primary_model': 'ModelComp_PrimaryModel',
    'modelcomp_confidence': 'ModelComp_Confidence',

    # DCF results
    'modelcomp_dcf_implied_growth': 'ModelComp_DCF_ImpliedGrowth',
    'modelcomp_dcf_interpretation': 'ModelComp_DCF_Interpretation',
    'modelcomp_dcf_data_available': 'ModelComp_DCF_DataAvailable',
    'modelcomp_dcf_score': 'ModelComp_DCF_Score',

    # DDM results
    'modelcomp_ddm_implied_growth': 'ModelComp_DDM_ImpliedGrowth',
    'modelcomp_ddm_interpretation': 'ModelComp_DDM_Interpretation',
    'modelcomp_ddm_data_available': 'ModelComp_DDM_DataAvailable',
    'modelcomp_ddm_score': 'ModelComp_DDM_Score',

    # Revenue-Based results
    'modelcomp_revbased_implied_multiple': 'ModelComp_RevBased_ImpliedMultiple',
    'modelcomp_revbased_interpretation': 'ModelComp_RevBased_Interpretation',
    'modelcomp_revbased_data_available': 'ModelComp_RevBased_DataAvailable',
    'modelcomp_revbased_score': 'ModelComp_RevBased_Score',

    # Comps results
    'modelcomp_comps_implied_premium': 'ModelComp_Comps_ImpliedPremium',
    'modelcomp_comps_interpretation': 'ModelComp_Comps_Interpretation',
    'modelcomp_comps_data_available': 'ModelComp_Comps_DataAvailable',
    'modelcomp_comps_score': 'ModelComp_Comps_Score',

    # ========================================================================
    # MODEL COMPARISON — Intrinsic Value Price Grid (32 ranges: 8 scenarios × 4 models)
    # ========================================================================

    # DCF intrinsic values (8 scenarios)
    'modelcomp_dcf_cons': 'ModelComp_DCF_Cons',
    'modelcomp_dcf_base': 'ModelComp_DCF_Base',
    'modelcomp_dcf_opt': 'ModelComp_DCF_Opt',
    'modelcomp_dcf_aicons': 'ModelComp_DCF_AICons',
    'modelcomp_dcf_aibase': 'ModelComp_DCF_AIBase',
    'modelcomp_dcf_aiopt': 'ModelComp_DCF_AIOpt',
    'modelcomp_dcf_market': 'ModelComp_DCF_Market',
    'modelcomp_dcf_marketai': 'ModelComp_DCF_MarketAI',

    # DDM intrinsic values (8 scenarios)
    'modelcomp_ddm_cons': 'ModelComp_DDM_Cons',
    'modelcomp_ddm_base': 'ModelComp_DDM_Base',
    'modelcomp_ddm_opt': 'ModelComp_DDM_Opt',
    'modelcomp_ddm_aicons': 'ModelComp_DDM_AICons',
    'modelcomp_ddm_aibase': 'ModelComp_DDM_AIBase',
    'modelcomp_ddm_aiopt': 'ModelComp_DDM_AIOpt',
    'modelcomp_ddm_market': 'ModelComp_DDM_Market',
    'modelcomp_ddm_marketai': 'ModelComp_DDM_MarketAI',

    # RevBased intrinsic values (8 scenarios)
    'modelcomp_revbased_cons': 'ModelComp_RevBased_Cons',
    'modelcomp_revbased_base': 'ModelComp_RevBased_Base',
    'modelcomp_revbased_opt': 'ModelComp_RevBased_Opt',
    'modelcomp_revbased_aicons': 'ModelComp_RevBased_AICons',
    'modelcomp_revbased_aibase': 'ModelComp_RevBased_AIBase',
    'modelcomp_revbased_aiopt': 'ModelComp_RevBased_AIOpt',
    'modelcomp_revbased_market': 'ModelComp_RevBased_Market',
    'modelcomp_revbased_marketai': 'ModelComp_RevBased_MarketAI',

    # Comps intrinsic values (8 scenarios)
    'modelcomp_comps_cons': 'ModelComp_Comps_Cons',
    'modelcomp_comps_base': 'ModelComp_Comps_Base',
    'modelcomp_comps_opt': 'ModelComp_Comps_Opt',
    'modelcomp_comps_aicons': 'ModelComp_Comps_AICons',
    'modelcomp_comps_aibase': 'ModelComp_Comps_AIBase',
    'modelcomp_comps_aiopt': 'ModelComp_Comps_AIOpt',
    'modelcomp_comps_market': 'ModelComp_Comps_Market',
    'modelcomp_comps_marketai': 'ModelComp_Comps_MarketAI',

    # ========================================================================
    # MODEL COMPARISON — Enhanced Market-Implied Detail
    # ========================================================================

    # DCF detail
    'modelcomp_dcf_wacc': 'ModelComp_DCF_WACC',
    'modelcomp_dcf_termgrowth': 'ModelComp_DCF_TermGrowth',
    'modelcomp_dcf_fcfmargin': 'ModelComp_DCF_FCFMargin',
    'modelcomp_dcf_converged': 'ModelComp_DCF_Converged',

    # DDM detail
    'modelcomp_ddm_dps': 'ModelComp_DDM_DPS',
    'modelcomp_ddm_reqreturn': 'ModelComp_DDM_ReqReturn',

    # RevBased detail
    'modelcomp_revbased_ev': 'ModelComp_RevBased_EV',
    'modelcomp_revbased_revenue': 'ModelComp_RevBased_Revenue',

    # Comps detail
    'modelcomp_comps_companype': 'ModelComp_Comps_CompanyPE',
    'modelcomp_comps_industrype': 'ModelComp_Comps_IndustryPE',

    # Summary stats
    'modelcomp_avg_base': 'ModelComp_Avg_Base',
    'modelcomp_range_low': 'ModelComp_Range_Low',
    'modelcomp_range_high': 'ModelComp_Range_High',

    # ========================================================================
    # ASSUMPTIONS SHEET RANGES (read-only by save_to_history)
    # These are user-maintained formula cells — Python reads but NEVER writes
    # ========================================================================
    'dcf_wacc_base': 'DCF_WACC_Base',
    'revbased_wacc_base': 'RevBased_Asmp_WACC_Base',
    'dcf_rev_growth_base': 'DCF_Asmp_RevGrowth15_Base',
    'ddm_div_growth_stage1_base': 'DDM_Asmp_DivGrowth_Stage1_Base',
    'revbased_near_term_growth_base': 'RevBased_Asmp_NearTermGrowth_Base',
    'dcf_term_growth_base': 'DCF_Asmp_TermGrowth_Base',
    'ddm_terminal_growth_base': 'DDM_Asmp_TerminalGrowth_Base',
}


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Model prefixes for programmatic access
MODEL_PREFIXES = {
    'Standard DCF': 'dcf',
    'DDM': 'ddm',
    'Revenue-Based': 'revbased',
    'Comps': 'comps'
}

# Model sheet names in Excel
MODEL_SHEETS = {
    'Standard DCF': 'DCF_Yahoo_Data',
    'DDM': 'DDM_Yahoo_Data',
    'Revenue-Based': 'RevBased_Yahoo_Data',
    'Comps': 'Comps_Yahoo_Data'
}


# ============================================================================
# PER-MODEL INTRINSIC VALUE NAMED RANGES
# These may or may not exist in the workbook. Used by read_all_intrinsic_values()
# to try the fast path (direct per-model read) before falling back to model-switch.
# Naming convention from fix_intrinsic_pending.py: {Model}_IntrinsicValue_{Scenario}
# ============================================================================

INTRINSIC_RANGE_MAP = {
    'Standard DCF': {
        'Conservative': 'DCF_IntrinsicValue_Cons',
        'Base': 'DCF_IntrinsicValue_Base',
        'Optimistic': 'DCF_IntrinsicValue_Opt',
        'AI-Cons': 'DCF_IntrinsicValue_AICons',
        'AI-Base': 'DCF_IntrinsicValue_AIBase',
        'AI-Opt': 'DCF_IntrinsicValue_AIOpt',
        'Market': 'DCF_IntrinsicValue_Market',
        'Market+AI': 'DCF_IntrinsicValue_MarketAI',
    },
    'DDM': {
        'Conservative': 'DDM_IntrinsicValue_Cons',
        'Base': 'DDM_IntrinsicValue_Base',
        'Optimistic': 'DDM_IntrinsicValue_Opt',
        'AI-Cons': 'DDM_IntrinsicValue_AICons',
        'AI-Base': 'DDM_IntrinsicValue_AIBase',
        'AI-Opt': 'DDM_IntrinsicValue_AIOpt',
        'Market': 'DDM_IntrinsicValue_Market',
        'Market+AI': 'DDM_IntrinsicValue_MarketAI',
    },
    'Revenue-Based': {
        'Conservative': 'RevBased_IntrinsicValue_Cons',
        'Base': 'RevBased_IntrinsicValue_Base',
        'Optimistic': 'RevBased_IntrinsicValue_Opt',
        'AI-Cons': 'RevBased_IntrinsicValue_AICons',
        'AI-Base': 'RevBased_IntrinsicValue_AIBase',
        'AI-Opt': 'RevBased_IntrinsicValue_AIOpt',
        'Market': 'RevBased_IntrinsicValue_Market',
        'Market+AI': 'RevBased_IntrinsicValue_MarketAI',
    },
    'Comps': {
        'Conservative': 'Comps_IntrinsicValue_Cons',
        'Base': 'Comps_IntrinsicValue_Base',
        'Optimistic': 'Comps_IntrinsicValue_Opt',
        'AI-Cons': 'Comps_IntrinsicValue_AICons',
        'AI-Base': 'Comps_IntrinsicValue_AIBase',
        'AI-Opt': 'Comps_IntrinsicValue_AIOpt',
        'Market': 'Comps_IntrinsicValue_Market',
        'Market+AI': 'Comps_IntrinsicValue_MarketAI',
    },
}

# Home sheet intrinsic value named ranges (8 scenarios — these always exist)
HOME_SCENARIO_RANGES = [
    'IntrinsicValue_Cons',
    'IntrinsicValue_Base',
    'IntrinsicValue_Opt',
    'IntrinsicValue_AI_Cons',
    'IntrinsicValue_AI_Base',
    'IntrinsicValue_AI_Opt',
    'Market_IntrinsicValue',
    'MarketAI_IntrinsicValue',
]

# Scenario labels matching HOME_SCENARIO_RANGES order
SCENARIO_LABELS = [
    'Conservative', 'Base', 'Optimistic',
    'AI-Cons', 'AI-Base', 'AI-Opt',
    'Market', 'Market+AI',
]

ALL_MODELS = ['Standard DCF', 'DDM', 'Revenue-Based', 'Comps']


# ============================================================================
# SCENARIO CONFIGURATION
# ============================================================================

# Number of scenarios supported
NUM_SCENARIOS = 8

# Scenario names/descriptions
SCENARIO_NAMES = {
    1: 'Conservative',
    2: 'Base Case',
    3: 'Optimistic',
    4: 'AI-Capex Conservative',
    5: 'AI-Capex Base',
    6: 'AI-Capex Optimistic',
    7: 'Market Case',  # Uses market-implied assumptions
    8: 'Market+AI Case'  # Market case + AI benefits
}


# ============================================================================
# VERSION INFO
# ============================================================================

VERSION = '2.6'
VERSION_DATE = '2026-02-17'
DESCRIPTION = 'Stock Valuation System with All-4-Models Comparison, Price Grid, and Market-Implied Analysis'


# ============================================================================
# HOME SHEET NAME (used by fallback write paths)
# ============================================================================

HOME_SHEET_NAME = 'Home'
