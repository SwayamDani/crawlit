#!/usr/bin/env python3
"""
crawlit - Modular, Ethical Python Web Crawler

A flexible web crawler library that can be used programmatically or via CLI.
"""

__version__ = '1.0.0'

# Export stable data models (v1.2+)
from crawlit.models import (
    PageArtifact,
    HTTPInfo,
    ContentInfo,
    DownloadRecord,
    CrawlMeta,
    ArtifactSource,
    SCHEMA_VERSION,
    ERROR_CODES,
    CrawlError,
    CrawlJob,
)

# Export composable config (v1.1+)
from crawlit.config import CrawlerConfig, FetchConfig, RateLimitConfig, OutputConfig

# Export plugin interfaces (v1.2+)
from crawlit.interfaces import (
    Extractor, AsyncExtractor, Pipeline, AsyncPipeline,
    FetchRequest, FetchResult, Fetcher, AsyncFetcher,
)

# Export default fetcher implementations (v1.1+)
from crawlit.fetchers import DefaultFetcher, DefaultAsyncFetcher

# Export content-type router (v1.2+)
from crawlit.content_router import ContentRouter

# Export built-in pipelines (v1.2+)
from crawlit.pipelines import JSONLWriter, BlobStore, EdgesWriter, ArtifactStore

# Export cross-run deduplication store (v1.2+)
from crawlit.utils.content_hash_store import ContentHashStore

# Export core functionality
from crawlit.crawler.engine import Crawler
from crawlit.crawler.async_engine import AsyncCrawler
from crawlit.output.formatters import save_results, generate_summary_report

# Export fetcher functionality
from crawlit.crawler.fetcher import fetch_url, fetch_page
from crawlit.crawler.async_fetcher import fetch_url_async, fetch_page_async, ResponseLike

# Export extraction modules (v0.2.0+)
from crawlit.extractors.tables import extract_tables, tables_to_csv, tables_to_dict, tables_to_json
from crawlit.extractors.image_extractor import ImageTagParser
from crawlit.extractors.keyword_extractor import KeywordExtractor
from crawlit.extractors.forms import FormExtractor, Form, FormField, extract_forms
from crawlit.extractors.structured_data import StructuredDataExtractor, StructuredData, extract_structured_data
from crawlit.extractors.language import LanguageDetector, LanguageDetection, detect_language
from crawlit.extractors.pdf_extractor import PDFExtractor, extract_pdf_text, is_pdf_available
from crawlit.extractors.js_embedded_data import JSEmbeddedDataExtractor, extract_js_embedded_data

# Export compatibility utilities
from crawlit.compat import ensure_response_compatibility, is_async_context

# Export utility modules
from crawlit.utils import (
    SessionManager,
    URLFilter,
    ProgressTracker,
    create_progress_callback,
    QueueManager,
    PageCache,
    CrawlResume,
    StorageManager,
    SitemapParser,
    get_sitemaps_from_robots,
    get_sitemaps_from_robots_async,
    RateLimiter,
    AsyncRateLimiter,
    DynamicRateLimiter,
    AsyncDynamicRateLimiter,
    ContentDeduplicator,
    BudgetTracker,
    AsyncBudgetTracker,
    BudgetLimits,
    URLPriorityQueue,
    AsyncURLPriorityQueue,
    PriorityStrategy,
    BreadthFirstStrategy,
    DepthFirstStrategy,
    SitemapPriorityStrategy,
    URLPatternStrategy,
    CompositeStrategy,
    get_strategy,
    CookieJar,
    save_cookies,
    load_cookies,
    DownloadManager,
    IncrementalCrawler,
    CrawlScheduler,
    ScheduledCrawl,
    is_croniter_available,
    LoggingConfig,
    configure_logging,
    get_logger,
    log_with_context,
    CrawlitError,
    FetchError,
    RobotsError,
    ParseError,
    ExtractionError,
    handle_fetch_error,
    AuthManager,
    AuthConfig,
    create_basic_auth,
    create_bearer_auth,
    create_api_key_auth,
    create_custom_auth,
    create_digest_auth,
    EnvLoader,
    ConfigLoader,
    load_env,
    getenv
)

# Export database integration (v0.2.0+)
from crawlit.utils.database import (
    DatabaseBackend,
    SQLiteBackend,
    PostgreSQLBackend,
    MongoDBBackend,
    get_database_backend
)

# Export proxy support (v0.2.0+)
from crawlit.utils.proxy_manager import ProxyManager, Proxy

