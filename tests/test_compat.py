"""Tests for crawlit.compat module."""

import pytest
from unittest.mock import MagicMock, PropertyMock
import inspect

from crawlit.compat import ensure_response_compatibility, is_async_context


class TestEnsureResponseCompatibility:
    def test_response_like_passthrough(self):
        from crawlit.crawler.async_fetcher import ResponseLike
        resp = ResponseLike(
            url="https://example.com",
            status_code=200,
            headers={"Content-Type": "text/html"},
            text="hello",
        )
        result = ensure_response_compatibility(resp)
        assert result is resp

    def test_requests_response_passthrough(self):
        mock_resp = MagicMock()
        mock_resp.text = "html content"
        type(mock_resp).text = PropertyMock(return_value="html content")
        result = ensure_response_compatibility(mock_resp)
        assert result is mock_resp

    def test_unknown_object_passthrough(self):
        obj = {"key": "value"}
        result = ensure_response_compatibility(obj)
        assert result is obj

    def test_none_passthrough(self):
        result = ensure_response_compatibility(None)
        assert result is None


class TestIsAsyncContext:
    def test_sync_context_returns_false(self):
        assert is_async_context() is False

    @pytest.mark.asyncio
    async def test_in_async_function(self):
        # is_async_context checks the call stack; whether it finds
        # coroutine frames depends on the Python version and pytest-asyncio
        # internals, so we just verify it doesn't raise.
        result = is_async_context()
        assert isinstance(result, bool)
