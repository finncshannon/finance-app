# REFERENCE CODE SNAPSHOT — READ ONLY
> Created: February 22, 2026 by Designer Agent
> Purpose: Reference copies of source files for planning sessions on school computer
> WARNING: These are SNAPSHOTS. Do NOT edit. Do NOT run. Reference only.

## What's Here

### Priority 1: Planning Documents (specs/)
These are the actual planning outputs — the primary artifacts of our work.
They live in ../specs/ and are NOT duplicated here.

### Priority 2: Python Scripts (python_scripts/)
Core source code from the Excel-based valuation system being migrated.
These files define how data flows, what calculations exist, and what
named ranges / data structures the new app must replicate.

| File | Purpose | Used In Sessions |
|------|---------|-----------------|
| auto_detect_model.py | ModelDetector v4.0 scoring engine | 1B, 1C, 1D, 1E, 1F |
| config.py | All named ranges, model configs, system defaults | All model sessions |
| data_extractor.py | Yahoo Finance API extraction | 0B, 0C, 1E |
| data_cache.py | SQLite cache for API responses | 0B |
| excel_writer.py | Writes data to Excel per model | 1B, 1C, 1D |
| market_implied_calculator.py | Reverse-DCF/DDM/RevBased/Comps | 1B, 1C, 1D, 1F |
| utils.py | Shared utilities (formatting, math, logging) | Reference |
| excel_helpers.py | Named range access, DataFrame extraction | Reference |
| requirements.txt | Python dependencies list | 0G |

### Priority 3: Screening Tool (screening_tool/)
The current Python/tkinter screening tool that will be rebuilt as the Scanner module.

| File | Purpose | Used In Sessions |
|------|---------|-----------------|
| core/search_engine.py | Keyword search with scoring/rarity | Phase 2 |
| core/filter_engine.py | Numeric filters for screening | Phase 2 |
| core/company_store.py | Local file cache for filings | Phase 2, 0B |
| core/settings.py | App settings management | Phase 2, 0E |
| gui/main_window.py | Tkinter UI (reference for redesign) | Phase 2 |
| gui/styles.py | Current UI styling | Phase 2, 6 |
| config/settings.json | Default configuration | Phase 2 |
| config/saved_searches.json | Saved search presets | Phase 2 |

### Priority 4: Agent Pipeline (agent_pipeline/)
The multi-agent development framework that will execute the specs we produce.

| File | Purpose | Used In Sessions |
|------|---------|-----------------|
| README.md | Pipeline operator guide | Reference |
| 00_designer_agent.md | Designer Agent instructions (us) | Reference |
| 01_pm_agent.md | PM Agent instructions | Reference |
| 02_architect_agent.md | Architect Agent instructions | Reference |
| 03_developer_agent.md | Developer Agent instructions | Reference |

### Priority 5: Root Documents (root_docs/)
Key documents from the project root that provide context.

| File | Purpose | Used In Sessions |
|------|---------|-----------------|
| Chat Reference File.txt | Project context and history | Reference |
| PERFORMANCE_ANALYSIS.md | Benchmark data | 0F |

## How to Use This Folder

1. Claude reads these files at the start of a planning session
2. The files provide context about how the CURRENT system works
3. New spec documents reference these to ensure accuracy
4. These files are NEVER modified — they're snapshots
5. If source code changes at home, re-snapshot before next school session
