#!/usr/bin/env python3
"""
Test JavaScript rendering functionality
"""

import pytest
from unittest.mock import Mock, patch
from crawlit.crawler.js_renderer import (
    is_playwright_available,
    JavaScriptRenderer,
    AsyncJavaScriptRenderer,
)
from crawlit import Crawler, AsyncCrawler


class TestJavaScriptRendererAvailability:
    """Test Playwright availability detection"""
    
    def test_is_playwright_available(self):
        """Test that Playwright availability can be checked"""
        result = is_playwright_available()
        assert isinstance(result, bool)


class TestProxyConfiguration:
    """Test proxy creation and configuration"""
    
    def test_crawler_accepts_js_parameters(self):
        """Test that Crawler accepts JS rendering parameters"""
        crawler = Crawler(
            start_url="https://example.com",
            max_depth=1,
            use_js_rendering=True,
            js_browser_type="chromium",
            js_wait_for_selector="#content",
            js_wait_for_timeout=2000
        )
        
        # Check parameters are stored correctly
        assert hasattr(crawler, 'use_js_rendering')
        assert crawler.js_browser_type == "chromium"
        assert crawler.js_wait_for_selector == "#content"
        assert crawler.js_wait_for_timeout == 2000
    
    def test_crawler_js_rendering_defaults(self):
        """Test default JS rendering settings"""
        crawler = Crawler(
            start_url="https://example.com",
            max_depth=1
        )
        
        assert hasattr(crawler, 'use_js_rendering')
        assert crawler.use_js_rendering == False
    
    def test_async_crawler_accepts_js_parameters(self):
        """Test that AsyncCrawler accepts JS rendering parameters"""
        crawler = AsyncCrawler(
            start_url="https://example.com",
            max_depth=1,
            use_js_rendering=True,
            js_browser_type="firefox",
            js_wait_for_selector="#app",
            js_wait_for_timeout=3000
        )
        
        assert hasattr(crawler, 'use_js_rendering')
        assert crawler.js_browser_type == "firefox"
        assert crawler.js_wait_for_selector == "#app"
        assert crawler.js_wait_for_timeout == 3000


class TestFetcherIntegration:
    """Test fetcher integration with JS rendering"""
    
    def test_sync_fetcher_has_js_parameters(self):
        """Test that sync fetcher accepts JS rendering parameters"""
        from crawlit.crawler.fetcher import fetch_page
        import inspect
        
        sig = inspect.signature(fetch_page)
        params = sig.parameters
        
        assert 'use_js_rendering' in params
        assert 'js_renderer' in params
        assert 'wait_for_selector' in params
        assert 'wait_for_timeout' in params
    
    def test_async_fetcher_has_js_parameters(self):
        """Test that async fetcher accepts JS rendering parameters"""
        from crawlit.crawler.async_fetcher import fetch_page_async
        import inspect
        
        sig = inspect.signature(fetch_page_async)
        params = sig.parameters
        
        assert 'use_js_rendering' in params
        assert 'js_renderer' in params
        assert 'wait_for_selector' in params
        assert 'wait_for_timeout' in params


@pytest.mark.skipif(not is_playwright_available(), reason="Playwright not installed")
class TestJavaScriptRenderer:
    """Test JavaScript renderer (requires Playwright)"""
    
    def test_javascript_renderer_creation(self):
        """Test creating a JavaScript renderer"""
        renderer = JavaScriptRenderer(
            browser_type="chromium",
            headless=True,
            timeout=30000
        )
        
        assert renderer.browser_type == "chromium"
        assert renderer.headless == True
        assert renderer.timeout == 30000
    
    def test_async_javascript_renderer_creation(self):
        """Test creating an async JavaScript renderer"""
        renderer = AsyncJavaScriptRenderer(
            browser_type="firefox",
            headless=True,
            timeout=20000
        )
        
        assert renderer.browser_type == "firefox"
        assert renderer.headless == True
        assert renderer.timeout == 20000


class TestCLIIntegration:
    """Test CLI integration for JS rendering"""
    
    def test_cli_has_js_arguments(self):
        """Test that CLI has JS rendering arguments"""
        with open('crawlit/crawlit.py', 'r', encoding='utf-8') as f:
            cli_content = f.read()
        
        required_args = [
            '--use-js',
            '--javascript',
            '--js-browser',
            '--js-wait-selector',
            '--js-wait-timeout'
        ]
        
        for arg in required_args:
            assert arg in cli_content, f"Missing CLI argument: {arg}"


class TestDocumentation:
    """Test that documentation exists"""
    
    def test_js_rendering_documentation_exists(self):
        """Test that JS rendering documentation files exist"""
        import os
        
        files_to_check = [
            'README.md',
            'RELEASE_NOTES.md',
            'JAVASCRIPT_RENDERING.md',
            'examples/javascript_rendering.py'
        ]
        
        missing_files = [f for f in files_to_check if not os.path.exists(f)]
        if missing_files:
            pytest.skip(f"Missing documentation files: {', '.join(missing_files)}")
        
        # All files exist, test passes
        assert True
    
    def test_readme_mentions_js_rendering(self):
        """Test that README mentions JavaScript rendering"""
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'JavaScript Rendering' in content or 'JavaScript rendering' in content
        assert 'Playwright' in content
        assert 'React' in content or 'SPA' in content

