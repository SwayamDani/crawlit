#!/usr/bin/env python3
"""
Integration tests for JavaScript rendering with real SPAs
"""

import pytest
import asyncio


@pytest.mark.playwright
@pytest.mark.integration
class TestJavaScriptRendering:
    """Tests for JavaScript rendering with Playwright."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    def test_render_react_spa(self):
        """Test rendering a React single-page application."""
        from crawlit.crawler.js_renderer import JavaScriptRenderer
        
        # Use a public React SPA example
        url = "https://react-shopping-cart-67954.firebaseapp.com/"
        
        renderer = JavaScriptRenderer(headless=True, timeout=10000)
        
        try:
            result = renderer.render(url, wait_for_selector="body")
            
            assert result['success']
            assert len(result['html']) > 0
            
            # React apps should have rendered content
            assert 'react' in result['html'].lower() or len(result['html']) > 1000
        finally:
            renderer.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    def test_render_with_wait_for_network(self):
        """Test waiting for network idle."""
        from crawlit.crawler.js_renderer import JavaScriptRenderer
        
        url = "https://example.com"
        
        renderer = JavaScriptRenderer(headless=True)
        
        try:
            result = renderer.render(
                url,
                wait_for_network_idle=True,
                wait_for_timeout=3000
            )
            
            assert result['success']
            assert len(result['html']) > 0
        finally:
            renderer.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    def test_screenshot_capture(self):
        """Test capturing screenshots."""
        from crawlit.crawler.js_renderer import JavaScriptRenderer
        import tempfile
        from pathlib import Path
        
        url = "https://example.com"
        
        renderer = JavaScriptRenderer(headless=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            screenshot_path = Path(tmpdir) / "screenshot.png"
            
            try:
                result = renderer.render(
                    url,
                    screenshot_path=str(screenshot_path)
                )
                
                assert result['success']
                assert screenshot_path.exists()
                
                # Screenshot should have reasonable size
                assert screenshot_path.stat().st_size > 1000
            finally:
                renderer.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    def test_execute_custom_javascript(self):
        """Test executing custom JavaScript."""
        from crawlit.crawler.js_renderer import JavaScriptRenderer
        
        url = "https://example.com"
        
        renderer = JavaScriptRenderer(headless=True)
        
        try:
            result = renderer.render(
                url,
                execute_js="document.title"
            )
            
            assert result['success']
            assert 'js_result' in result
        finally:
            renderer.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    async def test_async_rendering(self):
        """Test async JavaScript rendering."""
        from crawlit.crawler.js_renderer import AsyncJavaScriptRenderer
        
        url = "https://example.com"
        
        renderer = AsyncJavaScriptRenderer(headless=True, timeout=10000)
        
        try:
            result = await renderer.render(url)
            
            assert result['success']
            assert len(result['html']) > 0
        finally:
            await renderer.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    async def test_concurrent_async_rendering(self):
        """Test concurrent async rendering of multiple pages."""
        from crawlit.crawler.js_renderer import AsyncJavaScriptRenderer
        
        urls = [
            "https://example.com",
            "https://www.w3.org",
            "https://httpbin.org"
        ]
        
        renderer = AsyncJavaScriptRenderer(headless=True, timeout=10000)
        
        try:
            tasks = [renderer.render(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # At least some should succeed
            successful = [r for r in results if isinstance(r, dict) and r.get('success')]
            assert len(successful) > 0
        finally:
            await renderer.close()


@pytest.mark.integration
class TestJavaScriptRenderingEdgeCases:
    """Edge case tests for JavaScript rendering."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    def test_render_timeout_handling(self):
        """Test handling of render timeouts."""
        from crawlit.crawler.js_renderer import JavaScriptRenderer
        
        # Use a slow-loading page or timeout quickly
        url = "https://example.com"
        
        renderer = JavaScriptRenderer(headless=True, timeout=100)  # Very short timeout
        
        try:
            result = renderer.render(url)
            
            # Should either succeed quickly or handle timeout gracefully
            assert 'success' in result
            
            if not result['success']:
                assert 'error' in result
        finally:
            renderer.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    def test_render_invalid_url(self):
        """Test rendering with invalid URL."""
        from crawlit.crawler.js_renderer import JavaScriptRenderer
        
        renderer = JavaScriptRenderer(headless=True)
        
        try:
            result = renderer.render("not-a-valid-url")
            
            assert not result['success']
            assert 'error' in result
        finally:
            renderer.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("playwright", minversion="1.40.0"),
        reason="Playwright not installed"
    )
    def test_render_page_with_infinite_scroll(self):
        """Test handling pages with infinite scroll."""
        from crawlit.crawler.js_renderer import JavaScriptRenderer
        
        # Example: Twitter-like infinite scroll
        # This is a challenge - need to scroll to load more
        
        renderer = JavaScriptRenderer(headless=True, timeout=10000)
        
        try:
            # For now, just test that it doesn't hang
            result = renderer.render(
                "https://example.com",
                wait_for_timeout=2000
            )
            
            assert result['success']
        finally:
            renderer.close()

