#!/usr/bin/env python3
"""
async_fetcher.py - Asynchronous HTTP request handling
"""

import logging
import aiohttp
import asyncio
from typing import Union, Dict, Tuple, Any, Optional

logger = logging.getLogger(__name__)

async def fetch_page_async(url, user_agent="crawlit/2.0", max_retries=3, timeout=10):
    """
    Asynchronously fetch a web page with retries and proper error handling
    
    Args:
        url: The URL to fetch
        user_agent: User agent string to use in the request
        max_retries: Maximum number of retries on failure
        timeout: Request timeout in seconds
        
    Returns:
        tuple: (success, response_or_error, status_code)
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    retries = 0
    status_code = None
    last_error_type = None
    
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    
    while retries <= max_retries:
        try:
            logger.debug(f"Requesting {url} (attempt {retries + 1}/{max_retries + 1})")
            
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(url, headers=headers) as response:
                    status_code = response.status
                    
                    # Check if the request was successful
                    if response.status == 200:
                        # Check content type to determine if we should get text or binary content
                        content_type = response.headers.get('Content-Type', '').lower()
                        
                        # For text-based content types, decode as text
                        if 'text/' in content_type or 'html' in content_type or 'xml' in content_type or 'json' in content_type:
                            try:
                                content = await response.text()
                            except UnicodeDecodeError:
                                # Fallback to binary if text decoding fails
                                logger.warning(f"Unicode decode error for {url}, falling back to binary mode")
                                content = await response.read()
                                is_binary = True
                            else:
                                is_binary = False
                        else:
                            # For binary content types (images, pdfs, etc.), don't decode
                            content = await response.read()
                            is_binary = True
                        
                        # Create a response-like object compatible with the synchronous API
                        response_obj = ResponseLike(
                            url=str(response.url),
                            status_code=response.status,
                            headers=dict(response.headers),
                            text=content,
                            is_binary=is_binary
                        )
                        
                        return True, response_obj, status_code
                    # For 5xx server errors, retry if we haven't exceeded max retries
                    elif 500 <= response.status < 600:
                        logger.warning(f"HTTP Error {response.status} for {url}, will retry")
                        retries += 1
                        # If we've exceeded max retries, fail
                        if retries > max_retries:
                            logger.warning(f"Max retries ({max_retries}) exceeded for {url}")
                            return False, f"HTTP Error: {response.status}", status_code
                    else:
                        # For client errors (4xx) and other status codes, don't retry
                        logger.warning(f"HTTP Error {response.status} for {url}")
                        return False, f"HTTP Error: {response.status}", status_code
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout error for {url} (attempt {retries + 1})")
            retries += 1
            status_code = 408  # Request Timeout
            last_error_type = "timeout"
            
        except aiohttp.ClientConnectorError:
            logger.warning(f"Connection error for {url} (attempt {retries + 1})")
            retries += 1
            status_code = 503  # Service Unavailable
            last_error_type = "connection"
            
        except aiohttp.TooManyRedirects:
            logger.warning(f"Too many redirects for {url}")
            return False, "Too many redirects", 310
            
        except aiohttp.ClientError as e:
            logger.error(f"Request failed for {url}: {e}")
            return False, str(e), status_code or 500
        
        # Add a small delay between retries
        if retries <= max_retries:
            await asyncio.sleep(0.5)
    
    # Include error type in the message if known
    if last_error_type:
        return False, f"Max retries ({max_retries}) exceeded due to {last_error_type} errors", status_code or 429
    else:
        return False, f"Max retries ({max_retries}) exceeded", status_code or 429


async def fetch_url_async(url: str, user_agent: str = "crawlit/2.0", 
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
    
    while attempt <= max_retries:
        if attempt > 0:
            logger.debug(f"Retry attempt {attempt} for URL: {url}")
            # Exponential backoff between retries
            await asyncio.sleep(2 ** attempt)
        
        attempt += 1
        
        try:
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    status = response.status
                    
                    # Check if we got a successful response
                    if response.ok:
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
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
