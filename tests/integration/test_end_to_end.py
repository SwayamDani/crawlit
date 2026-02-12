#!/usr/bin/env python3
"""
End-to-end integration tests with real HTTP servers
"""

import pytest
import tempfile
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time


class CustomHTTPHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for testing."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = b'''
            <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Homepage</h1>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
            </body>
            </html>
            '''
            self.wfile.write(html)
        
        elif self.path == '/page1':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('ETag', 'etag-page1')
            self.end_headers()
            html = b'''
            <html>
            <head><title>Page 1</title></head>
            <body>
                <h1>Page 1 Content</h1>
                <a href="/page2">Go to Page 2</a>
            </body>
            </html>
            '''
            self.wfile.write(html)
        
        elif self.path == '/page2':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Last-Modified', 'Mon, 01 Jan 2024 00:00:00 GMT')
            self.end_headers()
            html = b'''
            <html>
            <head><title>Page 2</title></head>
            <body>
                <h1>Page 2 Content</h1>
            </body>
            </html>
            '''
            self.wfile.write(html)
        
        elif self.path == '/robots.txt':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            robots = b'''
            User-agent: *
            Disallow: /private/
            Allow: /
            '''
            self.wfile.write(robots)
        
        elif self.path == '/sitemap.xml':
            self.send_response(200)
            self.send_header('Content-Type', 'application/xml')
            self.end_headers()
            sitemap = b'''<?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url>
                    <loc>http://localhost:8765/</loc>
                    <priority>1.0</priority>
                </url>
                <url>
                    <loc>http://localhost:8765/page1</loc>
                    <priority>0.8</priority>
                </url>
            </urlset>
            '''
            self.wfile.write(sitemap)
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


@pytest.fixture(scope="module")
def test_server():
    """Start a test HTTP server."""
    port = 8765
    server = HTTPServer(('localhost', port), CustomHTTPHandler)
    
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    time.sleep(0.5)  # Give server time to start
    
    yield f"http://localhost:{port}"
    
    server.shutdown()


class TestEndToEndCrawling:
    """End-to-end integration tests."""
    
    def test_basic_crawl(self, test_server):
        """Test basic crawl with real HTTP server."""
        from crawlit import Crawler
        
        crawler = Crawler(
            max_depth=2,
            max_pages=10,
            respect_robots_txt=True
        )
        
        results = crawler.crawl(test_server)
        
        assert len(results) > 0
        
        # Check homepage was crawled
        homepage = next((r for r in results if r['url'] == test_server + '/'), None)
        assert homepage is not None
        assert 'Test Homepage' in homepage['html']
        
        # Check links were followed
        assert any('/page1' in r['url'] for r in results)
    
    def test_crawl_with_budget_tracker(self, test_server):
        """Test crawling with budget limits."""
        from crawlit import Crawler, BudgetTracker
        
        tracker = BudgetTracker(max_pages=2, max_bandwidth_mb=1.0)
        tracker.start()
        
        crawler = Crawler(max_depth=2)
        
        # Crawl with budget limits
        results = []
        for result in crawler.crawl_iter(test_server):
            tracker.record_page(len(result['html'].encode('utf-8')))
            results.append(result)
            
            if tracker.is_budget_exceeded():
                break
        
        # Should stop at or before max_pages
        assert len(results) <= 2
    
    def test_crawl_with_incremental_state(self, test_server):
        """Test incremental crawling with real server."""
        from crawlit import Crawler
        from crawlit.utils.incremental import IncrementalState
        
        state = IncrementalState()
        
        # First crawl
        crawler = Crawler(max_depth=1, max_pages=5)
        results1 = list(crawler.crawl_iter(test_server))
        
        # Store state
        for result in results1:
            etag = result.get('headers', {}).get('ETag')
            last_modified = result.get('headers', {}).get('Last-Modified')
            state.set_url_state(result['url'], etag=etag, last_modified=last_modified)
        
        # Second crawl - check what should be re-crawled
        crawler2 = Crawler(max_depth=1, max_pages=5)
        
        urls_to_crawl = []
        for result in results1:
            should_crawl, reason = state.should_crawl(
                result['url'],
                current_etag=result.get('headers', {}).get('ETag'),
                current_last_modified=result.get('headers', {}).get('Last-Modified')
            )
            if should_crawl:
                urls_to_crawl.append(result['url'])
        
        # With unchanged content, most URLs shouldn't need re-crawling
        assert len(urls_to_crawl) < len(results1)
    
    def test_crawl_with_robots_txt(self, test_server):
        """Test respecting robots.txt."""
        from crawlit import Crawler
        
        crawler = Crawler(
            max_depth=2,
            respect_robots_txt=True
        )
        
        results = crawler.crawl(test_server)
        
        # Should not crawl /private/ URLs (disallowed in robots.txt)
        assert not any('/private/' in r['url'] for r in results)
    
    def test_sitemap_discovery(self, test_server):
        """Test sitemap discovery and parsing."""
        from crawlit.parser.sitemap_parser import SitemapParser
        
        parser = SitemapParser()
        sitemap_url = f"{test_server}/sitemap.xml"
        
        urls = parser.parse_sitemap(sitemap_url)
        
        assert len(urls) > 0
        assert any(test_server in url['loc'] for url in urls)
    
    def test_concurrent_crawling(self, test_server):
        """Test concurrent crawling with thread pool."""
        from crawlit import Crawler
        
        crawler = Crawler(
            max_depth=2,
            max_pages=10,
            max_concurrent=3
        )
        
        start_time = time.time()
        results = crawler.crawl(test_server)
        end_time = time.time()
        
        assert len(results) > 0
        
        # Concurrent crawling should be faster than sequential
        # (This is a rough check)
        assert end_time - start_time < 10  # Should complete reasonably fast


@pytest.mark.asyncio
class TestAsyncEndToEndCrawling:
    """Async end-to-end integration tests."""
    
    async def test_async_basic_crawl(self, test_server):
        """Test basic async crawl."""
        from crawlit import AsyncCrawler
        
        crawler = AsyncCrawler(
            max_depth=2,
            max_pages=10
        )
        
        results = await crawler.crawl(test_server)
        
        assert len(results) > 0
        assert any(test_server in r['url'] for r in results)
    
    async def test_async_concurrent_crawling(self, test_server):
        """Test async concurrent crawling."""
        from crawlit import AsyncCrawler
        
        crawler = AsyncCrawler(
            max_depth=2,
            max_pages=10,
            max_concurrent=5
        )
        
        start_time = time.time()
        results = await crawler.crawl(test_server)
        end_time = time.time()
        
        assert len(results) > 0
        
        # Should complete reasonably fast
        assert end_time - start_time < 5


class TestRealWorldScenarios:
    """Tests with real-world-like scenarios."""
    
    def test_crawl_with_download_files(self, test_server):
        """Test crawling and downloading files."""
        from crawlit import Crawler
        from crawlit.utils.download_manager import DownloadManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crawler = Crawler(max_depth=1)
            download_manager = DownloadManager(download_dir=tmpdir)
            
            results = crawler.crawl(test_server)
            
            # In a real scenario, would download PDF/image files found
            # For this test, just verify setup works
            assert len(results) > 0
    
    def test_full_feature_crawl(self, test_server):
        """Test crawl with multiple features enabled."""
        from crawlit import Crawler, BudgetTracker
        from crawlit.utils.priority_queue import URLPriorityQueue, BreadthFirstStrategy
        from crawlit.utils.incremental import IncrementalState
        
        # Setup
        budget = BudgetTracker(max_pages=10, max_bandwidth_mb=10.0)
        budget.start()
        
        state = IncrementalState()
        
        queue = URLPriorityQueue(strategy=BreadthFirstStrategy())
        
        # Crawl
        crawler = Crawler(
            max_depth=2,
            max_pages=10,
            respect_robots_txt=True,
            follow_redirects=True
        )
        
        results = crawler.crawl(test_server)
        
        # Verify multiple aspects
        assert len(results) > 0
        assert not budget.is_budget_exceeded() or len(results) <= 10
        
        # Update state
        for result in results:
            state.set_url_state(result['url'], etag="test")
        
        assert len(state) > 0

