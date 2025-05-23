#!/usr/bin/env python3
"""
Example of using crawlit programmatically as a library in your own Python applications.

This example shows how to:
1. Initialize the crawler with custom parameters
2. Process results as they come in
3. Save results in different formats
4. Generate custom reports
5. Use various extractors (tables, images, keywords)
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
import requests

# Import the crawler components
from crawlit import Crawler, save_results, generate_summary_report
from crawlit import extract_tables, tables_to_csv, tables_to_dict, tables_to_json
from crawlit import ImageTagParser
from crawlit import KeywordExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def basic_crawl(target_url="https://swayamdani.com"):
    """Example of basic crawling and result processing"""
    # Record start time for duration calculation
    start_time = datetime.now()
    
    # Initialize the crawler with custom parameters
    crawler = Crawler(
        start_url=target_url,
        max_depth=1,                     # Crawl only homepage and direct links
        internal_only=True,              # Only crawl within the same domain
        user_agent="MyCustomBot/2.0",    # Set a custom user agent
        delay=0.5,                       # Wait 0.5 seconds between requests
        respect_robots=True,             # Respect robots.txt rules
    )
    
    # Start crawling
    crawler.crawl()
    
    # Get results after crawl is complete
    results = crawler.get_results()
    
    # Example: Get skipped external URLs
    skipped_external = crawler.get_skipped_external_urls()
    
    # Example: Get URLs skipped due to robots.txt
    skipped_robots = crawler.get_skipped_robots_paths()
    
    # Example: Access specific types of pages from the results
    html_pages = [url for url, data in results.items() 
                 if data.get('content_type') and data.get('content_type').startswith('text/html')]
    
    # Example: Filter results by status code
    successful_pages = {url: data for url, data in results.items() if data.get('status') == 200}
    
    # Example: Save results in different formats (JSON, CSV, HTML)
    save_results(results, "json", "basic_crawl_results.json", pretty_json=True)
    save_results(results, "csv", "basic_crawl_results.csv")
    save_results(results, "html", "basic_crawl_results.html")
    
    # Generate and display a summary report
    summary = generate_summary_report(results)
    print("\nBasic Crawl Summary Report:")
    print(summary)
    
    # Calculate and display crawl duration
    end_time = datetime.now()
    duration = end_time - start_time
    
    return results

def table_extraction_example(target_url="https://swayamdani.com"):
    """Example of table extraction from a website"""
    
    # Method 1: Extract tables during crawl
    crawler = Crawler(
        start_url=target_url,
        max_depth=1,
        internal_only=True,
        user_agent="crawlit/2.0",  # Required for table extraction
        enable_table_extraction=True  # Enable automatic table extraction
    )
    
    crawler.crawl()
    results = crawler.get_results()
    
    tables_found = {}
    for url, data in results.items():
        if 'tables' in data and data['tables']:
            tables_found[url] = len(data['tables'])
            
            # Example: Save first table to CSV
            if data['tables']:
                table_filename = url.split('://')[1].replace('/', '_').replace('.', '_') + "_table"
                tables_to_csv([data['tables'][0]], table_filename)
    
    # Save results in all formats regardless of tables found
    save_results(results, "json", "table_extraction_results.json", pretty_json=True)
    save_results(results, "csv", "table_extraction_results.csv")
    save_results(results, "html", "table_extraction_results.html")
    
    if not tables_found:        
        # Method 2: Extract tables directly from HTML
        # Fetch a page that might contain tables
        try:
            response = requests.get(
                target_url,
                headers={"User-Agent": "crawlit/example-script"},
                timeout=10
            )
            
            if response.status_code == 200:
                html_content = response.text
                
                # Extract tables with minimum 1 row and 2 columns
                tables = extract_tables(html_content, min_rows=1, min_columns=2)
                
                if tables:
                    
                    # Save to different formats
                    csv_files = tables_to_csv(tables, "direct_extraction_table")
                    
                    # Convert to dictionaries (using first row as headers)
                    table_dicts = tables_to_dict(tables)
                    
                    # Display sample of first table if available
                    if table_dicts and len(table_dicts) > 0 and len(table_dicts[0]) > 0:
                        first_row = table_dicts[0][0]
                    
                    # Save to JSON
                    json_files = tables_to_json(tables, "direct_extraction_table")

        except Exception as e:
            logging.error(f"Error during direct table extraction: {e}")
    
    return tables_found

def image_extraction_example(target_url="https://swayamdani.com"):
    """Example of extracting images from a website"""    
    # Method 1: Extract images during crawl
    crawler = Crawler(
        start_url=target_url,
        max_depth=1,
        internal_only=True,
        user_agent="crawlit/2.0",  # Required for image extraction
        enable_image_extraction=True  # Enable automatic image extraction
    )
    
    crawler.crawl()
    results = crawler.get_results()
    
    # Save results in all formats
    save_results(results, "json", "image_extraction_results.json", pretty_json=True)
    save_results(results, "csv", "image_extraction_results.csv")
    save_results(results, "html", "image_extraction_results.html")
    
    total_images = 0
    missing_alt = 0
    
    # Process images from crawl results
    for url, page_data in results.items():
        if 'images' in page_data and page_data['images']:
            page_images = page_data['images']
            total_images += len(page_images)
            
            # Example: Check for images missing alt text (accessibility issue)
            page_missing_alt = sum(1 for img in page_images if img.get('decorative', False))
            missing_alt += page_missing_alt
        
        # Method 2: Extract images directly from HTML
        try:
            response = requests.get(
                target_url,
                headers={"User-Agent": "crawlit/example-script"},
                timeout=10
            )
            
            if response.status_code == 200:
                html_content = response.text
                
                # Create parser and extract images
                parser = ImageTagParser()
                parser.feed(html_content)
                
                # Process extracted images
                images = parser.images

        except Exception as e:
            logging.error(f"Error during direct image extraction: {e}")
    
    return total_images

def keyword_extraction_example(target_url="https://swayamdani.com"):
    """Example of extracting keywords and phrases from a website"""
    
    # Method 1: Extract keywords during crawl
    crawler = Crawler(
        start_url=target_url,
        max_depth=1,
        internal_only=True,
        user_agent="crawlit/2.0",  # Required for keyword extraction
        enable_keyword_extraction=True  # Enable automatic keyword extraction
    )
    
    crawler.crawl()
    results = crawler.get_results()
    
    # Save results in all formats
    save_results(results, "json", "keyword_extraction_results.json", pretty_json=True)
    save_results(results, "csv", "keyword_extraction_results.csv")
    save_results(results, "html", "keyword_extraction_results.html")
    
    # Process keywords from results
    all_keywords = {}
    all_keyphrases = set()
    
    if not all_keywords and not all_keyphrases:
        
        # Method 2: Extract keywords directly from HTML
        try:
            response = requests.get(
                target_url,
                headers={"User-Agent": "crawlit/example-script"},
                timeout=10
            )
            
            if response.status_code == 200:
                html_content = response.text
                
                # Create extractor and extract keywords
                extractor = KeywordExtractor(min_word_length=4, max_keywords=15)
                # Extract keyphrases
                keyphrases = extractor.extract_keyphrases(html_content)
    
        except Exception as e:
            logging.error(f"Error during direct keyword extraction: {e}")
    
    return {'keywords': all_keywords, 'keyphrases': all_keyphrases}

def main():
    """Run all example demonstrations"""
    try:
        # Record start time for duration calculation
        start_time = datetime.now()
        
        # Example URL - website to crawl
        target_url = "https://swayamdani.com"
        
        # Run basic crawl example
        print("\n" + "="*80)
        print("EXAMPLE 1: BASIC CRAWLING")
        print("="*80)
        basic_results = basic_crawl(target_url)
        
        # Run table extraction example
        print("\n" + "="*80)
        print("EXAMPLE 2: TABLE EXTRACTION")
        print("="*80)
        table_results = table_extraction_example(target_url)
        
        # Run image extraction example
        print("\n" + "="*80)
        print("EXAMPLE 3: IMAGE EXTRACTION")
        print("="*80)
        image_results = image_extraction_example(target_url)
        
        # Run keyword extraction example
        print("\n" + "="*80)
        print("EXAMPLE 4: KEYWORD EXTRACTION")
        print("="*80)
        keyword_results = keyword_extraction_example(target_url)
        
        # Calculate and display total duration
        end_time = datetime.now()
        duration = end_time - start_time
        print("\n" + "="*80)
        print(f"Total time for all examples: {duration}")
        print("="*80)
        
    except KeyboardInterrupt:
        logging.info("Examples interrupted by user.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())