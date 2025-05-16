#!/usr/bin/env python3

import sys
import traceback
from crawlit.crawler.engine import Crawler
from crawlit.output.formatters import save_results
import datetime
import json
import os

try:
    # Initialize the crawler
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=0,  # Just crawl the start URL
        user_agent="crawlit/2.0",  # Use v2.0 to extract HTML content
    )

    # Start crawling
    print("Starting crawl...")
    crawler.crawl()

    # Get results
    results = crawler.get_results()
    print(f"Crawl complete. Visited {len(results)} URLs.")
    
    # Check if results contain HTML content
    print("Checking for HTML content in results...")
    has_html = any('html_content' in data for url, data in results.items())
    print(f"HTML content found in results: {has_html}")

    # Save as JSON with pretty formatting
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_file = save_results(results, output_format="json", pretty=True, output_file="fixed_crawl_results.json")

    print(f"Results saved to {output_file}")
    
    # Read the saved file to check if HTML content was saved
    print("Checking saved JSON file...")
    with open(output_file, 'r') as f:
        saved_data = json.load(f)
        
    # Check if the saved data contains HTML content
    for url, data in saved_data["urls"].items():
        if "html_content" in data:
            print(f"ERROR: HTML content found in saved data for {url}")
        else:
            print(f"SUCCESS: No HTML content in saved data for {url}")
            
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
