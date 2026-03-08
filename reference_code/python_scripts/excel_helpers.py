"""
Excel Helper Functions - Shared Utilities

Canonical implementations of named range access and DataFrame value extraction.
Used by: excel_writer.py, excel_integration.py, excel_writer_batch.py,
         market_implied_calculator.py, auto_detect_model.py

Version: 1.0
"""

import xlwings as xw
import pandas as pd
from typing import Any
import logging

logger = logging.getLogger('StockValuation')


# ============================================================================
# FORMULA PROTECTION
# ============================================================================

def cell_has_formula(wb: xw.Book, range_name: str) -> bool:
    """
    Check if the target cell of a named range contains a formula.

    Returns True if the cell has a formula (starts with '='), False otherwise.
    Returns False on any error (safe to proceed with write).
    """
    try:
        cell = wb.names[range_name].refers_to_range
        formula = cell.formula
        if isinstance(formula, str) and formula.startswith('='):
            return True
        return False
    except Exception as e:
        logger.debug(f"cell_has_formula check failed for '{range_name}': {e}")
        return False


# ============================================================================
# NAMED RANGE ACCESS
# ============================================================================

def get_named_range_value(wb: xw.Book, range_name: str, default: Any = '') -> Any:
    """
    Safely get value from named range with multiple fallback methods.

    Tries in order:
    1. Bracket notation (wb.names['range'])
    2. Parentheses notation (wb.names('range'))
    3. Workbook-level range resolution (wb.range('range'))

    Args:
        wb: xlwings Workbook object
        range_name: Name of the named range
        default: Default value if range not found

    Returns:
        Value from named range or default
    """
    # Method 1: Bracket syntax
    try:
        return wb.names[range_name].refers_to_range.value
    except Exception:
        pass

    # Method 2: Parentheses syntax
    try:
        return wb.names(range_name).refers_to_range.value
    except Exception:
        pass

    # Method 3: Workbook-level range resolution (no sheet assumption)
    try:
        return wb.range(range_name).value
    except Exception:
        pass

    logger.debug(f"Named range '{range_name}' not found, using default: {default}")
    return default


def set_named_range_value(wb: xw.Book, range_name: str, value: Any) -> bool:
    """
    Safely set value to named range with multiple fallback methods.
    Skips write if the target cell contains a formula (protects user formulas).

    Args:
        wb: xlwings Workbook object
        range_name: Name of the named range
        value: Value to set

    Returns:
        True if successful, False otherwise
    """
    # Formula protection: never overwrite a cell that contains a formula
    if cell_has_formula(wb, range_name):
        logger.warning(f"Skipping '{range_name}': cell contains a formula")
        return False

    # Method 1: Parentheses syntax (most reliable for writing)
    try:
        wb.names(range_name).refers_to_range.value = value
        return True
    except Exception:
        pass

    # Method 2: Workbook-level range resolution (no sheet assumption)
    try:
        wb.range(range_name).value = value
        return True
    except Exception:
        pass

    # Method 3: Bracket syntax
    try:
        wb.names[range_name].refers_to_range.value = value
        return True
    except Exception:
        pass

    logger.warning(f"Could not set named range '{range_name}' to value: {value}")
    return False


# ============================================================================
# DATAFRAME VALUE EXTRACTION
# ============================================================================

def get_df_value(df: pd.DataFrame, row_name: str, col_index: int = 0, default: Any = 0) -> Any:
    """
    Extract value from DataFrame by row name and column index.

    Tries exact match first, then case-insensitive match.

    Args:
        df: DataFrame to search (e.g. income_statement, balance_sheet)
        row_name: Row label to find (e.g. 'Total Revenue', 'Net Income')
        col_index: Column index, 0 = most recent period
        default: Value to return if not found

    Returns:
        Extracted value or default
    """
    if df is None or df.empty:
        return default

    try:
        # Try exact match first
        if row_name in df.index:
            if col_index < len(df.columns):
                val = df.loc[row_name].iloc[col_index]
                return val if pd.notna(val) else default

        # Try case-insensitive match
        for idx in df.index:
            if str(idx).lower() == row_name.lower():
                if col_index < len(df.columns):
                    val = df.loc[idx].iloc[col_index]
                    return val if pd.notna(val) else default

        return default

    except (KeyError, IndexError, TypeError, ValueError):
        return default
