from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import TableStyle

# Colors
PRIMARY = colors.HexColor('#1F2937')
SECONDARY = colors.HexColor('#6B7280')
ACCENT = colors.HexColor('#3B82F6')
POSITIVE = colors.HexColor('#10B981')
NEGATIVE = colors.HexColor('#EF4444')
BG_LIGHT = colors.HexColor('#F9FAFB')
BORDER = colors.HexColor('#E5E7EB')

HEADER_TABLE_STYLE = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
    ('TEXTCOLOR', (0, 0), (-1, 0), PRIMARY),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 8),
    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
    ('FONTNAME', (1, 1), (-1, -1), 'Courier'),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
])

SIMPLE_TABLE_STYLE = TableStyle([
    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ('TOPPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER),
])

def fmt_currency(val):
    if val is None: return '--'
    if abs(val) >= 1e9: return f"${val/1e9:,.1f}B"
    if abs(val) >= 1e6: return f"${val/1e6:,.1f}M"
    return f"${val:,.0f}"

def fmt_pct(val):
    if val is None: return '--'
    return f"{val*100:.1f}%"

def fmt_multiple(val):
    if val is None: return '--'
    return f"{val:.1f}x"

def fmt_price(val):
    if val is None: return '--'
    return f"${val:,.2f}"
