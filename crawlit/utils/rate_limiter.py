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
    
    def __init__(self, default_delay: float = 0.1, requests_per_second: Optional[float] = None):
        """
        Initialize the rate limiter.
        
        Args:
            default_delay: Default delay in seconds between requests (global fallback)
            requests_per_second: Alternative way to specify rate limit (converted to delay)
        """
        # If requests_per_second is provided, convert to delay
        if requests_per_second is not None:
            if requests_per_second <= 0:
                raise ValueError("requests_per_second must be positive")
            self.default_delay = 1.0 / requests_per_second
        else:
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
    
    def wait(self, url: str) -> None:
        """
        Wait if necessary to respect rate limiting (alias for wait_if_needed).
        
        Args:
            url: URL or domain being requested
        """
        self.wait_if_needed(url)
    
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
            url: Full URL or domain name
            
        Returns:
            Domain name (e.g., "example.com")
        """
        try:
            # If no scheme, add one for proper parsing
            if not url.startswith(('http://', 'https://', '//')):
                url = 'http://' + url
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # If still no netloc, might just be a domain name
            if not domain and parsed.path:
                domain = parsed.path.split('/')[0].lower()
            
            return domain or "unknown"
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


class DynamicRateLimiter(RateLimiter):
    """
    Dynamic rate limiter that adapts delays based on server responses.
    
    Automatically adjusts crawl rate based on:
    - Response times
    - Error rates  
    - HTTP 429 (Too Many Requests) responses
    - Retry-After headers
    """
    
    def __init__(
        self,
        default_delay: float = 0.1,
        min_delay: float = 0.05,
        max_delay: float = 10.0,
        sensitivity: str = 'medium',
        adjustment_factor: float = 1.5
    ):
        """
        Initialize the dynamic rate limiter.
        
        Args:
            default_delay: Default delay in seconds
            min_delay: Minimum allowed delay
            max_delay: Maximum allowed delay
            sensitivity: Adjustment sensitivity ('low', 'medium', 'high')
            adjustment_factor: Factor for delay adjustments
        """
        super().__init__(default_delay=default_delay)
        
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.adjustment_factor = adjustment_factor
        
        # Response time tracking per domain
        self._response_times: Dict[str, List[float]] = defaultdict(list)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._success_counts: Dict[str, int] = defaultdict(int)
        
        # Sensitivity settings
        sensitivity_map = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5
        }
        self.sensitivity_multiplier = sensitivity_map.get(sensitivity, 1.0)
        
        logger.debug(f"Dynamic rate limiter initialized: min={min_delay}s, max={max_delay}s, sensitivity={sensitivity}")
    
    def record_response(
        self,
        url: str,
        response_time: float,
        status_code: int,
        retry_after: Optional[int] = None
    ) -> None:
        """
        Record a response and adjust delay if needed.
        
        Args:
            url: URL that was requested
            response_time: Response time in seconds
            status_code: HTTP status code
            retry_after: Retry-After header value in seconds (if present)
        """
        domain = self._extract_domain(url)
        
        with self._lock:
            # Record response time
            self._response_times[domain].append(response_time)
            
            # Keep only last 10 response times
            if len(self._response_times[domain]) > 10:
                self._response_times[domain] = self._response_times[domain][-10:]
            
            # Track success/error
            if 200 <= status_code < 400:
                self._success_counts[domain] += 1
            else:
                self._error_counts[domain] += 1
            
            current_delay = self.get_domain_delay(domain)
            
            # Handle explicit rate limiting
            if status_code == 429:
                # Too Many Requests - increase delay significantly
                if retry_after:
                    new_delay = float(retry_after)
                else:
                    new_delay = current_delay * self.adjustment_factor * 2.0
                
                new_delay = min(new_delay, self.max_delay)
                self.set_domain_delay(domain, new_delay)
                logger.warning(f"Rate limit hit for {domain}, increased delay to {new_delay:.2f}s")
                return
            
            # Calculate error rate
            total_requests = self._success_counts[domain] + self._error_counts[domain]
            if total_requests >= 5:  # Need minimum sample size
                error_rate = self._error_counts[domain] / total_requests
                
                # High error rate - slow down
                if error_rate > 0.3:
                    new_delay = current_delay * (1.0 + self.sensitivity_multiplier * 0.2)
                    new_delay = min(new_delay, self.max_delay)
                    if new_delay != current_delay:
                        self.set_domain_delay(domain, new_delay)
                        logger.info(f"High error rate ({error_rate:.1%}) for {domain}, increased delay to {new_delay:.2f}s")
                    return
            
            # Adjust based on response time
            if len(self._response_times[domain]) >= 5:
                avg_response_time = sum(self._response_times[domain]) / len(self._response_times[domain])
                
                # Slow responses - increase delay
                if avg_response_time > 2.0:
                    new_delay = current_delay * (1.0 + self.sensitivity_multiplier * 0.1)
                    new_delay = min(new_delay, self.max_delay)
                    if new_delay != current_delay:
                        self.set_domain_delay(domain, new_delay)
                        logger.debug(f"Slow responses ({avg_response_time:.2f}s avg) for {domain}, increased delay to {new_delay:.2f}s")
                
                # Fast responses and low error rate - decrease delay
                elif avg_response_time < 0.5 and error_rate < 0.1:
                    new_delay = current_delay / (1.0 + self.sensitivity_multiplier * 0.1)
                    new_delay = max(new_delay, self.min_delay)
                    if new_delay != current_delay:
                        self.set_domain_delay(domain, new_delay)
                        logger.debug(f"Fast responses ({avg_response_time:.2f}s avg) for {domain}, decreased delay to {new_delay:.2f}s")
    
    def get_stats(self) -> Dict[str, any]:
        """Get extended statistics including dynamic adjustments."""
        stats = super().get_stats()
        
        with self._lock:
            stats['dynamic_tracking'] = {
                'domains_tracked': len(self._response_times),
                'min_delay': self.min_delay,
                'max_delay': self.max_delay,
                'sensitivity_multiplier': self.sensitivity_multiplier
            }
            
            # Per-domain stats
            domain_stats = {}
            for domain in self._response_times.keys():
                if self._response_times[domain]:
                    avg_response_time = sum(self._response_times[domain]) / len(self._response_times[domain])
                    total = self._success_counts[domain] + self._error_counts[domain]
                    error_rate = self._error_counts[domain] / total if total > 0 else 0
                    
                    domain_stats[domain] = {
                        'avg_response_time': avg_response_time,
                        'error_rate': error_rate,
                        'total_requests': total,
                        'current_delay': self.get_domain_delay(domain)
                    }
            
            stats['domain_stats'] = domain_stats
        
        return stats


class AsyncDynamicRateLimiter(AsyncRateLimiter):
    """
    Async version of dynamic rate limiter.
    
    Automatically adjusts crawl rate based on server responses.
    """
    
    def __init__(
        self,
        default_delay: float = 0.1,
        min_delay: float = 0.05,
        max_delay: float = 10.0,
        sensitivity: str = 'medium',
        adjustment_factor: float = 1.5
    ):
        """
        Initialize the async dynamic rate limiter.
        
        Args:
            default_delay: Default delay in seconds
            min_delay: Minimum allowed delay
            max_delay: Maximum allowed delay
            sensitivity: Adjustment sensitivity ('low', 'medium', 'high')
            adjustment_factor: Factor for delay adjustments
        """
        super().__init__(default_delay=default_delay)
        
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.adjustment_factor = adjustment_factor
        
        # Response time tracking per domain
        self._response_times: Dict[str, List[float]] = defaultdict(list)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._success_counts: Dict[str, int] = defaultdict(int)
        
        # Sensitivity settings
        sensitivity_map = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5
        }
        self.sensitivity_multiplier = sensitivity_map.get(sensitivity, 1.0)
        
        logger.debug(f"Async dynamic rate limiter initialized: min={min_delay}s, max={max_delay}s, sensitivity={sensitivity}")
    
    async def record_response(
        self,
        url: str,
        response_time: float,
        status_code: int,
        retry_after: Optional[int] = None
    ) -> None:
        """
        Record a response and adjust delay if needed (async).
        
        Args:
            url: URL that was requested
            response_time: Response time in seconds
            status_code: HTTP status code
            retry_after: Retry-After header value in seconds (if present)
        """
        domain = self._extract_domain(url)
        
        async with self._lock:
            # Record response time
            self._response_times[domain].append(response_time)
            
            # Keep only last 10 response times
            if len(self._response_times[domain]) > 10:
                self._response_times[domain] = self._response_times[domain][-10:]
            
            # Track success/error
            if 200 <= status_code < 400:
                self._success_counts[domain] += 1
            else:
                self._error_counts[domain] += 1
            
            current_delay = await self.get_domain_delay(domain)
            
            # Handle explicit rate limiting
            if status_code == 429:
                # Too Many Requests - increase delay significantly
                if retry_after:
                    new_delay = float(retry_after)
                else:
                    new_delay = current_delay * self.adjustment_factor * 2.0
                
                new_delay = min(new_delay, self.max_delay)
                await self.set_domain_delay(domain, new_delay)
                logger.warning(f"Rate limit hit for {domain}, increased delay to {new_delay:.2f}s")
                return
            
            # Calculate error rate
            total_requests = self._success_counts[domain] + self._error_counts[domain]
            if total_requests >= 5:  # Need minimum sample size
                error_rate = self._error_counts[domain] / total_requests
                
                # High error rate - slow down
                if error_rate > 0.3:
                    new_delay = current_delay * (1.0 + self.sensitivity_multiplier * 0.2)
                    new_delay = min(new_delay, self.max_delay)
                    if new_delay != current_delay:
                        await self.set_domain_delay(domain, new_delay)
                        logger.info(f"High error rate ({error_rate:.1%}) for {domain}, increased delay to {new_delay:.2f}s")
                    return
            
            # Adjust based on response time
            if len(self._response_times[domain]) >= 5:
                avg_response_time = sum(self._response_times[domain]) / len(self._response_times[domain])
                
                # Slow responses - increase delay
                if avg_response_time > 2.0:
                    new_delay = current_delay * (1.0 + self.sensitivity_multiplier * 0.1)
                    new_delay = min(new_delay, self.max_delay)
                    if new_delay != current_delay:
                        await self.set_domain_delay(domain, new_delay)
                        logger.debug(f"Slow responses ({avg_response_time:.2f}s avg) for {domain}, increased delay to {new_delay:.2f}s")
                
                # Fast responses and low error rate - decrease delay
                elif avg_response_time < 0.5 and error_rate < 0.1:
                    new_delay = current_delay / (1.0 + self.sensitivity_multiplier * 0.1)
                    new_delay = max(new_delay, self.min_delay)
                    if new_delay != current_delay:
                        await self.set_domain_delay(domain, new_delay)
                        logger.debug(f"Fast responses ({avg_response_time:.2f}s avg) for {domain}, decreased delay to {new_delay:.2f}s")
    
    async def get_stats(self) -> Dict[str, any]:
        """Get extended statistics including dynamic adjustments (async)."""
        stats = await super().get_stats()
        
        async with self._lock:
            stats['dynamic_tracking'] = {
                'domains_tracked': len(self._response_times),
                'min_delay': self.min_delay,
                'max_delay': self.max_delay,
                'sensitivity_multiplier': self.sensitivity_multiplier
            }
            
            # Per-domain stats
            domain_stats = {}
            for domain in self._response_times.keys():
                if self._response_times[domain]:
                    avg_response_time = sum(self._response_times[domain]) / len(self._response_times[domain])
                    total = self._success_counts[domain] + self._error_counts[domain]
                    error_rate = self._error_counts[domain] / total if total > 0 else 0
                    
                    domain_stats[domain] = {
                        'avg_response_time': avg_response_time,
                        'error_rate': error_rate,
                        'total_requests': total,
                        'current_delay': await self.get_domain_delay(domain)
                    }
            
            stats['domain_stats'] = domain_stats
        
        return stats
