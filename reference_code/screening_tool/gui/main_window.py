"""
Main application window for the Company Intelligence Screener.

Layout:
    +----------------------------------------------------------+
    |  [Title Bar]          [Refresh Data] [Export]             |
    +----------------------------------------------------------+
    |  Search: [___________________________]  Sector: [v]      |
    |  [Search]                                                 |
    +----------------------------------------------------------+
    |  Results Table                                            |
    |  Ticker | Company | Match% | Sector | Keywords | Model   |
    |  ...                                                      |
    +----------------------------------------------------------+
    |  Detail Panel (selected company)                          |
    |  Business excerpt, matched keywords, financials, model fit|
    +----------------------------------------------------------+
    |  Log Panel                                                |
    +----------------------------------------------------------+
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import List, Optional

from gui.styles import *
from gui.log_panel import LogPanel
from core.filter_engine import FilterEngine, Filter
from core.filter_engine import value_screen, growth_screen, quality_screen, dividend_screen
from core.yahoo_metrics import METRIC_DEFS
from core.settings import get_setting, set_setting


class MainWindow:
    """Main screener application window."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=BG_DARK)

        # Center on screen
        w, h = 1300, 850
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f'{w}x{h}+{x}+{y}')

        # State
        self.search_results = []
        self.universe = []
        self._runner_lock = threading.Lock()
        self._is_running = False
        self.filter_engine = FilterEngine()
        self._filter_panel_visible = False

        # Lazy-loaded core modules
        self._client = None
        self._store = None
        self._universe_mgr = None
        self._engine = None
        self._xbrl = None
        self._checker = None
        self._fetcher = None
        self._parser = None

        # Build UI
        self._build_layout()

        # Load universe on startup
        self.root.after(100, self._load_universe_async)

    # ----------------------------------------------------------------
    # Core module lazy initialization
    # ----------------------------------------------------------------

    def _init_core(self):
        """Initialize core modules (lazy, first use)."""
        if self._client is not None:
            return

        from core.sec_client import SECClient
        from core.company_store import CompanyStore
        from core.universe import UniverseManager
        from core.search_engine import SearchEngine
        from core.xbrl_parser import XBRLParser
        from core.model_checker import ModelChecker
        from core.filing_fetcher import FilingFetcher
        from core.filing_parser import FilingParser
        from core.settings import get_sec_email

        email = get_sec_email() or "stockvaluation@users.local"

        self._client = SECClient(contact_email=email)
        self._store = CompanyStore()
        self._universe_mgr = UniverseManager(self._client)
        self._engine = SearchEngine(self._store)
        self._xbrl = XBRLParser(self._client)
        self._checker = ModelChecker()
        self._fetcher = FilingFetcher(self._client)
        self._parser = FilingParser()

    # ----------------------------------------------------------------
    # Layout
    # ----------------------------------------------------------------

    def _build_layout(self):
        """Build the main UI layout."""
        # Top bar
        self._build_top_bar()

        # Search bar
        self._build_search_bar()

        # Filter panel (collapsible)
        self._build_filter_panel()

        # Main content: results table + detail panel (PanedWindow)
        paned = tk.PanedWindow(
            self.root, orient='vertical', bg=BG_DARK,
            sashwidth=4, sashrelief='flat',
        )
        paned.pack(fill='both', expand=True, padx=PAD_MEDIUM, pady=(0, PAD_SMALL))

        # Results table
        self.results_frame = tk.Frame(paned, bg=BG_DARK)
        self._build_results_table(self.results_frame)
        paned.add(self.results_frame, minsize=200)

        # Detail + Log panel
        bottom_frame = tk.Frame(paned, bg=BG_DARK)
        paned.add(bottom_frame, minsize=150)

        # Detail panel
        self.detail_frame = tk.Frame(bottom_frame, bg=BG_PANEL)
        self.detail_frame.pack(fill='both', expand=True, pady=(0, PAD_SMALL))
        self._build_detail_panel(self.detail_frame)

        # Log panel
        self.log_panel = LogPanel(bottom_frame, height=6)
        self.log_panel.pack(fill='x')

    def _build_top_bar(self):
        """Build the top title bar with action buttons and universe controls."""
        top = tk.Frame(self.root, bg=BG_SIDEBAR, height=50)
        top.pack(fill='x')
        top.pack_propagate(False)

        # Title
        tk.Label(
            top, text="Company Intelligence Screener",
            font=FONT_HEADING, bg=BG_SIDEBAR, fg=TEXT_HEADING,
        ).pack(side='left', padx=PAD_LARGE)

        # Buttons (right side)
        btn_frame = tk.Frame(top, bg=BG_SIDEBAR)
        btn_frame.pack(side='right', padx=PAD_LARGE)

        self.refresh_btn = tk.Button(
            btn_frame, text="Refresh Data", font=FONT_BUTTON,
            bg=BG_BUTTON, fg=TEXT_PRIMARY, relief='flat', cursor='hand2',
            padx=12, pady=4,
            command=self._on_refresh_data,
        )
        self.refresh_btn.pack(side='left', padx=PAD_SMALL)

        self.export_btn = tk.Button(
            btn_frame, text="Export Excel", font=FONT_BUTTON,
            bg=BG_BUTTON, fg=TEXT_PRIMARY, relief='flat', cursor='hand2',
            padx=12, pady=4, state='disabled',
            command=self._on_export,
        )
        self.export_btn.pack(side='left', padx=PAD_SMALL)

        # Universe controls (center area)
        universe_frame = tk.Frame(top, bg=BG_SIDEBAR)
        universe_frame.pack(side='left', padx=PAD_LARGE)

        tk.Label(
            universe_frame, text="Universe:", font=FONT_SMALL,
            bg=BG_SIDEBAR, fg=TEXT_SECONDARY,
        ).pack(side='left', padx=(0, 4))

        # Universe mode dropdown
        saved_mode = get_setting("universe_mode", "sp500")
        mode_display_map = {
            "sp500": "S&P 500",
            "sp500_plus_custom": "S&P 500 + Custom",
            "custom": "Custom Only",
        }
        self._universe_mode_var = tk.StringVar(
            value=mode_display_map.get(saved_mode, "S&P 500"))
        self._universe_mode_combo = ttk.Combobox(
            universe_frame, textvariable=self._universe_mode_var,
            values=["S&P 500", "S&P 500 + Custom", "Custom Only"],
            state='readonly', width=16, font=FONT_SMALL,
        )
        self._universe_mode_combo.pack(side='left', padx=(0, PAD_SMALL))
        self._universe_mode_combo.bind(
            '<<ComboboxSelected>>', self._on_universe_mode_change)

        # Add ticker entry
        self._custom_ticker_var = tk.StringVar()
        self._custom_ticker_entry = tk.Entry(
            universe_frame, textvariable=self._custom_ticker_var,
            font=FONT_SMALL, bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief='flat', width=8,
        )
        self._custom_ticker_entry.pack(side='left', padx=(0, 2), ipady=2)
        self._custom_ticker_entry.bind('<Return>', lambda e: self._on_add_ticker())

        tk.Button(
            universe_frame, text="+Add", font=FONT_SMALL,
            bg=BG_BUTTON, fg=TEXT_PRIMARY, relief='flat', cursor='hand2',
            padx=6, pady=1,
            command=self._on_add_ticker,
        ).pack(side='left', padx=(0, 2))

        tk.Button(
            universe_frame, text="Load File", font=FONT_SMALL,
            bg=BG_BUTTON, fg=TEXT_PRIMARY, relief='flat', cursor='hand2',
            padx=6, pady=1,
            command=self._on_load_ticker_file,
        ).pack(side='left', padx=(0, PAD_SMALL))

        # Custom ticker count label
        self._custom_count_label = tk.Label(
            universe_frame, text="", font=FONT_SMALL,
            bg=BG_SIDEBAR, fg=TEXT_ACCENT,
        )
        self._custom_count_label.pack(side='left', padx=(0, PAD_SMALL))
        self._update_custom_count_label()

        # Status label
        self.status_label = tk.Label(
            top, text="", font=FONT_SMALL,
            bg=BG_SIDEBAR, fg=TEXT_ACCENT,
        )
        self.status_label.pack(side='right', padx=PAD_MEDIUM)

    def _build_search_bar(self):
        """Build the search input area."""
        search_frame = tk.Frame(self.root, bg=BG_PANEL, height=60)
        search_frame.pack(fill='x', padx=PAD_MEDIUM, pady=PAD_SMALL)

        inner = tk.Frame(search_frame, bg=BG_PANEL)
        inner.pack(fill='x', padx=PAD_MEDIUM, pady=PAD_SMALL)

        # Search label + entry
        tk.Label(
            inner, text="Search:", font=FONT_BODY_BOLD,
            bg=BG_PANEL, fg=TEXT_PRIMARY,
        ).pack(side='left', padx=(0, PAD_SMALL))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            inner, textvariable=self.search_var,
            font=FONT_BODY, bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            selectbackground='#334155', selectforeground=TEXT_PRIMARY,
            relief='flat', width=50,
        )
        self.search_entry.pack(side='left', padx=PAD_SMALL, ipady=4)
        self.search_entry.bind('<Return>', lambda e: self._on_search())

        # Sector filter
        tk.Label(
            inner, text="Sector:", font=FONT_BODY_BOLD,
            bg=BG_PANEL, fg=TEXT_PRIMARY,
        ).pack(side='left', padx=(PAD_LARGE, PAD_SMALL))

        self.sector_var = tk.StringVar(value="All")
        self.sector_combo = ttk.Combobox(
            inner, textvariable=self.sector_var,
            values=["All", "Communication Services", "Consumer Discretionary",
                    "Consumer Staples", "Energy", "Financials", "Health Care",
                    "Industrials", "Information Technology", "Materials",
                    "Real Estate", "Utilities"],
            state='readonly', width=22, font=FONT_SMALL,
        )
        self.sector_combo.pack(side='left', padx=PAD_SMALL)

        # Filing type checkboxes
        filing_frame = tk.Frame(inner, bg=BG_PANEL)
        filing_frame.pack(side='left', padx=(PAD_LARGE, 0))

        tk.Label(
            filing_frame, text="Filings:", font=FONT_SMALL,
            bg=BG_PANEL, fg=TEXT_SECONDARY,
        ).pack(side='left', padx=(0, 2))

        self._ft_10k_var = tk.BooleanVar(value=True)
        self._ft_10q_var = tk.BooleanVar(value=False)
        self._ft_8k_var = tk.BooleanVar(value=False)

        for label, var in [("10-K", self._ft_10k_var),
                           ("10-Q", self._ft_10q_var),
                           ("8-K", self._ft_8k_var)]:
            tk.Checkbutton(
                filing_frame, text=label, variable=var,
                font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_PRIMARY,
                selectcolor=BG_DARK, activebackground=BG_PANEL,
                activeforeground=TEXT_PRIMARY,
            ).pack(side='left', padx=1)

        # Search button
        self.search_btn = tk.Button(
            inner, text="Search", font=FONT_BUTTON,
            bg=BG_BUTTON, fg=TEXT_PRIMARY, relief='flat', cursor='hand2',
            padx=16, pady=2,
            command=self._on_search,
        )
        self.search_btn.pack(side='left', padx=PAD_MEDIUM)

        # Results count
        self.results_label = tk.Label(
            inner, text="", font=FONT_SMALL,
            bg=BG_PANEL, fg=TEXT_SECONDARY,
        )
        self.results_label.pack(side='right', padx=PAD_SMALL)

    def _build_filter_panel(self):
        """Build a collapsible financial filter panel."""
        # Toggle button in search area
        # Container frame
        self.filter_container = tk.Frame(self.root, bg=BG_PANEL)
        # Hidden by default — don't pack

        # Toggle button (placed after search bar)
        self.filter_toggle_btn = tk.Button(
            self.root, text="Filters ▼", font=FONT_SMALL,
            bg=BG_PANEL, fg=TEXT_ACCENT, relief='flat', cursor='hand2',
            command=self._toggle_filter_panel,
        )
        self.filter_toggle_btn.pack(fill='x', padx=PAD_MEDIUM)

        # Inner content
        inner = tk.Frame(self.filter_container, bg=BG_PANEL)
        inner.pack(fill='x', padx=PAD_MEDIUM, pady=PAD_SMALL)

        # Preset buttons row
        preset_frame = tk.Frame(inner, bg=BG_PANEL)
        preset_frame.pack(fill='x', pady=(0, PAD_SMALL))

        tk.Label(
            preset_frame, text="Presets:", font=FONT_SMALL,
            bg=BG_PANEL, fg=TEXT_SECONDARY,
        ).pack(side='left', padx=(0, PAD_SMALL))

        for label, preset_fn in [
            ("Value", value_screen),
            ("Growth", growth_screen),
            ("Quality", quality_screen),
            ("Dividend", dividend_screen),
        ]:
            tk.Button(
                preset_frame, text=label, font=FONT_SMALL,
                bg=BG_SIDEBAR, fg=TEXT_PRIMARY, relief='flat', cursor='hand2',
                padx=8, pady=1,
                command=lambda fn=preset_fn: self._apply_preset(fn),
            ).pack(side='left', padx=2)

        tk.Button(
            preset_frame, text="Clear All", font=FONT_SMALL,
            bg=BG_DARK, fg=TEXT_SECONDARY, relief='flat', cursor='hand2',
            padx=8, pady=1,
            command=self._clear_filters,
        ).pack(side='left', padx=(PAD_MEDIUM, 0))

        # Add filter row
        add_frame = tk.Frame(inner, bg=BG_PANEL)
        add_frame.pack(fill='x', pady=(0, PAD_SMALL))

        # Metric dropdown
        metric_options = [(k, v[0]) for k, v in METRIC_DEFS.items()]
        self._filter_metric_var = tk.StringVar(value=metric_options[0][0])
        metric_display = [f"{v[0]} ({k})" for k, v in METRIC_DEFS.items()]
        self._filter_metric_combo = ttk.Combobox(
            add_frame, values=metric_display,
            state='readonly', width=20, font=FONT_SMALL,
        )
        self._filter_metric_combo.current(0)
        self._filter_metric_combo.pack(side='left', padx=(0, PAD_SMALL))

        # Operator dropdown
        self._filter_op_var = tk.StringVar(value='>')
        op_combo = ttk.Combobox(
            add_frame, textvariable=self._filter_op_var,
            values=['>', '<', '>=', '<=', '==', 'between'],
            state='readonly', width=8, font=FONT_SMALL,
        )
        op_combo.pack(side='left', padx=(0, PAD_SMALL))

        # Value entry
        self._filter_value_var = tk.StringVar()
        tk.Entry(
            add_frame, textvariable=self._filter_value_var,
            font=FONT_SMALL, bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief='flat', width=12,
        ).pack(side='left', padx=(0, PAD_SMALL), ipady=2)

        # Add button
        tk.Button(
            add_frame, text="+ Add Filter", font=FONT_SMALL,
            bg=BG_BUTTON, fg=TEXT_PRIMARY, relief='flat', cursor='hand2',
            padx=8, pady=1,
            command=self._add_filter_from_ui,
        ).pack(side='left', padx=PAD_SMALL)

        # Active filters display
        self.filter_list_frame = tk.Frame(inner, bg=BG_PANEL)
        self.filter_list_frame.pack(fill='x')

        # Active filters label
        self.filter_status_label = tk.Label(
            inner, text="No active filters", font=FONT_SMALL,
            bg=BG_PANEL, fg=TEXT_SECONDARY,
        )
        self.filter_status_label.pack(anchor='w')

    def _toggle_filter_panel(self):
        """Show/hide the filter panel."""
        if self._filter_panel_visible:
            self.filter_container.pack_forget()
            self.filter_toggle_btn.configure(text="Filters ▼")
            self._filter_panel_visible = False
        else:
            # Pack filter container right after toggle button
            self.filter_container.pack(
                fill='x', padx=PAD_MEDIUM, pady=(0, PAD_SMALL),
                after=self.filter_toggle_btn,
            )
            self.filter_toggle_btn.configure(text="Filters ▲")
            self._filter_panel_visible = True

    def _add_filter_from_ui(self):
        """Add a filter from the UI controls."""
        # Get selected metric key from combo display text
        combo_idx = self._filter_metric_combo.current()
        metric_keys = list(METRIC_DEFS.keys())
        if combo_idx < 0 or combo_idx >= len(metric_keys):
            return
        metric_key = metric_keys[combo_idx]

        op = self._filter_op_var.get()
        value_str = self._filter_value_var.get().strip()
        if not value_str:
            return

        try:
            value = float(value_str)
        except ValueError:
            self.log_panel.append(f"Invalid filter value: {value_str}", 'error')
            return

        f = Filter(metric_key, op, value)
        self.filter_engine.add_filter(f)
        self._filter_value_var.set('')
        self._refresh_filter_display()

    def _apply_preset(self, preset_fn):
        """Apply a preset filter set."""
        self.filter_engine.clear_filters()
        for f in preset_fn():
            self.filter_engine.add_filter(f)
        self._refresh_filter_display()

    def _clear_filters(self):
        """Clear all active filters."""
        self.filter_engine.clear_filters()
        self._refresh_filter_display()

    def _remove_filter(self, index: int):
        """Remove a filter by index."""
        self.filter_engine.remove_filter(index)
        self._refresh_filter_display()

    def _refresh_filter_display(self):
        """Update the active filters display."""
        # Clear existing filter chips
        for widget in self.filter_list_frame.winfo_children():
            widget.destroy()

        if not self.filter_engine.has_filters():
            self.filter_status_label.configure(text="No active filters")
            return

        # Show filter chips
        for i, f in enumerate(self.filter_engine.filters):
            chip = tk.Frame(self.filter_list_frame, bg=BG_SIDEBAR, padx=4, pady=1)
            chip.pack(side='left', padx=2, pady=2)
            tk.Label(
                chip, text=f.display_name, font=FONT_SMALL,
                bg=BG_SIDEBAR, fg=TEXT_PRIMARY,
            ).pack(side='left')
            tk.Button(
                chip, text="×", font=FONT_SMALL,
                bg=BG_SIDEBAR, fg=TEXT_SECONDARY, relief='flat',
                cursor='hand2', padx=2, pady=0,
                command=lambda idx=i: self._remove_filter(idx),
            ).pack(side='left')

        count = len(self.filter_engine.filters)
        self.filter_status_label.configure(
            text=f"{count} active filter{'s' if count != 1 else ''}"
        )

    def _build_results_table(self, parent):
        """Build the results Treeview table."""
        columns = ("ticker", "company", "score", "hits", "sector", "keywords", "model", "revenue", "pe", "mktcap")
        self.tree = ttk.Treeview(
            parent, columns=columns, show='headings',
            selectmode='browse', height=12,
        )

        # Column definitions
        col_config = [
            ("ticker",   "Ticker",   70,  'w'),
            ("company",  "Company",  180, 'w'),
            ("score",    "Match%",   65,  'center'),
            ("hits",     "Hits",     45,  'center'),
            ("sector",   "Sector",   120, 'w'),
            ("keywords", "Keywords", 170, 'w'),
            ("model",    "Model Fit", 100, 'w'),
            ("revenue",  "Revenue",  80,  'e'),
            ("pe",       "P/E",      55,  'e'),
            ("mktcap",   "Mkt Cap",  75,  'e'),
        ]

        for col_id, heading, width, anchor in col_config:
            self.tree.heading(col_id, text=heading,
                              command=lambda c=col_id: self._sort_column(c))
            self.tree.column(col_id, width=width, anchor=anchor)

        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient='vertical',
                                   command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Selection handler
        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # Style the treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview',
                         background=BG_DARK,
                         foreground=TEXT_PRIMARY,
                         fieldbackground=BG_DARK,
                         font=FONT_SMALL,
                         rowheight=ROW_HEIGHT)
        style.configure('Treeview.Heading',
                         background=HEADER_BG,
                         foreground=TEXT_HEADING,
                         font=FONT_BODY_BOLD)
        style.map('Treeview',
                   background=[('selected', ROW_SELECTED)],
                   foreground=[('selected', TEXT_HEADING)])

    def _build_detail_panel(self, parent):
        """Build the detail panel for selected company."""
        # Title
        self.detail_title = tk.Label(
            parent, text="Select a result to see details",
            font=FONT_SUBHEADING, bg=BG_PANEL, fg=TEXT_SECONDARY,
            anchor='w',
        )
        self.detail_title.pack(fill='x', padx=PAD_MEDIUM, pady=(PAD_SMALL, 0))

        # Detail text
        self.detail_text = tk.Text(
            parent, height=8, bg=BG_PANEL, fg=TEXT_PRIMARY,
            font=FONT_MONO, wrap='word', state='disabled',
            insertbackground=TEXT_PRIMARY, borderwidth=0,
            padx=PAD_MEDIUM, pady=PAD_SMALL,
        )
        self.detail_text.pack(fill='both', expand=True)

        self.detail_text.tag_configure('keyword', foreground=TEXT_ACCENT,
                                        font=('Consolas', 9, 'bold'))
        self.detail_text.tag_configure('label', foreground=TEXT_SECONDARY)
        self.detail_text.tag_configure('value', foreground=TEXT_PRIMARY)
        self.detail_text.tag_configure('heading', foreground=TEXT_HEADING,
                                        font=('Consolas', 10, 'bold'))

    # ----------------------------------------------------------------
    # Event Handlers
    # ----------------------------------------------------------------

    def _get_selected_form_types(self) -> list:
        """Get the list of selected filing types from checkboxes."""
        types = []
        if self._ft_10k_var.get():
            types.append("10-K")
        if self._ft_10q_var.get():
            types.append("10-Q")
        if self._ft_8k_var.get():
            types.append("8-K")
        return types or ["10-K"]  # Default to 10-K if nothing selected

    def _on_search(self):
        """Handle search button click."""
        query = self.search_var.get().strip()
        if not query:
            return

        self._init_core()

        sector = self.sector_var.get()
        if sector == "All":
            sector = None

        form_types = self._get_selected_form_types()

        self.log_panel.append(f"Searching for: {query}", 'info')
        if sector:
            self.log_panel.append(f"  Sector filter: {sector}", 'muted')
        if form_types != ["10-K"]:
            self.log_panel.append(f"  Filing types: {', '.join(form_types)}", 'muted')

        self.search_btn.configure(state='disabled')

        def _do_search():
            try:
                results = self._engine.search(
                    query, sector=sector, universe=self.universe,
                    form_types=form_types
                )

                # Enrich with model fit
                for r in results:
                    financials = self._store.get_financials(r.ticker)
                    if financials:
                        fit = self._checker.check_fit(financials, r.sector)
                        r._model_fit = fit
                    else:
                        r._model_fit = None

                # Apply financial filters (if any active)
                if self.filter_engine.has_filters():
                    pre_count = len(results)
                    self.root.after(0, lambda: self.log_panel.append(
                        f"  Applying {len(self.filter_engine.filters)} financial filters...", 'muted'))
                    results = self.filter_engine.apply(results)
                    self.root.after(0, lambda pc=pre_count: self.log_panel.append(
                        f"  Filtered: {len(results)}/{pc} passed", 'info'))

                self.root.after(0, lambda: self._show_results(results, query))

            except Exception as e:
                self.root.after(0, lambda: self.log_panel.append(
                    f"Search error: {e}", 'error'))
            finally:
                self.root.after(0, lambda: self.search_btn.configure(state='normal'))

        threading.Thread(target=_do_search, daemon=True).start()

    def _on_select(self, event):
        """Handle result row selection."""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        ticker = item['values'][0] if item['values'] else ""

        # Find the result object
        result = None
        for r in self.search_results:
            if r.ticker == ticker:
                result = r
                break

        if result:
            self._show_detail(result)

    def _on_refresh_data(self):
        """Handle Refresh Data button click."""
        if self._is_running:
            messagebox.showinfo("In Progress",
                                "A data refresh is already running.")
            return

        form_types = self._get_selected_form_types()
        ft_str = ", ".join(form_types)
        mode = self._get_universe_mode_key()

        if mode == "sp500":
            desc = "S&P 500 companies"
        elif mode == "custom":
            custom = get_setting("custom_tickers", [])
            desc = f"{len(custom)} custom tickers"
        else:
            custom = get_setting("custom_tickers", [])
            desc = f"S&P 500 + {len(custom)} custom tickers"

        count = messagebox.askyesno(
            "Refresh Data",
            f"This will download {ft_str} filings and financial data for {desc}.\n\n"
            "First run takes ~15-20 minutes (500 companies).\n"
            "Subsequent runs only download new filings.\n\n"
            "Proceed?"
        )
        if not count:
            return

        self._init_core()
        self._start_data_refresh(form_types=form_types)

    # ----------------------------------------------------------------
    # Universe management
    # ----------------------------------------------------------------

    def _get_universe_mode_key(self) -> str:
        """Convert display text to settings key."""
        display = self._universe_mode_var.get()
        display_to_key = {
            "S&P 500": "sp500",
            "S&P 500 + Custom": "sp500_plus_custom",
            "Custom Only": "custom",
        }
        return display_to_key.get(display, "sp500")

    def _on_universe_mode_change(self, event=None):
        """Handle universe mode dropdown change."""
        mode = self._get_universe_mode_key()
        set_setting("universe_mode", mode)
        self.log_panel.append(f"Universe mode: {self._universe_mode_var.get()}", 'info')
        # Reload universe with new mode
        self._load_universe_async()

    def _on_add_ticker(self):
        """Add a custom ticker from the entry field."""
        ticker = self._custom_ticker_var.get().strip().upper()
        if not ticker:
            return

        self._init_core()
        self._custom_ticker_var.set('')

        # Validate against SEC database
        info = self._universe_mgr.validate_ticker(ticker)
        if info:
            custom = get_setting("custom_tickers", [])
            if ticker not in custom:
                custom.append(ticker)
                set_setting("custom_tickers", custom)
                self._update_custom_count_label()
                self.log_panel.append(
                    f"Added {ticker} ({info.get('name', '')})", 'success')
                # Reload if in custom or combined mode
                mode = self._get_universe_mode_key()
                if mode != "sp500":
                    self._load_universe_async()
            else:
                self.log_panel.append(f"{ticker} already in custom list", 'warning')
        else:
            self.log_panel.append(
                f"Ticker {ticker} not found in SEC database", 'error')

    def _on_load_ticker_file(self):
        """Load tickers from a file."""
        from pathlib import Path

        path = filedialog.askopenfilename(
            title="Load Ticker List",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"),
                       ("All files", "*.*")],
        )
        if not path:
            return

        self._init_core()
        tickers = self._universe_mgr.load_custom_from_file(Path(path))
        if not tickers:
            self.log_panel.append("No tickers found in file", 'warning')
            return

        custom = get_setting("custom_tickers", [])
        added = 0
        for t in tickers:
            if t not in custom:
                custom.append(t)
                added += 1
        set_setting("custom_tickers", custom)
        self._update_custom_count_label()
        self.log_panel.append(
            f"Loaded {added} new tickers from file ({len(tickers)} total in file)",
            'success')

        mode = self._get_universe_mode_key()
        if mode != "sp500":
            self._load_universe_async()

    def _update_custom_count_label(self):
        """Update the custom ticker count display."""
        custom = get_setting("custom_tickers", [])
        if custom:
            self._custom_count_label.configure(
                text=f"({len(custom)} custom)")
        else:
            self._custom_count_label.configure(text="")

    def _on_export(self):
        """Handle Export Excel button click."""
        if not self.search_results:
            return

        self._init_core()

        try:
            from export.excel_export import export_results
            query = self.search_var.get().strip()
            path = export_results(self.search_results, query, self._store)
            self.log_panel.append(f"Exported to: {path}", 'success')
            messagebox.showinfo("Export Complete", f"Results exported to:\n{path}")
        except Exception as e:
            self.log_panel.append(f"Export error: {e}", 'error')
            messagebox.showerror("Export Error", str(e))

    # ----------------------------------------------------------------
    # Results display
    # ----------------------------------------------------------------

    def _show_results(self, results, query):
        """Display search results in the table."""
        self.search_results = results

        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Format currency helper
        def fmt_currency(val):
            if val is None:
                return "N/A"
            abs_val = abs(val)
            sign = "-" if val < 0 else ""
            if abs_val >= 1e12:
                return f"{sign}${abs_val/1e12:.1f}T"
            elif abs_val >= 1e9:
                return f"{sign}${abs_val/1e9:.1f}B"
            elif abs_val >= 1e6:
                return f"{sign}${abs_val/1e6:.0f}M"
            return f"{sign}${abs_val:,.0f}"

        # Add rows
        for r in results:
            # Model fit summary
            model_str = ""
            if hasattr(r, '_model_fit') and r._model_fit:
                fit = r._model_fit
                model_str = fit.fit_summary
            else:
                model_str = "?"

            # Keywords matched (abbreviated)
            kw_str = ", ".join(
                f"{kw}({r.keyword_counts.get(kw, 0)})"
                for kw in r.keywords_matched[:4]
            )

            # Yahoo metrics (if enriched by filter engine)
            ym = getattr(r, '_yahoo_metrics', None) or {}
            pe_val = ym.get('pe_ratio')
            pe_str = f"{pe_val:.1f}" if pe_val is not None else ""
            mc_val = ym.get('market_cap')
            mc_str = fmt_currency(mc_val) if mc_val is not None else fmt_currency(r.market_cap)

            self.tree.insert('', 'end', values=(
                r.ticker,
                r.company_name,
                f"{r.match_score:.0f}%",
                r.total_hits,
                r.sector,
                kw_str,
                model_str,
                fmt_currency(r.revenue),
                pe_str,
                mc_str,
            ))

        # Update status
        self.results_label.configure(
            text=f"Found {len(results)} matches"
        )
        self.log_panel.append(
            f"Found {len(results)} companies matching '{query}'",
            'success' if results else 'warning'
        )

        # Enable export if results exist
        if results:
            self.export_btn.configure(state='normal')
        else:
            self.export_btn.configure(state='disabled')

    def _show_detail(self, result):
        """Show detail panel for a selected search result."""
        self.detail_title.configure(
            text=f"{result.ticker} - {result.company_name}",
            fg=TEXT_HEADING,
        )

        self.detail_text.configure(state='normal')
        self.detail_text.delete('1.0', 'end')

        # Matched keywords
        self.detail_text.insert('end', "Matched Keywords: ", 'label')
        for kw in result.keywords_matched:
            count = result.keyword_counts.get(kw, 0)
            self.detail_text.insert('end', f"{kw}({count}) ", 'keyword')
        self.detail_text.insert('end', "\n\n")

        # Sections matched
        section_names = {
            "item1": "Business (Item 1)",
            "item1a": "Risk Factors (Item 1A)",
            "item7": "MD&A (Item 7)",
        }
        sections = [section_names.get(s, s) for s in result.sections_matched]
        self.detail_text.insert('end', "Found in: ", 'label')
        self.detail_text.insert('end', ", ".join(sections) + "\n", 'value')

        # Financials
        self.detail_text.insert('end', "\nFinancials: ", 'heading')

        def fmt(val, is_pct=False):
            if val is None:
                return "N/A"
            if is_pct:
                return f"{val*100:.1f}%"
            abs_v = abs(val)
            sign = "-" if val < 0 else ""
            if abs_v >= 1e12: return f"{sign}${abs_v/1e12:.1f}T"
            if abs_v >= 1e9: return f"{sign}${abs_v/1e9:.1f}B"
            if abs_v >= 1e6: return f"{sign}${abs_v/1e6:.0f}M"
            return f"{sign}${abs_v:,.0f}"

        financials = self._store.get_financials(result.ticker) if self._store else None
        if financials:
            metrics = [
                ("Revenue", financials.get("revenue")),
                ("Net Income", financials.get("net_income")),
                ("FCF", financials.get("fcf")),
                ("Op. Margin", financials.get("operating_margin")),
            ]
            parts = []
            for label, val in metrics:
                if val is not None:
                    is_pct = "margin" in label.lower()
                    parts.append(f"{label}: {fmt(val, is_pct)}")
            self.detail_text.insert('end', " | ".join(parts) + "\n", 'value')
        else:
            self.detail_text.insert('end', "No financial data cached\n", 'label')

        # Model fit
        if hasattr(result, '_model_fit') and result._model_fit:
            fit = result._model_fit
            self.detail_text.insert('end', f"\nModel Fit: ", 'heading')
            self.detail_text.insert('end', f"{fit.fit_summary}", 'value')
            if fit.recommended:
                self.detail_text.insert('end',
                    f" (Recommended: {fit.recommended})", 'keyword')
            self.detail_text.insert('end', "\n")
            for note in fit.notes[:3]:
                self.detail_text.insert('end', f"  - {note}\n", 'label')

        # Excerpts
        if result.matched_excerpts:
            self.detail_text.insert('end', "\nExcerpts:\n", 'heading')
            for i, excerpt in enumerate(result.matched_excerpts[:5]):
                self.detail_text.insert('end', f"  {excerpt}\n\n", 'value')

        self.detail_text.configure(state='disabled')

    # ----------------------------------------------------------------
    # Column sorting
    # ----------------------------------------------------------------

    def _sort_column(self, col):
        """Sort the results table by column."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children()]

        # Try numeric sort for score/hits/revenue
        try:
            items.sort(key=lambda t: float(t[0].replace('%', '').replace('$', '')
                                            .replace('B', 'e9').replace('M', 'e6')
                                            .replace('T', 'e12').replace('N/A', '0')
                                            .replace(',', '')),
                       reverse=True)
        except (ValueError, TypeError):
            items.sort(key=lambda t: t[0])

        for index, (val, k) in enumerate(items):
            self.tree.move(k, '', index)

    # ----------------------------------------------------------------
    # Data refresh
    # ----------------------------------------------------------------

    def _load_universe_async(self):
        """Load the universe based on current mode setting."""
        self._init_core()

        def _load():
            try:
                mode = self._get_universe_mode_key()
                custom_tickers = get_setting("custom_tickers", [])

                if mode == "sp500":
                    self.universe = self._universe_mgr.get_sp500()
                    desc = f"{len(self.universe)} S&P 500 companies"
                elif mode == "custom":
                    self.universe = self._universe_mgr.get_custom(custom_tickers)
                    desc = f"{len(self.universe)} custom companies"
                else:  # sp500_plus_custom
                    self.universe = self._universe_mgr.get_combined(
                        True, custom_tickers)
                    desc = (f"{len(self.universe)} companies "
                            f"(S&P 500 + {len(custom_tickers)} custom)")

                cached = self._store.company_count()
                self.root.after(0, lambda: self.status_label.configure(
                    text=f"{len(self.universe)} companies | {cached} cached"
                ))
                self.root.after(0, lambda d=desc, c=cached: self.log_panel.append(
                    f"Loaded {d}, {c} have cached data", 'info'
                ))
            except Exception as e:
                self.root.after(0, lambda: self.log_panel.append(
                    f"Failed to load universe: {e}", 'error'
                ))

        threading.Thread(target=_load, daemon=True).start()

    def _start_data_refresh(self, form_types: list = None):
        """Download filings + financials for the active universe."""
        if form_types is None:
            form_types = ["10-K"]

        self._is_running = True
        self.refresh_btn.configure(state='disabled')

        def _refresh():
            try:
                # Build universe based on mode
                mode = self._get_universe_mode_key()
                custom_tickers = get_setting("custom_tickers", [])

                if mode == "sp500":
                    universe = self._universe_mgr.get_sp500(force_refresh=True)
                elif mode == "custom":
                    universe = self._universe_mgr.get_custom(custom_tickers)
                else:  # sp500_plus_custom
                    universe = self._universe_mgr.get_combined(
                        True, custom_tickers)
                total = len(universe)
                success = 0
                failed = 0

                for i, company in enumerate(universe):
                    ticker = company["ticker"]
                    cik = company.get("cik", "")

                    if not cik:
                        self.root.after(0, lambda t=ticker: self.log_panel.append(
                            f"  Skipping {t} (no CIK)", 'warning'))
                        failed += 1
                        continue

                    # Progress update
                    self.root.after(0, lambda t=ticker, n=i+1: (
                        self.status_label.configure(
                            text=f"Refreshing {n}/{total}: {t}"
                        )
                    ))

                    try:
                        company_ok = False

                        for ft in form_types:
                            if ft == "10-K":
                                # Check if filing already cached and current
                                if not self._fetcher.needs_refresh(ticker, cik):
                                    if self._store.has_filing_data(ticker, "10-K"):
                                        company_ok = True
                                        continue

                                result = self._fetcher.fetch_latest_10k(ticker, cik)
                            else:
                                result = self._fetcher.fetch_filing(
                                    ticker, cik, form_type=ft)

                            if result and result.get("html"):
                                sections = self._parser.extract_sections(
                                    result["html"], form_type=ft)
                                company_dir = self._fetcher.data_dir / ticker
                                self._parser.save_sections(sections, company_dir)
                                company_ok = True
                            else:
                                self.root.after(0, lambda t=ticker, f=ft:
                                    self.log_panel.append(
                                        f"  No {f} for {t}", 'warning'))

                        # Fetch XBRL financials (once per company, not per form type)
                        if company_ok:
                            if not self._store.has_financials(ticker):
                                financials = self._xbrl.get_financials(ticker, cik)
                                self._store.save_financials(ticker, financials)
                            success += 1
                        else:
                            failed += 1

                    except Exception as e:
                        failed += 1
                        self.root.after(0, lambda t=ticker, err=str(e):
                            self.log_panel.append(
                                f"  Error for {t}: {err}", 'error'))

                # Done
                self.root.after(0, lambda: (
                    self.status_label.configure(
                        text=f"{len(universe)} companies | {success} cached"
                    ),
                    self.log_panel.append(
                        f"Refresh complete: {success} success, {failed} failed",
                        'success'
                    ),
                    self.refresh_btn.configure(state='normal'),
                ))
                self.universe = universe

            except Exception as e:
                self.root.after(0, lambda: (
                    self.log_panel.append(f"Refresh failed: {e}", 'error'),
                    self.refresh_btn.configure(state='normal'),
                ))
            finally:
                self._is_running = False

        threading.Thread(target=_refresh, daemon=True).start()
