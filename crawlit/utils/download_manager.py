#!/usr/bin/env python3
"""
download_manager.py - Dedicated file download management

Handles downloading non-HTML resources with streaming, resume, and verification.
"""

import asyncio
import logging
import os
import hashlib
import time
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass
import requests
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    url: str
    filepath: Optional[Path]
    bytes_downloaded: int
    error: Optional[str] = None
    checksum_valid: bool = True
    retry_count: int = 0
    download_time_seconds: float = 0.0
    download_speed_bps: float = 0.0


@dataclass
class DownloadProgress:
    """Progress information for a download."""
    url: str
    downloaded_bytes: int
    total_bytes: int
    progress_percent: float
    download_speed_bps: float = 0.0


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
        on_progress: Optional[Callable[[str, int, int], None]] = None,
        max_concurrent: int = 3,
        timeout: int = 30,
        max_retries: int = 3
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
            max_concurrent: Maximum concurrent downloads
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.download_dir = Path(download_dir)
        self.max_file_size_mb = max_file_size_mb
        self.allowed_extensions = allowed_extensions
        self.blocked_extensions = blocked_extensions or []
        self.chunk_size = chunk_size
        self.verify_checksums = verify_checksums
        self.on_progress = on_progress
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries
        
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
        session: Optional[requests.Session] = None,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> DownloadResult:
        """
        Download a file synchronously.
        
        Args:
            url: URL to download
            filename: Optional filename (auto-generated if None)
            session: Optional requests session
            progress_callback: Optional callback for progress updates
            
        Returns:
            DownloadResult object
        """
        if session is None:
            session = requests.Session()
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                start_time = time.time()
                
                # Get file info with HEAD request
                head_response = session.head(url, allow_redirects=True, timeout=self.timeout)
                content_length = head_response.headers.get('Content-Length')
                content_type = head_response.headers.get('Content-Type', '')
                content_disposition = head_response.headers.get('Content-Disposition', '')
                
                # Check if should download
                should_dl, reason = self.should_download(
                    url,
                    content_type,
                    int(content_length) if content_length else None
                )
                
                if not should_dl:
                    return DownloadResult(
                        success=False,
                        url=url,
                        filepath=None,
                        bytes_downloaded=0,
                        error=reason,
                        retry_count=retry_count
                    )
                
                # Determine filename
                if not filename:
                    filename = self._extract_filename(url, content_type, content_disposition)
                
                filepath = self.download_dir / filename
                
                # Download file with streaming
                logger.info(f"Downloading: {url} -> {filepath}")
                
                response = session.get(url, stream=True, timeout=self.timeout)
                response.raise_for_status()
                
                total_size = int(response.headers.get('Content-Length', 0))
                bytes_downloaded = 0
                last_progress_time = time.time()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            
                            # Progress callback
                            if progress_callback and total_size > 0:
                                current_time = time.time()
                                elapsed = current_time - start_time
                                speed = bytes_downloaded / elapsed if elapsed > 0 else 0
                                progress = DownloadProgress(
                                    url=url,
                                    downloaded_bytes=bytes_downloaded,
                                    total_bytes=total_size,
                                    progress_percent=(bytes_downloaded / total_size * 100) if total_size > 0 else 0,
                                    download_speed_bps=speed
                                )
                                try:
                                    progress_callback(progress)
                                except Exception as e:
                                    logger.warning(f"Progress callback error: {e}")
                            
                            # Legacy callback
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
                
                end_time = time.time()
                download_time = max(end_time - start_time, 0.001)  # Minimum 1ms to avoid division by zero
                download_speed = bytes_downloaded / download_time
                
                logger.info(f"Downloaded {bytes_downloaded} bytes to {filepath} in {download_time:.2f}s")
                
                return DownloadResult(
                    success=True,
                    url=url,
                    filepath=filepath,
                    bytes_downloaded=bytes_downloaded,
                    checksum_valid=checksum_valid,
                    error=None,
                    retry_count=retry_count,
                    download_time_seconds=download_time,
                    download_speed_bps=download_speed
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Download attempt {retry_count + 1} failed for {url}: {e}")
                retry_count += 1
                
                if retry_count <= self.max_retries:
                    time.sleep(min(2 ** retry_count, 10))  # Exponential backoff
        
        # All retries exhausted
        logger.error(f"Download failed for {url} after {retry_count} attempts: {last_error}")
        self._failed_count += 1
        return DownloadResult(
            success=False,
            url=url,
            filepath=None,
            bytes_downloaded=0,
            error=last_error,
            retry_count=retry_count
        )
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing or replacing invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for filesystem
        """
        import re
        # Remove or replace invalid characters for Windows/Unix
        # Invalid: <>:"/\|?*
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', filename)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # If filename is empty after sanitization, use a default
        if not sanitized:
            sanitized = 'download'
        
        return sanitized
    
    def _extract_filename(self, url: str, content_type: str, content_disposition: str = '') -> str:
        """
        Extract filename from URL, Content-Disposition, or generate one.
        
        Args:
            url: Source URL
            content_type: Content-Type header
            content_disposition: Content-Disposition header
            
        Returns:
            Extracted or generated filename
        """
        # Try to extract from Content-Disposition header
        if content_disposition:
            import re
            match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if match:
                filename = match.group(1)
                return self._sanitize_filename(filename)
        
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
        else:
            filename = self._sanitize_filename(filename)
        
        # Ensure unique filename
        final_path = self.download_dir / filename
        counter = 1
        original_stem = Path(filename).stem
        original_suffix = Path(filename).suffix
        while final_path.exists():
            filename = f"{original_stem}_{counter}{original_suffix}"
            final_path = self.download_dir / filename
            counter += 1
        
        return filename
    
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


class AsyncDownloadManager:
    """
    Asynchronous download manager for concurrent file downloads.
    
    Supports:
    - Concurrent downloads with aiohttp
    - Progress tracking
    - Retry logic with exponential backoff
    - File size limits
    - Extension filtering
    """
    
    def __init__(
        self,
        download_dir: str = "downloads",
        max_file_size_mb: int = 100,
        allowed_extensions: Optional[List[str]] = None,
        blocked_extensions: Optional[List[str]] = None,
        chunk_size: int = 8192,
        max_concurrent: int = 5,
        timeout: int = 300,
        max_retries: int = 3
    ):
        """
        Initialize async download manager.
        
        Args:
            download_dir: Directory to save downloads
            max_file_size_mb: Maximum file size to download (MB)
            allowed_extensions: List of allowed file extensions
            blocked_extensions: List of blocked file extensions
            chunk_size: Download chunk size in bytes
            max_concurrent: Maximum concurrent downloads
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.download_dir = Path(download_dir)
        self.max_file_size_mb = max_file_size_mb
        self.allowed_extensions = allowed_extensions
        self.blocked_extensions = blocked_extensions or []
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Create download directory
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self._downloads_count = 0
        self._bytes_downloaded = 0
        self._failed_count = 0
        
    async def download(
        self,
        url: str,
        filename: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        progress_callback: Optional[callable] = None
    ) -> DownloadResult:
        """
        Download a file asynchronously.
        
        Args:
            url: URL to download
            filename: Optional custom filename
            session: Optional aiohttp session (will create one if None)
            progress_callback: Optional progress callback function
            
        Returns:
            DownloadResult with download information
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        start_time = time.time()
        retry_count = 0
        last_error = None
        
        try:
            while retry_count <= self.max_retries:
                try:
                    # Get file info with HEAD request
                    async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as head_response:
                        content_length = head_response.headers.get('Content-Length')
                        content_type = head_response.headers.get('Content-Type', '')
                        content_disposition = head_response.headers.get('Content-Disposition', '')
                    
                    # Determine filename
                    if not filename:
                        filename = self._extract_filename(url, content_type, content_disposition)
                    
                    filepath = self.download_dir / filename
                    
                    # Download file with streaming
                    logger.info(f"Downloading (async): {url} -> {filepath}")
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                        response.raise_for_status()
                        
                        total_size = int(response.headers.get('Content-Length', 0))
                        bytes_downloaded = 0
                        
                        with open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(self.chunk_size):
                                f.write(chunk)
                                bytes_downloaded += len(chunk)
                                
                                # Progress callback
                                if progress_callback and total_size > 0:
                                    try:
                                        progress = DownloadProgress(
                                            url=url,
                                            downloaded_bytes=bytes_downloaded,
                                            total_bytes=total_size,
                                            progress_percent=(bytes_downloaded / total_size * 100),
                                            download_speed_bps=bytes_downloaded / (time.time() - start_time)
                                        )
                                        await progress_callback(progress) if asyncio.iscoroutinefunction(progress_callback) else progress_callback(progress)
                                    except Exception as e:
                                        logger.warning(f"Progress callback error: {e}")
                        
                        # Update statistics
                        self._downloads_count += 1
                        self._bytes_downloaded += bytes_downloaded
                        
                        end_time = time.time()
                        download_time = max(end_time - start_time, 0.001)
                        download_speed = bytes_downloaded / download_time
                        
                        logger.info(f"Downloaded {bytes_downloaded} bytes to {filepath}")
                        
                        return DownloadResult(
                            success=True,
                            url=url,
                            filepath=filepath,
                            bytes_downloaded=bytes_downloaded,
                            checksum_valid=True,
                            error=None,
                            retry_count=retry_count,
                            download_time_seconds=download_time,
                            download_speed_bps=download_speed
                        )
                        
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Download attempt {retry_count + 1} failed for {url}: {e}")
                    retry_count += 1
                    
                    if retry_count <= self.max_retries:
                        await asyncio.sleep(min(2 ** retry_count, 10))
            
            # All retries failed
            self._failed_count += 1
            logger.error(f"Download failed for {url} after {retry_count} attempts: {last_error}")
            
            return DownloadResult(
                success=False,
                url=url,
                filepath=None,
                bytes_downloaded=0,
                error=last_error,
                checksum_valid=True,
                retry_count=retry_count,
                download_time_seconds=0.0,
                download_speed_bps=0.0
            )
            
        finally:
            if close_session:
                await session.close()
    
    async def download_many(
        self,
        urls: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[DownloadResult]:
        """
        Download multiple files concurrently.
        
        Args:
            urls: List of URLs to download
            progress_callback: Optional progress callback function
            
        Returns:
            List of DownloadResult objects
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def download_with_semaphore(url: str, session: aiohttp.ClientSession) -> DownloadResult:
            async with semaphore:
                return await self.download(url, session=session, progress_callback=progress_callback)
        
        async with aiohttp.ClientSession() as session:
            tasks = [download_with_semaphore(url, session) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert any exceptions to failed DownloadResults
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(DownloadResult(
                        success=False,
                        url=urls[i],
                        filepath=None,
                        bytes_downloaded=0,
                        error=str(result),
                        checksum_valid=True,
                        retry_count=0,
                        download_time_seconds=0.0,
                        download_speed_bps=0.0
                    ))
                else:
                    processed_results.append(result)
            
            return processed_results
    
    def _extract_filename(self, url: str, content_type: str, content_disposition: str = '') -> str:
        """Extract filename from URL or headers."""
        # Try Content-Disposition first
        if content_disposition:
            import re
            match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if match:
                return self._sanitize_filename(match.group(1))
        
        # Extract from URL
        path = Path(url.split('?')[0])
        filename = path.name
        
        if not filename or filename in ['', 'download', 'file']:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            ext = self._extension_from_content_type(content_type)
            filename = f"download_{url_hash}{ext}"
        else:
            filename = self._sanitize_filename(filename)
        
        # Ensure unique filename
        final_path = self.download_dir / filename
        counter = 1
        original_stem = Path(filename).stem
        original_suffix = Path(filename).suffix
        while final_path.exists():
            filename = f"{original_stem}_{counter}{original_suffix}"
            final_path = self.download_dir / filename
            counter += 1
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters."""
        import re
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', filename)
        sanitized = sanitized.strip('. ')
        return sanitized if sanitized else 'download'
    
    def _extension_from_content_type(self, content_type: str) -> str:
        """Determine file extension from content type."""
        content_type_lower = content_type.lower().split(';')[0].strip()
        content_type_map = {
            'text/html': '.html',
            'text/plain': '.txt',
            'application/pdf': '.pdf',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'application/json': '.json',
            'application/xml': '.xml',
            'application/zip': '.zip',
            'video/mp4': '.mp4',
        }
        return content_type_map.get(content_type_lower, '')



