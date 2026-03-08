"""
Excel Writer Module

Handles writing data from Python to Excel named ranges and sheets.
Provides write functions for all 4 valuation models:
- Standard DCF
- Dividend Discount Model (DDM)
- Revenue-Based Valuation
- Comparable Multiples (Comps)

Uses robust named range access with multiple fallback methods.
All functions include comprehensive logging for debugging.
"""

import xlwings as xw
import pandas as pd
from typing import Dict, Any, Optional, List
import logging

# Import utilities and configuration
import utils  # CRITICAL: Import utils module for timestamp, formatting, etc.
import config
from excel_helpers import (
    get_named_range_value,
    set_named_range_value as _set_named_range_value_immediate,
    cell_has_formula,
    get_df_value as _get_df_value,
)

# Import batch writing support (uses batching when active, falls back to immediate)
try:
    from excel_writer_batch import batch_set_named_range as _batch_write
    BATCH_SUPPORT = True
except ImportError:
    BATCH_SUPPORT = False
    _batch_write = None

logger = logging.getLogger('StockValuation')


# ============================================================================
# NAMED RANGE ACCESS (delegated to excel_helpers, with batch support wrapper)
# ============================================================================
# get_named_range_value is imported directly from excel_helpers


def set_named_range_value(wb: xw.Book, range_name: str, value: Any) -> bool:
    """
    Batch-aware wrapper around excel_helpers.set_named_range_value.

    When a batch session is active, delegates to the batch writer.
    Otherwise falls back to the immediate write path in excel_helpers
    (which includes formula protection).
    """
    # Formula protection: never overwrite a cell that contains a formula
    if cell_has_formula(wb, range_name):
        logger.warning(f"Skipping '{range_name}': cell contains a formula")
        return False

    # Use batch writing if available and active
    if BATCH_SUPPORT and _batch_write is not None:
        return _batch_write(wb, range_name, value)

    # Fallback to immediate write (formula check already done above)
    return _set_named_range_value_immediate(wb, range_name, value)


