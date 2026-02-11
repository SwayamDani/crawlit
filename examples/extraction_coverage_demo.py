#!/usr/bin/env python3
"""
extraction_coverage_demo.py - Demonstrate the enhanced extraction coverage features
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add the parent directory to sys.path to import the library
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawlit.crawler.engine import Crawler
from crawlit.crawler.async_engine import AsyncCrawler
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def save_results(results, filename):
    """Save crawl results to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {filename}")

def display_extracted_metadata(results):
    """Display the extracted metadata fields for each page"""
    print("\n=== EXTRACTION COVERAGE DEMONSTRATION ===\n")
    
    for url, data in results.items():
        if not data.get('success', False):
            continue
            
        print(f"\nURL: {url}")
        print(f"Title: {data.get('title')}")
        print(f"Meta Description: {data.get('meta_description')}")
        print(f"Meta Keywords: {', '.join(data.get('meta_keywords', []))}")
        print(f"Canonical URL: {data.get('canonical_url')}")
        print(f"Language: {data.get('language')}")
        print(f"Page Type: {data.get('page_type')}")
        print(f"Last Modified: {data.get('last_modified')}")
        print(f"HTTP Status: {data.get('status')}")
        
        # Print heading hierarchy
        if data.get('headings'):
            print("\nHeading Hierarchy:")
            for heading in data.get('headings', [])[:3]:  # Show first 3 headings
                print(f"  {'#' * heading['level']} {heading['text']}")
            if len(data.get('headings', [])) > 3:
                print(f"  ... and {len(data.get('headings', [])) - 3} more headings")
        
        # Show images with context
        if data.get('images_with_context'):
            print("\nImages with Context:")
            for img in data.get('images_with_context', [])[:2]:  # Show first 2 images
                print(f"  Image: {img['src']}")
                print(f"  Alt: {img['alt']}")
                print(f"  Context: {img['context'][:100]}..." if len(img['context']) > 100 else f"  Context: {img['context']}")
            if len(data.get('images_with_context', [])) > 2:
                print(f"  ... and {len(data.get('images_with_context', [])) - 2} more images")
        
        print("\n" + "=" * 50)

def run_sync_crawler():
    """Run a synchronous crawler with all extraction features enabled"""
    print("\nStarting synchronous crawler...")
    
    # Create a crawler instance with our start URL
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=1,
        respect_robots=True,
        enable_image_extraction=True,
        enable_keyword_extraction=True,
        enable_table_extraction=True
    )
    
    # Start the crawl
    crawler.crawl()
    
    # Get the results
    results = crawler.get_results()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"extraction_demo_sync_{timestamp}.json"
    save_results(results, filename)
    
    # Display the metadata extraction results
    display_extracted_metadata(results)
    
    return results

async def run_async_crawler():
    """Run an asynchronous crawler with all extraction features enabled"""
    print("\nStarting asynchronous crawler...")
    
    # Create an async crawler instance with our start URL
    crawler = AsyncCrawler(
        start_url="https://example.com",
        max_depth=1,
        respect_robots=True,
        enable_image_extraction=True,
        enable_keyword_extraction=True,
        enable_table_extraction=True
    )
    
    # Start the crawl
    await crawler.crawl()
    
    # Get the results
    results = crawler.results
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"extraction_demo_async_{timestamp}.json"
    save_results(results, filename)
    
    # Display the metadata extraction results
    display_extracted_metadata(results)
    
    return results

if __name__ == "__main__":
    # Choose whether to run sync or async crawler
    mode = input("Run in [s]ync or [a]sync mode? (s/a): ").lower()
    
    if mode == 'a':
        # Run the async crawler
        asyncio.run(run_async_crawler())
    else:
        # Run the sync crawler
        run_sync_crawler()
