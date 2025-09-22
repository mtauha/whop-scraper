#!/bin/bash

# Whop Scraper Full Pipeline Script
# This script runs the complete scraping pipeline:
# 1. Sets up environment and dependencies
# 2. Extracts URLs from sitemaps (explore.py)
# 3. Scrapes community data (scrape_new.py)
# 4. Ranks and analyzes data (rank.py)

set -e  # Exit on any error

echo "=========================================="
echo "WHOP SCRAPER FULL PIPELINE"
echo "=========================================="
echo "Starting at: $(date)"
echo ""

# Step 1: Activate virtual environment (if it exists)
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
elif [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

echo ""

# Step 2: Install/update requirements
echo "📦 Installing Python requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Requirements installed"
else
    echo "⚠️  No requirements.txt found, installing basic packages..."
    pip install requests beautifulsoup4 lxml
fi

echo ""

# Step 3: Create output directory
echo "📁 Creating output directory..."
mkdir -p output
echo "✅ Output directory ready"

echo ""

# Step 4: Run explore.py to extract URLs from sitemaps
echo "🔍 Step 1/3: Running explore.py to extract community URLs..."
echo "This will fetch all XML sitemaps and extract product URLs..."
python explore.py

if [ ! -f "output/sample_discovery.txt" ]; then
    echo "❌ Error: sample_discovery.txt not created by explore.py"
    exit 1
fi

URL_COUNT=$(wc -l < output/sample_discovery.txt)
echo "✅ Found $URL_COUNT product sitemap URLs"

echo ""

# Step 5: Run scrape_new.py to scrape community data
echo "🕷️  Step 2/3: Running scrape_new.py to scrape community data..."
echo "This will extract community URLs from product sitemaps and scrape each page..."
python scrape_new.py

if [ ! -f "output/raw_communities.json" ]; then
    echo "❌ Error: raw_communities.json not created by scrape_new.py"
    exit 1
fi

COMMUNITY_COUNT=$(python -c "import json; data=json.load(open('output/raw_communities.json')); print(len(data))")
echo "✅ Scraped $COMMUNITY_COUNT communities"

echo ""

# Step 6: Run rank.py to analyze and rank data
echo "📊 Step 3/3: Running rank.py to rank and analyze communities..."
python rank.py

if [ ! -f "output/ranked_communities.csv" ]; then
    echo "❌ Error: ranked_communities.csv not created by rank.py"
    exit 1
fi

echo "✅ Rankings generated"

echo ""

# Step 7: Summary
echo "=========================================="
echo "🎉 PIPELINE COMPLETED SUCCESSFULLY!"
echo "=========================================="
echo "Completed at: $(date)"
echo ""
echo "📋 RESULTS SUMMARY:"
echo "   • Product sitemaps processed: $URL_COUNT"
echo "   • Communities scraped: $COMMUNITY_COUNT"
echo "   • Output files created:"
echo "     - output/sample_discovery.txt (product sitemap URLs)"
echo "     - output/raw_communities.json (scraped community data)"
echo "     - output/ranked_communities.csv (top ranked communities)"
echo "     - output/all_communities_ranked.json (full ranked data)"
echo ""
echo "🚀 Ready for analysis! Check the output/ directory for results."
echo ""

# Optional: Show top 5 communities
echo "🏆 TOP 5 COMMUNITIES:"
if command -v csvlook &> /dev/null; then
    head -6 output/ranked_communities.csv | csvlook
else
    head -6 output/ranked_communities.csv
fi