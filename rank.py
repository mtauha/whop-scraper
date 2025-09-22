#!/usr/bin/env python3
"""
Whop Communities Ranker - Estimates size and ranks communities
Run: python rank.py
"""

import json
import csv
from datetime import datetime
import os

# Configuration
OUTPUT_DIR = "output"
TOP_N = 70  # Top 50 + 20 alternates


def estimate_community_size(community):
    """
    Estimate community member count based on available metrics

    Industry standard: 2-5% of members leave reviews
    We'll use category-specific ratios
    """
    reviews = community.get("reviews_count", 0)
    price = community.get("price_monthly_usd", 0)
    rating = community.get("average_rating", 0)
    category = community.get("category", "Other")

    # Base review-to-member ratios by category
    category_ratios = {
        "Trading": 0.03,  # 3% - Trading communities have engaged users
        "E-commerce": 0.025,  # 2.5%
        "Real Estate": 0.02,  # 2%
        "Finance": 0.03,  # 3%
        "Crypto": 0.035,  # 3.5% - Crypto communities are very engaged
        "Education": 0.02,  # 2%
        "Other": 0.025,  # 2.5% default
    }

    # Get ratio for this category
    ratio = category_ratios.get(category, 0.025)

    # Base estimate from reviews
    if reviews > 0:
        base_estimate = reviews / ratio
    else:
        # No reviews - use price as indicator
        base_estimate = 100 if price > 0 else 50

    # Price multiplier (premium communities tend to be larger/more established)
    if price == 0:  # Free
        price_multiplier = 1.2  # Free communities can be large
    elif price < 50:
        price_multiplier = 1.0
    elif price < 100:
        price_multiplier = 1.1
    elif price < 250:
        price_multiplier = 1.2
    else:  # $250+
        price_multiplier = 1.3

    # Rating quality boost (higher rated = more successful = likely larger)
    if rating >= 4.8:
        rating_multiplier = 1.2
    elif rating >= 4.5:
        rating_multiplier = 1.1
    elif rating >= 4.0:
        rating_multiplier = 1.0
    else:
        rating_multiplier = 0.9

    # Calculate final estimate
    estimated_members = int(base_estimate * price_multiplier * rating_multiplier)

    # Sanity check - minimum based on review count
    min_members = reviews * 10  # At least 10x the review count
    estimated_members = max(estimated_members, min_members)

    # Cap at reasonable maximum
    estimated_members = min(estimated_members, 500000)

    return estimated_members


def calculate_engagement_score(community):
    """
    Calculate overall engagement score for ranking
    """
    estimated_members = community.get("estimated_members", 0)
    reviews = community.get("reviews_count", 0)
    rating = community.get("average_rating", 0)
    price = community.get("price_monthly_usd", 0)

    # Primary factor: Estimated size (60% weight)
    size_score = estimated_members * 0.6

    # Review engagement (20% weight)
    review_score = (reviews * (rating / 5)) * 20  # Normalized by rating quality

    # Revenue indicator (15% weight)
    # Higher price + members = likely successful
    revenue_indicator = (estimated_members * price / 100) * 0.15

    # Review density bonus (5% weight)
    # Communities with high review-to-member ratio are highly engaged
    review_density = (reviews / max(estimated_members, 1)) * 10000

    total_score = size_score + review_score + revenue_indicator + review_density

    return round(total_score, 2)


def assign_confidence(community):
    """
    Assign confidence level to our size estimate
    """
    reviews = community.get("reviews_count", 0)
    rating = community.get("average_rating", 0)

    if reviews >= 100 and rating >= 4.0:
        return "High"
    elif reviews >= 25:
        return "Medium"
    else:
        return "Low"


def main():
    """Main ranking function"""
    print("=" * 50)
    print("Starting Community Ranking Process...")
    print("=" * 50)

    # Load scraped data
    input_file = f"{OUTPUT_DIR}/raw_communities.json"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        print("Please run 'python scrape.py' first.")
        return

    with open(input_file, "r") as f:
        communities = json.load(f)

    print(f"Loaded {len(communities)} communities")

    # Step 1: Estimate sizes and calculate scores
    print("\nStep 1: Estimating community sizes...")

    for community in communities:
        # Add estimated members
        community["estimated_members"] = estimate_community_size(community)

        # Add confidence level
        community["confidence"] = assign_confidence(community)

        # Calculate engagement score
        community["engagement_score"] = calculate_engagement_score(community)

    # Step 2: Sort by engagement score
    print("Step 2: Ranking communities by engagement score...")
    communities.sort(key=lambda x: x.get("engagement_score", 0), reverse=True)

    # Step 3: Assign ranks
    for i, community in enumerate(communities, 1):
        community["rank"] = i

    # Step 4: Get top 70
    top_communities = communities[:TOP_N]

    # Step 5: Save results
    print(f"Step 3: Saving top {TOP_N} communities to CSV...")

    # Save to CSV
    csv_file = f"{OUTPUT_DIR}/ranked_communities.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "rank",
            "community_name",
            "creator_name",
            "url",
            "category",
            "is_free",
            "price_monthly_usd",
            "reviews_count",
            "average_rating",
            "estimated_members",
            "confidence",
            "engagement_score",
            "description",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for community in top_communities:
            row = {field: community.get(field, "") for field in fieldnames}
            writer.writerow(row)

    # Save full ranked data to JSON (for reference)
    with open(f"{OUTPUT_DIR}/all_communities_ranked.json", "w") as f:
        json.dump(communities, f, indent=2)

    # Print summary
    print("\n" + "=" * 50)
    print("RANKING COMPLETE!")
    print("=" * 50)
    print(f"\nTop 5 Largest Communities:")
    print("-" * 30)

    for community in top_communities[:5]:
        print(f"{community['rank']}. {community['community_name']}")
        print(f"   Estimated Members: {community['estimated_members']:,}")
        print(
            f"   Reviews: {community['reviews_count']} | Rating: {community['average_rating']}"
        )
        print(f"   Price: ${community['price_monthly_usd']}/month")
        print(f"   Confidence: {community['confidence']}")
        print()

    # Statistics
    print("Statistics:")
    print("-" * 30)
    total_reviews = sum(c.get("reviews_count", 0) for c in top_communities)
    avg_price = sum(c.get("price_monthly_usd", 0) for c in top_communities) / len(
        top_communities
    )
    free_count = sum(1 for c in top_communities if c.get("is_free", False))

    print(f"Total communities ranked: {len(communities)}")
    print(f"Top {TOP_N} communities saved to: {csv_file}")
    print(f"Average price in top {TOP_N}: ${avg_price:.2f}/month")
    print(f"Free communities in top {TOP_N}: {free_count}")
    print(f"Total reviews across top {TOP_N}: {total_reviews:,}")

    # Confidence breakdown
    high_conf = sum(1 for c in top_communities if c.get("confidence") == "High")
    med_conf = sum(1 for c in top_communities if c.get("confidence") == "Medium")
    low_conf = sum(1 for c in top_communities if c.get("confidence") == "Low")

    print(f"\nConfidence Levels in Top {TOP_N}:")
    print(f"  High: {high_conf}")
    print(f"  Medium: {med_conf}")
    print(f"  Low: {low_conf}")

    print("\n" + "=" * 50)
    print("All files saved in 'output/' directory")
    print("=" * 50)


if __name__ == "__main__":
    main()