# Export distributed crawling (v0.2.0+)
# These names are only available when optional deps (pika / kafka-python) are
# installed.  We define them as None here so the module-level namespace is
# consistent; callers that need them should install crawlit[distributed].
_DISTRIBUTED_AVAILABLE = False
try:
    from crawlit.distributed import (
        MessageQueue,
        RabbitMQBackend,
        KafkaBackend,
        get_message_queue,
        DistributedCrawler,
        CrawlWorker,
        CrawlCoordinator,
        ConnectionPool,
        DatabaseConnectionPool,
        HTTPConnectionPool,
    )
    _DISTRIBUTED_AVAILABLE = True
except ImportError:
    MessageQueue = None  # type: ignore[assignment,misc]
    RabbitMQBackend = None  # type: ignore[assignment,misc]
    KafkaBackend = None  # type: ignore[assignment,misc]
    get_message_queue = None  # type: ignore[assignment]
    DistributedCrawler = None  # type: ignore[assignment,misc]
    CrawlWorker = None  # type: ignore[assignment,misc]
    CrawlCoordinator = None  # type: ignore[assignment,misc]
    ConnectionPool = None  # type: ignore[assignment,misc]
    DatabaseConnectionPool = None  # type: ignore[assignment,misc]
    HTTPConnectionPool = None  # type: ignore[assignment,misc]

# Export security features (v0.2.0+)
from crawlit.security import (
    CSRFTokenExtractor,
    CSRFTokenHandler,
    SecurityHeadersAnalyzer,
    SecurityRating,
    analyze_security_headers,
    WAFDetector,
    WAFType,
    detect_waf,
    HoneypotDetector,
    detect_honeypots,
    CaptchaDetector,
    CaptchaType,
    detect_captcha
)

# CLI functionality (but not executed on import)
def cli_main():
    """Entry point for the CLI interface when installed with [cli] option"""
    from crawlit.crawlit import main
    return main()

