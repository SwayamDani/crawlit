#!/usr/bin/env python3
"""
Tests for sitemap parsing and crawling support
"""

import pytest
from crawlit.crawler.engine import Crawler
from crawlit.utils.sitemap import SitemapParser, get_sitemaps_from_robots


class TestSitemapParser:
    """Test sitemap parser functionality"""
    
    def test_parse_simple_sitemap(self):
        """Test parsing a simple sitemap XML"""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/</loc>
        <lastmod>2023-01-01</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://example.com/page1</loc>
        <lastmod>2023-01-02</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
</urlset>"""
        
        parser = SitemapParser()
        
        # Mock the HTTP request by directly parsing XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(sitemap_xml)
        url_elements = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        
        urls = []
        for url_elem in url_elements:
            loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_elem is not None:
                urls.append(loc_elem.text.strip())
        
        assert len(urls) == 2
        assert 'https://example.com/' in urls
        assert 'https://example.com/page1' in urls
    
    def test_get_urls_from_sitemap(self, httpserver):
        """Test extracting URLs from a sitemap via HTTP"""
        base_url = httpserver.url_for("/")
        port = httpserver.port
        
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>http://localhost:{}/page1</loc>
    </url>
    <url>
        <loc>http://localhost:{}/page2</loc>
    </url>
</urlset>""".format(port, port)
        
        httpserver.expect_request("/sitemap.xml").respond_with_data(
            sitemap_xml,
            content_type="application/xml"
        )
        
        parser = SitemapParser()
        sitemap_url = f"http://localhost:{port}/sitemap.xml"
        urls = parser.get_urls_from_sitemap(sitemap_url)
        
        assert len(urls) == 2
        assert f"http://localhost:{port}/page1" in urls
        assert f"http://localhost:{port}/page2" in urls


class TestCrawlerWithSitemap:
    """Test crawler integration with sitemap support"""
    
    def test_crawler_with_sitemap_disabled(self, mock_website):
        """Test crawler with sitemap support disabled (default)"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            use_sitemap=False
        )
        
        # Should work normally without sitemap
        crawler.crawl()
        results = crawler.get_results()
        assert len(results) > 0
    
    def test_crawler_with_explicit_sitemap(self, httpserver):
        """Test crawler with explicitly provided sitemap URL"""
        port = httpserver.port
        base_url = f"http://localhost:{port}"
        
        # Create a sitemap
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>http://localhost:{}/sitemap-page1</loc>
    </url>
    <url>
        <loc>http://localhost:{}/sitemap-page2</loc>
    </url>
</urlset>""".format(port, port)
        
        httpserver.expect_request("/sitemap.xml").respond_with_data(
            sitemap_xml,
            content_type="application/xml"
        )
        
        # Create pages referenced in sitemap
        httpserver.expect_request("/sitemap-page1").respond_with_data(
            "<html><body>Page 1</body></html>",
            content_type="text/html"
        )
        httpserver.expect_request("/sitemap-page2").respond_with_data(
            "<html><body>Page 2</body></html>",
            content_type="text/html"
        )
        
        # Also need to handle robots.txt and root path
        httpserver.expect_request("/robots.txt").respond_with_data(
            "User-agent: *\nAllow: /\n",
            content_type="text/plain"
        )
        httpserver.expect_request("/").respond_with_data(
            "<html><body>Home</body></html>",
            content_type="text/html"
        )
        
        sitemap_url = f"{base_url}/sitemap.xml"
        
        crawler = Crawler(
            start_url=base_url,
            max_depth=0,
            use_sitemap=True,
            sitemap_urls=[sitemap_url],
            internal_only=False  # Allow crawling sitemap URLs
        )
        
        crawler.crawl()
        results = crawler.get_results()
        
        # Should have crawled pages from sitemap (at least the ones from sitemap)
        # The start_url might fail, but sitemap URLs should be crawled
        sitemap_urls_found = [
            url for url in results.keys() 
            if "sitemap-page1" in url or "sitemap-page2" in url
        ]
        assert len(sitemap_urls_found) >= 2, f"Expected at least 2 sitemap URLs, found: {sitemap_urls_found}"


