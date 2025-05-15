#!/usr/bin/env python3
"""
crawlit.py - Modular, Ethical Python Web Crawler
"""

import argparse
import sys
import logging
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the crawler components
from crawlit.crawler.engine import Crawler
from crawlit.output.formatters import save_results, generate_summary_report

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="crawlit - Modular, Ethical Python Web Crawler",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--url", "-u", required=True, help="Target website URL")
    parser.add_argument("--depth", "-d", type=int, default=3, help="Maximum crawl depth")
    parser.add_argument("--output-format", "-f", default="json", choices=["json", "csv", "txt", "html"], 
                        help="Output format (json, csv, txt, html)")
    parser.add_argument("--output", "-O", default="crawl_results.json", help="File to save results")
    parser.add_argument("--pretty-json", "-p", action="store_true", default=False,
                        help="Enable pretty-print JSON with indentation")
    parser.add_argument("--ignore-robots", "-i", action="store_true", default=False, 
                       help="Ignore robots.txt rules when crawling")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    parser.add_argument("--user-agent", "-a", default="crawlit/1.0", help="Custom User-Agent string")
    parser.add_argument("--allow-external", "-e", action="store_true", default=False, 
                        help="Allow crawling URLs outside the initial domain")
    parser.add_argument("--summary", "-s", action="store_true", default=False,
                        help="Show a summary of crawl results at the end")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # Table extraction options
    parser.add_argument("--extract-tables", "-t", action="store_true", default=False,
                        help="Extract HTML tables from crawled pages")
    parser.add_argument("--tables-output", default="table_output", 
                        help="Directory to save extracted tables")
    parser.add_argument("--tables-format", default="csv", choices=["csv", "json"],
                        help="Format to save extracted tables (csv or json)")
    parser.add_argument("--min-rows", type=int, default=1,
                        help="Minimum number of rows for a table to be extracted")
    parser.add_argument("--min-columns", type=int, default=2,
                        help="Minimum number of columns for a table to be extracted")
    parser.add_argument("--max-table-depth", type=int, default=None,
                        help="Maximum depth to extract tables from (default: same as max crawl depth)")
    
    return parser.parse_args()

def main():
    """Main entry point for the crawler"""
    args = parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    # Check if trying to use table extraction with crawlit/1.0
    if args.extract_tables and args.user_agent != "crawlit/2.0":
        logger.warning("Table extraction (--extract-tables) requires --user-agent crawlit/2.0")
        logger.warning("To extract tables, please use: --user-agent crawlit/2.0")
        logger.warning("Continuing with standard crawl (no table extraction)")
    
    # Check if using other v2.0 features with old user agent
    if args.user_agent != "crawlit/2.0" and (
        args.min_rows != 1 or 
        args.min_columns != 2 or 
        args.max_table_depth is not None or
        args.tables_format != "csv"
    ):
        logger.warning("Table extraction parameters (--min-rows, --min-columns, --max-table-depth, --tables-format) require --user-agent crawlit/2.0")
        logger.warning("These parameters will be ignored with the current user agent.")
    
    try:
        # Record start time for duration calculation
        start_time = datetime.datetime.now()
        
        # Initialize the crawler
        crawler = Crawler(
            start_url=args.url,
            max_depth=args.depth,
            internal_only=not args.allow_external,  # Invert the allow-external flag
            user_agent=args.user_agent,
            delay=args.delay,
            respect_robots=not args.ignore_robots  # Invert the ignore-robots flag
        )
        
        # Start crawling
        logger.info(f"Starting crawl from: {args.url}")
        logger.info(f"Domain restriction is {'disabled' if args.allow_external else 'enabled'}")
        crawler.crawl()
        
        # Get results
        results = crawler.get_results()
        logger.info(f"Crawl complete. Visited {len(results)} URLs.")
        
        # Handle table extraction if enabled
        if args.extract_tables:
            import os
            
            # Check if user is using crawlit/2.0 user agent for table extraction
            is_v2_user_agent = args.user_agent == "crawlit/2.0"
            
            if not is_v2_user_agent:
                # Table extraction is only available with crawlit/2.0
                logger.warning("Table extraction is only available with --user-agent crawlit/2.0")
                logger.warning("To extract tables, please use: --user-agent crawlit/2.0")
                logger.warning("Continuing with standard crawl (no table extraction)")
            else:
                # Table extraction feature - only available in crawlit/2.0
                logger.info(f"Using table extraction feature (crawlit/2.0)...")
                from crawlit.extractors.tables import extract_and_save_tables_from_crawl
                
                # Process all results and extract tables
                stats = extract_and_save_tables_from_crawl(
                    results=results,
                    output_dir=args.tables_output,
                    output_format=args.tables_format,
                    min_rows=args.min_rows,
                    min_columns=args.min_columns,
                    max_depth=args.max_table_depth if args.max_table_depth is not None else args.depth
                )
                
                # Log the results
                if stats["total_tables_found"] > 0:
                    logger.info(f"[crawlit/2.0] Extracted {stats['total_tables_found']} tables from {stats['total_pages_with_tables']} pages, saved to {stats['total_files_saved']} files in {args.tables_output}/")
                    
                    # Log tables by depth
                    for depth, count in sorted(stats["tables_by_depth"].items()):
                        logger.debug(f"[crawlit/2.0] Depth {depth}: {count} tables found")
                else:
                    logger.info("[crawlit/2.0] No tables found on any crawled pages.")
        
        # Report skipped external URLs if domain restriction is enabled
        if not args.allow_external and hasattr(crawler, 'get_skipped_external_urls'):
            skipped = crawler.get_skipped_external_urls()
            if skipped:
                logger.info(f"Skipped {len(skipped)} external URLs (use --allow-external to crawl them)")
        
        # Save results to file in the specified format
        output_path = save_results(results, args.output_format, args.output, args.pretty_json)
        logger.info(f"Results saved to {output_path}")
        
        # Calculate and display crawl duration
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logger.info(f"Total crawl time: {duration}")
        
        # Show summary if requested
        if args.summary:
            print("\n" + generate_summary_report(results))
        
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())