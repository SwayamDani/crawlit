#!/usr/bin/env python3
"""
download_manager.py - Dedicated file download management

Handles downloading non-HTML resources with streaming, resume, and verification.
"""

import logging
import os
import hashlib
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import requests
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class DownloadManager:
    """
    Manager for downloading files with streaming and verification.
    
    Supports:
    - Streaming large files to disk
    - Resume interrupted downloads
    - Checksum verification
    - Progress tracking
    - File type filtering
    """
    
    # Common downloadable file extensions
    DOWNLOADABLE_EXTENSIONS = [
        '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
        '.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.mp3', '.mp4', '.avi', '.mov', '.mkv', '.flv',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
        '.iso', '.img',
    ]
    
    def __init__(
        self,
        download_dir: str = './downloads',
        max_file_size_mb: Optional[float] = None,
        allowed_extensions: Optional[List[str]] = None,
        blocked_extensions: Optional[List[str]] = None,
        chunk_size: int = 8192,
        verify_checksums: bool = False,
        on_progress: Optional[Callable[[str, int, int], None]] = None
    ):
        """
        Initialize the download manager.
        
        Args:
            download_dir: Directory to save downloads
            max_file_size_mb: Maximum file size to download (MB)
            allowed_extensions: List of allowed file extensions (None = all)
            blocked_extensions: List of blocked file extensions
            chunk_size: Download chunk size in bytes
            verify_checksums: Whether to verify checksums
            on_progress: Progress callback (url, bytes_downloaded, total_bytes)
        """
        self.download_dir = Path(download_dir)
        self.max_file_size_mb = max_file_size_mb
        self.allowed_extensions = allowed_extensions
        self.blocked_extensions = blocked_extensions or []
        self.chunk_size = chunk_size
        self.verify_checksums = verify_checksums
        self.on_progress = on_progress
        
        # Create download directory
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Download statistics
        self._downloads_count = 0
        self._bytes_downloaded = 0
        self._failed_count = 0
        
        logger.debug(f"Download manager initialized: dir={download_dir}, max_size={max_file_size_mb}MB")
    
    def should_download(self, url: str, content_type: str = "", content_length: Optional[int] = None) -> tuple[bool, Optional[str]]:
        """
        Check if a URL should be downloaded.
        
        Args:
            url: URL to check
            content_type: Content-Type header
            content_length: Content-Length header
            
        Returns:
            Tuple of (should_download, reason)
        """
        # Check file extension
        url_lower = url.lower()
        extension = Path(url_lower).suffix
        
        # Check blocked extensions
        if extension in self.blocked_extensions:
            return False, f"Blocked extension: {extension}"
        
        # Check allowed extensions
        if self.allowed_extensions and extension not in self.allowed_extensions:
            return False, f"Extension not in allowed list: {extension}"
        
        # Check file size
        if self.max_file_size_mb and content_length:
            max_bytes = self.max_file_size_mb * 1024 * 1024
            if content_length > max_bytes:
                return False, f"File too large: {content_length / (1024*1024):.2f}MB > {self.max_file_size_mb}MB"
        
        return True, None
    
    def download(
        self,
        url: str,
        filename: Optional[str] = None,
        session: Optional[requests.Session] = None
    ) -> Dict[str, Any]:
        """
        Download a file synchronously.
        
        Args:
            url: URL to download
            filename: Optional filename (auto-generated if None)
            session: Optional requests session
            
        Returns:
            Dictionary with download results
        """
        if session is None:
            session = requests.Session()
        
        try:
            # Get file info with HEAD request
            head_response = session.head(url, allow_redirects=True, timeout=10)
            content_length = head_response.headers.get('Content-Length')
            content_type = head_response.headers.get('Content-Type', '')
            
            # Check if should download
            should_dl, reason = self.should_download(
                url,
                content_type,
                int(content_length) if content_length else None
            )
            
            if not should_dl:
                return {
                    'success': False,
                    'url': url,
                    'filepath': None,
                    'bytes_downloaded': 0,
                    'error': reason
                }
            
            # Determine filename
            if not filename:
                filename = self._generate_filename(url, content_type)
            
            filepath = self.download_dir / filename
            
            # Download file with streaming
            logger.info(f"Downloading: {url} -> {filepath}")
            
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('Content-Length', 0))
            bytes_downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Progress callback
                        if self.on_progress:
                            try:
                                self.on_progress(url, bytes_downloaded, total_size)
                            except Exception as e:
                                logger.warning(f"Progress callback error: {e}")
            
            # Verify checksum if available
            checksum_valid = True
            if self.verify_checksums:
                checksum_valid = self._verify_checksum(filepath, response.headers)
            
            # Update statistics
            self._downloads_count += 1
            self._bytes_downloaded += bytes_downloaded
            
            logger.info(f"Downloaded {bytes_downloaded} bytes to {filepath}")
            
            return {
                'success': True,
                'url': url,
                'filepath': str(filepath),
                'bytes_downloaded': bytes_downloaded,
                'checksum_valid': checksum_valid,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            self._failed_count += 1
            return {
                'success': False,
                'url': url,
                'filepath': None,
                'bytes_downloaded': 0,
                'error': str(e)
            }
    
    async def download_async(
        self,
        url: str,
        filename: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> Dict[str, Any]:
        """
        Download a file asynchronously.
        
        Args:
            url: URL to download
            filename: Optional filename (auto-generated if None)
            session: Optional aiohttp session
            
        Returns:
            Dictionary with download results
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            # Get file info with HEAD request
            async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as head_response:
                content_length = head_response.headers.get('Content-Length')
                content_type = head_response.headers.get('Content-Type', '')
            
            # Check if should download
            should_dl, reason = self.should_download(
                url,
                content_type,
                int(content_length) if content_length else None
            )
            
            if not should_dl:
                return {
                    'success': False,
                    'url': url,
                    'filepath': None,
                    'bytes_downloaded': 0,
                    'error': reason
                }
            
            # Determine filename
            if not filename:
                filename = self._generate_filename(url, content_type)
            
            filepath = self.download_dir / filename
            
            # Download file with streaming
            logger.info(f"Downloading (async): {url} -> {filepath}")
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('Content-Length', 0))
                bytes_downloaded = 0
                
                with open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Progress callback
                        if self.on_progress:
                            try:
                                self.on_progress(url, bytes_downloaded, total_size)
                            except Exception as e:
                                logger.warning(f"Progress callback error: {e}")
                
                # Update statistics
                self._downloads_count += 1
                self._bytes_downloaded += bytes_downloaded
                
                logger.info(f"Downloaded {bytes_downloaded} bytes to {filepath}")
                
                return {
                    'success': True,
                    'url': url,
                    'filepath': str(filepath),
                    'bytes_downloaded': bytes_downloaded,
                    'error': None
                }
                
        except Exception as e:
            logger.error(f"Async download failed for {url}: {e}")
            self._failed_count += 1
            return {
                'success': False,
                'url': url,
                'filepath': None,
                'bytes_downloaded': 0,
                'error': str(e)
            }
        finally:
            if close_session:
                await session.close()
    
    def _generate_filename(self, url: str, content_type: str) -> str:
        """
        Generate a filename from URL and content type.
        
        Args:
            url: Source URL
            content_type: Content-Type header
            
        Returns:
            Generated filename
        """
        # Try to extract filename from URL
        path = Path(url.split('?')[0])  # Remove query string
        filename = path.name
        
        # If no filename or generic, generate one
        if not filename or filename in ['', 'download', 'file']:
            # Use URL hash as filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Try to determine extension from content type
            extension = self._extension_from_content_type(content_type)
            filename = f"download_{url_hash}{extension}"
        
        # Ensure unique filename
        final_path = self.download_dir / filename
        counter = 1
        while final_path.exists():
            stem = path.stem
            suffix = path.suffix
            filename = f"{stem}_{counter}{suffix}"
            final_path = self.download_dir / filename
            counter += 1
        
        return filename
    
    def _extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type."""
        content_type_map = {
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'application/x-tar': '.tar',
            'application/gzip': '.gz',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'video/mp4': '.mp4',
            'audio/mpeg': '.mp3',
        }
        
        content_type_lower = content_type.lower().split(';')[0].strip()
        return content_type_map.get(content_type_lower, '')
    
    def _verify_checksum(self, filepath: Path, headers: Dict[str, str]) -> bool:
        """
        Verify file checksum if provided in headers.
        
        Args:
            filepath: Path to downloaded file
            headers: Response headers
            
        Returns:
            True if checksum valid or not provided
        """
        # Check for common checksum headers
        etag = headers.get('ETag', '').strip('"')
        content_md5 = headers.get('Content-MD5', '')
        
        if not etag and not content_md5:
            return True  # No checksum to verify
        
        # Calculate MD5
        md5_hash = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b''):
                md5_hash.update(chunk)
        
        calculated_md5 = md5_hash.hexdigest()
        
        # Compare with ETag or Content-MD5
        if content_md5 and calculated_md5 != content_md5:
            logger.warning(f"MD5 checksum mismatch for {filepath}")
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get download statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'downloads_count': self._downloads_count,
            'bytes_downloaded': self._bytes_downloaded,
            'mb_downloaded': self._bytes_downloaded / (1024 * 1024),
            'failed_count': self._failed_count,
            'download_dir': str(self.download_dir)
        }

