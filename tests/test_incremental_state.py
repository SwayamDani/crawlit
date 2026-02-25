#!/usr/bin/env python3
"""
test_incremental_state.py - Tests for IncrementalState and StateManager
"""

import json
import pickle
import tempfile
import time
from pathlib import Path

import pytest

from crawlit.utils.incremental import IncrementalState, StateManager


# ──────────────────────────────────────────────────────────
# IncrementalState tests
# ──────────────────────────────────────────────────────────

class TestIncrementalState:
    def test_empty_on_init(self):
        state = IncrementalState()
        assert state.is_empty()
        assert len(state) == 0

    def test_set_and_get_url_state(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"abc123"')
        info = state.get_url_state("https://example.com")
        assert info is not None
        assert info["etag"] == '"abc123"'
        assert "last_crawled" in info

    def test_set_url_state_updates_last_crawled(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"v1"')
        t1 = state.get_url_state("https://example.com")["last_crawled"]
        time.sleep(0.05)
        state.set_url_state("https://example.com", etag='"v2"')
        t2 = state.get_url_state("https://example.com")["last_crawled"]
        assert t2 >= t1

    def test_get_missing_url_returns_none(self):
        state = IncrementalState()
        assert state.get_url_state("https://nothere.com") is None

    def test_contains(self):
        state = IncrementalState()
        state.set_url_state("https://example.com")
        assert "https://example.com" in state
        assert "https://other.com" not in state

    # ── should_crawl ──

    def test_should_crawl_new_url(self):
        state = IncrementalState()
        crawl, reason = state.should_crawl("https://example.com")
        assert crawl is True
        assert reason == "new_url"

    def test_should_crawl_force(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"abc"')
        crawl, reason = state.should_crawl("https://example.com",
                                           current_etag='"abc"', force=True)
        assert crawl is True
        assert reason == "forced"

    def test_should_crawl_etag_match(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"abc123"')
        crawl, reason = state.should_crawl("https://example.com",
                                           current_etag='"abc123"')
        assert crawl is False
        assert reason == "etag_match"

    def test_should_crawl_etag_changed(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"old"')
        crawl, reason = state.should_crawl("https://example.com",
                                           current_etag='"new"')
        assert crawl is True
        assert reason == "etag_changed"

    def test_should_crawl_last_modified_match(self):
        state = IncrementalState()
        lm = "Wed, 01 Jan 2025 00:00:00 GMT"
        state.set_url_state("https://example.com", last_modified=lm)
        crawl, reason = state.should_crawl("https://example.com",
                                           current_last_modified=lm)
        assert crawl is False
        assert reason == "last_modified_match"

    def test_should_crawl_last_modified_changed(self):
        state = IncrementalState()
        state.set_url_state("https://example.com",
                            last_modified="Mon, 01 Jan 2024 00:00:00 GMT")
        crawl, reason = state.should_crawl(
            "https://example.com",
            current_last_modified="Fri, 01 Jan 2025 00:00:00 GMT"
        )
        assert crawl is True
        assert reason == "last_modified_changed"

    def test_should_crawl_content_hash_match(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", content_hash="deadbeef")
        crawl, reason = state.should_crawl("https://example.com",
                                           current_content_hash="deadbeef")
        assert crawl is False
        assert reason == "content_match"

    def test_should_crawl_content_hash_changed(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", content_hash="aaa")
        crawl, reason = state.should_crawl("https://example.com",
                                           current_content_hash="bbb")
        assert crawl is True
        assert reason == "content_changed"

    def test_should_crawl_no_comparison_data(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"x"')
        # No current_ values passed → nothing to compare
        crawl, reason = state.should_crawl("https://example.com")
        assert crawl is True
        assert reason == "no_comparison_data"

    def test_max_age_expired(self):
        state = IncrementalState()
        state.set_url_state("https://example.com")
        # Force an old last_crawled by patching the stored value
        state._state["https://example.com"]["last_crawled"] = "2000-01-01T00:00:00+00:00"
        crawl, reason = state.should_crawl("https://example.com",
                                           max_age_hours=1)
        assert crawl is True
        assert reason == "expired"

    def test_max_age_not_expired(self):
        state = IncrementalState()
        state.set_url_state("https://example.com")
        crawl, reason = state.should_crawl("https://example.com",
                                           max_age_hours=24)
        # Recently crawled → should not crawl again (falls through to no_comparison_data)
        assert reason != "expired"

    # ── remove / clear ──

    def test_remove_url(self):
        state = IncrementalState()
        state.set_url_state("https://example.com")
        assert state.remove_url("https://example.com") is True
        assert "https://example.com" not in state

    def test_remove_missing_url_returns_false(self):
        state = IncrementalState()
        assert state.remove_url("https://nothere.com") is False

    def test_clear(self):
        state = IncrementalState()
        state.set_url_state("https://a.com")
        state.set_url_state("https://b.com")
        state.clear()
        assert state.is_empty()

    # ── statistics ──

    def test_get_statistics(self):
        state = IncrementalState()
        state.set_url_state("https://a.com", etag='"a"')
        state.set_url_state("https://b.com", last_modified="Mon, 01 Jan 2024 00:00:00 GMT")
        state.set_url_state("https://c.com", content_hash="abc")
        stats = state.get_statistics()
        assert stats["total_urls"] == 3
        assert stats["urls_with_etag"] == 1
        assert stats["urls_with_last_modified"] == 1
        assert stats["urls_with_content_hash"] == 1

    # ── serialisation ──

    def test_to_dict_and_from_dict(self):
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"x"',
                            content_hash="hash1")
        d = state.to_dict()
        assert "https://example.com" in d

        state2 = IncrementalState()
        state2.from_dict(d)
        assert state2.get_url_state("https://example.com")["etag"] == '"x"'


# ──────────────────────────────────────────────────────────
# StateManager tests
# ──────────────────────────────────────────────────────────

class TestStateManager:
    def test_load_nonexistent_file_returns_empty_state(self, tmp_path):
        manager = StateManager(str(tmp_path / "state.json"))
        state = manager.load()
        assert state.is_empty()

    def test_save_and_load_json(self, tmp_path):
        manager = StateManager(str(tmp_path / "state.json"), format="json")
        state = IncrementalState()
        state.set_url_state("https://example.com", etag='"v1"')
        manager.save(state)

        loaded = manager.load()
        info = loaded.get_url_state("https://example.com")
        assert info is not None
        assert info["etag"] == '"v1"'

    def test_save_and_load_pickle(self, tmp_path):
        manager = StateManager(str(tmp_path / "state.pkl"), format="pickle")
        state = IncrementalState()
        state.set_url_state("https://example.com", content_hash="abc")
        manager.save(state)

        loaded = manager.load()
        info = loaded.get_url_state("https://example.com")
        assert info is not None
        assert info["content_hash"] == "abc"

    def test_unsupported_format_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported format"):
            StateManager(str(tmp_path / "state.xml"), format="xml")

    def test_load_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "state.json"
        manager = StateManager(str(deep_path))
        state = IncrementalState()
        state.set_url_state("https://example.com")
        manager.save(state)
        assert deep_path.exists()

    def test_load_corrupt_file_returns_empty_state(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("not valid json")
        manager = StateManager(str(path))
        state = manager.load()
        assert state.is_empty()
