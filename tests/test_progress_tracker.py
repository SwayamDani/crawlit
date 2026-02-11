"""
Tests for progress tracking functionality
"""

import pytest
from crawlit.utils.progress import ProgressTracker, create_progress_callback


class TestProgressTracker:
    """Test cases for ProgressTracker class"""
    
    def test_initialization(self):
        """Test tracker initialization"""
        tracker = ProgressTracker()
        
        assert tracker.urls_crawled == 0
        assert tracker.urls_successful == 0
        assert tracker.urls_failed == 0
    
    def test_start(self):
        """Test starting the tracker"""
        tracker = ProgressTracker()
        tracker.start()
        
        assert tracker.start_time is not None
    
    def test_record_url(self):
        """Test recording URLs"""
        tracker = ProgressTracker()
        tracker.start()
        
        tracker.record_url('https://example.com', True, links_found=5, depth=0)
        
        assert tracker.urls_crawled == 1
        assert tracker.urls_successful == 1
        assert tracker.urls_failed == 0
        assert tracker.total_links_found == 5
    
    def test_record_failed_url(self):
        """Test recording failed URLs"""
        tracker = ProgressTracker()
        tracker.start()
        
        tracker.record_url('https://example.com', False, depth=0)
        
        assert tracker.urls_crawled == 1
        assert tracker.urls_successful == 0
        assert tracker.urls_failed == 1
    
    def test_callback_on_url_crawled(self):
        """Test URL crawled callback"""
        called_urls = []
        
        def callback(url: str, data: dict):
            called_urls.append(url)
        
        tracker = ProgressTracker(on_url_crawled=callback)
        tracker.start()
        tracker.record_url('https://example.com', True)
        
        assert 'https://example.com' in called_urls
    
    def test_callback_on_progress(self):
        """Test progress callback"""
        progress_calls = []
        
        def callback(stats: dict):
            progress_calls.append(stats)
        
        tracker = ProgressTracker(on_progress=callback, update_interval=2)
        tracker.start()
        
        tracker.record_url('https://example.com/1', True)
        tracker.record_url('https://example.com/2', True)
        
        # Should be called after 2 URLs
        assert len(progress_calls) > 0
    
    def test_get_stats(self):
        """Test getting statistics"""
        tracker = ProgressTracker()
        tracker.start()
        
        tracker.record_url('https://example.com', True, links_found=3)
        
        stats = tracker.get_stats()
        
        assert stats['urls_crawled'] == 1
        assert stats['urls_successful'] == 1
        assert stats['total_links_found'] == 3
        assert 'success_rate' in stats
    
    def test_finish(self):
        """Test finishing the tracker"""
        tracker = ProgressTracker()
        tracker.start()
        tracker.record_url('https://example.com', True)
        
        final_stats = tracker.finish()
        
        assert final_stats['urls_crawled'] == 1


class TestProgressCallbacks:
    """Test cases for progress callback utilities"""
    
    def test_create_progress_callback(self):
        """Test creating a progress callback"""
        callback = create_progress_callback(show_progress=True)
        
        assert callback is not None
        assert callable(callback)
    
    def test_create_progress_callback_disabled(self):
        """Test creating a disabled progress callback"""
        callback = create_progress_callback(show_progress=False)
        
        assert callback is None

