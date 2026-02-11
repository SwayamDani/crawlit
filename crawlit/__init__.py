#!/usr/bin/env python3
"""
crawlit - Modular, Ethical Python Web Crawler

A flexible web crawler library that can be used programmatically or via CLI.
"""

__version__ = '0.2.0'

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
    ContentDeduplicator,
    LoggingConfig,
    configure_logging,
    get_logger,
    log_with_context,
    CrawlitError,
    FetchError,
    handle_fetch_error
)

# CLI functionality (but not executed on import)
def cli_main():
    """Entry point for the CLI interface when installed with [cli] option"""
    from crawlit.crawlit import main
    return main()

__all__ = [
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
    'ContentDeduplicator',  # Content-based deduplication
    'LoggingConfig',     # Enhanced logging configuration
    'configure_logging', # Convenience function for logging setup
    'get_logger',        # Get logger instance
    'log_with_context',  # Log with additional context
    'CrawlitError',      # Base exception
    'FetchError',        # Fetch exception
    'handle_fetch_error',  # Error handler
]