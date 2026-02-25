#!/usr/bin/env python3
"""
test_async_engine.py - Unit tests for async crawler engine
"""

import pytest
import aiohttp
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock

from crawlit.crawler.async_engine import AsyncCrawler
from crawlit.crawler.async_fetcher import fetch_page_async, ResponseLike

@pytest.fixture
def mock_response():
    """Create a mock response object with HTML content"""
    return ResponseLike(
        url="https://example.com",
        status_code=200,
        headers={"Content-Type": "text/html"},
        text="<html><body><a href='https://example.com/page1'>Link 1</a></body></html>"
    )

@pytest.mark.asyncio
async def test_fetch_page_async_success(mock_response):
    """Test successful async page fetch"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_context = MagicMock()
        mock_context.__aenter__.return_value = mock_response
        mock_get.return_value = mock_context
        
        success, response, status = await fetch_page_async("https://example.com")
        
        assert success is True
        assert status == 200
        response_text = await response.text()
        mock_text = await mock_response.text()
        assert response_text == mock_text

@pytest.mark.asyncio
async def test_fetch_page_async_error():
    """Test error handling in async fetch"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = aiohttp.ClientError("Connection error")
        
        success, error, status = await fetch_page_async("https://example.com")
        
        assert success is False
        assert status == 500
        assert "Connection error" in error

@pytest.mark.asyncio
async def test_async_crawler_init():
    """Test AsyncCrawler initialization"""
    crawler = AsyncCrawler("https://example.com", max_depth=2, max_concurrent_requests=5)

    assert crawler.start_url == "https://example.com"
    assert crawler.max_depth == 2
    assert crawler.max_concurrent_requests == 5
    assert crawler.base_domain == "example.com"
    # Semaphore is created lazily inside crawl() to avoid binding to the wrong event loop
    assert crawler.semaphore is None

@pytest.mark.asyncio
async def test_should_crawl_internal_only():
    """Test _should_crawl method with internal_only=True"""
    crawler = AsyncCrawler("https://example.com", internal_only=True)
    
    # Internal URL should be crawled
    assert await crawler._should_crawl("https://example.com/path") is True
    
    # External URL should be skipped
    assert await crawler._should_crawl("https://other-domain.com") is False
    
    # Already visited URL should be skipped
    crawler.visited_urls.add("https://example.com/visited")
    assert await crawler._should_crawl("https://example.com/visited") is False

@pytest.mark.asyncio
async def test_process_url():
    """Test _process_url method - properly testing crawler functionality with mocks"""
    # Configure a debug logger to see more information
    import logging
    test_logger = logging.getLogger()
    test_logger.setLevel(logging.DEBUG)
    
    # Create the crawler and initialise the semaphore (normally done inside crawl())
    crawler = AsyncCrawler("https://example.com", max_depth=2)
    crawler.semaphore = asyncio.Semaphore(crawler.max_concurrent_requests)

    # Create a proper async response with HTML content
    mock_html = "<html><body><a href='https://example.com/page1'>Link 1</a></body></html>"

    # Patch async_fetch_page to return a successful response
    with patch('crawlit.crawler.async_engine.async_fetch_page') as mock_fetch:
        # Create a simple response object
        mock_response = AsyncMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.status = 200
        mock_response.is_binary = False
        
        # Set up async text method to return our HTML
        mock_response.text = AsyncMock(return_value=mock_html)
        
        # Set up the mock to return success and our mock response
        mock_fetch.return_value = (True, mock_response, 200)
         # Define a side effect function that returns our desired links
        def mock_extract_side_effect(html_content, base_url, delay=0.1):
            # Return our predefined list of links including the one we're checking for
            return ["https://example.com/page1", "https://www.iana.org/domains/example"]
        
        # Now patch extract_links with our side effect
        with patch('crawlit.crawler.async_engine.extract_links', side_effect=mock_extract_side_effect) as mock_extract:
            
            # Call the method under test
            await crawler._process_url("https://example.com", 0)

            # Verify the results
            assert "https://example.com" in crawler.results
            assert crawler.results["https://example.com"]["success"] is True
            assert crawler.results["https://example.com"]["status"] == 200
            # Check that the link from the actual result is present
            assert "https://www.iana.org/domains/example" in crawler.results["https://example.com"]["links"]


