@echo off
REM Copy reference code snapshot for planning sessions
REM Run this from home computer to update reference files

echo Copying Python scripts...
copy "C:\Claude Access Point\StockValuation\python_scripts\auto_detect_model.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\config.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\data_extractor.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\data_cache.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\excel_writer.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\market_implied_calculator.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\utils.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\excel_helpers.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y
copy "C:\Claude Access Point\StockValuation\python_scripts\requirements.txt" "C:\Claude Access Point\StockValuation\Finance App\reference_code\python_scripts\" /Y

echo Copying Screening Tool core...
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\search_engine.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\filter_engine.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\company_store.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\settings.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\yahoo_metrics.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\universe.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\sec_client.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\filing_fetcher.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\filing_parser.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\xbrl_parser.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\core\model_checker.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\core\" /Y

echo Copying Screening Tool GUI...
copy "C:\Claude Access Point\StockValuation\Screening_Tool\gui\main_window.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\gui\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\gui\styles.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\gui\" /Y

echo Copying Screening Tool config...
copy "C:\Claude Access Point\StockValuation\Screening_Tool\config\settings.json" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\config\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\config\saved_searches.json" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\config\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\config\stopwords.txt" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\config\" /Y

echo Copying Screening Tool export...
copy "C:\Claude Access Point\StockValuation\Screening_Tool\export\excel_export.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\export\" /Y

echo Copying Screening Tool root...
copy "C:\Claude Access Point\StockValuation\Screening_Tool\app.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\" /Y
copy "C:\Claude Access Point\StockValuation\Screening_Tool\run_screen.py" "C:\Claude Access Point\StockValuation\Finance App\reference_code\screening_tool\" /Y

echo Copying Agent Pipeline...
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\README.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\00_designer_agent.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\01_pm_agent.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\02_architect_agent.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\03_developer_agent.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\04_qa_agent.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\05_reviewer_agent.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y
copy "C:\Claude Access Point\StockValuation\Finance App\Setup files\06_docs_agent.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\agent_pipeline\" /Y

echo Copying Root Documents...
copy "C:\Claude Access Point\StockValuation\Chat Reference File.txt" "C:\Claude Access Point\StockValuation\Finance App\reference_code\root_docs\" /Y
copy "C:\Claude Access Point\StockValuation\PERFORMANCE_ANALYSIS.md" "C:\Claude Access Point\StockValuation\Finance App\reference_code\root_docs\" /Y

echo.
echo === COPY COMPLETE ===
echo Reference code snapshot updated in Finance App\reference_code\
echo.
pause
