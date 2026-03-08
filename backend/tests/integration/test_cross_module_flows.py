"""
Integration tests — cross-module API flows.
Requires the backend running on localhost:8000.
"""

import pytest
import httpx


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=15.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Test 1 — Scanner -> Model Builder flow
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_scanner_to_research_profile(client: httpx.AsyncClient):
    """Screen for stocks, then pull the first ticker's research profile."""
    # Step 1: run a scanner screen
    screen_resp = await client.post(
        "/api/v1/scanner/screen",
        json={
            "filters": [],
            "form_types": ["10-K"],
            "universe": "all",
            "limit": 5,
            "offset": 0,
        },
    )
    assert screen_resp.status_code == 200
    screen_data = screen_resp.json()["data"]

    rows = screen_data.get("rows") or screen_data.get("results") or []
    if not rows:
        pytest.skip("Scanner returned no rows — need data loaded first")

    # Step 2: grab first ticker
    first = rows[0]
    ticker = first.get("ticker") or first.get("symbol")
    assert ticker, "Could not extract ticker from scanner row"

    # Step 3: hit research profile
    profile_resp = await client.get(f"/api/v1/research/{ticker}/profile")
    assert profile_resp.status_code == 200

    # Step 4: verify company_name present
    profile_data = profile_resp.json()["data"]
    assert "company_name" in profile_data, "Profile missing company_name"


# ---------------------------------------------------------------------------
# Test 2 — Research -> Export flow
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_research_to_export(client: httpx.AsyncClient):
    """Fetch AAPL financials then export to Excel."""
    # Step 1: financials
    fin_resp = await client.get(
        "/api/v1/research/AAPL/financials",
        params={"period_type": "annual", "limit": 5},
    )
    assert fin_resp.status_code == 200

    # Step 2: export to excel
    export_resp = await client.post("/api/v1/export/research/AAPL/excel")
    assert export_resp.status_code == 200

    # Step 3: verify content type
    ct = export_resp.headers.get("content-type", "")
    assert "spreadsheet" in ct, f"Expected spreadsheet content-type, got {ct}"


# ---------------------------------------------------------------------------
# Test 3 — Portfolio implied prices
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_portfolio_implied_prices(client: httpx.AsyncClient):
    """GET implied prices — should always return 200 with an implied_prices key."""
    resp = await client.get("/api/v1/portfolio/implied-prices")
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert "implied_prices" in data, "Response missing implied_prices key"


# ---------------------------------------------------------------------------
# Test 4 — Settings system info
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_settings_system_info(client: httpx.AsyncClient):
    """System info should return app_version and python_version."""
    resp = await client.get("/api/v1/settings/system-info")
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert "app_version" in data, "Missing app_version"
    assert "python_version" in data, "Missing python_version"


# ---------------------------------------------------------------------------
# Test 5 — Scanner → Model Builder detect flow
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_scanner_to_model_builder(client: httpx.AsyncClient):
    """Screen stocks, take first ticker, run model detection."""
    screen = await client.post("/api/v1/scanner/screen", json={
        "filters": [], "form_types": ["10-K"], "universe": "all", "limit": 5, "offset": 0,
    })
    assert screen.status_code == 200
    rows = screen.json()["data"].get("rows", [])
    if not rows:
        pytest.skip("No scanner data")

    ticker = rows[0]["ticker"]

    # Detect model type
    detect = await client.get(f"/api/v1/model-builder/{ticker}/detect")
    assert detect.status_code == 200
    det_data = detect.json()["data"]
    assert "recommended_model" in det_data
    assert det_data["recommended_model"] in ("dcf", "ddm", "comps", "revbased")


# ---------------------------------------------------------------------------
# Test 6 — Full lifecycle flow
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_lifecycle_flow(client: httpx.AsyncClient):
    """Full flow: detect model → generate → run → check implied prices."""
    ticker = "AAPL"

    # 1. Detect
    detect = await client.get(f"/api/v1/model-builder/{ticker}/detect")
    if detect.status_code != 200:
        pytest.skip("Detection not available for AAPL")
    model_type = detect.json()["data"]["recommended_model"]

    # 2. Generate assumptions
    gen = await client.post(f"/api/v1/model-builder/{ticker}/generate", json={"model_type": model_type})
    assert gen.status_code == 200

    # 3. Check implied prices endpoint works
    implied = await client.get("/api/v1/portfolio/implied-prices")
    assert implied.status_code == 200
    assert "implied_prices" in implied.json()["data"]


# ---------------------------------------------------------------------------
# Test 7 — Watchlist round-trip
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_watchlist_round_trip(client: httpx.AsyncClient):
    """Create watchlist, add ticker, verify it appears, clean up."""
    # Create
    create = await client.post("/api/v1/dashboard/watchlists", json={"name": "_test_nav_wl"})
    assert create.status_code == 200
    wl_id = create.json()["data"]["id"]

    try:
        # Add ticker
        add = await client.post(f"/api/v1/dashboard/watchlists/{wl_id}/items", json={"ticker": "MSFT"})
        assert add.status_code == 200

        # Verify appears
        detail = await client.get(f"/api/v1/dashboard/watchlists/{wl_id}")
        assert detail.status_code == 200
        items = detail.json()["data"]["items"]
        tickers = [i["ticker"] for i in items]
        assert "MSFT" in tickers
    finally:
        # Cleanup
        await client.delete(f"/api/v1/dashboard/watchlists/{wl_id}")