def write_to_named_range(range_name: str, value: Any, wb: Optional[xw.Book] = None) -> bool:
    """
    Write value to named range in active workbook.
    
    Convenience wrapper around set_named_range_value.
    
    Args:
        range_name: Name of the named range
        value: Value to write
        wb: Workbook (optional, will get active if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        return set_named_range_value(wb, range_name, value)
        
    except Exception as e:
        utils.log_error('EXCEL_WRITE', range_name, 'Failed to write to named range', str(e))
        return False


# ============================================================================
# HOME SHEET WRITING FUNCTIONS
# ============================================================================

def write_company_info(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """Write company information to Home Sheet."""
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        logger.info("Writing company info to Home Sheet...")

        company_info = data.get('company_info', {})
        key_metrics = data.get('key_metrics', {})

        # Company name
        company_name = company_info.get('longName') or company_info.get('shortName') or data.get('ticker', 'N/A')
        set_named_range_value(wb, 'CompanyName', company_name)
        logger.debug(f"Company: {company_name}")
        
        # Sector and Industry
        set_named_range_value(wb, 'Sector', company_info.get('sector', 'N/A'))
        set_named_range_value(wb, 'Industry', company_info.get('industry', 'N/A'))
        
        # Market metrics
        market_cap = company_info.get('market_cap') or key_metrics.get('marketCap')
        set_named_range_value(wb, 'MarketCap', market_cap)
        
        beta = company_info.get('beta') or key_metrics.get('beta')
        set_named_range_value(wb, 'Beta', beta)
        
        shares = company_info.get('shares_outstanding') or key_metrics.get('sharesOutstanding')
        set_named_range_value(wb, 'SharesOutstanding', shares)
        
        # Current Price
        current_price = key_metrics.get('currentPrice') or key_metrics.get('regularMarketPrice')
        set_named_range_value(wb, 'Current_Price', current_price)
        set_named_range_value(wb, 'MarketPrice', current_price)
        
        if current_price:
            logger.debug(f"Current Price: ${current_price:.2f}")
        
        utils.log_info(f"Company information written for {data.get('ticker')}")
        return True
        
    except Exception as e:
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write company info', str(e))
        return False


def write_detection_results(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """Write model detection results to Home Sheet."""
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        recommendation = data.get('model_recommendation', {})
        
        # Write detection results
        set_named_range_value(wb, 'AutoDetectedModel', recommendation.get('recommended_model', 'Unknown'))
        set_named_range_value(wb, 'SelectedModel', recommendation.get('recommended_model', 'Unknown'))
        set_named_range_value(wb, 'DetectionConfidence', recommendation.get('confidence', 'Low'))
        
        reasoning = recommendation.get('reasoning', 'No reasoning available')
        set_named_range_value(wb, 'DetectionReasoning', reasoning)
        
        # Alternative suggestion if confidence is low
        confidence_pct = recommendation.get('confidence_percentage', 100)
        alternative = recommendation.get('alternative', None)
        
        if confidence_pct < 80 and alternative:
            suggestion_text = f"⚠️ Low confidence ({confidence_pct}%). Consider also: {alternative}"
            set_named_range_value(wb, 'AlternativeModelSuggestion', suggestion_text)
            logger.info(f"[ALTERNATIVE SUGGESTION] {suggestion_text}")
        else:
            set_named_range_value(wb, 'AlternativeModelSuggestion', '')
        
        utils.log_info(f"Detection results written: {recommendation.get('recommended_model')}")
        return True
        
    except Exception as e:
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write detection results', str(e))
        return False


def write_data_availability(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """Write data availability flags to Home Sheet."""
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        availability = data.get('data_availability', {})
        
        set_named_range_value(wb, 'Status_Revenue', availability.get('revenue', False))
        set_named_range_value(wb, 'Status_FCF', availability.get('fcf', False))
        set_named_range_value(wb, 'Status_Dividends', availability.get('dividends', False))
        set_named_range_value(wb, 'Status_Estimates', availability.get('estimates', False))
        set_named_range_value(wb, 'Status_BalanceSheet', availability.get('balance_sheet', False))
        
        utils.log_info("Data availability flags written")
        return True
        
    except Exception as e:
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write data availability', str(e))
        return False


def write_placeholder_valuation(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """Write placeholder values to valuation results.

    NOTE: Previously this function wrote 'Pending' to IntrinsicValue_Base and
    IntrinsicValue_AI_Base named ranges. This was REMOVED because those cells
    (Home!B109 and Home!B113) contain Excel formulas that calculate intrinsic
    values from the model Dashboard sheets. Writing 'Pending' destroyed those
    formulas and broke the History sheet save functionality.

    The formulas in those cells are:
    - B109: =IFERROR(IF(C4="Standard DCF",DCF_IntrinsicValue_Base,...),0)
    - B113: =IFERROR(IF(C4="Standard DCF",DCF_IntrinsicValue_AIBase,...),0)

    DO NOT add writes to these named ranges without understanding the impact.
    """
    try:
        if wb is None:
            wb = utils.get_workbook()

        # REMOVED: These lines destroyed Excel formulas in Home!B109 and B113
        # set_named_range_value(wb, 'IntrinsicValue_Base', 'Pending')
        # set_named_range_value(wb, 'IntrinsicValue_AI_Base', 'Pending')

        # This function now does nothing but exists for backward compatibility
        # with any code that calls it. The intrinsic values are calculated
        # by Excel formulas on the Dashboard sheets.

        return True

    except Exception as e:
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write placeholder valuation', str(e))
        return False


# ============================================================================
# DCF MODEL - WRITE FUNCTIONS
# ============================================================================

def write_dcf_yahoo_data(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """
    Write 5 years of historical financial data to DCF_Yahoo_Data sheet.
    
    Writes:
    - Income statement (revenue, costs, margins, etc.)
    - Balance sheet (assets, liabilities, equity, debt)
    - Cash flow (OCF, CapEx, FCF)
    - Key metrics (price, shares, market cap, beta)
    
    Args:
        data: Extracted data from YahooFinanceExtractor
        wb: Workbook (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        logger.info("=" * 70)
        logger.info("WRITING DCF YAHOO DATA")
        logger.info("=" * 70)

        # Get timestamp
        timestamp = utils.get_timestamp()
        logger.debug(f"Timestamp: {timestamp}")
        
        # Get data sections
        income_stmt = data.get('income_statement', pd.DataFrame())
        balance_sheet = data.get('balance_sheet', pd.DataFrame())
        cash_flow = data.get('cash_flow', pd.DataFrame())
        company_info = data.get('company_info', {})
        key_metrics = data.get('key_metrics', {})
        
        logger.debug(f"Data sections available: Income={not income_stmt.empty}, "
                     f"Balance={not balance_sheet.empty}, CashFlow={not cash_flow.empty}")
        
        get_df_value = _get_df_value
        
        # Write Income Statement (5 years: yr0=TTM, yr1-4=historical)
        logger.debug("Writing income statement data (5 years)...")
        for year in range(5):
            # Revenue
            revenue = get_df_value(income_stmt, "Total Revenue", year) or \
                     get_df_value(income_stmt, "Operating Revenue", year)
            set_named_range_value(wb, f'DCF_Revenue_Yr{year}', revenue)
            
            if year == 0 and revenue:
                logger.debug(f"Year 0 Revenue: {utils.format_currency(revenue, 0)}")
            
            # Cost of Revenue
            cost = get_df_value(income_stmt, "Cost Of Revenue", year)
            set_named_range_value(wb, f'DCF_CostOfRevenue_Yr{year}', cost)
            
            # Gross Profit
            gross_profit = get_df_value(income_stmt, "Gross Profit", year)
            set_named_range_value(wb, f'DCF_GrossProfit_Yr{year}', gross_profit)
            
            # Operating Expense
            opex = get_df_value(income_stmt, "Operating Expense", year)
            set_named_range_value(wb, f'DCF_OpEx_Yr{year}', opex)
            
            # EBIT
            ebit = get_df_value(income_stmt, "Operating Income", year) or \
                  get_df_value(income_stmt, "EBIT", year)
            set_named_range_value(wb, f'DCF_EBIT_Yr{year}', ebit)
            
            # Interest Expense
            interest = get_df_value(income_stmt, "Interest Expense", year)
            set_named_range_value(wb, f'DCF_InterestExpense_Yr{year}', interest)
            
            # Taxes
            taxes = get_df_value(income_stmt, "Tax Provision", year)
            set_named_range_value(wb, f'DCF_Taxes_Yr{year}', taxes)
            
            # Net Income
            net_income = get_df_value(income_stmt, "Net Income", year)
            set_named_range_value(wb, f'DCF_NetIncome_Yr{year}', net_income)
            
            # EBITDA
            ebitda = get_df_value(income_stmt, "EBITDA", year) or \
                    get_df_value(income_stmt, "Normalized EBITDA", year)
            set_named_range_value(wb, f'DCF_EBITDA_Yr{year}', ebitda)
            
            # Depreciation & Amortization
            da = get_df_value(income_stmt, "Reconciled Depreciation", year) or \
                get_df_value(income_stmt, "Depreciation And Amortization", year)
            # Calculate D&A from EBITDA - EBIT if not available (only accept non-negative)
            if da == 0 and ebitda != 0 and ebit != 0:
                calculated_da = ebitda - ebit
                if calculated_da >= 0:
                    da = calculated_da
                else:
                    logger.debug(f"Skipping D&A fallback: EBITDA-EBIT is negative ({calculated_da})")
            set_named_range_value(wb, f'DCF_DA_Yr{year}', da)
        
        logger.debug("Income statement data written (5 years)")

        # Write Balance Sheet (5 years)
        logger.debug("Writing balance sheet data (5 years)...")
        for year in range(5):
            # Total Assets
            total_assets = get_df_value(balance_sheet, "Total Assets", year)
            set_named_range_value(wb, f'DCF_TotalAssets_Yr{year}', total_assets)
            
            # Current Assets
            current_assets = get_df_value(balance_sheet, "Current Assets", year)
            set_named_range_value(wb, f'DCF_CurrentAssets_Yr{year}', current_assets)
            
            # Cash
            cash = get_df_value(balance_sheet, "Cash And Cash Equivalents", year) or \
                  get_df_value(balance_sheet, "Cash", year)
            set_named_range_value(wb, f'DCF_Cash_Yr{year}', cash)
            
            # Total Liabilities
            total_liabilities = get_df_value(balance_sheet, "Total Liabilities Net Minority Interest", year) or \
                              get_df_value(balance_sheet, "Total Liabilities", year)
            set_named_range_value(wb, f'DCF_TotalLiabilities_Yr{year}', total_liabilities)
            
            # Current Liabilities
            current_liabilities = get_df_value(balance_sheet, "Current Liabilities", year)
            set_named_range_value(wb, f'DCF_CurrentLiabilities_Yr{year}', current_liabilities)
            
            # Long-term Debt
            ltd = get_df_value(balance_sheet, "Long Term Debt", year) or \
                 get_df_value(balance_sheet, "Long Term Debt And Capital Lease Obligation", year)
            set_named_range_value(wb, f'DCF_LongTermDebt_Yr{year}', ltd)
            
            # Short-term Debt
            std = get_df_value(balance_sheet, "Current Debt", year) or \
                 get_df_value(balance_sheet, "Short Term Debt", year)
            set_named_range_value(wb, f'DCF_ShortTermDebt_Yr{year}', std)
            
            # Total Debt
            total_debt = (ltd or 0) + (std or 0)
            set_named_range_value(wb, f'DCF_TotalDebt_Yr{year}', total_debt)
            
            # Equity
            equity = get_df_value(balance_sheet, "Stockholders Equity", year) or \
                    get_df_value(balance_sheet, "Total Equity Gross Minority Interest", year)
            set_named_range_value(wb, f'DCF_Equity_Yr{year}', equity)
        
        logger.debug("Balance sheet data written (5 years)")

        # Write Cash Flow (5 years)
        logger.debug("Writing cash flow data (5 years)...")
        for year in range(5):
            # Operating Cash Flow
            ocf = get_df_value(cash_flow, "Operating Cash Flow", year) or \
                 get_df_value(cash_flow, "Total Cash From Operating Activities", year)
            set_named_range_value(wb, f'DCF_OCF_Yr{year}', ocf)
            
            # Investing Cash Flow
            investing_cf = get_df_value(cash_flow, "Investing Cash Flow", year)
            set_named_range_value(wb, f'DCF_InvestingCF_Yr{year}', investing_cf)
            
            # Financing Cash Flow
            financing_cf = get_df_value(cash_flow, "Financing Cash Flow", year)
            set_named_range_value(wb, f'DCF_FinancingCF_Yr{year}', financing_cf)
            
            # CapEx (make positive)
            capex = get_df_value(cash_flow, "Capital Expenditure", year)
            capex = abs(capex) if capex else 0
            set_named_range_value(wb, f'DCF_CapEx_Yr{year}', capex)
            
            # Free Cash Flow
            fcf = get_df_value(cash_flow, "Free Cash Flow", year)
            # Calculate if not available: FCF = OCF - CapEx
            if fcf == 0 and ocf != 0:
                fcf = ocf - capex
            set_named_range_value(wb, f'DCF_FCF_Yr{year}', fcf)
            
            # Change in NWC
            nwc_change = get_df_value(cash_flow, "Change In Working Capital", year)
            set_named_range_value(wb, f'DCF_ChangeNWC_Yr{year}', nwc_change)
        
        logger.debug("Cash flow data written (5 years)")

        # Write Key Metrics
        logger.debug("Writing key metrics...")
        
        current_price = key_metrics.get('currentPrice') or key_metrics.get('regularMarketPrice')
        set_named_range_value(wb, 'DCF_CurrentPrice', current_price)
        
        shares_out = company_info.get('shares_outstanding') or key_metrics.get('sharesOutstanding')
        set_named_range_value(wb, 'DCF_SharesOut', shares_out)
        
        market_cap = company_info.get('market_cap') or key_metrics.get('marketCap')
        set_named_range_value(wb, 'DCF_MarketCap', market_cap)
        
        ev = key_metrics.get('enterpriseValue')
        set_named_range_value(wb, 'DCF_EnterpriseValue', ev)
        
        beta = company_info.get('beta') or key_metrics.get('beta')
        set_named_range_value(wb, 'DCF_Beta', beta)
        
        logger.debug("Key metrics written")

        logger.info("=" * 70)
        logger.info("DCF YAHOO DATA WRITE COMPLETE")
        logger.info("=" * 70)
        
        utils.log_info(f"DCF data written for {data.get('ticker')}")
        return True
        
    except Exception as e:
        logger.error(f"ERROR WRITING DCF YAHOO DATA: {e}", exc_info=True)
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write DCF data', str(e))
        return False


# ============================================================================
# DDM MODEL - WRITE FUNCTIONS
# ============================================================================

def write_ddm_yahoo_data(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """Write dividend and earnings data to DDM_Yahoo_Data sheet."""
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        logger.info("=" * 70)
        logger.info("WRITING DDM YAHOO DATA")
        logger.info("=" * 70)

        timestamp = utils.get_timestamp()
        logger.debug(f"Timestamp: {timestamp}")
        
        dividends = data.get('dividends', {})
        income_stmt = data.get('income_statement', pd.DataFrame())
        company_info = data.get('company_info', {})
        key_metrics = data.get('key_metrics', {})
        
        get_df_value = _get_df_value
        
        shares_out = company_info.get('shares_outstanding') or key_metrics.get('sharesOutstanding') or 0
        if not shares_out:
            logger.warning("shares_outstanding unavailable — EPS and payout ratios will be zero")

        # Write 5 years of earnings and dividend data
        # NOTE: Named ranges use DDM_Data_* prefix (e.g., DDM_Data_DPS_Yr0)
        logger.debug("Writing earnings data (5 years)...")
        annual_divs = dividends.get('annual', {})

        for year in range(5):
            # Net Income
            net_income = get_df_value(income_stmt, "Net Income", year)
            set_named_range_value(wb, f'DDM_Data_NetIncome_Yr{year}', net_income)

            # EPS
            eps = utils.safe_divide(net_income, shares_out, default=0)
            set_named_range_value(wb, f'DDM_Data_EPS_Yr{year}', eps)

            # Get actual dividend data from extracted annual dividends
            dps = annual_divs.get(f'year_{year}', 0)
            # Convert numpy types to Python native
            if hasattr(dps, 'item'):
                dps = dps.item()
            dps = float(dps) if dps else 0

            # Calculate total dividends paid
            total_div = dps * shares_out if shares_out and dps else 0

            set_named_range_value(wb, f'DDM_Data_DPS_Yr{year}', dps)
            set_named_range_value(wb, f'DDM_Data_TotalDiv_Yr{year}', total_div)

            # Payout ratio for each year (DPS / EPS)
            payout = utils.safe_divide(dps, eps, default=0) if eps else 0
            set_named_range_value(wb, f'DDM_Data_PayoutRatio_Yr{year}', payout)

            # Dividend growth for each year (calculated vs prior year)
            if year < 4:
                prior_dps = annual_divs.get(f'year_{year+1}', 0)
                if hasattr(prior_dps, 'item'):
                    prior_dps = prior_dps.item()
                prior_dps = float(prior_dps) if prior_dps else 0
                if prior_dps > 0:
                    div_growth_yr = (dps - prior_dps) / prior_dps
                else:
                    div_growth_yr = 0
                set_named_range_value(wb, f'DDM_Data_DivGrowth_Yr{year}', div_growth_yr)

        logger.debug("Earnings and dividend data written (5 years)")

        # Write key metrics (using DDM_Data_* prefix)
        logger.debug("Writing key metrics...")

        current_price = key_metrics.get('currentPrice') or key_metrics.get('regularMarketPrice')
        set_named_range_value(wb, 'DDM_Data_CurrentPrice', current_price)

        set_named_range_value(wb, 'DDM_Data_SharesOut', shares_out)

        market_cap = company_info.get('market_cap') or key_metrics.get('marketCap')
        set_named_range_value(wb, 'DDM_Data_MarketCap', market_cap)

        beta = company_info.get('beta') or key_metrics.get('beta')
        set_named_range_value(wb, 'DDM_Data_Beta', beta)

        # Dividend yield (convert from percentage to decimal if > 1)
        div_yield = key_metrics.get('dividendYield', 0) or 0
        if div_yield > 1:  # yfinance returns 2.17 meaning 2.17%
            div_yield = div_yield / 100
        set_named_range_value(wb, 'DDM_Data_CurrentYield', div_yield)

        # Calculate dividend growth rate (CAGR over available years)
        y0 = float(annual_divs.get('year_0', 0) or 0)
        y4 = float(annual_divs.get('year_4', 0) or 0)
        if y4 > 0 and y0 > 0:
            div_growth = (y0 / y4) ** (1/4) - 1  # 4-year CAGR
        else:
            div_growth = 0
        set_named_range_value(wb, 'DDM_Data_DivCAGR', div_growth)

        logger.debug("Key metrics written (incl. yield, beta, growth)")

        logger.info("=" * 70)
        logger.info("DDM YAHOO DATA WRITE COMPLETE")
        logger.info("=" * 70)
        
        utils.log_info(f"DDM data written for {data.get('ticker')}")
        return True
        
    except Exception as e:
        logger.error(f"ERROR WRITING DDM YAHOO DATA: {e}", exc_info=True)
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write DDM data', str(e))
        return False


# ============================================================================
# REVENUE-BASED MODEL - WRITE FUNCTIONS
# ============================================================================

def write_revbased_yahoo_data(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """Write revenue and margin data to RevBased_Yahoo_Data sheet."""
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        logger.info("=" * 70)
        logger.info("WRITING REVENUE-BASED YAHOO DATA")
        logger.info("=" * 70)

        timestamp = utils.get_timestamp()
        logger.debug(f"Timestamp: {timestamp}")
        
        income_stmt = data.get('income_statement', pd.DataFrame())
        balance_sheet = data.get('balance_sheet', pd.DataFrame())
        company_info = data.get('company_info', {})
        key_metrics = data.get('key_metrics', {})
        
        get_df_value = _get_df_value

        # Write 5 years of income statement data
        # NOTE: Named ranges use RevBased_Data_* prefix
        logger.debug("Writing income statement data (5 years)...")
        for year in range(5):
            # Revenue
            revenue = get_df_value(income_stmt, "Total Revenue", year) or \
                     get_df_value(income_stmt, "Operating Revenue", year)
            set_named_range_value(wb, f'RevBased_Data_Revenue_Yr{year}', revenue)

            # Gross Profit
            gross_profit = get_df_value(income_stmt, "Gross Profit", year)
            set_named_range_value(wb, f'RevBased_Data_GrossProfit_Yr{year}', gross_profit)

            # EBIT (Operating Income)
            ebit = get_df_value(income_stmt, "Operating Income", year) or \
                  get_df_value(income_stmt, "EBIT", year)
            set_named_range_value(wb, f'RevBased_Data_EBIT_Yr{year}', ebit)

            # Net Income
            net_income = get_df_value(income_stmt, "Net Income", year)
            set_named_range_value(wb, f'RevBased_Data_NetIncome_Yr{year}', net_income)

            # Calculate margins
            if revenue and revenue > 0:
                gross_margin = gross_profit / revenue if gross_profit else 0
                op_margin = ebit / revenue if ebit else 0
                net_margin = net_income / revenue if net_income else 0
            else:
                gross_margin = op_margin = net_margin = 0
            set_named_range_value(wb, f'RevBased_Data_GrossMargin_Yr{year}', gross_margin)
            set_named_range_value(wb, f'RevBased_Data_OpMargin_Yr{year}', op_margin)
            set_named_range_value(wb, f'RevBased_Data_NetMargin_Yr{year}', net_margin)

        logger.debug("Income statement data written")

        # Write 5 years of balance sheet data
        logger.debug("Writing balance sheet data (5 years)...")
        for year in range(5):
            # Cash
            cash = get_df_value(balance_sheet, "Cash And Cash Equivalents", year) or \
                  get_df_value(balance_sheet, "Cash", year)
            set_named_range_value(wb, f'RevBased_Data_Cash_Yr{year}', cash)

            # Total Debt
            ltd = get_df_value(balance_sheet, "Long Term Debt", year)
            std = get_df_value(balance_sheet, "Current Debt", year) or \
                 get_df_value(balance_sheet, "Short Term Debt", year)
            total_debt = (ltd or 0) + (std or 0)
            set_named_range_value(wb, f'RevBased_Data_TotalDebt_Yr{year}', total_debt)

        logger.debug("Balance sheet data written")

        # Write key metrics (using RevBased_Data_* prefix)
        logger.debug("Writing key metrics...")

        current_price = key_metrics.get('currentPrice') or key_metrics.get('regularMarketPrice')
        set_named_range_value(wb, 'RevBased_Data_CurrentPrice', current_price)

        shares_out = company_info.get('shares_outstanding') or key_metrics.get('sharesOutstanding')
        set_named_range_value(wb, 'RevBased_Data_SharesOut', shares_out)

        market_cap = company_info.get('market_cap') or key_metrics.get('marketCap')
        set_named_range_value(wb, 'RevBased_Data_MarketCap', market_cap)

        beta = company_info.get('beta') or key_metrics.get('beta')
        set_named_range_value(wb, 'RevBased_Data_Beta', beta)

        logger.debug("Key metrics written")

        logger.info("=" * 70)
        logger.info("REVENUE-BASED YAHOO DATA WRITE COMPLETE")
        logger.info("=" * 70)
        
        utils.log_info(f"Revenue-Based data written for {data.get('ticker')}")
        return True
        
    except Exception as e:
        logger.error(f"ERROR WRITING REVENUE-BASED YAHOO DATA: {e}", exc_info=True)
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write Revenue-Based data', str(e))
        return False


# ============================================================================
# COMPS MODEL - WRITE FUNCTIONS
# ============================================================================

def write_comps_yahoo_data(data: Dict[str, Any], wb: Optional[xw.Book] = None) -> bool:
    """Write company financials and metrics to Comps_Yahoo_Data sheet."""
    try:
        if wb is None:
            wb = utils.get_workbook()
        
        logger.info("=" * 70)
        logger.info("WRITING COMPS YAHOO DATA")
        logger.info("=" * 70)

        timestamp = utils.get_timestamp()
        logger.debug(f"Timestamp: {timestamp}")
        
        company_info = data.get('company_info', {})
        income_stmt = data.get('income_statement', pd.DataFrame())
        balance_sheet = data.get('balance_sheet', pd.DataFrame())
        key_metrics = data.get('key_metrics', {})
        
        get_df_value = _get_df_value

        # Write company info (using Comps_Data_* prefix)
        logger.debug("Writing company info...")

        company_name = company_info.get('longName') or company_info.get('shortName') or data.get('ticker', 'N/A')
        set_named_range_value(wb, 'Comps_Data_CompanyName', company_name)
        set_named_range_value(wb, 'Comps_Data_Ticker', data.get('ticker', 'N/A'))
        set_named_range_value(wb, 'Comps_Data_Sector', company_info.get('sector', 'N/A'))
        set_named_range_value(wb, 'Comps_Data_Industry', company_info.get('industry', 'N/A'))

        logger.debug("Company info written")

        # Write financial data (TTM)
        logger.debug("Writing financial data (TTM)...")

        revenue = get_df_value(income_stmt, "Total Revenue", 0) or \
                 get_df_value(income_stmt, "Operating Revenue", 0)
        set_named_range_value(wb, 'Comps_Data_Revenue', revenue)

        ebitda = get_df_value(income_stmt, "EBITDA", 0) or \
                get_df_value(income_stmt, "Normalized EBITDA", 0)
        set_named_range_value(wb, 'Comps_Data_EBITDA', ebitda)

        ebit = get_df_value(income_stmt, "Operating Income", 0) or \
              get_df_value(income_stmt, "EBIT", 0)
        set_named_range_value(wb, 'Comps_Data_EBIT', ebit)

        net_income = get_df_value(income_stmt, "Net Income", 0)
        set_named_range_value(wb, 'Comps_Data_NetIncome', net_income)

        shares_out = company_info.get('shares_outstanding') or key_metrics.get('sharesOutstanding') or 0
        if not shares_out:
            logger.warning("shares_outstanding unavailable — EPS and payout ratios will be zero")
        eps = utils.safe_divide(net_income, shares_out, default=0)
        set_named_range_value(wb, 'Comps_Data_EPS', eps)

        equity = get_df_value(balance_sheet, "Stockholders Equity", 0)
        book_value = utils.safe_divide(equity, shares_out, default=0)
        set_named_range_value(wb, 'Comps_Data_BookValue', book_value)

        logger.debug("Financial data written")

        # Calculate and write metrics
        logger.debug("Calculating metrics...")

        # Revenue growth
        rev_y0 = revenue
        rev_y1 = get_df_value(income_stmt, "Total Revenue", 1) or \
                get_df_value(income_stmt, "Operating Revenue", 1)
        rev_growth = utils.calculate_growth_rate(rev_y0, rev_y1)
        set_named_range_value(wb, 'Comps_Data_RevGrowth', rev_growth)

        # Margins
        ebitda_margin = utils.safe_divide(ebitda, revenue, default=0)
        set_named_range_value(wb, 'Comps_Data_EBITDAMargin', ebitda_margin)

        net_margin = utils.safe_divide(net_income, revenue, default=0)
        set_named_range_value(wb, 'Comps_Data_NetMargin', net_margin)

        # ROE
        roe = utils.safe_divide(net_income, equity, default=0)
        set_named_range_value(wb, 'Comps_Data_ROE', roe)

        logger.debug("Metrics calculated and written")

        # Write market data
        logger.debug("Writing market data...")

        current_price = key_metrics.get('currentPrice') or key_metrics.get('regularMarketPrice')
        set_named_range_value(wb, 'Comps_Data_CurrentPrice', current_price)

        set_named_range_value(wb, 'Comps_Data_SharesOut', shares_out)

        market_cap = company_info.get('market_cap') or key_metrics.get('marketCap')
        set_named_range_value(wb, 'Comps_Data_MarketCap', market_cap)

        ltd = get_df_value(balance_sheet, "Long Term Debt", 0)
        std = get_df_value(balance_sheet, "Current Debt", 0) or \
             get_df_value(balance_sheet, "Short Term Debt", 0)
        total_debt = (ltd or 0) + (std or 0)
        set_named_range_value(wb, 'Comps_Data_TotalDebt', total_debt)

        cash = get_df_value(balance_sheet, "Cash And Cash Equivalents", 0) or \
              get_df_value(balance_sheet, "Cash", 0)
        set_named_range_value(wb, 'Comps_Data_Cash', cash)

        beta = company_info.get('beta') or key_metrics.get('beta')
        set_named_range_value(wb, 'Comps_Data_Beta', beta)

        logger.debug("Market data written")

        # Write valuation multiples (from Yahoo Finance key_metrics)
        logger.debug("Writing valuation multiples...")

        pe = key_metrics.get('trailingPE', 0)
        set_named_range_value(wb, 'Comps_Data_PE', pe)

        forward_pe = key_metrics.get('forwardPE', 0)
        set_named_range_value(wb, 'Comps_Data_ForwardPE', forward_pe)

        pb = key_metrics.get('priceToBook', 0)
        set_named_range_value(wb, 'Comps_Data_PB', pb)

        ps = key_metrics.get('priceToSales', 0)
        set_named_range_value(wb, 'Comps_Data_PS', ps)

        ev_revenue = key_metrics.get('enterpriseToRevenue', 0)
        set_named_range_value(wb, 'Comps_Data_EVRevenue', ev_revenue)

        ev_ebitda = key_metrics.get('enterpriseToEbitda', 0)
        set_named_range_value(wb, 'Comps_Data_EVEBITDA', ev_ebitda)

        # EV/EBIT: calculate from enterprise value and EBIT if not directly available
        enterprise_value = key_metrics.get('enterpriseValue', 0)
        set_named_range_value(wb, 'Comps_Data_EnterpriseValue', enterprise_value)

        if ebit and ebit != 0 and enterprise_value:
            ev_ebit = utils.safe_divide(enterprise_value, ebit, default=0)
        else:
            ev_ebit = 0
        set_named_range_value(wb, 'Comps_Data_EVEBIT', ev_ebit)

        debt_equity = key_metrics.get('debtToEquity', 0)
        set_named_range_value(wb, 'Comps_Data_DebtEquity', debt_equity)

        logger.debug("Valuation multiples written")

        logger.info("=" * 70)
        logger.info("COMPS YAHOO DATA WRITE COMPLETE")
        logger.info("=" * 70)
        
        utils.log_info(f"Comps data written for {data.get('ticker')}")
        return True
        
    except Exception as e:
        logger.error(f"ERROR WRITING COMPS YAHOO DATA: {e}", exc_info=True)
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write Comps data', str(e))
        return False


# ============================================================================
# MODEL CLEARING FUNCTIONS
# ============================================================================

def _clear_data_values(ws, sheet_name: str) -> int:
    """
    Clear NUMERIC data values from a Yahoo_Data sheet while preserving:
    - All formulas (cells starting with '=')
    - All text labels (string values)
    - All formatting

    Only clears: int, float values that were written by Python writers.

    OPTIMIZED: Uses batch reads to minimize COM calls.
    Previous version made 4500+ COM calls per sheet (very slow).
    This version makes ~10 COM calls per sheet (fast).

    Returns number of cells cleared.
    """
    used = ws.used_range
    if used is None:
        return 0

    last_row = used.last_cell.row
    last_col = used.last_cell.column

    # Skip if only column A exists (labels only)
    if last_col < 2:
        return 0

    # Define the data range (columns B onwards, skip column A which is labels)
    # Use xlwings range for batch operations
    data_range = ws.range((1, 2), (last_row, last_col))

    # Batch read all values and formulas in TWO COM calls (instead of thousands)
    try:
        all_values = data_range.value
        all_formulas = data_range.formula
    except Exception as e:
        logger.warning(f"Could not read data range in {sheet_name}: {e}")
        return 0

    # Handle single-cell case (returns scalar, not list)
    if not isinstance(all_values, list):
        all_values = [[all_values]]
        all_formulas = [[all_formulas]]

    # Handle single-row case (returns list, not list of lists)
    if all_values and not isinstance(all_values[0], list):
        all_values = [all_values]
        all_formulas = [all_formulas]

    if not all_values:
        return 0

    # Process in memory - find cells that need clearing
    cells_to_clear = []
    for row_idx, row_data in enumerate(all_values):
        if row_data is None:
            continue
        formula_row = all_formulas[row_idx] if row_idx < len(all_formulas) else None

        for col_idx, val in enumerate(row_data):
            # Skip if formula
            if formula_row:
                formula = formula_row[col_idx] if col_idx < len(formula_row) else None
                if formula and str(formula).startswith('='):
                    continue

            # Skip empty
            if val is None or val == '':
                continue

            # Only clear NUMERIC values
            if isinstance(val, (int, float)):
                # Excel row/col (1-indexed), offset by +2 for column (B=2)
                excel_row = row_idx + 1
                excel_col = col_idx + 2
                cells_to_clear.append((excel_row, excel_col))

    # Clear cells - batch by setting values to None
    # For small numbers of cells, individual clears are fine
    # For larger numbers, we could build a new array, but individual is simpler
    cleared = 0
    for (row, col) in cells_to_clear:
        try:
            ws.cells(row, col).value = None
            cleared += 1
        except Exception as e:
            logger.debug(f"Could not clear cell: {e}")

    return cleared


def clear_other_models(selected_model: str, wb: Optional[xw.Book] = None) -> bool:
    """
    Clear Yahoo_Data sheets for all models EXCEPT the selected one.

    Preserves:
    - All labels (text in column A and header rows)
    - All formulas
    - All formatting

    Only clears numeric data values written by Python writers.
    """
    try:
        if wb is None:
            wb = utils.get_workbook()

        MODEL_SHEET_MAP = {
            'Standard DCF': 'DCF_Yahoo_Data',
            'DDM': 'DDM_Yahoo_Data',
            'Revenue-Based': 'RevBased_Yahoo_Data',
            'Comps': 'Comps_Yahoo_Data',
        }

        all_models = ['Standard DCF', 'DDM', 'Revenue-Based', 'Comps']
        total_cleared = 0

        logger.info("Clearing data from non-selected models...")

        for model in all_models:
            if model == selected_model:
                logger.debug(f"[KEEP] {model} (selected)")
                continue

            sheet_name = MODEL_SHEET_MAP.get(model)
            if not sheet_name:
                continue

            try:
                ws = wb.sheets[sheet_name]
            except Exception as e:
                logger.warning(f"Sheet '{sheet_name}' not found: {e}")
                continue

            cells_cleared = _clear_data_values(ws, sheet_name)
            total_cleared += cells_cleared
            logger.debug(f"[CLEARED] {model}: {cells_cleared} cells in {sheet_name}")

        logger.info(f"Total cells cleared: {total_cleared}")
        return True

    except Exception as e:
        logger.error(f"Failed to clear models: {e}", exc_info=True)
        utils.log_error('EXCEL_CLEAR', 'Multiple',
                       'Failed to clear other models', str(e))
        return False


# ============================================================================
# HISTORY SHEET FUNCTIONS
# ============================================================================

def save_to_history(data: Dict[str, Any] = None, wb: xw.Book = None) -> bool:
    """
    Save current analysis to History sheet.

    Reads values from Excel (named ranges + specific cells) and appends
    one row to the History sheet. Data starts at row 13.

    Header structure (row 12) — 22 columns, unified with VBA SaveToHistory:
    A: Date | B: Ticker | C: Company Name | D: Sector | E: Industry |
    F: Model Used | G: Current Price |
    H: Conservative | I: Base | J: Optimistic |
    K: AI-Capex Cons | L: AI-Capex Base | M: AI-Capex Opt |
    N: Market | O: Market+AI |
    P: Best Case Value | Q: Upside % |
    R: Growth Rate | S: WACC | T: Terminal Growth |
    U: Capex Reduction | V: Notes

    Args:
        data: Optional data dict (not used - we read from Excel)
        wb: Workbook (uses active if not provided)

    Returns:
        True if save succeeded
    """
    import datetime

    try:
        if wb is None:
            wb = xw.books.active

        # Get History sheet
        try:
            ws = wb.sheets['History']
        except Exception as e:
            logger.error(f"History sheet error: {e}")
            return False

        # Find next empty row by scanning DOWN from row 13
        DATA_START_ROW = 13
        MAX_ROW = 112  # Don't exceed 100 entries (rows 13-112)

        next_row = DATA_START_ROW
        while ws.range(f'A{next_row}').value is not None:
            next_row += 1
            if next_row > MAX_ROW:
                logger.warning("History sheet is full (100 entries). Please manually clear old entries to make room.")
                return False

        logger.info(f"Saving to History row {next_row}...")

        # Helper to read named ranges safely
        def read_named(name, default=None):
            try:
                val = wb.names(name).refers_to_range.value
                # Skip "Pending" values
                if val == 'Pending':
                    return default
                return val if val is not None else default
            except Exception as e:
                logger.debug(f"Could not read named range '{name}': {e}")
                return default

        # Helper to read from specific sheet/cell
        def read_cell(sheet_name, address, default=None):
            try:
                val = wb.sheets[sheet_name].range(address).value
                return val if val is not None else default
            except Exception as e:
                logger.debug(f"Could not read cell {sheet_name}!{address}: {e}")
                return default

        # Get selected model to determine which growth/WACC to read
        selected_model = read_named('SelectedModel', 'Unknown')

        # Read WACC based on model
        wacc = None
        if selected_model == 'Standard DCF':
            wacc = read_named('DCF_WACC_Base')
        elif selected_model == 'DDM':
            wacc = read_cell('DDM_Assumptions', 'C38')  # Cost of Equity
        elif selected_model == 'Revenue-Based':
            wacc = read_named('RevBased_Asmp_WACC_Base')

        # Read Growth Rate based on model
        growth_rate = None
        if selected_model == 'Standard DCF':
            growth_rate = read_named('DCF_Asmp_RevGrowth15_Base')
        elif selected_model == 'DDM':
            growth_rate = read_named('DDM_Asmp_DivGrowth_Stage1_Base')
        elif selected_model == 'Revenue-Based':
            growth_rate = read_named('RevBased_Asmp_NearTermGrowth_Base')

        # Read Terminal Growth
        terminal_growth = None
        if selected_model == 'Standard DCF':
            terminal_growth = read_named('DCF_Asmp_TermGrowth_Base')
        elif selected_model == 'DDM':
            terminal_growth = read_named('DDM_Asmp_TerminalGrowth_Base')

        # Read sector and industry from data dict if available, else from named range
        sector = None
        industry = None
        if data:
            sector = data.get('sector')
            industry = data.get('industry')
        if not sector:
            sector = read_named('Sector', '')
        if not industry:
            industry = read_named('Industry', '')

        # Build the row data matching header structure (columns A-V, 22 cols)
        # Unified with VBA SaveToHistory layout
        row_data = [
            datetime.datetime.now(),                    # A: Date
            read_named('TickerInput', ''),              # B: Ticker
            read_named('CompanyName', ''),              # C: Company Name
            sector,                                      # D: Sector
            industry,                                    # E: Industry
            selected_model,                              # F: Model Used
            read_named('Current_Price'),                 # G: Current Price
            read_named('IntrinsicValue_Cons'),           # H: Conservative
            read_named('IntrinsicValue_Base'),           # I: Base
            read_named('IntrinsicValue_Opt'),            # J: Optimistic
            read_named('IntrinsicValue_AI_Cons'),        # K: AI-Capex Cons
            read_named('IntrinsicValue_AI_Base'),        # L: AI-Capex Base
            read_named('IntrinsicValue_AI_Opt'),         # M: AI-Capex Opt
            read_named('Market_IntrinsicValue'),         # N: Market
            read_named('MarketAI_IntrinsicValue'),       # O: Market+AI
            read_named('BestCase'),                      # P: Best Case Value
            read_named('UpsidePotential'),               # Q: Upside %
            growth_rate,                                 # R: Growth Rate
            wacc,                                        # S: WACC
            terminal_growth,                             # T: Terminal Growth
            None,                                        # U: Capex Reduction (not tracked)
            None,                                        # V: Notes
        ]

        # Write the entire row in ONE batch write
        ws.range(f'A{next_row}').value = row_data

        # Apply number formatting to the new row
        try:
            ws.range(f'A{next_row}').number_format = 'mm/dd/yyyy hh:mm'
            ws.range(f'G{next_row}:P{next_row}').number_format = '$#,##0.00'
            ws.range(f'Q{next_row}').number_format = '0.0%'
            ws.range(f'R{next_row}:T{next_row}').number_format = '0.0%'
        except Exception as e:
            logger.debug(f"Formatting error: {e}")

        ticker = row_data[1] or 'Unknown'
        logger.info(f"History saved: {ticker} to row {next_row}")
        logger.info(f"Saved {ticker} analysis to History row {next_row}")
        return True

    except Exception as e:
        logger.error(f"Failed to save to history: {e}", exc_info=True)
        return False


def read_all_intrinsic_values(wb: xw.Book) -> Dict[str, Dict[str, Any]]:
    """
    Read intrinsic value prices for all 8 scenarios across all 4 models.

    Uses a hybrid approach:
      Phase 1 (fast path): Try per-model named ranges (e.g., DCF_IntrinsicValue_Base)
      Phase 2 (fallback): Switch SelectedModel, recalculate, read Home sheet ranges

    IMPORTANT: The batch writer must be ended and wb.app.calculate() called
    BEFORE this function, so Dashboard formulas have recalculated.

    Args:
        wb: Active xlwings workbook (with all data already written and recalculated)

    Returns:
        Dict like:
        {
            'Standard DCF': {'Conservative': 125.50, 'Base': 142.30, ...},
            'DDM': {'Conservative': None, 'Base': None, ...},
            ...
        }
    """
    results = {model: {} for model in config.ALL_MODELS}

    # Save original SelectedModel so we can restore it
    original_model = get_named_range_value(wb, 'SelectedModel', default='')
    logger.debug(f"Original SelectedModel: '{original_model}'")

    try:
        # PHASE 1: Try per-model named ranges (fast path — no model switching)
        models_needing_fallback = []

        for model in config.ALL_MODELS:
            range_map = config.INTRINSIC_RANGE_MAP.get(model, {})
            missing_count = 0

            for scenario in config.SCENARIO_LABELS:
                range_name = range_map.get(scenario)
                if range_name:
                    try:
                        val = wb.names[range_name].refers_to_range.value
                        if val is not None and isinstance(val, (int, float)) and val != 0:
                            results[model][scenario] = round(val, 2)
                        else:
                            missing_count += 1
                    except Exception as e:
                        logger.debug(f"Could not read {range_name}: {e}")
                        missing_count += 1
                else:
                    missing_count += 1

            if missing_count > 0:
                models_needing_fallback.append(model)
                logger.debug(f"{model}: {8 - missing_count}/8 from named ranges, "
                             f"{missing_count} need fallback")
            else:
                logger.debug(f"{model}: all 8 scenarios from named ranges")

        # PHASE 2: Fallback — switch SelectedModel and read Home sheet ranges
        if models_needing_fallback:
            logger.info(f"Using model-switch fallback for: {models_needing_fallback}")

            for model in models_needing_fallback:
                # Write model name to SelectedModel (NOT a formula cell — safe to write)
                _set_named_range_value_immediate(wb, 'SelectedModel', model)
                wb.app.calculate()

                for i, scenario in enumerate(config.SCENARIO_LABELS):
                    # Only read if not already populated from Phase 1
                    if scenario not in results[model]:
                        home_range = config.HOME_SCENARIO_RANGES[i]
                        try:
                            val = wb.names[home_range].refers_to_range.value
                            if val is not None and isinstance(val, (int, float)):
                                results[model][scenario] = round(val, 2)
                            else:
                                results[model][scenario] = None
                        except Exception as e:
                            logger.debug(f"Could not read {home_range} for {model}/{scenario}: {e}")
                            results[model][scenario] = None

                filled = sum(1 for v in results[model].values()
                             if v is not None and v != 0)
                logger.debug(f"{model}: {filled}/8 scenarios populated after fallback")

    finally:
        # ALWAYS restore original SelectedModel
        if original_model:
            _set_named_range_value_immediate(wb, 'SelectedModel', original_model)
            wb.app.calculate()
            logger.debug(f"SelectedModel restored to '{original_model}'")

    return results


def write_model_comparison(data: Dict[str, Any], market_results: Dict[str, Any],
                           detection_result: Dict[str, Any],
                           wb: Optional[xw.Book] = None,
                           intrinsic_prices: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
    """
    Write a side-by-side model comparison to the Model_Comparison sheet.

    Displays market-implied values, data availability, auto-detect scores,
    and the primary model recommendation for all 4 valuation models.

    If the Model_Comparison sheet doesn't exist, creates it automatically.

    Args:
        data: Extracted data from YahooFinanceExtractor
        market_results: Dict from MarketImpliedCalculator.calculate_all()
                        Keys: 'dcf', 'ddm', 'revenue_based', 'comps'
        detection_result: Dict from ModelDetector.detect_model()
        wb: Workbook (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        if wb is None:
            wb = utils.get_workbook()

        logger.info("=" * 70)
        logger.info("WRITING MODEL COMPARISON")
        logger.info("=" * 70)

        # Find or create the Model_Comparison sheet
        sheet_name = 'Model_Comparison'
        try:
            ws = wb.sheets[sheet_name]
        except Exception as e:
            # Create the sheet after Home
            logger.debug(f"Sheet '{sheet_name}' not found ({e}), creating...")
            try:
                ws = wb.sheets.add(sheet_name, after=wb.sheets['Home'])
                logger.info(f"Created '{sheet_name}' sheet")
            except Exception as e2:
                logger.debug(f"Could not create after Home: {e2}")
                ws = wb.sheets.add(sheet_name)
                logger.info(f"Created '{sheet_name}' sheet (at end)")

        # Try named ranges first, fall back to direct cell writing
        company_info = data.get('company_info', {})
        key_metrics = data.get('key_metrics', {})
        ticker = data.get('ticker', '')
        company_name = (company_info.get('longName') or
                        company_info.get('shortName') or ticker)
        current_price = (key_metrics.get('currentPrice') or
                         key_metrics.get('regularMarketPrice'))
        primary_model = detection_result.get('recommended_model', 'Unknown')
        confidence = detection_result.get('confidence_percentage', 0)
        data_avail = data.get('data_availability', {})

        # Try named ranges
        set_named_range_value(wb, 'ModelComp_Ticker', ticker)
        set_named_range_value(wb, 'ModelComp_CompanyName', company_name)
        set_named_range_value(wb, 'ModelComp_CurrentPrice', current_price)
        set_named_range_value(wb, 'ModelComp_PrimaryModel', primary_model)
        set_named_range_value(wb, 'ModelComp_Confidence', f"{confidence}%")

        # DCF results
        dcf = market_results.get('dcf', {})
        set_named_range_value(wb, 'ModelComp_DCF_ImpliedGrowth',
                              dcf.get('implied_growth'))
        set_named_range_value(wb, 'ModelComp_DCF_Interpretation',
                              dcf.get('interpretation', ''))
        set_named_range_value(wb, 'ModelComp_DCF_DataAvailable',
                              'Yes' if data_avail.get('revenue') else 'No')

        # DDM results
        ddm = market_results.get('ddm', {})
        set_named_range_value(wb, 'ModelComp_DDM_ImpliedGrowth',
                              ddm.get('implied_growth'))
        set_named_range_value(wb, 'ModelComp_DDM_Interpretation',
                              ddm.get('interpretation', ''))
        set_named_range_value(wb, 'ModelComp_DDM_DataAvailable',
                              'Yes' if data_avail.get('dividends') else 'No')

        # RevBased results
        revbased = market_results.get('revenue_based', {})
        set_named_range_value(wb, 'ModelComp_RevBased_ImpliedMultiple',
                              revbased.get('implied_multiple'))
        set_named_range_value(wb, 'ModelComp_RevBased_Interpretation',
                              revbased.get('interpretation', ''))
        set_named_range_value(wb, 'ModelComp_RevBased_DataAvailable',
                              'Yes' if data_avail.get('revenue') else 'No')

        # Comps results
        comps = market_results.get('comps', {})
        set_named_range_value(wb, 'ModelComp_Comps_ImpliedPremium',
                              comps.get('implied_premium'))
        set_named_range_value(wb, 'ModelComp_Comps_Interpretation',
                              comps.get('interpretation', ''))
        set_named_range_value(wb, 'ModelComp_Comps_DataAvailable', 'Yes')

        # Auto-detect scores (from detection result)
        scores = detection_result.get('model_scores', {})
        set_named_range_value(wb, 'ModelComp_DCF_Score',
                              scores.get('Standard DCF'))
        set_named_range_value(wb, 'ModelComp_DDM_Score',
                              scores.get('DDM'))
        set_named_range_value(wb, 'ModelComp_RevBased_Score',
                              scores.get('Revenue-Based'))
        set_named_range_value(wb, 'ModelComp_Comps_Score',
                              scores.get('Comps'))

        # Write intrinsic value prices to named ranges (32 ranges)
        if intrinsic_prices:
            prefix_map = {
                'Standard DCF': 'DCF', 'DDM': 'DDM',
                'Revenue-Based': 'RevBased', 'Comps': 'Comps',
            }
            scenario_suffix = {
                'Conservative': 'Cons', 'Base': 'Base', 'Optimistic': 'Opt',
                'AI-Cons': 'AICons', 'AI-Base': 'AIBase', 'AI-Opt': 'AIOpt',
                'Market': 'Market', 'Market+AI': 'MarketAI',
            }
            for model, prices in intrinsic_prices.items():
                pfx = prefix_map.get(model, '')
                for scenario, price in prices.items():
                    sfx = scenario_suffix.get(scenario, '')
                    if pfx and sfx:
                        range_name = f'ModelComp_{pfx}_{sfx}'
                        set_named_range_value(wb, range_name, price)

            # Write summary stats
            all_base = [intrinsic_prices[m].get('Base')
                        for m in config.ALL_MODELS
                        if intrinsic_prices.get(m, {}).get('Base')]
            valid_base = [v for v in all_base if v and isinstance(v, (int, float)) and v > 0]
            if valid_base:
                set_named_range_value(wb, 'ModelComp_Avg_Base',
                                      round(sum(valid_base) / len(valid_base), 2))

            # Range across all scenarios and models
            all_prices = []
            for m in config.ALL_MODELS:
                for s in config.SCENARIO_LABELS:
                    v = intrinsic_prices.get(m, {}).get(s)
                    if v and isinstance(v, (int, float)) and v > 0:
                        all_prices.append(v)
            if all_prices:
                set_named_range_value(wb, 'ModelComp_Range_Low', round(min(all_prices), 2))
                set_named_range_value(wb, 'ModelComp_Range_High', round(max(all_prices), 2))

        # Enhanced market-implied detail to named ranges
        dcf = market_results.get('dcf', {})
        set_named_range_value(wb, 'ModelComp_DCF_WACC', dcf.get('wacc'))
        set_named_range_value(wb, 'ModelComp_DCF_TermGrowth', dcf.get('terminal_growth'))
        set_named_range_value(wb, 'ModelComp_DCF_FCFMargin', dcf.get('fcf_margin'))
        set_named_range_value(wb, 'ModelComp_DCF_Converged',
                              'Yes' if dcf.get('converged') else 'No')

        ddm = market_results.get('ddm', {})
        set_named_range_value(wb, 'ModelComp_DDM_DPS', ddm.get('dps'))
        set_named_range_value(wb, 'ModelComp_DDM_ReqReturn', ddm.get('required_return'))

        revbased = market_results.get('revenue_based', {})
        set_named_range_value(wb, 'ModelComp_RevBased_EV', revbased.get('enterprise_value'))
        set_named_range_value(wb, 'ModelComp_RevBased_Revenue', revbased.get('revenue'))

        comps = market_results.get('comps', {})
        set_named_range_value(wb, 'ModelComp_Comps_CompanyPE', comps.get('company_pe'))
        set_named_range_value(wb, 'ModelComp_Comps_IndustryPE', comps.get('industry_pe'))

        # Write the formatted table directly to cells
        _write_comparison_table(ws, data, market_results, detection_result,
                                intrinsic_prices)

        logger.info(f"Model comparison written for {ticker}")
        logger.debug(f"Primary: {primary_model} ({confidence}%)")
        if intrinsic_prices:
            for model in config.ALL_MODELS:
                base_val = intrinsic_prices.get(model, {}).get('Base')
                if base_val:
                    logger.debug(f"{model} Base: ${base_val:.2f}")
                else:
                    logger.debug(f"{model} Base: N/A")

        logger.info("=" * 70)
        logger.info("MODEL COMPARISON WRITE COMPLETE")
        logger.info("=" * 70)

        utils.log_info(f"Model comparison written for {ticker}")
        return True

    except Exception as e:
        logger.error(f"ERROR WRITING MODEL COMPARISON: {e}", exc_info=True)
        utils.log_error('EXCEL_WRITE', data.get('ticker', 'Unknown'),
                       'Failed to write model comparison', str(e))
        return False


def _write_comparison_table(ws, data: Dict[str, Any],
                             market_results: Dict[str, Any],
                             detection_result: Dict[str, Any],
                             intrinsic_prices: Optional[Dict[str, Dict[str, Any]]] = None):
    """
    Write a comprehensive comparison table directly to cells on Model_Comparison sheet.

    Layout:
      Section 1: Header (rows 1-3)
      Section 2: Intrinsic Value Price Grid — 8 scenarios × 4 models (rows 5-13)
      Section 3: Upside/Downside vs Current Price (rows 15-23)
      Section 4: Market-Implied Analysis Detail (rows 25-38)
      Section 5: Model Suitability (rows 40-44)
    """
    company_info = data.get('company_info', {})
    key_metrics = data.get('key_metrics', {})
    data_avail = data.get('data_availability', {})
    ticker = data.get('ticker', '')
    company_name = (company_info.get('longName') or
                    company_info.get('shortName') or ticker)
    current_price = (key_metrics.get('currentPrice') or
                     key_metrics.get('regularMarketPrice', 0))
    primary_model = detection_result.get('recommended_model', 'Unknown')
    confidence = detection_result.get('confidence_percentage', 0)
    scores = detection_result.get('model_scores', {})

    dcf = market_results.get('dcf', {})
    ddm = market_results.get('ddm', {})
    revbased = market_results.get('revenue_based', {})
    comps = market_results.get('comps', {})

    if intrinsic_prices is None:
        intrinsic_prices = {}

    # Column mapping: B=DCF, C=DDM, D=RevBased, E=Comps, F=Average, G=vs Price
    model_cols = {'Standard DCF': 'B', 'DDM': 'C', 'Revenue-Based': 'D', 'Comps': 'E'}

    # Clear the sheet first to avoid stale data
    try:
        ws.clear()
    except Exception as e:
        logger.warning(f"Could not clear Model_Comparison: {e}")

    # =========================================================================
    # SECTION 1: Header (rows 1-3)
    # =========================================================================
    ws.range('A1').value = "Model Comparison"
    ws.range('A2').value = f"{ticker} - {company_name}"
    ws.range('A3').value = f"Current Price: ${current_price:.2f}" if current_price else "Current Price: N/A"
    ws.range('D3').value = f"Primary: {primary_model} ({confidence}%)"
    ws.range('F3').value = f"Generated: {utils.get_timestamp()}"

    # =========================================================================
    # SECTION 2: Intrinsic Value — Price Per Share (rows 5-13)
    # =========================================================================
    ws.range('A4').value = "INTRINSIC VALUE — PRICE PER SHARE"

    # Headers
    headers = ['Scenario', 'Standard DCF', 'DDM', 'Revenue-Based', 'Comps', 'Average', 'vs Price']
    ws.range('A5').value = headers

    scenario_labels = config.SCENARIO_LABELS
    scenario_display = [
        'Conservative', 'Base Case', 'Optimistic',
        'AI-Capex Cons', 'AI-Capex Base', 'AI-Capex Opt',
        'Market Case', 'Market+AI Case',
    ]

    for i, (scenario_key, display_name) in enumerate(zip(scenario_labels, scenario_display)):
        row = 6 + i
        ws.range(f'A{row}').value = display_name

        # Collect valid prices for averaging
        valid_prices = []

        for model in config.ALL_MODELS:
            col = model_cols[model]
            price = intrinsic_prices.get(model, {}).get(scenario_key)
            if price and isinstance(price, (int, float)) and price > 0:
                ws.range(f'{col}{row}').value = price
                valid_prices.append(price)
            else:
                ws.range(f'{col}{row}').value = 'N/A'

        # Average (column F)
        if valid_prices:
            avg = sum(valid_prices) / len(valid_prices)
            ws.range(f'F{row}').value = round(avg, 2)

            # vs Price (column G) — upside/downside of the average
            if current_price and current_price > 0:
                upside = (avg - current_price) / current_price
                ws.range(f'G{row}').value = upside
        else:
            ws.range(f'F{row}').value = 'N/A'
            ws.range(f'G{row}').value = 'N/A'

    # =========================================================================
    # SECTION 3: Upside/Downside vs Current Price (rows 15-23)
    # =========================================================================
    ws.range('A14').value = "UPSIDE / DOWNSIDE vs CURRENT PRICE"

    # Headers
    upside_headers = ['Scenario', 'Standard DCF', 'DDM', 'Revenue-Based', 'Comps']
    ws.range('A15').value = upside_headers

    for i, (scenario_key, display_name) in enumerate(zip(scenario_labels, scenario_display)):
        row = 16 + i
        ws.range(f'A{row}').value = display_name

        for model in config.ALL_MODELS:
            col = model_cols[model]
            price = intrinsic_prices.get(model, {}).get(scenario_key)
            if (price and isinstance(price, (int, float)) and price > 0 and
                    current_price and current_price > 0):
                upside = (price - current_price) / current_price
                ws.range(f'{col}{row}').value = upside
            else:
                ws.range(f'{col}{row}').value = 'N/A'

    # =========================================================================
    # SECTION 4: Market-Implied Analysis Detail (rows 25-38)
    # =========================================================================
    ws.range('A24').value = "MARKET-IMPLIED ANALYSIS"

    mi_headers = ['Metric', 'Standard DCF', 'DDM', 'Revenue-Based', 'Comps']
    ws.range('A25').value = mi_headers

    # Row 26: Key Implied Metric
    ws.range('A26').value = 'Key Implied Value'
    dcf_val = dcf.get('implied_growth')
    ws.range('B26').value = f"{dcf_val:.2%}" if dcf_val is not None else 'N/A'
    ddm_val = ddm.get('implied_growth')
    ws.range('C26').value = f"{ddm_val:.2%}" if ddm_val is not None else 'N/A'
    rev_val = revbased.get('implied_multiple')
    ws.range('D26').value = f"{rev_val:.2f}x" if rev_val is not None else 'N/A'
    comp_val = comps.get('implied_premium')
    ws.range('E26').value = f"{comp_val:.1%}" if comp_val is not None else 'N/A'

    # Row 27: Metric Type
    ws.range('A27').value = 'Metric Type'
    ws.range('B27').value = 'Rev Growth'
    ws.range('C27').value = 'Div Growth'
    ws.range('D27').value = 'EV/Revenue'
    ws.range('E27').value = 'Quality Premium'

    # Row 28: Interpretation
    ws.range('A28').value = 'Interpretation'
    ws.range('B28').value = dcf.get('interpretation', 'N/A')
    ws.range('C28').value = ddm.get('interpretation', 'N/A')
    ws.range('D28').value = revbased.get('interpretation', 'N/A')
    ws.range('E28').value = comps.get('interpretation', 'N/A')

    # Row 29: Converged (DCF only)
    ws.range('A29').value = 'Converged?'
    ws.range('B29').value = 'Yes' if dcf.get('converged') else ('No' if dcf else 'N/A')
    ws.range('C29').value = 'N/A'
    ws.range('D29').value = 'N/A'
    ws.range('E29').value = 'N/A'

    # Row 30: WACC (DCF) / Required Return (DDM)
    ws.range('A30').value = 'WACC / Req Return'
    wacc = dcf.get('wacc')
    ws.range('B30').value = f"{wacc:.2%}" if wacc is not None else 'N/A'
    req_ret = ddm.get('required_return')
    ws.range('C30').value = f"{req_ret:.2%}" if req_ret is not None else 'N/A'
    ws.range('D30').value = 'N/A'
    ws.range('E30').value = 'N/A'

    # Row 31: Terminal Growth (DCF only)
    ws.range('A31').value = 'Terminal Growth'
    tg = dcf.get('terminal_growth')
    ws.range('B31').value = f"{tg:.2%}" if tg is not None else 'N/A'
    ws.range('C31').value = 'N/A'
    ws.range('D31').value = 'N/A'
    ws.range('E31').value = 'N/A'

    # Row 32: FCF Margin (DCF only)
    ws.range('A32').value = 'FCF Margin'
    fcf_m = dcf.get('fcf_margin')
    ws.range('B32').value = f"{fcf_m:.1%}" if fcf_m is not None else 'N/A'
    ws.range('C32').value = 'N/A'
    ws.range('D32').value = 'N/A'
    ws.range('E32').value = 'N/A'

    # Row 33: DPS (DDM only)
    ws.range('A33').value = 'Dividend/Share'
    ws.range('B33').value = 'N/A'
    dps = ddm.get('dps')
    ws.range('C33').value = f"${dps:.2f}" if dps is not None else 'N/A'
    ws.range('D33').value = 'N/A'
    ws.range('E33').value = 'N/A'

    # Row 34: Enterprise Value (RevBased only)
    ws.range('A34').value = 'Enterprise Value'
    ws.range('B34').value = 'N/A'
    ws.range('C34').value = 'N/A'
    ev = revbased.get('enterprise_value')
    ws.range('D34').value = f"${ev/1e9:.1f}B" if ev and ev > 0 else 'N/A'
    ws.range('E34').value = 'N/A'

    # Row 35: Revenue TTM (RevBased only)
    ws.range('A35').value = 'Revenue (TTM)'
    ws.range('B35').value = 'N/A'
    ws.range('C35').value = 'N/A'
    rev = revbased.get('revenue')
    ws.range('D35').value = f"${rev/1e9:.1f}B" if rev and rev > 0 else 'N/A'
    ws.range('E35').value = 'N/A'

    # Row 36: Company P/E (Comps only)
    ws.range('A36').value = 'Company P/E'
    ws.range('B36').value = 'N/A'
    ws.range('C36').value = 'N/A'
    ws.range('D36').value = 'N/A'
    cpe = comps.get('company_pe')
    ws.range('E36').value = f"{cpe:.1f}x" if cpe is not None else 'N/A'

    # Row 37: Industry P/E (Comps only)
    ws.range('A37').value = 'Industry P/E'
    ws.range('B37').value = 'N/A'
    ws.range('C37').value = 'N/A'
    ws.range('D37').value = 'N/A'
    ipe = comps.get('industry_pe')
    ws.range('E37').value = f"{ipe:.1f}x" if ipe is not None else 'N/A'

    # =========================================================================
    # SECTION 5: Model Suitability (rows 39-44)
    # =========================================================================
    ws.range('A39').value = "MODEL SUITABILITY"

    suit_headers = ['Metric', 'Standard DCF', 'DDM', 'Revenue-Based', 'Comps']
    ws.range('A40').value = suit_headers

    # Data Available
    ws.range('A41').value = 'Data Available'
    ws.range('B41').value = 'Yes' if data_avail.get('revenue') else 'No'
    ws.range('C41').value = 'Yes' if data_avail.get('dividends') else 'No'
    ws.range('D41').value = 'Yes' if data_avail.get('revenue') else 'No'
    ws.range('E41').value = 'Yes'

    # Detection Score
    ws.range('A42').value = 'Detection Score'
    ws.range('B42').value = scores.get('Standard DCF')
    ws.range('C42').value = scores.get('DDM')
    ws.range('D42').value = scores.get('Revenue-Based')
    ws.range('E42').value = scores.get('Comps')

    # Recommended
    ws.range('A43').value = 'Recommended'
    for col, model in [('B', 'Standard DCF'), ('C', 'DDM'),
                       ('D', 'Revenue-Based'), ('E', 'Comps')]:
        ws.range(f'{col}43').value = '✓' if model == primary_model else ''

    # Reasoning
    ws.range('A44').value = 'Reasoning'
    ws.range('B44').value = detection_result.get('reasoning', '')

    # =========================================================================
    # FORMATTING
    # =========================================================================
    try:
        # Title formatting
        ws.range('A1').font.bold = True
        ws.range('A1').font.size = 14
        ws.range('A2').font.size = 11

        # Section headers (bold, colored background)
        dark_blue = (50, 50, 80)
        white = (255, 255, 255)

        for section_label_cell in ['A4', 'A14', 'A24', 'A39']:
            cell = ws.range(section_label_cell)
            cell.font.bold = True
            cell.font.size = 11

        # Table header rows — dark blue with white text
        for header_row in ['A5:G5', 'A15:E15', 'A25:E25', 'A40:E40']:
            rng = ws.range(header_row)
            rng.font.bold = True
            rng.font.size = 10
            rng.color = dark_blue
            rng.font.color = white

        # Currency format for intrinsic values (rows 6-13, columns B-F)
        for row in range(6, 14):
            for col in ['B', 'C', 'D', 'E', 'F']:
                cell = ws.range(f'{col}{row}')
                if isinstance(cell.value, (int, float)):
                    cell.number_format = '$#,##0.00'

        # Percentage format for vs Price column (G6:G13)
        for row in range(6, 14):
            cell = ws.range(f'G{row}')
            if isinstance(cell.value, (int, float)):
                cell.number_format = '+0.0%;-0.0%'

        # Percentage format for upside/downside section (rows 16-23, B-E)
        for row in range(16, 24):
            for col in ['B', 'C', 'D', 'E']:
                cell = ws.range(f'{col}{row}')
                if isinstance(cell.value, (int, float)):
                    cell.number_format = '+0.0%;-0.0%'
                    # Color: green for positive, red for negative
                    if cell.value >= 0:
                        cell.font.color = (34, 139, 34)   # Forest green
                    else:
                        cell.font.color = (178, 34, 34)   # Firebrick red

        # Column widths
        ws.range('A:A').column_width = 20
        for col in ['B', 'C', 'D', 'E']:
            ws.range(f'{col}:{col}').column_width = 18
        ws.range('F:F').column_width = 14
        ws.range('G:G').column_width = 14

    except Exception as e:
        logger.debug(f"Formatting error: {e}")


def format_history_sheet(wb: xw.Book = None) -> bool:
    """
    Apply professional formatting to the History sheet.

    - Bold headers with dark background
    - Column widths sized appropriately
    - Number formats for currency/percentage columns
    - Freeze panes at row 13
    - Auto-filter on headers
    """
    try:
        if wb is None:
            wb = xw.books.active

        ws = wb.sheets['History']

        # Header row formatting (row 12)
        header_range = ws.range('A12:T12')
        header_range.font.bold = True
        header_range.font.size = 10
        header_range.color = (50, 50, 80)  # Dark blue
        header_range.font.color = (255, 255, 255)  # White text
        header_range.api.HorizontalAlignment = -4108  # Center

        # Column widths
        widths = {
            'A': 16, 'B': 8, 'C': 25, 'D': 15, 'E': 20,
            'F': 14, 'G': 12, 'H': 12, 'I': 12, 'J': 12,
            'K': 12, 'L': 12, 'M': 12, 'N': 12, 'O': 10,
            'P': 10, 'Q': 8, 'R': 12, 'S': 12, 'T': 20
        }
        for col, width in widths.items():
            ws.range(f'{col}:{col}').column_width = width

        # Number formats for data region (rows 13-112)
        ws.range('A13:A112').number_format = 'mm/dd/yyyy hh:mm'
        ws.range('G13:N112').number_format = '$#,##0.00'
        ws.range('O13:R112').number_format = '0.0%'

        # Freeze panes
        ws.range('A13').select()
        wb.app.api.ActiveWindow.FreezePanes = True

        # Auto-filter on headers
        ws.range('A12:T12').api.AutoFilter()

        logger.info("History sheet formatted")
        return True

    except Exception as e:
        logger.error(f"Failed to format history sheet: {e}")
        return False


# ============================================================================
# MODULE METADATA
# ============================================================================

__version__ = '2.10'
__all__ = [
    'write_company_info',
    'write_detection_results',
    'write_data_availability',
    'write_placeholder_valuation',
    'write_dcf_yahoo_data',
    'write_ddm_yahoo_data',
    'write_revbased_yahoo_data',
    'write_comps_yahoo_data',
    'clear_other_models',
    'save_to_history',
    'format_history_sheet',
    'read_all_intrinsic_values',
    'write_model_comparison',
    'set_named_range_value',
]