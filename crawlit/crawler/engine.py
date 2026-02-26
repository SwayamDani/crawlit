#!/usr/bin/env python3
"""
engine.py - Core crawler engine
"""

import logging
import re
import time
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Set, List, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin

from .fetcher import fetch_page
from .parser import extract_links
from .robots import RobotsHandler

# Check if Playwright is available for JavaScript rendering
try:
    from .js_renderer import JavaScriptRenderer, is_playwright_available
    PLAYWRIGHT_AVAILABLE = is_playwright_available()
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    JavaScriptRenderer = None
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
from ..utils.sitemap import SitemapParser, get_sitemaps_from_robots
from ..utils.rate_limiter import RateLimiter
from ..utils.deduplication import ContentDeduplicator
from ..utils.budget_tracker import BudgetTracker
from ..models.page_artifact import (
    PageArtifact, HTTPInfo, ContentInfo, CrawlMeta, DownloadRecord, CrawlJob, CrawlError,
)

logger = logging.getLogger(__name__)

class Crawler:
    """Main crawler class that manages the crawling process.

    This class provides the core functionality for crawling web pages,
    extracting links, and following them according to the specified rules.

    Class constants
    ---------------
    _MAX_SKIPPED_EXTERNAL : int
        Maximum entries kept in ``skipped_external_urls`` to bound memory use
        on large crawls.
    
    Attributes:
        start_url (str): The starting URL for the crawler.
        max_depth (int): Maximum depth of crawling from the start URL.
        internal_only (bool): Whether to restrict crawling to the same domain.
        respect_robots (bool): Whether to respect robots.txt rules.
        visited_urls (set): Set of URLs already visited.
        results (dict): Dictionary containing crawl results and metadata.
    """

    _MAX_SKIPPED_EXTERNAL: int = 10_000

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
        max_queue_size: Optional[int] = None,
        max_workers: Optional[int] = 1,
        progress_tracker: Optional[ProgressTracker] = None,
        url_filter: Optional[URLFilter] = None,
        session_manager: Optional[SessionManager] = None,
        page_cache: Optional[PageCache] = None,
        storage_manager: Optional[StorageManager] = None,
        store_html_content: bool = True,
        use_sitemap: bool = False,
        sitemap_urls: Optional[List[str]] = None,
        rate_limiter: Optional[RateLimiter] = None,
        use_per_domain_delay: bool = True,
        content_deduplicator: Optional[ContentDeduplicator] = None,
        enable_content_deduplication: bool = False,
        use_js_rendering: bool = False,
        js_wait_for_selector: Optional[str] = None,
        js_wait_for_timeout: Optional[int] = None,
        js_browser_type: str = "chromium",
        proxy: Optional[str] = None,
        proxy_manager: Optional['ProxyManager'] = None,
        budget_tracker: Optional[BudgetTracker] = None,
        # --- Plugin extension points ---
        extractors: Optional[List[Any]] = None,
        pipelines: Optional[List[Any]] = None,
        enable_pdf_extraction: bool = False,
        enable_js_embedded_data: bool = False,
        # --- Composable config (overrides individual kwargs when supplied) ---
        config: Optional[Any] = None,
        # --- Fetch abstraction ---
        fetcher: Optional[Any] = None,
        # --- Incremental crawling ---
        incremental: Optional[Any] = None,
        # --- Crawl job metadata ---
        run_id: Optional[str] = None,
    ) -> None:
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
            max_queue_size (int, optional): Maximum size of the URL queue. Defaults to None (no limit).
            max_workers (int, optional): Maximum number of worker threads for concurrent crawling. Defaults to 1 (single-threaded). Set to > 1 to enable multi-threading.
            progress_tracker (ProgressTracker, optional): Progress tracker for monitoring crawl progress. Defaults to None.
            url_filter (URLFilter, optional): Advanced URL filter for additional filtering rules. Defaults to None.
            session_manager (SessionManager, optional): Session manager for cookie persistence. Defaults to None.
            page_cache (PageCache, optional): Page cache for avoiding re-fetching. Defaults to None.
            storage_manager (StorageManager, optional): Storage manager for HTML content. Defaults to None.
            store_html_content (bool, optional): Whether to store HTML content in results. Defaults to True.
            use_sitemap (bool, optional): Whether to discover and use sitemaps for URL discovery. Defaults to False.
            sitemap_urls (List[str], optional): Explicit list of sitemap URLs to parse. If not provided, will try to discover from robots.txt or common locations.
            use_js_rendering (bool, optional): Whether to use JavaScript rendering (Playwright) for SPAs and JS-heavy sites. Defaults to False.
            js_wait_for_selector (str, optional): CSS selector to wait for when using JS rendering. Defaults to None.
            js_wait_for_timeout (int, optional): Additional timeout in milliseconds after page load when using JS rendering. Defaults to None.
            js_browser_type (str, optional): Browser type for JS rendering: 'chromium', 'firefox', or 'webkit'. Defaults to 'chromium'.
        """
        parsed_start = urlparse(start_url)
        if parsed_start.scheme not in ('http', 'https'):
            raise ValueError(
                f"start_url must use http or https scheme, got: {start_url!r}"
            )
        if not parsed_start.netloc:
            raise ValueError(f"start_url has no host: {start_url!r}")

        self.start_url: str = start_url
        self.max_depth: int = max_depth
        self.internal_only: bool = internal_only
        self.respect_robots: bool = respect_robots
        self.visited_urls: Set[str] = set()  # Store visited URLs
        self.queue: deque = deque()  # Queue for BFS crawling
        self.results: Dict[str, Dict[str, Any]] = {}  # Store results with metadata
        self.skipped_external_urls: Set[str] = set()  # Track skipped external URLs
        
        # Queue management
        self.max_queue_size: Optional[int] = max_queue_size
        self._paused: bool = False
        
        # Threading support
        self.max_workers: Optional[int] = max_workers if max_workers and max_workers > 0 else 1
        self._queue_lock: threading.Lock = threading.Lock()
        self._visited_lock: threading.Lock = threading.Lock()
        self._results_lock: threading.Lock = threading.Lock()
        self._delay_lock: threading.Lock = threading.Lock()
        self._last_request_time: float = 0.0
        
        # Request parameters
        self.user_agent: str = user_agent
        self.max_retries: int = max_retries
        self.timeout: int = timeout
        self.delay: float = delay
        
        # Extract domain and path information for URL filtering
        parsed_url = urlparse(start_url)
        self.base_domain: str = parsed_url.netloc
        self.start_path: str = parsed_url.path
        
        # If the URL ends with a trailing slash, keep it for proper path matching
        if not self.start_path.endswith('/') and self.start_path:
            self.start_path += '/'
        
        # For domain-only URLs (like example.com or example.com/), we'll crawl the whole site
        self.crawl_entire_domain: bool = not self.start_path or self.start_path == '/'
        
        # Initialize robots.txt handler if needed
        self.robots_handler: Optional[RobotsHandler] = RobotsHandler() if respect_robots else None
        if self.respect_robots:
            logger.info("Robots.txt handling enabled")
        else:
            logger.info("Robots.txt handling disabled")
            
        # Initialize extractors based on feature flags
        self.image_extraction_enabled: bool = enable_image_extraction
        self.keyword_extraction_enabled: bool = enable_keyword_extraction
        self.table_extraction_enabled: bool = enable_table_extraction
        self.content_extraction_enabled: bool = enable_content_extraction
        
        # Initialize content extractor only if enabled
        if self.content_extraction_enabled:
            self.content_extractor: Optional[ContentExtractor] = ContentExtractor()
            logger.info("Content extraction enabled")
        else:
            self.content_extractor: Optional[ContentExtractor] = None
            logger.info("Content extraction disabled")
        
        if self.image_extraction_enabled:
            self.image_extractor: Optional[ImageTagParser] = ImageTagParser()
            logger.info("Image extraction enabled")
        else:
            self.image_extractor: Optional[ImageTagParser] = None
            logger.info("Image extraction disabled")
            
        if self.keyword_extraction_enabled:
            self.keyword_extractor: Optional[KeywordExtractor] = KeywordExtractor()
            logger.info("Keyword extraction enabled")
        else:
            self.keyword_extractor: Optional[KeywordExtractor] = None
            logger.info("Keyword extraction disabled")
            
        if self.table_extraction_enabled:
            logger.info("Table extraction enabled")
        else:
            logger.info("Table extraction disabled")
        
        # New attribute for same_path_only
        self.same_path_only: bool = same_path_only
        
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
        
        logger.info(f"Base domain extracted: {self.base_domain}")
        if self.same_path_only:
            if self.crawl_entire_domain:
                logger.info(f"Crawling entire domain: {self.base_domain}")
            else:
                logger.info(f"Restricting crawl to path: {self.start_path}")
        
        if self.progress_tracker:
            logger.info("Progress tracking enabled")
        if self.url_filter:
            logger.info("Advanced URL filtering enabled")
        
        if self.max_queue_size:
            logger.info(f"Queue size limit: {self.max_queue_size}")
        
        if self.max_workers > 1:
            logger.info(f"Thread pool enabled with {self.max_workers} workers")
        else:
            logger.info("Single-threaded mode (no threading)")
        
        # Initialize page cache
        self.page_cache: Optional[PageCache] = page_cache
        if self.page_cache:
            logger.info("Page caching enabled")
        
        # Initialize storage manager
        if storage_manager:
            self.storage_manager: StorageManager = storage_manager
        else:
            self.storage_manager = StorageManager(
                store_html_content=store_html_content,
                enable_disk_storage=False
            )
        
        if not self.storage_manager.store_html_content:
            logger.info("HTML content storage disabled (memory optimization)")
        elif self.storage_manager.enable_disk_storage:
            logger.info(f"Disk-based HTML storage enabled at {self.storage_manager.storage_dir}")
        
        # Initialize sitemap parser if sitemap support is enabled
        self.use_sitemap = use_sitemap
        self.sitemap_urls = sitemap_urls or []
        self.sitemap_parser: Optional[SitemapParser] = None
        if self.use_sitemap:
            self.sitemap_parser = SitemapParser(timeout=self.timeout)
            logger.info("Sitemap support enabled")
        
        # Initialize rate limiter for per-domain rate limiting
        self.use_per_domain_delay = use_per_domain_delay
        if rate_limiter:
            self.rate_limiter: RateLimiter = rate_limiter
        else:
            self.rate_limiter = RateLimiter(default_delay=self.delay)
        
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
        self.budget_tracker: Optional[BudgetTracker] = budget_tracker
        if self.budget_tracker:
            logger.info("Budget tracking enabled")
            self.budget_tracker.start()
        
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
                # Note: JS renderer will be created per request to avoid threading issues

        # --- Apply CrawlerConfig overrides (config= takes precedence) ---
        if config is not None:
            self._apply_config(config)

        # --- Plugin extension points ---
        self.extractors: List[Any] = list(extractors or [])
        self.pipelines: List[Any] = list(pipelines or [])
        self.enable_pdf_extraction: bool = enable_pdf_extraction
        self.enable_js_embedded_data: bool = enable_js_embedded_data

        # Auto-register JSEmbeddedDataExtractor when flag is set and not already present
        if self.enable_js_embedded_data:
            from ..extractors.js_embedded_data import JSEmbeddedDataExtractor
            if not any(isinstance(e, JSEmbeddedDataExtractor) for e in self.extractors):
                self.extractors.append(JSEmbeddedDataExtractor())
                logger.info("JS embedded data extraction enabled")

        # Artifact store: url → PageArtifact
        self.artifacts: Dict[str, PageArtifact] = {}

        # Discovery metadata: populated before enqueuing, consumed during processing
        self._discovered_from: Dict[str, str] = {}
        self._discovery_method: Dict[str, str] = {}
        self._discovery_lock: threading.Lock = threading.Lock()

        # --- Type safety: reject async plugins in sync engine ---
        from ..interfaces import AsyncExtractor, AsyncPipeline
        for e in self.extractors:
            if isinstance(e, AsyncExtractor):
                raise TypeError(
                    f"Extractor '{e.name}' is an AsyncExtractor and cannot be used with the "
                    "synchronous Crawler.  Use AsyncCrawler or implement Extractor instead."
                )
        for p in self.pipelines:
            if isinstance(p, AsyncPipeline):
                raise TypeError(
                    f"Pipeline '{type(p).__name__}' is an AsyncPipeline and cannot be used "
                    "with the synchronous Crawler.  Use AsyncCrawler or implement Pipeline instead."
                )

        # --- Fetch abstraction (optional custom Fetcher) ---
        self.fetcher: Optional[Any] = fetcher

        # --- Incremental crawling ---
        self.incremental: Optional[Any] = incremental
        if self.incremental:
            logger.info("Incremental crawling enabled")

        # --- Crawl job / run metadata ---
        self.job = CrawlJob(
            run_id=run_id or __import__("uuid").uuid4().hex,
            started_at=None,   # set at crawl() time
            seed_urls=[self.start_url],
        )

        if self.extractors:
            logger.info(f"Registered extractors: {[e.name for e in self.extractors]}")
        if self.pipelines:
            logger.info(f"Registered pipelines: {[type(p).__name__ for p in self.pipelines]}")

    def _apply_config(self, config: Any) -> None:
        """Apply CrawlerConfig fields to override current instance settings."""
        if getattr(config, "start_url", None):
            self.start_url = config.start_url
        for attr in (
            "max_depth", "internal_only", "same_path_only", "respect_robots",
            "max_queue_size",
        ):
            if hasattr(config, attr):
                setattr(self, attr, getattr(config, attr))
        if hasattr(config, "max_workers") and config.max_workers:
            self.max_workers = config.max_workers

        fetch = getattr(config, "fetch", None)
        if fetch:
            for attr in ("user_agent", "max_retries", "timeout", "proxy",
                         "use_js_rendering", "js_wait_for_selector",
                         "js_wait_for_timeout", "js_browser_type"):
                if hasattr(fetch, attr):
                    setattr(self, attr, getattr(fetch, attr))

        rl = getattr(config, "rate_limit", None)
        if rl:
            if hasattr(rl, "delay"):
                self.delay = rl.delay
            if hasattr(rl, "use_per_domain_delay"):
                self.use_per_domain_delay = rl.use_per_domain_delay

        out = getattr(config, "output", None)
        if out:
            if getattr(out, "write_jsonl", False) and getattr(out, "jsonl_path", None):
                from ..pipelines.jsonl_writer import JSONLWriter
                self.pipelines.append(JSONLWriter(out.jsonl_path))
                logger.info(f"Auto-registered JSONLWriter → {out.jsonl_path}")
            if getattr(out, "write_blobs", False) and getattr(out, "blobs_dir", None):
                from ..pipelines.blob_store import BlobStore
                self.pipelines.append(BlobStore(out.blobs_dir))
                logger.info(f"Auto-registered BlobStore → {out.blobs_dir}")
            if getattr(out, "write_edges", False) and getattr(out, "edges_path", None):
                from ..pipelines.edges_writer import EdgesWriter
                self.pipelines.append(EdgesWriter(out.edges_path))
                logger.info(f"Auto-registered EdgesWriter → {out.edges_path}")

        for flag in (
            "enable_image_extraction", "enable_keyword_extraction",
            "enable_table_extraction", "enable_content_extraction",
            "enable_content_deduplication", "enable_pdf_extraction",
            "enable_js_embedded_data",
        ):
            if hasattr(config, flag):
                setattr(self, flag.replace("enable_", "") + "_enabled"
                        if flag.endswith("_extraction") or flag.endswith("_deduplication")
                        else flag, getattr(config, flag))
        # Resolve compound flag names to instance attrs
        if hasattr(config, "enable_image_extraction"):
            self.image_extraction_enabled = config.enable_image_extraction
        if hasattr(config, "enable_keyword_extraction"):
            self.keyword_extraction_enabled = config.enable_keyword_extraction
        if hasattr(config, "enable_table_extraction"):
            self.table_extraction_enabled = config.enable_table_extraction
        if hasattr(config, "enable_content_extraction"):
            self.content_extraction_enabled = config.enable_content_extraction
        if hasattr(config, "enable_pdf_extraction"):
            self.enable_pdf_extraction = config.enable_pdf_extraction
        if hasattr(config, "enable_js_embedded_data"):
            self.enable_js_embedded_data = config.enable_js_embedded_data

    def _extract_base_domain(self, url: str) -> str:
        """Extract the base domain from a URL"""
        parsed_url = urlparse(url)
        # Return the domain without any subdomain/port
        return parsed_url.netloc
    
    def _discover_sitemaps(self, session) -> None:
        """Discover and parse sitemaps to populate the queue"""
        sitemap_urls_to_parse = []
        
        # Get sitemaps from robots.txt if available
        if self.respect_robots and self.robots_handler:
            try:
                robots_sitemaps = get_sitemaps_from_robots(self.robots_handler, self.start_url)
                sitemap_urls_to_parse.extend(robots_sitemaps)
                if robots_sitemaps:
                    logger.info(f"Found {len(robots_sitemaps)} sitemap(s) in robots.txt")
            except Exception as e:
                logger.warning(f"Error extracting sitemaps from robots.txt: {e}")
        
        # Add explicitly provided sitemap URLs
        if self.sitemap_urls:
            sitemap_urls_to_parse.extend(self.sitemap_urls)
            logger.info(f"Using {len(self.sitemap_urls)} explicitly provided sitemap URL(s)")
        
        # Try common sitemap locations if no sitemaps found
        if not sitemap_urls_to_parse:
            parsed_url = urlparse(self.start_url)
            common_sitemaps = [
                f"{parsed_url.scheme}://{parsed_url.netloc}/sitemap.xml",
                f"{parsed_url.scheme}://{parsed_url.netloc}/sitemap_index.xml",
            ]
            sitemap_urls_to_parse.extend(common_sitemaps)
            logger.info("No sitemaps found, trying common locations")
        
        # Parse each sitemap and add URLs to queue
        urls_added = 0
        for sitemap_url in sitemap_urls_to_parse:
            try:
                url_info_list = self.sitemap_parser.parse_sitemap(sitemap_url, session)
                for url_info in url_info_list:
                    url = url_info['url']
                    # Check if URL should be crawled
                    if self._should_crawl(url):
                        # Check queue size limit
                        if self.max_queue_size and len(self.queue) >= self.max_queue_size:
                            logger.warning(f"Queue size limit ({self.max_queue_size}) reached while adding sitemap URLs")
                            break
                        with self._discovery_lock:
                            self._discovered_from[url] = sitemap_url
                            self._discovery_method[url] = "sitemap"
                        self.queue.append((url, 0))  # Sitemap URLs start at depth 0
                        urls_added += 1
                if urls_added > 0:
                    logger.info(f"Added {urls_added} URLs from sitemap: {sitemap_url}")
            except Exception as e:
                logger.warning(f"Error parsing sitemap {sitemap_url}: {e}")
                continue
        
        if urls_added > 0:
            logger.info(f"Total URLs added from sitemaps: {urls_added}")
        else:
            logger.info("No URLs found in sitemaps or all URLs were filtered out")

    def crawl(self) -> None:
        """Start the crawling process"""
        self.job.started_at = datetime.now(timezone.utc)

        # Start progress tracker if provided
        if self.progress_tracker:
            self.progress_tracker.start()
        
        # Get session from session manager
        session = self.session_manager.get_sync_session()
        
        # Discover and parse sitemaps if enabled
        if self.use_sitemap and self.sitemap_parser:
            self._discover_sitemaps(session)
        
        # Add the starting URL to the queue with depth 0
        self.queue.append((self.start_url, 0))
        
        # Use threading if max_workers > 1
        if self.max_workers > 1:
            self._crawl_with_threading(session)
        else:
            self._crawl_single_threaded(session)
        
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
        
        # Finish progress tracking
        if self.progress_tracker:
            self.progress_tracker.finish()
    
    def _crawl_single_threaded(self, session) -> None:
        """Single-threaded crawling (original implementation)"""
        while self.queue:
            # Check if paused
            while self._paused:
                time.sleep(0.1)  # Small sleep to avoid busy waiting
            
            # Check budget before processing next URL
            if self.budget_tracker:
                can_crawl, reason = self.budget_tracker.can_crawl_page()
                if not can_crawl:
                    logger.warning(f"Stopping crawl: {reason}")
                    break
            
            current_url, depth = self.queue.popleft()

            # Skip if we've already visited this URL or exceeded max depth
            if current_url in self.visited_urls:
                continue
            if depth > self.max_depth:
                continue

            # Mark as visited here (before processing) so that any links
            # added to the queue during processing cannot re-enqueue this URL.
            self.visited_urls.add(current_url)

            # Rate limiting is handled in _process_url
            # Process the URL
            self._process_url(current_url, depth, session)
    
    def _crawl_with_threading(self, session) -> None:
        """Multi-threaded crawling using ThreadPoolExecutor"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            while self.queue or futures:
                # Check if paused
                while self._paused:
                    time.sleep(0.1)
                
                # Check budget before submitting new tasks
                if self.budget_tracker:
                    can_crawl, reason = self.budget_tracker.can_crawl_page()
                    if not can_crawl:
                        logger.warning(f"Stopping crawl: {reason}")
                        # Wait for existing futures to complete
                        break
                
                # Submit new tasks from queue
                while len(futures) < self.max_workers:
                    with self._queue_lock:
                        if not self.queue:
                            break
                        current_url, depth = self.queue.popleft()

                    # Check depth limit before acquiring the visited lock
                    if depth > self.max_depth:
                        continue

                    # Atomically check-and-mark as visited before submitting.
                    # This prevents the race where two loop iterations dequeue
                    # the same URL, both pass the "in visited_urls" check, and
                    # both submit a worker — resulting in a double-fetch.
                    with self._visited_lock:
                        if current_url in self.visited_urls:
                            continue
                        # Mark as visited now, before the worker starts, so no
                        # other iteration can submit the same URL concurrently.
                        self.visited_urls.add(current_url)

                    # Submit task to thread pool
                    future = executor.submit(self._process_url, current_url, depth, session)
                    futures[future] = (current_url, depth)
                
                # Process completed tasks
                if futures:
                    try:
                        for future in as_completed(futures, timeout=0.1):
                            if future in futures:
                                try:
                                    future.result()  # Get result to raise any exceptions
                                except Exception as e:
                                    url, depth = futures[future]
                                    logger.error(f"Error in thread processing {url}: {e}")
                                finally:
                                    del futures[future]
                                    break
                    except TimeoutError:
                        # Some futures are still running, continue loop
                        pass
    
    def _process_url(self, url: str, depth: int, session) -> None:
        """Process a single URL (thread-safe)"""
        # Apply per-domain rate limiting if enabled
        if self.use_per_domain_delay:
            # Check for crawl-delay from robots.txt if available
            if self.respect_robots and self.robots_handler:
                try:
                    crawl_delay = self.robots_handler.get_crawl_delay(url, self.user_agent)
                    if crawl_delay is not None:
                        domain = urlparse(url).netloc.lower()
                        self.rate_limiter.set_domain_delay(domain, crawl_delay)
                        logger.debug(f"Using crawl-delay {crawl_delay}s from robots.txt for {domain}")
                except Exception as e:
                    logger.debug(f"Could not get crawl-delay from robots.txt: {e}")
            
            # Wait if needed for this domain
            self.rate_limiter.wait_if_needed(url)
        else:
            # Apply global delay between requests if needed (thread-safe)
            if self.delay > 0:
                with self._delay_lock:
                    current_time = time.time()
                    time_since_last_request = current_time - self._last_request_time
                    if time_since_last_request < self.delay:
                        time.sleep(self.delay - time_since_last_request)
                    self._last_request_time = time.time()
        
        logger.info(f"Crawling: {url} (depth: {depth})")

        # Retrieve discovery context recorded when this URL was enqueued
        with self._discovery_lock:
            discovered_from = self._discovered_from.pop(url, None)
            discovery_method = self._discovery_method.pop(url, "seed" if depth == 0 else "link")

        # Build the PageArtifact early so extractors/pipelines always receive one
        artifact = PageArtifact(
            url=url,
            fetched_at=datetime.now(timezone.utc),
            crawl=CrawlMeta(
                depth=depth,
                discovered_from=discovered_from,
                discovery_method=discovery_method,
                run_id=self.job.run_id,
            ),
        )

        # --- Incremental: get conditional headers (If-None-Match / If-Modified-Since) ---
        incremental_headers: Dict[str, str] = {}
        if self.incremental:
            try:
                incremental_headers = self.incremental.get_conditional_headers(url) or {}
            except Exception as _e:
                logger.debug(f"Incremental header lookup failed for {url}: {_e}")

        # Initialize result data for this URL (thread-safe)
        with self._results_lock:
            self.results[url] = {
                'depth': depth,
                'status': None,
                'headers': None,
                'links': [],
                'content_type': None,
                'error': None,
                'success': False
            }
        
        # Check cache first
        cached_data = None
        if self.page_cache:
            cached_data = self.page_cache.get(url)
        
        if cached_data:
            # Use cached data
            logger.debug(f"Using cached data for {url}")
            status_code = cached_data.get('status_code', 200)
            headers = cached_data.get('headers', {})
            response_data = cached_data.get('response_data', {})
            content = cached_data.get('content')
            
            success = status_code == 200
            
            # Case-insensitive content-type lookup for cached headers
            cached_content_type = next((v for k, v in headers.items() if k.lower() == 'content-type'), '')
            
            with self._results_lock:
                self.results[url]['status'] = status_code
                self.results[url]['success'] = success
                self.results[url]['headers'] = headers
                self.results[url]['content_type'] = cached_content_type

            # Process cached content similar to fresh fetch
            if success and content and cached_content_type.split(';')[0].strip().lower() == 'text/html':
                # Process cached HTML content
                self._process_cached_content(url, depth, content, headers)
            return
        
        # Fetch the page using our fetcher with session
        success, response_or_error, status_code = fetch_page(
            url,
            self.user_agent,
            self.max_retries,
            self.timeout,
            session=session,
            use_js_rendering=self.use_js_rendering,
            js_renderer=None,  # Create new renderer per request to avoid threading issues
            wait_for_selector=self.js_wait_for_selector,
            wait_for_timeout=self.js_wait_for_timeout,
            proxy=self.proxy,
            proxy_manager=self.proxy_manager,
            extra_headers=incremental_headers if incremental_headers else None,
        )

        # --- Incremental: handle 304 Not Modified ---
        if status_code == 304:
            logger.debug(f"304 Not Modified for {url} — skipping reprocessing")
            artifact.http = HTTPInfo(status=304, content_type=None)
            artifact.add_error(CrawlError.not_modified())
            with self._results_lock:
                self.results[url]['status'] = 304
                self.artifacts[url] = artifact
            if self.incremental:
                try:
                    self.incremental.record_response(url, 304)
                except Exception as _e:
                    logger.debug(f"Incremental record failed for {url}: {_e}")
            return
        
        # Update results (thread-safe)
        with self._results_lock:
            self.results[url]['status'] = status_code
            self.results[url]['success'] = success
        
        if success:
            response = response_or_error
            
            # Store response headers (use CaseInsensitiveDict for content_type lookup)
            headers = dict(response.headers)
            content_type = response.headers.get('Content-Type', '')
            
            with self._results_lock:
                self.results[url]['headers'] = headers
                self.results[url]['content_type'] = content_type
            
            # Record bytes downloaded for budget tracking
            if self.budget_tracker:
                # Try to get content length from header, otherwise estimate from content
                content_length = headers.get('Content-Length')
                if content_length:
                    bytes_downloaded = int(content_length)
                else:
                    # Estimate from response content if available
                    try:
                        if hasattr(response, 'content'):
                            bytes_downloaded = len(response.content)
                        elif hasattr(response, 'text'):
                            bytes_downloaded = len(response.text.encode('utf-8'))
                        else:
                            bytes_downloaded = 0
                    except Exception:
                        bytes_downloaded = 0
                
                if bytes_downloaded > 0:
                    self.budget_tracker.record_page(bytes_downloaded)
            
            # Populate artifact HTTP info
            artifact.http = HTTPInfo(
                status=status_code,
                headers=headers,
                content_type=content_type,
                etag=headers.get("ETag") or headers.get("etag"),
                last_modified=headers.get("Last-Modified") or headers.get("last-modified"),
                cache_control=headers.get("Cache-Control") or headers.get("cache-control"),
            )

            # Cache will be updated after HTML content is processed

            try:
                # Initialize links list for all URLs
                links = []

                content_type_base = content_type.split(';')[0].strip().lower()

                # Process the page to extract links if it's HTML
                if content_type_base == 'text/html':
                    html_content = response.text

                    # Check for duplicate content
                    if self.content_deduplicator.enabled:
                        if self.content_deduplicator.is_duplicate(html_content, url):
                            logger.info(f"Skipping duplicate content at {url}")
                            duplicate_urls = self.content_deduplicator.get_duplicate_urls(url)
                            with self._results_lock:
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
                        with self._results_lock:
                            self.results[url]['html_content'] = stored_html

                    # Populate artifact content
                    artifact.content = ContentInfo(raw_html=html_content)

                    # Use ContentExtractor to extract all page metadata if enabled
                    if self.content_extraction_enabled and self.content_extractor:
                        content_data = self.content_extractor.extract_content(html_content, url, response)

                        # Merge content extractor results with page results
                        with self._results_lock:
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
                        # Mirror into artifact
                        for key in ('title', 'meta_description', 'meta_keywords',
                                    'canonical_url', 'language', 'headings',
                                    'images_with_context', 'page_type', 'last_modified'):
                            val = content_data.get(key)
                            if val is not None:
                                artifact.extracted[key] = val
                        logger.debug(f"Extracted metadata for {url}")

                    # Extract links from HTML content
                    links = extract_links(html_content, url)
                    logger.debug(f"Extracted {len(links)} links from HTML content at {url}")

                    # Extract images from the page if extraction is enabled
                    if self.image_extraction_enabled:
                        images = self.image_extractor.extract_images(html_content)
                        with self._results_lock:
                            self.results[url]['images'] = images
                        artifact.extracted['images'] = images
                        logger.debug(f"Extracted {len(images)} images from {url}")

                    # Extract keywords from the page if extraction is enabled
                    if self.keyword_extraction_enabled:
                        keywords_data = self.keyword_extractor.extract_keywords(html_content, include_scores=True)
                        keyphrases = self.keyword_extractor.extract_keyphrases(html_content)
                        with self._results_lock:
                            self.results[url]['keywords'] = keywords_data['keywords']
                            self.results[url]['keyword_scores'] = keywords_data['scores']
                            self.results[url]['keyphrases'] = keyphrases
                        artifact.extracted['keywords'] = keywords_data['keywords']
                        artifact.extracted['keyword_scores'] = keywords_data['scores']
                        artifact.extracted['keyphrases'] = keyphrases
                        logger.debug(f"Extracted {len(keywords_data['keywords'])} keywords and {len(keyphrases)} keyphrases from {url}")

                    # Extract tables from the page if extraction is enabled
                    if self.table_extraction_enabled:
                        try:
                            tables = extract_tables(html_content, min_rows=1, min_columns=1)
                            with self._results_lock:
                                self.results[url]['tables'] = tables
                            artifact.extracted['tables'] = tables
                            logger.debug(f"Extracted {len(tables)} tables from {url}")
                        except Exception as e:
                            logger.error(f"Error extracting tables from {url}: {e}")
                            with self._results_lock:
                                self.results[url]['tables'] = []

                    # Run plugin extractors on the HTML
                    for extractor in self.extractors:
                        try:
                            result = extractor.extract(html_content, artifact)
                            if result is not None:
                                artifact.extracted[extractor.name] = result
                        except Exception as exc:
                            logger.warning(f"Extractor '{extractor.name}' failed for {url}: {exc}")
                            artifact.add_error(CrawlError.extractor(extractor.name, str(exc)))

                    # Cache the response if cache is enabled
                    if self.page_cache:
                        self.page_cache.set(
                            url,
                            self.results[url],
                            status_code,
                            headers,
                            html_content
                        )

                elif content_type_base == 'application/pdf' and self.enable_pdf_extraction:
                    # --- PDF content-type routing ---
                    try:
                        from ..extractors.pdf_extractor import PDFExtractor, is_pdf_available
                        if is_pdf_available():
                            pdf_bytes = response.content
                            pdf_extractor = PDFExtractor()
                            pdf_result = pdf_extractor.extract_from_bytes(pdf_bytes)
                            with self._results_lock:
                                self.results[url]['pdf_data'] = pdf_result
                            artifact.extracted['pdf'] = pdf_result
                            artifact.content = ContentInfo(
                                raw_html=pdf_bytes.decode('latin-1', errors='replace'),
                                size_bytes=len(pdf_bytes),
                            )
                            artifact.downloads.append(DownloadRecord(
                                url=url,
                                bytes_downloaded=len(pdf_bytes),
                                content_type='application/pdf',
                                parse_status='success' if pdf_result else 'empty',
                            ))
                            logger.debug(f"PDF extracted from {url}")
                        else:
                            logger.debug(f"PDF extraction skipped (no PDF library) for {url}")
                    except Exception as e:
                        logger.warning(f"PDF extraction failed for {url}: {e}")
                        artifact.add_error(CrawlError.pdf(str(e)))
                else:
                    logger.debug(f"Skipping content extraction for non-HTML content type: {content_type} at {url}")

                # Store the links in the results (even if empty for non-HTML content)
                artifact.links = links
                with self._results_lock:
                    self.results[url]['links'] = links

                # Record progress for successful URL
                if self.progress_tracker:
                    with self._results_lock:
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

                # --- Incremental: record ETag/Last-Modified for next run ---
                if self.incremental:
                    try:
                        self.incremental.record_response(
                            url,
                            status_code,
                            etag=artifact.http.etag,
                            last_modified=artifact.http.last_modified,
                            content=artifact.content.raw_html,
                        )
                    except Exception as _e:
                        logger.debug(f"Incremental record failed for {url}: {_e}")

                # Run pipeline stages on the completed artifact
                self._run_pipelines(artifact)

                # Add new links to the queue (thread-safe)
                for link in links:
                    if self._should_crawl(link):
                        with self._queue_lock:
                            # Check queue size limit
                            if self.max_queue_size and len(self.queue) >= self.max_queue_size:
                                logger.warning(f"Queue size limit ({self.max_queue_size}) reached, skipping URL: {link}")
                                continue
                            with self._discovery_lock:
                                self._discovered_from[link] = url
                                self._discovery_method[link] = "link"
                            self.queue.append((link, depth + 1))
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                artifact.add_error(CrawlError(code="UNKNOWN", message=str(e), source="engine"))
                with self._results_lock:
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
            err_msg = str(response_or_error)
            artifact.add_error(CrawlError.fetch(err_msg, http_status=status_code))
            with self._results_lock:
                self.results[url]['error'] = err_msg
            # Record progress for failed URL
            if self.progress_tracker:
                self.progress_tracker.record_url(
                    url,
                    False,
                    links_found=0,
                    depth=depth
                )

        # Store artifact (always, even on failure, so callers have a record)
        with self._results_lock:
            self.artifacts[url] = artifact
    
    def _should_crawl(self, url: str) -> bool:
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
                if len(self.skipped_external_urls) < self._MAX_SKIPPED_EXTERNAL:
                    self.skipped_external_urls.add(url)
                logger.debug(f"Skipping external URL: {url} (external domain)")
                return False

            # If same_path_only is True, check path restriction
            if self.same_path_only and not self.crawl_entire_domain:
                # For path-specific crawling, ensure the URL path starts with the start_path
                if not parsed_url.path.startswith(self.start_path):
                    if len(self.skipped_external_urls) < self._MAX_SKIPPED_EXTERNAL:
                        self.skipped_external_urls.add(url)
                    logger.debug(f"Skipping external URL: {url} (not under {self.start_path})")
                    return False
        
        # Check robots.txt rules if enabled
        if self.respect_robots and self.robots_handler:
            if not self.robots_handler.can_fetch(url, self.user_agent):
                logger.debug(f"Skipping URL disallowed by robots.txt: {url}")
                return False
        
        # Check URL filter if provided
        if self.url_filter and not self.url_filter.is_allowed(url):
            logger.debug(f"Skipping URL blocked by URLFilter: {url}")
            return False
        
        return True
        
    def _run_pipelines(self, artifact: PageArtifact) -> None:
        """Run all registered pipeline stages on *artifact* (thread-safe).

        Each stage receives a :meth:`~PageArtifact.copy` of the current artifact
        so that a failing stage cannot corrupt the state seen by later stages.
        """
        current = artifact
        for pipeline in self.pipelines:
            if current is None:
                break
            snapshot = current.copy()  # snapshot before each stage
            try:
                current = pipeline.process(current)
            except Exception as exc:
                logger.warning(
                    f"Pipeline '{type(pipeline).__name__}' failed for {artifact.url}: {exc}"
                )
                current = snapshot  # restore pre-failure state
        with self._results_lock:
            self.artifacts[artifact.url] = current if current is not None else artifact

    def get_results(self) -> Dict[str, Dict[str, Any]]:
        """Return the detailed crawl results (legacy dict format)."""
        return self.results

    def get_artifacts(self) -> Dict[str, PageArtifact]:
        """Return crawl results as :class:`~crawlit.models.PageArtifact` objects."""
        return self.artifacts

    def get_skipped_external_urls(self) -> List[str]:
        """Return the list of skipped external URLs"""
        return list(self.skipped_external_urls)
        
    def get_skipped_robots_paths(self) -> List[str]:
        """Return the list of URLs skipped due to robots.txt rules"""
        if self.robots_handler:
            return self.robots_handler.get_skipped_paths()
        return []
    
    def is_valid_url(self, url: str) -> bool:
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
                if len(self.skipped_external_urls) < self._MAX_SKIPPED_EXTERNAL:
                    self.skipped_external_urls.add(url)
                return False

        return True

    def _extract_links(self, url: str, soup: Any) -> List[str]:
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
                if len(self.skipped_external_urls) < self._MAX_SKIPPED_EXTERNAL:
                    self.skipped_external_urls.add(href)
                logger.debug(f"Skipping external URL: {href} (external domain)")
                continue
            
            # If same_path_only is True and we're not crawling the entire domain,
            # check path restriction
            if self.same_path_only and not self.crawl_entire_domain:
                if not parsed_href.path.startswith(self.start_path):
                    if len(self.skipped_external_urls) < self._MAX_SKIPPED_EXTERNAL:
                        self.skipped_external_urls.add(href)
                    logger.debug(f"Skipping path-external URL: {href} (not under {self.start_path})")
                    continue
            
            links.append(href)
        
        return links
    
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
    
    def save_state(self, filepath: str) -> None:
        """
        Save the current crawler state to a file.
        
        Args:
            filepath: Path to save the state file
        """
        metadata = {
            'start_url': self.start_url,
            'max_depth': self.max_depth,
            'internal_only': self.internal_only,
            'respect_robots': self.respect_robots,
            'max_queue_size': self.max_queue_size
        }
        QueueManager.save_state(
            self.queue,
            self.visited_urls,
            self.results,
            filepath,
            metadata
        )
    
    def load_state(self, filepath: str) -> None:
        """
        Load crawler state from a file.
        
        Args:
            filepath: Path to the state file
        """
        self.queue, self.visited_urls, self.results, metadata = QueueManager.load_state(filepath)
        
        # Optionally restore metadata
        if metadata:
            logger.info(f"Loaded state metadata: {metadata}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current queue.
        
        Returns:
            Dictionary with queue statistics
        """
        return QueueManager.get_queue_stats(self.queue)
    
    def _process_cached_content(self, url: str, depth: int, content: str, headers: Dict[str, Any]) -> None:
        """Process cached HTML content (similar to fresh fetch processing)"""
        try:
            links = []
            
            # Store HTML content using storage manager
            stored_html = self.storage_manager.store_html(url, content)
            if stored_html is not None:
                with self._results_lock:
                    self.results[url]['html_content'] = stored_html
            
            # Use ContentExtractor to extract all page metadata if enabled
            if self.content_extraction_enabled and self.content_extractor:
                # Content extractor can work without response object
                content_data = self.content_extractor.extract_content(content, url, None)
                
                # Merge content extractor results with page results
                with self._results_lock:
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
                logger.debug(f"Extracted metadata from cache for {url}")
            
            # Extract links from HTML content
            links = extract_links(content, url)
            logger.debug(f"Extracted {len(links)} links from cached HTML content at {url}")
            
            # Extract images from the page if extraction is enabled
            if self.image_extraction_enabled:
                images = self.image_extractor.extract_images(content)
                with self._results_lock:
                    self.results[url]['images'] = images
                logger.debug(f"Extracted {len(images)} images from cached {url}")
            
            # Extract keywords from the page if extraction is enabled
            if self.keyword_extraction_enabled:
                keywords_data = self.keyword_extractor.extract_keywords(content, include_scores=True)
                keyphrases = self.keyword_extractor.extract_keyphrases(content)
                with self._results_lock:
                    self.results[url]['keywords'] = keywords_data['keywords']
                    self.results[url]['keyword_scores'] = keywords_data['scores']
                    self.results[url]['keyphrases'] = keyphrases
                logger.debug(f"Extracted {len(keywords_data['keywords'])} keywords and {len(keyphrases)} keyphrases from cached {url}")
            
            # Extract tables from the page if extraction is enabled
            if self.table_extraction_enabled:
                try:
                    tables = extract_tables(content, min_rows=1, min_columns=1)
                    with self._results_lock:
                        self.results[url]['tables'] = tables
                    logger.debug(f"Extracted {len(tables)} tables from cached {url}")
                except Exception as e:
                    logger.error(f"Error extracting tables from cached {url}: {e}")
                    with self._results_lock:
                        self.results[url]['tables'] = []
            
            # Store the links in the results
            with self._results_lock:
                self.results[url]['links'] = links
            
            # Record progress for successful URL
            if self.progress_tracker:
                with self._results_lock:
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
            
            # Add new links to the queue (thread-safe)
            for link in links:
                if self._should_crawl(link):
                    with self._queue_lock:
                        # Check queue size limit
                        if self.max_queue_size and len(self.queue) >= self.max_queue_size:
                            logger.warning(f"Queue size limit ({self.max_queue_size}) reached, skipping URL: {link}")
                            continue
                        self.queue.append((link, depth + 1))
        except Exception as e:
            logger.error(f"Error processing cached content for {url}: {e}")
            with self._results_lock:
                self.results[url]['error'] = str(e)
    
    def resume_from(self, filepath: str) -> None:
        """
        Resume crawling from a saved state file.
        
        Args:
            filepath: Path to the saved state file
        """
        if not CrawlResume.can_resume(filepath):
            raise ValueError(f"Cannot resume from {filepath}: file not found or invalid")
        
        resume_info = CrawlResume.get_resume_info(filepath)
        logger.info(f"Resuming crawl from {filepath}")
        logger.info(f"  - Saved at: {resume_info.get('saved_at')}")
        logger.info(f"  - Queue size: {resume_info.get('queue_size')}")
        logger.info(f"  - Visited URLs: {resume_info.get('visited_count')}")
        logger.info(f"  - Results: {resume_info.get('results_count')}")
        
        # Load the state
        self.load_state(filepath)
        
        # Continue crawling
        session = self.session_manager.get_sync_session()
        if self.max_workers > 1:
            self._crawl_with_threading(session)
        else:
            self._crawl_single_threaded(session)