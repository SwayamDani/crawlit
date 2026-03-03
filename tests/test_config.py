"""Tests for crawlit.config module."""

import dataclasses
import pytest

from crawlit.config import FetchConfig, RateLimitConfig, OutputConfig, CrawlerConfig


class TestFetchConfig:
    def test_defaults(self):
        cfg = FetchConfig()
        assert cfg.user_agent == "crawlit/1.0"
        assert cfg.max_retries == 3
        assert cfg.timeout == 10
        assert cfg.verify_ssl is True
        assert cfg.proxy is None
        assert cfg.use_js_rendering is False
        assert cfg.js_wait_for_selector is None
        assert cfg.js_wait_for_timeout is None
        assert cfg.js_browser_type == "chromium"

    def test_custom_values(self):
        cfg = FetchConfig(
            user_agent="Bot/2.0",
            max_retries=5,
            timeout=30,
            verify_ssl=False,
            proxy="http://proxy:8080",
            use_js_rendering=True,
            js_browser_type="firefox",
        )
        assert cfg.user_agent == "Bot/2.0"
        assert cfg.max_retries == 5
        assert cfg.timeout == 30
        assert cfg.verify_ssl is False
        assert cfg.proxy == "http://proxy:8080"
        assert cfg.use_js_rendering is True
        assert cfg.js_browser_type == "firefox"

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(FetchConfig)
        assert dataclasses.is_dataclass(FetchConfig())

    def test_equality(self):
        a = FetchConfig(timeout=30)
        b = FetchConfig(timeout=30)
        assert a == b

    def test_replace(self):
        original = FetchConfig()
        modified = dataclasses.replace(original, timeout=60)
        assert modified.timeout == 60
        assert original.timeout == 10


class TestRateLimitConfig:
    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.delay == 0.1
        assert cfg.use_per_domain_delay is True
        assert cfg.respect_robots_crawl_delay is True

    def test_custom_values(self):
        cfg = RateLimitConfig(delay=2.0, use_per_domain_delay=False, respect_robots_crawl_delay=False)
        assert cfg.delay == 2.0
        assert cfg.use_per_domain_delay is False
        assert cfg.respect_robots_crawl_delay is False


class TestOutputConfig:
    def test_defaults(self):
        cfg = OutputConfig()
        assert cfg.store_html_content is True
        assert cfg.enable_disk_storage is False
        assert cfg.storage_dir is None
        assert cfg.write_jsonl is False
        assert cfg.jsonl_path is None
        assert cfg.write_blobs is False
        assert cfg.blobs_dir is None
        assert cfg.write_edges is False
        assert cfg.edges_path is None

    def test_jsonl_enabled(self):
        cfg = OutputConfig(write_jsonl=True, jsonl_path="/tmp/artifacts.jsonl")
        assert cfg.write_jsonl is True
        assert cfg.jsonl_path == "/tmp/artifacts.jsonl"

    def test_blob_store(self):
        cfg = OutputConfig(write_blobs=True, blobs_dir="/tmp/blobs")
        assert cfg.write_blobs is True
        assert cfg.blobs_dir == "/tmp/blobs"


class TestCrawlerConfig:
    def test_defaults(self):
        cfg = CrawlerConfig()
        assert cfg.start_url == ""
        assert cfg.max_depth == 3
        assert cfg.internal_only is True
        assert cfg.same_path_only is False
        assert cfg.respect_robots is True
        assert cfg.max_queue_size is None
        assert cfg.max_workers == 1
        assert cfg.max_concurrent_requests == 5
        assert isinstance(cfg.fetch, FetchConfig)
        assert isinstance(cfg.rate_limit, RateLimitConfig)
        assert isinstance(cfg.output, OutputConfig)
        assert cfg.enable_image_extraction is False
        assert cfg.enable_keyword_extraction is False
        assert cfg.enable_table_extraction is False
        assert cfg.enable_content_extraction is False
        assert cfg.enable_content_deduplication is False
        assert cfg.enable_incremental is False
        assert cfg.enable_pdf_extraction is False
        assert cfg.enable_js_embedded_data is False
        assert cfg.enable_dom_features is False
        assert cfg.use_sitemap is False
        assert cfg.sitemap_urls == []
        assert cfg.max_pages is None
        assert cfg.max_bytes is None
        assert cfg.max_time_seconds is None

    def test_composition(self):
        cfg = CrawlerConfig(
            start_url="https://example.com",
            max_depth=5,
            fetch=FetchConfig(timeout=30, user_agent="TestBot/1.0"),
            rate_limit=RateLimitConfig(delay=0.5),
            output=OutputConfig(write_jsonl=True),
        )
        assert cfg.start_url == "https://example.com"
        assert cfg.max_depth == 5
        assert cfg.fetch.timeout == 30
        assert cfg.fetch.user_agent == "TestBot/1.0"
        assert cfg.rate_limit.delay == 0.5
        assert cfg.output.write_jsonl is True

    def test_feature_flags(self):
        cfg = CrawlerConfig(
            enable_image_extraction=True,
            enable_keyword_extraction=True,
            enable_table_extraction=True,
            enable_content_extraction=True,
            enable_pdf_extraction=True,
        )
        assert cfg.enable_image_extraction is True
        assert cfg.enable_keyword_extraction is True
        assert cfg.enable_table_extraction is True
        assert cfg.enable_content_extraction is True
        assert cfg.enable_pdf_extraction is True

    def test_budget_limits(self):
        cfg = CrawlerConfig(
            max_pages=100,
            max_bytes=1_000_000,
            max_time_seconds=300.0,
        )
        assert cfg.max_pages == 100
        assert cfg.max_bytes == 1_000_000
        assert cfg.max_time_seconds == 300.0

    def test_sitemap(self):
        cfg = CrawlerConfig(
            use_sitemap=True,
            sitemap_urls=["https://example.com/sitemap.xml"],
        )
        assert cfg.use_sitemap is True
        assert cfg.sitemap_urls == ["https://example.com/sitemap.xml"]

    def test_independent_sub_configs(self):
        cfg1 = CrawlerConfig()
        cfg2 = CrawlerConfig()
        cfg1.fetch.timeout = 99
        assert cfg2.fetch.timeout == 10

    def test_asdict(self):
        cfg = CrawlerConfig(start_url="https://example.com")
        d = dataclasses.asdict(cfg)
        assert d["start_url"] == "https://example.com"
        assert isinstance(d["fetch"], dict)
        assert d["fetch"]["user_agent"] == "crawlit/1.0"
