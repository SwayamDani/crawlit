#!/usr/bin/env python3
"""
async_fetcher.py - Asynchronous HTTP request handling
"""

import logging
import aiohttp
import asyncio
from typing import Union, Dict, Tuple, Any, Optional
from crawlit.utils.errors import handle_fetch_error
from crawlit.utils.url_filter import sanitize_url_for_log

logger = logging.getLogger(__name__)

# Check if Playwright is available for JavaScript rendering
try:
    from crawlit.crawler.js_renderer import AsyncJavaScriptRenderer, is_playwright_available
    PLAYWRIGHT_AVAILABLE = is_playwright_available()
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    AsyncJavaScriptRenderer = None

def _detect_charset_from_bytes(raw: bytes) -> Optional[str]:
    """
    Attempt to detect charset by scanning the first ~4 KB of raw HTML bytes for
    <meta charset="..."> or <meta http-equiv="content-type" content="...charset=...">
    tags.  Returns the charset name string, or None if not found.
    """
    import re as _re
    # Scan only the first 4 KB to keep it fast
    head = raw[:4096]
    # Try as latin-1 (every byte is valid) so we can regex-scan
    try:
        snippet = head.decode('latin-1')
    except Exception:
        return None

    # HTML5: <meta charset="utf-8">
    m = _re.search(r'<meta[^>]+charset\s*=\s*["\']?\s*([\w-]+)', snippet, _re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Legacy: <meta http-equiv="content-type" content="text/html; charset=utf-8">
    m = _re.search(r'charset\s*=\s*([\w-]+)', snippet, _re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return None


async def fetch_page_async(
    url: str,
    user_agent: str = "crawlit/1.0",
    max_retries: int = 3,
    timeout: int = 10,
    session: Optional[aiohttp.ClientSession] = None,
    use_js_rendering: bool = False,
    js_renderer: Optional[Any] = None,
    wait_for_selector: Optional[str] = None,
    wait_for_timeout: Optional[int] = None,
    proxy: Optional[str] = None,
    proxy_manager: Optional[Any] = None,
    max_response_bytes: Optional[int] = None,
):
    """
    Asynchronously fetch a web page with retries and proper error handling

    Args:
        url: The URL to fetch
        user_agent: User agent string to use in the request
        max_retries: Maximum number of retries on failure
        timeout: Request timeout in seconds
        session: Optional aiohttp session to reuse
        use_js_rendering: Whether to use JavaScript rendering (Playwright)
        js_renderer: Optional AsyncJavaScriptRenderer instance
        wait_for_selector: CSS selector to wait for (JS rendering only)
        wait_for_timeout: Additional timeout after page load (JS rendering only)
        proxy: Proxy URL string
        proxy_manager: Optional ProxyManager for automatic proxy rotation
        max_response_bytes: Maximum response body size in bytes. Responses
            larger than this limit are rejected to prevent memory exhaustion.
            ``None`` (default) imposes no limit.

    Returns:
        tuple: (success, response_or_error, status_code)
    """
    # Use JavaScript rendering if requested and available
    if use_js_rendering:
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("JavaScript rendering requested but Playwright not available. Falling back to standard fetch.")
        else:
            return await _fetch_with_js_rendering(
                url, user_agent, max_retries, timeout * 1000,  # Convert to milliseconds
                js_renderer, wait_for_selector, wait_for_timeout
            )
    
    # Determine proxy to use
    proxy_url = None
    current_proxy = None
    
    if proxy_manager:
        # Get proxy from manager
        current_proxy = proxy_manager.get_next_proxy()
        if current_proxy:
            proxy_url = current_proxy.get_url()
            logger.debug(f"Using proxy from manager: {current_proxy}")
    elif proxy:
        # Use provided proxy
        proxy_url = proxy
        logger.debug(f"Using provided proxy: {proxy}")
    
    # Standard HTTP fetch (existing code)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    retries = 0
    status_code = None
    
    timeout_obj = aiohttp.ClientTimeout(total=timeout)

    # Create a single session for all retry attempts when none is provided.
    # This reuses the underlying TCP connection pool instead of tearing it
    # down and rebuilding it on every attempt (A1 fix).
    _own_session: Optional[aiohttp.ClientSession] = None
    if not session:
        _own_session = aiohttp.ClientSession(timeout=timeout_obj, headers=headers)

    try:
      while retries <= max_retries:
        _session = session if session else _own_session
        try:
            logger.debug(f"Requesting {sanitize_url_for_log(url)} (attempt {retries + 1}/{max_retries + 1})")

            request_kwargs: Dict[str, Any] = {"proxy": proxy_url}
            if not session:
                # headers already baked into _own_session; pass nothing extra
                pass

            async with _session.get(url, **request_kwargs) as response:
                status_code = response.status

                if response.status == 200:
                    # Enforce optional response body size limit via Content-Length header
                    if max_response_bytes is not None:
                        content_length_hdr = response.headers.get('Content-Length')
                        if content_length_hdr and int(content_length_hdr) > max_response_bytes:
                            logger.warning(
                                f"Response for {url} exceeds size limit "
                                f"({content_length_hdr} > {max_response_bytes} bytes), skipping"
                            )
                            return False, "Response too large", status_code

                    content_type = response.headers.get('Content-Type', '').lower()

                    if 'text/' in content_type or 'html' in content_type or 'xml' in content_type or 'json' in content_type:
                        try:
                            content = await response.text()
                            is_binary = False
                        except UnicodeDecodeError:
                            # S6: charset declared in HTTP header was wrong (or absent).
                            # Read raw bytes and attempt to detect charset from HTML
                            # <meta charset> / <meta http-equiv> tags before giving up.
                            raw = await response.read()
                            detected = _detect_charset_from_bytes(raw)
                            if detected:
                                try:
                                    content = raw.decode(detected)
                                    is_binary = False
                                    logger.debug(f"Decoded {url} using meta-detected charset: {detected}")
                                except (UnicodeDecodeError, LookupError):
                                    logger.warning(f"Unicode decode error for {url} even with detected charset {detected!r}, falling back to binary mode")
                                    content = raw
                                    is_binary = True
                            else:
                                logger.warning(f"Unicode decode error for {url}, falling back to binary mode")
                                content = raw
                                is_binary = True
                    else:
                        content = await response.read()
                        is_binary = True

                    response_obj = ResponseLike(
                        url=str(response.url),
                        status_code=response.status,
                        headers=dict(response.headers),
                        text=content,
                        is_binary=is_binary
                    )

                    if proxy_manager and current_proxy:
                        proxy_manager.report_success(current_proxy)
                    return True, response_obj, status_code

                elif response.status == 429:
                    # HTTP 429 Too Many Requests — retry after server-specified delay
                    retries += 1
                    if retries > max_retries:
                        logger.warning(f"Max retries ({max_retries}) exceeded for {url} (HTTP 429)")
                        return False, f"HTTP Error: {response.status}", status_code
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            backoff_time = min(float(retry_after), 120)
                        except (ValueError, TypeError):
                            backoff_time = min(2 ** retries, 32)
                    else:
                        backoff_time = min(2 ** retries, 32)
                    logger.warning(f"HTTP 429 for {url}, retrying in {backoff_time}s (attempt {retries}/{max_retries})")
                    await asyncio.sleep(backoff_time)

                elif 500 <= response.status < 600:
                    logger.warning(f"HTTP Error {response.status} for {url}, will retry")
                    retries += 1
                    if retries > max_retries:
                        logger.warning(f"Max retries ({max_retries}) exceeded for {url}")
                        return False, f"HTTP Error: {response.status}", status_code
                    backoff_time = min(2 ** retries, 32)
                    logger.debug(f"Waiting {backoff_time}s before retry (exponential backoff)")
                    await asyncio.sleep(backoff_time)
                else:
                    logger.warning(f"HTTP Error {response.status} for {url}")
                    return False, f"HTTP Error: {response.status}", status_code

        except (asyncio.TimeoutError,
                aiohttp.ClientConnectorError,
                aiohttp.TooManyRedirects,
                aiohttp.ClientResponseError,
                aiohttp.ClientError) as e:
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
                        proxy_url = current_proxy.get_url()
                        logger.debug(f"Retrying with different proxy: {current_proxy}")
            
            if not should_retry:
                # Don't retry for certain errors (e.g., TooManyRedirects, 4xx)
                return False, error_message, status_code or 500
            
            retries += 1
            if retries > max_retries:
                return False, error_message, status_code or 429
            
            # Exponential backoff before retry (only for exceptions)
            backoff_time = min(2 ** retries, 32)  # Cap at 32 seconds
            logger.debug(f"Waiting {backoff_time}s before retry (exponential backoff)")
            await asyncio.sleep(backoff_time)

      # If we've exhausted all retries
      return False, f"Max retries ({max_retries}) exceeded", status_code or 429

    finally:
        # Close the session we created ourselves; leave caller-provided sessions open.
        if _own_session is not None:
            await _own_session.close()


async def fetch_url_async(url: str, user_agent: str = "crawlit/1.0", 
                         max_retries: int = 3, timeout: int = 10):
    """
    Asynchronous version of fetch_url - provides same interface as the synchronous fetch_url
    
    This function is an alias for fetch_page_async that directly returns a ResponseLike object
    or raises appropriate exceptions, mirroring the behavior of the synchronous fetch_url.
    
    Args:
        url: The URL to fetch
        user_agent: User agent string to use in the request
        max_retries: Maximum number of retries on failure
        timeout: Request timeout in seconds
        
    Returns:
        ResponseLike: A response object with a requests.Response-compatible interface
        
    Raises:
        aiohttp.ClientResponseError: For HTTP error status codes
        aiohttp.ClientError: For other request errors
    """
    success, response_or_error, status_code = await fetch_page_async(url, user_agent, max_retries, timeout)
    
    # Return just the response object or raise exception
    if success:
        # For success case, return response object
        return response_or_error
    else:
        # For error case, raise an exception
        if isinstance(response_or_error, str) and "HTTP Error" in response_or_error:
            # Extract status code from error message and raise proper exception
            from aiohttp import ClientResponseError
            raise ClientResponseError(
                request_info=None,
                history=None,
                status=status_code,
                message=response_or_error
            )
        else:
            # For other errors, raise a generic exception
            from aiohttp import ClientError
            raise ClientError(response_or_error)


class ResponseLike:
    """A class to provide a requests.Response-like interface for aiohttp responses
    
    This class is designed to be compatible with both the requests.Response interface
    used by the synchronous crawler and the aiohttp.ClientResponse interface used by
    the asynchronous crawler.
    """
    
    def __init__(self, url, status_code, headers, text, is_binary=False):
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self._text = text     # Store text content privately
        
        # Store content as either text or binary depending on content type
        if is_binary:
            self.content = text  # In binary mode, 'text' parameter is actually binary content
            self._text = None    # No text representation for binary content
        else:
            self.content = text.encode('utf-8') if text else None  # Create binary content from text
            
        self.is_binary = is_binary
        self.ok = 200 <= status_code < 300  # Match requests.Response.ok property
        
    @property
    def status(self):
        """Compatibility property for aiohttp's response.status"""
        return self.status_code
        
    # Cannot have both a property and a method with the same name
    # Instead we'll make text() the async method and use a property getter
    # to make the object behave like a requests.Response in sync contexts
    
    async def text(self):
        """Async method to mimic aiohttp's response.text() method
        
        This makes ResponseLike usable in async contexts like aiohttp.ClientResponse
        """
        return self._text
    
    # Python doesn't support having both a property and method with the same name
    # Instead, we'll use a different property name for synchronous access
    @property
    def text_content(self):
        """Property to mimic requests.Response.text
        
        This makes the ResponseLike class work in sync contexts similar to requests.Response
        """
        return self._text
        
    def text_sync(self):
        """Legacy sync version of text for non-async contexts
        
        Maintained for backward compatibility
        """
        return self._text
        
    def raise_for_status(self):
        """Mimic requests.Response.raise_for_status()
        
        Raises an HTTPError for bad responses (4xx and 5xx)
        """
        if 400 <= self.status_code < 600:
            from aiohttp import ClientResponseError
            raise ClientResponseError(
                request_info=None,
                history=None,
                status=self.status_code,
                message=f"HTTP Error {self.status_code}"
            )
            
    def json(self):
        """Parse JSON content if the response contains JSON
        
        Mimics requests.Response.json()
        """
        if self._text:
            import json
            return json.loads(self._text)
        return None


async def async_fetch_page(url: str, user_agent: str, max_retries: int = 3, timeout: int = 30) -> Tuple[bool, Optional[str], int]:
    """
    Asynchronously fetch a web page with retry functionality.
    
    Args:
        url: The URL to fetch
        user_agent: User-agent string to use in request headers
        max_retries: Maximum number of retry attempts for failed requests
        timeout: Request timeout in seconds
    
    Returns:
        Tuple containing:
        - Success flag (bool): True if the request was successful
        - Response content (str or None): HTML content if successful, None otherwise
        - Status code (int): HTTP status code or 0 for request errors
    """
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    attempt = 0

    # Configure client timeout
    timeout_obj = aiohttp.ClientTimeout(total=timeout)

    # Create session once outside the retry loop to avoid resource leaks
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        while attempt <= max_retries:
            if attempt > 0:
                logger.debug(f"Retry attempt {attempt} for URL: {sanitize_url_for_log(url)}")
                # Exponential backoff between retries
                await asyncio.sleep(2 ** attempt)

            attempt += 1

            try:
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    status = response.status

                    # Check if we got a successful response
                    if response.ok:
                        content_type = response.headers.get('Content-Type', '')
                        mime_type = content_type.split(';')[0].strip().lower()
                        if mime_type in ('text/html', 'application/xhtml+xml'):
                            try:
                                html_content = await response.text()
                                return True, html_content, status
                            except Exception as e:
                                logger.error(f"Failed to decode content from {url}: {str(e)}")
                                return False, None, status
                        else:
                            logger.debug(f"URL {url} returned non-HTML content: {content_type}")
                            return False, None, status
                    else:
                        logger.debug(f"URL {url} returned status code: {status}")
                        if status >= 400 and status < 500 and status != 429:
                            # Client errors except for 429 (Too Many Requests) shouldn't be retried
                            return False, None, status
                        elif attempt > max_retries:
                            return False, None, status

                        # Otherwise we'll retry for server errors (5xx) and 429
                        continue

            except asyncio.TimeoutError:
                logger.warning(f"Request to {url} timed out after {timeout} seconds")
                if attempt > max_retries:
                    return False, None, 0
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                if attempt > max_retries:
                    return False, None, 0
            except Exception as e:
                logger.exception(f"Unexpected error while fetching {url}: {str(e)}")
                if attempt > max_retries:
                    return False, None, 0
    
    # If we've exhausted all retries and still no success
    return False, None, 0


async def _fetch_with_js_rendering(
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
        js_renderer: Optional AsyncJavaScriptRenderer instance to reuse
        wait_for_selector: CSS selector to wait for
        wait_for_timeout: Additional timeout after page load
        
    Returns:
        Tuple of (success, response_or_error, status_code)
    """
    should_close_renderer = False
    
    try:
        # Use provided renderer or create a new one
        if js_renderer is None:
            js_renderer = AsyncJavaScriptRenderer(
                user_agent=user_agent,
                timeout=timeout,
                headless=True
            )
            should_close_renderer = True
            await js_renderer.start()
            
        retries = 0
        while retries <= max_retries:
            result = await js_renderer.render(
                url,
                wait_for_selector=wait_for_selector,
                wait_for_timeout=wait_for_timeout
            )
            
            if result["success"]:
                # Create a ResponseLike object from the rendered content
                response_obj = ResponseLike(
                    url=result["url"],
                    status_code=result["status_code"],
                    headers={"Content-Type": "text/html; charset=utf-8"},
                    text=result["html"],
                    is_binary=False
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
                        await asyncio.sleep(backoff_time)
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
                await js_renderer.close()
            except Exception as e:
                logger.warning(f"Error closing JS renderer: {e}")
