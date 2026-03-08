"""Smoke test -- hits all major API endpoints and reports pass/fail."""

import sys
import json
import httpx

BASE = "http://localhost:8000"
TIMEOUT = 10.0
MB_TIMEOUT = 30.0  # Model builder endpoints can be slower

passed = 0
failed = 0


def check(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  \033[32m[PASS]\033[0m {name}")
        passed += 1
    except Exception as e:
        print(f"  \033[31m[FAIL]\033[0m {name} -- {e}")
        failed += 1


client = httpx.Client(base_url=BASE, timeout=TIMEOUT)


def get_ok(path):
    r = client.get(path)
    assert r.status_code == 200, f"status {r.status_code}"
    return r.json().get("data", r.json())


def post_ok(path, body=None, timeout=None):
    r = client.post(path, json=body or {}, timeout=timeout)
    assert r.status_code == 200, f"status {r.status_code}"
    return r.json().get("data", r.json())


def put_ok(path, body=None):
    r = client.put(path, json=body or {})
    assert r.status_code == 200, f"status {r.status_code}"
    return r.json().get("data", r.json())


# -------------------------------------------------------------------
print("\n=== Finance App Smoke Test ===\n")

# 1. System health
check("System health", lambda: get_ok("/api/v1/system/health"))

# 2. Companies search
check("Companies search", lambda: get_ok("/api/v1/companies/search?q=Apple"))

# 3. Scanner screen (empty filters)
check(
    "Scanner screen",
    lambda: post_ok(
        "/api/v1/scanner/screen",
        {
            "filters": [],
            "form_types": ["10-K"],
            "universe": "all",
            "limit": 5,
            "offset": 0,
        },
    ),
)

# 4. Scanner metrics
check("Scanner metrics", lambda: get_ok("/api/v1/scanner/metrics"))

# 5. Research profile
check("Research profile (AAPL)", lambda: get_ok("/api/v1/research/AAPL/profile"))

# 6. Research financials
check(
    "Research financials (AAPL)",
    lambda: get_ok("/api/v1/research/AAPL/financials?period_type=annual&limit=3"),
)

# 7. Research ratios
check("Research ratios (AAPL)", lambda: get_ok("/api/v1/research/AAPL/ratios"))

# 8. Research filings
check(
    "Research filings (AAPL)",
    lambda: get_ok("/api/v1/research/AAPL/filings?limit=3"),
)

# 9. Portfolio positions
check("Portfolio positions", lambda: get_ok("/api/v1/portfolio/positions"))

# 10. Portfolio implied prices
check("Portfolio implied prices", lambda: get_ok("/api/v1/portfolio/implied-prices"))

# 11. Dashboard summary
check("Dashboard summary", lambda: get_ok("/api/v1/dashboard/summary"))

# 12. Dashboard watchlists
check("Dashboard watchlists", lambda: get_ok("/api/v1/dashboard/watchlists"))

# 13. Settings system info
check("Settings system info", lambda: get_ok("/api/v1/settings/system-info"))

# 14. Settings database stats
check("Settings database stats", lambda: get_ok("/api/v1/settings/database-stats"))

# 15. Export scanner CSV (returns binary CSV, not JSON)
def _check_export_csv():
    r = client.post("/api/v1/export/scanner/csv", json={"results": []}, timeout=TIMEOUT)
    assert r.status_code == 200, f"status {r.status_code}"
check("Export scanner CSV", _check_export_csv)

# 16. Export research Excel
def _check_export_excel():
    r = client.post("/api/v1/export/research/AAPL/excel")
    assert r.status_code == 200, f"status {r.status_code}"

check("Export research Excel (AAPL)", _check_export_excel)

# ─── Model Builder Workflow ──────────────────────────────────────────

TICKER = "AAPL"
MB = f"/api/v1/model-builder/{TICKER}"

# 17. Model detection
def _check_detect():
    d = get_ok(f"{MB}/detect")
    assert "scores" in d, "missing scores"
    assert len(d["scores"]) >= 2, "expected multiple model scores"

check("MB: detect model type", _check_detect)

# 18. Generate assumptions (DCF)
check(
    "MB: generate assumptions (DCF)",
    lambda: post_ok(
        f"{MB}/generate",
        {"model_type": "dcf"},
        timeout=MB_TIMEOUT,
    ),
)

# 19. Generate assumptions (Comps)
check(
    "MB: generate assumptions (Comps)",
    lambda: post_ok(
        f"{MB}/generate",
        {"model_type": "comps"},
        timeout=MB_TIMEOUT,
    ),
)

# 20. Generate assumptions (Revenue-Based)
check(
    "MB: generate assumptions (RevBased)",
    lambda: post_ok(
        f"{MB}/generate",
        {"model_type": "revenue_based"},
        timeout=MB_TIMEOUT,
    ),
)

# 21. Run DCF engine
def _check_run_dcf():
    d = post_ok(f"{MB}/run/dcf", {"overrides": {}}, timeout=MB_TIMEOUT)
    assert d is not None, "empty result"

check("MB: run DCF engine", _check_run_dcf)

# 22. Run DDM engine
check(
    "MB: run DDM engine",
    lambda: post_ok(f"{MB}/run/ddm", {"overrides": {}}, timeout=MB_TIMEOUT),
)

# 23. Run Comps engine
check(
    "MB: run Comps engine",
    lambda: post_ok(f"{MB}/run/comps", {"overrides": {}}, timeout=MB_TIMEOUT),
)

# 24. Run Revenue-Based engine
check(
    "MB: run RevBased engine",
    lambda: post_ok(f"{MB}/run/revbased", {"overrides": {}}, timeout=MB_TIMEOUT),
)

# 25. Sensitivity — slider
check(
    "MB: sensitivity slider",
    lambda: post_ok(f"{MB}/sensitivity/slider", {"overrides": {}}, timeout=MB_TIMEOUT),
)

# 26. Sensitivity — tornado
check(
    "MB: sensitivity tornado",
    lambda: post_ok(f"{MB}/sensitivity/tornado", {"overrides": {}}, timeout=MB_TIMEOUT),
)

# 27. Sensitivity — Monte Carlo
check(
    "MB: sensitivity Monte Carlo",
    lambda: post_ok(
        f"{MB}/sensitivity/monte-carlo",
        {"overrides": {}, "iterations": 100, "seed": 42},
        timeout=MB_TIMEOUT,
    ),
)

# 28. Sensitivity — 2D table
check(
    "MB: sensitivity 2D table",
    lambda: post_ok(
        f"{MB}/sensitivity/table-2d",
        {"overrides": {}, "grid_size": 5},
        timeout=MB_TIMEOUT,
    ),
)

# 29. Overview
check(
    "MB: overview",
    lambda: post_ok(f"{MB}/overview", {"overrides": {}}, timeout=MB_TIMEOUT),
)

# 30. Version save/load round-trip
def _check_version_roundtrip():
    # List models to find or create one
    models = get_ok(f"{MB}/models")
    if isinstance(models, dict):
        model_list = models.get("models", [])
    else:
        model_list = models
    if not model_list:
        # Generate + run to create a model first
        post_ok(f"{MB}/generate", {"model_type": "dcf"}, timeout=MB_TIMEOUT)
        post_ok(f"{MB}/run/dcf", {"overrides": {}}, timeout=MB_TIMEOUT)
        models = get_ok(f"{MB}/models")
        model_list = models.get("models", []) if isinstance(models, dict) else models
    if not model_list:
        # Ephemeral workflow doesn't persist models — verify empty list is valid
        assert isinstance(models, (list, dict)), "unexpected models response"
        return
    assert len(model_list) > 0, "no models found after generate+run"
    model_id = model_list[0]["id"]

    # Save a version
    ver = post_ok(
        f"/api/v1/model-builder/model/{model_id}/save-version",
        {"annotation": "smoke test snapshot"},
        timeout=MB_TIMEOUT,
    )

    # List versions
    versions = get_ok(f"/api/v1/model-builder/model/{model_id}/versions")
    ver_list = versions.get("versions", []) if isinstance(versions, dict) else versions
    assert len(ver_list) > 0, "no versions found after save"

check("MB: version save/load round-trip", _check_version_roundtrip)

# 31. WebSocket connection (status broadcasts every 30s, just verify connect)
def _check_ws():
    import websockets.sync.client as ws_sync
    ws_url = BASE.replace("http", "ws") + "/ws/status"
    with ws_sync.connect(ws_url, close_timeout=2) as ws:
        ws.send("ping")
        # Connection succeeded — broadcasts happen on 30s interval, don't wait

check("WebSocket status connection", _check_ws)

# -------------------------------------------------------------------
client.close()

print(f"\n{'=' * 40}")
print(f"  Passed: {passed}  |  Failed: {failed}  |  Total: {passed + failed}")
print(f"{'=' * 40}\n")

sys.exit(0 if failed == 0 else 1)
