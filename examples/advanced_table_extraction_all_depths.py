#!/usr/bin/env python3
"""
Advanced example for table extraction at all depths with robots.txt bypassing.

This example script demonstrates:
1. How to use the crawlit/2.0 user agent to enable table extraction
2. How to bypass robots.txt for testing purposes
3. How to extract tables from pages at all depths
"""

from crawlit.crawler.engine import Crawler
from crawlit.extractors.tables import extract_and_save_tables_from_crawl
import logging
import os
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Advanced table extraction with robots.txt bypass")
    parser.add_argument("--url", required=True, help="URL to start crawling from")
    parser.add_argument("--depth", type=int, default=2, help="Maximum crawl depth (default: 2)")
    parser.add_argument("--output-dir", default="extracted_tables", help="Directory for saving tables")
    parser.add_argument("--min-rows", type=int, default=1, help="Minimum number of rows in tables")
    parser.add_argument("--min-columns", type=int, default=2, help="Minimum number of columns in tables")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format for tables")
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Configure crawler with crawlit/2.0 user agent and robots.txt disabled
    logger.info("Initializing crawler with table extraction support (crawlit/2.0)...")
    crawler = Crawler(
        start_url=args.url,
        max_depth=args.depth,
        internal_only=True,  # Stay within same domain
        user_agent="crawlit/2.0",  # Required for table extraction
        delay=0.2,  # Be gentle with the server
        respect_robots=False  # Bypass robots.txt for testing multi-depth extraction
    )
    
    # Start crawling
    logger.info(f"Starting crawl from {args.url} with depth {args.depth}...")
    logger.warning("robots.txt restrictions bypassed for testing purposes")
    crawler.crawl()
    
    # Get crawl results
    results = crawler.get_results()
    count_by_depth = {}
    
    # Count pages by depth
    for url, data in results.items():
        depth = data.get("depth", 0)
        count_by_depth[depth] = count_by_depth.get(depth, 0) + 1
    
    # Report crawled pages by depth
    logger.info(f"Crawl complete. Visited {len(results)} pages:")
    for depth, count in sorted(count_by_depth.items()):
        logger.info(f"  Depth {depth}: {count} pages")
    
    # Extract tables from all pages
    logger.info(f"Extracting tables from {len(results)} pages at all depths...")
    stats = extract_and_save_tables_from_crawl(
        results=results,
        output_dir=args.output_dir,
        output_format=args.format,
        min_rows=args.min_rows,
        min_columns=args.min_columns,
        max_depth=args.depth  # Extract tables up to the maximum crawl depth
    )
    
    # Report extraction results
    if stats["total_tables_found"] > 0:
        logger.info(f"Extracted {stats['total_tables_found']} tables from {stats['total_pages_with_tables']} pages")
        logger.info(f"Saved {stats['total_files_saved']} files to {args.output_dir}/")
        
        # Show tables by depth
        for depth, count in sorted(stats["tables_by_depth"].items()):
            logger.info(f"  Depth {depth}: {count} tables")
            
        # Show some URLs with tables
        if stats["urls_with_tables"]:
            logger.info("Example URLs with tables:")
            for url in stats["urls_with_tables"][:3]:  # Show first 3 examples
                logger.info(f"  {url}")
    else:
        logger.info("No tables found on any crawled pages.")

if __name__ == "__main__":
    main()
