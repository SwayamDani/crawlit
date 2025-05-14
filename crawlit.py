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
from crawler.engine import Crawler
from output.formatters import save_results, generate_summary_report

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="crawlit - Modular, Ethical Python Web Crawler",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--url", "-u", required=True, help="Target website URL")
    parser.add_argument("--depth", "-d", type=int, default=3, help="Maximum crawl depth")
    parser.add_argument("--output-format", "-f", default="json", choices=["json", "csv", "txt"], 
                        help="Output format (json, csv, txt)")
    parser.add_argument("--output", "-O", default="crawl_results.json", help="File to save results")
    parser.add_argument("--ignore-robots", "-i", action="store_true", default=False, 
                       help="Ignore robots.txt rules when crawling")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    parser.add_argument("--user-agent", "-a", default="crawlit/1.0", help="Custom User-Agent string")
    parser.add_argument("--allow-external", "-e", action="store_true", default=False, 
                        help="Allow crawling URLs outside the initial domain")
    parser.add_argument("--summary", "-s", action="store_true", default=False,
                        help="Show a summary of crawl results at the end")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    return parser.parse_args()

def main():
    """Main entry point for the crawler"""
    args = parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
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
        
        # Report skipped external URLs if domain restriction is enabled
        if not args.allow_external and hasattr(crawler, 'get_skipped_external_urls'):
            skipped = crawler.get_skipped_external_urls()
            if skipped:
                logger.info(f"Skipped {len(skipped)} external URLs (use --allow-external to crawl them)")
        
        # Save results to file in the specified format
        output_path = save_results(results, args.output_format, args.output)
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