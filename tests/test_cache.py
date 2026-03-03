"""Tests for crawlit.utils.cache module."""

import time
import pytest
from crawlit.utils.cache import PageCache


class TestPageCache:
    def test_init_memory_only(self):
        cache = PageCache()
        assert cache is not None
        assert cache.enable_disk_cache is False

    def test_init_with_disk(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cache = PageCache(cache_dir=str(cache_dir), enable_disk_cache=True)
        assert cache_dir.exists()

    def test_set_and_get(self, tmp_path):
        cache = PageCache(ttl=3600)
        cache.set(
            "https://example.com",
            response_data={"title": "Test"},
            status_code=200,
            headers={"Content-Type": "text/html"},
            content="<html>Hello</html>",
        )
        result = cache.get("https://example.com")
        assert result is not None
        assert result["status_code"] == 200
        assert result["content"] == "<html>Hello</html>"

    def test_get_nonexistent(self):
        cache = PageCache()
        result = cache.get("https://missing.com")
        assert result is None

    def test_cache_expiry(self):
        cache = PageCache(ttl=0)
        cache.set(
            "https://example.com",
            response_data={},
            status_code=200,
            headers={},
        )
        time.sleep(0.01)
        result = cache.get("https://example.com")
        assert result is None

    def test_clear(self):
        cache = PageCache()
        cache.set("https://example.com", response_data={}, status_code=200, headers={})
        cache.clear()
        result = cache.get("https://example.com")
        assert result is None

    def test_remove(self):
        cache = PageCache()
        cache.set("https://example.com", response_data={}, status_code=200, headers={})
        cache.remove("https://example.com")
        result = cache.get("https://example.com")
        assert result is None

    def test_remove_nonexistent(self):
        cache = PageCache()
        cache.remove("https://missing.com")

    def test_get_stats(self):
        cache = PageCache()
        cache.set("https://example.com", response_data={}, status_code=200, headers={})
        stats = cache.get_stats()
        assert isinstance(stats, dict)
