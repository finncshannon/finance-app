"""
Theme constants for the Company Intelligence Screener.
Same dark theme as Diagnostic GUI for visual consistency.
"""

# Window
WINDOW_TITLE = "StockValuation - Company Intelligence Screener"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800

# Colors -- Dark theme (matches Diagnostic GUI)
BG_DARK = '#1a1a2e'
BG_PANEL = '#16213e'
BG_SIDEBAR = '#0f3460'
BG_INPUT = '#0d1b2a'
BG_BUTTON = '#533483'
BG_BUTTON_HOVER = '#7c3aed'
BG_BUTTON_ACTIVE = '#6d28d9'
TEXT_PRIMARY = '#e2e8f0'
TEXT_SECONDARY = '#94a3b8'
TEXT_HEADING = '#f8fafc'
TEXT_ACCENT = '#a78bfa'

# Match score colors
SCORE_HIGH = '#22c55e'       # Green (80%+)
SCORE_MEDIUM = '#eab308'     # Yellow (50-80%)
SCORE_LOW = '#f97316'        # Orange (20-50%)
SCORE_MINIMAL = '#ef4444'    # Red (<20%)

# Model fit colors
FIT_YES = '#22c55e'          # Green
FIT_NO = '#ef4444'           # Red
FIT_PARTIAL = '#eab308'      # Yellow

# Status colors
COLOR_SUCCESS = '#22c55e'
COLOR_WARNING = '#eab308'
COLOR_ERROR = '#ef4444'
COLOR_INFO = '#3b82f6'

# Fonts
FONT_HEADING = ('Segoe UI', 16, 'bold')
FONT_SUBHEADING = ('Segoe UI', 12, 'bold')
FONT_BODY = ('Segoe UI', 10)
FONT_BODY_BOLD = ('Segoe UI', 10, 'bold')
FONT_SMALL = ('Segoe UI', 9)
FONT_MONO = ('Consolas', 9)
FONT_MONO_SMALL = ('Consolas', 8)
FONT_BUTTON = ('Segoe UI', 10, 'bold')
FONT_BIG_NUMBER = ('Segoe UI', 28, 'bold')

# Padding
PAD_SMALL = 5
PAD_MEDIUM = 10
PAD_LARGE = 20

# Table
ROW_HEIGHT = 28
HEADER_BG = '#1e293b'
ROW_ALT_BG = '#1e2a4a'
ROW_SELECTED = '#334155'


def score_color(score: float) -> str:
    """Return color for a match score (0-100)."""
    if score >= 80:
        return SCORE_HIGH
    if score >= 50:
        return SCORE_MEDIUM
    if score >= 20:
        return SCORE_LOW
    return SCORE_MINIMAL
