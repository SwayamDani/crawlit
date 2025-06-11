#!/usr/bin/env python3
"""
engine.py - Core crawler engine
"""

import logging
import re
import time
from collections import deque
from urllib.parse import urlparse, urljoin

from .fetcher import fetch_page
from .parser import extract_links
from .robots import RobotsHandler
from ..extractors.image_extractor import ImageTagParser
from ..extractors.keyword_extractor import KeywordExtractor
from ..extractors.tables import extract_tables
from ..extractors.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)

class Crawler:
    """Main crawler class that manages the crawling process.
    
    This class provides the core functionality for crawling web pages,
    extracting links, and following them according to the specified rules.
    
    Attributes:
        start_url (str): The starting URL for the crawler.
        max_depth (int): Maximum depth of crawling from the start URL.
        internal_only (bool): Whether to restrict crawling to the same domain.
        respect_robots (bool): Whether to respect robots.txt rules.
        visited_urls (set): Set of URLs already visited.
        results (dict): Dictionary containing crawl results and metadata.
    """
    
    def __init__(self, start_url, max_depth=3, internal_only=True, 
                 user_agent="crawlit/2.0", max_retries=3, timeout=10, delay=0.1,
                 respect_robots=True, enable_image_extraction=False, enable_keyword_extraction=False,
                 enable_table_extraction=False, same_path_only=False):
        """Initialize the crawler with given parameters.
        
        Args:
            start_url (str): The URL where crawling will begin.
            max_depth (int, optional): Maximum crawling depth. Defaults to 3.
            internal_only (bool, optional): Whether to stay within the same domain. Defaults to True.
            user_agent (str, optional): User agent string to use in HTTP requests. Defaults to "crawlit/2.0".
            max_retries (int, optional): Maximum number of retry attempts for failed requests. Defaults to 3.
            timeout (int, optional): Request timeout in seconds. Defaults to 10.
            delay (float, optional): Delay between requests in seconds. Defaults to 0.1.
            respect_robots (bool, optional): Whether to respect robots.txt rules. Defaults to True.
            enable_image_extraction (bool, optional): Whether to enable image extraction. Defaults to False.
            enable_keyword_extraction (bool, optional): Whether to enable keyword extraction. Defaults to False.
            enable_table_extraction (bool, optional): Whether to enable table extraction. Defaults to False.
            same_path_only (bool, optional): Whether to restrict crawling to URLs with the same path prefix as the start URL. Defaults to False.
        """
        self.start_url = start_url
        self.max_depth = max_depth
        self.internal_only = internal_only
        self.respect_robots = respect_robots
        self.visited_urls = set()  # Store visited URLs
        self.queue = deque()  # Queue for BFS crawling
        self.results = {}  # Store results with metadata
        self.skipped_external_urls = set()  # Track skipped external URLs
        
        # Request parameters
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.delay = delay
        
        # Extract domain and path information for URL filtering
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        self.start_path = parsed_url.path
        
        # If the URL ends with a trailing slash, keep it for proper path matching
        if not self.start_path.endswith('/') and self.start_path:
            self.start_path += '/'
        
        # For domain-only URLs (like example.com or example.com/), we'll crawl the whole site
        self.crawl_entire_domain = not self.start_path or self.start_path == '/'
        
        # Initialize robots.txt handler if needed
        self.robots_handler = RobotsHandler() if respect_robots else None
        if self.respect_robots:
            logger.info("Robots.txt handling enabled")
        else:
            logger.info("Robots.txt handling disabled")
            
        # Initialize extractors based on feature flags
        self.image_extraction_enabled = enable_image_extraction
        self.keyword_extraction_enabled = enable_keyword_extraction
        self.table_extraction_enabled = enable_table_extraction
        
        # Always enable content extraction for metadata, headings, etc.
        self.content_extractor = ContentExtractor()
        logger.info("Content extraction enabled")
        
        if self.image_extraction_enabled:
            self.image_extractor = ImageTagParser()
            logger.info("Image extraction enabled")
        else:
            self.image_extractor = None
            logger.info("Image extraction disabled")
            
        if self.keyword_extraction_enabled:
            self.keyword_extractor = KeywordExtractor()
            logger.info("Keyword extraction enabled")
        else:
            self.keyword_extractor = None
            logger.info("Keyword extraction disabled")
            
        if self.table_extraction_enabled:
            logger.info("Table extraction enabled")
        else:
            logger.info("Table extraction disabled")
        
        # New attribute for same_path_only
        self.same_path_only = same_path_only
        
        logger.info(f"Base domain extracted: {self.base_domain}")
        if self.same_path_only:
            if self.crawl_entire_domain:
                logger.info(f"Crawling entire domain: {self.base_domain}")
            else:
                logger.info(f"Restricting crawl to path: {self.start_path}")

    def _extract_base_domain(self, url):
        """Extract the base domain from a URL"""
        parsed_url = urlparse(url)
        # Return the domain without any subdomain/port
        return parsed_url.netloc

    def crawl(self):
        """Start the crawling process"""
        # Add the starting URL to the queue with depth 0
        self.queue.append((self.start_url, 0))
        
        # Track last request time to implement delay between requests
        last_request_time = 0
        
        while self.queue:
            current_url, depth = self.queue.popleft()
            
            # Skip if we've already visited this URL
            if current_url in self.visited_urls:
                continue
                
            # Skip if we've exceeded the maximum depth
            if depth > self.max_depth:
                continue
                
            # Apply delay between requests if needed
            if self.delay > 0:
                current_time = time.time()
                time_since_last_request = current_time - last_request_time
                if time_since_last_request < self.delay:
                    # Sleep for remaining time to satisfy the delay
                    time.sleep(self.delay - time_since_last_request)
            
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
            
            # Update the last request time
            last_request_time = time.time()
            
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
            
            # Update success flag based on fetch result
            self.results[current_url]['success'] = success
            
            # Update success flag based on fetch result
            self.results[current_url]['success'] = success
            
            if success:
                response = response_or_error
                
                # Store response headers
                self.results[current_url]['headers'] = dict(response.headers)
                self.results[current_url]['content_type'] = response.headers.get('Content-Type')
                
                try:
                    # Initialize links list for all URLs
                    links = []
                    
                    # Process the page to extract links if it's HTML
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        # Store HTML content for extraction features (like tables)
                        self.results[current_url]['html_content'] = response.text
                        
                        # Use ContentExtractor to extract all page metadata
                        content_data = self.content_extractor.extract_content(response.text, current_url, response)
                        
                        # Merge content extractor results with page results
                        self.results[current_url].update({
                            'title': content_data.get('title'),
                            'meta_description': content_data.get('meta_description'),
                            'meta_keywords': content_data.get('meta_keywords'),
                            'canonical_url': content_data.get('canonical_url'),
                            'language': content_data.get('language'),
                            'headings': content_data.get('headings'),
                            'images_with_context': content_data.get('images_with_context'),
                            'page_type': content_data.get('page_type'),
                            'last_modified': content_data.get('last_modified')
                        })
                        logger.debug(f"Extracted metadata for {current_url}")
                        
                        # Extract links from HTML content
                        links = extract_links(response.text, current_url, self.delay)
                        logger.debug(f"Extracted {len(links)} links from HTML content at {current_url}")
                        
                        # Extract images from the page if extraction is enabled
                        if self.image_extraction_enabled:
                            images = self.image_extractor.extract_images(response.text)
                            self.results[current_url]['images'] = images
                            logger.debug(f"Extracted {len(images)} images from {current_url}")
                        
                        # Extract keywords from the page if extraction is enabled
                        if self.keyword_extraction_enabled:
                            keywords_data = self.keyword_extractor.extract_keywords(response.text, include_scores=True)
                            self.results[current_url]['keywords'] = keywords_data['keywords']
                            self.results[current_url]['keyword_scores'] = keywords_data['scores']
                            keyphrases = self.keyword_extractor.extract_keyphrases(response.text)
                            self.results[current_url]['keyphrases'] = keyphrases
                            logger.debug(f"Extracted {len(keywords_data['keywords'])} keywords and {len(keyphrases)} keyphrases from {current_url}")
                        
                        # Extract tables from the page if extraction is enabled
                        if self.table_extraction_enabled:
                            try:
                                tables = extract_tables(response.text, min_rows=1, min_columns=1)
                                self.results[current_url]['tables'] = tables
                                logger.debug(f"Extracted {len(tables)} tables from {current_url}")
                            except Exception as e:
                                logger.error(f"Error extracting tables from {current_url}: {e}")
                                self.results[current_url]['tables'] = []
                    else:
                        logger.debug(f"Skipping content extraction for non-HTML content type: {content_type} at {current_url}")
                    
                    # Store the links in the results (even if empty for non-HTML content)
                    self.results[current_url]['links'] = links
                    
                    # Add new links to the queue (will be empty for non-HTML content)
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
        
        # Report skipped robots.txt paths at the end
        if self.respect_robots and self.robots_handler:
            skipped_paths = self.get_skipped_robots_paths()
            if skipped_paths:
                logger.info(f"Skipped {len(skipped_paths)} URLs disallowed by robots.txt")
                for url in skipped_paths[:5]:  # Log first 5 examples
                    logger.debug(f"Skipped (robots.txt): {url}")
                if len(skipped_paths) > 5:
                    logger.debug(f"... and {len(skipped_paths) - 5} more")
    
    def _should_crawl(self, url):
        """Determine if a URL should be crawled based on settings"""
        # Check if URL is already visited
        if url in self.visited_urls:
            logger.debug(f"Skipping already visited URL: {url}")
            return False
        
        # Check if URL is internal when internal_only is True
        if self.internal_only:
            parsed_url = urlparse(url)
            
            # First check if the domain matches
            if parsed_url.netloc != self.base_domain:
                self.skipped_external_urls.add(url)
                logger.debug(f"Skipping external URL: {url} (external domain)")
                return False
            
            # If same_path_only is True, check path restriction
            if self.same_path_only and not self.crawl_entire_domain:
                # For path-specific crawling, ensure the URL path starts with the start_path
                if not parsed_url.path.startswith(self.start_path):
                    self.skipped_external_urls.add(url)
                    logger.debug(f"Skipping external URL: {url} (not under {self.start_path})")
                    return False
        
        # Check robots.txt rules if enabled
        if self.respect_robots and self.robots_handler:
            if not self.robots_handler.can_fetch(url, self.user_agent):
                logger.debug(f"Skipping URL disallowed by robots.txt: {url}")
                return False
        
        return True
        
    def get_results(self):
        """Return the detailed crawl results"""
        return self.results
        
    def get_skipped_external_urls(self):
        """Return the list of skipped external URLs"""
        return list(self.skipped_external_urls)
        
    def get_skipped_robots_paths(self):
        """Return the list of URLs skipped due to robots.txt rules"""
        if self.robots_handler:
            return self.robots_handler.get_skipped_paths()
        return []
    
    def is_valid_url(self, url):
        """Check if the URL should be crawled based on crawler settings"""
        # Check if URL is already processed or queued
        if url in self.visited_urls or url in self.queue:
            return False

        # Parse the URL to extract domain and path
        parsed_url = urlparse(url)
        
        # If URL is not in the base domain and internal_only is True, skip it
        if self.internal_only and parsed_url.netloc != self.base_domain:
            return False

        # If same_path_only is True and we're not crawling the entire domain,
        # ensure the URL path starts with the start_path
        if self.same_path_only and not self.crawl_entire_domain:
            if not parsed_url.path.startswith(self.start_path):
                logger.debug(f"Skipping URL: {url} (not under path {self.start_path})")
                self.skipped_external_urls.add(url)
                return False

        return True

    def _extract_links(self, url, soup):
        """Extract all links from the page"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            # Handle relative URLs
            if href.startswith('/'):
                # Convert relative URL to absolute
                href = f"http://{self.base_domain}{href}"
            elif not (href.startswith('http://') or href.startswith('https://')):
                # Handle URLs without protocol and domain
                href = urljoin(url, href)
            
            # Skip non-http(s) URLs
            if not (href.startswith('http://') or href.startswith('https://')):
                continue
            
            # Parse the URL to check domain and path
            parsed_href = urlparse(href)
            
            # Skip if not in same domain when internal_only is True
            if self.internal_only and parsed_href.netloc != self.base_domain:
                self.skipped_external_urls.add(href)
                logger.debug(f"Skipping external URL: {href} (external domain)")
                continue
            
            # If same_path_only is True and we're not crawling the entire domain,
            # check path restriction
            if self.same_path_only and not self.crawl_entire_domain:
                if not parsed_href.path.startswith(self.start_path):
                    self.skipped_external_urls.add(href)
                    logger.debug(f"Skipping path-external URL: {href} (not under {self.start_path})")
                    continue
            
            links.append(href)
        
        return links