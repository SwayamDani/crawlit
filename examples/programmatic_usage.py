#!/usr/bin/env python3
"""
Example of using crawlit programmatically as a library in your own Python applications.

This example shows how to:
1. Initialize the crawler with custom parameters
2. Process results as they come in
3. Save results in different formats
4. Generate custom reports
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path to make imports work when running this file directly
sys.path.append(str(Path(__file__).parent.parent))

# Import the crawler components
from crawlit.crawler.engine import Crawler
from crawlit.output.formatters import save_results, generate_summary_report

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Example of programmatically using crawlit"""
    try:
        # Record start time for duration calculation
        start_time = datetime.now()
        
        # Example URL - replace with your target
        target_url = "https://example.com"
        
        # Initialize the crawler with custom parameters
        crawler = Crawler(
            start_url=target_url,
            max_depth=2,                     # Crawl up to 2 links deep
            internal_only=True,              # Only crawl within the same domain
            user_agent="MyCustomBot/1.0",    # Set a custom user agent
            delay=0.5,                       # Wait 0.5 seconds between requests
            respect_robots=True              # Respect robots.txt rules
        )
        
        # Start crawling
        logger.info(f"Starting programmatic crawl from: {target_url}")
        crawler.crawl()
        
        # Get results after crawl is complete
        results = crawler.get_results()
        logger.info(f"Crawl complete. Visited {len(results)} URLs.")
        
        # Example: Get skipped external URLs
        skipped_external = crawler.get_skipped_external_urls()
        logger.info(f"Skipped {len(skipped_external)} external URLs")
        
        # Example: Get URLs skipped due to robots.txt
        skipped_robots = crawler.get_skipped_robots_paths()
        logger.info(f"Skipped {len(skipped_robots)} URLs due to robots.txt rules")
        
        # Example: Access specific types of pages from the results
        html_pages = [url for url, data in results.items() 
                     if data.get('content_type') and data.get('content_type').startswith('text/html')]
        logger.info(f"Found {len(html_pages)} HTML pages")
        
        # Example: Filter results by status code
        successful_pages = {url: data for url, data in results.items() if data.get('status') == 200}
        logger.info(f"Found {len(successful_pages)} pages with 200 OK status")
        
        # Example: Save results in different formats
        save_results(results, "json", "programmatic_results.json", pretty_json=True)
        save_results(results, "csv", "programmatic_results.csv")
        
        # Generate and display a summary report
        summary = generate_summary_report(results)
        print("\nCrawl Summary Report:")
        print(summary)
        
        # Calculate and display crawl duration
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Total crawl time: {duration}")
        
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())