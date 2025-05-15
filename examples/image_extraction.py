#!/usr/bin/env python3
"""
Example of using Crawlit's image extraction feature

This example demonstrates how to:
1. Set up a crawler
2. Crawl a website
3. Examine and process extracted images
"""

import os
import sys
import logging
from pprint import pprint

# Add parent directory to path to import from crawlit
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawlit.crawler.engine import Crawler

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    # Example URL - replace with your target website
    url = "https://swayamdani.com"
    
    print(f"Starting crawler on {url}")
    
    # Create the crawler with default settings
    crawler = Crawler(
        start_url=url,
        max_depth=1,  # Only crawl 2 levels deep
        internal_only=False,  # Only stay within the same domain
        respect_robots=True,  # Respect robots.txt directives
    )
    
    # Start the crawling process
    crawler.crawl()
    
    # Get the results
    results = crawler.get_results()
    
    # Process and display images from each page
    total_images = 0
    
    print("\n=== Extracted Images ===\n")
    
    for url, page_data in results.items():
        if not page_data['success']:
            continue
            
        # Check if images were extracted for this page
        if 'images' in page_data and page_data['images']:
            num_images = len(page_data['images'])
            total_images += num_images
            
            print(f"\n--- {url} ({num_images} images) ---")
            
            # Display information about each image
            for i, img in enumerate(page_data['images'], 1):
                print(f"\n{i}. Image:")
                print(f"   Source: {img.get('src', 'N/A')}")
                print(f"   Alt text: {img.get('alt', 'None')}")
                
                # Print dimensions if available
                if 'width' in img and 'height' in img:
                    print(f"   Dimensions: {img['width']}x{img['height']}")
                
                # Print if the image is decorative
                print(f"   Decorative: {img.get('decorative', False)}")
                
                # Print parent tag for context
                if 'parent_tag' in img:
                    print(f"   Container: <{img['parent_tag']}>")
    
    print(f"\nTotal images found: {total_images}")
    
    # Example of filtering for images without alt text (accessibility issues)
    missing_alt = 0
    for url, page_data in results.items():
        if 'images' in page_data:
            for img in page_data['images']:
                if img.get('decorative', False):
                    missing_alt += 1
    
    if missing_alt > 0:
        print(f"\nAccessibility note: {missing_alt} images are missing alt text")

if __name__ == "__main__":
    main()