"""
Market-Implied Calculator

Calculates what assumptions the market is implying based on current stock price.
Provides reverse calculations for all 4 valuation models:
- DCF: Reverse-solve for implied revenue growth rate
- DDM: Reverse-solve for implied dividend growth rate
- Revenue-Based: Calculate implied EV/Revenue multiple
- Comps: Calculate implied quality premium

Used for Scenarios 7 & 8 (Market Case and Market+AI Case)
"""

import logging
from typing import Dict, Any
import pandas as pd

import utils  # Import for safe_divide and logging
import config
from excel_helpers import get_df_value as _get_df_value

logger = logging.getLogger('StockValuation')


class MarketImpliedCalculator:
    """
    Calculate market-implied assumptions based on current stock price.
    
    Reverse-engineers what growth rates, multiples, or premiums the market
    is using to arrive at the current stock price.
    """
    
    def __init__(self, ticker: str, data: Dict[str, Any], current_price: float):
        """
        Initialize calculator with company data and current market price.
        
        Args:
            ticker (str): Stock ticker symbol
            data (dict): Extracted company data
            current_price (float): Current market price per share
        """
        self.ticker = ticker
        self.data = data
        self.current_price = current_price
        
        # Extract key data sections (use `or` to handle explicit None values)
        self.company_info = data.get('company_info') or {}
        self.key_metrics = data.get('key_metrics') or {}
        self.income_stmt = data.get('income_statement') or pd.DataFrame()
        self.balance_sheet = data.get('balance_sheet') or pd.DataFrame()
        self.cash_flow = data.get('cash_flow') or pd.DataFrame()

        # Get critical metrics — default to 0, not 1, to avoid 10^9x market cap errors
        self.shares_out = (
            self.company_info.get('shares_outstanding') or
            self.key_metrics.get('sharesOutstanding') or 0
        )
        if not self.shares_out:
            logger.warning(f"No shares outstanding data for {ticker} — using direct marketCap field")

        self.market_cap = (
            self.current_price * self.shares_out if self.shares_out else
            self.company_info.get('market_cap') or
            self.key_metrics.get('marketCap', 0)
        )

        if not self.market_cap:
            logger.warning(f"Market cap is zero for {ticker} — all calculations will be invalid")
        if not current_price:
            logger.warning(f"current_price=0 passed to MarketImpliedCalculator for {ticker}")

        logger.info(f"MarketImpliedCalculator initialized for {ticker}")
        logger.info(f"Current price: ${current_price:.2f}, Market cap: ${self.market_cap/1e9:.2f}B")
    
    
    def get_df_value(self, df: pd.DataFrame, row_name: str, col_index: int = 0, default: float = 0) -> float:
        """Delegate to excel_helpers.get_df_value."""
        return _get_df_value(df, row_name, col_index, default)
    
    
    def calculate_for_dcf(self) -> Dict[str, Any]:
        """
        Calculate market-implied revenue growth rate for DCF model.
        
        Uses binary search to find the revenue growth rate that makes
        the DCF valuation equal to the current market cap.
        
        Returns:
            dict: {
                'implied_growth': float,
                'converged': bool,
                'iterations': int,
                'interpretation': str
            }
        """
        try:
            logger.info(f"Calculating market-implied DCF assumptions for {self.ticker}")
            
            # Get current revenue (TTM)
            revenue = self.get_df_value(self.income_stmt, "Total Revenue", 0) or \
                     self.get_df_value(self.income_stmt, "Operating Revenue", 0)
            
            if not revenue or revenue <= 0:
                logger.info(f"No revenue data available for {self.ticker}")
                return {
                    'implied_growth': 0.0,
                    'converged': False,
                    'error': 'No revenue data'
                }
            
            # Get FCF or estimate from operating cash flow
            fcf = self.get_df_value(self.cash_flow, "Free Cash Flow", 0)
            if not fcf or fcf == 0:
                ocf = self.get_df_value(self.cash_flow, "Operating Cash Flow", 0)
                capex = abs(self.get_df_value(self.cash_flow, "Capital Expenditure", 0))
                fcf = ocf - capex if ocf else 0
            
            # Calculate FCF margin
            fcf_margin = utils.safe_divide(fcf, revenue, default=config.DEFAULT_FCF_MARGIN)
            if fcf_margin <= 0:
                fcf_margin = config.DEFAULT_FCF_MARGIN  # Use default if negative/zero
            
            # Get debt and cash for enterprise value
            total_debt = self.get_df_value(self.balance_sheet, "Total Debt", 0) or \
                        (self.get_df_value(self.balance_sheet, "Long Term Debt", 0) + \
                         self.get_df_value(self.balance_sheet, "Current Debt", 0))
            
            cash = self.get_df_value(self.balance_sheet, "Cash And Cash Equivalents", 0) or \
                  self.get_df_value(self.balance_sheet, "Cash", 0)
            
            enterprise_value = self.market_cap + total_debt - cash
            
            logger.info(f"  Revenue: ${revenue/1e9:.2f}B, FCF Margin: {fcf_margin:.1%}, EV: ${enterprise_value/1e9:.2f}B")
            
            # Binary search for implied growth rate
            min_growth = config.REVERSE_DCF_MIN_GROWTH  # -10%
            max_growth = config.REVERSE_DCF_MAX_GROWTH  # 60%
            tolerance = config.REVERSE_DCF_TOLERANCE    # 0.5%
            max_iterations = config.REVERSE_DCF_MAX_ITERATIONS
            
            wacc = config.DEFAULT_WACC
            terminal_growth = config.DEFAULT_TERMINAL_GROWTH
            
            converged = False
            iterations = 0
            implied_growth = 0.0
            mid_growth = (min_growth + max_growth) / 2  # Pre-initialize before loop

            # Guard against zero or negative enterprise value
            if enterprise_value <= 0:
                logger.warning(f"Enterprise value is {enterprise_value:.0f} for {self.ticker} — cannot converge DCF")
                return {
                    'implied_growth': 0.0,
                    'converged': False,
                    'error': f'Enterprise value is non-positive ({enterprise_value:.0f})',
                    'fcf_margin': fcf_margin,
                    'wacc': wacc,
                    'terminal_growth': terminal_growth
                }

            for i in range(max_iterations):
                iterations = i + 1
                mid_growth = (min_growth + max_growth) / 2

                # Calculate DCF value with this growth rate
                dcf_value = self._calculate_simple_dcf(
                    revenue, mid_growth, fcf_margin, wacc, terminal_growth
                )

                # Check convergence (use abs() on denominator for safety)
                error = abs(dcf_value - enterprise_value) / abs(enterprise_value)

                if error < tolerance:
                    implied_growth = mid_growth
                    converged = True
                    break

                # Adjust search range
                if dcf_value < enterprise_value:
                    min_growth = mid_growth  # Need higher growth
                else:
                    max_growth = mid_growth  # Need lower growth

            if not converged:
                # Use the last calculated value even if not fully converged
                implied_growth = mid_growth
                logger.info(f"DCF binary search did not fully converge after {iterations} iterations")
            
            # Interpret the result
            if implied_growth > 0.30:
                interpretation = "VERY HIGH growth expectations"
            elif implied_growth > 0.15:
                interpretation = "HIGH growth expectations"
            elif implied_growth > 0.05:
                interpretation = "MODERATE growth expectations"
            elif implied_growth > 0:
                interpretation = "LOW growth expectations"
            else:
                interpretation = "NEGATIVE growth expectations"
            
            logger.info(f"  DCF implied growth: {implied_growth:.2%} ({interpretation}), converged={converged} ({iterations} iters)")
            
            return {
                'implied_growth': implied_growth,
                'converged': converged,
                'iterations': iterations,
                'interpretation': interpretation,
                'fcf_margin': fcf_margin,
                'wacc': wacc,
                'terminal_growth': terminal_growth
            }
            
        except Exception as e:
            logger.error(f"Error calculating DCF market-implied: {e}")
            logger.warning(f"  Error: {e}")
            return {
                'implied_growth': 0.0,
                'converged': False,
                'error': str(e)
            }
    
    
    def _calculate_simple_dcf(self, revenue: float, growth_rate: float, 
                             fcf_margin: float, wacc: float, 
                             terminal_growth: float) -> float:
        """
        Calculate simplified DCF enterprise value.
        
        Args:
            revenue: Current revenue
            growth_rate: Revenue growth rate (decimal)
            fcf_margin: FCF as % of revenue
            wacc: Weighted average cost of capital
            terminal_growth: Terminal growth rate
            
        Returns:
            float: Calculated enterprise value
        """
        projection_years = config.PROJECTION_YEARS
        pv_fcf = 0
        
        # Project FCF for explicit forecast period
        current_revenue = revenue
        for year in range(1, projection_years + 1):
            # Revenue grows at specified rate
            current_revenue = current_revenue * (1 + growth_rate)
            
            # FCF = Revenue * FCF Margin
            fcf = current_revenue * fcf_margin
            
            # Discount to present value
            discount_factor = (1 + wacc) ** year
            pv_fcf += fcf / discount_factor
        
        # Terminal value
        terminal_revenue = current_revenue * (1 + terminal_growth)
        terminal_fcf = terminal_revenue * fcf_margin
        terminal_value = utils.safe_divide(terminal_fcf, (wacc - terminal_growth), default=0)
        
        # Discount terminal value to present
        pv_terminal = terminal_value / ((1 + wacc) ** projection_years)
        
        # Total enterprise value
        enterprise_value = pv_fcf + pv_terminal
        
        return enterprise_value
    
    
    def calculate_for_ddm(self) -> Dict[str, Any]:
        """
        Calculate market-implied dividend growth rate for DDM model.
        
        Uses Gordon Growth Model: P = D / (r - g)
        Solving for g: g = r - (D / P)
        
        Returns:
            dict: {
                'implied_growth': float,
                'interpretation': str
            }
        """
        try:
            logger.info(f"Calculating market-implied DDM assumptions for {self.ticker}")

            # Get most recent dividend per share — try dividend history first (most accurate)
            dividends_data = self.data.get('dividends', {})
            dps = dividends_data.get('most_recent', 0) if isinstance(dividends_data, dict) else 0

            if not dps:
                # Fallback: estimate from annual cash flow statement
                total_dividends = self.get_df_value(self.cash_flow, "Cash Dividends Paid", 0) or \
                                self.get_df_value(self.cash_flow, "Dividends Paid", 0)
                if total_dividends and self.shares_out:
                    dps = abs(total_dividends) / self.shares_out

            if not dps or dps <= 0:
                logger.info(f"No dividend data available for {self.ticker}")
                return {
                    'implied_growth': 0.0,
                    'error': 'No dividend data'
                }

            # Guard against zero price
            if not self.current_price:
                logger.error(f"Cannot calculate DDM implied growth: current_price is 0")
                return {'implied_growth': 0.0, 'error': 'current_price is zero'}

            # Required return (use CAPM with config constants)
            beta = self.company_info.get('beta') or self.key_metrics.get('beta', 1.0)
            risk_free_rate = config.DDM_RISK_FREE_RATE
            market_return = config.DDM_MARKET_RETURN
            required_return = risk_free_rate + beta * (market_return - risk_free_rate)

            # Solve for g: g = r - (D / P)
            implied_growth = required_return - (dps / self.current_price)

            # Sanity check - cap at reasonable levels using config constants
            if implied_growth >= required_return * config.DDM_MAX_GROWTH_RATIO:
                implied_growth = required_return * config.DDM_MAX_GROWTH_RATIO
                logger.info(f"DDM implied growth capped at {config.DDM_MAX_GROWTH_RATIO:.0%} of required return")

            if implied_growth < config.DDM_MIN_IMPLIED_GROWTH:
                implied_growth = config.DDM_MIN_IMPLIED_GROWTH
                logger.info(f"DDM implied growth floored at {config.DDM_MIN_IMPLIED_GROWTH:.0%}")
            
            # Interpret
            if implied_growth > 0.10:
                interpretation = "HIGH dividend growth expectations"
            elif implied_growth > 0.05:
                interpretation = "MODERATE dividend growth expectations"
            elif implied_growth > 0:
                interpretation = "LOW dividend growth expectations"
            else:
                interpretation = "NEGATIVE dividend growth expectations"
            
            logger.info(f"  DDM: DPS=${dps:.2f}, req_return={required_return:.1%}, implied_growth={implied_growth:.2%} ({interpretation})")
            
            return {
                'implied_growth': implied_growth,
                'dps': dps,
                'required_return': required_return,
                'interpretation': interpretation
            }
            
        except Exception as e:
            logger.error(f"Error calculating DDM market-implied: {e}")
            logger.warning(f"  Error: {e}")
            return {
                'implied_growth': 0.0,
                'error': str(e)
            }
    
    
    def calculate_for_revenue_based(self) -> Dict[str, Any]:
        """
        Calculate market-implied EV/Revenue multiple.
        
        This is a direct calculation, not an optimization problem.
        
        Returns:
            dict: {
                'implied_multiple': float,
                'enterprise_value': float,
                'interpretation': str
            }
        """
        try:
            logger.info(f"Calculating market-implied Revenue-Based assumptions for {self.ticker}")
            
            # Get current revenue (TTM)
            revenue = self.get_df_value(self.income_stmt, "Total Revenue", 0) or \
                     self.get_df_value(self.income_stmt, "Operating Revenue", 0)
            
            if not revenue or revenue <= 0:
                logger.info(f"No revenue data available for {self.ticker}")
                return {
                    'implied_multiple': 0.0,
                    'error': 'No revenue data'
                }
            
            # Calculate enterprise value
            total_debt = self.get_df_value(self.balance_sheet, "Total Debt", 0) or \
                        (self.get_df_value(self.balance_sheet, "Long Term Debt", 0) + \
                         self.get_df_value(self.balance_sheet, "Current Debt", 0))
            
            cash = self.get_df_value(self.balance_sheet, "Cash And Cash Equivalents", 0) or \
                  self.get_df_value(self.balance_sheet, "Cash", 0)
            
            enterprise_value = self.market_cap + total_debt - cash
            
            # Calculate implied multiple
            implied_multiple = utils.safe_divide(enterprise_value, revenue, default=0)
            
            # Interpret
            if implied_multiple > 10:
                interpretation = "VERY HIGH multiple - hypergrowth expectations"
            elif implied_multiple > 5:
                interpretation = "HIGH multiple - strong growth expectations"
            elif implied_multiple > 2:
                interpretation = "MODERATE multiple - average expectations"
            elif implied_multiple > 0:
                interpretation = "LOW multiple - mature/stable expectations"
            else:
                interpretation = "NEGATIVE - distressed situation"
            
            logger.info(f"  RevBased: Revenue=${revenue/1e9:.2f}B, EV=${enterprise_value/1e9:.2f}B, implied EV/Rev={implied_multiple:.2f}x ({interpretation})")
            
            return {
                'implied_multiple': implied_multiple,
                'enterprise_value': enterprise_value,
                'revenue': revenue,
                'interpretation': interpretation
            }
            
        except Exception as e:
            logger.error(f"Error calculating Revenue-Based market-implied: {e}")
            logger.warning(f"  Error: {e}")
            return {
                'implied_multiple': 0.0,
                'error': str(e)
            }
    
    
    def calculate_for_comps(self) -> Dict[str, Any]:
        """
        Calculate market-implied quality premium for Comps model.
        
        This compares company's actual multiple to peer average.
        
        Returns:
            dict: {
                'implied_premium': float,
                'interpretation': str
            }
        """
        try:
            logger.info(f"Calculating market-implied Comps assumptions for {self.ticker}")
            
            # For Comps, we use current market multiples directly
            # Scenario 7 uses peer multiples as-is
            # Scenario 8 adds AI-Capex premium on top
            
            # Get company's actual P/E ratio
            net_income = self.get_df_value(self.income_stmt, "Net Income", 0)
            
            if net_income and net_income > 0 and self.shares_out:
                eps = net_income / self.shares_out
                pe_ratio = utils.safe_divide(self.current_price, eps, default=0)
            else:
                pe_ratio = 0
            
            # Industry average P/E from config (cross-sector default; override per sector if needed)
            industry_pe = config.DEFAULT_INDUSTRY_PE
            
            # Calculate premium/discount
            implied_premium = utils.safe_divide(pe_ratio - industry_pe, industry_pe, default=0)
            
            # Interpret
            if implied_premium > 0.50:
                interpretation = "VERY HIGH premium - exceptional quality"
            elif implied_premium > 0.20:
                interpretation = "HIGH premium - above-average quality"
            elif implied_premium > -0.20:
                interpretation = "MODERATE - in-line with peers"
            else:
                interpretation = "DISCOUNT - below-average quality"
            
            logger.info(f"  Comps: Company P/E={pe_ratio:.1f}x, Industry P/E={industry_pe:.1f}x, premium={implied_premium:.1%} ({interpretation})")
            
            return {
                'implied_premium': implied_premium,
                'company_pe': pe_ratio,
                'industry_pe': industry_pe,
                'interpretation': interpretation
            }
            
        except Exception as e:
            logger.error(f"Error calculating Comps market-implied: {e}")
            logger.warning(f"  Error: {e}")
            return {
                'implied_premium': 0.0,
                'error': str(e)
            }
    
    
    def calculate_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate market-implied assumptions for all 4 models.
        
        Returns:
            dict: {
                'dcf': {...},
                'ddm': {...},
                'revenue_based': {...},
                'comps': {...}
            }
        """
        return {
            'dcf': self.calculate_for_dcf(),
            'ddm': self.calculate_for_ddm(),
            'revenue_based': self.calculate_for_revenue_based(),
            'comps': self.calculate_for_comps()
        }


# ============================================================================
# MODULE METADATA
# ============================================================================

__version__ = '2.6'
__all__ = ['MarketImpliedCalculator']