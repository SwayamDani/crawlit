"""
Tests for integrated utilities (ProgressTracker, URLFilter, SessionManager)
"""

import pytest
from crawlit import Crawler, AsyncCrawler
from crawlit.utils import ProgressTracker, URLFilter, SessionManager, create_progress_callback


class TestIntegratedProgressTracker:
    """Test ProgressTracker integration with Crawler"""
    
    def test_progress_tracker_integration(self, mock_website):
        """Test that ProgressTracker is automatically used by crawler"""
        progress_calls = []
        
        def progress_callback(stats):
            progress_calls.append(stats)
        
        tracker = ProgressTracker(
            on_progress=progress_callback,
            update_interval=2
        )
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            progress_tracker=tracker
        )
        
        crawler.crawl()
        
        # Progress tracker should have been called
        assert tracker.urls_crawled > 0
        assert len(progress_calls) > 0 or tracker.urls_crawled < 2
        
        # Check final stats
        final_stats = tracker.get_stats()
        assert final_stats['urls_crawled'] > 0
        assert 'success_rate' in final_stats
    
    def test_progress_tracker_without_callback(self, mock_website):
        """Test ProgressTracker works without callbacks"""
        tracker = ProgressTracker()
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            progress_tracker=tracker
        )
        
        crawler.crawl()
        
        # Should still track progress
        assert tracker.urls_crawled > 0
        stats = tracker.get_stats()
        assert stats['urls_crawled'] > 0


class TestIntegratedURLFilter:
    """Test URLFilter integration with Crawler"""
    
    def test_url_filter_integration(self, mock_website):
        """Test that URLFilter is used by crawler"""
        # Create filter that blocks specific pattern
        url_filter = URLFilter.from_patterns(blocked_regex=r'page2')
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=2,
            url_filter=url_filter
        )
        
        crawler.crawl()
        results = crawler.get_results()
        
        # page2 should not be in results (blocked by filter)
        for url in results.keys():
            assert 'page2' not in url.lower()
    
    def test_url_filter_html_only(self, mock_website):
        """Test HTML-only filter integration"""
        url_filter = URLFilter.html_only()
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            url_filter=url_filter
        )
        
        crawler.crawl()
        results = crawler.get_results()
        
        # All URLs should be HTML or have no extension
        for url in results.keys():
            # Filter should have been applied
            assert url_filter.is_allowed(url) or url not in results


class TestIntegratedSessionManager:
    """Test SessionManager integration with Crawler"""
    
    def test_session_manager_integration(self, mock_website):
        """Test that SessionManager is used by crawler"""
        session_mgr = SessionManager(
            user_agent="test-agent/1.0",
            cookies={'test': 'value'}
        )
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            session_manager=session_mgr
        )
        
        crawler.crawl()
        
        # Session should have been used
        session = session_mgr.get_sync_session()
        assert session is not None
        assert session.headers['User-Agent'] == "test-agent/1.0"
    
    def test_session_manager_auto_creation(self, mock_website):
        """Test that SessionManager is auto-created if not provided"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        # Should have a session manager
        assert hasattr(crawler, 'session_manager')
        assert crawler.session_manager is not None


class TestAllFeaturesIntegrated:
    """Test all features working together"""
    
    def test_all_features_together(self, mock_website):
        """Test ProgressTracker, URLFilter, and SessionManager all together"""
        progress_calls = []
        
        def progress_callback(stats):
            progress_calls.append(stats)
        
        tracker = ProgressTracker(
            on_progress=progress_callback,
            update_interval=1
        )
        
        url_filter = URLFilter.html_only()
        session_mgr = SessionManager(user_agent="integrated-test/1.0")
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            progress_tracker=tracker,
            url_filter=url_filter,
            session_manager=session_mgr
        )
        
        crawler.crawl()
        
        # All features should have worked
        assert tracker.urls_crawled > 0
        assert crawler.session_manager is session_mgr
        assert crawler.url_filter is url_filter


class TestBackwardCompatibility:
    """Test that crawler still works without integrated features"""
    
    def test_crawler_without_utilities(self, mock_website):
        """Test crawler works without any utilities (backward compatibility)"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should work normally
        assert len(results) > 0
        # Session manager should be auto-created
        assert hasattr(crawler, 'session_manager')
        assert crawler.session_manager is not None
    
    def test_content_extraction_disabled(self, mock_website):
        """Test that content extraction can be disabled to save resources"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            enable_content_extraction=False
        )
        
        # Verify content extraction is disabled
        assert crawler.content_extraction_enabled == False
        assert crawler.content_extractor is None
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should work normally
        assert len(results) > 0
        
        # Check that content extraction fields are NOT present
        for url, data in results.items():
            if data.get('success'):
                # Content extraction fields should not be present
                assert 'title' not in data or data.get('title') is None
                assert 'meta_description' not in data or data.get('meta_description') is None
                assert 'headings' not in data or data.get('headings') is None
                assert 'page_type' not in data or data.get('page_type') is None
    
    def test_content_extraction_enabled(self, mock_website):
        """Test that content extraction works when enabled"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            enable_content_extraction=True
        )
        
        # Verify content extraction is enabled
        assert crawler.content_extraction_enabled == True
        assert crawler.content_extractor is not None
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should work normally
        assert len(results) > 0
        
        # Check that content extraction fields ARE present for successful pages
        for url, data in results.items():
            if data.get('success') and 'text/html' in data.get('content_type', ''):
                # Content extraction fields should be present
                assert 'title' in data
                assert 'headings' in data
                assert 'page_type' in data

