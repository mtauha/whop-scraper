#!/usr/bin/env python3
"""
Whop Structure Explorer - Discovers the actual HTML structure
Run this FIRST to understand the site structure before scraping
Usage: python explore.py
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime


def get_page(url, retries=3):
    """Fetch a page with retry logic"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)  # Longer timeout for XML files
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                print(f"URL not found (404): {url}")
                return None
            else:
                print(f"HTTP {response.status_code} for {url}")
        except requests.exceptions.Timeout:
            wait_time = (attempt + 1) * 3
            print(f"Timeout on {url} (attempt {attempt + 1}/{retries}). Waiting {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2)

    print(f"Failed to fetch {url} after {retries} attempts")
    return None


def explore_sitemap():
    """Extract community URLs from discover sitemap and save to file"""
    print("\n" + "=" * 60)
    print("EXTRACTING COMMUNITY URLs FROM DISCOVER SITEMAP")
    print("=" * 60)

    # Fetch discover sitemap - all XML files from 1.xml to 11.xml
    main_sitemap_url = "https://whop.com/sitemaps/discover/"
    all_community_urls = []

    for i in range(1, 12):
        xml_url = f"{main_sitemap_url}{i}.xml"
        print(f"\nFetching discover sitemap {i}/11: {xml_url}")

        xml_content = get_page(xml_url)
        if not xml_content:
            print(f"Failed to fetch sitemap {i}.xml!")
            continue

        print(f"Sitemap {i}.xml size: {len(xml_content)} bytes")

        # Extract URLs from XML sitemap format
        # Pattern: <loc>https://whop.com/sitemaps/product/prod_XXX.xml</loc>
        all_urls = re.findall(r"<loc>([^<]+)</loc>", xml_content)
        print(f"Found {len(all_urls)} total URLs in sitemap {i}.xml")

        # Filter for product sitemap URLs with pattern: https://whop.com/sitemaps/product/prod_
        product_sitemap_urls = [url for url in all_urls if 'sitemaps/product/prod_' in url]
        print(f"Found {len(product_sitemap_urls)} product sitemap URLs in {i}.xml")

        all_community_urls.extend(product_sitemap_urls)

        # Small delay between requests to be respectful
        time.sleep(1)

    print(f"\n{'='*50}")
    print(f"TOTAL SUMMARY:")
    print(f"Total product sitemap URLs found across all XML files: {len(all_community_urls)}")
    print(f"{'='*50}")

    if all_community_urls:
        print(f"\nSaving {len(all_community_urls)} product sitemap URLs to sample_discovery.txt")

        # Save to sample_discovery.txt
        with open("output/sample_discovery.txt", "w") as f:
            for url in all_community_urls:
                f.write(url + "\n")

        print("✓ Product sitemap URLs saved to output/sample_discovery.txt")
        print("\nFirst 10 product sitemap URLs:")
        for url in all_community_urls[:10]:
            print(f"  - {url}")

        return all_community_urls[0] if all_community_urls else None
    else:
        print("No product sitemap URLs found across any XML files!")
        return None


def explore_community_page(url):
    """Explore a community page structure"""
    print("\n" + "=" * 60)
    print("EXPLORING COMMUNITY PAGE STRUCTURE")
    print("=" * 60)
    print(f"\nFetching: {url}")

    html = get_page(url)
    if not html:
        print("Failed to fetch community page!")
        return

    soup = BeautifulSoup(html, "html.parser")
    print(f"Page size: {len(html)} bytes")

    # Save raw HTML for inspection
    with open("output/sample_community.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved raw HTML to: output/sample_community.html")

    # Explore different elements
    findings = {}

    # 1. Find title/name
    print("\n1. LOOKING FOR COMMUNITY NAME:")
    h1_tags = soup.find_all("h1")
    if h1_tags:
        print(f"  Found {len(h1_tags)} <h1> tags:")
        for h1 in h1_tags[:3]:
            print(f"    - {h1.text.strip()[:50]}")
            findings["h1_example"] = h1.text.strip()

    # Check meta tags
    og_title = soup.find("meta", {"property": "og:title"})
    if og_title:
        print(f"  Found og:title: {og_title.get('content', '')[:50]}")
        findings["og_title"] = og_title.get("content", "")

    # 2. Find price
    print("\n2. LOOKING FOR PRICE:")
    # Look for dollar signs
    price_patterns = soup.find_all(text=re.compile(r"\$\d+"))
    if price_patterns:
        print(f"  Found {len(price_patterns)} price patterns:")
        for price in price_patterns[:3]:
            parent = price.parent
            print(f"    - Text: {price.strip()[:30]}")
            print(
                f"      Parent tag: <{parent.name}> with class: {parent.get('class', 'no-class')}"
            )
            findings["price_example"] = price.strip()

    # Look for common price container classes
    for class_name in ["price", "pricing", "cost", "amount"]:
        elements = soup.find_all(class_=re.compile(class_name, re.I))
        if elements:
            print(f"  Found {len(elements)} elements with '{class_name}' in class")
            for elem in elements[:2]:
                print(f"    - {elem.text.strip()[:50]}")

    # 3. Find reviews/ratings
    print("\n3. LOOKING FOR REVIEWS/RATINGS:")
    # Look for star patterns or rating numbers
    rating_patterns = soup.find_all(text=re.compile(r"[★⭐]|(\d\.\d+)\s*\((\d+)"))
    if rating_patterns:
        print(f"  Found {len(rating_patterns)} potential rating patterns:")
        for rating in rating_patterns[:3]:
            print(f"    - {rating.strip()[:50]}")
            findings["rating_example"] = rating.strip()

    # Look for review-related classes
    for class_name in ["review", "rating", "star", "feedback"]:
        elements = soup.find_all(class_=re.compile(class_name, re.I))
        if elements:
            print(f"  Found {len(elements)} elements with '{class_name}' in class")
            for elem in elements[:2]:
                print(f"    - {elem.text.strip()[:50]}")

    # 4. Find category
    print("\n4. LOOKING FOR CATEGORY:")
    # Check for category links
    category_links = soup.find_all("a", href=re.compile("/category/"))
    if category_links:
        print(f"  Found {len(category_links)} category links:")
        for link in category_links[:3]:
            print(f"    - {link.text.strip()}: {link.get('href')}")
            findings["category_example"] = link.text.strip()

    # 5. Check data attributes
    print("\n5. CHECKING DATA ATTRIBUTES:")
    # Look for React/Next.js data
    script_tags = soup.find_all("script", type="application/json")
    if script_tags:
        print(f"  Found {len(script_tags)} JSON script tags")
        for i, script in enumerate(script_tags[:2]):
            try:
                data = json.loads(script.string)
                print(f"    Script {i+1} keys: {list(data.keys())[:5]}")
                # Save for inspection
                with open(f"output/json_data_{i+1}.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(f"    Saved to: output/json_data_{i+1}.json")
            except:
                pass

    # Check for Next.js data
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data:
        print("  Found __NEXT_DATA__ script!")
        try:
            data = json.loads(next_data.string)
            with open("output/next_data.json", "w") as f:
                json.dump(data, f, indent=2)
            print("  Saved to: output/next_data.json")

            # Try to find relevant data in Next.js structure
            if "props" in data and "pageProps" in data["props"]:
                page_props = data["props"]["pageProps"]
                print(f"  pageProps keys: {list(page_props.keys())}")
                findings["next_data_available"] = True
        except:
            pass

    # 6. Analyze overall structure
    print("\n6. PAGE STRUCTURE SUMMARY:")
    print(f"  Total divs: {len(soup.find_all('div'))}")
    print(f"  Total links: {len(soup.find_all('a'))}")
    print(f"  Total buttons: {len(soup.find_all('button'))}")

    # Find main content containers
    main_containers = soup.find_all(["main", "section", "article"])
    print(f"  Main containers: {len(main_containers)}")

    # Save findings
    with open("output/structure_findings.json", "w") as f:
        json.dump(findings, f, indent=2)
    print("\nFindings saved to: output/structure_findings.json")

    return findings


def explore_discovery_page():
    """Explore the discovery/browse page"""
    print("\n" + "=" * 60)
    print("EXPLORING DISCOVERY PAGE")
    print("=" * 60)

    url = "https://whop.com/discover"
    print(f"\nFetching: {url}")

    html = get_page(url)
    if not html:
        print("Failed to fetch discovery page!")
        return

    soup = BeautifulSoup(html, "html.parser")

    # Find community cards/links
    print("\n1. LOOKING FOR COMMUNITY CARDS:")

    # Common card patterns
    cards = soup.find_all("a", href=re.compile("^/[^/]+$"))
    filtered_cards = [
        c
        for c in cards
        if not any(
            skip in c.get("href", "")
            for skip in ["/login", "/signup", "/discover", "/category"]
        )
    ]

    print(f"  Found {len(filtered_cards)} potential community links")
    if filtered_cards:
        print("  First 5 community URLs:")
        for card in filtered_cards[:5]:
            print(f"    - {card.get('href')}: {card.text.strip()[:30]}")

    # Save sample HTML
    with open("output/sample_discovery.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\nSaved discovery page to: output/sample_discovery.html")


def main():
    """Main function - Extract community URLs from discover sitemap"""
    print("=" * 60)
    print("WHOP COMMUNITY URL EXTRACTOR")
    print("=" * 60)
    print("\nExtracting community URLs from discover sitemap")

    # Create output directory
    import os

    if not os.path.exists("output"):
        os.makedirs("output")

    # Extract community URLs from discover sitemap
    sample_community_url = explore_sitemap()

    # COMMENTED OUT - Focus only on extracting URLs
    # # Step 2: Explore a community page
    # if sample_community_url:
    #     explore_community_page(sample_community_url)
    # else:
    #     print("\nNo sample URL found in sitemap.")

    # # Step 3: Explore discovery page
    # explore_discovery_page()

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE!")
    print("=" * 60)
    print("\nCheck the 'output' folder for:")
    print("  - sample_discovery.txt - Community URLs from discover sitemap")
    print("\nNext: Update scrape.py to read from sample_discovery.txt")


if __name__ == "__main__":
    main()
