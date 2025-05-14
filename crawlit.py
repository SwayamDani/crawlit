#!/usr/bin/env python3
"""
crawlit.py - Modular, Ethical Python Web Crawler
"""

import argparse
import sys
from urllib.parse import urlparse, urljoin
import requests
from collections import deque
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class Crawler:
    """Main crawler class that manages the crawling process"""
    
    def __init__(self, start_url, max_depth=3, internal_only=True):
        """Initialize the crawler with given parameters"""
        self.start_url = start_url
        self.max_depth = max_depth
        self.internal_only = internal_only
        self.visited_urls = set()  # Store visited URLs
        self.queue = deque()  # Queue for BFS crawling
        
        # Extract domain from start URL for internal-only crawling
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        
    def crawl(self):
        """Start the crawling process"""
        # Add the starting URL to the queue with depth 0
        self.queue.append((self.start_url, 0))
        
        while self.queue:
            current_url, depth = self.queue.popleft()
            
            # Skip if we've already visited this URL
            if current_url in self.visited_urls:
                continue
                
            # Skip if we've exceeded the maximum depth
            if depth > self.max_depth:
                continue
                
            logger.info(f"Crawling: {current_url} (depth: {depth})")
            
            try:
                # Fetch and process the page
                response = requests.get(current_url, timeout=10)
                self.visited_urls.add(current_url)
                
                # Handle the response (to be implemented)
                # Extract links and add them to the queue
                # Process the page content as needed
                
                # Placeholder for link extraction
                # new_links = extract_links(response.text, current_url)
                # for link in new_links:
                #    if self._should_crawl(link):
                #        self.queue.append((link, depth + 1))
                
            except Exception as e:
                logger.error(f"Error crawling {current_url}: {e}")
    
    def _should_crawl(self, url):
        """Determine if a URL should be crawled based on settings"""
        # Check if URL is already visited
        if url in self.visited_urls:
            return False
            
        # Check if URL is internal when internal_only is True
        if self.internal_only:
            parsed_url = urlparse(url)
            if parsed_url.netloc != self.base_domain:
                return False
                
        return True
        
    def get_results(self):
        """Return the crawl results"""
        return list(self.visited_urls)

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
    parser.add_argument("--output-file", "-o", default="crawl_results.json", help="File to save results")
    parser.add_argument("--respect-robots", "-r", action="store_true", help="Respect robots.txt rules")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    parser.add_argument("--user-agent", default="crawlit/1.0", help="Custom User-Agent string")
    parser.add_argument("--internal-only", "-i", action="store_true", default=True, 
                        help="Only crawl URLs within the same domain")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    return parser.parse_args()

def main():
    """Main entry point for the crawler"""
    args = parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Initialize the crawler
        crawler = Crawler(
            start_url=args.url,
            max_depth=args.depth,
            internal_only=args.internal_only
        )
        
        # Start crawling
        logger.info(f"Starting crawl from: {args.url}")
        crawler.crawl()
        
        # Get and output results
        results = crawler.get_results()
        logger.info(f"Crawl complete. Visited {len(results)} URLs.")
        
        # Future: Save results to file in the specified format
        # save_results(results, args.output_format, args.output_file)
        
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())