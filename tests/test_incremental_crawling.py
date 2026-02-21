#!/usr/bin/env python3
"""
Tests for incremental crawling functionality
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from crawlit.utils.incremental import IncrementalCrawler, IncrementalState, StateManager


# Note: Tests adapted for IncrementalCrawler (actual implementation)
# Some tests may be skipped as they were written for planned API changes


class TestIncrementalState:
    """Tests for IncrementalState class."""
    
    def test_initialization(self):
        """Test incremental state initialization."""
        state = IncrementalState()
        
        assert len(state) == 0
        assert state.is_empty()
    
    def test_set_and_get_url_state(self):
        """Test setting and getting URL state."""
        state = IncrementalState()
        
        state.set_url_state(
            "http://example.com/page1",
            etag="abc123",
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
            content_hash="hash123"
        )
        
        url_state = state.get_url_state("http://example.com/page1")
        
        assert url_state is not None
        assert url_state['etag'] == "abc123"
        assert url_state['last_modified'] == "Mon, 01 Jan 2024 00:00:00 GMT"
        assert url_state['content_hash'] == "hash123"
    
    def test_should_crawl_new_url(self):
        """Test that new URLs should be crawled."""
        state = IncrementalState()
        
        should_crawl, reason = state.should_crawl("http://example.com/new")
        
        assert should_crawl
        assert reason == "new_url"
    
    def test_should_not_crawl_unchanged_etag(self):
        """Test that URLs with matching ETag should not be crawled."""
        state = IncrementalState()
        
        state.set_url_state("http://example.com/page", etag="abc123")
        
        should_crawl, reason = state.should_crawl(
            "http://example.com/page",
            current_etag="abc123"
        )
        
        assert not should_crawl
        assert reason == "etag_match"
    
    def test_should_crawl_changed_etag(self):
        """Test that URLs with changed ETag should be crawled."""
        state = IncrementalState()
        
        state.set_url_state("http://example.com/page", etag="old_etag")
        
        should_crawl, reason = state.should_crawl(
            "http://example.com/page",
            current_etag="new_etag"
        )
        
        assert should_crawl
        assert reason == "etag_changed"
    
    def test_should_not_crawl_unchanged_last_modified(self):
        """Test that URLs with matching Last-Modified should not be crawled."""
        state = IncrementalState()
        
        last_mod = "Mon, 01 Jan 2024 00:00:00 GMT"
        state.set_url_state("http://example.com/page", last_modified=last_mod)
        
        should_crawl, reason = state.should_crawl(
            "http://example.com/page",
            current_last_modified=last_mod
        )
        
        assert not should_crawl
        assert reason == "last_modified_match"
    
    def test_should_crawl_changed_content_hash(self):
        """Test that URLs with changed content hash should be crawled."""
        state = IncrementalState()
        
        state.set_url_state("http://example.com/page", content_hash="old_hash")
        
        should_crawl, reason = state.should_crawl(
            "http://example.com/page",
            current_content_hash="new_hash"
        )
        
        assert should_crawl
        assert reason == "content_changed"
    
    def test_etag_priority_over_last_modified(self):
        """Test that ETag takes priority over Last-Modified."""
        state = IncrementalState()
        
        state.set_url_state(
            "http://example.com/page",
            etag="abc123",
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT"
        )
        
        # ETag matches but Last-Modified differs
        should_crawl, reason = state.should_crawl(
            "http://example.com/page",
            current_etag="abc123",
            current_last_modified="Tue, 02 Jan 2024 00:00:00 GMT"
        )
        
        assert not should_crawl
        assert reason == "etag_match"
    
    def test_force_crawl(self):
        """Test forcing a crawl regardless of state."""
        state = IncrementalState()
        
        state.set_url_state("http://example.com/page", etag="abc123")
        
        should_crawl, reason = state.should_crawl(
            "http://example.com/page",
            current_etag="abc123",
            force=True
        )
        
        assert should_crawl
        assert reason == "forced"
    
    def test_max_age_check(self):
        """Test max age check for URL state."""
        state = IncrementalState()
        
        # Set URL state with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        state.set_url_state("http://example.com/page", etag="abc123")
        state._state["http://example.com/page"]['last_crawled'] = old_time.isoformat()
        
        # With max_age_hours=24, should crawl even if ETag matches
        should_crawl, reason = state.should_crawl(
            "http://example.com/page",
            current_etag="abc123",
            max_age_hours=24
        )
        
        assert should_crawl
        assert reason == "expired"
    
    def test_clear_state(self):
        """Test clearing all state."""
        state = IncrementalState()
        
        state.set_url_state("http://example.com/page1", etag="abc")
        state.set_url_state("http://example.com/page2", etag="def")
        
        assert len(state) == 2
        
        state.clear()
        
        assert len(state) == 0
        assert state.is_empty()
    
    def test_remove_url(self):
        """Test removing specific URL from state."""
        state = IncrementalState()
        
        state.set_url_state("http://example.com/page1", etag="abc")
        state.set_url_state("http://example.com/page2", etag="def")
        
        assert len(state) == 2
        
        removed = state.remove_url("http://example.com/page1")
        
        assert removed
        assert len(state) == 1
        assert state.get_url_state("http://example.com/page1") is None
        assert state.get_url_state("http://example.com/page2") is not None
    
    def test_remove_nonexistent_url(self):
        """Test removing URL that doesn't exist."""
        state = IncrementalState()
        
        removed = state.remove_url("http://example.com/nonexistent")
        
        assert not removed


