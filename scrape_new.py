#!/usr/bin/env python3
"""
Updated Whop Communities Scraper - Batch Processing by URL Ranges
Run: python scrape_new.py <batch_number>
Example: python scrape_new.py 1 (processes URLs 0-10000)
         python scrape_new.py 2 (processes URLs 10000-20000)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
import os
import gc
import sys

# Configuration
BASE_URL = "https://whop.com"
DELAY_BETWEEN_REQUESTS = 1.5  # Seconds between requests
OUTPUT_DIR = "output"

# Create output directory
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def log_message(message):
    """Simple logging to console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(f"{OUTPUT_DIR}/scrape_log.txt", "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def get_page(url, retries=3):
    """Fetch a page with retry logic"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:  # Rate limited
                wait_time = (attempt + 1) * 5
                log_message(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
        except Exception as e:
            log_message(f"Error fetching {url}: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None

def scrape_community_page(url):
    """Scrape data from individual community page - updated for current Whop structure"""
    html = get_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Extract the slug from URL (e.g., "realtraders-community" from the URL)
    url_parts = url.split('/')
    slug = ''
    for part in url_parts:
        if '?' in part:
            slug = part.split('?')[0]
            break
        elif part and part not in ['https:', '', 'whop.com', 'discover']:
            slug = part

    # Extract productId from URL if present
    product_id = ''
    if 'productId=' in url:
        product_id = url.split('productId=')[1].split('&')[0]

    community_data = {
        'url': url,
        'url_slug': slug,
        'product_id': product_id,
        'scraped_at': datetime.now().isoformat()
    }

    # METHOD 1: Extract from JSON-LD structured data (most reliable)
    json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
    product_data = None
    for script in json_ld_scripts:
        try:
            structured_data = json.loads(script.string)
            # Handle multiple JSON-LD scripts - find the Product one
            if isinstance(structured_data, list):
                for item in structured_data:
                    if item.get('@type') == 'Product':
                        product_data = item
                        break
            elif structured_data.get('@type') == 'Product':
                product_data = structured_data

            if product_data:
                break  # Found Product data, stop searching
        except Exception as e:
            log_message(f"Error parsing JSON-LD script: {e}")
            continue

    if product_data:
        try:
            # Extract data from structured JSON-LD
            community_data['community_name'] = product_data.get('name', 'Unknown')
            community_data['description'] = product_data.get('description', '')[:500]

            # Extract ratings from aggregateRating
            aggregate_rating = product_data.get('aggregateRating', {})
            if aggregate_rating:
                community_data['average_rating'] = float(aggregate_rating.get('ratingValue', 0))
                community_data['reviews_count'] = int(aggregate_rating.get('reviewCount', 0))
            else:
                community_data['average_rating'] = 0.0
                community_data['reviews_count'] = 0

            # Extract brand/creator
            brand = product_data.get('brand', {})
            if brand:
                community_data['creator_name'] = brand.get('name', '')
            else:
                community_data['creator_name'] = ''

            # Category - map based on rank.py expected categories
            desc = community_data['description'].lower()
            name = community_data['community_name'].lower()
            combined_text = desc + ' ' + name

            if any(word in combined_text for word in ['trading', 'forex', 'crypto', 'bitcoin', 'stocks', 'investment']):
                community_data['category'] = 'Trading'
            elif any(word in combined_text for word in ['ecommerce', 'e-commerce', 'dropship', 'amazon', 'shopify']):
                community_data['category'] = 'E-commerce'
            elif any(word in combined_text for word in ['real estate', 'property', 'realestate']):
                community_data['category'] = 'Real Estate'
            elif any(word in combined_text for word in ['finance', 'financial', 'money', 'wealth']):
                community_data['category'] = 'Finance'
            elif any(word in combined_text for word in ['crypto', 'cryptocurrency', 'bitcoin', 'ethereum', 'nft']):
                community_data['category'] = 'Crypto'
            elif any(word in combined_text for word in ['education', 'course', 'learn', 'tutorial', 'training']):
                community_data['category'] = 'Education'
            else:
                community_data['category'] = 'Other'

            # Price handling - try to extract from HTML after JSON-LD
            log_message(f"Extracted from JSON-LD: {community_data['community_name']}")

            # Fall through to extract pricing from HTML since JSON-LD doesn't have price info

        except Exception as e:
            log_message(f"Failed to parse JSON-LD: {e}")

    # METHOD 2: Extract rating and review data from HTML (if not in JSON-LD)
    if not community_data.get('average_rating'):
        try:
            # Look for "X out of 5" pattern
            rating_text = soup.find(string=re.compile(r'(\d+(?:\.\d+)?)\s+out\s+of\s+5', re.I))
            if rating_text:
                rating_match = re.search(r'(\d+(?:\.\d+)?)\s+out\s+of\s+5', rating_text, re.I)
                if rating_match:
                    community_data['average_rating'] = float(rating_match.group(1))
                    log_message(f"Found rating: {community_data['average_rating']}")

            # Look for "X ratings & reviews" pattern
            reviews_text = soup.find(string=re.compile(r'(\d+)\s+ratings?\s*&?\s*reviews?', re.I))
            if reviews_text:
                reviews_match = re.search(r'(\d+)\s+ratings?\s*&?\s*reviews?', reviews_text, re.I)
                if reviews_match:
                    community_data['reviews_count'] = int(reviews_match.group(1))
                    log_message(f"Found reviews: {community_data['reviews_count']}")

        except Exception as e:
            log_message(f"Error extracting rating/reviews: {e}")

    # METHOD 3: Extract from HTML meta tags (fallback)
    if not community_data.get('community_name') or community_data.get('community_name') == 'Unknown':
        try:
            # Get community name from meta tags or title
            og_title = soup.find('meta', {'property': 'og:title'})
            title = soup.find('title')

            if og_title:
                community_data['community_name'] = og_title.get('content', 'Unknown')
            elif title:
                title_text = title.text.strip()
                # Remove " | Whop" suffix if present
                if ' | Whop' in title_text:
                    community_data['community_name'] = title_text.replace(' | Whop', '')
                else:
                    community_data['community_name'] = title_text
            else:
                community_data['community_name'] = 'Unknown'

            # Get description from meta tags
            og_description = soup.find('meta', {'property': 'og:description'})
            meta_description = soup.find('meta', {'name': 'description'})

            if og_description:
                community_data['description'] = og_description.get('content', '')[:500]
            elif meta_description:
                community_data['description'] = meta_description.get('content', '')[:500]
            else:
                community_data['description'] = ''

            log_message(f"Extracted from meta tags: {community_data['community_name']}")

        except Exception as e:
            log_message(f"Error in HTML extraction: {e}")

    # Set defaults for missing data
    if not community_data.get('average_rating'):
        community_data['average_rating'] = 0.0
    if not community_data.get('reviews_count'):
        community_data['reviews_count'] = 0
    if not community_data.get('creator_name'):
        community_data['creator_name'] = ''
    if not community_data.get('category'):
        community_data['category'] = 'Other'
    if not community_data.get('community_name'):
        community_data['community_name'] = 'Unknown'
    if not community_data.get('description'):
        community_data['description'] = ''

    # FINAL STEP: Extract pricing information from HTML (works for both JSON-LD and fallback cases)
    try:
        price_extracted = False

        # Method 1: Look for radio button with price pattern (like "$3,000.00 one-time purchase")
        radio_buttons = soup.find_all(['div', 'span'], class_=re.compile(r'fui-RadioButtonGroup|radio', re.I))
        for radio in radio_buttons:
            radio_text = radio.get_text().strip()
            # Look for price pattern with commas: $3,000.00 or $39.99
            price_match = re.search(r'\$([0-9,]+(?:\.[0-9]{2})?)', radio_text)
            if price_match:
                price_value_str = price_match.group(1).replace(',', '')
                price_value = float(price_value_str)

                # Determine billing period from the text
                if re.search(r'one-?time|lifetime', radio_text, re.I):
                    period = "one-time purchase"
                    community_data['price_monthly_usd'] = price_value  # Keep as-is for one-time
                elif re.search(r'week|weekly', radio_text, re.I):
                    period = "week"
                    community_data['price_monthly_usd'] = price_value * 4.33  # Convert to monthly
                elif re.search(r'year|yearly|annual', radio_text, re.I):
                    period = "year"
                    community_data['price_monthly_usd'] = price_value / 12  # Convert to monthly
                elif re.search(r'day|daily', radio_text, re.I):
                    period = "day"
                    community_data['price_monthly_usd'] = price_value * 30  # Convert to monthly
                else:
                    period = "month"
                    community_data['price_monthly_usd'] = price_value

                community_data['price_display'] = f"${price_value:.2f} / {period}"
                community_data['is_free'] = False
                price_extracted = True
                log_message(f"Found price in radio button: ${price_value:.2f} / {period}")
                break

        # Method 2: Look for button text with pricing
        if not price_extracted:
            buttons = soup.find_all(['button', 'a'], string=re.compile(r'\$[\d,]+\.?\d*', re.I))
            for button in buttons:
                button_text = button.get_text().strip()
                price_match = re.search(r'\$([0-9,]+(?:\.[0-9]{2})?)', button_text)
                if price_match:
                    price_value_str = price_match.group(1).replace(',', '')
                    price_value = float(price_value_str)
                    community_data['price_monthly_usd'] = price_value
                    community_data['price_display'] = f"${price_value:.2f} / month"
                    community_data['is_free'] = False
                    price_extracted = True
                    log_message(f"Found price in button: {button_text}")
                    break

        # Method 3: Look for price in any text containing dollar signs
        if not price_extracted:
            price_elements = soup.find_all(string=re.compile(r'\$[\d,]+\.?\d*'))
            for element in price_elements:
                # Skip script tags
                if element.parent.name in ['script', 'style']:
                    continue

                price_text = str(element).strip()
                price_match = re.search(r'\$([0-9,]+(?:\.[0-9]{2})?)', price_text)
                if price_match:
                    price_value_str = price_match.group(1).replace(',', '')
                    price_value = float(price_value_str)

                    # Determine billing period
                    period = "month"
                    if re.search(r'one-?time|lifetime', price_text, re.I):
                        period = "one-time purchase"
                        community_data['price_monthly_usd'] = price_value  # Keep as-is for one-time
                    elif re.search(r'week|weekly', price_text, re.I):
                        period = "week"
                        community_data['price_monthly_usd'] = price_value * 4.33  # Convert to monthly
                    elif re.search(r'year|yearly|annual', price_text, re.I):
                        period = "year"
                        community_data['price_monthly_usd'] = price_value / 12  # Convert to monthly
                    elif re.search(r'day|daily', price_text, re.I):
                        period = "day"
                        community_data['price_monthly_usd'] = price_value * 30  # Convert to monthly
                    else:
                        community_data['price_monthly_usd'] = price_value  # Assume monthly

                    community_data['price_display'] = f"${price_value:.2f} / {period}"
                    community_data['is_free'] = False
                    price_extracted = True
                    log_message(f"Found price in text: {price_text}")
                    break

        # Method 4: Look for "Free" or similar
        if not price_extracted:
            free_indicators = soup.find_all(string=re.compile(r'\bfree\b|\$0\b|no cost', re.I))
            if free_indicators:
                community_data['price_monthly_usd'] = 0
                community_data['price_display'] = "Free"
                community_data['is_free'] = True
                price_extracted = True
                log_message("Found free pricing indicator")

        # Default if no price found
        if not price_extracted:
            community_data['price_monthly_usd'] = 0
            community_data['price_display'] = "Unknown"
            community_data['is_free'] = False

    except Exception as e:
        log_message(f"Error extracting price: {e}")
        community_data['price_monthly_usd'] = 0
        community_data['price_display'] = "Unknown"
        community_data['is_free'] = False

    return community_data

def process_sitemap_and_scrape(sitemap_url, output_file, all_communities, communities_batch, batch_size):
    """Process a single product sitemap URL, extract community URL, scrape it, and save data"""
    try:
        # Get the XML content of the product sitemap
        xml_content = get_page(sitemap_url)
        if not xml_content:
            log_message(f"Failed to fetch sitemap: {sitemap_url}")
            return communities_batch

        # Extract all URLs from this product sitemap
        urls_in_sitemap = re.findall(r'<loc>([^<]+)</loc>', xml_content)

        # Find the community URL (not /app/ URLs)
        community_url = None
        for url in urls_in_sitemap:
            if '/app/' not in url and url.startswith('https://whop.com/discover/'):
                community_url = url
                break

        if not community_url:
            log_message(f"No community URL found in sitemap: {sitemap_url}")
            return communities_batch

        log_message(f"Found community URL: {community_url}")

        # Scrape the community page immediately
        community_data = scrape_community_page(community_url)
        if community_data and community_data.get('community_name', 'Unknown') != 'Unknown':
            communities_batch.append(community_data)
            log_message(f"Successfully scraped: {community_data['community_name']}")

            # Save data to file every batch_size communities
            if len(communities_batch) >= batch_size:
                all_communities.extend(communities_batch)

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(all_communities, f, indent=2)

                log_message(f"Saved batch of {len(communities_batch)} communities. Total: {len(all_communities)}")
                communities_batch.clear()
                gc.collect()

        else:
            log_message(f"Failed to scrape community: {community_url}")

        # Small delay between requests
        time.sleep(DELAY_BETWEEN_REQUESTS)

    except Exception as e:
        log_message(f"Error processing sitemap {sitemap_url}: {e}")

    return communities_batch

def read_and_process_urls_batch(batch_number):
    """Read product sitemap URLs from file and process a specific batch range"""
    file_path = f"{OUTPUT_DIR}/sample_discovery.txt"

    try:
        with open(file_path, "r") as f:
            product_sitemap_urls = [line.strip() for line in f if line.strip().startswith("https://")]

        log_message(f"Read {len(product_sitemap_urls)} product sitemap URLs from {file_path}")

    except FileNotFoundError:
        log_message(f"Error: File {file_path} not found!")
        log_message("Please run 'python explore.py' first to generate the URLs file.")
        return
    except Exception as e:
        log_message(f"Error reading {file_path}: {e}")
        return

    # Calculate batch range
    batch_size_urls = 10000  # Process 10k URLs per batch
    start_index = (batch_number - 1) * batch_size_urls
    end_index = min(start_index + batch_size_urls, len(product_sitemap_urls))

    if start_index >= len(product_sitemap_urls):
        log_message(f"Batch {batch_number} is out of range. Total URLs: {len(product_sitemap_urls)}")
        return 0

    batch_urls = product_sitemap_urls[start_index:end_index]
    log_message(f"Processing batch {batch_number}: URLs {start_index} to {end_index} ({len(batch_urls)} URLs)")

    # Initialize data structures
    output_file = f"{OUTPUT_DIR}/raw_communities_batch_{batch_number}.json"
    communities_batch = []
    batch_size = 15

    # Load existing data if file exists
    all_communities = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                all_communities = json.load(f)
            log_message(f"Loaded {len(all_communities)} existing communities from batch file")
        except:
            all_communities = []

    # Process each sitemap URL in this batch
    log_message(f"Starting batch {batch_number} processing: sitemap -> community URL -> scrape -> save")

    for i, sitemap_url in enumerate(batch_urls, 1):
        log_message(f"Processing sitemap {start_index + i}/{len(product_sitemap_urls)}: {sitemap_url}")

        communities_batch = process_sitemap_and_scrape(
            sitemap_url, output_file, all_communities, communities_batch, batch_size
        )

        if i % 50 == 0:
            log_message(f"Batch {batch_number} progress: {i}/{len(batch_urls)} sitemaps processed. Total communities: {len(all_communities)}")

    # Save any remaining communities in the final batch
    if communities_batch:
        all_communities.extend(communities_batch)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_communities, f, indent=2)
        log_message(f"Saved final batch of {len(communities_batch)} communities")

    log_message(f"Batch {batch_number} processing complete! Total communities scraped: {len(all_communities)}")
    return len(all_communities)

def main():
    """Main scraping function - Batch processing version"""
    if len(sys.argv) != 2:
        print("Usage: python scrape_new.py <batch_number>")
        print("Example: python scrape_new.py 1  (processes URLs 0-10000)")
        print("         python scrape_new.py 2  (processes URLs 10000-20000)")
        print("         python scrape_new.py 3  (processes URLs 20000-30000)")
        sys.exit(1)

    try:
        batch_number = int(sys.argv[1])
        if batch_number < 1:
            print("Batch number must be 1 or greater")
            sys.exit(1)
    except ValueError:
        print("Batch number must be an integer")
        sys.exit(1)

    log_message("Starting Updated Whop Communities Scraper...")
    log_message(f"Processing batch {batch_number} (10k URLs per batch)")
    log_message("Using batch processing: sitemap -> community URL -> scrape -> save")

    # Process URLs for this batch
    total_communities = read_and_process_urls_batch(batch_number)

    if total_communities is None:
        log_message("Batch processing failed! Please check your sample_discovery.txt file.")
        return

    # Final summary
    log_message("="*50)
    log_message(f"Batch {batch_number} Scraping Complete!")
    log_message(f"Total communities scraped in this batch: {total_communities}")
    log_message(f"Data saved to: {OUTPUT_DIR}/raw_communities_batch_{batch_number}.json")
    log_message("="*50)
    log_message("To merge all batches, run the merge script after all batches complete")

if __name__ == "__main__":
    main()
