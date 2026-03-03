"""Tests for crawlit.crawler.async_fetcher module."""

import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from crawlit.crawler.async_fetcher import ResponseLike, _detect_charset_from_bytes


class TestResponseLike:
    def test_text_mode_constructor(self):
        r = ResponseLike("https://example.com", 200, {"Content-Type": "text/html"}, "hello")
        assert r.url == "https://example.com"
        assert r.status_code == 200
        assert r.ok is True
        assert r.content == b"hello"
        assert r.is_binary is False

    def test_binary_mode_constructor(self):
        data = b"\x89PNG binary data"
        r = ResponseLike("https://example.com/img.png", 200, {}, data, is_binary=True)
        assert r.content == data
        assert r._text is None
        assert r.is_binary is True

    def test_status_property(self):
        r = ResponseLike("https://example.com", 404, {}, "not found")
        assert r.status == 404
        assert r.status_code == 404

    def test_ok_for_success_codes(self):
        for code in [200, 201, 204, 299]:
            r = ResponseLike("https://example.com", code, {}, "")
            assert r.ok is True, f"Expected ok=True for status {code}"

    def test_ok_for_error_codes(self):
        for code in [301, 400, 404, 500]:
            r = ResponseLike("https://example.com", code, {}, "")
            assert r.ok is False, f"Expected ok=False for status {code}"

    @pytest.mark.asyncio
    async def test_text_async_method(self):
        r = ResponseLike("https://example.com", 200, {}, "hello world")
        result = await r.text()
        assert result == "hello world"

    def test_text_content_property(self):
        r = ResponseLike("https://example.com", 200, {}, "hello world")
        assert r.text_content == "hello world"

    def test_text_sync_method(self):
        r = ResponseLike("https://example.com", 200, {}, "hello world")
        assert r.text_sync() == "hello world"

    def test_json_method(self):
        data = {"key": "value", "num": 42}
        r = ResponseLike("https://example.com", 200, {}, json.dumps(data))
        assert r.json() == data

    def test_json_method_none_text(self):
        r = ResponseLike("https://example.com", 200, {}, None)
        assert r.json() is None

    def test_raise_for_status_success(self):
        r = ResponseLike("https://example.com", 200, {}, "ok")
        r.raise_for_status()

    def test_raise_for_status_error(self):
        r = ResponseLike("https://example.com", 500, {}, "error")
        with pytest.raises(Exception):
            r.raise_for_status()

    def test_raise_for_status_404(self):
        r = ResponseLike("https://example.com", 404, {}, "not found")
        with pytest.raises(Exception):
            r.raise_for_status()

    def test_none_text_content_encoding(self):
        r = ResponseLike("https://example.com", 200, {}, None)
        assert r.content is None

    @pytest.mark.asyncio
    async def test_text_binary_returns_none(self):
        r = ResponseLike("https://example.com", 200, {}, b"binary", is_binary=True)
        result = await r.text()
        assert result is None


class TestDetectCharsetFromBytes:
    def test_utf8_meta_charset(self):
        html = b'<html><head><meta charset="utf-8"></head></html>'
        assert _detect_charset_from_bytes(html) == "utf-8"

    def test_iso_charset(self):
        html = b'<meta charset="iso-8859-1">'
        assert _detect_charset_from_bytes(html) == "iso-8859-1"

    def test_content_type_meta(self):
        html = b'<meta http-equiv="content-type" content="text/html; charset=windows-1252">'
        assert _detect_charset_from_bytes(html) == "windows-1252"

    def test_no_charset(self):
        html = b'<html><body>Hello</body></html>'
        assert _detect_charset_from_bytes(html) is None

    def test_empty_bytes(self):
        assert _detect_charset_from_bytes(b"") is None


class TestAsyncFetchPage:
    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        from crawlit.crawler.async_fetcher import async_fetch_page
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.text = AsyncMock(return_value="<html>Hello</html>")

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_cm)

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            success, content, status = await async_fetch_page(
                "https://example.com", "test-agent", max_retries=0
            )
        assert success is True
        assert content == "<html>Hello</html>"
        assert status == 200

    @pytest.mark.asyncio
    async def test_non_html_content_type(self):
        from crawlit.crawler.async_fetcher import async_fetch_page
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = AsyncMock(return_value='{"key": "val"}')

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_cm)

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            success, content, status = await async_fetch_page(
                "https://example.com/data", "test-agent", max_retries=0
            )
        assert success is False
        assert content is None

    @pytest.mark.asyncio
    async def test_404_not_retried(self):
        from crawlit.crawler.async_fetcher import async_fetch_page
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.ok = False
        mock_response.headers = {"Content-Type": "text/html"}

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_cm)

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            success, content, status = await async_fetch_page(
                "https://example.com/missing", "test-agent", max_retries=3
            )
        assert success is False
        assert status == 404
        assert mock_session.get.call_count == 1
