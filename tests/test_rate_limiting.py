#!/usr/bin/env python3
"""
Tests for per-domain rate limiting
"""

import pytest
import time
from crawlit.utils.rate_limiter import RateLimiter, AsyncRateLimiter
from crawlit.crawler.engine import Crawler
from crawlit.crawler.async_engine import AsyncCrawler


class TestRateLimiter:
    """Test RateLimiter class"""
    
    def test_default_delay(self):
        """Test default delay behavior"""
        rl = RateLimiter(default_delay=0.5)
        assert rl.default_delay == 0.5
    
    def test_set_domain_delay(self):
        """Test setting custom delay for a domain"""
        rl = RateLimiter(default_delay=0.1)
        rl.set_domain_delay("example.com", 1.0)
        
        assert rl.get_domain_delay("example.com") == 1.0
        assert rl.get_domain_delay("other.com") == 0.1  # Should use default
    
    def test_wait_if_needed(self):
        """Test that wait_if_needed respects delays"""
        rl = RateLimiter(default_delay=0.2)
        
        # First request should not wait
        start = time.time()
        rl.wait_if_needed("https://example.com/page1")
        first_duration = time.time() - start
        assert first_duration < 0.1  # Should be very fast
        
        # Second request to same domain should wait
        start = time.time()
        rl.wait_if_needed("https://example.com/page2")
        second_duration = time.time() - start
        assert second_duration >= 0.15  # Should wait approximately 0.2s
    
    def test_different_domains(self):
        """Test that different domains have independent delays"""
        rl = RateLimiter(default_delay=0.3)
        rl.set_domain_delay("example.com", 0.5)
        rl.set_domain_delay("test.com", 0.1)
        
        # Request to example.com
        rl.wait_if_needed("https://example.com/page1")
        
        # Request to test.com should not wait (different domain)
        start = time.time()
        rl.wait_if_needed("https://test.com/page1")
        duration = time.time() - start
        assert duration < 0.05  # Should be fast (different domain)
    
    def test_get_stats(self):
        """Test getting rate limiter statistics"""
        rl = RateLimiter(default_delay=0.1)
        rl.set_domain_delay("example.com", 0.5)
        rl.wait_if_needed("https://example.com/page1")
        
        stats = rl.get_stats()
        assert stats['default_delay'] == 0.1
        assert stats['domains_with_custom_delay'] == 1
        assert stats['domains_tracked'] == 1
        assert "example.com" in stats['domain_delays']
    
    def test_clear(self):
        """Test clearing rate limiter state"""
        rl = RateLimiter(default_delay=0.1)
        rl.set_domain_delay("example.com", 0.5)
        rl.wait_if_needed("https://example.com/page1")
        
        rl.clear()
        
        stats = rl.get_stats()
        assert stats['domains_with_custom_delay'] == 0
        assert stats['domains_tracked'] == 0


class TestCrawlerWithRateLimiting:
    """Test crawler integration with rate limiting"""
    
    def test_crawler_with_rate_limiter(self, mock_website):
        """Test crawler with custom rate limiter"""
        rl = RateLimiter(default_delay=0.1)
        rl.set_domain_delay("example.com", 0.2)
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            rate_limiter=rl,
            use_per_domain_delay=True
        )
        
        assert crawler.use_per_domain_delay is True
        assert crawler.rate_limiter is rl
    
    def test_crawler_without_rate_limiter(self, mock_website):
        """Test crawler without rate limiter (uses global delay)"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            delay=0.1,
            use_per_domain_delay=False
        )
        
        assert crawler.use_per_domain_delay is False
        assert crawler.rate_limiter.default_delay == 0.1
    
    def test_crawler_auto_creates_rate_limiter(self, mock_website):
        """Test that crawler auto-creates rate limiter when per-domain delay is enabled"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            delay=0.2,
            use_per_domain_delay=True
        )
        
        assert crawler.use_per_domain_delay is True
        assert crawler.rate_limiter is not None
        assert crawler.rate_limiter.default_delay == 0.2


@pytest.mark.asyncio
class TestAsyncRateLimiter:
    """Test AsyncRateLimiter class"""
    
    async def test_default_delay(self):
        """Test default delay behavior (async)"""
        rl = AsyncRateLimiter(default_delay=0.5)
        assert rl.default_delay == 0.5
    
    async def test_set_domain_delay(self):
        """Test setting custom delay for a domain (async)"""
        rl = AsyncRateLimiter(default_delay=0.1)
        await rl.set_domain_delay("example.com", 1.0)
        
        delay = await rl.get_domain_delay("example.com")
        assert delay == 1.0
        
        delay = await rl.get_domain_delay("other.com")
        assert delay == 0.1  # Should use default
    
    async def test_wait_if_needed(self):
        """Test that wait_if_needed respects delays (async)"""
        rl = AsyncRateLimiter(default_delay=0.2)
        
        # First request should not wait
        start = time.time()
        await rl.wait_if_needed("https://example.com/page1")
        first_duration = time.time() - start
        assert first_duration < 0.1  # Should be very fast
        
        # Second request to same domain should wait
        start = time.time()
        await rl.wait_if_needed("https://example.com/page2")
        second_duration = time.time() - start
        assert second_duration >= 0.15  # Should wait approximately 0.2s
    
    async def test_get_stats(self):
        """Test getting rate limiter statistics (async)"""
        rl = AsyncRateLimiter(default_delay=0.1)
        await rl.set_domain_delay("example.com", 0.5)
        await rl.wait_if_needed("https://example.com/page1")
        
        stats = await rl.get_stats()
        assert stats['default_delay'] == 0.1
        assert stats['domains_with_custom_delay'] == 1
        assert "example.com" in stats['domain_delays']


@pytest.mark.asyncio
class TestAsyncCrawlerWithRateLimiting:
    """Test async crawler integration with rate limiting"""
    
    async def test_async_crawler_with_rate_limiter(self, mock_website):
        """Test async crawler with custom rate limiter"""
        rl = AsyncRateLimiter(default_delay=0.1)
        await rl.set_domain_delay("example.com", 0.2)
        
        crawler = AsyncCrawler(
            start_url=mock_website,
            max_depth=0,
            rate_limiter=rl,
            use_per_domain_delay=True
        )
        
        assert crawler.use_per_domain_delay is True
        assert crawler.rate_limiter is rl
    
    async def test_async_crawler_auto_creates_rate_limiter(self, mock_website):
        """Test that async crawler auto-creates rate limiter when per-domain delay is enabled"""
        crawler = AsyncCrawler(
            start_url=mock_website,
            max_depth=0,
            delay=0.2,
            use_per_domain_delay=True
        )
        
        assert crawler.use_per_domain_delay is True
        assert crawler.rate_limiter is not None
        assert crawler.rate_limiter.default_delay == 0.2


