#!/usr/bin/env python3
"""
js_renderer.py - JavaScript rendering support using Playwright

Provides both synchronous and asynchronous JavaScript rendering capabilities
for Single Page Applications (SPAs) and JavaScript-heavy websites.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Union
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError
from playwright.sync_api import sync_playwright, Browser as SyncBrowser, BrowserContext as SyncBrowserContext, Page as SyncPage, Error as SyncPlaywrightError

logger = logging.getLogger(__name__)


class JavaScriptRenderer:
    """
    Synchronous JavaScript renderer using Playwright.
    
    Supports rendering JavaScript-heavy websites including React, Vue, Angular,
    and other SPA frameworks.
    """
    
    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        timeout: int = 30000,
        wait_until: str = "networkidle",
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        javascript_enabled: bool = True,
        ignore_https_errors: bool = False,
        extra_http_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the JavaScript renderer.
        
        Args:
            browser_type: Browser to use ('chromium', 'firefox', or 'webkit')
            headless: Whether to run browser in headless mode
            timeout: Page load timeout in milliseconds
            wait_until: When to consider page loaded ('load', 'domcontentloaded', 'networkidle')
            user_agent: Custom user agent string
            viewport: Viewport size dict with 'width' and 'height' keys
            javascript_enabled: Whether to enable JavaScript execution
            ignore_https_errors: Whether to ignore HTTPS certificate errors
            extra_http_headers: Additional HTTP headers to send with requests
        """
        self.browser_type = browser_type
        self.headless = headless
        self.timeout = timeout
        self.wait_until = wait_until
        self.user_agent = user_agent
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.javascript_enabled = javascript_enabled
        self.ignore_https_errors = ignore_https_errors
        self.extra_http_headers = extra_http_headers
        
        self.playwright = None
        self.browser = None
        self.context = None
        
    def __enter__(self):
        """Context manager entry - start Playwright and browser."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
        
    def start(self):
        """Start Playwright and launch browser."""
        if self.playwright is None:
            logger.debug("Starting Playwright (sync)")
            self.playwright = sync_playwright().start()
            
            # Select browser type
            if self.browser_type == "firefox":
                browser_launcher = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium
                
            logger.debug(f"Launching {self.browser_type} browser (headless={self.headless})")
            self.browser = browser_launcher.launch(headless=self.headless)
            
            # Create browser context with options
            context_options = {
                "viewport": self.viewport,
                "ignore_https_errors": self.ignore_https_errors,
                "java_script_enabled": self.javascript_enabled
            }
            
            if self.user_agent:
                context_options["user_agent"] = self.user_agent
                
            if self.extra_http_headers:
                context_options["extra_http_headers"] = self.extra_http_headers
                
            self.context = self.browser.new_context(**context_options)
            logger.debug("Browser context created")
            
    def close(self):
        """Close browser and stop Playwright."""
        if self.context:
            self.context.close()
            self.context = None
            
        if self.browser:
            self.browser.close()
            self.browser = None
            
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
            
        logger.debug("Playwright closed")
        
    def render(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        wait_for_timeout: Optional[int] = None,
        execute_script: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Render a URL and return the fully loaded page content.
        
        Args:
            url: The URL to render
            wait_for_selector: Optional CSS selector to wait for before returning
            wait_for_timeout: Additional timeout to wait after page load (milliseconds)
            execute_script: Optional JavaScript to execute on the page
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating if rendering succeeded
                - html: The rendered HTML content (if successful)
                - url: The final URL after redirects
                - status_code: HTTP status code
                - error: Error message (if failed)
        """
        if not self.browser:
            self.start()
            
        page = None
        try:
            logger.debug(f"Creating new page for URL: {url}")
            page = self.context.new_page()
            
            # Set default timeout
            page.set_default_timeout(self.timeout)
            
            logger.debug(f"Navigating to {url} (wait_until={self.wait_until})")
            response = page.goto(url, wait_until=self.wait_until, timeout=self.timeout)
            
            if response is None:
                logger.warning(f"No response received for {url}")
                return {
                    "success": False,
                    "html": None,
                    "url": url,
                    "status_code": 0,
                    "error": "No response received"
                }
                
            status_code = response.status
            logger.debug(f"Page loaded with status {status_code}")
            
            # Wait for specific selector if provided
            if wait_for_selector:
                logger.debug(f"Waiting for selector: {wait_for_selector}")
                try:
                    page.wait_for_selector(wait_for_selector, timeout=self.timeout)
                except Exception as e:
                    logger.warning(f"Selector {wait_for_selector} not found: {e}")
                    
            # Additional wait time if specified
            if wait_for_timeout:
                logger.debug(f"Waiting additional {wait_for_timeout}ms")
                page.wait_for_timeout(wait_for_timeout)
                
            # Execute custom JavaScript if provided
            if execute_script:
                logger.debug("Executing custom JavaScript")
                try:
                    page.evaluate(execute_script)
                except Exception as e:
                    logger.warning(f"Script execution failed: {e}")
                    
            # Get the fully rendered HTML
            html_content = page.content()
            final_url = page.url
            
            logger.debug(f"Successfully rendered {url} ({len(html_content)} bytes)")
            
            return {
                "success": True,
                "html": html_content,
                "url": final_url,
                "status_code": status_code,
                "error": None
            }
            
        except SyncPlaywrightError as e:
            logger.error(f"Playwright error rendering {url}: {e}")
            return {
                "success": False,
                "html": None,
                "url": url,
                "status_code": 0,
                "error": f"Playwright error: {str(e)}"
            }
        except Exception as e:
            logger.exception(f"Unexpected error rendering {url}: {e}")
            return {
                "success": False,
                "html": None,
                "url": url,
                "status_code": 0,
                "error": f"Unexpected error: {str(e)}"
            }
        finally:
            if page:
                page.close()
    
    def capture_screenshot(
        self,
        url: str,
        filepath: str,
        wait_for_selector: Optional[str] = None,
        wait_for_timeout: Optional[int] = None,
        full_page: bool = True,
        screenshot_type: str = "png"
    ) -> Dict[str, Any]:
        """
        Capture a screenshot of a rendered page.
        
        Args:
            url: The URL to screenshot
            filepath: Path to save the screenshot
            wait_for_selector: Optional CSS selector to wait for before capturing
            wait_for_timeout: Additional timeout to wait after page load (milliseconds)
            full_page: Whether to capture the full scrollable page (default: True)
            screenshot_type: Image format ('png' or 'jpeg')
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating if screenshot succeeded
                - filepath: Path where screenshot was saved
                - url: The final URL after redirects
                - error: Error message (if failed)
        """
        if not self.browser:
            self.start()
        
        page = None
        try:
            logger.debug(f"Creating new page for screenshot: {url}")
            page = self.context.new_page()
            
            # Set default timeout
            page.set_default_timeout(self.timeout)
            
            logger.debug(f"Navigating to {url} for screenshot")
            response = page.goto(url, wait_until=self.wait_until, timeout=self.timeout)
            
            if response is None:
                return {
                    "success": False,
                    "filepath": None,
                    "url": url,
                    "error": "No response received"
                }
            
            # Wait for specific selector if provided
            if wait_for_selector:
                logger.debug(f"Waiting for selector: {wait_for_selector}")
                try:
                    page.wait_for_selector(wait_for_selector, timeout=self.timeout)
                except Exception as e:
                    logger.warning(f"Selector {wait_for_selector} not found: {e}")
            
            # Additional wait time if specified
            if wait_for_timeout:
                logger.debug(f"Waiting additional {wait_for_timeout}ms before screenshot")
                page.wait_for_timeout(wait_for_timeout)
            
            # Capture screenshot
            screenshot_options = {
                "path": filepath,
                "full_page": full_page,
                "type": screenshot_type
            }
            
            page.screenshot(**screenshot_options)
            final_url = page.url
            
            logger.info(f"Screenshot saved: {filepath} (url={url})")
            
            return {
                "success": True,
                "filepath": filepath,
                "url": final_url,
                "error": None
            }
            
        except SyncPlaywrightError as e:
            logger.error(f"Playwright error capturing screenshot {url}: {e}")
            return {
                "success": False,
                "filepath": None,
                "url": url,
                "error": f"Playwright error: {str(e)}"
            }
        except Exception as e:
            logger.exception(f"Unexpected error capturing screenshot {url}: {e}")
            return {
                "success": False,
                "filepath": None,
                "url": url,
                "error": f"Unexpected error: {str(e)}"
            }
        finally:
            if page:
                page.close()


