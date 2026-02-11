#!/usr/bin/env python3
"""
deduplication.py - Content-based deduplication for crawler
"""

import logging
import hashlib
import threading
from typing import Set, Optional, Dict, Any
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class ContentDeduplicator:
    """
    Content-based deduplication that detects duplicate content even when URLs differ.
    
    Supports:
    - Exact content matching (hash-based)
    - Normalized content matching (whitespace/structure normalized)
    - Content similarity detection (optional, using hash-based approach)
    """
    
    def __init__(
        self,
        normalize_content: bool = True,
        min_content_length: int = 100,
        enabled: bool = True
    ):
        """
        Initialize the content deduplicator.
        
        Args:
            normalize_content: Whether to normalize content before hashing (removes extra whitespace, normalizes HTML)
            min_content_length: Minimum content length to consider for deduplication (in characters)
            enabled: Whether deduplication is enabled
        """
        self.normalize_content = normalize_content
        self.min_content_length = min_content_length
        self.enabled = enabled
        
        # Track seen content hashes
        self._content_hashes: Set[str] = set()
        self._content_to_urls: Dict[str, Set[str]] = {}  # Hash -> set of URLs
        self._lock = threading.Lock()  # Thread-safe access
        
        # Statistics
        self._duplicates_found = 0
        self._total_checked = 0
    
    def is_duplicate(self, content: str, url: str) -> bool:
        """
        Check if content is a duplicate of previously seen content.
        
        Args:
            content: HTML content to check
            url: URL of the content (for tracking)
            
        Returns:
            True if content is a duplicate, False otherwise
        """
        if not self.enabled:
            return False
        
        if not content or len(content) < self.min_content_length:
            return False
        
        with self._lock:
            self._total_checked += 1
            
            # Normalize content if enabled
            if self.normalize_content:
                normalized = self._normalize_content(content)
            else:
                normalized = content
            
            # Generate hash
            content_hash = self._hash_content(normalized)
            
            # Check if we've seen this hash before
            if content_hash in self._content_hashes:
                self._duplicates_found += 1
                
                # Track which URLs have this content
                if content_hash not in self._content_to_urls:
                    self._content_to_urls[content_hash] = set()
                self._content_to_urls[content_hash].add(url)
                
                # Get original URL(s) with this content
                original_urls = self._content_to_urls[content_hash]
                logger.debug(
                    f"Duplicate content detected for {url}. "
                    f"Original URL(s): {', '.join(original_urls)}"
                )
                return True
            
            # Add to seen content
            self._content_hashes.add(content_hash)
            if content_hash not in self._content_to_urls:
                self._content_to_urls[content_hash] = set()
            self._content_to_urls[content_hash].add(url)
            
            return False
    
    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for better duplicate detection.
        
        Removes:
        - Extra whitespace
        - HTML comments
        - Script and style tags (optional)
        - Normalizes whitespace
        
        Args:
            content: Raw HTML content
            
        Returns:
            Normalized content string
        """
        try:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style tags (they often vary but don't affect content)
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            
            # Remove comments
            from bs4 import Comment
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            for comment in comments:
                comment.extract()
            
            # Get text content
            text = soup.get_text()
            
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
        except Exception as e:
            logger.warning(f"Error normalizing content: {e}. Using original content.")
            return content
    
    def _hash_content(self, content: str) -> str:
        """
        Generate a hash for content.
        
        Args:
            content: Content string to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_duplicate_urls(self, url: str) -> Optional[Set[str]]:
        """
        Get URLs that have the same content as the given URL.
        
        Args:
            url: URL to check
            
        Returns:
            Set of URLs with duplicate content, or None if not found
        """
        if not self.enabled:
            return None
        
        with self._lock:
            for content_hash, urls in self._content_to_urls.items():
                if url in urls:
                    # Return all URLs with this content, excluding the given URL
                    return urls - {url}
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                'enabled': self.enabled,
                'normalize_content': self.normalize_content,
                'min_content_length': self.min_content_length,
                'total_checked': self._total_checked,
                'duplicates_found': self._duplicates_found,
                'unique_content_count': len(self._content_hashes),
                'duplicate_rate': (
                    self._duplicates_found / self._total_checked 
                    if self._total_checked > 0 else 0.0
                )
            }
    
    def clear(self) -> None:
        """Clear all tracked content hashes."""
        with self._lock:
            self._content_hashes.clear()
            self._content_to_urls.clear()
            self._duplicates_found = 0
            self._total_checked = 0
            logger.debug("Content deduplicator cleared")
    
    def reset_stats(self) -> None:
        """Reset statistics while keeping tracked content."""
        with self._lock:
            self._duplicates_found = 0
            self._total_checked = 0


