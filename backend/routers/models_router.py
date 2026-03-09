import json
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from models.response import success_response, error_response
from engines import DCFEngine, DDMEngine, CompsEngine, RevBasedEngine
from repositories.market_data_repo import MarketDataRepo
from repositories.company_repo import CompanyRepo
from repositories.model_repo import ModelRepo
from services.sensitivity import SensitivityService
from services.model_overview import ModelOverviewService

router = APIRouter(prefix="/api/v1/model-builder", tags=["model-builder"])
logger = logging.getLogger("finance_app")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    model_type: str | None = None
    overrides: dict | None = None
    method: str = "monte_carlo"  # "monte_carlo" or "deterministic"
    trials: int = 100
    seed: int | None = None


class UpdateAssumptionsRequest(BaseModel):
    overrides: dict


class RunRequest(BaseModel):
    overrides: dict | None = None
    peer_tickers: list[str] | None = None  # Comps only


class SliderRequest(BaseModel):
    overrides: dict[str, float]


class TornadoRequest(BaseModel):
    overrides: dict | None = None


class MonteCarloRequest(BaseModel):
    overrides: dict | None = None
    iterations: int | None = None
    seed: int | None = None


class Table2DRequest(BaseModel):
    overrides: dict | None = None
    row_variable: str | None = None
    col_variable: str | None = None
    grid_size: int = 9
    row_min: float | None = None
    row_max: float | None = None
    col_min: float | None = None
    col_max: float | None = None


class OverviewRequest(BaseModel):
    overrides: dict | None = None
    peer_tickers: list[str] | None = None


class SaveVersionRequest(BaseModel):
    annotation: str | None = None


class UpdateModelAssumptionsRequest(BaseModel):
    assumptions: dict


# ---------------------------------------------------------------------------
# Assumption Engine endpoints
# ---------------------------------------------------------------------------


@router.post("/{ticker}/generate")
async def generate_assumptions(ticker: str, body: GenerateRequest, request: Request):
    """Generate a full assumption set for a ticker."""
    engine = request.app.state.assumption_engine
    try:
        if body.method == "deterministic":
            result = await engine.generate_assumptions(
                ticker,
                model_type=body.model_type,
                overrides=body.overrides,
            )
        else:
            result = await engine.generate_assumptions_mc(
                ticker,
                n_trials=body.trials,
                seed=body.seed,
                overrides=body.overrides,
            )
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        return error_response("ENGINE_ERROR", str(exc))


@router.get("/{ticker}/assumptions")
async def get_assumptions(ticker: str, request: Request):
    """Get current assumptions for a ticker (generates if not cached)."""
    engine = request.app.state.assumption_engine
    try:
        result = await engine.generate_assumptions(ticker)
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        return error_response("ENGINE_ERROR", str(exc))


@router.put("/{ticker}/assumptions")
async def update_assumptions_override(
    ticker: str, body: UpdateAssumptionsRequest, request: Request,
):
    """Re-generate assumptions with user overrides applied."""
    engine = request.app.state.assumption_engine
    try:
        result = await engine.generate_assumptions(
            ticker, overrides=body.overrides,
        )
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/assumptions/reset")
async def reset_assumptions(ticker: str, request: Request):
    """Reset overrides — re-generate pure engine assumptions."""
    engine = request.app.state.assumption_engine
    try:
        result = await engine.generate_assumptions(ticker, overrides={})
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        return error_response("ENGINE_ERROR", str(exc))


# ---------------------------------------------------------------------------
# Detection endpoint
# ---------------------------------------------------------------------------


@router.get("/{ticker}/detect")
async def detect_model(ticker: str, request: Request):
    """Run model-type auto-detection for a ticker.

    Analyses financial characteristics and scores DCF, DDM, Comps,
    and Revenue-Based models from 0-100, returning a ranked
    recommendation with confidence level.
    """
    svc = request.app.state.model_detection_service
    result = await svc.detect(ticker)
    return success_response(data=result.model_dump())


# ---------------------------------------------------------------------------
# Data Readiness endpoint
# ---------------------------------------------------------------------------


@router.get("/{ticker}/data-readiness")
async def get_data_readiness(ticker: str, request: Request):
    """Data readiness analysis for all engines."""
    try:
        svc = request.app.state.data_readiness_service
        result = await svc.get_readiness(ticker.upper())
        return success_response(data=result)
    except Exception as exc:
        logger.exception("Data readiness failed for %s", ticker)
        return error_response("DATA_READINESS_ERROR", str(exc))


# ---------------------------------------------------------------------------
# Valuation Engine run endpoints
# ---------------------------------------------------------------------------


