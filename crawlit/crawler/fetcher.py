#!/usr/bin/env python3
"""
fetcher.py - HTTP request handling
"""

import logging
import time
from typing import Tuple, Union, Optional, Any, Dict
import requests
from crawlit.utils.errors import handle_fetch_error

logger = logging.getLogger(__name__)

# Check if Playwright is available for JavaScript rendering
try:
    from crawlit.crawler.js_renderer import JavaScriptRenderer, is_playwright_available
    PLAYWRIGHT_AVAILABLE = is_playwright_available()
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    JavaScriptRenderer = None

def fetch_page(
    url: str, 
    user_agent: str = "crawlit/2.0", 
    max_retries: int = 3, 
    timeout: int = 10,
    session: Optional[requests.Session] = None,
    use_js_rendering: bool = False,
    js_renderer: Optional[Any] = None,
    wait_for_selector: Optional[str] = None,
    wait_for_timeout: Optional[int] = None,
    proxy: Optional[Union[str, Dict[str, str]]] = None,
    proxy_manager: Optional[Any] = None
) -> Tuple[bool, Union[requests.Response, str], int]:
    """
    Fetch a web page with retries and proper error handling
    
    Args:
        url: The URL to fetch
        user_agent: User agent string to use in the request
        max_retries: Maximum number of retries on failure
        timeout: Request timeout in seconds
        session: Optional requests session to reuse
        use_js_rendering: Whether to use JavaScript rendering (Playwright)
        js_renderer: Optional JavaScriptRenderer instance
        wait_for_selector: CSS selector to wait for (JS rendering only)
        wait_for_timeout: Additional timeout after page load (JS rendering only)
        proxy: Proxy configuration (URL string or dict with 'http'/'https' keys)
        proxy_manager: Optional ProxyManager for automatic proxy rotation
        
    Returns:
        tuple: (success, response_or_error, status_code)
    """
    # Use JavaScript rendering if requested and available
    if use_js_rendering:
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("JavaScript rendering requested but Playwright not available. Falling back to standard fetch.")
        else:
            return _fetch_with_js_rendering(
                url, user_agent, max_retries, timeout * 1000,  # Convert to milliseconds
                js_renderer, wait_for_selector, wait_for_timeout
            )
    
    # Standard HTTP fetch (existing code)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Determine proxy to use
    proxies_dict = None
    current_proxy = None
    
    if proxy_manager:
        # Get proxy from manager
        current_proxy = proxy_manager.get_next_proxy()
        if current_proxy:
            proxies_dict = current_proxy.get_dict()
            logger.debug(f"Using proxy from manager: {current_proxy}")
    elif proxy:
        # Use provided proxy
        if isinstance(proxy, str):
            proxies_dict = {'http': proxy, 'https': proxy}
        else:
            proxies_dict = proxy
        logger.debug(f"Using provided proxy: {proxy}")
    
    retries = 0
    status_code = None
    
    while retries <= max_retries:
        try:
            logger.debug(f"Requesting {url} (attempt {retries + 1}/{max_retries + 1})")
            # Use provided session or create new request
            if session:
                response = session.get(
                    url,
                    timeout=timeout,
                    proxies=proxies_dict
                )
            else:
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=timeout,
                    proxies=proxies_dict
                )
            status_code = response.status_code
            
            # Check if the request was successful
            if response.status_code == 200:
                # Report success to proxy manager if using one
                if proxy_manager and current_proxy:
                    proxy_manager.report_success(current_proxy)
                return True, response, status_code
            # For 5xx server errors, retry if we haven't exceeded max retries
            elif 500 <= response.status_code < 600:
                logger.warning(f"HTTP Error {response.status_code} for {url}, will retry")
                retries += 1
                # If we've exceeded max retries, fail
                if retries > max_retries:
                    logger.warning(f"Max retries ({max_retries}) exceeded for {url}")
                    return False, f"HTTP Error: {response.status_code}", status_code
                # Exponential backoff before retry
                backoff_time = min(2 ** retries, 32)  # Cap at 32 seconds
                logger.debug(f"Waiting {backoff_time}s before retry (exponential backoff)")
                time.sleep(backoff_time)
            else:
                # For client errors (4xx) and other status codes, don't retry
                logger.warning(f"HTTP Error {response.status_code} for {url}")
                return False, f"HTTP Error: {response.status_code}", status_code
                
        except (requests.exceptions.Timeout, 
                requests.exceptions.ConnectionError,
                requests.exceptions.TooManyRedirects,
                requests.exceptions.HTTPError,
                requests.exceptions.RequestException) as e:
            # Use standardized error handling
            should_retry, error_message, error_status = handle_fetch_error(
                url, e, max_retries, retries
            )
            
            status_code = error_status or status_code
            logger.warning(f"{error_message} (attempt {retries + 1})")
            
            # Report failure to proxy manager
            if proxy_manager and current_proxy:
                proxy_manager.report_failure(current_proxy)
                # Get a new proxy for retry if available
                if retries < max_retries:
                    new_proxy = proxy_manager.get_next_proxy()
                    if new_proxy:
                        current_proxy = new_proxy
                        proxies_dict = current_proxy.get_dict()
                        logger.debug(f"Retrying with different proxy: {current_proxy}")
            
            if not should_retry:
                # Don't retry for certain errors (e.g., TooManyRedirects, 4xx)
                return False, error_message, status_code or 500
            
            retries += 1
            if retries > max_retries:
                return False, error_message, status_code or 429
            
            # Exponential backoff before retry
            backoff_time = min(2 ** retries, 32)  # Cap at 32 seconds
            logger.debug(f"Waiting {backoff_time}s before retry (exponential backoff)")
            time.sleep(backoff_time)
    
    # If we've exhausted all retries
    return False, f"Max retries ({max_retries}) exceeded", status_code or 429

