"""
Utility modules for crawlit
"""

from crawlit.utils.session_manager import SessionManager
from crawlit.utils.url_filter import URLFilter, validate_url
from crawlit.utils.progress import ProgressTracker, create_progress_callback
from crawlit.utils.queue_manager import QueueManager
from crawlit.utils.cache import PageCache, CrawlResume
from crawlit.utils.storage import StorageManager
from crawlit.utils.sitemap import SitemapParser, get_sitemaps_from_robots, get_sitemaps_from_robots_async
from crawlit.utils.rate_limiter import RateLimiter, AsyncRateLimiter
from crawlit.utils.deduplication import ContentDeduplicator
from crawlit.utils.logging_config import (
    LoggingConfig,
    configure_logging,
    get_logger,
    log_with_context,
    JSONFormatter,
    ContextualFormatter
)
from crawlit.utils.errors import (
    CrawlitError,
    FetchError,
    RobotsError,
    ParseError,
    ExtractionError,
    handle_fetch_error
)

__all__ = [
    'SessionManager',
    'URLFilter',
    'validate_url',
    'ProgressTracker',
    'create_progress_callback',
    'QueueManager',
    'PageCache',
    'CrawlResume',
    'StorageManager',
    'SitemapParser',
    'get_sitemaps_from_robots',
    'get_sitemaps_from_robots_async',
    'RateLimiter',
    'AsyncRateLimiter',
    'ContentDeduplicator',
    'LoggingConfig',
    'configure_logging',
    'get_logger',
    'log_with_context',
    'JSONFormatter',
    'ContextualFormatter',
    'CrawlitError',
    'FetchError',
    'RobotsError',
    'ParseError',
    'ExtractionError',
    'handle_fetch_error',
]

