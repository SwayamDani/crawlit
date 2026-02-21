#!/usr/bin/env python3
"""
incremental.py - Incremental crawling with ETags and Last-Modified

Enables crawling only changed pages using conditional HTTP requests.
"""

import logging
import json
import sqlite3
import pickle
import threading
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import hashlib

logger = logging.getLogger(__name__)


class IncrementalState:
    """
    Manages incremental crawling state for URLs.
    
    Tracks ETags, Last-Modified headers, content hashes, and timestamps
    to determine if URLs need to be re-crawled.
    """
    
    def __init__(self):
        """Initialize empty state."""
        self._state: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for consistent storage.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        # Basic normalization - can be extended
        return url.strip()
    
    def set_url_state(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content_hash: Optional[str] = None
    ) -> None:
        """
        Set the state for a URL.
        
        Args:
            url: URL to set state for
            etag: ETag header value
            last_modified: Last-Modified header value
            content_hash: Content hash value
        """
        url = self._normalize_url(url)
        
        with self._lock:
            if url not in self._state:
                self._state[url] = {}
            
            if etag is not None:
                self._state[url]['etag'] = etag
            if last_modified is not None:
                self._state[url]['last_modified'] = last_modified
            if content_hash is not None:
                self._state[url]['content_hash'] = content_hash
            
            self._state[url]['last_crawled'] = datetime.now(timezone.utc).isoformat()
    
    def get_url_state(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get the state for a URL.
        
        Args:
            url: URL to get state for
            
        Returns:
            Dictionary with state data or None if not found
        """
        url = self._normalize_url(url)
        
        with self._lock:
            return self._state.get(url)
    
    def should_crawl(
        self,
        url: str,
        current_etag: Optional[str] = None,
        current_last_modified: Optional[str] = None,
        current_content_hash: Optional[str] = None,
        force: bool = False,
        max_age_hours: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Determine if a URL should be crawled.
        
        Args:
            url: URL to check
            current_etag: Current ETag value
            current_last_modified: Current Last-Modified value
            current_content_hash: Current content hash
            force: Force crawl regardless of state
            max_age_hours: Maximum age in hours before forced re-crawl
            
        Returns:
            Tuple of (should_crawl: bool, reason: str)
        """
        if force:
            return True, "forced"
        
        url = self._normalize_url(url)
        
        with self._lock:
            state = self._state.get(url)
            
            if not state:
                return True, "new_url"
            
            # Check max age
            if max_age_hours is not None:
                last_crawled_str = state.get('last_crawled')
                if last_crawled_str:
                    try:
                        last_crawled = datetime.fromisoformat(last_crawled_str)
                        age = datetime.now(timezone.utc) - last_crawled
                        if age > timedelta(hours=max_age_hours):
                            return True, "expired"
                    except Exception as e:
                        logger.warning(f"Failed to parse last_crawled time: {e}")
            
            # ETag has priority
            if current_etag is not None and 'etag' in state:
                if current_etag == state['etag']:
                    return False, "etag_match"
                else:
                    return True, "etag_changed"
            
            # Then check Last-Modified
            if current_last_modified is not None and 'last_modified' in state:
                if current_last_modified == state['last_modified']:
                    return False, "last_modified_match"
                else:
                    return True, "last_modified_changed"
            
            # Finally check content hash
            if current_content_hash is not None and 'content_hash' in state:
                if current_content_hash == state['content_hash']:
                    return False, "content_match"
                else:
                    return True, "content_changed"
            
            # If we have no way to compare, assume we should crawl
            return True, "no_comparison_data"
    
    def remove_url(self, url: str) -> bool:
        """
        Remove a URL from state.
        
        Args:
            url: URL to remove
            
        Returns:
            True if URL was removed, False if it didn't exist
        """
        url = self._normalize_url(url)
        
        with self._lock:
            if url in self._state:
                del self._state[url]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all state."""
        with self._lock:
            self._state.clear()
    
    def is_empty(self) -> bool:
        """Check if state is empty."""
        with self._lock:
            return len(self._state) == 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the state.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            total_urls = len(self._state)
            urls_with_etag = sum(1 for s in self._state.values() if 'etag' in s and s['etag'])
            urls_with_last_modified = sum(1 for s in self._state.values() if 'last_modified' in s and s['last_modified'])
            urls_with_content_hash = sum(1 for s in self._state.values() if 'content_hash' in s and s['content_hash'])
            
            return {
                'total_urls': total_urls,
                'urls_with_etag': urls_with_etag,
                'urls_with_last_modified': urls_with_last_modified,
                'urls_with_content_hash': urls_with_content_hash
            }
    
    def __len__(self) -> int:
        """Return number of URLs in state."""
        with self._lock:
            return len(self._state)
    
    def __contains__(self, url: str) -> bool:
        """Check if URL is in state."""
        url = self._normalize_url(url)
        with self._lock:
            return url in self._state
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Export state as dictionary."""
        with self._lock:
            return dict(self._state)
    
    def from_dict(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Import state from dictionary."""
        with self._lock:
            self._state = dict(data)


class StateManager:
    """
    Manages saving and loading IncrementalState to/from disk.
    """
    
    def __init__(
        self,
        filepath: str,
        format: str = 'json',
        auto_save: bool = False
    ):
        """
        Initialize state manager.
        
        Args:
            filepath: Path to state file
            format: File format ('json' or 'pickle')
            auto_save: Whether to auto-save (not implemented yet)
        """
        self.filepath = Path(filepath)
        self.format = format.lower()
        self.auto_save = auto_save
        
        if self.format not in ('json', 'pickle'):
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'pickle'")
    
    def save(self, state: IncrementalState) -> None:
        """
        Save state to file.
        
        Args:
            state: IncrementalState to save
        """
        # Ensure directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        state_dict = state.to_dict()
        
        if self.format == 'json':
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
        elif self.format == 'pickle':
            with open(self.filepath, 'wb') as f:
                pickle.dump(state_dict, f)
        
        logger.debug(f"Saved state to {self.filepath} ({len(state)} URLs)")
    
    def load(self) -> IncrementalState:
        """
        Load state from file.
        
        Returns:
            IncrementalState loaded from file, or empty state if file doesn't exist
        """
        if not self.filepath.exists():
            logger.debug(f"State file {self.filepath} does not exist, returning empty state")
            return IncrementalState()
        
        try:
            if self.format == 'json':
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    state_dict = json.load(f)
            elif self.format == 'pickle':
                with open(self.filepath, 'rb') as f:
                    state_dict = pickle.load(f)
            
            state = IncrementalState()
            state.from_dict(state_dict)
            
            logger.debug(f"Loaded state from {self.filepath} ({len(state)} URLs)")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state from {self.filepath}: {e}")
            return IncrementalState()


class IncrementalCrawler:
    """
    Manages incremental crawling state using ETags and Last-Modified headers.
    
    Stores metadata from previous crawls and uses it to send conditional requests.
    Handles 304 Not Modified responses efficiently.
    """
    
    def __init__(
        self,
        storage_path: str = './incremental_crawl.db',
        use_content_hash: bool = True,
        force_refresh: bool = False
    ):
        """
        Initialize the incremental crawler.
        
        Args:
            storage_path: Path to SQLite database for storing metadata
            use_content_hash: Whether to also track content hashes
            force_refresh: Force refresh all pages (ignore stored metadata)
        """
        self.storage_path = Path(storage_path)
        self.use_content_hash = use_content_hash
        self.force_refresh = force_refresh
        
        # Initialize database
        self._init_database()
        
        logger.debug(f"Incremental crawler initialized: storage={storage_path}, force_refresh={force_refresh}")
    
    def _init_database(self) -> None:
        """Initialize the SQLite database."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        # Create table for storing page metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS page_metadata (
                url TEXT PRIMARY KEY,
                etag TEXT,
                last_modified TEXT,
                content_hash TEXT,
                last_crawled TEXT,
                crawl_count INTEGER DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.debug("Incremental crawl database initialized")
    
    def get_conditional_headers(self, url: str) -> Dict[str, str]:
        """
        Get conditional request headers for a URL.
        
        Args:
            url: URL to check
            
        Returns:
            Dictionary with If-None-Match and/or If-Modified-Since headers
        """
        if self.force_refresh:
            return {}
        
        try:
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT etag, last_modified FROM page_metadata WHERE url = ?',
                (url,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {}
            
            headers = {}
            etag, last_modified = row
            
            if etag:
                headers['If-None-Match'] = etag
            
            if last_modified:
                headers['If-Modified-Since'] = last_modified
            
            logger.debug(f"Using conditional headers for {url}: {headers}")
            return headers
            
        except Exception as e:
            logger.error(f"Failed to get conditional headers for {url}: {e}")
            return {}
    
    def record_response(
        self,
        url: str,
        status_code: int,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content: Optional[str] = None
    ) -> None:
        """
        Record response metadata for future incremental crawls.
        
        Args:
            url: URL that was crawled
            status_code: HTTP status code
            etag: ETag header value
            last_modified: Last-Modified header value
            content: Page content (for hash calculation)
        """
        try:
            # Calculate content hash if enabled
            content_hash = None
            if self.use_content_hash and content:
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            
            # Check if URL exists
            cursor.execute('SELECT crawl_count FROM page_metadata WHERE url = ?', (url,))
            row = cursor.fetchone()
            
            now = datetime.now().isoformat()
            
            if row:
                # Update existing record
                crawl_count = row[0] + 1
                cursor.execute('''
                    UPDATE page_metadata
                    SET etag = ?, last_modified = ?, content_hash = ?,
                        last_crawled = ?, crawl_count = ?
                    WHERE url = ?
                ''', (etag, last_modified, content_hash, now, crawl_count, url))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO page_metadata
                    (url, etag, last_modified, content_hash, last_crawled, crawl_count)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (url, etag, last_modified, content_hash, now))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Recorded metadata for {url}")
            
        except Exception as e:
            logger.error(f"Failed to record metadata for {url}: {e}")
    
    def is_modified(self, url: str, content: Optional[str] = None) -> bool:
        """
        Check if a URL's content has been modified since last crawl.
        
        Args:
            url: URL to check
            content: Current content for comparison
            
        Returns:
            True if content is new or modified
        """
        if self.force_refresh:
            return True
        
        if not self.use_content_hash or not content:
            return True
        
        try:
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT content_hash FROM page_metadata WHERE url = ?',
                (url,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if not row or not row[0]:
                return True
            
            # Calculate current content hash
            current_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Compare hashes
            is_modified = current_hash != row[0]
            
            if not is_modified:
                logger.debug(f"Content unchanged for {url}")
            
            return is_modified
            
        except Exception as e:
            logger.error(f"Failed to check if modified for {url}: {e}")
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored page metadata.
        
        Returns:
            Dictionary with statistics
        """
        try:
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            
            # Total pages
            cursor.execute('SELECT COUNT(*) FROM page_metadata')
            total_pages = cursor.fetchone()[0]
            
            # Pages with ETags
            cursor.execute('SELECT COUNT(*) FROM page_metadata WHERE etag IS NOT NULL')
            pages_with_etag = cursor.fetchone()[0]
            
            # Pages with Last-Modified
            cursor.execute('SELECT COUNT(*) FROM page_metadata WHERE last_modified IS NOT NULL')
            pages_with_last_modified = cursor.fetchone()[0]
            
            # Average crawl count
            cursor.execute('SELECT AVG(crawl_count) FROM page_metadata')
            avg_crawl_count = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_pages': total_pages,
                'pages_with_etag': pages_with_etag,
                'pages_with_last_modified': pages_with_last_modified,
                'avg_crawl_count': round(avg_crawl_count, 2),
                'storage_path': str(self.storage_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def clear_metadata(self, url: Optional[str] = None) -> None:
        """
        Clear stored metadata.
        
        Args:
            url: Specific URL to clear (None = clear all)
        """
        try:
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            
            if url:
                cursor.execute('DELETE FROM page_metadata WHERE url = ?', (url,))
                logger.info(f"Cleared metadata for {url}")
            else:
                cursor.execute('DELETE FROM page_metadata')
                logger.info("Cleared all metadata")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to clear metadata: {e}")
    
    def export_metadata(self, filepath: str) -> None:
        """
        Export metadata to JSON file.
        
        Args:
            filepath: Path to export file
        """
        try:
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM page_metadata')
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            metadata = []
            for row in rows:
                metadata.append({
                    'url': row[0],
                    'etag': row[1],
                    'last_modified': row[2],
                    'content_hash': row[3],
                    'last_crawled': row[4],
                    'crawl_count': row[5]
                })
            
            conn.close()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Exported {len(metadata)} records to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to export metadata: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
    
    def __len__(self) -> int:
        """Return the number of URLs tracked."""
        try:
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM page_metadata')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            return 0
    
    def set_url_state(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content_hash: Optional[str] = None
    ) -> None:
        """
        Set the state for a URL manually.
        
        This is an alias for record_response for API compatibility.
        
        Args:
            url: URL to set state for
            etag: ETag header value
            last_modified: Last-Modified header value
            content_hash: Content hash value
        """
        self.record_response(
            url=url,
            status_code=200,
            etag=etag,
            last_modified=last_modified,
            content=None  # Content hash provided directly
        )
    
    def should_crawl(
        self,
        url: str,
        current_etag: Optional[str] = None,
        current_last_modified: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Determine if a URL should be crawled based on stored metadata.
        
        Args:
            url: URL to check
            current_etag: Current ETag value from server
            current_last_modified: Current Last-Modified value from server
            
        Returns:
            Tuple of (should_crawl: bool, reason: str)
        """
        if self.force_refresh:
            return True, "force_refresh enabled"
        
        try:
            conn = sqlite3.connect(str(self.storage_path))
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT etag, last_modified FROM page_metadata WHERE url = ?',
                (url,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return True, "no previous metadata"
            
            stored_etag, stored_last_modified = row
            
            # Check if content has changed
            if current_etag and stored_etag:
                if current_etag == stored_etag:
                    return False, "etag unchanged"
                else:
                    return True, "etag changed"
            
            if current_last_modified and stored_last_modified:
                if current_last_modified == stored_last_modified:
                    return False, "last_modified unchanged"
                else:
                    return True, "last_modified changed"
            
            # If no comparison possible, crawl to be safe
            return True, "no comparison data available"
            
        except Exception as e:
            logger.error(f"Failed to check if {url} should be crawled: {e}")
            return True, f"error: {e}"

