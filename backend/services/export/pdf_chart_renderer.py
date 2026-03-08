import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

BLUE = '#3B82F6'
RED = '#EF4444'
GREEN = '#10B981'
GRAY = '#6B7280'
DARK = '#1F2937'

def render_waterfall_chart(steps, width=6, height=3.5):
    """Render DCF waterfall chart as PNG bytes."""
    if not steps:
        return _empty_chart(width, height, "No waterfall data")

    labels = [s.get('label', '') for s in steps]
    values = [s.get('value', 0) for s in steps]
    types = [s.get('step_type', 'addition') for s in steps]

    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    running = 0
    bottoms = []
    bar_values = []
    bar_colors = []

    for val, st in zip(values, types):
        if st in ('start', 'subtotal', 'end'):
            bottoms.append(0)
            bar_values.append(val)
            bar_colors.append(DARK if st != 'end' else BLUE)
            running = val
        elif st == 'addition':
            bottoms.append(running)
            bar_values.append(val)
            bar_colors.append(GREEN)
            running += val
        elif st == 'subtraction':
            running += val  # val is negative
            bottoms.append(running)
            bar_values.append(abs(val))
            bar_colors.append(RED)

    x = range(len(labels))
    bars = ax.bar(x, bar_values, bottom=bottoms, color=bar_colors, width=0.6, edgecolor='white', linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=7, color=GRAY)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1e9:.1f}B" if abs(v) >= 1e9 else f"${v/1e6:.0f}M"))
    ax.tick_params(axis='y', labelsize=7, colors=GRAY)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.grid(axis='y', color='#E5E7EB', linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#FFFFFF')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def render_football_field(ranges, current_price, width=6, height=2.5):
    """Render football field chart as PNG bytes."""
    if not ranges:
        return _empty_chart(width, height, "No range data")

    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    y_positions = list(range(len(ranges)))
    labels = []

    for i, r in enumerate(ranges):
        method = r.get('method', f'Method {i}')
        low = r.get('low', 0)
        mid = r.get('mid', 0)
        high = r.get('high', 0)
        labels.append(method)

        ax.barh(i, high - low, left=low, height=0.4, color=BLUE, alpha=0.3, edgecolor=BLUE, linewidth=0.5)
        ax.plot(mid, i, 'o', color=BLUE, markersize=6)

    # Current price line
    ax.axvline(x=current_price, color=RED, linewidth=1.5, linestyle='--', label=f'Current: ${current_price:.2f}')

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=8, color=GRAY)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.tick_params(axis='x', labelsize=7, colors=GRAY)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.legend(fontsize=7, frameon=False)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#FFFFFF')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def render_sensitivity_heatmap(grid, row_labels, col_labels, width=5, height=4):
    """Render 2D sensitivity table as heatmap PNG."""
    if not grid:
        return _empty_chart(width, height, "No sensitivity data")

    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    data = np.array(grid)
    im = ax.imshow(data, cmap='RdYlGn', aspect='auto')

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels([f"{v*100:.1f}%" if isinstance(v, float) else str(v) for v in col_labels], fontsize=7, rotation=45)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels([f"{v*100:.1f}%" if isinstance(v, float) else str(v) for v in row_labels], fontsize=7)

    for i in range(len(row_labels)):
        for j in range(len(col_labels)):
            ax.text(j, i, f"${data[i, j]:,.0f}", ha='center', va='center', fontsize=6, color=DARK)

    ax.set_xlabel("Terminal Growth", fontsize=8, color=GRAY)
    ax.set_ylabel("WACC", fontsize=8, color=GRAY)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#FFFFFF')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def _empty_chart(width, height, message):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=10, color=GRAY)
    ax.axis('off')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#FFFFFF')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()
