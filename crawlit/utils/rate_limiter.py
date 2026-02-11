#!/usr/bin/env python3
"""
rate_limiter.py - Per-domain rate limiting for crawler
"""

import logging
import time
import threading
import asyncio
from typing import Dict, Optional
from urllib.parse import urlparse
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Per-domain rate limiter that tracks last request time per domain
    and enforces delays between requests to the same domain.
    """
    
    def __init__(self, default_delay: float = 0.1):
        """
        Initialize the rate limiter.
        
        Args:
            default_delay: Default delay in seconds between requests (global fallback)
        """
        self.default_delay = default_delay
        self._domain_delays: Dict[str, float] = {}  # Domain -> delay in seconds
        self._domain_last_request: Dict[str, float] = {}  # Domain -> last request timestamp
        self._lock = threading.Lock()  # Thread-safe access
    
    def set_domain_delay(self, domain: str, delay: float) -> None:
        """
        Set a custom delay for a specific domain.
        
        Args:
            domain: Domain name (e.g., "example.com")
            delay: Delay in seconds between requests to this domain
        """
        with self._lock:
            self._domain_delays[domain] = delay
            logger.debug(f"Set delay for {domain}: {delay}s")
    
    def get_domain_delay(self, domain: str) -> float:
        """
        Get the delay for a specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Delay in seconds for this domain, or default delay if not set
        """
        with self._lock:
            return self._domain_delays.get(domain, self.default_delay)
    
    def wait_if_needed(self, url: str) -> None:
        """
        Wait if necessary to respect rate limiting for the domain.
        This is a blocking call for synchronous code.
        
        Args:
            url: URL being requested
        """
        domain = self._extract_domain(url)
        delay = self.get_domain_delay(domain)
        
        if delay <= 0:
            return
        
        with self._lock:
            last_request_time = self._domain_last_request.get(domain, 0)
            current_time = time.time()
            time_since_last_request = current_time - last_request_time
            
            if time_since_last_request < delay:
                sleep_time = delay - time_since_last_request
                logger.debug(f"Rate limiting: waiting {sleep_time:.3f}s for {domain}")
                time.sleep(sleep_time)
            
            self._domain_last_request[domain] = time.time()
    
    async def wait_if_needed_async(self, url: str) -> None:
        """
        Wait if necessary to respect rate limiting for the domain (async version).
        
        Args:
            url: URL being requested
        """
        domain = self._extract_domain(url)
        delay = self.get_domain_delay(domain)
        
        if delay <= 0:
            return
        
        # Use asyncio.Lock for async thread-safety
        # Note: In async context, we use a simpler approach
        current_time = time.time()
        last_request_time = self._domain_last_request.get(domain, 0)
        time_since_last_request = current_time - last_request_time
        
        if time_since_last_request < delay:
            sleep_time = delay - time_since_last_request
            logger.debug(f"Rate limiting: waiting {sleep_time:.3f}s for {domain}")
            await asyncio.sleep(sleep_time)
        
        self._domain_last_request[domain] = time.time()
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Domain name (e.g., "example.com")
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return "unknown"
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about rate limiting.
        
        Returns:
            Dictionary with rate limiting statistics
        """
        with self._lock:
            return {
                'default_delay': self.default_delay,
                'domains_with_custom_delay': len(self._domain_delays),
                'domains_tracked': len(self._domain_last_request),
                'domain_delays': self._domain_delays.copy(),
            }
    
    def clear(self) -> None:
        """Clear all domain-specific delays and reset tracking."""
        with self._lock:
            self._domain_delays.clear()
            self._domain_last_request.clear()
            logger.debug("Rate limiter cleared")


class AsyncRateLimiter:
    """
    Async version of rate limiter using asyncio locks.
    """
    
    def __init__(self, default_delay: float = 0.1):
        """
        Initialize the async rate limiter.
        
        Args:
            default_delay: Default delay in seconds between requests (global fallback)
        """
        self.default_delay = default_delay
        self._domain_delays: Dict[str, float] = {}
        self._domain_last_request: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def set_domain_delay(self, domain: str, delay: float) -> None:
        """Set a custom delay for a specific domain (async)."""
        async with self._lock:
            self._domain_delays[domain] = delay
            logger.debug(f"Set delay for {domain}: {delay}s")
    
    async def get_domain_delay(self, domain: str) -> float:
        """Get the delay for a specific domain (async)."""
        async with self._lock:
            return self._domain_delays.get(domain, self.default_delay)
    
    async def wait_if_needed(self, url: str) -> None:
        """Wait if necessary to respect rate limiting for the domain (async)."""
        domain = self._extract_domain(url)
        delay = await self.get_domain_delay(domain)
        
        if delay <= 0:
            return
        
        async with self._lock:
            last_request_time = self._domain_last_request.get(domain, 0)
            current_time = time.time()
            time_since_last_request = current_time - last_request_time
            
            if time_since_last_request < delay:
                sleep_time = delay - time_since_last_request
                logger.debug(f"Rate limiting: waiting {sleep_time:.3f}s for {domain}")
                await asyncio.sleep(sleep_time)
            
            self._domain_last_request[domain] = time.time()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return "unknown"
    
    async def get_stats(self) -> Dict[str, any]:
        """Get statistics about rate limiting (async)."""
        async with self._lock:
            return {
                'default_delay': self.default_delay,
                'domains_with_custom_delay': len(self._domain_delays),
                'domains_tracked': len(self._domain_last_request),
                'domain_delays': self._domain_delays.copy(),
            }
    
    async def clear(self) -> None:
        """Clear all domain-specific delays and reset tracking (async)."""
        async with self._lock:
            self._domain_delays.clear()
            self._domain_last_request.clear()
            logger.debug("Async rate limiter cleared")


