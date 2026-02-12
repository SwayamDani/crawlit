"""
Utility modules for crawlit
"""

from crawlit.utils.session_manager import SessionManager
from crawlit.utils.url_filter import URLFilter
from crawlit.utils.progress import ProgressTracker, create_progress_callback
from crawlit.utils.queue_manager import QueueManager
from crawlit.utils.cache import PageCache, CrawlResume
from crawlit.utils.storage import StorageManager
from crawlit.utils.sitemap import SitemapParser, get_sitemaps_from_robots, get_sitemaps_from_robots_async
from crawlit.utils.rate_limiter import RateLimiter, AsyncRateLimiter, DynamicRateLimiter, AsyncDynamicRateLimiter
from crawlit.utils.deduplication import ContentDeduplicator
from crawlit.utils.budget_tracker import BudgetTracker, AsyncBudgetTracker, BudgetLimits
from crawlit.utils.priority_queue import (
    URLPriorityQueue,
    AsyncURLPriorityQueue,
    PriorityStrategy,
    BreadthFirstStrategy,
    DepthFirstStrategy,
    SitemapPriorityStrategy,
    URLPatternStrategy,
    CompositeStrategy,
    get_strategy
)
from crawlit.utils.cookie_persistence import (
    CookieJar,
    save_cookies,
    load_cookies
)
from crawlit.utils.download_manager import DownloadManager
from crawlit.utils.incremental import IncrementalCrawler
from crawlit.utils.scheduler import CrawlScheduler, ScheduledCrawl, is_croniter_available
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
from crawlit.utils.auth import (
    AuthManager,
    AuthConfig,
    create_basic_auth,
    create_bearer_auth,
    create_api_key_auth,
    create_custom_auth,
    create_digest_auth,
    get_auth_tuple
)
from crawlit.utils.env_loader import (
    EnvLoader,
    ConfigLoader,
    load_env,
    getenv
)

__all__ = [
    'SessionManager',
    'URLFilter',
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
    'DynamicRateLimiter',
    'AsyncDynamicRateLimiter',
    'ContentDeduplicator',
    'BudgetTracker',
    'AsyncBudgetTracker',
    'BudgetLimits',
    'URLPriorityQueue',
    'AsyncURLPriorityQueue',
    'PriorityStrategy',
    'BreadthFirstStrategy',
    'DepthFirstStrategy',
    'SitemapPriorityStrategy',
    'URLPatternStrategy',
    'CompositeStrategy',
    'get_strategy',
    'CookieJar',
    'save_cookies',
    'load_cookies',
    'DownloadManager',
    'IncrementalCrawler',
    'CrawlScheduler',
    'ScheduledCrawl',
    'is_croniter_available',
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
    # Authentication
    'AuthManager',
    'AuthConfig',
    'create_basic_auth',
    'create_bearer_auth',
    'create_api_key_auth',
    'create_custom_auth',
    'create_digest_auth',
    'get_auth_tuple',
    # Environment/Config
    'EnvLoader',
    'ConfigLoader',
    'load_env',
    'getenv',
]

