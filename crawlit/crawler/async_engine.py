#!/usr/bin/env python3
"""
async_engine.py - Asynchronous crawler engine
"""

import logging
import re
import asyncio
from collections import deque
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional, Any
import time

from .async_fetcher import fetch_page_async as async_fetch_page
from .parser import extract_links
from .robots import AsyncRobotsHandler

# Check if Playwright is available for JavaScript rendering
try:
    from .js_renderer import AsyncJavaScriptRenderer, is_playwright_available
    PLAYWRIGHT_AVAILABLE = is_playwright_available()
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    AsyncJavaScriptRenderer = None
from ..extractors.image_extractor import ImageTagParser
from ..extractors.keyword_extractor import KeywordExtractor
from ..extractors.tables import extract_tables
from ..extractors.content_extractor import ContentExtractor
from ..utils.progress import ProgressTracker
from ..utils.url_filter import URLFilter
from ..utils.session_manager import SessionManager
from ..utils.queue_manager import QueueManager
from ..utils.cache import PageCache, CrawlResume
from ..utils.storage import StorageManager
from ..utils.sitemap import SitemapParser, get_sitemaps_from_robots_async
from ..utils.rate_limiter import AsyncRateLimiter
from ..utils.deduplication import ContentDeduplicator
from ..utils.budget_tracker import AsyncBudgetTracker

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
    
    def __init__(
        self, 
        start_url: str, 
        max_depth: int = 3, 
        internal_only: bool = True, 
        user_agent: str = "crawlit/1.0", 
        max_retries: int = 3, 
        timeout: int = 10, 
        delay: float = 0.1,
        respect_robots: bool = True, 
        enable_image_extraction: bool = False, 
        enable_keyword_extraction: bool = False,
        enable_table_extraction: bool = False,
        enable_content_extraction: bool = False,
        same_path_only: bool = False, 
        max_concurrent_requests: int = 5,
        max_queue_size: Optional[int] = None,
        progress_tracker: Optional[ProgressTracker] = None,
        url_filter: Optional[URLFilter] = None,
        session_manager: Optional[SessionManager] = None,
        page_cache: Optional[PageCache] = None,
        storage_manager: Optional[StorageManager] = None,
        store_html_content: bool = True,
        use_sitemap: bool = False,
        sitemap_urls: Optional[List[str]] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
        use_per_domain_delay: bool = True,
        content_deduplicator: Optional[ContentDeduplicator] = None,
        enable_content_deduplication: bool = False,
        use_js_rendering: bool = False,
        js_wait_for_selector: Optional[str] = None,
        js_wait_for_timeout: Optional[int] = None,
        js_browser_type: str = "chromium",
        proxy: Optional[str] = None,
        proxy_manager: Optional['ProxyManager'] = None,
        budget_tracker: Optional[AsyncBudgetTracker] = None
    ):
        """Initialize the crawler with given parameters.
        
        Args:
            start_url (str): The URL where crawling will begin.
            max_depth (int, optional): Maximum crawling depth. Defaults to 3.
            internal_only (bool, optional): Whether to stay within the same domain. Defaults to True.
            user_agent (str, optional): User agent string to use in HTTP requests. Defaults to "crawlit/1.0".
            max_retries (int, optional): Maximum number of retry attempts for failed requests. Defaults to 3.
            timeout (int, optional): Request timeout in seconds. Defaults to 10.
            delay (float, optional): Delay between requests in seconds. Defaults to 0.1.
            respect_robots (bool, optional): Whether to respect robots.txt rules. Defaults to True.
            enable_image_extraction (bool, optional): Whether to enable image extraction. Defaults to False.
            enable_keyword_extraction (bool, optional): Whether to enable keyword extraction. Defaults to False.
            enable_table_extraction (bool, optional): Whether to enable table extraction. Defaults to False.
            same_path_only (bool, optional): Whether to restrict crawling to URLs with the same path prefix as the start URL. Defaults to False.
            max_concurrent_requests (int, optional): Maximum number of concurrent requests. Defaults to 5.
            progress_tracker (ProgressTracker, optional): Progress tracker for monitoring crawl progress. Defaults to None.
            url_filter (URLFilter, optional): Advanced URL filter for additional filtering rules. Defaults to None.
            session_manager (SessionManager, optional): Session manager for cookie persistence. Defaults to None.
            page_cache (PageCache, optional): Page cache for avoiding re-fetching. Defaults to None.
            storage_manager (StorageManager, optional): Storage manager for HTML content. Defaults to None.
            store_html_content (bool, optional): Whether to store HTML content in results. Defaults to True.
        """
        self.start_url = start_url
        self.max_depth = max_depth
        self.internal_only = internal_only
        self.respect_robots = respect_robots
        self.visited_urls = set()  # Store visited URLs
        self.queue: asyncio.Queue = asyncio.Queue()
        self.results = {}  # Store results with metadata
        self.skipped_external_urls = set()  # Track skipped external URLs

        # Queue management
        self.max_queue_size: Optional[int] = max_queue_size
        self._paused: bool = False

        # Request parameters
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.delay = delay

        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent_requests)
        
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
        self.content_extraction_enabled = enable_content_extraction
        
        # Initialize content extractor only if enabled
        if self.content_extraction_enabled:
            self.content_extractor = ContentExtractor()
            logger.info("Content extraction enabled")
        else:
            self.content_extractor = None
            logger.info("Content extraction disabled")
        
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
        
        # Initialize utilities
        self.progress_tracker: Optional[ProgressTracker] = progress_tracker
        self.url_filter: Optional[URLFilter] = url_filter
        
        # Initialize session manager
        if session_manager:
            self.session_manager: SessionManager = session_manager
        else:
            self.session_manager = SessionManager(
                user_agent=user_agent,
                timeout=timeout,
                verify_ssl=True
            )
        
        if self.progress_tracker:
            logger.info("Progress tracking enabled")
        if self.url_filter:
            logger.info("Advanced URL filtering enabled")
        
        if self.max_queue_size:
            logger.info(f"Queue size limit: {self.max_queue_size}")
        
        # Initialize page cache
        self.page_cache = page_cache
        if self.page_cache:
            logger.info("Page caching enabled")
        
        # Initialize storage manager
        if storage_manager:
            self.storage_manager = storage_manager
        else:
            self.storage_manager = StorageManager(
                store_html_content=store_html_content,
                enable_disk_storage=False
            )
        
        if not self.storage_manager.store_html_content:
            logger.info("HTML content storage disabled (memory optimization)")
        elif self.storage_manager.enable_disk_storage:
            logger.info(f"Disk-based HTML storage enabled at {self.storage_manager.storage_dir}")
        
        # Initialize rate limiter for per-domain rate limiting
        self.use_per_domain_delay = use_per_domain_delay
        if rate_limiter:
            self.rate_limiter: AsyncRateLimiter = rate_limiter
        else:
            self.rate_limiter = AsyncRateLimiter(default_delay=self.delay)
        
        if self.use_per_domain_delay:
            logger.info("Per-domain rate limiting enabled")
        
        # Initialize content deduplicator
        self.enable_content_deduplication = enable_content_deduplication
        if content_deduplicator:
            self.content_deduplicator: ContentDeduplicator = content_deduplicator
        elif enable_content_deduplication:
            self.content_deduplicator = ContentDeduplicator(enabled=True)
        else:
            self.content_deduplicator = ContentDeduplicator(enabled=False)
        
        if self.enable_content_deduplication or self.content_deduplicator.enabled:
            logger.info("Content-based deduplication enabled")
        
        # Initialize JavaScript renderer if enabled
        self.use_js_rendering = use_js_rendering
        self.js_wait_for_selector = js_wait_for_selector
        self.js_wait_for_timeout = js_wait_for_timeout
        self.js_browser_type = js_browser_type
        self.js_renderer: Optional[Any] = None
        
        # Proxy support
        self.proxy = proxy
        self.proxy_manager = proxy_manager
        
        # Budget tracker
        self.budget_tracker: Optional[AsyncBudgetTracker] = budget_tracker
        if self.budget_tracker:
            logger.info("Budget tracking enabled")
        
        # Sitemap support
        self.use_sitemap = use_sitemap
        self.sitemap_urls = sitemap_urls or []
        self.sitemap_parser = None
        if self.use_sitemap:
            self.sitemap_parser = SitemapParser(timeout=self.timeout)
            logger.info("Sitemap support enabled")
        
        if self.use_js_rendering:
            if not PLAYWRIGHT_AVAILABLE:
                logger.warning("JavaScript rendering requested but Playwright not installed. "
                             "Install with: pip install playwright && python -m playwright install")
                self.use_js_rendering = False
            else:
                logger.info(f"JavaScript rendering enabled with {js_browser_type} browser")
                if js_wait_for_selector:
                    logger.info(f"Waiting for selector: {js_wait_for_selector}")
                if js_wait_for_timeout:
                    logger.info(f"Additional wait timeout: {js_wait_for_timeout}ms")
                # Create a shared renderer for async context
                self.js_renderer = AsyncJavaScriptRenderer(
                    browser_type=js_browser_type,
                    user_agent=user_agent,
                    timeout=timeout * 1000,  # Convert to milliseconds
                    headless=True
                )
            
    async def crawl(self):
        """Start the asynchronous crawling process"""
        # Reset queue and semaphore at the start of each crawl so that
        # crawl() can safely be called more than once on the same instance.
        self.queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # Start progress tracker if provided
        if self.progress_tracker:
            self.progress_tracker.start()

        # Get async session from session manager
        session = await self.session_manager.get_async_session()

        # Discover and parse sitemaps if enabled
        if self.use_sitemap and self.sitemap_parser:
            await self._discover_sitemaps(session)

        # Add the starting URL to the queue with depth 0
        await self.queue.put((self.start_url, 0))

        # Create worker tasks using the running loop's create_task
        workers = []
        for _ in range(self.max_concurrent_requests):
            task = asyncio.create_task(self._worker())
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
        
        # Finish progress tracking
        if self.progress_tracker:
            self.progress_tracker.finish()

        # Cleanup JavaScript renderer if it was used
        if self.js_renderer:
            try:
                await self.js_renderer.close()
            except Exception as e:
                logger.warning(f"Error closing JavaScript renderer: {e}")

        # Cleanup async session from session manager
        try:
            await self.session_manager.close_async_session()
        except Exception as e:
            logger.warning(f"Error closing async session: {e}")
    
    async def _worker(self):
        """Worker task for processing URLs from the queue"""
        while True:
            # Check if paused
            while self._paused:
                await asyncio.sleep(0.1)  # Small sleep to avoid busy waiting

            current_url, depth = await self.queue.get()

            try:
                # Check budget before processing this URL
                if self.budget_tracker:
                    can_crawl, reason = self.budget_tracker.can_crawl_page()
                    if not can_crawl:
                        logger.warning(f"Stopping crawl: {reason}")
                        break

                # Skip if we've already visited this URL
                if current_url in self.visited_urls:
                    continue

                # Skip if we've exceeded the maximum depth
                if depth > self.max_depth:
                    continue

                # Mark as visited before processing to prevent duplicates
                self.visited_urls.add(current_url)

                # Process the URL
                await self._process_url(current_url, depth)

            except Exception as e:
                logger.error(f"Error processing {current_url}: {e}")
            finally:
                # Mark the task as done regardless of outcome
                self.queue.task_done()
    
    async def _process_url(self, url, depth):
        """Process a single URL"""
        # Limit concurrent requests using semaphore
        async with self.semaphore:
            # Apply per-domain rate limiting if enabled
            if self.use_per_domain_delay:
                # Check for crawl-delay from robots.txt if available
                if self.respect_robots and self.robots_handler:
                    try:
                        crawl_delay = await self.robots_handler.get_crawl_delay(url, self.user_agent)
                        if crawl_delay is not None:
                            parsed_url = urlparse(url)
                            domain = parsed_url.netloc.lower()
                            await self.rate_limiter.set_domain_delay(domain, crawl_delay)
                            logger.debug(f"Using crawl-delay {crawl_delay}s from robots.txt for {domain}")
                    except Exception as e:
                        logger.debug(f"Could not get crawl-delay from robots.txt: {e}")
                
                # Wait if needed for this domain
                await self.rate_limiter.wait_if_needed(url)
            else:
                # Apply global delay if configured
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
            
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
            
            # Get async session from session manager
            session = await self.session_manager.get_async_session()
            
            # Fetch the page asynchronously with session
            success, response_or_error, status_code = await async_fetch_page(
                url, 
                self.user_agent, 
                self.max_retries, 
                self.timeout,
                session=session,
                use_js_rendering=self.use_js_rendering,
                js_renderer=self.js_renderer,
                wait_for_selector=self.js_wait_for_selector,
                wait_for_timeout=self.js_wait_for_timeout,
                proxy=self.proxy,
                proxy_manager=self.proxy_manager
            )
            
            # Record the HTTP status code
            self.results[url]['status'] = status_code
            
            # Update success flag based on fetch result
            self.results[url]['success'] = success
            
            if success:
                response = response_or_error
                
                # Store response headers
                headers = dict(response.headers)
                self.results[url]['headers'] = headers
                self.results[url]['content_type'] = response.headers.get('Content-Type')
                
                # Record bytes downloaded for budget tracking
                if self.budget_tracker:
                    # Try to get content length from header
                    content_length = headers.get('Content-Length')
                    if content_length:
                        bytes_downloaded = int(content_length)
                    else:
                        # Estimate from response content if available
                        try:
                            # For aiohttp, content might not be loaded yet
                            bytes_downloaded = 0
                            if hasattr(response, '_body') and response._body:
                                bytes_downloaded = len(response._body)
                        except Exception:
                            bytes_downloaded = 0
                    
                    if bytes_downloaded > 0:
                        self.budget_tracker.record_page(bytes_downloaded)
                
                try:
                    # Initialize links list for all URLs
                    links = []
                    
                    # Process the page to extract links if it's HTML
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        # Get the HTML content
                        html_content = await response.text()
                        
                        # Check for duplicate content
                        if self.content_deduplicator.enabled:
                            if self.content_deduplicator.is_duplicate(html_content, url):
                                logger.info(f"Skipping duplicate content at {url}")
                                duplicate_urls = self.content_deduplicator.get_duplicate_urls(url)
                                self.results[url]['duplicate'] = True
                                if duplicate_urls:
                                    self.results[url]['duplicate_of'] = list(duplicate_urls)
                                
                                # Still record progress but mark as duplicate
                                if self.progress_tracker:
                                    self.progress_tracker.record_url(
                                        url,
                                        True,
                                        links_found=0,
                                        depth=depth,
                                        metadata={'duplicate': True}
                                    )
                                return  # Skip processing duplicate content
                        
                        # Store HTML content using storage manager
                        stored_html = self.storage_manager.store_html(url, html_content)
                        if stored_html is not None:
                            self.results[url]['html_content'] = stored_html
                        
                        # Use ContentExtractor to extract all page metadata (async version) if enabled
                        if self.content_extraction_enabled and self.content_extractor:
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
                        
                        # Cache the response if cache is enabled
                        if self.page_cache:
                            self.page_cache.set(
                                url,
                                self.results[url],
                                status_code,
                                dict(response.headers),
                                html_content
                            )
                    else:
                        logger.debug(f"Skipping content extraction for non-HTML content type: {content_type} at {url}")
                    
                    # Store the links in the results (even if empty for non-HTML content)
                    self.results[url]['links'] = links
                    
                    # Record progress for successful URL
                    if self.progress_tracker:
                        images_count = len(self.results[url].get('images', []))
                        keywords_count = len(self.results[url].get('keywords', []))
                        tables_count = len(self.results[url].get('tables', []))
                        self.progress_tracker.record_url(
                            url,
                            True,
                            links_found=len(links),
                            depth=depth,
                            metadata={
                                'images': images_count,
                                'keywords': keywords_count,
                                'tables': tables_count
                            }
                        )
                    
                    # Add new links to the queue (will be empty for non-HTML content)
                    for link in links:
                        if await self._should_crawl(link):
                            # Check queue size limit
                            if self.max_queue_size and self.queue.qsize() >= self.max_queue_size:
                                logger.warning(f"Queue size limit ({self.max_queue_size}) reached, skipping URL: {link}")
                                continue
                            await self.queue.put((link, depth + 1))
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    self.results[url]['error'] = str(e)
                    # Record progress for failed URL
                    if self.progress_tracker:
                        self.progress_tracker.record_url(
                            url,
                            False,
                            links_found=0,
                            depth=depth
                        )
            else:
                # Store the error information
                logger.error(f"Failed to fetch {url}: {response_or_error}")
                self.results[url]['error'] = response_or_error
                # Record progress for failed URL
                if self.progress_tracker:
                    self.progress_tracker.record_url(
                        url,
                        False,
                        links_found=0,
                        depth=depth
                    )
    
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
        
        # Check URL filter if provided
        if self.url_filter and not self.url_filter.is_allowed(url):
            logger.debug(f"Skipping URL blocked by URLFilter: {url}")
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
    
    def pause(self) -> None:
        """Pause the crawling process."""
        self._paused = True
        logger.info("Crawling paused")
    
    def resume(self) -> None:
        """Resume the crawling process."""
        self._paused = False
        logger.info("Crawling resumed")
    
    def is_paused(self) -> bool:
        """Check if crawling is paused."""
        return self._paused
    
    async def save_state(self, filepath: str) -> None:
        """
        Save the current crawler state to a file (async version).
        
        Args:
            filepath: Path to save the state file
        """
        # Convert asyncio.Queue to list for serialization
        queue_list = []
        temp_queue = asyncio.Queue()
        
        # Drain the queue and rebuild it
        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                queue_list.append(item)
                temp_queue.put_nowait(item)
            except asyncio.QueueEmpty:
                break
        
        # Restore the queue
        while not temp_queue.empty():
            try:
                item = temp_queue.get_nowait()
                self.queue.put_nowait(item)
            except asyncio.QueueEmpty:
                break
        
        # Create a deque for compatibility with QueueManager
        queue_deque = deque(queue_list)
        
        metadata = {
            'start_url': self.start_url,
            'max_depth': self.max_depth,
            'internal_only': self.internal_only,
            'respect_robots': self.respect_robots,
            'max_queue_size': self.max_queue_size
        }
        QueueManager.save_state(
            queue_deque,
            self.visited_urls,
            self.results,
            filepath,
            metadata
        )
    
    async def load_state(self, filepath: str) -> None:
        """
        Load crawler state from a file (async version).
        
        Args:
            filepath: Path to the state file
        """
        queue_deque, self.visited_urls, self.results, metadata = QueueManager.load_state(filepath)
        
        # Convert deque back to asyncio.Queue
        self.queue = asyncio.Queue()
        for item in queue_deque:
            self.queue.put_nowait(item)
        
        # Optionally restore metadata
        if metadata:
            logger.info(f"Loaded state metadata: {metadata}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current queue.
        
        Returns:
            Dictionary with queue statistics
        """
        # Convert asyncio.Queue to deque for stats
        queue_list = []
        temp_queue = asyncio.Queue()
        
        # Drain the queue and rebuild it
        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                queue_list.append(item)
                temp_queue.put_nowait(item)
            except asyncio.QueueEmpty:
                break
        
        # Restore the queue
        while not temp_queue.empty():
            try:
                item = temp_queue.get_nowait()
                self.queue.put_nowait(item)
            except asyncio.QueueEmpty:
                break
        
        queue_deque = deque(queue_list)
        return QueueManager.get_queue_stats(queue_deque)
