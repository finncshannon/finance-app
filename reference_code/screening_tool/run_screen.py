"""Quick aerospace screen — search + market cap filter, display in GUI window."""

import sys
import os
import tkinter as tk
from tkinter import ttk

# Ensure we're running from the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.company_store import CompanyStore
from core.search_engine import SearchEngine
from core.filter_engine import FilterEngine, Filter


def run_screen():
    print("Initializing store...")
    store = CompanyStore()
    engine = SearchEngine(store)

    # --- Phase 1: Multiple focused keyword searches to cast a wide net ---
    # The search engine has a "core term gate" that requires the rarest keyword,
    # so we run several shorter queries and merge/dedupe results.
    queries = [
        '"aerospace and defense"',       # exact phrase — hits most A&D companies
        "aerospace aircraft defense",     # broad A&D terms
        "missile satellite defense",      # weapons/space systems
        "aircraft engine turbine",        # engine/propulsion makers
        "military defense contractor",    # pure defense plays
    ]

    all_results = {}  # ticker -> best SearchResult
    for q in queries:
        print(f"Searching: {q}")
        hits = engine.search(
            query=q,
            sector=None,
            max_results=100,
            min_score=5.0,
        )
        print(f"  -> {len(hits)} results")
        for r in hits:
            # Keep the result with the highest score per ticker
            if r.ticker not in all_results or r.match_score > all_results[r.ticker].match_score:
                all_results[r.ticker] = r

    results = list(all_results.values())
    results.sort(key=lambda r: r.match_score, reverse=True)
    print(f"\nCombined unique results: {len(results)}")

    # --- Phase 2: Filter by market cap > $75B ---
    print("\nApplying market cap filter (>=$75B) via Yahoo Finance...")
    fe = FilterEngine()
    fe.add_filter(Filter('market_cap', '>=', 75_000_000_000))

    def progress(cur, total, ticker):
        print(f"  [{cur}/{total}] Fetching metrics for {ticker}...")

    filtered = fe.apply(results, progress_callback=progress)
    print(f"\n{len(filtered)} companies passed market cap >= $75B filter.\n")

    # Sort by match score descending
    filtered.sort(key=lambda r: r.match_score, reverse=True)

    # Take top 20
    top = filtered[:20]

    # Print to console
    print(f"{'#':<4} {'Ticker':<8} {'Company':<35} {'Score':<8} {'Mkt Cap ($B)':<14} {'Hits':<6} {'Keywords Matched'}")
    print("-" * 110)
    for i, r in enumerate(top, 1):
        mcap = getattr(r, '_yahoo_metrics', {}).get('market_cap')
        mcap_str = f"${mcap/1e9:.1f}B" if mcap else "N/A"
        kw = ", ".join(r.keywords_matched[:5])
        print(f"{i:<4} {r.ticker:<8} {r.company_name[:34]:<35} {r.match_score:<8.1f} {mcap_str:<14} {r.total_hits:<6} {kw}")

    # --- Phase 3: Display in a Tkinter window on screen ---
    show_results_window(top, "Aerospace & Defense")


def show_results_window(results, query):
    """Pop up a Tkinter table on the desktop."""
    root = tk.Tk()
    root.title(f"Screening Results — Aerospace / Mkt Cap ≥ $75B")
    root.geometry("1200x650")
    root.configure(bg="#1e1e2e")

    # Header
    header = tk.Label(
        root,
        text=f"Aerospace Screen — Market Cap ≥ $75B  |  {len(results)} results",
        font=("Segoe UI", 14, "bold"),
        fg="#cdd6f4", bg="#1e1e2e", pady=10,
    )
    header.pack(fill=tk.X)

    # Treeview table
    columns = ("rank", "ticker", "company", "score", "mkt_cap", "pe", "hits", "keywords")
    tree = ttk.Treeview(root, columns=columns, show="headings", height=20)

    col_config = [
        ("rank",    "#",            50,  tk.CENTER),
        ("ticker",  "Ticker",       70,  tk.CENTER),
        ("company", "Company",      260, tk.W),
        ("score",   "Match %",      80,  tk.CENTER),
        ("mkt_cap", "Mkt Cap",      110, tk.CENTER),
        ("pe",      "P/E",          70,  tk.CENTER),
        ("hits",    "Hits",         60,  tk.CENTER),
        ("keywords","Keywords Matched", 450, tk.W),
    ]
    for cid, heading, width, anchor in col_config:
        tree.heading(cid, text=heading)
        tree.column(cid, width=width, anchor=anchor, minwidth=40)

    # Style
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
                     background="#313244",
                     foreground="#cdd6f4",
                     fieldbackground="#313244",
                     font=("Segoe UI", 10),
                     rowheight=28)
    style.configure("Treeview.Heading",
                     background="#45475a",
                     foreground="#cdd6f4",
                     font=("Segoe UI", 10, "bold"))
    style.map("Treeview", background=[("selected", "#585b70")])

    # Insert rows
    for i, r in enumerate(results, 1):
        metrics = getattr(r, '_yahoo_metrics', {}) or {}
        mcap = metrics.get('market_cap')
        pe = metrics.get('pe_ratio')
        mcap_str = f"${mcap/1e9:.1f}B" if mcap else "—"
        pe_str = f"{pe:.1f}" if pe else "—"
        kw = ", ".join(r.keywords_matched)
        tree.insert("", tk.END, values=(
            i, r.ticker, r.company_name, f"{r.match_score:.1f}%",
            mcap_str, pe_str, r.total_hits, kw,
        ))

    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    # Close button
    btn = tk.Button(
        root, text="Close", command=root.destroy,
        font=("Segoe UI", 11), bg="#45475a", fg="#cdd6f4",
        activebackground="#585b70", activeforeground="#cdd6f4",
        relief=tk.FLAT, padx=20, pady=5,
    )
    btn.pack(pady=(0, 12))

    root.mainloop()


if __name__ == "__main__":
    run_screen()