class AsyncJavaScriptRenderer:
    """
    Asynchronous JavaScript renderer using Playwright.
    
    Supports rendering JavaScript-heavy websites including React, Vue, Angular,
    and other SPA frameworks in async contexts.
    """
    
    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        timeout: int = 30000,
        wait_until: str = "networkidle",
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        javascript_enabled: bool = True,
        ignore_https_errors: bool = False,
        extra_http_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the asynchronous JavaScript renderer.
        
        Args:
            browser_type: Browser to use ('chromium', 'firefox', or 'webkit')
            headless: Whether to run browser in headless mode
            timeout: Page load timeout in milliseconds
            wait_until: When to consider page loaded ('load', 'domcontentloaded', 'networkidle')
            user_agent: Custom user agent string
            viewport: Viewport size dict with 'width' and 'height' keys
            javascript_enabled: Whether to enable JavaScript execution
            ignore_https_errors: Whether to ignore HTTPS certificate errors
            extra_http_headers: Additional HTTP headers to send with requests
        """
        self.browser_type = browser_type
        self.headless = headless
        self.timeout = timeout
        self.wait_until = wait_until
        self.user_agent = user_agent
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.javascript_enabled = javascript_enabled
        self.ignore_https_errors = ignore_https_errors
        self.extra_http_headers = extra_http_headers
        
        self.playwright = None
        self.browser = None
        self.context = None
        
    async def __aenter__(self):
        """Async context manager entry - start Playwright and browser."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        await self.close()
        
    async def start(self):
        """Start Playwright and launch browser asynchronously."""
        if self.playwright is None:
            logger.debug("Starting Playwright (async)")
            self.playwright = await async_playwright().start()
            
            # Select browser type
            if self.browser_type == "firefox":
                browser_launcher = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium
                
            logger.debug(f"Launching {self.browser_type} browser (headless={self.headless})")
            self.browser = await browser_launcher.launch(headless=self.headless)
            
            # Create browser context with options
            context_options = {
                "viewport": self.viewport,
                "ignore_https_errors": self.ignore_https_errors,
                "java_script_enabled": self.javascript_enabled
            }
            
            if self.user_agent:
                context_options["user_agent"] = self.user_agent
                
            if self.extra_http_headers:
                context_options["extra_http_headers"] = self.extra_http_headers
                
            self.context = await self.browser.new_context(**context_options)
            logger.debug("Browser context created")
            
    async def close(self):
        """Close browser and stop Playwright asynchronously."""
        if self.context:
            await self.context.close()
            self.context = None
            
        if self.browser:
            await self.browser.close()
            self.browser = None
            
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            
        logger.debug("Playwright closed")
        
    async def render(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        wait_for_timeout: Optional[int] = None,
        execute_script: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Render a URL asynchronously and return the fully loaded page content.
        
        Args:
            url: The URL to render
            wait_for_selector: Optional CSS selector to wait for before returning
            wait_for_timeout: Additional timeout to wait after page load (milliseconds)
            execute_script: Optional JavaScript to execute on the page
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating if rendering succeeded
                - html: The rendered HTML content (if successful)
                - url: The final URL after redirects
                - status_code: HTTP status code
                - error: Error message (if failed)
        """
        if not self.browser:
            await self.start()
            
        page = None
        try:
            logger.debug(f"Creating new page for URL: {url}")
            page = await self.context.new_page()
            
            # Set default timeout
            page.set_default_timeout(self.timeout)
            
            logger.debug(f"Navigating to {url} (wait_until={self.wait_until})")
            response = await page.goto(url, wait_until=self.wait_until, timeout=self.timeout)
            
            if response is None:
                logger.warning(f"No response received for {url}")
                return {
                    "success": False,
                    "html": None,
                    "url": url,
                    "status_code": 0,
                    "error": "No response received"
                }
                
            status_code = response.status
            logger.debug(f"Page loaded with status {status_code}")
            
            # Wait for specific selector if provided
            if wait_for_selector:
                logger.debug(f"Waiting for selector: {wait_for_selector}")
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=self.timeout)
                except Exception as e:
                    logger.warning(f"Selector {wait_for_selector} not found: {e}")
                    
            # Additional wait time if specified
            if wait_for_timeout:
                logger.debug(f"Waiting additional {wait_for_timeout}ms")
                await page.wait_for_timeout(wait_for_timeout)
                
            # Execute custom JavaScript if provided
            if execute_script:
                logger.debug("Executing custom JavaScript")
                try:
                    await page.evaluate(execute_script)
                except Exception as e:
                    logger.warning(f"Script execution failed: {e}")
                    
            # Get the fully rendered HTML
            html_content = await page.content()
            final_url = page.url
            
            logger.debug(f"Successfully rendered {url} ({len(html_content)} bytes)")
            
            return {
                "success": True,
                "html": html_content,
                "url": final_url,
                "status_code": status_code,
                "error": None
            }
            
        except PlaywrightError as e:
            logger.error(f"Playwright error rendering {url}: {e}")
            return {
                "success": False,
                "html": None,
                "url": url,
                "status_code": 0,
                "error": f"Playwright error: {str(e)}"
            }
        except Exception as e:
            logger.exception(f"Unexpected error rendering {url}: {e}")
            return {
                "success": False,
                "html": None,
                "url": url,
                "status_code": 0,
                "error": f"Unexpected error: {str(e)}"
            }
        finally:
            if page:
                await page.close()
    
    async def capture_screenshot(
        self,
        url: str,
        filepath: str,
        wait_for_selector: Optional[str] = None,
        wait_for_timeout: Optional[int] = None,
        full_page: bool = True,
        screenshot_type: str = "png"
    ) -> Dict[str, Any]:
        """
        Capture a screenshot of a rendered page (async).
        
        Args:
            url: The URL to screenshot
            filepath: Path to save the screenshot
            wait_for_selector: Optional CSS selector to wait for before capturing
            wait_for_timeout: Additional timeout to wait after page load (milliseconds)
            full_page: Whether to capture the full scrollable page (default: True)
            screenshot_type: Image format ('png' or 'jpeg')
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating if screenshot succeeded
                - filepath: Path where screenshot was saved
                - url: The final URL after redirects
                - error: Error message (if failed)
        """
        if not self.browser:
            await self.start()
        
        page = None
        try:
            logger.debug(f"Creating new page for screenshot: {url}")
            page = await self.context.new_page()
            
            # Set default timeout
            page.set_default_timeout(self.timeout)
            
            logger.debug(f"Navigating to {url} for screenshot")
            response = await page.goto(url, wait_until=self.wait_until, timeout=self.timeout)
            
            if response is None:
                return {
                    "success": False,
                    "filepath": None,
                    "url": url,
                    "error": "No response received"
                }
            
            # Wait for specific selector if provided
            if wait_for_selector:
                logger.debug(f"Waiting for selector: {wait_for_selector}")
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=self.timeout)
                except Exception as e:
                    logger.warning(f"Selector {wait_for_selector} not found: {e}")
            
            # Additional wait time if specified
            if wait_for_timeout:
                logger.debug(f"Waiting additional {wait_for_timeout}ms before screenshot")
                await page.wait_for_timeout(wait_for_timeout)
            
            # Capture screenshot
            screenshot_options = {
                "path": filepath,
                "full_page": full_page,
                "type": screenshot_type
            }
            
            await page.screenshot(**screenshot_options)
            final_url = page.url
            
            logger.info(f"Screenshot saved: {filepath} (url={url})")
            
            return {
                "success": True,
                "filepath": filepath,
                "url": final_url,
                "error": None
            }
            
        except PlaywrightError as e:
            logger.error(f"Playwright error capturing screenshot {url}: {e}")
            return {
                "success": False,
                "filepath": None,
                "url": url,
                "error": f"Playwright error: {str(e)}"
            }
        except Exception as e:
            logger.exception(f"Unexpected error capturing screenshot {url}: {e}")
            return {
                "success": False,
                "filepath": None,
                "url": url,
                "error": f"Unexpected error: {str(e)}"
            }
        finally:
            if page:
                await page.close()


def is_playwright_available() -> bool:
    """
    Check if Playwright is installed and browsers are available.
    
    Returns:
        bool: True if Playwright is available, False otherwise
    """
    try:
        import playwright
        return True
    except ImportError:
        return False

