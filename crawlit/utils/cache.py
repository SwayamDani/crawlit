#!/usr/bin/env python3
"""
cache.py - Caching layer for crawled pages
"""

import os
import json
import hashlib
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class PageCache:
    """
    Cache for crawled pages with optional TTL and disk persistence.
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl: Optional[int] = None,
        enable_disk_cache: bool = False
    ):
        """
        Initialize the page cache.
        
        Args:
            cache_dir: Directory for disk-based caching (if enable_disk_cache is True)
            ttl: Time-to-live in seconds for cached pages (None = no expiration)
            enable_disk_cache: Whether to persist cache to disk
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.ttl = ttl  # Time-to-live in seconds
        self.enable_disk_cache = enable_disk_cache
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # Create cache directory if needed
        if self.enable_disk_cache and self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Disk cache enabled at {self.cache_dir}")
        elif self.enable_disk_cache and not self.cache_dir:
            # Use default cache directory
            self.cache_dir = Path.home() / '.crawlit' / 'cache'
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Disk cache enabled at default location: {self.cache_dir}")
        else:
            logger.info("Memory-only cache enabled")
    
    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from URL"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, url: str) -> Path:
        """Get the file path for a cached URL"""
        if not self.cache_dir:
            raise ValueError("Disk cache not enabled")
        cache_key = self._get_cache_key(url)
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_expired(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data has expired"""
        if self.ttl is None:
            return False
        
        cached_time = cached_data.get('cached_at')
        if not cached_time:
            return True
        
        # Parse ISO format datetime
        if isinstance(cached_time, str):
            cached_time = datetime.fromisoformat(cached_time)
        
        elapsed = (datetime.now() - cached_time).total_seconds()
        return elapsed > self.ttl
    
    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached page data for a URL.
        
        Args:
            url: The URL to look up
            
        Returns:
            Cached data dict or None if not found/expired
        """
        # Check memory cache first
        if url in self.memory_cache:
            cached_data = self.memory_cache[url]
            if not self._is_expired(cached_data):
                logger.debug(f"Cache hit (memory): {url}")
                return cached_data
            else:
                # Expired, remove from memory
                del self.memory_cache[url]
        
        # Check disk cache if enabled
        if self.enable_disk_cache and self.cache_dir:
            cache_path = self._get_cache_path(url)
            if cache_path.exists():
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    # Check expiration
                    if not self._is_expired(cached_data):
                        logger.debug(f"Cache hit (disk): {url}")
                        # Also store in memory for faster access
                        self.memory_cache[url] = cached_data
                        return cached_data
                    else:
                        # Expired, remove from disk
                        cache_path.unlink()
                        logger.debug(f"Cache expired, removed: {url}")
                except Exception as e:
                    logger.warning(f"Error reading cache file {cache_path}: {e}")
        
        logger.debug(f"Cache miss: {url}")
        return None
    
    def set(
        self,
        url: str,
        response_data: Dict[str, Any],
        status_code: int,
        headers: Dict[str, Any],
        content: Optional[str] = None
    ) -> None:
        """
        Cache page data for a URL.
        
        Args:
            url: The URL to cache
            response_data: Response data to cache
            status_code: HTTP status code
            headers: Response headers
            content: Optional HTML content (can be large, so optional)
        """
        cached_data = {
            'url': url,
            'status_code': status_code,
            'headers': headers,
            'response_data': response_data,
            'content': content,
            'cached_at': datetime.now().isoformat()
        }
        
        # Store in memory cache
        self.memory_cache[url] = cached_data
        
        # Store on disk if enabled
        if self.enable_disk_cache and self.cache_dir:
            cache_path = self._get_cache_path(url)
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cached_data, f, indent=2, default=str)
                logger.debug(f"Cached to disk: {url}")
            except Exception as e:
                logger.warning(f"Error writing cache file {cache_path}: {e}")
    
    def clear(self) -> None:
        """Clear all cached data"""
        self.memory_cache.clear()
        
        if self.enable_disk_cache and self.cache_dir:
            try:
                for cache_file in self.cache_dir.glob('*.json'):
                    cache_file.unlink()
                logger.info(f"Cleared disk cache at {self.cache_dir}")
            except Exception as e:
                logger.warning(f"Error clearing disk cache: {e}")
    
    def remove(self, url: str) -> None:
        """Remove cached data for a specific URL"""
        # Remove from memory
        if url in self.memory_cache:
            del self.memory_cache[url]
        
        # Remove from disk
        if self.enable_disk_cache and self.cache_dir:
            cache_path = self._get_cache_path(url)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    logger.debug(f"Removed from cache: {url}")
                except Exception as e:
                    logger.warning(f"Error removing cache file {cache_path}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        disk_count = 0
        if self.enable_disk_cache and self.cache_dir:
            try:
                disk_count = len(list(self.cache_dir.glob('*.json')))
            except Exception:
                pass
        
        return {
            'memory_entries': len(self.memory_cache),
            'disk_entries': disk_count,
            'ttl': self.ttl,
            'disk_cache_enabled': self.enable_disk_cache,
            'cache_dir': str(self.cache_dir) if self.cache_dir else None
        }


class CrawlResume:
    """
    Utility for resuming interrupted crawls from saved state.
    """
    
    @staticmethod
    def can_resume(filepath: str) -> bool:
        """Check if a resume file exists and is valid"""
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            # Check if it has required keys
            return all(key in state for key in ['queue', 'visited_urls', 'results'])
        except Exception:
            return False
    
    @staticmethod
    def get_resume_info(filepath: str) -> Dict[str, Any]:
        """Get information about a saved crawl state"""
        if not os.path.exists(filepath):
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            return {
                'saved_at': state.get('saved_at'),
                'queue_size': len(state.get('queue', [])),
                'visited_count': len(state.get('visited_urls', [])),
                'results_count': len(state.get('results', {})),
                'metadata': state.get('metadata', {})
            }
        except Exception as e:
            logger.error(f"Error reading resume file: {e}")
            return {}


