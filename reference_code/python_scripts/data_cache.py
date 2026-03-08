"""
Yahoo Finance Data Cache - SQLite-based

Caches API responses to reduce Yahoo Finance API calls and improve refresh speed.
Second refresh of the same ticker uses cached data instead of hitting the API.

TTLs:
- Price/info data: 5 minutes (changes frequently during market hours)
- Financial statements: 24 hours (updated quarterly)
- Dividend history: 24 hours (updated quarterly)

Storage:
- SQLite database at data/yahoo_cache/cache.db
- DataFrames serialized via JSON (orient='split', date_format='iso')
- Dicts/Series serialized via JSON

Version: 1.0
"""

import sqlite3
import json
import time
import logging
import os
import threading
from typing import Any, Optional
from pathlib import Path

import pandas as pd

logger = logging.getLogger('StockValuation')


# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Default TTLs in seconds
TTL_PRICE = 300       # 5 minutes for price/info data
TTL_FINANCIAL = 86400  # 24 hours for financial statements
TTL_DIVIDENDS = 86400  # 24 hours for dividend data

# Cache data types and their TTLs
CACHE_TTLS = {
    'info': TTL_PRICE,
    'financials': TTL_FINANCIAL,
    'balance_sheet': TTL_FINANCIAL,
    'cashflow': TTL_FINANCIAL,
    'dividends': TTL_DIVIDENDS,
}


# ============================================================================
# SERIALIZATION HELPERS
# ============================================================================

def _serialize_dataframe(df: pd.DataFrame) -> str:
    """Serialize a DataFrame to JSON string."""
    if df is None or df.empty:
        return ''
    return df.to_json(orient='split', date_format='iso')


def _deserialize_dataframe(data: str) -> pd.DataFrame:
    """Deserialize a JSON string back to DataFrame."""
    if not data:
        return pd.DataFrame()
    try:
        return pd.read_json(data, orient='split')
    except (ValueError, KeyError) as e:
        logger.warning(f"Corrupt DataFrame cache entry — discarding: {e}")
        return pd.DataFrame()


def _serialize_series(s: pd.Series) -> str:
    """Serialize a Series to JSON string."""
    if s is None or s.empty:
        return ''
    return s.to_json(date_format='iso')


def _deserialize_series(data: str) -> pd.Series:
    """Deserialize a JSON string back to Series."""
    if not data:
        return pd.Series()
    try:
        return pd.read_json(data, typ='series')
    except (ValueError, KeyError) as e:
        logger.warning(f"Corrupt Series cache entry — discarding: {e}")
        return pd.Series()


def _serialize_dict(d: dict) -> str:
    """Serialize a dict to JSON string, handling non-serializable values."""
    if not d:
        return '{}'

    def _make_serializable(obj):
        if isinstance(obj, (pd.Timestamp,)):
            return obj.isoformat()
        if isinstance(obj, (pd.Series, pd.DataFrame)):
            return None  # Skip embedded DataFrames/Series
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        return obj

    clean = {}
    for k, v in d.items():
        try:
            clean[k] = _make_serializable(v)
        except (TypeError, ValueError):
            clean[k] = None

    return json.dumps(clean)


def _deserialize_dict(data: str) -> dict:
    """Deserialize a JSON string back to dict."""
    if not data:
        return {}
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Corrupt dict cache entry — discarding: {e}")
        return {}


# ============================================================================
# CACHE CLASS
# ============================================================================

