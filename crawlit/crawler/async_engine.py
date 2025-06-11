#!/usr/bin/env python3
"""
async_engine.py - Asynchronous crawler engine
"""

import logging
import re
import asyncio
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional, Any

from .async_fetcher import fetch_page_async as async_fetch_page
from .parser import extract_links
from .robots import AsyncRobotsHandler
from ..extractors.image_extractor import ImageTagParser
from ..extractors.keyword_extractor import KeywordExtractor
from ..extractors.tables import extract_tables
from ..extractors.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)

class AsyncCrawler:
    """Asynchronous crawler class that manages the crawling process.
    
    This class provides asynchronous crawling of web pages,
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
                 enable_table_extraction=False, same_path_only=False, max_concurrent_requests=5
                 ):
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
            max_concurrent_requests (int, optional): Maximum number of concurrent requests. Defaults to 5.
        """
        self.start_url = start_url
        self.max_depth = max_depth
        self.internal_only = internal_only
        self.respect_robots = respect_robots
        self.visited_urls = set()  # Store visited URLs
        # Get the current event loop or create a new one if none exists
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)  # Async queue for crawling with explicit loop
        self.results = {}  # Store results with metadata
        self.skipped_external_urls = set()  # Track skipped external URLs
        
        # Request parameters
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.delay = delay
        
        self.max_concurrent_requests = max_concurrent_requests
        
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Extract domain and path information for URL filtering
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        self.start_path = parsed_url.path
        
        # If the URL ends with a trailing slash, keep it for proper path matching
        if not self.start_path.endswith('/') and self.start_path:
            self.start_path += '/'
        
        # For domain-only URLs (like example.com or example.com/), we'll crawl the whole site
        self.crawl_entire_domain = not self.start_path or self.start_path == '/'
        
        # New attribute for same_path_only
        self.same_path_only = same_path_only
        
        logger.info(f"Base domain extracted: {self.base_domain}")
        if self.same_path_only:
            if self.crawl_entire_domain:
                logger.info(f"Crawling entire domain: {self.base_domain}")
            else:
                logger.info(f"Restricting crawl to path: {self.start_path}")
        
        # Initialize robots.txt handler if needed
        if self.respect_robots:
            self.robots_handler = AsyncRobotsHandler() 
            logger.info("Robots.txt handling enabled")
        else:
            self.robots_handler = None
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
            
    async def crawl(self):
        """Start the asynchronous crawling process"""
        # Add the starting URL to the queue with depth 0
        await self.queue.put((self.start_url, 0))
        
        # Create worker tasks with the explicit loop
        workers = []
        for _ in range(self.max_concurrent_requests):
            task = self.loop.create_task(self._worker())
            workers.append(task)
        
        # Wait until the queue is empty
        await self.queue.join()
        
        # Cancel all worker tasks
        for worker in workers:
            worker.cancel()
        
        # Wait for all worker tasks to be cancelled
        await asyncio.gather(*workers, return_exceptions=True)
        
        # Report skipped external URLs
        if self.skipped_external_urls and self.internal_only:
            logger.info(f"Skipped {len(self.skipped_external_urls)} external URLs due to domain restriction")
            for url in list(self.skipped_external_urls)[:5]:  # Log first 5 examples
                logger.debug(f"Skipped external URL: {url}")
            if len(self.skipped_external_urls) > 5:
                logger.debug(f"... and {len(self.skipped_external_urls) - 5} more")
    
    async def _worker(self):
        """Worker task for processing URLs from the queue"""
        while True:
            current_url, depth = await self.queue.get()
            
            try:
                # Skip if we've already visited this URL
                if current_url in self.visited_urls:
                    self.queue.task_done()
                    continue
                    
                # Skip if we've exceeded the maximum depth
                if depth > self.max_depth:
                    self.queue.task_done()
                    continue
                
                # Mark as visited before processing to prevent duplicates
                self.visited_urls.add(current_url)
                
                # Process the URL
                await self._process_url(current_url, depth)
                
            except Exception as e:
                logger.error(f"Error processing {current_url}: {e}")
            finally:
                # Mark the task as done
                self.queue.task_done()
    
    async def _process_url(self, url, depth):
        """Process a single URL"""
        # Limit concurrent requests using semaphore
        async with self.semaphore:
            logger.info(f"Crawling: {url} (depth: {depth})")
            
            # Initialize result data for this URL
            self.results[url] = {
                'depth': depth,
                'status': None,
                'headers': None,
                'links': [],
                'content_type': None,
                'error': None,
                'success': False
            }
            
            # If delay is configured, apply it
            if self.delay > 0:
                await asyncio.sleep(self.delay)
            
            # Fetch the page asynchronously
            success, response_or_error, status_code = await async_fetch_page(
                url, 
                self.user_agent, 
                self.max_retries, 
                self.timeout
            )
            
            # Record the HTTP status code
            self.results[url]['status'] = status_code
            
            # Update success flag based on fetch result
            self.results[url]['success'] = success
            
            if success:
                response = response_or_error
                
                # Store response headers
                self.results[url]['headers'] = dict(response.headers)
                self.results[url]['content_type'] = response.headers.get('Content-Type')
                
                try:
                    # Initialize links list for all URLs
                    links = []
                    
                    # Process the page to extract links if it's HTML
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        # Get the HTML content
                        html_content = await response.text()
                        
                        # Store HTML content for extraction features (like tables)
                        self.results[url]['html_content'] = html_content
                        
                        # Use ContentExtractor to extract all page metadata (async version)
                        content_data = await self.content_extractor.extract_content_async(html_content, url, response)
                        
                        # Merge content extractor results with page results
                        self.results[url].update({
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
                        logger.debug(f"Extracted metadata for {url}")
                        
                        # Extract links from HTML content
                        links = extract_links(html_content, url, self.delay)
                        logger.debug(f"Extracted {len(links)} links from HTML content at {url}")
                        
                        # Extract images from the page if extraction is enabled
                        if self.image_extraction_enabled:
                            images = self.image_extractor.extract_images(html_content)
                            self.results[url]['images'] = images
                            logger.debug(f"Extracted {len(images)} images from {url}")
                        
                        # Extract keywords from the page if extraction is enabled
                        if self.keyword_extraction_enabled:
                            keywords_data = self.keyword_extractor.extract_keywords(html_content, include_scores=True)
                            self.results[url]['keywords'] = keywords_data['keywords']
                            self.results[url]['keyword_scores'] = keywords_data['scores']
                            keyphrases = self.keyword_extractor.extract_keyphrases(html_content)
                            self.results[url]['keyphrases'] = keyphrases
                            logger.debug(f"Extracted {len(keywords_data['keywords'])} keywords and {len(keyphrases)} keyphrases from {url}")
                        
                        # Extract tables from the page if extraction is enabled
                        if self.table_extraction_enabled:
                            try:
                                tables = extract_tables(html_content, min_rows=1, min_columns=1)
                                self.results[url]['tables'] = tables
                                logger.debug(f"Extracted {len(tables)} tables from {url}")
                            except Exception as e:
                                logger.error(f"Error extracting tables from {url}: {e}")
                                self.results[url]['tables'] = []
                    else:
                        logger.debug(f"Skipping content extraction for non-HTML content type: {content_type} at {url}")
                    
                    # Store the links in the results (even if empty for non-HTML content)
                    self.results[url]['links'] = links
                    
                    # Add new links to the queue (will be empty for non-HTML content)
                    for link in links:
                        if await self._should_crawl(link):
                            await self.queue.put((link, depth + 1))
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    self.results[url]['error'] = str(e)
            else:
                # Store the error information
                logger.error(f"Failed to fetch {url}: {response_or_error}")
                self.results[url]['error'] = response_or_error
    
    async def _should_crawl(self, url):
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
            can_fetch = await self.robots_handler.can_fetch(url, self.user_agent)
            if not can_fetch:
                logger.debug(f"Skipping URL disallowed by robots.txt: {url}")
                return False
        
        return True
    
    def get_results(self):
        """Return the detailed crawl results"""
        return self.results
    
    def get_skipped_external_urls(self):
        """Return the list of skipped external URLs"""
        return list(self.skipped_external_urls)
    
    async def get_skipped_robots_paths(self):
        """Return the list of URLs skipped due to robots.txt rules (async version)"""
        if self.robots_handler:
            return await self.robots_handler.get_skipped_paths()
        return []
