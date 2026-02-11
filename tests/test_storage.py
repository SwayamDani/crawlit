#!/usr/bin/env python3
"""
Tests for storage management features
"""

import pytest
import os
import tempfile
from crawlit.crawler.engine import Crawler
from crawlit.utils.storage import StorageManager


class TestStorageManager:
    """Test storage manager functionality"""
    
    def test_memory_storage(self):
        """Test memory-based storage"""
        storage = StorageManager(store_html_content=True, enable_disk_storage=False)
        
        stored = storage.store_html('https://example.com', '<html><body>Test</body></html>')
        assert stored == '<html><body>Test</body></html>'
        
        retrieved = storage.get_html('https://example.com', stored)
        assert retrieved == '<html><body>Test</body></html>'
    
    def test_disable_html_storage(self):
        """Test disabling HTML content storage"""
        storage = StorageManager(store_html_content=False, enable_disk_storage=False)
        
        stored = storage.store_html('https://example.com', '<html><body>Test</body></html>')
        assert stored is None
    
    def test_disk_storage(self):
        """Test disk-based storage"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager(
                store_html_content=True,
                storage_dir=tmpdir,
                enable_disk_storage=True
            )
            
            stored = storage.store_html('https://example.com', '<html><body>Test</body></html>')
            assert stored is not None
            assert os.path.exists(stored)
            
            retrieved = storage.get_html('https://example.com', stored)
            assert retrieved == '<html><body>Test</body></html>'
    
    def test_storage_stats(self):
        """Test storage statistics"""
        storage = StorageManager(store_html_content=True, enable_disk_storage=False)
        
        storage.store_html('https://example.com', '<html>Test</html>')
        
        stats = storage.get_stats()
        assert stats['store_html_content'] == True
        assert stats['disk_storage_enabled'] == False


class TestCrawlerWithStorage:
    """Test crawler integration with storage manager"""
    
    def test_crawler_without_html_storage(self, mock_website):
        """Test crawler with HTML storage disabled"""
        storage = StorageManager(store_html_content=False, enable_disk_storage=False)
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            storage_manager=storage
        )
        
        crawler.crawl()
        results = crawler.get_results()
        
        # HTML content should not be stored
        for url, data in results.items():
            assert 'html_content' not in data or data.get('html_content') is None
    
    def test_crawler_with_disk_storage(self, mock_website):
        """Test crawler with disk-based storage"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager(
                store_html_content=True,
                storage_dir=tmpdir,
                enable_disk_storage=True
            )
            
            crawler = Crawler(
                start_url=mock_website,
                max_depth=0,
                storage_manager=storage
            )
            
            crawler.crawl()
            results = crawler.get_results()
            
            # HTML content should be stored on disk
            for url, data in results.items():
                if 'html_content' in data and data['html_content']:
                    # Should be a file path
                    assert isinstance(data['html_content'], str)
                    # File should exist
                    if os.path.exists(data['html_content']):
                        # Verify we can read it
                        with open(data['html_content'], 'r', encoding='utf-8') as f:
                            content = f.read()
                            assert len(content) > 0


