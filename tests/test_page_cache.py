#!/usr/bin/env python3
"""
test_page_cache.py - Tests for PageCache and CrawlResume
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from crawlit.utils.cache import PageCache, CrawlResume


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────

def _make_entry(url="https://example.com", status=200, content="<html/>"):
    return dict(
        url=url,
        status_code=status,
        headers={"Content-Type": "text/html"},
        response_data={"status": status},
        content=content,
    )


# ──────────────────────────────────────────────────────────
# PageCache – memory only
# ──────────────────────────────────────────────────────────

class TestPageCacheMemory:
    def test_miss_on_empty_cache(self):
        cache = PageCache()
        assert cache.get("https://example.com") is None

    def test_set_and_get(self):
        cache = PageCache()
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"], e["content"])
        result = cache.get("https://example.com")
        assert result is not None
        assert result["status_code"] == 200
        assert result["content"] == "<html/>"

    def test_ttl_not_expired(self):
        cache = PageCache(ttl=3600)
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"])
        assert cache.get("https://example.com") is not None

    def test_ttl_expired(self):
        cache = PageCache(ttl=1)
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"])
        # Manually backdate the cached_at timestamp so the entry looks expired
        cache.memory_cache["https://example.com"]["cached_at"] = "2000-01-01T00:00:00+00:00"
        result = cache.get("https://example.com")
        assert result is None

    def test_no_ttl_never_expires(self):
        cache = PageCache(ttl=None)
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"])
        cache.memory_cache["https://example.com"]["cached_at"] = "2000-01-01T00:00:00+00:00"
        # Without TTL, data should still be returned
        result = cache.get("https://example.com")
        assert result is not None

    def test_remove(self):
        cache = PageCache()
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"])
        cache.remove("https://example.com")
        assert cache.get("https://example.com") is None

    def test_clear(self):
        cache = PageCache()
        for i in range(3):
            url = f"https://example.com/page{i}"
            cache.set(url, {}, 200, {})
        cache.clear()
        assert len(cache.memory_cache) == 0

    def test_stats_memory_only(self):
        cache = PageCache()
        cache.set("https://a.com", {}, 200, {})
        cache.set("https://b.com", {}, 200, {})
        stats = cache.get_stats()
        assert stats["memory_entries"] == 2
        assert stats["disk_entries"] == 0
        assert stats["disk_cache_enabled"] is False


# ──────────────────────────────────────────────────────────
# PageCache – disk mode
# ──────────────────────────────────────────────────────────

class TestPageCacheDisk:
    def test_set_writes_file(self, tmp_path):
        cache = PageCache(cache_dir=str(tmp_path), enable_disk_cache=True)
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"], e["content"])
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1

    def test_get_reads_from_disk(self, tmp_path):
        cache = PageCache(cache_dir=str(tmp_path), enable_disk_cache=True)
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"])
        # Clear memory to force disk read
        cache.memory_cache.clear()
        result = cache.get("https://example.com")
        assert result is not None
        assert result["status_code"] == 200

    def test_disk_expired_entry_removed(self, tmp_path):
        cache = PageCache(cache_dir=str(tmp_path), ttl=1, enable_disk_cache=True)
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"])
        # Backdate the file content
        cache_path = cache._get_cache_path("https://example.com")
        data = json.loads(cache_path.read_text())
        data["cached_at"] = "2000-01-01T00:00:00+00:00"
        cache_path.write_text(json.dumps(data))
        cache.memory_cache.clear()

        result = cache.get("https://example.com")
        assert result is None
        assert not cache_path.exists()

    def test_stats_disk_entries(self, tmp_path):
        cache = PageCache(cache_dir=str(tmp_path), enable_disk_cache=True)
        for i in range(3):
            cache.set(f"https://example.com/{i}", {}, 200, {})
        stats = cache.get_stats()
        assert stats["disk_entries"] == 3

    def test_remove_deletes_disk_file(self, tmp_path):
        cache = PageCache(cache_dir=str(tmp_path), enable_disk_cache=True)
        e = _make_entry()
        cache.set(e["url"], e["response_data"], e["status_code"], e["headers"])
        cache.remove("https://example.com")
        assert not list(tmp_path.glob("*.json"))

    def test_clear_removes_disk_files(self, tmp_path):
        cache = PageCache(cache_dir=str(tmp_path), enable_disk_cache=True)
        for i in range(3):
            cache.set(f"https://example.com/{i}", {}, 200, {})
        cache.clear()
        assert not list(tmp_path.glob("*.json"))

    def test_default_cache_dir_created_when_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cache = PageCache(enable_disk_cache=True)  # no cache_dir given
        assert cache.cache_dir is not None
        assert cache.cache_dir.exists()


# ──────────────────────────────────────────────────────────
# CrawlResume tests
# ──────────────────────────────────────────────────────────

class TestCrawlResume:
    def _write_state(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f)

    def test_can_resume_missing_file(self, tmp_path):
        assert CrawlResume.can_resume(str(tmp_path / "state.json")) is False

    def test_can_resume_valid_file(self, tmp_path):
        path = str(tmp_path / "state.json")
        self._write_state(path, {
            "queue": ["https://a.com"],
            "visited_urls": ["https://b.com"],
            "results": {}
        })
        assert CrawlResume.can_resume(path) is True

    def test_can_resume_missing_keys(self, tmp_path):
        path = str(tmp_path / "state.json")
        self._write_state(path, {"queue": []})  # Missing visited_urls and results
        assert CrawlResume.can_resume(path) is False

    def test_can_resume_corrupt_file(self, tmp_path):
        path = str(tmp_path / "state.json")
        Path(path).write_text("not json")
        assert CrawlResume.can_resume(path) is False

    def test_get_resume_info(self, tmp_path):
        path = str(tmp_path / "state.json")
        self._write_state(path, {
            "queue": ["https://a.com", "https://b.com"],
            "visited_urls": ["https://c.com"],
            "results": {"https://c.com": {}},
            "saved_at": "2025-01-01T00:00:00",
            "metadata": {"start_url": "https://c.com"}
        })
        info = CrawlResume.get_resume_info(path)
        assert info["queue_size"] == 2
        assert info["visited_count"] == 1
        assert info["results_count"] == 1
        assert info["saved_at"] == "2025-01-01T00:00:00"
        assert info["metadata"]["start_url"] == "https://c.com"

    def test_get_resume_info_missing_file(self, tmp_path):
        info = CrawlResume.get_resume_info(str(tmp_path / "missing.json"))
        assert info == {}
