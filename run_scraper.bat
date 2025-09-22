@echo off
REM Whop Scraper Full Pipeline Script (Windows)
REM This script runs the complete scraping pipeline:
REM 1. Sets up environment and dependencies
REM 2. Extracts URLs from sitemaps (explore.py)
REM 3. Scrapes community data (scrape_new.py)
REM 4. Ranks and analyzes data (rank.py)

echo ==========================================
echo WHOP SCRAPER FULL PIPELINE
echo ==========================================
echo Starting at: %date% %time%
echo.

REM Step 1: Activate virtual environment (if it exists)
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
) else if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
) else (
    echo ⚠️  No virtual environment found, using system Python
)

echo.

REM Step 2: Install/update requirements
echo 📦 Installing Python requirements...
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo ✅ Requirements installed
) else (
    echo ⚠️  No requirements.txt found, installing basic packages...
    pip install requests beautifulsoup4 lxml
)

echo.

REM Step 3: Create output directory
echo 📁 Creating output directory...
if not exist "output" mkdir output
echo ✅ Output directory ready

echo.

REM Step 4: Run explore.py to extract URLs from sitemaps
echo 🔍 Step 1/3: Running explore.py to extract community URLs...
echo This will fetch all XML sitemaps and extract product URLs...
python explore.py

if not exist "output\sample_discovery.txt" (
    echo ❌ Error: sample_discovery.txt not created by explore.py
    pause
    exit /b 1
)

for /f %%i in ('find /c /v "" ^< output\sample_discovery.txt') do set URL_COUNT=%%i
echo ✅ Found %URL_COUNT% product sitemap URLs

echo.

REM Step 5: Run scrape_new.py to scrape community data
echo 🕷️  Step 2/3: Running scrape_new.py to scrape community data...
echo This will extract community URLs from product sitemaps and scrape each page...
python scrape_new.py

if not exist "output\raw_communities.json" (
    echo ❌ Error: raw_communities.json not created by scrape_new.py
    pause
    exit /b 1
)

for /f %%i in ('python -c "import json; data=json.load(open('output/raw_communities.json')); print(len(data))"') do set COMMUNITY_COUNT=%%i
echo ✅ Scraped %COMMUNITY_COUNT% communities

echo.

REM Step 6: Run rank.py to analyze and rank data
echo 📊 Step 3/3: Running rank.py to rank and analyze communities...
python rank.py

if not exist "output\ranked_communities.csv" (
    echo ❌ Error: ranked_communities.csv not created by rank.py
    pause
    exit /b 1
)

echo ✅ Rankings generated

echo.

REM Step 7: Summary
echo ==========================================
echo 🎉 PIPELINE COMPLETED SUCCESSFULLY!
echo ==========================================
echo Completed at: %date% %time%
echo.
echo 📋 RESULTS SUMMARY:
echo    • Product sitemaps processed: %URL_COUNT%
echo    • Communities scraped: %COMMUNITY_COUNT%
echo    • Output files created:
echo      - output\sample_discovery.txt (product sitemap URLs)
echo      - output\raw_communities.json (scraped community data)
echo      - output\ranked_communities.csv (top ranked communities)
echo      - output\all_communities_ranked.json (full ranked data)
echo.
echo 🚀 Ready for analysis! Check the output\ directory for results.
echo.

REM Optional: Show top 5 communities
echo 🏆 TOP 5 COMMUNITIES:
powershell -Command "Get-Content output\ranked_communities.csv | Select-Object -First 6"

echo.
echo Press any key to exit...
pause >nul