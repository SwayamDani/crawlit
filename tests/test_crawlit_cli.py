"""Tests for crawlit.crawlit module (CLI entry point)."""

import sys
import pytest
from unittest.mock import patch


class TestCrawlitImports:
    def test_main_module_imports(self):
        import crawlit.crawlit

    def test_crawler_class_available(self):
        from crawlit.crawler.engine import Crawler
        assert Crawler is not None

    def test_async_crawler_class_available(self):
        from crawlit.crawler.async_engine import AsyncCrawler
        assert AsyncCrawler is not None


class TestCLIParsing:
    def _parse(self, args_list):
        from crawlit.crawlit import parse_args
        with patch.object(sys, "argv", ["crawlit"] + args_list):
            return parse_args()

    def test_parse_args_minimal(self):
        args = self._parse(["--url", "https://example.com"])
        assert args.url == "https://example.com"

    def test_parse_args_depth(self):
        args = self._parse(["--url", "https://example.com", "--depth", "5"])
        assert args.depth == 5

    def test_parse_args_output(self):
        args = self._parse(["--url", "https://example.com", "--output", "results.json"])
        assert args.output == "results.json"

    def test_parse_args_output_format(self):
        args = self._parse(["--url", "https://example.com", "--output-format", "csv"])
        assert args.output_format == "csv"

    def test_parse_args_allow_external(self):
        args = self._parse(["--url", "https://example.com", "--allow-external"])
        assert args.allow_external is True

    def test_parse_args_user_agent(self):
        args = self._parse(["--url", "https://example.com", "--user-agent", "my-bot/1.0"])
        assert args.user_agent == "my-bot/1.0"

    def test_parse_args_ignore_robots(self):
        args = self._parse(["--url", "https://example.com", "--ignore-robots"])
        assert args.ignore_robots is True

    def test_parse_args_image_extraction(self):
        args = self._parse(["--url", "https://example.com", "--extract-images"])
        assert args.extract_images is True

    def test_parse_args_table_extraction(self):
        args = self._parse(["--url", "https://example.com", "--extract-tables"])
        assert args.extract_tables is True

    def test_parse_args_keyword_extraction(self):
        args = self._parse(["--url", "https://example.com", "--extract-keywords"])
        assert args.extract_keywords is True

    def test_parse_args_content_extraction(self):
        args = self._parse(["--url", "https://example.com", "--extract-content"])
        assert args.extract_content is True

    def test_parse_args_async(self):
        args = self._parse(["--url", "https://example.com", "--async"])
        assert getattr(args, "async") is True

    def test_parse_args_concurrency(self):
        args = self._parse(["--url", "https://example.com", "--concurrency", "10"])
        assert args.concurrency == 10

    def test_parse_args_delay(self):
        args = self._parse(["--url", "https://example.com", "--delay", "2.0"])
        assert args.delay == 2.0

    def test_parse_args_timeout(self):
        args = self._parse(["--url", "https://example.com", "--timeout", "30"])
        assert args.timeout == 30

    def test_parse_args_verbose(self):
        args = self._parse(["--url", "https://example.com", "--verbose"])
        assert args.verbose is True

    def test_parse_args_summary(self):
        args = self._parse(["--url", "https://example.com", "--summary"])
        assert args.summary is True

    def test_parse_args_js_rendering(self):
        args = self._parse(["--url", "https://example.com", "--use-js"])
        assert args.use_js is True

    def test_parse_args_proxy(self):
        args = self._parse(["--url", "https://example.com", "--proxy", "http://proxy:8080"])
        assert args.proxy == "http://proxy:8080"

    def test_parse_args_max_pages(self):
        args = self._parse(["--url", "https://example.com", "--max-pages", "100"])
        assert args.max_pages == 100

    def test_parse_args_use_cache(self):
        args = self._parse(["--url", "https://example.com", "--use-cache"])
        assert args.use_cache is True

    def test_parse_args_same_path_only(self):
        args = self._parse(["--url", "https://example.com", "--same-path-only"])
        assert args.same_path_only is True

    def test_parse_args_use_sitemap(self):
        args = self._parse(["--url", "https://example.com", "--use-sitemap"])
        assert args.use_sitemap is True

    def test_parse_args_incremental(self):
        args = self._parse(["--url", "https://example.com", "--incremental"])
        assert args.incremental is True

    def test_parse_args_deduplication(self):
        args = self._parse(["--url", "https://example.com", "--enable-deduplication"])
        assert args.enable_deduplication is True

    def test_parse_args_shorthand(self):
        args = self._parse(["-u", "https://example.com"])
        assert args.url == "https://example.com"
