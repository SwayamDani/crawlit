"""Tests for crawlit.crawler.robots module."""

import time
import pytest
from unittest.mock import patch, MagicMock

from crawlit.crawler.robots import RobotsHandler, AsyncRobotsHandler, RobotsTxt


ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
ROBOTS_DENY_ADMIN = "User-agent: *\nDisallow: /admin/\nDisallow: /private/\n"
ROBOTS_WITH_CRAWL_DELAY = "User-agent: *\nCrawl-delay: 2.5\nDisallow: /secret/\n"
ROBOTS_WITH_SITEMAP = (
    "User-agent: *\nAllow: /\n"
    "Sitemap: https://example.com/sitemap.xml\n"
    "Sitemap: https://example.com/sitemap2.xml\n"
)


def _make_response(text, status=200, content_type="text/plain"):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.headers = {"Content-Type": content_type}
    return resp


class TestRobotsHandler:
    @patch("requests.get")
    def test_can_fetch_allowed(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_ALLOW_ALL)
        handler = RobotsHandler()
        assert handler.can_fetch("https://example.com/page", "crawlit/1.0") is True

    @patch("requests.get")
    def test_can_fetch_disallowed(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_DENY_ADMIN)
        handler = RobotsHandler()
        assert handler.can_fetch("https://example.com/admin/settings", "crawlit/1.0") is False

    @patch("requests.get")
    def test_skipped_paths_tracked(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_DENY_ADMIN)
        handler = RobotsHandler()
        handler.can_fetch("https://example.com/admin/x", "crawlit/1.0")
        paths = handler.get_skipped_paths()
        assert len(paths) == 1
        assert "admin" in paths[0]

    @patch("requests.get")
    def test_caching(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_ALLOW_ALL)
        handler = RobotsHandler()
        handler.can_fetch("https://example.com/page1", "bot")
        handler.can_fetch("https://example.com/page2", "bot")
        assert mock_get.call_count == 1

    @patch("requests.get")
    def test_cache_expiry(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_ALLOW_ALL)
        handler = RobotsHandler()
        handler.cache_expiry = 0
        handler.can_fetch("https://example.com/page1", "bot")
        time.sleep(0.01)
        handler.can_fetch("https://example.com/page2", "bot")
        assert mock_get.call_count == 2

    @patch("requests.get")
    def test_lru_eviction(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_ALLOW_ALL)
        handler = RobotsHandler()
        handler._MAX_CACHE_SIZE = 2

        handler.can_fetch("https://a.com/page", "bot")
        handler.can_fetch("https://b.com/page", "bot")
        handler.can_fetch("https://c.com/page", "bot")
        assert len(handler.parsers) <= 2

    @patch("requests.get")
    def test_crawl_delay(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_WITH_CRAWL_DELAY)
        handler = RobotsHandler()
        handler.get_robots_parser("https://example.com")
        delay = handler.get_crawl_delay("https://example.com/page", "*")
        assert delay == 2.5

    @patch("requests.get")
    def test_crawl_delay_no_directive(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_ALLOW_ALL)
        handler = RobotsHandler()
        handler.get_robots_parser("https://example.com")
        delay = handler.get_crawl_delay("https://example.com/page")
        assert delay is None

    @patch("requests.get")
    def test_fetch_failure_defaults_allow(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        handler = RobotsHandler()
        assert handler.can_fetch("https://example.com/page", "bot") is True

    @patch("requests.get")
    def test_non_200_defaults_allow(self, mock_get):
        mock_get.return_value = _make_response("", status=404)
        handler = RobotsHandler()
        assert handler.can_fetch("https://example.com/anything", "bot") is True


class TestAsyncRobotsHandler:
    @pytest.mark.asyncio
    async def test_can_fetch_allowed(self):
        handler = AsyncRobotsHandler()
        robots_txt = "User-agent: *\nAllow: /\n"

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.text = MagicMock(return_value=robots_txt)

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_cm = MagicMock()
            mock_cm.__aenter__ = MagicMock(return_value=mock_resp)
            mock_cm.__aexit__ = MagicMock(return_value=None)
            mock_session.get.return_value = mock_cm
            mock_session.__aenter__ = MagicMock(return_value=mock_session)
            mock_session.__aexit__ = MagicMock(return_value=None)
            mock_session_cls.return_value = mock_session

            result = await handler.can_fetch("https://example.com/page", "bot")
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        handler = AsyncRobotsHandler()
        handler.parsers["example.com"] = MagicMock()
        handler.last_fetch_time["example.com"] = time.time()
        handler.clear_cache()
        assert len(handler.parsers) == 0
        assert len(handler.last_fetch_time) == 0

    @pytest.mark.asyncio
    async def test_get_skipped_paths(self):
        handler = AsyncRobotsHandler()
        handler.skipped_paths = ["https://example.com/admin"]
        result = await handler.get_skipped_paths()
        assert result == ["https://example.com/admin"]

    def test_cache_expired_no_entry(self):
        handler = AsyncRobotsHandler()
        assert handler._is_cache_expired("unknown.com") is True

    def test_cache_not_expired(self):
        handler = AsyncRobotsHandler()
        handler.last_fetch_time["example.com"] = time.time()
        assert handler._is_cache_expired("example.com") is False

    def test_cache_expired(self):
        handler = AsyncRobotsHandler()
        handler.last_fetch_time["example.com"] = time.time() - 7200
        handler.cache_expiry = 3600
        assert handler._is_cache_expired("example.com") is True


class TestRobotsTxt:
    @patch("requests.get")
    def test_can_fetch(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_DENY_ADMIN)
        rt = RobotsTxt("https://example.com")
        assert rt.can_fetch("/page") is True
        assert rt.can_fetch("/admin/settings") is False

    @patch("requests.get")
    def test_get_sitemaps(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_WITH_SITEMAP)
        rt = RobotsTxt("https://example.com")
        sitemaps = rt.get_sitemaps()
        assert len(sitemaps) == 2
        assert "https://example.com/sitemap.xml" in sitemaps
        assert "https://example.com/sitemap2.xml" in sitemaps

    @patch("requests.get")
    def test_get_sitemaps_none(self, mock_get):
        mock_get.return_value = _make_response(ROBOTS_ALLOW_ALL)
        rt = RobotsTxt("https://example.com")
        sitemaps = rt.get_sitemaps()
        assert sitemaps == []
