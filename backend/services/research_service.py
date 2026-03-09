"""Research service — orchestrates company data, filings, financials, ratios, and notes."""

from __future__ import annotations

import logging

from db.connection import DatabaseConnection
from services.company_service import CompanyService
from services.data_extraction_service import DataExtractionService
from services.market_data_service import MarketDataService
from services.company_events_service import CompanyEventsService
from repositories.filing_repo import FilingRepo
from repositories.research_repo import ResearchRepo

logger = logging.getLogger("finance_app")

RATIO_GROUPS = {
    "profitability": [
        "gross_margin", "operating_margin", "net_margin",
        "ebitda_margin", "fcf_margin",
    ],
    "returns": ["roe", "roa", "roic"],
    "leverage": [
        "debt_to_equity", "net_debt_to_ebitda",
        "interest_coverage", "debt_to_assets",
    ],
    "liquidity": [],
    "valuation": [
        "pe_ratio", "pe_forward", "price_to_book", "price_to_sales",
        "ev_to_ebitda", "ev_to_revenue", "fcf_yield",
        "earnings_yield", "dividend_yield",
    ],
    "efficiency": ["asset_turnover"],
}


class ResearchService:

    def __init__(
        self,
        db: DatabaseConnection,
        company_svc: CompanyService,
        data_extraction_svc: DataExtractionService,
        market_data_svc: MarketDataService,
        events_svc: CompanyEventsService,
        filing_repo: FilingRepo,
        research_repo: ResearchRepo,
    ):
        self.db = db
        self.company_svc = company_svc
        self.extraction = data_extraction_svc
        self.mds = market_data_svc
        self.events_svc = events_svc
        self.filing_repo = filing_repo
        self.research_repo = research_repo

    async def get_profile(self, ticker: str) -> dict:
        ticker = ticker.upper()
        result = await self.company_svc.get_company_with_metrics(ticker)

        try:
            events = await self.events_svc.get_events_for_ticker(ticker)
            result["upcoming_events"] = [
                {
                    "event_type": e.get("event_type", ""),
                    "event_date": e.get("event_date", ""),
                    "description": e.get("description", ""),
                }
                for e in events
            ]
        except Exception:
            result["upcoming_events"] = []

        return result

    async def get_filings(
        self,
        ticker: str,
        form_types: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        ticker = ticker.upper()
        filings = await self.filing_repo.get_filings_by_ticker(ticker, form_types, limit)
        return [
            {
                "id": f["id"],
                "ticker": f.get("ticker", ticker),
                "form_type": f.get("form_type", ""),
                "filing_date": f.get("filing_date", ""),
                "accession_number": f.get("accession_number"),
                "doc_url": f.get("file_path"),
            }
            for f in filings
        ]

    async def fetch_filings(self, ticker: str) -> dict:
        """Fetch and cache filings from SEC EDGAR for a given ticker."""
        ticker = ticker.upper()

        try:
            filings_data = await self.company_svc.sec.get_filing_index(
                ticker, form_types=["10-K", "10-Q", "8-K"], limit=20,
            )
            count = 0
            for filing in filings_data:
                await self.filing_repo.upsert_filing({
                    "ticker": ticker,
                    "form_type": filing.form_type,
                    "filing_date": filing.filing_date,
                    "accession_number": filing.accession_number,
                    "cik": filing.cik,
                    "file_path": filing.primary_doc_url,
                })
                count += 1
            logger.info("Fetched %d filings for %s from SEC EDGAR", count, ticker)
            return {"ticker": ticker, "filings_count": count}
        except Exception as exc:
            logger.warning("Failed to fetch filings for %s: %s", ticker, exc)
            return {"ticker": ticker, "filings_count": 0, "message": str(exc)}

    async def get_filing_sections(self, filing_id: int) -> list[dict]:
        sections = await self.filing_repo.get_filing_sections(filing_id)

        # On-demand: if no sections cached, download and parse the filing
        if not sections:
            filing = await self.filing_repo.get_filing_by_id(filing_id)
            if filing:
                ticker = filing.get("ticker", "")
                form_type = filing.get("form_type", "")
                doc_url = filing.get("file_path", "")
                accession = filing.get("accession_number", "")

                html = None
                if doc_url:
                    html = await self.company_svc.sec.download_filing_by_url(doc_url)
                elif accession and ticker:
                    html = await self.company_svc.sec.download_filing(ticker, accession)

                if html:
                    if form_type in ("10-K", "10-Q"):
                        from providers.sec_edgar import SECEdgarProvider
                        parsed = SECEdgarProvider.parse_10k_sections(html)
                    else:
                        # For 8-K and other forms, store the full text as one section
                        import re
                        text = re.sub(r'<[^>]+>', ' ', html)
                        text = re.sub(r'\s+', ' ', text).strip()
                        if len(text) > 200_000:
                            text = text[:200_000] + "\n[Content truncated]"
                        parsed = {"full_text": {"title": f"{form_type} Filing", "content": text}}

                    if parsed:
                        await self.filing_repo.upsert_sections(filing_id, parsed)
                        sections = await self.filing_repo.get_filing_sections(filing_id)
                        logger.info("Parsed %d sections for filing %d (%s %s)",
                                    len(sections), filing_id, ticker, form_type)

        return [
            {
                "id": s["id"],
                "filing_id": s.get("filing_id", filing_id),
                "section_key": s.get("section_key", ""),
                "section_title": s.get("section_title", ""),
                "content_text": s.get("content_text", ""),
                "word_count": s.get("word_count"),
            }
            for s in sections
        ]

    async def get_financials(
        self,
        ticker: str,
        period_type: str = "annual",
        limit: int = 10,
    ) -> list[dict]:
        ticker = ticker.upper()
        rows = await self.db.fetchall(
            """SELECT * FROM cache.financial_data
               WHERE ticker = ? AND period_type = ?
               ORDER BY fiscal_year DESC
               LIMIT ?""",
            (ticker, period_type, limit),
        )
        return [dict(r) for r in rows]

    async def get_ratios(self, ticker: str) -> dict:
        ticker = ticker.upper()
        all_metrics = await self.extraction.compute_all_metrics(ticker)

        grouped: dict[str, dict] = {}
        for group_name, metric_keys in RATIO_GROUPS.items():
            grouped[group_name] = {}
            for key in metric_keys:
                grouped[group_name][key] = all_metrics.get(key)

        # Add growth metrics to a growth group
        growth_keys = [
            "revenue_growth_yoy", "net_income_growth_yoy",
            "eps_growth_yoy", "ebitda_growth_yoy", "fcf_growth_yoy",
            "revenue_cagr_3y", "revenue_cagr_5y",
            "eps_cagr_3y", "eps_cagr_5y",
        ]
        grouped["growth"] = {k: all_metrics.get(k) for k in growth_keys}

        return grouped

    async def get_ratio_history(
        self,
        ticker: str,
        metrics: list[str],
        years: int = 10,
    ) -> dict:
        ticker = ticker.upper()
        result: dict[str, list[dict]] = {}
        for metric in metrics:
            try:
                history = await self.extraction.get_metric_history(ticker, metric, years)
                result[metric] = history
            except Exception:
                result[metric] = []
        return result

    async def get_peers(self, ticker: str) -> list[dict]:
        ticker = ticker.upper()
        company = await self.db.fetchone(
            "SELECT sector, industry FROM companies WHERE ticker = ?",
            (ticker,),
        )
        if not company or not company.get("sector"):
            return []

        sector = company["sector"]
        peers = await self.db.fetchall(
            """SELECT ticker, company_name, sector, industry
               FROM companies
               WHERE sector = ? AND ticker != ?
               ORDER BY company_name
               LIMIT 15""",
            (sector, ticker),
        )

        result = []
        for p in peers:
            peer_ticker = p["ticker"]
            quote = await self.mds.get_quote(peer_ticker)
            entry = {
                "ticker": peer_ticker,
                "company_name": p.get("company_name"),
                "sector": p.get("sector"),
                "industry": p.get("industry"),
                "current_price": None,
                "market_cap": None,
                "pe_ratio": None,
                "day_change_pct": None,
            }
            if quote:
                entry["current_price"] = quote.get("current_price")
                entry["market_cap"] = quote.get("market_cap")
                entry["pe_ratio"] = quote.get("pe_trailing")
                entry["day_change_pct"] = quote.get("day_change_pct")
            result.append(entry)
        return result

    async def compare_filings(
        self,
        filing_id_left: int,
        filing_id_right: int,
        section_key: str,
    ) -> dict:
        left_section = await self.filing_repo.get_section(filing_id_left, section_key)
        right_section = await self.filing_repo.get_section(filing_id_right, section_key)
        return {
            "left": {
                "filing_id": filing_id_left,
                "title": left_section.get("section_title", "") if left_section else "",
                "content": left_section.get("content_text", "") if left_section else "",
            },
            "right": {
                "filing_id": filing_id_right,
                "title": right_section.get("section_title", "") if right_section else "",
                "content": right_section.get("content_text", "") if right_section else "",
            },
        }

    async def get_notes(self, ticker: str) -> list[dict]:
        return await self.research_repo.get_notes_for_ticker(ticker.upper())

    async def create_note(
        self, ticker: str, note_text: str, note_type: str = "general",
    ) -> dict:
        return await self.research_repo.create_note({
            "ticker": ticker.upper(),
            "note_text": note_text,
            "note_type": note_type,
        })

    async def update_note(self, note_id: int, data: dict) -> dict | None:
        return await self.research_repo.update_note(note_id, data)

    async def delete_note(self, note_id: int) -> bool:
        return await self.research_repo.delete_note(note_id)
