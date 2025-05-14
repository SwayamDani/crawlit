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
    
    def __init__(self, start_url, max_depth=3, internal_only=True, 
                 user_agent="crawlit/1.0", max_retries=3, timeout=10, delay=0.1):
        """Initialize the crawler with given parameters"""
        self.start_url = start_url
        self.max_depth = max_depth
        self.internal_only = internal_only
        self.visited_urls = set()  # Store visited URLs
        self.queue = deque()  # Queue for BFS crawling
        self.results = {}  # Store results with metadata
        
        # Request parameters
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.delay = delay
        
        # Extract domain from start URL for internal-only crawling
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc

    def fetch_page(self, url):
        """
        Fetch a web page with retries and proper error handling
        
        Args:
            url: The URL to fetch
            
        Returns:
            tuple: (success, response_or_error, status_code)
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        retries = 0
        status_code = None
        
        while retries <= self.max_retries:
            try:
                logger.debug(f"Requesting {url} (attempt {retries + 1}/{self.max_retries + 1})")
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=self.timeout
                )
                status_code = response.status_code
                
                # Check if the request was successful
                if response.status_code == 200:
                    return True, response, status_code
                else:
                    logger.warning(f"HTTP Error {response.status_code} for {url}")
                    return False, f"HTTP Error: {response.status_code}", status_code
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout error for {url} (attempt {retries + 1})")
                retries += 1
                status_code = 408  # Request Timeout
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error for {url} (attempt {retries + 1})")
                retries += 1
                status_code = 503  # Service Unavailable
                
            except requests.exceptions.TooManyRedirects:
                logger.warning(f"Too many redirects for {url}")
                return False, "Too many redirects", 310
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {url}: {e}")
                return False, str(e), status_code or 500
        
        return False, f"Max retries ({self.max_retries}) exceeded", status_code or 429

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
            
            # Initialize result data for this URL
            self.results[current_url] = {
                'depth': depth,
                'status': None,
                'headers': None,
                'links': [],
                'content_type': None,
                'error': None,
                'success': False
            }
            
            # Fetch the page using our fetch_page method
            success, response_or_error, status_code = self.fetch_page(current_url)
            
            # Record the HTTP status code
            self.results[current_url]['status'] = status_code
            
            # Mark URL as visited regardless of success
            self.visited_urls.add(current_url)
            
            if success:
                response = response_or_error
                
                # Store response headers
                self.results[current_url]['headers'] = dict(response.headers)
                self.results[current_url]['content_type'] = response.headers.get('Content-Type')
                self.results[current_url]['success'] = True
                
                try:
                    # Process the page to extract links if it's HTML
                    if 'text/html' in response.headers.get('Content-Type', ''):
                        links = self._extract_links(response.text, current_url)
                        self.results[current_url]['links'] = links
                        
                        # Add new links to the queue
                        for link in links:
                            if self._should_crawl(link):
                                self.queue.append((link, depth + 1))
                except Exception as e:
                    logger.error(f"Error processing {current_url}: {e}")
                    self.results[current_url]['error'] = str(e)
            else:
                # Store the error information
                logger.error(f"Failed to fetch {current_url}: {response_or_error}")
                self.results[current_url]['error'] = response_or_error
    
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
        
    def _extract_links(self, html_content, base_url):
        """
        Extract links from HTML content
        
        Args:
            html_content: The HTML content to parse
            base_url: The base URL for resolving relative links
            
        Returns:
            list: List of absolute URLs found in the HTML
        """
        from bs4 import BeautifulSoup
        import time
        
        # Introduce a small delay to be polite to the server
        time.sleep(self.delay)
        
        soup = BeautifulSoup(html_content, 'lxml')
        links = []
        
        # Find all anchor tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            # Skip empty links and javascript links
            if not href or href.startswith('javascript:') or href == '#':
                continue
                
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Normalize the URL (remove fragments, etc.)
            parsed = urlparse(absolute_url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized_url += f"?{parsed.query}"
                
            links.append(normalized_url)
            
        return links
        
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