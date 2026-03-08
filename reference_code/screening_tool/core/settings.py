"""
Settings manager — loads/saves app configuration from config/settings.json.

Also manages saved searches in config/saved_searches.json.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Paths relative to Screener root
SCREENER_ROOT = Path(__file__).parent.parent
CONFIG_DIR = SCREENER_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
SAVED_SEARCHES_FILE = CONFIG_DIR / "saved_searches.json"

# Default settings (used if settings.json is missing or incomplete)
DEFAULTS = {
    "sec_contact_email": "",
    "universe": "sp500",
    "universe_mode": "sp500",           # "sp500", "custom", "sp500_plus_custom"
    "custom_tickers": [],               # User-added tickers (e.g., ["PLTR", "RKLB"])
    "cache_dir": "data/_cache",
    "filing_sections": ["item1", "item1a", "item7"],
    "max_concurrent_downloads": 1,
    "search_defaults": {
        "sector_filter": "All",
        "min_match_score": 10,
        "max_results": 100,
    },
    "export_dir": "data/search_results",
    "last_data_refresh": "",
    "version": "1.0.0",
}


def load_settings() -> Dict[str, Any]:
    """
    Load settings from disk, merging with defaults for any missing keys.

    Returns:
        Complete settings dict with all keys guaranteed present.
    """
    settings = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            # Deep merge: update top-level, then nested dicts
            for key, value in saved.items():
                if isinstance(value, dict) and isinstance(settings.get(key), dict):
                    settings[key].update(value)
                else:
                    settings[key] = value
    except Exception:
        pass  # Use defaults on any error
    return settings


def save_settings(settings: Dict[str, Any]):
    """Save settings to disk. Creates config/ dir if needed."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2, default=str)
    except Exception:
        pass


def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting value by key."""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any):
    """Set a single setting value and save to disk."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def get_sec_email() -> str:
    """Get the SEC contact email."""
    return get_setting("sec_contact_email", "")


def set_sec_email(email: str):
    """Set the SEC contact email."""
    set_setting("sec_contact_email", email)


# ----------------------------------------------------------------
# Saved searches
# ----------------------------------------------------------------

def load_saved_searches() -> List[Dict]:
    """Load saved search presets."""
    try:
        if SAVED_SEARCHES_FILE.exists():
            with open(SAVED_SEARCHES_FILE, "r") as f:
                data = json.load(f)
            return data.get("searches", [])
    except Exception:
        pass
    return []


def save_search(name: str, query: str, sector: str = "All",
                universe: str = "sp500"):
    """Save a search preset."""
    searches = load_saved_searches()
    # Update existing or append
    for s in searches:
        if s.get("name") == name:
            s["query"] = query
            s["sector"] = sector
            s["universe"] = universe
            break
    else:
        searches.append({
            "name": name,
            "query": query,
            "sector": sector,
            "universe": universe,
        })

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SAVED_SEARCHES_FILE, "w") as f:
            json.dump({"searches": searches}, f, indent=2)
    except Exception:
        pass


def delete_saved_search(name: str):
    """Delete a saved search by name."""
    searches = load_saved_searches()
    searches = [s for s in searches if s.get("name") != name]
    try:
        with open(SAVED_SEARCHES_FILE, "w") as f:
            json.dump({"searches": searches}, f, indent=2)
    except Exception:
        pass
