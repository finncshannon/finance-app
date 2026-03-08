"""
Financial Filter Engine for Screening Tool

Applies numeric filters to search results based on Yahoo Finance metrics.
Supports composable AND-logic filters with standard comparison operators.

Usage:
    from core.filter_engine import FilterEngine, Filter

    engine = FilterEngine()

    # Add filters
    engine.add_filter(Filter('pe_ratio', '<', 15))
    engine.add_filter(Filter('dividend_yield', '>', 0.03))
    engine.add_filter(Filter('market_cap', '>=', 1e9))

    # Apply to search results (enriches with metrics and filters)
    filtered = engine.apply(results)

Version: 1.0
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from core.yahoo_metrics import fetch_metrics, METRIC_DEFS

logger = logging.getLogger(__name__)


@dataclass
class Filter:
    """A single numeric filter criterion."""

    metric: str      # Key from METRIC_DEFS (e.g., 'pe_ratio', 'market_cap')
    operator: str    # One of: '>', '<', '>=', '<=', '==', 'between'
    value: float     # Threshold value (or lower bound for 'between')
    value_upper: Optional[float] = None  # Upper bound (only for 'between')

    def matches(self, metric_value: Optional[float]) -> bool:
        """Check if a metric value passes this filter."""
        if metric_value is None:
            return False

        if self.operator == '>':
            return metric_value > self.value
        elif self.operator == '<':
            return metric_value < self.value
        elif self.operator == '>=':
            return metric_value >= self.value
        elif self.operator == '<=':
            return metric_value <= self.value
        elif self.operator == '==':
            return abs(metric_value - self.value) < 1e-9
        elif self.operator == 'between':
            if self.value_upper is None:
                return False
            return self.value <= metric_value <= self.value_upper
        else:
            logger.warning(f"Unknown operator: {self.operator}")
            return True  # Don't filter on unknown operators

    @property
    def display_name(self) -> str:
        """Human-readable description of this filter."""
        name = METRIC_DEFS.get(self.metric, (self.metric,))[0]
        if self.operator == 'between':
            return f"{name} {self.value}–{self.value_upper}"
        return f"{name} {self.operator} {self.value}"

    def __repr__(self):
        return f"Filter({self.display_name})"


class FilterEngine:
    """
    Composable filter engine for screening results.

    All filters are combined with AND logic — a result must pass
    every active filter to be included.
    """

    def __init__(self):
        self.filters: List[Filter] = []
        self._metrics_cache: Dict[str, Dict[str, Any]] = {}

    def add_filter(self, f: Filter):
        """Add a filter criterion."""
        self.filters.append(f)

    def remove_filter(self, index: int):
        """Remove filter by index."""
        if 0 <= index < len(self.filters):
            self.filters.pop(index)

    def clear_filters(self):
        """Remove all filters."""
        self.filters.clear()
        self._metrics_cache.clear()

    def has_filters(self) -> bool:
        """Check if any filters are active."""
        return len(self.filters) > 0

    def apply(self, results: list, progress_callback=None) -> list:
        """
        Apply all filters to search results.

        Fetches Yahoo metrics for each result's ticker, then filters
        based on all active criteria.

        Args:
            results: List of SearchResult objects (must have .ticker attribute)
            progress_callback: Optional callable(current, total, ticker)

        Returns:
            Filtered list of results (same type, preserving all attributes).
            Each result gets a `_yahoo_metrics` attribute with the fetched metrics.
        """
        if not self.filters:
            return results

        filtered = []
        total = len(results)

        for i, result in enumerate(results):
            ticker = result.ticker

            if progress_callback:
                progress_callback(i + 1, total, ticker)

            # Fetch metrics (with cache)
            if ticker not in self._metrics_cache:
                self._metrics_cache[ticker] = fetch_metrics(ticker)
            metrics = self._metrics_cache[ticker]

            # Attach metrics to result for display
            result._yahoo_metrics = metrics

            # Check all filters (AND logic)
            passes = True
            for f in self.filters:
                metric_value = metrics.get(f.metric)
                if not f.matches(metric_value):
                    passes = False
                    break

            if passes:
                filtered.append(result)

        logger.info(f"Filter: {len(filtered)}/{total} results passed "
                    f"({len(self.filters)} filters)")
        return filtered

    def get_active_filters_display(self) -> List[str]:
        """Get human-readable list of active filters."""
        return [f.display_name for f in self.filters]


# ============================================================================
# PRESET FILTERS
# ============================================================================

def value_screen() -> List[Filter]:
    """Classic value investing screen: low P/E, decent dividend."""
    return [
        Filter('pe_ratio', '<', 15),
        Filter('price_to_book', '<', 2),
        Filter('dividend_yield', '>', 0.02),
    ]


def growth_screen() -> List[Filter]:
    """Growth stock screen: strong revenue growth, high margins."""
    return [
        Filter('revenue_growth', '>', 0.15),
        Filter('gross_margin', '>', 0.40),
        Filter('market_cap', '>=', 1e9),
    ]


def quality_screen() -> List[Filter]:
    """Quality screen: high ROE, low debt, profitable."""
    return [
        Filter('roe', '>', 0.15),
        Filter('debt_to_equity', '<', 100),
        Filter('net_margin', '>', 0.10),
    ]


def dividend_screen() -> List[Filter]:
    """Dividend income screen."""
    return [
        Filter('dividend_yield', '>', 0.03),
        Filter('pe_ratio', '<', 25),
        Filter('debt_to_equity', '<', 150),
    ]
