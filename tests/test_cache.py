#!/usr/bin/env python3
"""
Tests for caching and persistence features
"""

import pytest
import os
import tempfile
import time
from crawlit.crawler.engine import Crawler
from crawlit.utils.cache import PageCache, CrawlResume


class TestPageCache:
    """Test page caching functionality"""
    
    def test_memory_cache(self):
        """Test memory-only caching"""
        cache = PageCache(ttl=60, enable_disk_cache=False)
        
        # Cache a page
        cache.set(
            'https://example.com',
            {'title': 'Example'},
            200,
            {'Content-Type': 'text/html'},
            '<html><body>Test</body></html>'
        )
        
        # Retrieve from cache
        cached = cache.get('https://example.com')
        assert cached is not None
        assert cached['status_code'] == 200
        assert cached['content'] == '<html><body>Test</body></html>'
    
    def test_cache_expiration(self):
        """Test cache expiration with TTL"""
        cache = PageCache(ttl=1, enable_disk_cache=False)  # 1 second TTL
        
        # Cache a page
        cache.set(
            'https://example.com',
            {'title': 'Example'},
            200,
            {'Content-Type': 'text/html'},
            '<html><body>Test</body></html>'
        )
        
        # Should be available immediately
        assert cache.get('https://example.com') is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get('https://example.com') is None
    
    def test_disk_cache(self):
        """Test disk-based caching"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PageCache(cache_dir=tmpdir, ttl=None, enable_disk_cache=True)
            
            # Cache a page
            cache.set(
                'https://example.com',
                {'title': 'Example'},
                200,
                {'Content-Type': 'text/html'},
                '<html><body>Test</body></html>'
            )
            
            # Create new cache instance (simulating restart)
            new_cache = PageCache(cache_dir=tmpdir, ttl=None, enable_disk_cache=True)
            
            # Should retrieve from disk
            cached = new_cache.get('https://example.com')
            assert cached is not None
            assert cached['status_code'] == 200
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = PageCache(ttl=60, enable_disk_cache=False)
        
        cache.set('https://example.com', {}, 200, {}, 'content')
        cache.set('https://example.org', {}, 200, {}, 'content')
        
        stats = cache.get_stats()
        assert stats['memory_entries'] == 2
        assert stats['ttl'] == 60
        assert stats['disk_cache_enabled'] == False
    
    def test_cache_clear(self):
        """Test clearing cache"""
        cache = PageCache(ttl=60, enable_disk_cache=False)
        
        cache.set('https://example.com', {}, 200, {}, 'content')
        assert cache.get('https://example.com') is not None
        
        cache.clear()
        assert cache.get('https://example.com') is None


class TestCrawlResume:
    """Test crawl resume functionality"""
    
    @pytest.fixture
    def mock_website(self, httpserver):
        """Create a simple mock website for testing"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Cache Test Site</title></head>
        <body>
            <h1>Cache Test Website</h1>
            <p>This is a test page for caching.</p>
            <a href="/page1">Page 1</a>
        </body>
        </html>
        """
        
        page1_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Page 1</title></head>
        <body>
            <h1>Page 1</h1>
            <p>This is page 1.</p>
        </body>
        </html>
        """
        
        httpserver.expect_request("/").respond_with_data(
            html,
            content_type="text/html"
        )
        httpserver.expect_request("/page1").respond_with_data(
            page1_html,
            content_type="text/html"
        )
        
        return httpserver.url_for("/")
    
    def test_can_resume(self, mock_website):
        """Test checking if resume is possible"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        crawler.queue.append((mock_website, 0))
        crawler.visited_urls.add(mock_website)
        crawler.results[mock_website] = {'success': True}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            crawler.save_state(temp_path)
            
            assert CrawlResume.can_resume(temp_path) == True
            assert CrawlResume.can_resume('nonexistent.json') == False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_get_resume_info(self, mock_website):
        """Test getting resume information"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        crawler.queue.append((mock_website, 0))
        crawler.visited_urls.add(mock_website)
        crawler.results[mock_website] = {'success': True}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            crawler.save_state(temp_path)
            
            info = CrawlResume.get_resume_info(temp_path)
            assert info['queue_size'] == 1
            assert info['visited_count'] == 1
            assert info['results_count'] == 1
            assert 'saved_at' in info
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestCrawlerWithCache:
    """Test crawler integration with cache"""
    
    @pytest.fixture
    def mock_website(self, httpserver):
        """Create a simple mock website for testing"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Cache Test Site</title></head>
        <body>
            <h1>Cache Test Website</h1>
            <p>This is a test page for caching.</p>
            <a href="/page1">Page 1</a>
        </body>
        </html>
        """
        
        page1_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Page 1</title></head>
        <body>
            <h1>Page 1</h1>
            <p>This is page 1.</p>
        </body>
        </html>
        """
        
        httpserver.expect_request("/").respond_with_data(
            html,
            content_type="text/html"
        )
        httpserver.expect_request("/page1").respond_with_data(
            page1_html,
            content_type="text/html"
        )
        
        return httpserver.url_for("/")
    
    def test_crawler_with_cache(self, mock_website):
        """Test crawler using cache"""
        cache = PageCache(ttl=3600, enable_disk_cache=False)
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            page_cache=cache
        )
        
        # First crawl - should fetch
        crawler.crawl()
        results = crawler.get_results()
        assert len(results) > 0
        
        # Check cache was populated
        stats = cache.get_stats()
        assert stats['memory_entries'] > 0
    
    def test_crawler_resume(self, mock_website):
        """Test resuming a crawl"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        # Start crawling
        crawler.crawl()
        
        # Save state
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            crawler.save_state(temp_path)
            
            # Create new crawler and resume
            new_crawler = Crawler(
                start_url=mock_website,
                max_depth=1
            )
            
            # Should be able to resume
            assert CrawlResume.can_resume(temp_path) == True
            
            # Resume (this will continue crawling)
            new_crawler.resume_from(temp_path)
            
            # Should have results
            results = new_crawler.get_results()
            assert len(results) > 0
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