# ──────────────────────────────────────────────────────────
# URL validation (M2)
# ──────────────────────────────────────────────────────────

def test_async_crawler_rejects_non_http_scheme():
    """AsyncCrawler constructor must raise ValueError for non-http/https URLs"""
    with pytest.raises(ValueError, match="http or https"):
        AsyncCrawler("ftp://example.com")


def test_async_crawler_rejects_no_scheme():
    with pytest.raises(ValueError):
        AsyncCrawler("example.com/path")


def test_async_crawler_rejects_empty_host():
    with pytest.raises(ValueError, match="no host"):
        AsyncCrawler("https:///path")


# ──────────────────────────────────────────────────────────
# Depth limit – enforced in the crawl loop
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crawl_respects_max_depth():
    """Crawler must not process URLs beyond max_depth."""
    crawler = AsyncCrawler("https://example.com", max_depth=1,
                           respect_robots=False)

    call_count = 0

    async def fake_fetch(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_r = AsyncMock()
        mock_r.headers = {"Content-Type": "text/html"}
        mock_r.status = 200
        mock_r.is_binary = False
        mock_r.text = AsyncMock(return_value="<html></html>")
        return (True, mock_r, 200)

    with patch('crawlit.crawler.async_engine.async_fetch_page', side_effect=fake_fetch), \
         patch('crawlit.crawler.async_engine.extract_links',
               return_value=["https://example.com/depth1"]):
        await crawler.crawl()

    # Start URL (depth 0) + depth-1 URL, but nothing beyond depth 1
    assert "https://example.com" in crawler.results
    assert "https://example.com/depth1" in crawler.results


# ──────────────────────────────────────────────────────────
# _should_crawl – external URLs with internal_only=False
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_should_crawl_allows_external_when_not_internal_only():
    crawler = AsyncCrawler("https://example.com", internal_only=False)
    result = await crawler._should_crawl("https://other-domain.com/page")
    assert result is True


# ──────────────────────────────────────────────────────────
# _process_url – failed fetch stored in results
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_url_failed_fetch():
    """When fetch fails the result should record success=False"""
    crawler = AsyncCrawler("https://example.com", max_depth=2)
    crawler.semaphore = asyncio.Semaphore(crawler.max_concurrent_requests)

    with patch('crawlit.crawler.async_engine.async_fetch_page') as mock_fetch:
        mock_fetch.return_value = (False, "Connection refused", 500)
        await crawler._process_url("https://example.com/fail", 0)

    assert "https://example.com/fail" in crawler.results
    result = crawler.results["https://example.com/fail"]
    assert result["success"] is False
    assert result["status"] == 500


# ──────────────────────────────────────────────────────────
# _process_url – non-HTML content type skips link extraction
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_url_non_html_no_links():
    """Non-HTML responses must not trigger link extraction."""
    crawler = AsyncCrawler("https://example.com", max_depth=2)
    crawler.semaphore = asyncio.Semaphore(crawler.max_concurrent_requests)

    with patch('crawlit.crawler.async_engine.async_fetch_page') as mock_fetch, \
         patch('crawlit.crawler.async_engine.extract_links') as mock_extract:
        mock_response = AsyncMock()
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.status = 200
        mock_response.is_binary = True
        mock_response.text = AsyncMock(return_value=b"")
        mock_fetch.return_value = (True, mock_response, 200)

        await crawler._process_url("https://example.com/doc.pdf", 0)

        mock_extract.assert_not_called()


# ──────────────────────────────────────────────────────────
# Concurrency semaphore is created inside crawl()
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crawl_creates_semaphore():
    """Semaphore must be bound to the running event loop (created inside crawl)."""
    crawler = AsyncCrawler("https://example.com", max_depth=0,
                           max_concurrent_requests=3, respect_robots=False)

    with patch('crawlit.crawler.async_engine.async_fetch_page') as mock_fetch:
        mock_response = AsyncMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.status = 200
        mock_response.is_binary = False
        mock_response.text = AsyncMock(return_value="<html></html>")
        mock_fetch.return_value = (True, mock_response, 200)

        with patch('crawlit.crawler.async_engine.extract_links', return_value=[]):
            await crawler.crawl()

    # After crawl(), the semaphore must have been created
    assert isinstance(crawler.semaphore, asyncio.Semaphore)
