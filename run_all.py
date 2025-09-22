"""
Run the complete Whop scraping and ranking process
Usage: python run_all.py
"""

import subprocess
import sys
import os
import time


def check_requirements():
    """Check if required packages are installed"""
    try:
        import requests
        import bs4
        import lxml

        print("✓ All required packages installed")
        return True
    except ImportError as e:
        print("✗ Missing required packages")
        print("Please run: pip install -r requirements.txt")
        return False


def run_script(script_name):
    """Run a Python script and capture output"""
    print(f"\n{'='*50}")
    print(f"Running {script_name}...")
    print("=" * 50)

    try:
        result = subprocess.run(
            [sys.executable, script_name], capture_output=False, text=True
        )
        if result.returncode == 0:
            print(f"✓ {script_name} completed successfully")
            return True
        else:
            print(f"✗ {script_name} failed with error")
            return False
    except Exception as e:
        print(f"✗ Error running {script_name}: {e}")
        return False


def main():
    """Run the complete process"""
    print("=" * 60)
    print("WHOP COMMUNITIES SCRAPER & RANKER")
    print("=" * 60)

    # Check requirements
    if not check_requirements():
        return

    # Create output directory
    if not os.path.exists("output"):
        os.makedirs("output")
        print("✓ Created output directory")

    print("\nThis process will:")
    print("1. Scrape all Whop communities (may take 2-3 hours)")
    print("2. Rank them by estimated size")
    print("3. Output top 70 communities to CSV")

    response = input("\nDo you want to continue? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Exiting...")
        return

    start_time = time.time()

    # Run scraper
    print("\n" + "=" * 60)
    print("PHASE 1: SCRAPING")
    print("=" * 60)
    if not run_script("scrape.py"):
        print("\nScraping failed. Please check output/scrape_log.txt for details.")
        return

    # Small pause between scripts
    time.sleep(2)

    # Run ranker
    print("\n" + "=" * 60)
    print("PHASE 2: RANKING")
    print("=" * 60)
    if not run_script("rank.py"):
        print("\nRanking failed. Please check the error messages above.")
        return

    # Summary
    elapsed_time = time.time() - start_time
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)

    print("\n" + "=" * 60)
    print("✓ PROCESS COMPLETE!")
    print("=" * 60)
    print(f"Total time: {hours}h {minutes}m")
    print("\nOutput files:")
    print("  • output/ranked_communities.csv - Top 70 communities (MAIN RESULT)")
    print("  • output/raw_communities.json - All scraped data")
    print("  • output/all_communities_ranked.json - All communities with rankings")
    print("  • output/scrape_log.txt - Detailed log")
    print("\nThe main result file is: output/ranked_communities.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
