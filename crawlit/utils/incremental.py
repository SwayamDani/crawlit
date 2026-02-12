#!/usr/bin/env python3
"""
incremental.py - Incremental crawling with ETags and Last-Modified

Enables crawling only changed pages using conditional HTTP requests.
"""

import logging
import json
import sqlite3
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


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

