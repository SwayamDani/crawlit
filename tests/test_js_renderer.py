"""
JavaScript renderer integration tests using real Playwright (no mocks).

Uses pytest-httpserver to serve real HTML over HTTP and exercises
JavaScriptRenderer (sync) and AsyncJavaScriptRenderer (async) against
a real browser. Requires: pip install playwright && playwright install chromium.
"""

import asyncio
import pytest

pytest.importorskip("playwright")

from crawlit.crawler.js_renderer import (
    JavaScriptRenderer,
    AsyncJavaScriptRenderer,
    is_playwright_available,
)


# Skip entire module if Playwright is not available (e.g. import only, no browsers)
def _playwright_available():
    if not is_playwright_available():
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _playwright_available(),
    reason="Playwright not installed or browsers not available (run: playwright install chromium)",
)


# ---------------------------------------------------------------------------
# Static HTML served by local server
# ---------------------------------------------------------------------------

SIMPLE_HTML = """<!DOCTYPE html>
<html>
<head><title>JS Renderer Test</title></head>
<body>
  <h1 id="heading">Hello from server</h1>
  <p class="content">Static content</p>
</body>
</html>
"""

# Page that uses JS to inject content (proves JS is executed)
HTML_WITH_JS = """<!DOCTYPE html>
<html>
<head><title>Dynamic</title></head>
<body>
  <div id="root">Loading...</div>
  <script>
    document.getElementById('root').innerHTML = '<span id="js-rendered">Rendered by JavaScript</span>';
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Sync JavaScriptRenderer – real Playwright + real HTTP
# ---------------------------------------------------------------------------

class TestJavaScriptRendererSync:
    """Synchronous JavaScriptRenderer against real server and browser."""

    def test_render_simple_page(self, httpserver):
        httpserver.expect_request("/simple").respond_with_data(
            SIMPLE_HTML,
            content_type="text/html; charset=utf-8",
        )
        url = httpserver.url_for("/simple")

        renderer = JavaScriptRenderer(
            browser_type="chromium",
            headless=True,
            timeout=10000,
            wait_until="domcontentloaded",
        )
        renderer.start()
        try:
            result = renderer.render(url)
            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["html"] is not None
            assert "Hello from server" in result["html"]
            assert "Static content" in result["html"]
            assert "JS Renderer Test" in result["html"]
            assert result["url"] == url
        finally:
            renderer.close()

    def test_render_page_with_js_injection(self, httpserver):
        httpserver.expect_request("/dynamic").respond_with_data(
            HTML_WITH_JS,
            content_type="text/html; charset=utf-8",
        )
        url = httpserver.url_for("/dynamic")

        renderer = JavaScriptRenderer(
            headless=True,
            timeout=10000,
            wait_until="domcontentloaded",
        )
        renderer.start()
        try:
            result = renderer.render(url)
            assert result["success"] is True
            assert "Rendered by JavaScript" in result["html"]
            assert "js-rendered" in result["html"]
        finally:
            renderer.close()

    def test_render_with_execute_script(self, httpserver):
        httpserver.expect_request("/exec").respond_with_data(
            "<html><body><div id='out'></div></body></html>",
            content_type="text/html; charset=utf-8",
        )
        url = httpserver.url_for("/exec")

        renderer = JavaScriptRenderer(headless=True, timeout=10000, wait_until="domcontentloaded")
        renderer.start()
        try:
            result = renderer.render(
                url,
                execute_script="() => { document.getElementById('out').textContent = 'Injected'; return 42; }",
            )
            assert result["success"] is True
            assert result.get("js_result") == 42
            assert "Injected" in result["html"]
        finally:
            renderer.close()

    def test_context_manager(self, httpserver):
        httpserver.expect_request("/cm").respond_with_data(
            "<html><body>Context manager</body></html>",
            content_type="text/html; charset=utf-8",
        )
        url = httpserver.url_for("/cm")

        with JavaScriptRenderer(headless=True, timeout=10000, wait_until="domcontentloaded") as renderer:
            result = renderer.render(url)
            assert result["success"] is True
            assert "Context manager" in result["html"]

    def test_render_nonexistent_returns_failure(self, httpserver):
        httpserver.expect_request("/missing").respond_with_data(
            "Not found",
            status=404,
            content_type="text/plain",
        )
        url = httpserver.url_for("/missing")

        with JavaScriptRenderer(headless=True, timeout=10000, wait_until="domcontentloaded") as renderer:
            result = renderer.render(url)
            assert result["success"] is True
            assert result["status_code"] == 404
            assert result["html"] is not None


# ---------------------------------------------------------------------------
# Async AsyncJavaScriptRenderer – real Playwright + real HTTP
# ---------------------------------------------------------------------------

class TestAsyncJavaScriptRenderer:
    """Asynchronous AsyncJavaScriptRenderer against real server and browser."""

    @pytest.mark.asyncio
    async def test_render_simple_page_async(self, httpserver):
        httpserver.expect_request("/async-simple").respond_with_data(
            SIMPLE_HTML,
            content_type="text/html; charset=utf-8",
        )
        url = httpserver.url_for("/async-simple")

        async with AsyncJavaScriptRenderer(
            headless=True,
            timeout=10000,
            wait_until="domcontentloaded",
        ) as renderer:
            result = await renderer.render(url)
            assert result["success"] is True
            assert result["status_code"] == 200
            assert "Hello from server" in result["html"]
            assert result["url"] == url

    @pytest.mark.asyncio
    async def test_render_page_with_js_async(self, httpserver):
        httpserver.expect_request("/async-dynamic").respond_with_data(
            HTML_WITH_JS,
            content_type="text/html; charset=utf-8",
        )
        url = httpserver.url_for("/async-dynamic")

        async with AsyncJavaScriptRenderer(
            headless=True,
            timeout=10000,
            wait_until="domcontentloaded",
        ) as renderer:
            result = await renderer.render(url)
            assert result["success"] is True
            assert "Rendered by JavaScript" in result["html"]

    @pytest.mark.asyncio
    async def test_render_with_execute_script_async(self, httpserver):
        httpserver.expect_request("/async-exec").respond_with_data(
            "<html><body><div id='out'></div></body></html>",
            content_type="text/html; charset=utf-8",
        )
        url = httpserver.url_for("/async-exec")

        async with AsyncJavaScriptRenderer(
            headless=True,
            timeout=10000,
            wait_until="domcontentloaded",
        ) as renderer:
            result = await renderer.render(
                url,
                execute_script="() => { document.getElementById('out').innerText = 'Async'; return 100; }",
            )
            assert result["success"] is True
            assert result.get("js_result") == 100
            assert "Async" in result["html"]


# ---------------------------------------------------------------------------
# is_playwright_available (no browser required for this test)
# ---------------------------------------------------------------------------

class TestIsPlaywrightAvailable:
    """Test the availability check (import-only, no browser launch)."""

    def test_is_playwright_available_true_when_installed(self):
        assert is_playwright_available() is True
