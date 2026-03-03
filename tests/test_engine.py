"""Tests for crawlit.crawler.engine module (sync Crawler)."""

import pytest
from unittest.mock import patch, MagicMock
from crawlit.crawler.engine import Crawler


class TestCrawlerInit:
    def test_basic_initialization(self):
        crawler = Crawler("https://example.com")
        assert crawler.start_url == "https://example.com"
        assert crawler.max_depth == 3
        assert crawler.internal_only is True

    def test_custom_parameters(self):
        crawler = Crawler(
            "https://example.com",
            max_depth=5,
            internal_only=False,
            user_agent="custom-bot/2.0",
            max_retries=5,
            timeout=30,
            delay=1.0,
            respect_robots=False,
        )
        assert crawler.max_depth == 5
        assert crawler.internal_only is False
        assert crawler.user_agent == "custom-bot/2.0"

    def test_invalid_scheme_raises(self):
        with pytest.raises(ValueError, match="http or https"):
            Crawler("ftp://example.com")

    def test_invalid_scheme_file(self):
        with pytest.raises(ValueError):
            Crawler("file:///tmp/test.html")

    def test_feature_flags(self):
        crawler = Crawler(
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

    def test_js_rendering_flags(self):
        crawler = Crawler(
            "https://example.com",
            use_js_rendering=False,
            js_browser_type="firefox",
        )
        assert crawler.use_js_rendering is False
        assert crawler.js_browser_type == "firefox"

    def test_same_path_only(self):
        crawler = Crawler("https://example.com/docs/api", same_path_only=True)
        assert crawler.same_path_only is True

    def test_with_config_object(self):
        from crawlit.config import CrawlerConfig, FetchConfig
        config = CrawlerConfig(
            max_depth=10,
            fetch=FetchConfig(timeout=60, max_retries=5),
        )
        crawler = Crawler("https://example.com", config=config)
        assert crawler.max_depth == 10

    def test_visited_urls_initially_empty(self):
        crawler = Crawler("https://example.com")
        assert len(crawler.visited_urls) == 0

    def test_results_initially_empty(self):
        crawler = Crawler("https://example.com")
        assert crawler.results is not None


class TestCrawlerDomainCheck:
    def test_internal_url(self):
        crawler = Crawler("https://example.com", internal_only=True, respect_robots=False)
        assert crawler.is_valid_url("https://example.com/page") is True

    def test_external_url_blocked(self):
        crawler = Crawler("https://example.com", internal_only=True, respect_robots=False)
        assert crawler.is_valid_url("https://other.com/page") is False

    def test_external_url_allowed(self):
        crawler = Crawler("https://example.com", internal_only=False, respect_robots=False)
        assert crawler.is_valid_url("https://other.com/page") is True

    def test_same_path_filtering(self):
        crawler = Crawler(
            "https://example.com/docs/api",
            same_path_only=True,
            internal_only=True,
            respect_robots=False,
        )
        assert crawler.is_valid_url("https://example.com/docs/api/v1") is True
        assert crawler.is_valid_url("https://example.com/blog/post") is False


class TestCrawlerCrawl:
    @patch("crawlit.crawler.engine.fetch_page")
    def test_single_page_crawl(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><p>Hello</p></body></html>"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.url = "https://example.com"
        mock_resp.content = b"<html><body><p>Hello</p></body></html>"
        mock_fetch.return_value = (True, mock_resp, 200)

        crawler = Crawler(
            "https://example.com",
            max_depth=0,
            respect_robots=False,
        )
        crawler.crawl()
        assert len(crawler.visited_urls) >= 1
        assert len(crawler.results) >= 1

    @patch("crawlit.crawler.engine.fetch_page")
    def test_crawl_with_links(self, mock_fetch):
        html_with_links = """
        <html><body>
            <a href="/page2">Link</a>
            <a href="/page3">Link 2</a>
        </body></html>
        """
        html_simple = "<html><body>Simple</body></html>"

        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            resp = MagicMock()
            resp.status_code = 200
            resp.headers = {"Content-Type": "text/html"}
            if call_count["n"] == 1:
                resp.text = html_with_links
                resp.url = "https://example.com"
                resp.content = html_with_links.encode()
            else:
                resp.text = html_simple
                resp.url = f"https://example.com/page{call_count['n']}"
                resp.content = html_simple.encode()
            return (True, resp, 200)

        mock_fetch.side_effect = side_effect

        crawler = Crawler(
            "https://example.com",
            max_depth=1,
            respect_robots=False,
        )
        crawler.crawl()
        assert len(crawler.visited_urls) >= 1

    @patch("crawlit.crawler.engine.fetch_page")
    def test_crawl_handles_fetch_failure(self, mock_fetch):
        mock_fetch.return_value = (False, "Connection error", 0)

        crawler = Crawler(
            "https://example.com",
            max_depth=0,
            respect_robots=False,
        )
        crawler.crawl()
        assert len(crawler.visited_urls) >= 1

    @patch("crawlit.crawler.engine.fetch_page")
    def test_crawl_with_extractors(self, mock_fetch):
        html_content = """<html><head><title>Test</title></head>
        <body>
            <h1>Heading</h1>
            <img src="/img.png" alt="test">
            <table><tr><td>A</td><td>B</td></tr></table>
        </body></html>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_content
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.url = "https://example.com"
        mock_resp.content = html_content.encode()
        mock_fetch.return_value = (True, mock_resp, 200)

        crawler = Crawler(
            "https://example.com",
            max_depth=0,
            respect_robots=False,
            enable_image_extraction=True,
            enable_keyword_extraction=True,
            enable_table_extraction=True,
            enable_content_extraction=True,
        )
        crawler.crawl()
        assert len(crawler.visited_urls) >= 1
