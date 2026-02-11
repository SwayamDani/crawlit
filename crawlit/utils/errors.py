#!/usr/bin/env python3
"""
errors.py - Standardized error handling for crawlit
"""

from typing import Optional, Tuple, Union, Any
import logging
import asyncio

logger = logging.getLogger(__name__)


class CrawlitError(Exception):
    """Base exception for all crawlit errors."""
    pass


class FetchError(CrawlitError):
    """Exception raised when a URL fetch fails."""
    
    def __init__(self, url: str, status_code: Optional[int] = None, message: Optional[str] = None):
        self.url = url
        self.status_code = status_code
        self.message = message or f"Failed to fetch {url}"
        super().__init__(self.message)


class RobotsError(CrawlitError):
    """Exception raised when robots.txt parsing fails."""
    pass


class ParseError(CrawlitError):
    """Exception raised when HTML parsing fails."""
    pass


class ExtractionError(CrawlitError):
    """Exception raised when content extraction fails."""
    pass


def handle_fetch_error(
    url: str,
    error: Exception,
    max_retries: int,
    retry_count: int
) -> Tuple[bool, str, Optional[int]]:
    """
    Standardized error handling for fetch operations.
    
    Args:
        url: The URL that failed
        error: The exception that was raised
        max_retries: Maximum number of retries allowed
        retry_count: Current retry attempt number
        
    Returns:
        Tuple of (should_retry, error_message, status_code)
    """
    import requests
    import aiohttp
    
    status_code: Optional[int] = None
    error_message: str = str(error)
    should_retry: bool = False
    
    # Handle requests exceptions
    if isinstance(error, requests.exceptions.Timeout):
        status_code = 408
        error_message = f"Timeout error for {url}"
        should_retry = retry_count < max_retries
    elif isinstance(error, requests.exceptions.ConnectionError):
        status_code = 503
        error_message = f"Connection error for {url}"
        should_retry = retry_count < max_retries
    elif isinstance(error, requests.exceptions.TooManyRedirects):
        status_code = 310
        error_message = f"Too many redirects for {url}"
        should_retry = False
    elif isinstance(error, requests.exceptions.HTTPError):
        if hasattr(error.response, 'status_code'):
            status_code = error.response.status_code
        error_message = f"HTTP error {status_code} for {url}"
        # Retry on 5xx errors
        should_retry = status_code and 500 <= status_code < 600 and retry_count < max_retries
    elif isinstance(error, requests.exceptions.RequestException):
        status_code = 500
        error_message = f"Request failed for {url}: {error}"
        should_retry = retry_count < max_retries
    
    # Handle asyncio timeout exceptions (used by aiohttp)
    elif isinstance(error, asyncio.TimeoutError):
        status_code = 408
        error_message = f"Timeout error for {url}"
        should_retry = retry_count < max_retries
    elif isinstance(error, aiohttp.ClientConnectorError):
        status_code = 503
        error_message = f"Connection error for {url}"
        should_retry = retry_count < max_retries
    elif isinstance(error, aiohttp.TooManyRedirects):
        status_code = 310
        error_message = f"Too many redirects for {url}"
        should_retry = False
    elif isinstance(error, aiohttp.ClientResponseError):
        status_code = error.status
        error_message = f"HTTP error {status_code} for {url}"
        should_retry = 500 <= status_code < 600 and retry_count < max_retries
    elif isinstance(error, aiohttp.ClientError):
        status_code = 500
        error_message = f"Client error for {url}: {error}"
        should_retry = retry_count < max_retries
    
    # Handle generic exceptions
    else:
        status_code = 500
        error_message = f"Unexpected error for {url}: {error}"
        should_retry = retry_count < max_retries
    
    return should_retry, error_message, status_code

