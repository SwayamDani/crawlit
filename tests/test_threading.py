#!/usr/bin/env python3
"""
Tests for threading support in sync crawler
"""

import pytest
from crawlit.crawler.engine import Crawler


class TestThreadingSupport:
    """Test threading support in sync crawler"""
    
    def test_single_threaded_default(self, mock_website):
        """Test that crawler defaults to single-threaded mode"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        assert crawler.max_workers == 1
        # Verify locks exist even in single-threaded mode
        assert crawler._queue_lock is not None
        assert crawler._visited_lock is not None
        assert crawler._results_lock is not None
    
    def test_multi_threaded_enabled(self, mock_website):
        """Test that multi-threading can be enabled"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            max_workers=5
        )
        
        assert crawler.max_workers == 5
        assert crawler._queue_lock is not None
        assert crawler._visited_lock is not None
        assert crawler._results_lock is not None
    
    def test_single_threaded_crawl(self, mock_website):
        """Test that single-threaded crawling works"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            max_workers=1
        )
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should work normally
        assert len(results) > 0
    
    def test_multi_threaded_crawl(self, mock_website):
        """Test that multi-threaded crawling works"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            max_workers=3
        )
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should work normally
        assert len(results) > 0
    
    def test_threading_with_queue_limit(self, mock_website):
        """Test threading with queue size limit"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            max_workers=3,
            max_queue_size=10
        )
        
        assert crawler.max_workers == 3
        assert crawler.max_queue_size == 10
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should work normally
        assert len(results) > 0
    
    def test_threading_backward_compatibility(self, mock_website):
        """Test that existing code without max_workers still works"""
        # Don't specify max_workers - should default to 1
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        assert crawler.max_workers == 1
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should work normally
        assert len(results) > 0

