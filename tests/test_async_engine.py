"""Tests for crawlit.crawler.async_engine module (AsyncCrawler)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from crawlit.crawler.async_engine import AsyncCrawler


class TestAsyncCrawlerInit:
    def test_basic_initialization(self):
        crawler = AsyncCrawler("https://example.com")
        assert crawler.start_url == "https://example.com"
        assert crawler.max_depth == 3
        assert crawler.internal_only is True

    def test_custom_parameters(self):
        crawler = AsyncCrawler(
            "https://example.com",
            max_depth=5,
            internal_only=False,
            user_agent="async-bot/1.0",
            max_retries=5,
            timeout=30,
            delay=1.0,
            respect_robots=False,
        )
        assert crawler.max_depth == 5
        assert crawler.internal_only is False

    def test_invalid_scheme_raises(self):
        with pytest.raises(ValueError, match="http or https"):
            AsyncCrawler("ftp://example.com")

    def test_feature_flags(self):
        crawler = AsyncCrawler(
            "https://example.com",
            enable_image_extraction=True,
            enable_keyword_extraction=True,
            enable_table_extraction=True,
            enable_content_extraction=True,
        )
        assert crawler.image_extraction_enabled is True
        assert crawler.keyword_extraction_enabled is True
        assert crawler.table_extraction_enabled is True
        assert crawler.content_extraction_enabled is True

    def test_concurrency_setting(self):
        crawler = AsyncCrawler("https://example.com", max_concurrent_requests=10)
        assert crawler.max_concurrent_requests == 10

    def test_with_config(self):
        from crawlit.config import CrawlerConfig
        config = CrawlerConfig(max_depth=7)
        crawler = AsyncCrawler("https://example.com", config=config)
        assert crawler.max_depth == 7


class TestAsyncCrawlerValidation:
    @pytest.mark.asyncio
    async def test_should_crawl_internal(self):
        crawler = AsyncCrawler("https://example.com", internal_only=True, respect_robots=False)
        assert await crawler._should_crawl("https://example.com/page") is True

    @pytest.mark.asyncio
    async def test_should_crawl_external_blocked(self):
        crawler = AsyncCrawler("https://example.com", internal_only=True, respect_robots=False)
        assert await crawler._should_crawl("https://other.com/page") is False

    @pytest.mark.asyncio
    async def test_should_crawl_external_allowed(self):
        crawler = AsyncCrawler("https://example.com", internal_only=False, respect_robots=False)
        assert await crawler._should_crawl("https://other.com/page") is True


class TestAsyncCrawlerAttributes:
    def test_results_dict_initialized(self):
        crawler = AsyncCrawler("https://example.com")
        assert isinstance(crawler.results, dict)

    def test_visited_urls_initialized(self):
        crawler = AsyncCrawler("https://example.com")
        assert isinstance(crawler.visited_urls, set)
        assert len(crawler.visited_urls) == 0

    def test_domain_extracted(self):
        crawler = AsyncCrawler("https://example.com/path/page")
        assert crawler.base_domain == "example.com"

    def test_start_path_extracted(self):
        crawler = AsyncCrawler("https://example.com/docs/api", same_path_only=True)
        assert hasattr(crawler, "start_path")

    def test_retain_artifacts_flag(self):
        crawler = AsyncCrawler("https://example.com", retain_artifacts=False)
        assert crawler.retain_artifacts is False

    def test_with_budget_tracker(self):
        from crawlit.utils.budget_tracker import AsyncBudgetTracker
        bt = AsyncBudgetTracker(max_pages=100)
        crawler = AsyncCrawler("https://example.com", budget_tracker=bt)
        assert crawler.budget_tracker is bt

    def test_with_pipelines(self):
        mock_pipeline = MagicMock()
        crawler = AsyncCrawler("https://example.com", pipelines=[mock_pipeline])
        assert len(crawler.pipelines) >= 1

    def test_with_extractors(self):
        mock_extractor = MagicMock()
        crawler = AsyncCrawler("https://example.com", extractors=[mock_extractor])
        assert len(crawler.extractors) >= 1
