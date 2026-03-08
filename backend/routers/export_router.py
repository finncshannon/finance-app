"""Export router — generates Excel/PDF/CSV files and returns as download responses."""

from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import Response

from models.response import error_response

router = APIRouter(prefix="/api/v1/export", tags=["export"])


def _file_response(content: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME = "application/pdf"
CSV_MIME = "text/csv"


@router.post("/model/{model_id}/excel")
async def export_model_excel(model_id: int, request: Request):
    """Generate and return model Excel workbook."""
    try:
        model_repo = request.app.state.model_repo
        model = await model_repo.get_model(model_id)
        if not model:
            return error_response("NOT_FOUND", f"Model {model_id} not found")

        ticker = model.get("ticker", "UNKNOWN")
        model_type = model.get("model_type", "dcf")

        # Get assumptions
        assumption_engine = request.app.state.assumption_engine
        assumptions_obj = await assumption_engine.generate_assumptions(ticker, model_type=model_type)
        assumptions = assumptions_obj.model_dump(mode="json") if hasattr(assumptions_obj, 'model_dump') else assumptions_obj

        # Get latest engine output
        outputs = await model_repo.get_outputs_for_model(model_id)
        engine_result = {}
        if outputs:
            import json
            latest = outputs[0]  # newest first
            scenarios_json = latest.get("scenarios_json", "{}")
            engine_result = json.loads(scenarios_json) if isinstance(scenarios_json, str) else scenarios_json

        # Get historical financials
        db = request.app.state.db
        rows = await db.fetchall(
            "SELECT * FROM cache.financial_data WHERE ticker = ? AND period_type = 'annual' ORDER BY fiscal_year ASC",
            (ticker,),
        )
        historical = [dict(r) for r in rows] if rows else []

        # Get current price
        mds = request.app.state.market_data_service
        quote = await mds.get_quote(ticker)
        current_price = quote.get("current_price", 0) if quote else 0

        svc = request.app.state.model_excel_service
        file_bytes = await svc.generate(ticker, model_type, assumptions, engine_result, historical, current_price)

        date = datetime.now().strftime("%Y-%m-%d")
        return _file_response(file_bytes, f"{ticker}_{model_type}_{date}.xlsx", XLSX_MIME)
    except Exception as e:
        return error_response("EXPORT_ERROR", str(e))


@router.post("/model/{model_id}/pdf")
async def export_model_pdf(model_id: int, request: Request):
    """Generate and return model PDF report."""
    try:
        model_repo = request.app.state.model_repo
        model = await model_repo.get_model(model_id)
        if not model:
            return error_response("NOT_FOUND", f"Model {model_id} not found")

        ticker = model.get("ticker", "UNKNOWN")
        model_type = model.get("model_type", "dcf")

        assumption_engine = request.app.state.assumption_engine
        assumptions_obj = await assumption_engine.generate_assumptions(ticker, model_type=model_type)
        assumptions = assumptions_obj.model_dump(mode="json") if hasattr(assumptions_obj, 'model_dump') else assumptions_obj

        outputs = await model_repo.get_outputs_for_model(model_id)
        engine_result = {}
        if outputs:
            import json
            latest = outputs[0]  # newest first
            scenarios_json = latest.get("scenarios_json", "{}")
            engine_result = json.loads(scenarios_json) if isinstance(scenarios_json, str) else scenarios_json

        mds = request.app.state.market_data_service
        quote = await mds.get_quote(ticker)
        current_price = quote.get("current_price", 0) if quote else 0

        svc = request.app.state.model_pdf_service
        file_bytes = await svc.generate(ticker, model_type, assumptions, engine_result, current_price)

        date = datetime.now().strftime("%Y-%m-%d")
        return _file_response(file_bytes, f"{ticker}_{model_type}_{date}.pdf", PDF_MIME)
    except Exception as e:
        return error_response("EXPORT_ERROR", str(e))


@router.post("/scanner/excel")
async def export_scanner_excel(request: Request):
    """Export scanner results to Excel."""
    try:
        body = await request.json()
        results = body.get("results", [])
        config = body.get("config", None)

        svc = request.app.state.scanner_export_service
        file_bytes = await svc.generate_excel(results, config)

        date = datetime.now().strftime("%Y-%m-%d")
        return _file_response(file_bytes, f"scanner_results_{date}.xlsx", XLSX_MIME)
    except Exception as e:
        return error_response("EXPORT_ERROR", str(e))


@router.post("/scanner/csv")
async def export_scanner_csv(request: Request):
    """Export scanner results to CSV."""
    try:
        body = await request.json()
        results = body.get("results", [])

        svc = request.app.state.scanner_export_service
        file_bytes = await svc.generate_csv(results)

        date = datetime.now().strftime("%Y-%m-%d")
        return _file_response(file_bytes, f"scanner_results_{date}.csv", CSV_MIME)
    except Exception as e:
        return error_response("EXPORT_ERROR", str(e))


@router.post("/portfolio/excel")
async def export_portfolio_excel(request: Request):
    """Export portfolio to Excel."""
    try:
        body = await request.json()
        holdings = body.get("holdings", [])
        transactions = body.get("transactions", [])
        summary = body.get("summary", {})

        svc = request.app.state.portfolio_export_service
        file_bytes = await svc.generate_excel(
            holdings=holdings, transactions=transactions, summary=summary,
        )

        date = datetime.now().strftime("%Y-%m-%d")
        return _file_response(file_bytes, f"portfolio_{date}.xlsx", XLSX_MIME)
    except Exception as e:
        return error_response("EXPORT_ERROR", str(e))


@router.post("/portfolio/pdf")
async def export_portfolio_pdf(request: Request):
    """Export portfolio to PDF."""
    try:
        body = await request.json()
        holdings = body.get("holdings", [])
        summary = body.get("summary", {})

        svc = request.app.state.portfolio_export_service
        file_bytes = await svc.generate_pdf(holdings=holdings, summary=summary)

        date = datetime.now().strftime("%Y-%m-%d")
        return _file_response(file_bytes, f"portfolio_summary_{date}.pdf", PDF_MIME)
    except Exception as e:
        return error_response("EXPORT_ERROR", str(e))


@router.post("/research/{ticker}/excel")
async def export_research_excel(ticker: str, request: Request):
    """Export financial statements to Excel."""
    try:
        db = request.app.state.db
        rows = await db.fetchall(
            "SELECT * FROM cache.financial_data WHERE ticker = ? AND period_type = 'annual' ORDER BY fiscal_year DESC",
            (ticker,),
        )
        financials = [dict(r) for r in rows] if rows else []

        # Get ratios
        ratios = None
        try:
            data_ext = request.app.state.data_extraction_service
            ratios = await data_ext.compute_all_metrics(ticker)
        except Exception:
            pass

        svc = request.app.state.research_export_service
        file_bytes = await svc.generate_excel(ticker, financials=financials, ratios=ratios)

        date = datetime.now().strftime("%Y-%m-%d")
        return _file_response(file_bytes, f"{ticker}_financials_{date}.xlsx", XLSX_MIME)
    except Exception as e:
        return error_response("EXPORT_ERROR", str(e))
