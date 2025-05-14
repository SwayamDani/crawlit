#!/usr/bin/env python3
"""
engine.py - Core crawler engine
"""

import logging
from collections import deque
from urllib.parse import urlparse, urljoin

from .fetcher import fetch_page
from .parser import extract_links

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
        self.skipped_external_urls = set()  # Track skipped external URLs
        
        # Request parameters
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.delay = delay
        
        # Extract domain from start URL for internal-only crawling
        self.base_domain = self._extract_base_domain(start_url)
        logger.info(f"Base domain extracted: {self.base_domain}")

    def _extract_base_domain(self, url):
        """Extract the base domain from a URL"""
        parsed_url = urlparse(url)
        # Return the domain without any subdomain/port
        return parsed_url.netloc

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
            
            # Fetch the page using our fetcher
            success, response_or_error, status_code = fetch_page(
                current_url, 
                self.user_agent, 
                self.max_retries, 
                self.timeout
            )
            
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
                        links = extract_links(response.text, current_url, self.delay)
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
        
        # Report skipped external URLs at the end
        if self.skipped_external_urls and self.internal_only:
            logger.info(f"Skipped {len(self.skipped_external_urls)} external URLs due to domain restriction")
            for url in list(self.skipped_external_urls)[:5]:  # Log first 5 examples
                logger.debug(f"Skipped external URL: {url}")
            if len(self.skipped_external_urls) > 5:
                logger.debug(f"... and {len(self.skipped_external_urls) - 5} more")
    
    def _should_crawl(self, url):
        """Determine if a URL should be crawled based on settings"""
        # Check if URL is already visited
        if url in self.visited_urls:
            return False
            
        # Check if URL is internal when internal_only is True
        if self.internal_only:
            parsed_url = urlparse(url)
            url_domain = parsed_url.netloc
            
            if url_domain != self.base_domain:
                # Add to skipped external URLs set for logging
                self.skipped_external_urls.add(url)
                logger.debug(f"Skipping external URL: {url} (not in {self.base_domain})")
                return False
                
        return True
        
    def get_results(self):
        """Return the detailed crawl results"""
        return self.results
        
    def get_skipped_external_urls(self):
        """Return the list of skipped external URLs"""
        return list(self.skipped_external_urls)