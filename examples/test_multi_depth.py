#!/usr/bin/env python3
"""
Test script for multi-depth table extraction with robots.txt bypass.
"""

import argparse
import logging
import os
from crawlit.crawler.engine import Crawler
from crawlit.extractors.tables import extract_and_save_tables_from_crawl

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Test multi-depth table extraction")
    parser.add_argument("--url", default="https://www.worldometers.info/world-population/population-by-country/",
                      help="URL to crawl")
    parser.add_argument("--depth", type=int, default=2, help="Crawl depth")
    parser.add_argument("--output-dir", default="multi_depth_tables",
                      help="Output directory for tables")
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize crawler with robots.txt bypass
    logger.info(f"Starting crawl of {args.url} with depth {args.depth}")
    crawler = Crawler(
        start_url=args.url,
        max_depth=args.depth,
        user_agent="crawlit/2.0",
        respect_robots=False,  # Bypass robots.txt entirely for testing
        internal_only=True,
        delay=0.2
    )
    
    # Start the crawl
    logger.info("Crawling started (robots.txt bypassed for testing)")
    crawler.crawl()
    
    # Get the results
    results = crawler.get_results()
    logger.info(f"Crawl complete. Visited {len(results)} pages")
    
    # Count pages by depth
    depth_counts = {}
    for url, data in results.items():
        depth = data.get("depth", 0)
        depth_counts[depth] = depth_counts.get(depth, 0) + 1
    
    for depth, count in sorted(depth_counts.items()):
        logger.info(f"Depth {depth}: {count} pages")
    
    # Extract tables
    logger.info(f"Extracting tables from all crawled pages...")
    stats = extract_and_save_tables_from_crawl(
        results=results,
        output_dir=args.output_dir,
        output_format="csv",
        min_rows=1,
        min_columns=2
    )
    
    # Report results
    if stats["total_tables_found"] > 0:
        logger.info(f"Found {stats['total_tables_found']} tables on {stats['total_pages_with_tables']} pages")
        logger.info(f"Saved {stats['total_files_saved']} files to {args.output_dir}/")
        
        # Show tables by depth
        logger.info("Tables by depth:")
        for depth, count in sorted(stats["tables_by_depth"].items()):
            logger.info(f"  Depth {depth}: {count} tables")
    else:
        logger.info("No tables found on any crawled pages")

if __name__ == "__main__":
    main()
