#!/usr/bin/env python3
"""
progress.py - Progress tracking for crawls
"""

import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks progress of a crawl operation with callbacks and statistics.
    """
    
    def __init__(
        self,
        on_url_crawled: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        update_interval: int = 10
    ) -> None:
        """
        Initialize progress tracker.
        
        Args:
            on_url_crawled: Callback called after each URL is crawled
            on_progress: Callback called periodically with progress statistics
            update_interval: Number of URLs between progress updates
        """
        self.on_url_crawled = on_url_crawled
        self.on_progress = on_progress
        self.update_interval = update_interval
        
        self.start_time: Optional[datetime] = None
        self.urls_crawled: int = 0
        self.urls_successful: int = 0
        self.urls_failed: int = 0
        self.total_links_found: int = 0
        self.current_depth: int = 0
    
    def start(self) -> None:
        """Mark the start of crawling."""
        self.start_time = datetime.now()
        self.urls_crawled = 0
        self.urls_successful = 0
        self.urls_failed = 0
        self.total_links_found = 0
    
    def record_url(
        self,
        url: str,
        success: bool,
        links_found: int = 0,
        depth: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a crawled URL.
        
        Args:
            url: The URL that was crawled
            success: Whether the crawl was successful
            links_found: Number of links found on the page
            depth: Depth at which the URL was crawled
            metadata: Additional metadata about the crawl
        """
        self.urls_crawled += 1
        if success:
            self.urls_successful += 1
        else:
            self.urls_failed += 1
        
        self.total_links_found += links_found
        self.current_depth = max(self.current_depth, depth)
        
        # Call URL callback if provided
        if self.on_url_crawled:
            url_data = {
                'url': url,
                'success': success,
                'links_found': links_found,
                'depth': depth,
                **(metadata or {})
            }
            try:
                self.on_url_crawled(url, url_data)
            except Exception as e:
                logger.warning(f"Error in on_url_crawled callback: {e}")
        
        # Call progress callback periodically
        if self.on_progress and self.urls_crawled % self.update_interval == 0:
            self._notify_progress()
    
    def _notify_progress(self) -> None:
        """Notify progress callback with current statistics."""
        if not self.on_progress:
            return
        
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        rate = self.urls_crawled / elapsed if elapsed > 0 else 0
        
        stats = {
            'urls_crawled': self.urls_crawled,
            'urls_successful': self.urls_successful,
            'urls_failed': self.urls_failed,
            'total_links_found': self.total_links_found,
            'current_depth': self.current_depth,
            'elapsed_seconds': elapsed,
            'rate_per_second': rate,
            'success_rate': self.urls_successful / self.urls_crawled if self.urls_crawled > 0 else 0
        }
        
        try:
            self.on_progress(stats)
        except Exception as e:
            logger.warning(f"Error in on_progress callback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current progress statistics.
        
        Returns:
            Dictionary with current statistics
        """
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        rate = self.urls_crawled / elapsed if elapsed > 0 else 0
        
        return {
            'urls_crawled': self.urls_crawled,
            'urls_successful': self.urls_successful,
            'urls_failed': self.urls_failed,
            'total_links_found': self.total_links_found,
            'current_depth': self.current_depth,
            'elapsed_seconds': elapsed,
            'rate_per_second': rate,
            'success_rate': self.urls_successful / self.urls_crawled if self.urls_crawled > 0 else 0
        }
    
    def finish(self) -> Dict[str, Any]:
        """
        Mark the end of crawling and return final statistics.
        
        Returns:
            Dictionary with final statistics
        """
        # Final progress notification
        if self.on_progress:
            self._notify_progress()
        
        return self.get_stats()


def create_progress_callback(show_progress: bool = True) -> Optional[Callable[[Dict[str, Any]], None]]:
    """
    Create a simple progress callback that prints to console.
    
    Args:
        show_progress: Whether to show progress updates
        
    Returns:
        A progress callback function or None
    """
    if not show_progress:
        return None
    
    def progress_callback(stats: Dict[str, Any]) -> None:
        """Print progress statistics."""
        print(
            f"Progress: {stats['urls_crawled']} URLs crawled "
            f"({stats['urls_successful']} successful, {stats['urls_failed']} failed) "
            f"| Depth: {stats['current_depth']} | "
            f"Rate: {stats['rate_per_second']:.2f} URLs/sec"
        )
    
    return progress_callback

