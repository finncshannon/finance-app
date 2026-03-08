"""
Utility Functions for Stock Valuation System

Provides common helper functions for:
- Timestamp generation
- Safe mathematical operations
- Data formatting (currency, percentage)
- Growth rate calculations
- Logging configuration
- Excel workbook access

Used by: excel_integration.py, excel_writer.py, data_extractor.py, 
         market_implied_calculator.py, auto_detect_model.py
"""

import logging
import xlwings as xw
from datetime import datetime
import os
import sys


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Create logger for the application
logger = logging.getLogger('StockValuation')


def setup_logging(log_dir=None):
    """
    Configure comprehensive logging for the application.
    
    Sets up both file and console logging with appropriate formatting.
    Creates log directory if it doesn't exist.
    
    Args:
        log_dir (str): Directory for log files. If None, derives from config.LOG_DIR.

    Returns:
        logging.Logger: Configured logger object

    Example:
        >>> logger = setup_logging()
        >>> logger.info("System initialized")
    """
    try:
        if log_dir is None:
            import config
            log_dir = str(config.LOG_DIR)

        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log filename with date
        log_file = os.path.join(log_dir, f"valuation_{datetime.now().strftime('%Y%m%d')}.log")
        
        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Set logger level
        logger.setLevel(logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add formatter to handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Log initialization
        logger.info("=" * 70)
        logger.info("Stock Valuation System - Logging Initialized")
        logger.info(f"Log file: {log_file}")
        logger.info("=" * 70)
        
        return logger
        
    except Exception as e:
        # Fallback to basic console logging
        print(f"Warning: Could not set up file logging: {e}")
        print("Using console logging only")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        return logging.getLogger('StockValuation')


# ============================================================================
# TIMESTAMP FUNCTIONS
# ============================================================================

def get_timestamp():
    """
    Get current timestamp in standard format.
    
    Used throughout the system for:
    - Data extraction timestamps
    - Logging entries
    - Last refresh time tracking
    - Audit trails
    
    Returns:
        str: Formatted timestamp "YYYY-MM-DD HH:MM:SS"
        
    Examples:
        >>> get_timestamp()
        '2026-02-01 20:45:30'
        
        >>> timestamp = get_timestamp()
        >>> print(f"Data refreshed at {timestamp}")
        Data refreshed at 2026-02-01 20:45:30
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_date():
    """
    Get current date in standard format.
    
    Returns:
        str: Formatted date "YYYY-MM-DD"
        
    Example:
        >>> get_date()
        '2026-02-01'
    """
    return datetime.now().strftime("%Y-%m-%d")


# ============================================================================
# MATHEMATICAL FUNCTIONS
# ============================================================================

def safe_divide(numerator, denominator, default=0):
    """
    Safely divide two numbers with comprehensive error handling.
    
    Prevents ZeroDivisionError and handles None/invalid values gracefully.
    Critical for financial calculations where division by zero is common
    (e.g., margin calculations when revenue is zero).
    
    Args:
        numerator (float): Number to divide (top)
        denominator (float): Number to divide by (bottom)
        default (float): Value to return if division fails (default: 0)
        
    Returns:
        float: Result of division, or default if denominator is zero/None/invalid
        
    Examples:
        >>> safe_divide(100, 20)
        5.0
        
        >>> safe_divide(100, 0)
        0
        
        >>> safe_divide(100, 0, default=1)
        1
        
        >>> safe_divide(100, None, default=-1)
        -1
        
        >>> safe_divide(None, 50, default=0)
        0
        
        >>> safe_divide("100", "20")  # Handles string inputs
        5.0
    """
    try:
        # Check for None or zero denominator
        if denominator is None or denominator == 0:
            return default
        
        # Check for None numerator
        if numerator is None:
            return default
        
        # Perform division with type conversion
        return float(numerator) / float(denominator)
        
    except (TypeError, ZeroDivisionError, ValueError):
        return default


def calculate_growth_rate(current_value, previous_value):
    """
    Calculate growth rate between two values.
    
    Returns decimal growth rate (e.g., 0.15 for 15% growth, -0.10 for -10% decline)
    Handles edge cases like zero/None previous values.
    
    Args:
        current_value (float): Current period value
        previous_value (float): Previous period value
        
    Returns:
        float: Growth rate as decimal (0.15 = 15% growth)
        
    Examples:
        >>> calculate_growth_rate(115, 100)
        0.15
        
        >>> calculate_growth_rate(90, 100)
        -0.1
        
        >>> calculate_growth_rate(200, 100)
        1.0
        
        >>> calculate_growth_rate(100, 0)
        0.0
        
        >>> calculate_growth_rate(None, 100)
        0.0
        
        >>> calculate_growth_rate(100, None)
        0.0
    """
    # Handle None values
    if previous_value is None or previous_value == 0:
        return 0.0
    
    if current_value is None:
        return 0.0
    
    try:
        # Calculate growth rate
        # Use abs() on denominator to handle negative base values correctly
        return (float(current_value) - float(previous_value)) / abs(float(previous_value))
        
    except (TypeError, ZeroDivisionError, ValueError):
        return 0.0


def calculate_cagr(start_value, end_value, num_periods):
    """
    Calculate Compound Annual Growth Rate (CAGR).
    
    Args:
        start_value (float): Starting value
        end_value (float): Ending value
        num_periods (int): Number of periods
        
    Returns:
        float: CAGR as decimal (e.g., 0.15 for 15%)
        
    Examples:
        >>> calculate_cagr(100, 121, 2)
        0.1
        
        >>> calculate_cagr(100, 100, 5)
        0.0
    """
    try:
        if start_value is None or start_value <= 0:
            return 0.0
        
        if end_value is None or end_value <= 0:
            return 0.0
        
        if num_periods is None or num_periods <= 0:
            return 0.0
        
        # CAGR = (End/Start)^(1/periods) - 1
        cagr = (float(end_value) / float(start_value)) ** (1.0 / float(num_periods)) - 1.0
        
        return cagr
        
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_currency(value, decimals=2):
    """
    Format a numeric value as currency string with $ sign and commas.
    
    Used for displaying financial data in Excel and reports.
    Properly handles negative values with minus sign before dollar sign.
    
    Args:
        value (float): Numeric value to format
        decimals (int): Number of decimal places (default: 2)
        
    Returns:
        str: Formatted currency string
        
    Examples:
        >>> format_currency(1234.56)
        '$1,234.56'
        
        >>> format_currency(1234567.89)
        '$1,234,567.89'
        
        >>> format_currency(1000000, decimals=0)
        '$1,000,000'
        
        >>> format_currency(None)
        '$0.00'
        
        >>> format_currency(-500)
        '-$500.00'
        
        >>> format_currency(-1234.56)
        '-$1,234.56'
        
        >>> format_currency(0)
        '$0.00'
    """
    try:
        # Handle None
        if value is None:
            return "$0.00"
        
        # Convert to float
        value = float(value)
        
        # Handle negative values - minus sign before dollar sign
        if value < 0:
            return f"-${abs(value):,.{decimals}f}"
        
        # Positive values
        return f"${value:,.{decimals}f}"
        
    except (TypeError, ValueError):
        return "$0.00"


def format_percentage(value, decimals=1):
    """
    Format a decimal value as percentage string.
    
    Converts decimal to percentage (e.g., 0.15 → "15.0%")
    Used for displaying growth rates, margins, returns, etc.
    
    Args:
        value (float): Decimal value (e.g., 0.15 for 15%)
        decimals (int): Number of decimal places (default: 1)
        
    Returns:
        str: Formatted percentage string
        
    Examples:
        >>> format_percentage(0.15)
        '15.0%'
        
        >>> format_percentage(0.8523, decimals=2)
        '85.23%'
        
        >>> format_percentage(-0.05)
        '-5.0%'
        
        >>> format_percentage(None)
        '0.0%'
        
        >>> format_percentage(1.5, decimals=0)
        '150%'
        
        >>> format_percentage(0)
        '0.0%'
    """
    try:
        # Handle None
        if value is None:
            return "0.0%"
        
        # Convert to float and multiply by 100
        percentage = float(value) * 100
        
        # Format with specified decimals
        return f"{percentage:.{decimals}f}%"
        
    except (TypeError, ValueError):
        return "0.0%"


def format_number(value, decimals=2):
    """
    Format number with comma separators.
    
    Args:
        value (float): Numeric value
        decimals (int): Number of decimal places (default: 2)
        
    Returns:
        str: Formatted number (e.g., "1,234.56")
        
    Examples:
        >>> format_number(1234.56)
        '1,234.56'
        
        >>> format_number(1000000, decimals=0)
        '1,000,000'
    """
    try:
        if value is None:
            return "0.00"
        
        value = float(value)
        return f"{value:,.{decimals}f}"
        
    except (TypeError, ValueError):
        return "0.00"


# ============================================================================
# EXCEL WORKBOOK ACCESS
# ============================================================================

def get_workbook():
    """
    Get the active xlwings workbook.
    
    Provides centralized access to the Excel workbook for all modules.
    Includes error handling for cases where no workbook is active.
    
    Returns:
        xlwings.Book: Active workbook object
        
    Raises:
        Exception: If no active workbook found
        
    Example:
        >>> wb = get_workbook()
        >>> print(wb.name)
        'MasterValuation_8Scenarios.xlsm'
        
        >>> # Use in other functions
        >>> def write_data():
        ...     wb = get_workbook()
        ...     wb.sheets['Home'].range('A1').value = 'Hello'
    """
    try:
        wb = xw.books.active
        if wb is None:
            raise Exception("No active Excel workbook found")
        return wb
    except Exception as e:
        logger.error(f"Cannot get workbook: {e}")
        raise


# ============================================================================
# LOGGING HELPER FUNCTIONS
# ============================================================================

def log_info(message):
    """
    Log info message to both file and console.
    
    Args:
        message (str): Message to log
    """
    logger.info(message)


def log_warning(message):
    """
    Log warning message to both file and console.
    
    Args:
        message (str): Warning message to log
    """
    logger.warning(message)


def log_error(context, ticker, message, details=''):
    """
    Log error message with context.
    
    Args:
        context (str): Context where error occurred (e.g., 'EXCEL_WRITE', 'DATA_EXTRACTION')
        ticker (str): Stock ticker being processed
        message (str): Error message
        details (str): Additional details (optional)
    """
    full_message = f"[{context}] {ticker}: {message}"
    if details:
        full_message += f" - {details}"
    
    logger.error(full_message)


# ============================================================================
# DATA VALIDATION
# ============================================================================

def is_valid_number(value):
    """
    Check if value can be converted to a valid number.
    
    Args:
        value: Value to check
        
    Returns:
        bool: True if valid number, False otherwise
        
    Examples:
        >>> is_valid_number(123)
        True
        
        >>> is_valid_number("123.45")
        True
        
        >>> is_valid_number(None)
        False
        
        >>> is_valid_number("abc")
        False
    """
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def clean_numeric_value(value, default=0):
    """
    Clean and convert value to number, returning default if invalid.
    
    Removes common string artifacts like $, commas, etc.
    
    Args:
        value: Value to clean
        default: Default value if conversion fails
        
    Returns:
        float: Cleaned numeric value
        
    Examples:
        >>> clean_numeric_value("$1,234.56")
        1234.56
        
        >>> clean_numeric_value("15%")
        15.0
        
        >>> clean_numeric_value(None, default=-1)
        -1
    """
    try:
        if value is None or value == '':
            return default
        
        # If already a number, return it
        if isinstance(value, (int, float)):
            return float(value)
        
        # Clean string artifacts
        if isinstance(value, str):
            value = value.strip()
            value = value.replace('$', '')
            value = value.replace(',', '')
            value = value.replace('%', '')
        
        return float(value)
        
    except (TypeError, ValueError):
        return default


# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize logging when module is imported
try:
    setup_logging()
except Exception as e:
    print(f"Warning: Could not set up logging: {e}")
    print("Continuing with basic console logging")


# ============================================================================
# MODULE METADATA
# ============================================================================

__version__ = '2.1'
__author__ = 'Stock Valuation System'
__all__ = [
    # Timestamp functions
    'get_timestamp',
    'get_date',
    
    # Mathematical functions
    'safe_divide',
    'calculate_growth_rate',
    'calculate_cagr',
    
    # Formatting functions
    'format_currency',
    'format_percentage',
    'format_number',
    
    # Excel functions
    'get_workbook',
    
    # Logging functions
    'setup_logging',
    'log_info',
    'log_warning',
    'log_error',
    
    # Validation functions
    'is_valid_number',
    'clean_numeric_value',
]