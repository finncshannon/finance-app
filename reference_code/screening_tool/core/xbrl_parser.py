"""
XBRL Parser -- extracts structured financial data from SEC company facts.

Uses the SEC XBRL Company Facts API to get standardized financials.
Handles concept name variations across companies (different companies
use different XBRL tags for the same metric).

Usage:
    from core.sec_client import SECClient
    from core.xbrl_parser import XBRLParser

    client = SECClient(contact_email="you@email.com")
    parser = XBRLParser(client)

    financials = parser.get_financials("AAPL", cik="0000320193")
    print(financials["revenue"])        # Most recent annual revenue
    print(financials["net_income"])     # Most recent net income
    print(financials["fcf"])           # Free cash flow
"""

import logging
from typing import Dict, Optional, Any, List

from core.sec_client import SECClient

logger = logging.getLogger(__name__)


# XBRL concept aliases — companies use different tags for the same metric.
# For each metric, try concepts in order until one is found.
CONCEPT_ALIASES = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "cost_of_revenue": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "operating_income": [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    ],
    "net_income": [
        "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "ProfitLoss",
    ],
    "eps_basic": [
        "EarningsPerShareBasic",
    ],
    "eps_diluted": [
        "EarningsPerShareDiluted",
    ],
    "total_assets": [
        "Assets",
    ],
    "total_liabilities": [
        "Liabilities",
        "LiabilitiesAndStockholdersEquity",
    ],
    "stockholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
        "Cash",
    ],
    "total_debt": [
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebt",
        "DebtCurrent",
    ],
    "long_term_debt": [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
    ],
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
        "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ],
    "dividends_paid": [
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
        "PaymentsOfOrdinaryDividends",
        "DividendsCommonStockCash",
    ],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByOperatingActivities",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "CapitalExpendituresIncurredButNotYetPaid",
    ],
    "depreciation": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ],
    "research_development": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseDebt",
    ],
}


