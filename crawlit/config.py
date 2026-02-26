#!/usr/bin/env python3
"""
config.py - Composable crawl configuration.

Replaces the long keyword-argument list on Crawler / AsyncCrawler with a
typed, structured config object while remaining fully backwards-compatible:
all existing positional / keyword arguments still work unchanged.

Usage
-----
    from crawlit.config import CrawlerConfig, FetchConfig, RateLimitConfig, OutputConfig

    cfg = CrawlerConfig(
        start_url="https://example.com",
        max_depth=5,
        fetch=FetchConfig(timeout=30, user_agent="MyBot/2.0"),
        rate_limit=RateLimitConfig(delay=1.0),
        output=OutputConfig(
            write_jsonl=True,
            jsonl_path="out/artifacts.jsonl",
            write_blobs=True,
            blobs_dir="out/blobs",
        ),
        enable_content_extraction=True,
        enable_pdf_extraction=True,
    )
    crawler = Crawler(config=cfg)
    crawler.crawl()
"""

import dataclasses
from typing import List, Optional


@dataclasses.dataclass
class FetchConfig:
    """HTTP fetch / rendering parameters."""

    user_agent: str = "crawlit/1.0"
    max_retries: int = 3
    timeout: int = 10
    verify_ssl: bool = True
    proxy: Optional[str] = None
    # JavaScript rendering (requires Playwright)
    use_js_rendering: bool = False
    js_wait_for_selector: Optional[str] = None
    js_wait_for_timeout: Optional[int] = None
    js_browser_type: str = "chromium"


@dataclasses.dataclass
class RateLimitConfig:
    """Rate-limiting parameters."""

    delay: float = 0.1
    use_per_domain_delay: bool = True
    respect_robots_crawl_delay: bool = True


@dataclasses.dataclass
class OutputConfig:
    """Output and persistence parameters."""

    # HTML content storage
    store_html_content: bool = True
    enable_disk_storage: bool = False
    storage_dir: Optional[str] = None

    # JSONL artifact stream  (one artifact per line)
    write_jsonl: bool = False
    jsonl_path: Optional[str] = None

    # Blob store  (raw HTML / PDF files by content-hash)
    write_blobs: bool = False
    blobs_dir: Optional[str] = None

    # Navigation edge stream  (from_url → to_url)
    write_edges: bool = False
    edges_path: Optional[str] = None


@dataclasses.dataclass
class CrawlerConfig:
    """
    Top-level crawl configuration.

    Compose from sub-configs for fine-grained control::

        cfg = CrawlerConfig(
            start_url="https://example.com",
            fetch=FetchConfig(timeout=30),
            rate_limit=RateLimitConfig(delay=0.5),
            output=OutputConfig(
                write_jsonl=True,
                jsonl_path="out/artifacts.jsonl",
            ),
        )
        crawler = Crawler(config=cfg)

    Any field left at its default will be overridden by the corresponding
    explicit keyword argument if both are supplied to Crawler().
    """

    start_url: str = ""

    # Crawl scope
    max_depth: int = 3
    internal_only: bool = True
    same_path_only: bool = False
    respect_robots: bool = True
    max_queue_size: Optional[int] = None

    # Concurrency
    max_workers: Optional[int] = 1           # sync: ThreadPoolExecutor workers
    max_concurrent_requests: int = 5         # async: semaphore size

    # Sub-configs
    fetch: FetchConfig = dataclasses.field(default_factory=FetchConfig)
    rate_limit: RateLimitConfig = dataclasses.field(default_factory=RateLimitConfig)
    output: OutputConfig = dataclasses.field(default_factory=OutputConfig)

    # Extraction feature flags
    enable_image_extraction: bool = False
    enable_keyword_extraction: bool = False
    enable_table_extraction: bool = False
    enable_content_extraction: bool = False
    enable_content_deduplication: bool = False
    enable_incremental: bool = False
    enable_pdf_extraction: bool = False
    enable_js_embedded_data: bool = False
    enable_dom_features: bool = False

    # Sitemap support
    use_sitemap: bool = False
    sitemap_urls: List[str] = dataclasses.field(default_factory=list)

    # Budget limits
    max_pages: Optional[int] = None
    max_bytes: Optional[int] = None
    max_time_seconds: Optional[float] = None
