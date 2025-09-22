#!/usr/bin/env python3
"""
Batch Results Merger for Whop Scraper
Merges all batch JSON files into a single raw_communities.json file
Usage: python merge_batches.py
"""

import os
import json
import glob
from datetime import datetime


def merge_batch_files():
    """Merge all batch JSON files into a single file"""
    print("=== MERGING BATCH RESULTS ===")
    print(f"Start time: {datetime.now()}")

    # Find all batch files
    batch_files = glob.glob("output/raw_communities_batch_*.json")

    if not batch_files:
        print("No batch files found to merge!")
        print("Expected files: output/raw_communities_batch_1.json, output/raw_communities_batch_2.json, etc.")
        return

    # Sort by batch number
    batch_files.sort(key=lambda x: int(x.split('_')[-1].replace('.json', '')))

    print(f"Found {len(batch_files)} batch files to merge:")
    for file in batch_files:
        print(f"  - {file}")

    all_communities = []
    total_communities = 0

    # Process each batch file
    for batch_file in batch_files:
        print(f"\nProcessing: {batch_file}")

        try:
            with open(batch_file, "r", encoding="utf-8") as f:
                communities = json.load(f)

            if isinstance(communities, list):
                all_communities.extend(communities)
                total_communities += len(communities)
                print(f"  Added {len(communities)} communities from {batch_file}")
            else:
                print(f"  Warning: {batch_file} does not contain a list of communities")

        except Exception as e:
            print(f"  Error reading {batch_file}: {e}")

    print(f"\n=== MERGE SUMMARY ===")
    print(f"Total communities collected: {total_communities}")
    print(f"Batch files processed: {len(batch_files)}")

    if all_communities:
        # Remove duplicates based on URL
        seen_urls = set()
        unique_communities = []

        for community in all_communities:
            url = community.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_communities.append(community)

        print(f"Unique communities (after deduplication): {len(unique_communities)}")

        # Save merged results
        output_file = "output/raw_communities.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_communities, f, indent=2, ensure_ascii=False)

        print(f"Merged results saved to: {output_file}")

        # Create summary file
        summary = {
            "merge_timestamp": datetime.now().isoformat(),
            "total_batch_files_processed": len(batch_files),
            "total_communities_found": total_communities,
            "unique_communities": len(unique_communities),
            "duplicates_removed": total_communities - len(unique_communities),
            "batch_files": batch_files
        }

        with open("output/merge_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"Merge summary saved to: output/merge_summary.json")

        # Show some statistics
        print(f"\n=== COMMUNITY STATISTICS ===")

        # Count by price ranges
        free_count = sum(1 for c in unique_communities if c.get("is_free", False))
        paid_count = len(unique_communities) - free_count

        print(f"Free communities: {free_count}")
        print(f"Paid communities: {paid_count}")

        # Price statistics for paid communities
        paid_prices = [c.get("price_monthly_usd", 0) for c in unique_communities if not c.get("is_free", False) and c.get("price_monthly_usd", 0) > 0]

        if paid_prices:
            avg_price = sum(paid_prices) / len(paid_prices)
            min_price = min(paid_prices)
            max_price = max(paid_prices)

            print(f"Average price (paid communities): ${avg_price:.2f}/month")
            print(f"Price range: ${min_price:.2f} - ${max_price:.2f}/month")

        # Communities with ratings
        rated_communities = [c for c in unique_communities if c.get("average_rating", 0) > 0]
        print(f"Communities with ratings: {len(rated_communities)}")

        if rated_communities:
            avg_rating = sum(c.get("average_rating", 0) for c in rated_communities) / len(rated_communities)
            print(f"Average rating: {avg_rating:.2f}")

        print(f"\n=== TOP 5 HIGHEST PRICED COMMUNITIES ===")
        sorted_by_price = sorted(unique_communities, key=lambda x: x.get("price_monthly_usd", 0), reverse=True)
        for i, community in enumerate(sorted_by_price[:5]):
            name = community.get("community_name", "Unknown")
            price = community.get("price_monthly_usd", 0)
            print(f"{i+1}. {name}: ${price:.2f}/month")

        print(f"\n=== COMMUNITIES BY CATEGORY ===")
        categories = {}
        for community in unique_communities:
            category = community.get("category", "Unknown")
            categories[category] = categories.get(category, 0) + 1

        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"{category}: {count} communities")

    else:
        print("No communities found to merge!")

    print(f"\n=== MERGE COMPLETED ===")
    print(f"End time: {datetime.now()}")
    print("\nReady for ranking analysis! Run 'python rank.py' next.")


def show_batch_status():
    """Show status of all batch files"""
    print("\n=== BATCH STATUS ===")

    batch_files = glob.glob("output/raw_communities_batch_*.json")

    if not batch_files:
        print("No batch files found")
        return

    batch_files.sort(key=lambda x: int(x.split('_')[-1].replace('.json', '')))

    total_communities = 0
    for batch_file in batch_files:
        try:
            with open(batch_file, "r", encoding="utf-8") as f:
                communities = json.load(f)
            count = len(communities) if isinstance(communities, list) else 0
            total_communities += count
            batch_num = batch_file.split('_')[-1].replace('.json', '')
            print(f"Batch {batch_num}: {count} communities")
        except Exception as e:
            print(f"Error reading {batch_file}: {e}")

    print(f"\nTotal communities across all batches: {total_communities}")


def main():
    """Main function"""
    print("=== WHOP SCRAPER BATCH MERGER ===")

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # Show current batch status
    show_batch_status()

    # Ask for confirmation
    print("\nThis will merge all batch files into raw_communities.json")
    response = input("Continue? (y/n): ").lower().strip()

    if response == 'y' or response == 'yes':
        merge_batch_files()
    else:
        print("Merge cancelled")


if __name__ == "__main__":
    main()
