#!/usr/bin/env python3
"""
budget_tracker.py - Crawl budget tracking and enforcement

Tracks and enforces limits on:
- Maximum pages crawled
- Maximum bandwidth (bytes downloaded)
- Maximum time elapsed
- Maximum file size per request
"""

import logging
import time
import threading
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BudgetLimits:
    """Configuration for crawl budget limits."""
    max_pages: Optional[int] = None
    max_bandwidth_mb: Optional[float] = None
    max_time_seconds: Optional[float] = None
    max_file_size_mb: Optional[float] = None


class BudgetTracker:
    """
    Tracks crawl resource usage and enforces budget limits.
    
    Thread-safe implementation for use with multi-threaded crawlers.
    """
    
    def __init__(
        self,
        max_pages: Optional[int] = None,
        max_bandwidth_mb: Optional[float] = None,
        max_time_seconds: Optional[float] = None,
        max_file_size_mb: Optional[float] = None,
        on_budget_exceeded: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        """
        Initialize the budget tracker.
        
        Args:
            max_pages: Maximum number of pages to crawl (must be positive or None)
            max_bandwidth_mb: Maximum bandwidth in megabytes (must be positive or None)
            max_time_seconds: Maximum time in seconds (must be positive or None)
            max_file_size_mb: Maximum file size per request in megabytes (must be positive or None)
            on_budget_exceeded: Callback when budget is exceeded (receives limit_type and stats)
            
        Raises:
            ValueError: If any limit is zero or negative
        """
        # Validate limits
        if max_pages is not None and max_pages <= 0:
            raise ValueError(f"max_pages must be positive, got {max_pages}")
        if max_bandwidth_mb is not None and max_bandwidth_mb <= 0:
            raise ValueError(f"max_bandwidth_mb must be positive, got {max_bandwidth_mb}")
        if max_time_seconds is not None and max_time_seconds <= 0:
            raise ValueError(f"max_time_seconds must be positive, got {max_time_seconds}")
        if max_file_size_mb is not None and max_file_size_mb <= 0:
            raise ValueError(f"max_file_size_mb must be positive, got {max_file_size_mb}")
        self.limits = BudgetLimits(
            max_pages=max_pages,
            max_bandwidth_mb=max_bandwidth_mb,
            max_time_seconds=max_time_seconds,
            max_file_size_mb=max_file_size_mb
        )

        # Track usage
        self._pages_crawled = 0
        self._bytes_downloaded = 0
        self._start_time = time.time() if max_time_seconds else None
        self._on_budget_exceeded = on_budget_exceeded

        # Thread safety
        self._lock = threading.Lock()

        # Track if budget was exceeded
        self._budget_exceeded = False
        self._exceeded_reason = None

        logger.info(f"Budget tracker initialized: {self._format_limits()}")
    
    def _format_limits(self) -> str:
        """Format limits as a readable string."""
        limits = []
        if self.limits.max_pages:
            limits.append(f"pages={self.limits.max_pages}")
        if self.limits.max_bandwidth_mb:
            limits.append(f"bandwidth={self.limits.max_bandwidth_mb}MB")
        if self.limits.max_time_seconds:
            limits.append(f"time={self.limits.max_time_seconds}s")
        if self.limits.max_file_size_mb:
            limits.append(f"file_size={self.limits.max_file_size_mb}MB")
        return ", ".join(limits) if limits else "no limits"
    
    def can_crawl_page(self) -> Tuple[bool, Optional[str]]:
        """
        Check if a new page can be crawled without exceeding budget.

        Returns:
            Tuple of (can_crawl, reason) where reason is set if cannot crawl
        """
        callback_info = None
        
        with self._lock:
            # Check if budget already exceeded
            if self._budget_exceeded:
                return False, self._exceeded_reason
            
            # Check page limit
            if self.limits.max_pages and self._pages_crawled >= self.limits.max_pages:
                reason = f"Page limit reached ({self.limits.max_pages} pages)"
                callback_info = self._mark_exceeded(reason)
                # Fall through to trigger callback outside lock
            
            # Check time limit
            elif self.limits.max_time_seconds and self._start_time:
                elapsed = time.time() - self._start_time
                if elapsed >= self.limits.max_time_seconds:
                    reason = f"Time limit reached ({self.limits.max_time_seconds}s)"
                    callback_info = self._mark_exceeded(reason)
            
            # Check bandwidth limit
            elif self.limits.max_bandwidth_mb:
                mb_downloaded = self._bytes_downloaded / (1024 * 1024)
                if mb_downloaded >= self.limits.max_bandwidth_mb:
                    reason = f"Bandwidth limit reached ({self.limits.max_bandwidth_mb}MB)"
                    callback_info = self._mark_exceeded(reason)
            
            if callback_info:
                exceeded_reason = self._exceeded_reason
        
        # Trigger callback outside the lock to avoid deadlock
        if callback_info and callback_info[1]:  # callback_info[1] indicates if callback exists
            self._trigger_callback(callback_info[0])
            return False, callback_info[0]
        elif callback_info:
            return False, callback_info[0]
        
        return True, None
    
    def can_download_file(self, file_size_bytes: int) -> Tuple[bool, Optional[str]]:
        """
        Check if a file can be downloaded without exceeding budget.

        Args:
            file_size_bytes: Size of file to download

        Returns:
            Tuple of (can_download, reason)
        """
        with self._lock:
            # Check file size limit
            if self.limits.max_file_size_mb:
                file_size_mb = file_size_bytes / (1024 * 1024)
                if file_size_mb > self.limits.max_file_size_mb:
                    return False, f"File size ({file_size_mb:.2f}MB) exceeds limit ({self.limits.max_file_size_mb}MB)"
            
            # Check bandwidth limit
            if self.limits.max_bandwidth_mb:
                mb_downloaded = self._bytes_downloaded / (1024 * 1024)
                file_size_mb = file_size_bytes / (1024 * 1024)
                if mb_downloaded + file_size_mb > self.limits.max_bandwidth_mb:
                    return False, f"Would exceed bandwidth limit ({self.limits.max_bandwidth_mb}MB)"
            
            return True, None
    
    def record_page(self, bytes_downloaded: int):
        """
        Record a successfully crawled page.
        
        Args:
            bytes_downloaded: Number of bytes downloaded for this page
        """
        with self._lock:
            self._pages_crawled += 1
            self._bytes_downloaded += bytes_downloaded
            
            logger.debug(f"Budget: pages={self._pages_crawled}, "
                        f"bandwidth={self._bytes_downloaded / (1024 * 1024):.2f}MB")
    
    def _mark_exceeded(self, reason: str):
        """Mark budget as exceeded and return callback info."""
        self._budget_exceeded = True
        self._exceeded_reason = reason
        logger.warning(f"Budget exceeded: {reason}")
        
        # Return callback info to be invoked outside the lock
        return (reason, self._on_budget_exceeded is not None)
    
    def _trigger_callback(self, reason: str):
        """Trigger the budget exceeded callback outside of the lock."""
        if self._on_budget_exceeded:
            try:
                stats = self.get_stats()
                self._on_budget_exceeded(reason, stats)
            except Exception as e:
                logger.error(f"Error in budget exceeded callback: {e}")
    
    def is_budget_exceeded(self) -> bool:
        """Check if budget has been exceeded."""
        with self._lock:
            return self._budget_exceeded
    
    def get_exceeded_reason(self) -> Optional[str]:
        """Get the reason budget was exceeded, if any."""
        with self._lock:
            return self._exceeded_reason
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current budget usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        with self._lock:
            elapsed_time = None
            if self._start_time:
                elapsed_time = time.time() - self._start_time
            
            mb_downloaded = self._bytes_downloaded / (1024 * 1024)
            
            stats = {
                'pages_crawled': self._pages_crawled,
                'bytes_downloaded': self._bytes_downloaded,
                'mb_downloaded': mb_downloaded,
                'elapsed_time_seconds': elapsed_time,
                'budget_exceeded': self._budget_exceeded,
                'exceeded_reason': self._exceeded_reason,
                'limits': {
                    'max_pages': self.limits.max_pages,
                    'max_bandwidth_mb': self.limits.max_bandwidth_mb,
                    'max_time_seconds': self.limits.max_time_seconds,
                    'max_file_size_mb': self.limits.max_file_size_mb
                }
            }
            
            # Calculate percentage usage if limits are set
            if self.limits.max_pages:
                stats['pages_usage_percent'] = (self._pages_crawled / self.limits.max_pages) * 100
            
            if self.limits.max_bandwidth_mb:
                stats['bandwidth_usage_percent'] = (mb_downloaded / self.limits.max_bandwidth_mb) * 100
            
            if self.limits.max_time_seconds and elapsed_time:
                stats['time_usage_percent'] = (elapsed_time / self.limits.max_time_seconds) * 100
            
            return stats
    
    def reset(self):
        """Reset all counters and budget exceeded flag."""
        with self._lock:
            self._pages_crawled = 0
            self._bytes_downloaded = 0
            self._start_time = time.time() if self.limits.max_time_seconds else None
            self._budget_exceeded = False
            self._exceeded_reason = None
            logger.debug("Budget tracker reset")


class AsyncBudgetTracker(BudgetTracker):
    """
    Async-compatible budget tracker.
    
    Uses asyncio locks for thread safety in async contexts.
    Note: For simplicity, this still uses threading.Lock which works
    in async contexts, but for pure async use, consider asyncio.Lock.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize async budget tracker with same parameters as sync version."""
        super().__init__(*args, **kwargs)
        # Note: We keep threading.Lock as it works in both sync and async contexts
        # For a pure async implementation, use asyncio.Lock