async def _gather_engine_data(ticker: str, request: Request) -> tuple[dict, float]:
    """Gather financial data + current price for valuation engines."""
    market_repo = MarketDataRepo(request.app.state.db)
    financials = await market_repo.get_financials(ticker, 10)
    # Financials from repo come newest-first; engines expect oldest-first
    financials.reverse()

    market_data_svc = request.app.state.market_data_service
    quote = await market_data_svc.get_quote(ticker)
    current_price = 0.0
    if quote:
        current_price = (
            quote.get("current_price")
            or quote.get("regularMarketPrice")
            or 0.0
        )

    return {
        "annual_financials": financials,
        "quote_data": quote or {},
    }, current_price


@router.post("/{ticker}/run/dcf")
async def run_dcf(ticker: str, body: RunRequest, request: Request):
    """Run DCF valuation engine."""
    try:
        engine = request.app.state.assumption_engine
        assumptions = await engine.generate_assumptions(
            ticker, model_type="dcf", overrides=body.overrides,
        )
        data, price = await _gather_engine_data(ticker, request)
        result = DCFEngine.run(assumptions, data, price)

        # Auto-persist model record
        model_repo: ModelRepo = request.app.state.model_repo
        model = await model_repo.get_or_create_model(ticker, "dcf")
        result_dict = result.model_dump(mode="json")
        result_dict["model_id"] = model["id"]
        return success_response(data=result_dict)
    except Exception as exc:
        logger.exception("DCF run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/run/ddm")
async def run_ddm(ticker: str, body: RunRequest, request: Request):
    """Run DDM valuation engine."""
    try:
        engine = request.app.state.assumption_engine
        assumptions = await engine.generate_assumptions(
            ticker, model_type="ddm", overrides=body.overrides,
        )
        data, price = await _gather_engine_data(ticker, request)
        result = DDMEngine.run(assumptions, data, price)

        model_repo: ModelRepo = request.app.state.model_repo
        model = await model_repo.get_or_create_model(ticker, "ddm")
        result_dict = result.model_dump(mode="json")
        result_dict["model_id"] = model["id"]
        return success_response(data=result_dict)
    except Exception as exc:
        logger.exception("DDM run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/run/comps")
async def run_comps(ticker: str, body: RunRequest, request: Request):
    """Run Comps valuation engine.

    Pass ``peer_tickers`` in the request body to supply peer companies.
    """
    try:
        engine = request.app.state.assumption_engine
        assumptions = await engine.generate_assumptions(
            ticker, model_type="comps", overrides=body.overrides,
        )
        data, price = await _gather_engine_data(ticker, request)

        # Auto-discover peers if not provided
        peer_tickers = body.peer_tickers
        if not peer_tickers:
            company_svc = request.app.state.company_service
            peer_tickers = await company_svc.find_peers(ticker)
            logger.info("Auto-discovered %d peers for %s", len(peer_tickers), ticker)

        # Gather peer data
        peer_data = None
        if peer_tickers:
            peer_data = await _gather_peer_data(peer_tickers, request)

        result = CompsEngine.run(assumptions, data, price, peer_data)

        model_repo: ModelRepo = request.app.state.model_repo
        model = await model_repo.get_or_create_model(ticker, "comps")
        result_dict = result.model_dump(mode="json")
        result_dict["model_id"] = model["id"]
        return success_response(data=result_dict)
    except Exception as exc:
        logger.exception("Comps run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/run/revbased")
async def run_revbased(ticker: str, body: RunRequest, request: Request):
    """Run Revenue-Based valuation engine."""
    try:
        engine = request.app.state.assumption_engine
        assumptions = await engine.generate_assumptions(
            ticker, model_type="revenue_based", overrides=body.overrides,
        )
        data, price = await _gather_engine_data(ticker, request)
        result = RevBasedEngine.run(assumptions, data, price)

        model_repo: ModelRepo = request.app.state.model_repo
        model = await model_repo.get_or_create_model(ticker, "revenue_based")
        result_dict = result.model_dump(mode="json")
        result_dict["model_id"] = model["id"]
        return success_response(data=result_dict)
    except Exception as exc:
        logger.exception("RevBased run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/run/all")
