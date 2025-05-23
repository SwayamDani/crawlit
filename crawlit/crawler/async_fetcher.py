#!/usr/bin/env python3
"""
async_fetcher.py - Asynchronous HTTP request handling
"""

import logging
import aiohttp
import asyncio

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


class ResponseLike:
    """A class to provide a requests.Response-like interface for aiohttp responses"""
    
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
        
    @property
    def status(self):
        """Compatibility property for aiohttp's response.status"""
        return self.status_code
        
    async def text(self):
        """Async method to mimic aiohttp's response.text() method"""
        return self._text
        
    def text_sync(self):
        """Sync version of text for non-async contexts"""
        return self._text
