"""XBRL service — extracts structured financial data from SEC XBRL company facts.

Translates raw XBRL concept data into normalized financial_data rows.
Uses concept aliases to handle variation across filers (different companies
use different XBRL tags for the same metric).

All HTTP calls go through SECEdgarProvider (which handles rate-limiting).
"""

import logging
from datetime import datetime, timezone

from db.connection import DatabaseConnection
from providers.sec_edgar import SECEdgarProvider
from repositories.market_data_repo import MarketDataRepo

logger = logging.getLogger("finance_app")

# ---------------------------------------------------------------------------
# XBRL Concept Aliases
# ---------------------------------------------------------------------------
# For each metric, try concepts in order until one is found.
# Covers us-gaap and dei namespaces.

CONCEPT_ALIASES: dict[str, list[str]] = {
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
    "tax_provision": [
        "IncomeTaxExpenseBenefit",
        "IncomeTaxesPaid",
    ],
    "sga_expense": [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
    ],
    "current_assets": [
        "AssetsCurrent",
    ],
    "current_liabilities": [
        "LiabilitiesCurrent",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _extract_metric(
    us_gaap: dict, dei: dict, concepts: list[str], fiscal_year: int | None = None
) -> float | None:
    """Try each concept alias for a metric, return the best-matching value.

    Filters to annual 10-K data only.
    """
    best_value = None
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
                annual = [
                    v for v in vals
                    if v.get("form") == "10-K" and v.get("fp") == "FY"
                ]

                if not annual:
                    continue

                if fiscal_year is not None:
                    matches = [v for v in annual if v.get("fy") == fiscal_year]
                    if matches:
                        return matches[-1].get("val")
                else:
                    entry = annual[-1]
                    entry_fy = entry.get("fy", 0)
                    if isinstance(entry_fy, (int, float)) and entry_fy > best_fy:
                        best_fy = entry_fy
                        best_value = entry.get("val")

    return best_value


def _get_available_fiscal_years(us_gaap: dict) -> list[int]:
    """Get list of available fiscal years from revenue data."""
    all_years: set[int] = set()
    for concept in CONCEPT_ALIASES["revenue"]:
        if concept not in us_gaap:
            continue
        units = us_gaap[concept].get("units", {})
        if "USD" in units:
            vals = units["USD"]
            annual = [
                v for v in vals
                if v.get("form") == "10-K" and v.get("fp") == "FY"
            ]
            for v in annual:
                fy = v.get("fy")
                if fy:
                    all_years.add(fy)
    return sorted(all_years, reverse=True)


def _extract_year(
    us_gaap: dict, dei: dict, fiscal_year: int
) -> dict[str, float | None]:
    """Extract all metrics for a single fiscal year."""
    raw: dict[str, float | None] = {}
    for metric, concepts in CONCEPT_ALIASES.items():
        raw[metric] = _extract_metric(us_gaap, dei, concepts, fiscal_year)
    return raw


def _build_financial_row(
    ticker: str, fiscal_year: int, raw: dict[str, float | None]
) -> dict:
    """Map raw XBRL-extracted metrics to a financial_data table row."""
    ocf = raw.get("operating_cash_flow")
    capex = raw.get("capex")
    fcf = (ocf - capex) if (ocf is not None and capex is not None) else None

    ebit = raw.get("operating_income")
    dep = raw.get("depreciation")
    ebitda = (ebit + dep) if (ebit is not None and dep is not None) else None

    revenue = raw.get("revenue")
    net_income = raw.get("net_income")
    equity = raw.get("stockholders_equity")
    total_debt = raw.get("total_debt")
    cash = raw.get("cash")
    dividends = raw.get("dividends_paid")
    current_assets = raw.get("current_assets")
    current_liabilities = raw.get("current_liabilities")

    working_capital = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    net_debt = None
    if total_debt is not None and cash is not None:
        net_debt = total_debt - cash

    return {
        "ticker": ticker.upper(),
        "fiscal_year": fiscal_year,
        "period_type": "annual",
        "revenue": revenue,
        "cost_of_revenue": raw.get("cost_of_revenue"),
        "gross_profit": raw.get("gross_profit"),
        "rd_expense": raw.get("research_development"),
        "sga_expense": raw.get("sga_expense"),
        "ebit": ebit,
        "interest_expense": raw.get("interest_expense"),
        "tax_provision": raw.get("tax_provision"),
        "net_income": net_income,
        "ebitda": ebitda,
        "depreciation_amortization": dep,
        "eps_basic": raw.get("eps_basic"),
        "eps_diluted": raw.get("eps_diluted"),
        "total_assets": raw.get("total_assets"),
        "current_assets": current_assets,
        "cash_and_equivalents": cash,
        "total_liabilities": raw.get("total_liabilities"),
        "current_liabilities": current_liabilities,
        "long_term_debt": raw.get("long_term_debt"),
        "total_debt": total_debt,
        "stockholders_equity": equity,
        "working_capital": working_capital,
        "net_debt": net_debt,
        "operating_cash_flow": ocf,
        "capital_expenditure": capex,
        "free_cash_flow": fcf,
        "dividends_paid": dividends,
        "shares_outstanding": raw.get("shares_outstanding"),
        # Derived ratios
        "gross_margin": _safe_div(raw.get("gross_profit"), revenue),
        "operating_margin": _safe_div(ebit, revenue),
        "net_margin": _safe_div(net_income, revenue),
        "ebitda_margin": _safe_div(ebitda, revenue),
        "fcf_margin": _safe_div(fcf, revenue),
        "roe": _safe_div(net_income, equity),
        "debt_to_equity": _safe_div(total_debt, equity),
        "payout_ratio": _safe_div(dividends, net_income) if dividends and net_income else None,
        "data_source": "sec_edgar",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class XBRLService:
    """Extracts normalized financial data from SEC XBRL company facts.

    Uses SECEdgarProvider for API access and MarketDataRepo for persistence.
    """

    def __init__(self, db: DatabaseConnection, sec_provider: SECEdgarProvider):
        self.sec = sec_provider
        self.market_repo = MarketDataRepo(db)

    # ------------------------------------------------------------------
    # Core: parse XBRL company facts JSON
    # ------------------------------------------------------------------

    @staticmethod
    def parse_company_facts(
        facts_json: dict, ticker: str, years: int = 10
    ) -> list[dict]:
        """Parse XBRL company facts JSON into a list of financial_data rows.

        Args:
            facts_json: Raw JSON from SEC /api/xbrl/companyfacts/ endpoint.
            ticker: Stock ticker (for labeling rows).
            years: Max number of fiscal years to extract.

        Returns:
            List of financial_data dicts sorted by fiscal_year DESC.
        """
        us_gaap = facts_json.get("facts", {}).get("us-gaap", {})
        dei = facts_json.get("facts", {}).get("dei", {})

        if not us_gaap:
            logger.warning("%s: No us-gaap data in XBRL company facts", ticker)
            return []

        fy_list = _get_available_fiscal_years(us_gaap)[:years]

        rows: list[dict] = []
        for fy in fy_list:
            raw = _extract_year(us_gaap, dei, fy)
            row = _build_financial_row(ticker, fy, raw)
            rows.append(row)

        # Compute revenue_growth (YoY) where possible
        for i in range(len(rows) - 1):
            curr_rev = rows[i].get("revenue")
            prev_rev = rows[i + 1].get("revenue")
            if curr_rev is not None and prev_rev is not None and prev_rev != 0:
                rows[i]["revenue_growth"] = (curr_rev - prev_rev) / abs(prev_rev)

        logger.info(
            "Parsed %d fiscal years of XBRL data for %s (FY %s–%s)",
            len(rows),
            ticker,
            rows[-1]["fiscal_year"] if rows else "?",
            rows[0]["fiscal_year"] if rows else "?",
        )
        return rows

    # ------------------------------------------------------------------
    # Fetch + parse (convenience)
    # ------------------------------------------------------------------

    async def get_financials_from_xbrl(
        self, ticker: str, years: int = 10
    ) -> list[dict]:
        """Fetch XBRL company facts from SEC and parse into financial rows.

        Args:
            ticker: Stock ticker.
            years: Max number of fiscal years to extract.

        Returns:
            List of financial_data dicts, newest first.
        """
        facts = await self.sec.get_company_facts(ticker)
        if not facts:
            logger.warning("No XBRL company facts for %s", ticker)
            return []

        return self.parse_company_facts(facts, ticker, years)

    # ------------------------------------------------------------------
    # Persist to DB
    # ------------------------------------------------------------------

    async def store_financials(self, ticker: str, rows: list[dict]) -> int:
        """Store parsed XBRL financial rows into financial_data table.

        Uses upsert — existing rows are updated, new rows inserted.
        Returns number of rows stored.
        """
        count = 0
        for row in rows:
            try:
                await self.market_repo.upsert_financial(row)
                count += 1
            except Exception as exc:
                logger.warning(
                    "Failed to store XBRL financial row for %s FY%s: %s",
                    ticker, row.get("fiscal_year"), exc,
                )
        logger.info("Stored %d XBRL financial rows for %s", count, ticker)
        return count

    # ------------------------------------------------------------------
    # Full pipeline: fetch → parse → store
    # ------------------------------------------------------------------

    async def fetch_and_store(self, ticker: str, years: int = 10) -> list[dict]:
        """Fetch XBRL data, parse, store to DB, and return the rows.

        This is the main entry point for populating financial_data from SEC.
        """
        rows = await self.get_financials_from_xbrl(ticker, years)
        if rows:
            await self.store_financials(ticker, rows)
        return rows
