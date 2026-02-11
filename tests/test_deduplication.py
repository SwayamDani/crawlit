#!/usr/bin/env python3
"""
Tests for content-based deduplication
"""

import pytest
from crawlit.utils.deduplication import ContentDeduplicator
from crawlit.crawler.engine import Crawler
from crawlit.crawler.async_engine import AsyncCrawler


class TestContentDeduplicator:
    """Test ContentDeduplicator class"""
    
    def test_exact_duplicate_detection(self):
        """Test detection of exact duplicate content"""
        cd = ContentDeduplicator(enabled=True, normalize_content=False, min_content_length=10)
        
        content1 = "<html><body>Test content with enough length to pass minimum threshold</body></html>"
        content2 = "<html><body>Test content with enough length to pass minimum threshold</body></html>"
        
        # First content should not be duplicate
        assert cd.is_duplicate(content1, "https://example.com/page1") is False
        
        # Second content should be duplicate
        assert cd.is_duplicate(content2, "https://example.com/page2") is True
    
    def test_normalized_duplicate_detection(self):
        """Test detection of duplicates with normalized content"""
        cd = ContentDeduplicator(enabled=True, normalize_content=True, min_content_length=10)
        
        content1 = "<html><body>Test   content with enough length to pass minimum threshold</body></html>"
        content2 = "<html><body>Test content with enough length to pass minimum threshold</body></html>"
        
        # First content should not be duplicate
        assert cd.is_duplicate(content1, "https://example.com/page1") is False
        
        # Second content should be duplicate (normalized)
        assert cd.is_duplicate(content2, "https://example.com/page2") is True
    
    def test_different_content(self):
        """Test that different content is not marked as duplicate"""
        cd = ContentDeduplicator(enabled=True, min_content_length=10)
        
        content1 = "<html><body>First content with enough length to pass minimum threshold</body></html>"
        content2 = "<html><body>Second content with enough length to pass minimum threshold</body></html>"
        
        assert cd.is_duplicate(content1, "https://example.com/page1") is False
        assert cd.is_duplicate(content2, "https://example.com/page2") is False
    
    def test_min_content_length(self):
        """Test that content below minimum length is not checked"""
        cd = ContentDeduplicator(enabled=True, min_content_length=100)
        
        short_content = "Short"
        
        # Should return False (not duplicate) because content is too short
        assert cd.is_duplicate(short_content, "https://example.com/page1") is False
    
    def test_get_duplicate_urls(self):
        """Test getting URLs with duplicate content"""
        cd = ContentDeduplicator(enabled=True, min_content_length=10)
        
        content = "<html><body>Test content with enough length to pass minimum threshold</body></html>"
        
        # Add first URL
        cd.is_duplicate(content, "https://example.com/page1")
        
        # Add duplicate URL
        cd.is_duplicate(content, "https://example.com/page2")
        
        # Get duplicate URLs for page1
        duplicates = cd.get_duplicate_urls("https://example.com/page1")
        assert duplicates is not None
        assert "https://example.com/page2" in duplicates
    
    def test_get_stats(self):
        """Test getting deduplication statistics"""
        cd = ContentDeduplicator(enabled=True, min_content_length=10)
        
        content1 = "<html><body>First content with enough length to pass minimum threshold</body></html>"
        content2 = "<html><body>First content with enough length to pass minimum threshold</body></html>"
        content3 = "<html><body>Second content with enough length to pass minimum threshold</body></html>"
        
        cd.is_duplicate(content1, "https://example.com/page1")
        cd.is_duplicate(content2, "https://example.com/page2")  # Duplicate
        cd.is_duplicate(content3, "https://example.com/page3")
        
        stats = cd.get_stats()
        assert stats['enabled'] is True
        assert stats['total_checked'] == 3
        assert stats['duplicates_found'] == 1
        assert stats['unique_content_count'] == 2
        assert stats['duplicate_rate'] == pytest.approx(1.0 / 3.0, rel=0.1)
    
    def test_clear(self):
        """Test clearing deduplicator state"""
        cd = ContentDeduplicator(enabled=True, min_content_length=10)
        
        content = "<html><body>Test content with enough length to pass minimum threshold</body></html>"
        cd.is_duplicate(content, "https://example.com/page1")
        
        cd.clear()
        
        stats = cd.get_stats()
        assert stats['total_checked'] == 0
        assert stats['duplicates_found'] == 0
        assert stats['unique_content_count'] == 0
    
    def test_disabled(self):
        """Test that disabled deduplicator doesn't detect duplicates"""
        cd = ContentDeduplicator(enabled=False, min_content_length=10)
        
        content = "<html><body>Test content with enough length to pass minimum threshold</body></html>"
        
        # Should always return False when disabled
        assert cd.is_duplicate(content, "https://example.com/page1") is False
        assert cd.is_duplicate(content, "https://example.com/page2") is False


class TestCrawlerWithDeduplication:
    """Test crawler integration with deduplication"""
    
    def test_crawler_with_deduplicator(self, mock_website):
        """Test crawler with custom deduplicator"""
        cd = ContentDeduplicator(enabled=True)
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            content_deduplicator=cd,
            enable_content_deduplication=True
        )
        
        assert crawler.enable_content_deduplication is True
        assert crawler.content_deduplicator is cd
        assert crawler.content_deduplicator.enabled is True
    
    def test_crawler_without_deduplicator(self, mock_website):
        """Test crawler without deduplicator (disabled)"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            enable_content_deduplication=False
        )
        
        assert crawler.enable_content_deduplication is False
        assert crawler.content_deduplicator.enabled is False
    
    def test_crawler_auto_creates_deduplicator(self, mock_website):
        """Test that crawler auto-creates deduplicator when enabled"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            enable_content_deduplication=True
        )
        
        assert crawler.enable_content_deduplication is True
        assert crawler.content_deduplicator is not None
        assert crawler.content_deduplicator.enabled is True


@pytest.mark.asyncio
class TestAsyncCrawlerWithDeduplication:
    """Test async crawler integration with deduplication"""
    
    async def test_async_crawler_with_deduplicator(self, mock_website):
        """Test async crawler with custom deduplicator"""
        cd = ContentDeduplicator(enabled=True)
        
        crawler = AsyncCrawler(
            start_url=mock_website,
            max_depth=0,
            content_deduplicator=cd,
            enable_content_deduplication=True
        )
        
        assert crawler.enable_content_deduplication is True
        assert crawler.content_deduplicator is cd
        assert crawler.content_deduplicator.enabled is True
    
    async def test_async_crawler_auto_creates_deduplicator(self, mock_website):
        """Test that async crawler auto-creates deduplicator when enabled"""
        crawler = AsyncCrawler(
            start_url=mock_website,
            max_depth=0,
            enable_content_deduplication=True
        )
        
        assert crawler.enable_content_deduplication is True
        assert crawler.content_deduplicator is not None
        assert crawler.content_deduplicator.enabled is True