# Add fetch_url as an alias for fetch_page to make tests pass
# This provides backward compatibility with test code
def fetch_url(
    url: str, 
    user_agent: str = "crawlit/2.0", 
    max_retries: int = 3, 
    timeout: int = 10
) -> requests.Response:
    """
    Alias for fetch_page - maintained for backward compatibility with tests
    
    Note: Tests expect this function to return just the response object,
    unlike fetch_page which returns (success, response, status_code)
    """
    success, response_or_error, status_code = fetch_page(url, user_agent, max_retries, timeout)
    
    # Return just the response object as expected by tests
    if success:
        # For success case, tests expect response object
        return response_or_error
    else:
        # For error case, tests expect an exception to be raised
        if isinstance(response_or_error, str) and "HTTP Error" in response_or_error:
            # Extract status code from error message and raise proper exception
            raise requests.exceptions.HTTPError(response_or_error)
        else:
            # For other errors, raise a generic exception
            raise requests.exceptions.RequestException(response_or_error)


def _fetch_with_js_rendering(
    url: str,
    user_agent: str,
    max_retries: int,
    timeout: int,
    js_renderer: Optional[Any],
    wait_for_selector: Optional[str],
    wait_for_timeout: Optional[int]
) -> Tuple[bool, Any, int]:
    """
    Fetch a page using JavaScript rendering (Playwright).
    
    Args:
        url: The URL to fetch
        user_agent: User agent string
        max_retries: Maximum retry attempts
        timeout: Timeout in milliseconds
        js_renderer: Optional JavaScriptRenderer instance to reuse
        wait_for_selector: CSS selector to wait for
        wait_for_timeout: Additional timeout after page load
        
    Returns:
        Tuple of (success, response_or_error, status_code)
    """
    should_close_renderer = False
    
    try:
        # Use provided renderer or create a new one
        if js_renderer is None:
            js_renderer = JavaScriptRenderer(
                user_agent=user_agent,
                timeout=timeout,
                headless=True
            )
            should_close_renderer = True
            js_renderer.start()
            
        retries = 0
        while retries <= max_retries:
            result = js_renderer.render(
                url,
                wait_for_selector=wait_for_selector,
                wait_for_timeout=wait_for_timeout
            )
            
            if result["success"]:
                # Create a mock response object from the rendered content
                class JSResponse:
                    """Mock response object for JS-rendered content"""
                    def __init__(self, html, url, status_code):
                        self.text = html
                        self.content = html.encode('utf-8') if html else b''
                        self.url = url
                        self.status_code = status_code
                        self.headers = {"Content-Type": "text/html; charset=utf-8"}
                        self.ok = 200 <= status_code < 300
                        
                    def raise_for_status(self):
                        if not self.ok:
                            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")
                
                response_obj = JSResponse(
                    result["html"],
                    result["url"],
                    result["status_code"]
                )
                return True, response_obj, result["status_code"]
            else:
                # Retry on server errors or timeout
                if result["status_code"] >= 500 or result["status_code"] == 0:
                    retries += 1
                    if retries <= max_retries:
                        logger.warning(f"JS rendering failed for {url}, retrying (attempt {retries}/{max_retries})")
                        backoff_time = min(2 ** retries, 32)  # Exponential backoff, cap at 32 seconds
                        logger.debug(f"Waiting {backoff_time}s before retry (exponential backoff)")
                        time.sleep(backoff_time)
                        continue
                        
                # Don't retry on client errors
                return False, result["error"], result["status_code"]
                
        # Max retries exceeded
        return False, f"Max retries ({max_retries}) exceeded", 0
        
    except Exception as e:
        logger.exception(f"Unexpected error in JS rendering for {url}: {e}")
        return False, f"JavaScript rendering error: {str(e)}", 0
    finally:
        # Close renderer if we created it
        if should_close_renderer and js_renderer:
            try:
                js_renderer.close()
            except Exception as e:
                logger.warning(f"Error closing JS renderer: {e}")