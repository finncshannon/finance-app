"""
Integration tests — data consistency checks.
Requires the backend running on localhost:8000.
"""

import pytest
import httpx


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=15.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Test 1 — System health
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_system_health(client: httpx.AsyncClient):
    """Health endpoint should return 200."""
    resp = await client.get("/api/v1/system/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 2 — Settings returns valid data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_settings_returns_valid_data(client: httpx.AsyncClient):
    """GET /settings/ should return 200 with a JSON body."""
    resp = await client.get("/api/v1/settings/")
    assert resp.status_code == 200

    body = resp.json()
    assert body is not None, "Settings returned empty body"


# ---------------------------------------------------------------------------
# Test 3 — Database stats returns table counts
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_stats_table_counts(client: httpx.AsyncClient):
    """Database stats should return table count info."""
    resp = await client.get("/api/v1/settings/database-stats")
    assert resp.status_code == 200

    data = resp.json()["data"]
    # Should contain some kind of table/count information
    assert isinstance(data, dict), "Expected dict response from database-stats"
    assert len(data) > 0, "Database stats returned empty dict"


# ---------------------------------------------------------------------------
# Test 4 — Empty scanner does not cause server error
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_empty_scanner_no_server_error(client: httpx.AsyncClient):
    """POST scanner/screen with empty filters should not 500."""
    resp = await client.post(
        "/api/v1/scanner/screen",
        json={
            "filters": [],
            "form_types": ["10-K"],
            "universe": "all",
            "limit": 10,
            "offset": 0,
        },
    )
    assert resp.status_code != 500, "Server error on empty scanner screen"
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 5 — Company name consistency across modules
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.integration
async def test_company_name_consistency(client: httpx.AsyncClient):
    """Company name should match between companies search and research profile."""
    # Get company via search
    search = await client.get("/api/v1/companies/search?q=AAPL")
    if search.status_code != 200:
        pytest.skip("Companies search not available")
    results = search.json().get("data", [])
    if not results:
        pytest.skip("No search results for AAPL")

    search_name = None
    for r in results:
        if r.get("ticker") == "AAPL":
            search_name = r.get("company_name")
            break
    if not search_name:
        pytest.skip("AAPL not in search results")

    # Get from research profile
    profile = await client.get("/api/v1/research/AAPL/profile")
    if profile.status_code != 200:
        pytest.skip("Research profile not available")
    profile_name = profile.json()["data"].get("company_name")

    assert search_name == profile_name, f"Name mismatch: search='{search_name}' vs profile='{profile_name}'"
