"""Final verification — API-level equivalent of 15-step user workflow.

Requires: Backend running on localhost:8000 with AAPL data cached.
"""

import sys
import json
import time
import httpx

BASE = "http://localhost:8000"
TIMEOUT = 15.0
MB_TIMEOUT = 30.0

passed = 0
failed = 0
results = []

def step(num, name, fn):
    global passed, failed
    try:
        result = fn()
        print(f"  \033[32m[PASS]\033[0m Step {num}: {name}")
        passed += 1
        results.append((num, name, "PASS", result))
        return result
    except Exception as e:
        print(f"  \033[31m[FAIL]\033[0m Step {num}: {name} -- {e}")
        failed += 1
        results.append((num, name, "FAIL", str(e)))
        return None

client = httpx.Client(base_url=BASE, timeout=TIMEOUT)

def get(path):
    r = client.get(path)
    assert r.status_code == 200, f"GET {path} -> {r.status_code}"
    return r.json().get("data", r.json())

def post(path, body=None, timeout=None):
    r = client.post(path, json=body or {}, timeout=timeout or TIMEOUT)
    assert r.status_code == 200, f"POST {path} -> {r.status_code}"
    return r.json().get("data", r.json())

print("\n=== Finance App -- Final Verification ===\n")

# 1. Health check (simulates: app opens)
step(1, "App opens -- backend healthy", lambda: get("/api/v1/system/health"))

# 2. Dashboard loads
step(2, "Dashboard loads -- summary", lambda: get("/api/v1/dashboard/summary"))

# 3. Dashboard watchlists
step(3, "Dashboard watchlists load", lambda: get("/api/v1/dashboard/watchlists"))

# 4. Search AAPL
def _search():
    d = get("/api/v1/companies/search?q=AAPL")
    assert len(d) > 0, "no search results"
    return d
step(4, "Search AAPL", _search)

# 5. View company profile
step(5, "View AAPL profile", lambda: get("/api/v1/research/AAPL/profile"))

# 6. View quote
step(6, "View AAPL quote", lambda: get("/api/v1/companies/AAPL/quote"))

# 7. Model detection
def _detect():
    d = get("/api/v1/model-builder/AAPL/detect")
    assert "scores" in d, "missing scores"
    return d
step(7, "Model detection", _detect)

# 8. Generate assumptions (DCF)
step(8, "Generate DCF assumptions", lambda: post(
    "/api/v1/model-builder/AAPL/generate",
    {"model_type": "dcf"}, timeout=MB_TIMEOUT
))

# 9. Run DCF engine
def _run_dcf():
    d = post("/api/v1/model-builder/AAPL/run/dcf", {"overrides": {}}, timeout=MB_TIMEOUT)
    assert d is not None, "empty DCF result"
    return d
step(9, "Run DCF engine", _run_dcf)

# 10. Sensitivity — tornado
step(10, "Sensitivity tornado", lambda: post(
    "/api/v1/model-builder/AAPL/sensitivity/tornado",
    {"overrides": {}}, timeout=MB_TIMEOUT
))

# 11. Overview (football field)
step(11, "Model overview", lambda: post(
    "/api/v1/model-builder/AAPL/overview",
    {"overrides": {}}, timeout=MB_TIMEOUT
))

# 12. List models (save-version requires a persisted model; ephemeral runs don't persist)
def _list_models():
    models = get("/api/v1/model-builder/AAPL/models")
    model_list = models if isinstance(models, list) else models.get("models", models)
    if isinstance(model_list, list) and len(model_list) > 0:
        model_id = model_list[0]["id"]
        return post(
            f"/api/v1/model-builder/model/{model_id}/save-version",
            {"annotation": "final verification snapshot"}, timeout=MB_TIMEOUT
        )
    # No persisted models yet — verify endpoint returns valid empty list
    assert isinstance(models, (list, dict)), "unexpected models response type"
    return {"note": "no persisted models (expected on fresh DB)", "models": models}
step(12, "Models endpoint + save-version", _list_models)

# 13. Scanner screen
def _scan():
    d = post("/api/v1/scanner/screen", {
        "filters": [], "form_types": ["10-K"],
        "universe": "all", "limit": 10, "offset": 0
    })
    return d
step(13, "Scanner screen", _scan)

# 14. Portfolio positions
step(14, "Portfolio positions", lambda: get("/api/v1/portfolio/positions"))

# 15. Settings & system info
step(15, "Settings + system info", lambda: get("/api/v1/settings/system-info"))

# Summary
client.close()
print(f"\n{'=' * 50}")
print(f"  Passed: {passed}  |  Failed: {failed}  |  Total: {passed + failed}")
print(f"{'=' * 50}")

# Write results to file
with open("final_verification_results.json", "w") as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
        "steps": [{"step": s[0], "name": s[1], "status": s[2]} for s in results]
    }, f, indent=2)
    print(f"\n  Results saved to final_verification_results.json\n")

sys.exit(0 if failed == 0 else 1)