class DataCache:
    """
    SQLite-based cache for Yahoo Finance API data.

    Usage:
        cache = DataCache()

        # Check cache
        cached = cache.get('AAPL', 'financials')
        if cached is not None:
            return cached  # Use cached data

        # Fetch from API and store
        data = yf.Ticker('AAPL').financials
        cache.put('AAPL', 'financials', data)
    """

    def __init__(self, db_path: str = None):
        """
        Initialize cache with SQLite database.

        Args:
            db_path: Path to SQLite database file. If None, uses default
                     at data/yahoo_cache/cache.db
        """
        if db_path is None:
            import config
            cache_dir = config.DATA_DIR / 'yahoo_cache'
            os.makedirs(cache_dir, exist_ok=True)
            db_path = str(cache_dir / 'cache.db')

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create the cache table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    ticker TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    data TEXT,
                    timestamp REAL NOT NULL,
                    PRIMARY KEY (ticker, data_type)
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_cache_ticker
                ON cache(ticker)
            ''')

    def get(self, ticker: str, data_type: str) -> Optional[Any]:
        """
        Get cached data if it exists and hasn't expired.

        Args:
            ticker: Stock ticker symbol
            data_type: One of 'info', 'financials', 'balance_sheet',
                       'cashflow', 'dividends'

        Returns:
            Deserialized data, or None if not cached or expired
        """
        ttl = CACHE_TTLS.get(data_type, TTL_FINANCIAL)
        cutoff = time.time() - ttl

        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    'SELECT data, timestamp FROM cache '
                    'WHERE ticker = ? AND data_type = ? AND timestamp > ?',
                    (ticker.upper(), data_type, cutoff)
                ).fetchone()

            if row is None:
                return None

            raw_data, ts = row
            age = time.time() - ts

            # Deserialize based on type
            if data_type == 'info':
                result = _deserialize_dict(raw_data)
            elif data_type == 'dividends':
                result = _deserialize_series(raw_data)
            else:
                result = _deserialize_dataframe(raw_data)

            logger.debug(f"Cache HIT: {ticker}/{data_type} (age: {age:.0f}s)")
            return result

        except Exception as e:
            logger.warning(f"Cache read error for {ticker}/{data_type}: {e}")
            return None

    def put(self, ticker: str, data_type: str, data: Any):
        """
        Store data in cache.

        Args:
            ticker: Stock ticker symbol
            data_type: One of 'info', 'financials', 'balance_sheet',
                       'cashflow', 'dividends'
            data: Data to cache (dict, DataFrame, or Series)
        """
        try:
            # Serialize based on type
            if data_type == 'info':
                serialized = _serialize_dict(data)
            elif data_type == 'dividends':
                serialized = _serialize_series(data)
            else:
                serialized = _serialize_dataframe(data)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO cache (ticker, data_type, data, timestamp) '
                    'VALUES (?, ?, ?, ?)',
                    (ticker.upper(), data_type, serialized, time.time())
                )

            logger.debug(f"Cache PUT: {ticker}/{data_type}")

        except Exception as e:
            logger.warning(f"Cache write error for {ticker}/{data_type}: {e}")

    def invalidate(self, ticker: str = None, data_type: str = None):
        """
        Remove cached data.

        Args:
            ticker: If provided, invalidate only this ticker's data
            data_type: If provided, invalidate only this data type
                       (requires ticker)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if ticker and data_type:
                    conn.execute(
                        'DELETE FROM cache WHERE ticker = ? AND data_type = ?',
                        (ticker.upper(), data_type)
                    )
                elif ticker:
                    conn.execute(
                        'DELETE FROM cache WHERE ticker = ?',
                        (ticker.upper(),)
                    )
                else:
                    conn.execute('DELETE FROM cache')

            logger.info(f"Cache invalidated: ticker={ticker}, type={data_type}")

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute('SELECT COUNT(*) FROM cache').fetchone()[0]
                tickers = conn.execute(
                    'SELECT COUNT(DISTINCT ticker) FROM cache'
                ).fetchone()[0]
                oldest = conn.execute(
                    'SELECT MIN(timestamp) FROM cache'
                ).fetchone()[0]

            age = (time.time() - oldest) if oldest else 0
            return {
                'total_entries': total,
                'unique_tickers': tickers,
                'oldest_entry_age_hours': age / 3600,
                'db_path': self.db_path,
            }
        except Exception as e:
            return {'error': str(e)}

    def cleanup(self):
        """Remove all expired entries from cache, using per-type TTLs."""
        try:
            now = time.time()
            removed = 0
            with sqlite3.connect(self.db_path) as conn:
                for data_type, ttl in CACHE_TTLS.items():
                    cutoff = now - ttl
                    result = conn.execute(
                        'DELETE FROM cache WHERE data_type = ? AND timestamp < ?',
                        (data_type, cutoff)
                    )
                    removed += result.rowcount
                if removed > 0:
                    logger.info(f"Cache cleanup: removed {removed} expired entries")
                    conn.execute('VACUUM')
            return removed
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")
            return 0


# ============================================================================
# MODULE-LEVEL SINGLETON
# ============================================================================

_cache_instance: Optional[DataCache] = None
_cache_lock = threading.Lock()


def get_cache() -> DataCache:
    """Get or create the global cache instance (thread-safe)."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:  # double-checked locking
                _cache_instance = DataCache()
    return _cache_instance
