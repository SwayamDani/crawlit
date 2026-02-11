#!/usr/bin/env python3
"""
storage.py - Storage management for crawl results
"""

import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages storage of crawl results, with options for memory-only or disk-based storage.
    """
    
    def __init__(
        self,
        store_html_content: bool = True,
        storage_dir: Optional[str] = None,
        enable_disk_storage: bool = False
    ):
        """
        Initialize the storage manager.
        
        Args:
            store_html_content: Whether to store HTML content in results (default: True)
            storage_dir: Directory for disk-based storage (if enable_disk_storage is True)
            enable_disk_storage: Whether to store HTML content on disk instead of memory
        """
        self.store_html_content = store_html_content
        self.enable_disk_storage = enable_disk_storage
        self.storage_dir = Path(storage_dir) if storage_dir else None
        
        # Create storage directory if needed
        if self.enable_disk_storage:
            if self.storage_dir:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
            else:
                # Use default storage directory
                self.storage_dir = Path.home() / '.crawlit' / 'storage'
                self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Disk storage enabled at {self.storage_dir}")
        else:
            logger.info(f"Memory storage mode (store_html_content={store_html_content})")
    
    def _get_storage_path(self, url: str) -> Path:
        """Get the file path for storing HTML content"""
        if not self.storage_dir:
            raise ValueError("Disk storage not enabled")
        cache_key = hashlib.md5(url.encode('utf-8')).hexdigest()
        return self.storage_dir / f"{cache_key}.html"
    
    def store_html(self, url: str, html_content: str) -> Optional[str]:
        """
        Store HTML content based on configuration.
        
        Args:
            url: The URL the HTML belongs to
            html_content: The HTML content to store
            
        Returns:
            The stored content (if in memory) or a reference path (if on disk), or None if not storing
        """
        if not self.store_html_content:
            return None
        
        if self.enable_disk_storage and self.storage_dir:
            # Store on disk
            storage_path = self._get_storage_path(url)
            try:
                with open(storage_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.debug(f"Stored HTML to disk: {url} -> {storage_path}")
                return str(storage_path)  # Return path as reference
            except Exception as e:
                logger.warning(f"Error storing HTML to disk for {url}: {e}")
                # Fallback to memory if disk storage fails
                return html_content
        else:
            # Store in memory
            return html_content
    
    def get_html(self, url: str, stored_reference: Any) -> Optional[str]:
        """
        Retrieve HTML content from storage.
        
        Args:
            url: The URL the HTML belongs to
            stored_reference: Either the HTML content (if in memory) or a file path (if on disk)
            
        Returns:
            The HTML content or None if not available
        """
        if stored_reference is None:
            return None
        
        # If it's a string and looks like a file path, try to read from disk
        if isinstance(stored_reference, str) and os.path.exists(stored_reference):
            try:
                with open(stored_reference, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Error reading HTML from disk for {url}: {e}")
                return None
        
        # Otherwise, assume it's the HTML content itself
        return stored_reference
    
    def remove_html(self, url: str, stored_reference: Any) -> None:
        """
        Remove stored HTML content.
        
        Args:
            url: The URL the HTML belongs to
            stored_reference: Either the HTML content (if in memory) or a file path (if on disk)
        """
        if stored_reference and isinstance(stored_reference, str) and os.path.exists(stored_reference):
            try:
                os.unlink(stored_reference)
                logger.debug(f"Removed HTML from disk: {url}")
            except Exception as e:
                logger.warning(f"Error removing HTML from disk for {url}: {e}")
    
    def clear_storage(self) -> None:
        """Clear all stored HTML content"""
        if self.enable_disk_storage and self.storage_dir:
            try:
                for html_file in self.storage_dir.glob('*.html'):
                    html_file.unlink()
                logger.info(f"Cleared disk storage at {self.storage_dir}")
            except Exception as e:
                logger.warning(f"Error clearing disk storage: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        disk_count = 0
        if self.enable_disk_storage and self.storage_dir:
            try:
                disk_count = len(list(self.storage_dir.glob('*.html')))
            except Exception:
                pass
        
        return {
            'store_html_content': self.store_html_content,
            'disk_storage_enabled': self.enable_disk_storage,
            'disk_files': disk_count,
            'storage_dir': str(self.storage_dir) if self.storage_dir else None
        }