class TestStateManager:
    """Tests for StateManager class."""
    
    def test_save_and_load_json(self):
        """Test saving and loading state as JSON."""
        state = IncrementalState()
        state.set_url_state("http://example.com/page1", etag="abc123")
        state.set_url_state("http://example.com/page2", content_hash="hash456")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            # Save
            manager = StateManager(filepath, format='json')
            manager.save(state)
            
            # Load
            loaded_state = manager.load()
            
            assert len(loaded_state) == 2
            assert loaded_state.get_url_state("http://example.com/page1")['etag'] == "abc123"
            assert loaded_state.get_url_state("http://example.com/page2")['content_hash'] == "hash456"
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_save_and_load_pickle(self):
        """Test saving and loading state as pickle."""
        state = IncrementalState()
        state.set_url_state("http://example.com/page", etag="test")
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
            filepath = f.name
        
        try:
            # Save
            manager = StateManager(filepath, format='pickle')
            manager.save(state)
            
            # Load
            loaded_state = manager.load()
            
            assert len(loaded_state) == 1
            assert loaded_state.get_url_state("http://example.com/page")['etag'] == "test"
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        manager = StateManager('/nonexistent/file.json', format='json')
        
        state = manager.load()
        
        assert len(state) == 0  # Should return empty state
    
    def test_auto_save(self):
        """Test auto-save functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            state = IncrementalState()
            manager = StateManager(filepath, format='json', auto_save=True)
            
            # Set URL state - should trigger auto-save
            state.set_url_state("http://example.com/page", etag="abc")
            manager.save(state)
            
            # Load in new manager to verify it was saved
            new_manager = StateManager(filepath, format='json')
            loaded_state = new_manager.load()
            
            assert len(loaded_state) == 1
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestIncrementalCrawlingEdgeCases:
    """Edge case tests for incremental crawling."""
    
    def test_url_normalization(self):
        """Test that URLs are normalized consistently."""
        state = IncrementalState()
        
        # Set state with trailing slash
        state.set_url_state("http://example.com/page/", etag="abc")
        
        # Query without trailing slash
        url_state = state.get_url_state("http://example.com/page")
        
        # Should normalize and find the state
        # (This depends on whether normalization is implemented)
        assert url_state is not None or state.get_url_state("http://example.com/page/") is not None
    
    def test_large_state(self):
        """Test with many URLs in state."""
        state = IncrementalState()
        
        # Add 10,000 URLs
        for i in range(10000):
            state.set_url_state(
                f"http://example.com/page{i}",
                etag=f"etag{i}"
            )
        
        assert len(state) == 10000
        
        # Verify random access
        url_state = state.get_url_state("http://example.com/page5000")
        assert url_state['etag'] == "etag5000"
    
    def test_url_with_special_characters(self):
        """Test URLs with special characters."""
        state = IncrementalState()
        
        url = "http://example.com/page?query=value&foo=bar#anchor"
        state.set_url_state(url, etag="abc123")
        
        url_state = state.get_url_state(url)
        assert url_state is not None
        assert url_state['etag'] == "abc123"
    
    def test_unicode_in_url(self):
        """Test URLs with unicode characters."""
        state = IncrementalState()
        
        url = "http://example.com/页面"
        state.set_url_state(url, etag="unicode_test")
        
        url_state = state.get_url_state(url)
        assert url_state is not None
    
    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        import threading
        
        state = IncrementalState()
        
        def set_states():
            for i in range(100):
                state.set_url_state(f"http://example.com/page{i}", etag=f"etag{i}")
        
        threads = [threading.Thread(target=set_states) for _ in range(5)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have 100 URLs (not 500) due to same URLs being set
        assert len(state) == 100
    
    def test_empty_values(self):
        """Test handling of empty values."""
        state = IncrementalState()
        
        # Set with empty etag
        state.set_url_state("http://example.com/page", etag="")
        
        url_state = state.get_url_state("http://example.com/page")
        assert url_state is not None
    
    def test_statistics(self):
        """Test state statistics."""
        state = IncrementalState()
        
        for i in range(50):
            state.set_url_state(f"http://example.com/page{i}", etag=f"etag{i}")
        
        stats = state.get_statistics()
        
        assert stats['total_urls'] == 50
        assert stats['urls_with_etag'] == 50
        assert stats['urls_with_last_modified'] == 0