async def run_all_models(ticker: str, body: RunRequest, request: Request):
    """Run all applicable valuation engines and return combined results."""
    try:
        engine = request.app.state.assumption_engine
        assumptions = await engine.generate_assumptions(
            ticker, overrides=body.overrides,
        )
        data, price = await _gather_engine_data(ticker, request)

        results: dict = {}

        # DCF — always applicable
        dcf_result = DCFEngine.run(assumptions, data, price)
        results["dcf"] = dcf_result.model_dump(mode="json")

        # DDM — only if dividend payer
        ddm_result = DDMEngine.run(assumptions, data, price)
        results["ddm"] = ddm_result.model_dump(mode="json")

        # Comps — auto-discover peers if not provided
        peer_tickers = body.peer_tickers
        if not peer_tickers:
            company_svc = request.app.state.company_service
            peer_tickers = await company_svc.find_peers(ticker)
            logger.info("Auto-discovered %d peers for %s (run_all)", len(peer_tickers), ticker)

        peer_data = None
        if peer_tickers:
            peer_data = await _gather_peer_data(peer_tickers, request)
        comps_result = CompsEngine.run(assumptions, data, price, peer_data)
        results["comps"] = comps_result.model_dump(mode="json")

        # Revenue-Based
        rev_result = RevBasedEngine.run(assumptions, data, price)
        results["revenue_based"] = rev_result.model_dump(mode="json")

        # Auto-persist model records for each engine
        model_repo: ModelRepo = request.app.state.model_repo
        for model_type_key, engine_result_dict in results.items():
            model = await model_repo.get_or_create_model(ticker, model_type_key)
            engine_result_dict["model_id"] = model["id"]

        return success_response(data={
            "ticker": ticker.upper(),
            "current_price": price,
            "models": results,
        })
    except Exception as exc:
        logger.exception("Run-all failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


async def _gather_peer_data(
    peer_tickers: list[str],
    request: Request,
) -> list[dict]:
    """Fetch financial data for peer companies."""
    market_repo = MarketDataRepo(request.app.state.db)
    company_repo = CompanyRepo(request.app.state.db)
    market_data_svc = request.app.state.market_data_service
    peers: list[dict] = []

    for pticker in peer_tickers[:20]:  # Cap at 20 peers
        try:
            financials = await market_repo.get_financials(pticker, 10)
            if not financials:
                continue
            latest = financials[0]  # newest-first from repo

            quote = await market_data_svc.get_quote(pticker) or {}
            price = quote.get("current_price") or quote.get("regularMarketPrice") or 0
            shares = latest.get("shares_outstanding") or 0

            # Get company name from companies table (reliable) instead of quote cache
            company = await company_repo.get_by_ticker(pticker)
            company_name = (company.get("company_name") or "") if company else ""

            market_cap = quote.get("market_cap") or (price * shares)
            enterprise_value = quote.get("enterprise_value") or 0

            peers.append({
                "ticker": pticker.upper(),
                "company_name": company_name,
                "market_cap": market_cap,
                "enterprise_value": enterprise_value,
                "revenue": latest.get("revenue") or 0,
                "ebitda": latest.get("ebitda") or 0,
                "net_income": latest.get("net_income") or 0,
                "free_cash_flow": latest.get("free_cash_flow") or 0,
                "book_value": latest.get("stockholders_equity") or 0,
                "revenue_growth": latest.get("revenue_growth"),
                "operating_margin": latest.get("operating_margin"),
                "roe": latest.get("roe"),
            })
        except Exception as exc:
            logger.warning("Could not gather peer data for %s: %s", pticker, exc)

    return peers


# ---------------------------------------------------------------------------
# Model CRUD + version / output endpoints
# ---------------------------------------------------------------------------

ENGINE_MAP = {
    "dcf": DCFEngine,
    "ddm": DDMEngine,
    "comps": CompsEngine,
    "revenue_based": RevBasedEngine,
}


@router.get("/{ticker}/models")
async def get_models(ticker: str, request: Request):
    """List all saved models for a ticker."""
    repo: ModelRepo = request.app.state.model_repo
    rows = await repo.get_models_for_ticker(ticker)
    return success_response(data=rows)


@router.get("/model/{model_id}")
async def get_model(model_id: int, request: Request):
    """Get a model with its saved assumptions."""
    repo: ModelRepo = request.app.state.model_repo
    model = await repo.get_model(model_id)
    if not model:
        return error_response("NOT_FOUND", f"Model {model_id} not found")
    assumptions = await repo.get_assumptions(model_id, model["model_type"])
    return success_response(data={**model, "assumptions": assumptions})


@router.post("/model/{model_id}/run")
async def run_model(model_id: int, request: Request):
    """Run the valuation engine for a saved model."""
    try:
        repo: ModelRepo = request.app.state.model_repo
        model = await repo.get_model(model_id)
        if not model:
            return error_response("NOT_FOUND", f"Model {model_id} not found")

        ticker = model["ticker"]
        model_type = model["model_type"]
        engine_cls = ENGINE_MAP.get(model_type)
        if not engine_cls:
            return error_response("INVALID_MODEL", f"Unknown model type: {model_type}")

        # Generate assumptions and gather data
        assumption_engine = request.app.state.assumption_engine
        assumptions = await assumption_engine.generate_assumptions(ticker, model_type=model_type)
        data, price = await _gather_engine_data(ticker, request)

        # Run the engine
        if model_type == "comps":
            result = engine_cls.run(assumptions, data, price, None)
        else:
            result = engine_cls.run(assumptions, data, price)

        result_dict = result.model_dump(mode="json")

        # Store output
        existing_outputs = await repo.get_outputs_for_model(model_id)
        run_number = len(existing_outputs) + 1
        await repo.create_output({
            "model_id": model_id,
            "run_number": run_number,
            "intrinsic_value_per_share": result_dict.get("weighted_implied_price")
                or result_dict.get("weighted_intrinsic_value", 0),
            "enterprise_value": result_dict.get("weighted_enterprise_value", 0),
            "equity_value": 0,
            "scenarios_json": json.dumps(result_dict.get("scenarios", {})),
        })

        return success_response(data=result_dict)
    except Exception as exc:
        logger.exception("Model run failed for model_id=%s", model_id)
        return error_response("ENGINE_ERROR", str(exc))


@router.put("/model/{model_id}/assumptions")
async def update_model_assumptions(
    model_id: int, body: UpdateModelAssumptionsRequest, request: Request,
):
    """Update saved assumptions for a model."""
    try:
        repo: ModelRepo = request.app.state.model_repo
        model = await repo.get_model(model_id)
        if not model:
            return error_response("NOT_FOUND", f"Model {model_id} not found")
        result = await repo.upsert_assumptions(model_id, model["model_type"], body.assumptions)
        return success_response(data=result)
    except Exception as exc:
        logger.exception("Assumption update failed for model_id=%s", model_id)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/model/{model_id}/save-version")
async def save_version(model_id: int, body: SaveVersionRequest, request: Request):
    """Save a version snapshot of the current model state."""
    try:
        repo: ModelRepo = request.app.state.model_repo
        model = await repo.get_model(model_id)
        if not model:
            return error_response("NOT_FOUND", f"Model {model_id} not found")

        # Build snapshot: assumptions + latest output
        assumptions = await repo.get_assumptions(model_id, model["model_type"])
        outputs = await repo.get_outputs_for_model(model_id)
        latest_output = outputs[0] if outputs else None

        snapshot = {
            "model": model,
            "assumptions": assumptions,
            "output": latest_output,
        }
        snapshot_blob = json.dumps(snapshot, default=str)

        # Determine version number
        versions = await repo.get_versions_for_model(model_id)
        version_number = (versions[0]["version_number"] + 1) if versions else 1

        version = await repo.create_version({
            "model_id": model_id,
            "version_number": version_number,
            "snapshot_blob": snapshot_blob,
            "annotation": body.annotation,
            "snapshot_size_bytes": len(snapshot_blob.encode("utf-8")),
        })
        return success_response(data=version)
    except Exception as exc:
        logger.exception("Save version failed for model_id=%s", model_id)
        return error_response("ENGINE_ERROR", str(exc))


@router.get("/model/{model_id}/versions")
async def get_versions(model_id: int, request: Request):
    """List version history for a model."""
    repo: ModelRepo = request.app.state.model_repo
    versions = await repo.get_versions_for_model(model_id)
    return success_response(data=versions)


@router.get("/model/{model_id}/version/{version_id}")
async def get_version(model_id: int, version_id: int, request: Request):
    """Load a specific version snapshot."""
    repo: ModelRepo = request.app.state.model_repo
    version = await repo.get_version(version_id)
    if not version:
        return error_response("NOT_FOUND", f"Version {version_id} not found")
    # Parse snapshot_blob back to dict
    snapshot = json.loads(version["snapshot_blob"]) if version.get("snapshot_blob") else None
    return success_response(data={**version, "snapshot": snapshot})


@router.get("/model/{model_id}/outputs")
async def get_outputs(model_id: int, request: Request):
    """Get all run outputs for a model."""
    repo: ModelRepo = request.app.state.model_repo
    outputs = await repo.get_outputs_for_model(model_id)
    return success_response(data=outputs)


@router.get("/model/{model_id}/output/{output_id}")
async def get_output(model_id: int, output_id: int, request: Request):
    """Get a specific run output."""
    repo: ModelRepo = request.app.state.model_repo
    output = await repo.get_output(output_id)
    if not output:
        return error_response("NOT_FOUND", f"Output {output_id} not found")
    return success_response(data=output)


# ---------------------------------------------------------------------------
# Sensitivity Analysis endpoints
# ---------------------------------------------------------------------------


async def _get_assumptions_and_data(
    ticker: str, request: Request, overrides: dict | None = None,
):
    """Shared helper: generate assumptions + gather engine data."""
    engine = request.app.state.assumption_engine
    assumptions = await engine.generate_assumptions(
        ticker, model_type="dcf", overrides=overrides,
    )
    data, price = await _gather_engine_data(ticker, request)
    return assumptions, data, price


@router.post("/{ticker}/sensitivity/slider")
async def run_sensitivity_slider(
    ticker: str, body: SliderRequest, request: Request,
):
    """Recalculate DCF with slider parameter overrides."""
    try:
        assumptions, data, price = await _get_assumptions_and_data(
            ticker, request,
        )
        svc: SensitivityService = request.app.state.sensitivity_service
        result = await svc.run_slider(assumptions, body.overrides, data, price)
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("Slider run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/sensitivity/tornado")
async def run_sensitivity_tornado(
    ticker: str, body: TornadoRequest, request: Request,
):
    """Generate tornado chart sensitivity analysis."""
    try:
        assumptions, data, price = await _get_assumptions_and_data(
            ticker, request, overrides=body.overrides,
        )
        svc: SensitivityService = request.app.state.sensitivity_service
        result = await svc.run_tornado(assumptions, data, price)
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("Tornado run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/sensitivity/monte-carlo")
async def run_sensitivity_monte_carlo(
    ticker: str, body: MonteCarloRequest, request: Request,
):
    """Run Monte Carlo simulation on DCF assumptions."""
    try:
        assumptions, data, price = await _get_assumptions_and_data(
            ticker, request, overrides=body.overrides,
        )
        svc: SensitivityService = request.app.state.sensitivity_service
        result = await svc.run_monte_carlo(
            assumptions, data, price,
            iterations=body.iterations,
            seed=body.seed,
        )
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("Monte Carlo run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.post("/{ticker}/sensitivity/table-2d")
async def run_sensitivity_table_2d(
    ticker: str, body: Table2DRequest, request: Request,
):
    """Generate 2D sensitivity table (e.g. WACC × Terminal Growth)."""
    try:
        assumptions, data, price = await _get_assumptions_and_data(
            ticker, request, overrides=body.overrides,
        )
        svc: SensitivityService = request.app.state.sensitivity_service
        result = await svc.run_table_2d(
            assumptions, data, price,
            row_variable=body.row_variable,
            col_variable=body.col_variable,
            grid_size=body.grid_size,
            row_min=body.row_min,
            row_max=body.row_max,
            col_min=body.col_min,
            col_max=body.col_max,
        )
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("Table-2D run failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


@router.get("/{ticker}/sensitivity/parameters")
async def get_sensitivity_parameters(ticker: str, request: Request):
    """Return slider parameter definitions for the frontend."""
    svc: SensitivityService = request.app.state.sensitivity_service
    defs = svc.get_parameter_definitions()
    return success_response(data=[d.model_dump(mode="json") for d in defs])


# ---------------------------------------------------------------------------
# Model Overview endpoint
# ---------------------------------------------------------------------------


@router.post("/{ticker}/overview")
async def generate_overview(
    ticker: str, body: OverviewRequest, request: Request,
):
    """Generate full model overview: football field, weights, agreement, scenario table."""
    try:
        engine = request.app.state.assumption_engine
        assumptions = await engine.generate_assumptions(
            ticker, overrides=body.overrides,
        )
        data, price = await _gather_engine_data(ticker, request)

        # Get detection scores for weighting (convert list[ModelScore] → dict)
        detection_svc = request.app.state.model_detection_service
        detection_result = await detection_svc.detect(ticker)
        detection_scores = {
            ms.model_type: float(ms.score)
            for ms in detection_result.scores
        }

        # Auto-discover peers if not provided
        peer_tickers = body.peer_tickers
        if not peer_tickers:
            company_svc = request.app.state.company_service
            peer_tickers = await company_svc.find_peers(ticker)
            logger.info("Auto-discovered %d peers for %s (overview)", len(peer_tickers), ticker)

        peer_data = None
        if peer_tickers:
            peer_data = await _gather_peer_data(peer_tickers, request)

        svc: ModelOverviewService = request.app.state.model_overview_service
        result = await svc.generate_overview(
            ticker=ticker,
            assumption_set=assumptions,
            data=data,
            current_price=price,
            detection_scores=detection_scores,
            peer_data=peer_data,
        )
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("Overview generation failed for %s", ticker)
        return error_response("ENGINE_ERROR", str(exc))


