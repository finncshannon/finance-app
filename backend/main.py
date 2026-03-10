import asyncio
import json
import logging
import sys
import uuid

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from db.connection import db
from db.init_user_db import init_user_db
from db.init_cache_db import init_cache_db

# Configure finance_app logger so log output is visible via Electron's stdout/stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logging.getLogger("finance_app").setLevel(logging.INFO)
from routers import (
    companies_router,
    dashboard_router,
    export_router,
    models_router,
    news_router,
    portfolio_router,
    research_router,
    scanner_router,
    settings_router,
    system_router,
)
from routers import universe_router

logger = logging.getLogger("finance_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle for the FastAPI app."""
    # --- Startup ---
    logger.info("Initializing databases...")
    await db.connect()
    await init_user_db(db)
    await init_cache_db(db)
    logger.info("Databases initialized successfully.")

    # Seed default settings (INSERT OR IGNORE pattern)
    from services.settings_service import SettingsService
    settings_svc = SettingsService(db)
    await settings_svc.seed_defaults()
    app.state.settings_service = settings_svc

    # Initialize market data provider + service
    from providers.yahoo_finance import YahooFinanceProvider
    from providers.registry import provider_registry
    from services.market_data_service import MarketDataService

    yahoo_provider = YahooFinanceProvider()
    provider_registry.register("yahoo", yahoo_provider)
    market_data_svc = MarketDataService(db, provider_name="yahoo")
    app.state.market_data_service = market_data_svc
    logger.info("Market data service initialized (provider: yahoo).")

    # Initialize SEC EDGAR provider + XBRL service
    from providers.sec_edgar import SECEdgarProvider
    from services.xbrl_service import XBRLService

    sec_provider = SECEdgarProvider(settings_service=settings_svc)
    xbrl_svc = XBRLService(db, sec_provider)
    app.state.sec_provider = sec_provider
    app.state.xbrl_service = xbrl_svc
    logger.info("SEC EDGAR provider and XBRL service initialized.")

    # Initialize data extraction service
    from services.data_extraction_service import DataExtractionService

    data_extraction_svc = DataExtractionService(db, market_data_svc)
    app.state.data_extraction_service = data_extraction_svc
    logger.info("Data extraction service initialized.")

    # Initialize model detection service
    from services.model_detection_service import ModelDetectionService

    model_detection_svc = ModelDetectionService(db, data_extraction_svc)
    app.state.model_detection_service = model_detection_svc
    logger.info("Model detection service initialized.")

    # Initialize data readiness service
    from services.data_readiness_service import DataReadinessService

    data_readiness_svc = DataReadinessService(db=db, model_detection_svc=model_detection_svc)
    app.state.data_readiness_service = data_readiness_svc
    logger.info("Data readiness service initialized.")

    # Initialize assumption engine
    from services.assumption_engine import AssumptionEngine

    assumption_engine = AssumptionEngine(db, market_data_svc, settings_svc)
    app.state.assumption_engine = assumption_engine
    logger.info("Assumption engine initialized.")

    # Register valuation engines (stateless — stored on app.state for discoverability)
    from engines import DCFEngine, DDMEngine, CompsEngine, RevBasedEngine

    app.state.dcf_engine = DCFEngine
    app.state.ddm_engine = DDMEngine
    app.state.comps_engine = CompsEngine
    app.state.revbased_engine = RevBasedEngine
    logger.info("Valuation engines registered (DCF, DDM, Comps, RevBased).")

    # Initialize sensitivity service
    from services.sensitivity import SensitivityService

    sensitivity_svc = SensitivityService(settings_service=settings_svc)
    app.state.sensitivity_service = sensitivity_svc
    logger.info("Sensitivity service initialized.")

    # Initialize model overview service
    from services.model_overview import ModelOverviewService

    model_overview_svc = ModelOverviewService(db=db, settings_service=settings_svc)
    app.state.model_overview_service = model_overview_svc
    logger.info("Model overview service initialized.")

    # Initialize model repo
    from repositories.model_repo import ModelRepo

    model_repo = ModelRepo(db)
    app.state.model_repo = model_repo
    logger.info("Model repo initialized.")

    # Initialize scanner service
    from repositories.scanner_repo import ScannerRepo
    from services.scanner import ScannerService

    scanner_repo = ScannerRepo(db)
    scanner_svc = ScannerService(db, scanner_repo, market_data_svc=market_data_svc)
    app.state.scanner_service = scanner_svc
    app.state.scanner_repo = scanner_repo
    logger.info("Scanner service initialized.")

    # Initialize portfolio services
    from repositories.portfolio_repo import PortfolioRepo
    from repositories.portfolio_account_repo import PortfolioAccountRepo
    from repositories.portfolio_transaction_repo import PortfolioTransactionRepo
    from repositories.price_alert_repo import PriceAlertRepo
    from services.portfolio import PortfolioService
    from services.portfolio.analytics import PortfolioAnalytics
    from services.portfolio.benchmark import BenchmarkService
    from services.portfolio.attribution import AttributionService

    portfolio_repo = PortfolioRepo(db)
    account_repo = PortfolioAccountRepo(db)
    transaction_repo = PortfolioTransactionRepo(db)
    alert_repo = PriceAlertRepo(db)

    portfolio_svc = PortfolioService(
        db=db,
        portfolio_repo=portfolio_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        alert_repo=alert_repo,
        market_data_svc=market_data_svc,
    )
    app.state.portfolio_service = portfolio_svc

    portfolio_analytics = PortfolioAnalytics(db, market_data_svc)
    app.state.portfolio_analytics = portfolio_analytics

    bench_svc = BenchmarkService(db, market_data_svc)
    app.state.benchmark_service = bench_svc

    attr_svc = AttributionService(db, market_data_svc)
    app.state.attribution_service = attr_svc
    # Income service
    from services.portfolio.income_service import IncomeService

    income_svc = IncomeService(db, market_data_svc, portfolio_repo)
    app.state.income_service = income_svc
    logger.info("Portfolio services initialized (service, analytics, benchmark, attribution, income).")

    # Initialize watchlist service
    from repositories.watchlist_repo import WatchlistRepo
    from services.watchlist_service import WatchlistService

    watchlist_repo = WatchlistRepo(db)
    watchlist_svc = WatchlistService(db, watchlist_repo, market_data_svc)
    app.state.watchlist_service = watchlist_svc
    logger.info("Watchlist service initialized.")

    # Initialize company service
    from services.company_service import CompanyService

    company_svc = CompanyService(db, market_data_svc, data_extraction_svc, sec_provider)
    app.state.company_service = company_svc
    logger.info("Company service initialized.")

    # Initialize universe service
    from services.universe_service import UniverseService

    universe_svc = UniverseService(db, sec_provider)
    app.state.universe_service = universe_svc
    logger.info("Universe service initialized.")

    # Pre-load curated universes (DOW, S&P 500, Russell 3000) synchronously
    # so they're available before the frontend connects.
    try:
        curated_results = await universe_svc.load_all_curated()
        logger.info("Curated universes pre-loaded: %s", curated_results)
    except Exception as exc:
        logger.error("Failed to pre-load curated universes: %s", exc)

    # Initialize universe hydration service
    from services.universe_hydration_service import UniverseHydrationService

    hydration_svc = UniverseHydrationService(db, market_data_svc, universe_svc)
    app.state.hydration_service = hydration_svc
    logger.info("Universe hydration service initialized.")

    # Initialize company events service
    from services.company_events_service import CompanyEventsService

    events_svc = CompanyEventsService(db, market_data_svc)
    app.state.events_service = events_svc
    logger.info("Company events service initialized.")

    # Initialize dashboard service
    from services.dashboard_service import DashboardService

    dashboard_svc = DashboardService(
        db=db,
        market_data_svc=market_data_svc,
        portfolio_svc=portfolio_svc,
        watchlist_svc=watchlist_svc,
        events_svc=events_svc,
        universe_svc=universe_svc,
    )
    app.state.dashboard_service = dashboard_svc
    logger.info("Dashboard service initialized.")

    # Background event fetch (non-blocking)
    event_fetch_task = asyncio.create_task(
        events_svc.run_startup_fetch(portfolio_svc, watchlist_svc, universe_svc)
    )
    logger.info("Background event fetch task started.")

    # Initialize research service
    from services.research_service import ResearchService
    from repositories.filing_repo import FilingRepo
    from repositories.research_repo import ResearchRepo

    filing_repo = FilingRepo(db)
    research_repo = ResearchRepo(db)
    research_svc = ResearchService(
        db=db,
        company_svc=company_svc,
        data_extraction_svc=data_extraction_svc,
        market_data_svc=market_data_svc,
        events_svc=events_svc,
        filing_repo=filing_repo,
        research_repo=research_repo,
    )
    app.state.research_service = research_svc
    app.state.filing_repo = filing_repo
    app.state.research_repo = research_repo
    logger.info("Research service initialized.")

    # Initialize news service with DB persistence
    from repositories.news_repo import NewsRepo
    from services.news_service import NewsService

    news_repo = NewsRepo(db)
    news_svc = NewsService(news_repo=news_repo)
    app.state.news_service = news_svc
    logger.info("News service initialized (with DB persistence).")

    # Initialize price refresh service + start background loops
    from services.price_refresh_service import (
        PriceRefreshService,
        price_ws_manager,
        status_ws_manager,
    )

    price_refresh_svc = PriceRefreshService(market_data_svc, price_ws_manager, status_ws_manager)
    app.state.price_refresh_service = price_refresh_svc
    app.state.price_ws_manager = price_ws_manager
    app.state.status_ws_manager = status_ws_manager

    refresh_task = asyncio.create_task(price_refresh_svc.run_refresh_loop())
    status_task = asyncio.create_task(price_refresh_svc.run_status_loop())
    logger.info("Price refresh and status broadcast loops started.")

    # --- Startup price refresh (one-time, all portfolio + watchlist tickers) ---
    async def _startup_price_refresh():
        """One-time refresh of portfolio + watchlist tickers on app launch."""
        try:
            # Get portfolio tickers
            positions = await portfolio_svc.repo.get_all_positions()
            portfolio_tickers = list({p["ticker"] for p in positions})

            # Get watchlist tickers
            watchlist_tickers = []
            watchlists = await watchlist_svc.get_all_watchlists()
            for wl in watchlists:
                detail = await watchlist_svc.get_watchlist(wl["id"])
                if detail and "items" in detail:
                    watchlist_tickers.extend([item["ticker"] for item in detail["items"]])

            all_tickers = list(set(portfolio_tickers + watchlist_tickers))
            if all_tickers:
                logger.info("Startup refresh: %d tickers", len(all_tickers))
                await market_data_svc.refresh_batch(all_tickers)
                logger.info("Startup refresh complete")
            else:
                logger.info("Startup refresh: no tickers to refresh")
        except Exception as exc:
            logger.error("Startup refresh failed: %s", exc)

    startup_refresh_task = asyncio.create_task(_startup_price_refresh())

    # Start background hydration (fetch market data for universe tickers)
    # Note: curated universes are already loaded above during startup.
    async def _startup_hydration():
        try:
            logger.info("Starting background hydration...")
            await hydration_svc.run_hydration()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Startup hydration failed: %s", exc)

    hydration_task = asyncio.create_task(_startup_hydration())
    logger.info("Background hydration task started.")

    # --- Profile backfill (fetch missing company profiles for portfolio tickers) ---
    async def _backfill_profiles():
        """Fetch missing company profiles for portfolio positions."""
        try:
            from repositories.company_repo import CompanyRepo

            positions = await portfolio_svc.repo.get_all_positions()
            tickers = list({p["ticker"] for p in positions})
            company_repo_local = CompanyRepo(db)

            fetched = 0
            for ticker in tickers:
                company = await company_repo_local.get_by_ticker(ticker)
                if not company or company.get("company_name") == ticker or company.get("sector") == "Unknown":
                    try:
                        await market_data_svc.get_company(ticker)
                        fetched += 1
                        await asyncio.sleep(2)  # Rate limit friendly
                    except Exception:
                        pass
            logger.info("Profile backfill complete: %d/%d tickers fetched", fetched, len(tickers))
        except Exception as exc:
            logger.error("Profile backfill failed: %s", exc)

    backfill_task = asyncio.create_task(_backfill_profiles())
    logger.info("Background profile backfill task started.")

    # Start backup scheduler
    from services.backup_service import BackupService
    backup_svc = BackupService(db)
    backup_task = asyncio.create_task(backup_svc.run_scheduler())
    app.state.backup_service = backup_svc

    # Initialize export services
    from services.export.model_excel_service import ModelExcelService
    from services.export.model_pdf_service import ModelPDFService
    from services.export.scanner_export_service import ScannerExportService
    from services.export.portfolio_export_service import PortfolioExportService
    from services.export.research_export_service import ResearchExportService

    app.state.model_excel_service = ModelExcelService(model_repo=model_repo)
    app.state.model_pdf_service = ModelPDFService()
    app.state.scanner_export_service = ScannerExportService()
    app.state.portfolio_export_service = PortfolioExportService(portfolio_service=portfolio_svc)
    app.state.research_export_service = ResearchExportService(db=db)
    logger.info("Export services initialized.")

    # Initialize system info service
    from services.system_info_service import SystemInfoService

    system_info_svc = SystemInfoService(db_paths={
        "user_data": str(db.user_db_path),
        "market_cache": str(db.cache_db_path),
    })
    app.state.system_info_service = system_info_svc
    logger.info("System info service initialized.")

    # Make db available via app state for routers
    app.state.db = db

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    for task in [backup_task, refresh_task, status_task, event_fetch_task, hydration_task, startup_refresh_task, backfill_task]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await db.close()
    logger.info("Database connections closed.")


app = FastAPI(
    title="Finance App API",
    description="Backend API for the Finance App desktop application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow all localhost origins (Electron renderer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(system_router.router)
app.include_router(companies_router.router)
app.include_router(models_router.router)
app.include_router(scanner_router.router)
app.include_router(portfolio_router.router)
app.include_router(research_router.router)
app.include_router(news_router.router)
app.include_router(dashboard_router.router)
app.include_router(settings_router.router)
app.include_router(export_router.router)
app.include_router(universe_router.router)


# --- WebSocket Endpoints ---


@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    """Live price updates pushed to frontend during market hours.

    Accepts subscription messages:
        { "type": "subscribe", "tickers": ["AAPL", "MSFT"] }
    """
    from services.price_refresh_service import price_ws_manager

    client_id = str(uuid.uuid4())
    await price_ws_manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            if message.get("type") == "subscribe":
                tickers = message.get("tickers", [])
                price_ws_manager.subscribe(client_id, tickers)
                await websocket.send_json(
                    {"type": "subscription_confirmed", "tickers": tickers}
                )

                # Send initial snapshot for subscribed tickers
                refresh_svc = app.state.price_refresh_service
                snapshot = await refresh_svc.get_initial_snapshot(tickers)
                if snapshot:
                    await websocket.send_json(
                        {"type": "price_update", "data": snapshot}
                    )
    except WebSocketDisconnect:
        price_ws_manager.disconnect(client_id)
    except Exception:
        price_ws_manager.disconnect(client_id)


@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    """System health updates pushed to frontend every 30 seconds."""
    from services.price_refresh_service import status_ws_manager

    client_id = str(uuid.uuid4())
    await status_ws_manager.connect(websocket, client_id)

    try:
        while True:
            # Wait for any message (keepalive / ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        status_ws_manager.disconnect(client_id)
    except Exception:
        status_ws_manager.disconnect(client_id)