__all__ = [
    '__version__',
    # Stable data models (v1.2+)
    'SCHEMA_VERSION',
    'ERROR_CODES',
    'CrawlError',
    'CrawlJob',
    'PageArtifact',
    'HTTPInfo',
    'ContentInfo',
    'DownloadRecord',
    'CrawlMeta',
    'ArtifactSource',
    # Composable config (v1.1+)
    'CrawlerConfig',
    'FetchConfig',
    'RateLimitConfig',
    'OutputConfig',
    # Plugin interfaces (v1.2+)
    'Extractor',
    'AsyncExtractor',
    'Pipeline',
    'AsyncPipeline',
    'FetchRequest',
    'FetchResult',
    'Fetcher',
    'AsyncFetcher',
    # Default fetcher implementations (v1.1+)
    'DefaultFetcher',
    'DefaultAsyncFetcher',
    # Content-type router (v1.2+)
    'ContentRouter',
    # Built-in pipelines (v1.2+)
    'JSONLWriter',
    'BlobStore',
    'EdgesWriter',
    'ArtifactStore',
    # Cross-run deduplication (v1.2+)
    'ContentHashStore',
    # Core
    'Crawler',           # Main crawler engine
    'AsyncCrawler',      # Async crawler engine
    'fetch_url',         # Fetch URL (sync)
    'fetch_page',        # Fetch page (sync)
    'fetch_url_async',   # Fetch URL (async)
    'fetch_page_async',  # Fetch page (async)
    'ResponseLike',      # Response interface wrapper
    'ensure_response_compatibility',  # Compatibility helper
    'is_async_context',  # Context detection
    'save_results',      # Output formatters 
    'generate_summary_report',
    'cli_main',          # CLI entry point
    
    # Data extraction modules (v0.2.0+)
    'extract_tables',    # Table extraction
    'tables_to_csv',     # Table outputs
    'tables_to_dict',
    'tables_to_json',
    'ImageTagParser',    # Image extraction
    'KeywordExtractor',  # Keyword extraction
    'FormExtractor',     # Form extraction (NEW)
    'Form',              # Form data class
    'FormField',         # Form field data class
    'extract_forms',     # Convenience function
    'StructuredDataExtractor',  # Structured data extraction (NEW)
    'StructuredData',    # Structured data container
    'extract_structured_data',  # Convenience function
    'LanguageDetector',  # Language detection (NEW)
    'LanguageDetection', # Language detection result
    'detect_language',   # Convenience function
    'PDFExtractor',      # PDF text extraction (NEW)
    'extract_pdf_text',  # Convenience function
    'is_pdf_available',  # Check PDF support
    'JSEmbeddedDataExtractor',  # JS embedded data extraction (v1.1+)
    'extract_js_embedded_data', # Convenience function

    # Utility modules
    'SessionManager',    # Session management
    'URLFilter',         # URL filtering
    'ProgressTracker',   # Progress tracking
    'create_progress_callback',  # Progress callback helper
    'QueueManager',      # Queue management
    'PageCache',         # Page caching
    'CrawlResume',       # Crawl resume utilities
    'StorageManager',    # HTML content storage management
    'SitemapParser',     # Sitemap parsing
    'get_sitemaps_from_robots',  # Extract sitemaps from robots.txt
    'get_sitemaps_from_robots_async',  # Extract sitemaps from robots.txt (async)
    'RateLimiter',       # Per-domain rate limiting (sync)
    'AsyncRateLimiter',  # Per-domain rate limiting (async)
    'DynamicRateLimiter',  # Dynamic rate limiting (sync)
    'AsyncDynamicRateLimiter',  # Dynamic rate limiting (async)
    'ContentDeduplicator',  # Content-based deduplication
    'BudgetTracker',     # Crawl budget tracking (sync)
    'AsyncBudgetTracker',  # Crawl budget tracking (async)
    'BudgetLimits',      # Budget limits configuration
    'URLPriorityQueue',  # URL priority queue (sync)
    'AsyncURLPriorityQueue',  # URL priority queue (async)
    'PriorityStrategy',  # Base priority strategy
    'BreadthFirstStrategy',  # Breadth-first priority
    'DepthFirstStrategy',    # Depth-first priority
    'SitemapPriorityStrategy',  # Sitemap-based priority
    'URLPatternStrategy',    # Pattern-based priority
    'CompositeStrategy',     # Composite strategy
    'get_strategy',          # Strategy factory
    'CookieJar',             # Cookie jar with persistence
    'save_cookies',          # Save cookies to file
    'load_cookies',          # Load cookies from file
    'DownloadManager',       # File download manager
    'IncrementalCrawler',    # Incremental crawling with ETags
    'CrawlScheduler',        # Cron-like crawl scheduling
    'ScheduledCrawl',        # Scheduled crawl configuration
    'is_croniter_available', # Check cron support
    'LoggingConfig',     # Enhanced logging configuration
    'configure_logging', # Convenience function for logging setup
    'get_logger',        # Get logger instance
    'log_with_context',  # Log with additional context
    'CrawlitError',      # Base exception
    'FetchError',        # Fetch exception
    'RobotsError',       # Robots.txt exception
    'ParseError',        # HTML parse exception
    'ExtractionError',   # Content extraction exception
    'handle_fetch_error',  # Error handler
    
    # Authentication & Configuration (v0.2.0+)
    'AuthManager',       # Authentication manager
    'AuthConfig',        # Authentication configuration
    'create_basic_auth', # Create Basic auth
    'create_bearer_auth',  # Create Bearer token auth
    'create_api_key_auth',  # Create API key auth
    'create_custom_auth',  # Create custom header auth
    'create_digest_auth',  # Create Digest auth
    'EnvLoader',         # Environment variable loader
    'ConfigLoader',      # Configuration file loader
    'load_env',          # Load .env file
    'getenv',            # Get environment variable
    
    # Database integration (v0.2.0+)
    'DatabaseBackend',   # Abstract database backend
    'SQLiteBackend',     # SQLite backend
    'PostgreSQLBackend', # PostgreSQL backend
    'MongoDBBackend',    # MongoDB backend
    'get_database_backend',  # Database factory
    
    # Proxy support (v0.2.0+)
    'ProxyManager',      # Proxy manager with rotation and health tracking
    'Proxy',             # Proxy data class
    
    # Security features (v0.2.0+)
    'CSRFTokenExtractor',   # Extract CSRF tokens
    'CSRFTokenHandler',     # Handle CSRF tokens during crawling
    'SecurityHeadersAnalyzer',  # Analyze security headers
    'SecurityRating',       # Security rating enum
    'analyze_security_headers',  # Convenience function
    'WAFDetector',          # Detect Web Application Firewalls
    'WAFType',              # WAF type enum
    'detect_waf',           # Convenience function
    'HoneypotDetector',     # Detect honeypot traps
    'detect_honeypots',     # Convenience function
    'CaptchaDetector',      # Detect CAPTCHA challenges
    'CaptchaType',          # CAPTCHA type enum
    'detect_captcha',       # Convenience function
    
    # Distributed crawling (only available when crawlit[distributed] is installed)
    # Check _DISTRIBUTED_AVAILABLE before using these.
    'MessageQueue',
    'RabbitMQBackend',
    'KafkaBackend',
    'get_message_queue',
    'DistributedCrawler',
    'CrawlWorker',
    'CrawlCoordinator',
    'ConnectionPool',
    'DatabaseConnectionPool',
    'HTTPConnectionPool',
    '_DISTRIBUTED_AVAILABLE',
]