class XBRLParser:
    """
    Extracts normalized financial data from SEC XBRL company facts.
    """

    def __init__(self, client: SECClient):
        self.client = client

    def get_financials(self, ticker: str, cik: str,
                        fiscal_year: str = None) -> Dict[str, Any]:
        """
        Get normalized financial data for a company.

        Args:
            ticker: Stock ticker
            cik: 10-digit CIK (zero-padded)
            fiscal_year: Specific fiscal year (e.g., "2024"). None = latest.

        Returns:
            Dict with normalized financial metrics:
                - revenue, cost_of_revenue, gross_profit, operating_income
                - net_income, eps_basic, eps_diluted
                - total_assets, total_liabilities, stockholders_equity
                - cash, total_debt, long_term_debt
                - shares_outstanding, dividends_paid
                - operating_cash_flow, capex, fcf (computed)
                - depreciation, research_development, interest_expense
                - fiscal_year, fiscal_period_end
                - _raw: dict of raw concept values for debugging
        """
        cik = cik.zfill(10)
        facts = self.client.get_company_facts(cik)

        if not facts:
            logger.warning(f"{ticker}: No XBRL company facts available")
            return self._empty_financials(ticker)

        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        dei = facts.get("facts", {}).get("dei", {})

        if not us_gaap:
            logger.warning(f"{ticker}: No us-gaap data in company facts")
            return self._empty_financials(ticker)

        # Extract each metric using concept aliases
        result = {"ticker": ticker, "_raw": {}}

        for metric, concepts in CONCEPT_ALIASES.items():
            value, raw_info = self._extract_metric(
                us_gaap, dei, concepts, fiscal_year
            )
            result[metric] = value
            if raw_info:
                result["_raw"][metric] = raw_info

        # Compute derived metrics
        result["fcf"] = self._compute_fcf(result)
        result["gross_margin"] = self._safe_divide(
            result.get("gross_profit"), result.get("revenue")
        )
        result["operating_margin"] = self._safe_divide(
            result.get("operating_income"), result.get("revenue")
        )
        result["net_margin"] = self._safe_divide(
            result.get("net_income"), result.get("revenue")
        )

        # Fiscal year info
        raw_any = next(iter(result["_raw"].values()), {})
        result["fiscal_year"] = raw_any.get("fy", "")
        result["fiscal_period_end"] = raw_any.get("end", "")

        return result

    def get_multi_year_financials(self, ticker: str, cik: str,
                                   years: int = 3) -> List[Dict]:
        """
        Get financial data for multiple fiscal years.

        Args:
            ticker: Stock ticker
            cik: 10-digit CIK
            years: Number of years to retrieve

        Returns:
            List of financial dicts, most recent first.
        """
        cik = cik.zfill(10)
        facts = self.client.get_company_facts(cik)

        if not facts:
            return []

        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        dei = facts.get("facts", {}).get("dei", {})

        if not us_gaap:
            return []

        # Find available fiscal years from revenue data
        fy_list = self._get_available_fiscal_years(us_gaap)
        fy_list = sorted(fy_list, reverse=True)[:years]

        results = []
        for fy in fy_list:
            fin = {"ticker": ticker, "_raw": {}}
            for metric, concepts in CONCEPT_ALIASES.items():
                value, raw_info = self._extract_metric(
                    us_gaap, dei, concepts, str(fy)
                )
                fin[metric] = value
                if raw_info:
                    fin["_raw"][metric] = raw_info

            fin["fcf"] = self._compute_fcf(fin)
            fin["gross_margin"] = self._safe_divide(
                fin.get("gross_profit"), fin.get("revenue")
            )
            fin["operating_margin"] = self._safe_divide(
                fin.get("operating_income"), fin.get("revenue")
            )
            fin["net_margin"] = self._safe_divide(
                fin.get("net_income"), fin.get("revenue")
            )
            fin["fiscal_year"] = fy
            results.append(fin)

        return results

    # ----------------------------------------------------------------
    # Internal: metric extraction
    # ----------------------------------------------------------------

    def _extract_metric(self, us_gaap: Dict, dei: Dict,
                         concepts: List[str],
                         fiscal_year: str = None) -> tuple:
        """
        Try each concept alias, pick the one with the most recent data.

        Returns:
            (value, raw_info) where value is the numeric value (or None)
            and raw_info is the full XBRL entry dict for debugging.
        """
        best_value = None
        best_entry = None
        best_fy = 0

        for concept in concepts:
            for source in [us_gaap, dei]:
                if concept not in source:
                    continue

                entries = source[concept]
                units = entries.get("units", {})

                for unit_key in ["USD", "shares", "USD/shares", "pure"]:
                    if unit_key not in units:
                        continue

                    vals = units[unit_key]

                    # Filter to annual 10-K data
                    annual = [v for v in vals
                              if v.get("form") == "10-K" and v.get("fp") == "FY"]

                    if not annual:
                        continue

                    if fiscal_year:
                        matches = [v for v in annual if str(v.get("fy")) == str(fiscal_year)]
                        if matches:
                            entry = matches[-1]
                            return entry.get("val"), entry
                    else:
                        # Pick concept with the most recent fiscal year
                        entry = annual[-1]
                        entry_fy = entry.get("fy", 0)
                        if isinstance(entry_fy, (int, float)) and entry_fy > best_fy:
                            best_fy = entry_fy
                            best_value = entry.get("val")
                            best_entry = entry

        if best_value is not None:
            return best_value, best_entry
        return None, None

    def _get_available_fiscal_years(self, us_gaap: Dict) -> List[int]:
        """Get list of available fiscal years from revenue data."""
        all_years = set()
        # Check ALL revenue concepts and merge their years
        for concept in CONCEPT_ALIASES["revenue"]:
            if concept not in us_gaap:
                continue
            units = us_gaap[concept].get("units", {})
            if "USD" in units:
                vals = units["USD"]
                annual = [v for v in vals
                          if v.get("form") == "10-K" and v.get("fp") == "FY"]
                for v in annual:
                    fy = v.get("fy")
                    if fy:
                        all_years.add(fy)
        return list(all_years)

    # ----------------------------------------------------------------
    # Derived metrics
    # ----------------------------------------------------------------

    def _compute_fcf(self, financials: Dict) -> Optional[float]:
        """Compute Free Cash Flow = Operating Cash Flow - CapEx."""
        ocf = financials.get("operating_cash_flow")
        capex = financials.get("capex")

        if ocf is not None and capex is not None:
            # CapEx is reported as positive in XBRL (payments)
            return ocf - capex
        return None

    def _safe_divide(self, numerator, denominator) -> Optional[float]:
        """Safe division returning None if inputs are invalid."""
        if numerator is not None and denominator is not None and denominator != 0:
            return numerator / denominator
        return None

    def _empty_financials(self, ticker: str) -> Dict:
        """Return an empty financials dict with all keys set to None."""
        result = {"ticker": ticker, "_raw": {}}
        for metric in CONCEPT_ALIASES:
            result[metric] = None
        result["fcf"] = None
        result["gross_margin"] = None
        result["operating_margin"] = None
        result["net_margin"] = None
        result["fiscal_year"] = ""
        result["fiscal_period_end"] = ""
        return result

    def format_currency(self, value, compact: bool = True) -> str:
        """Format a currency value for display."""
        if value is None:
            return "N/A"

        if compact:
            abs_val = abs(value)
            sign = "-" if value < 0 else ""
            if abs_val >= 1e12:
                return f"{sign}${abs_val / 1e12:.1f}T"
            elif abs_val >= 1e9:
                return f"{sign}${abs_val / 1e9:.1f}B"
            elif abs_val >= 1e6:
                return f"{sign}${abs_val / 1e6:.1f}M"
            elif abs_val >= 1e3:
                return f"{sign}${abs_val / 1e3:.1f}K"
            else:
                return f"{sign}${abs_val:,.0f}"
        else:
            return f"${value:,.0f}"
