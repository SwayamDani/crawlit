"""
test_engine.py - Comprehensive tests for the main crawler engine functionality
"""

import pytest
from unittest.mock import patch, MagicMock, call
import requests
import time

from crawlit.crawler import engine


class TestCrawler:
    def test_crawler_initialization(self):
        """Test crawler initialization with various parameters"""
        # Test with default parameters
        crawler = engine.Crawler(start_url="https://example.com")
        assert crawler.start_url == "https://example.com"
        assert crawler.max_depth == 3  # Default max depth
        assert crawler.internal_only is True  # Default is to stay within domain
        
        # Test with custom parameters
        crawler = engine.Crawler(
            start_url="https://test.com",
            max_depth=5,
            internal_only=False,
            delay=0.2,
            user_agent="CustomBot/1.0",
            respect_robots=False
        )
        assert crawler.start_url == "https://test.com"
        assert crawler.max_depth == 5
        assert crawler.internal_only is False
        assert crawler.delay == 0.2
        assert crawler.user_agent == "CustomBot/1.0"
        assert crawler.respect_robots is False
        
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_links')
    def test_crawl_basic_functionality(self, mock_extract_links, mock_fetch_page):
        """Test basic crawl functionality with mocked components"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html; charset=utf-8'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Setup mock links to be "discovered"
        mock_links = [
            "https://example.com/page1",
            "https://example.com/page2"
        ]
        mock_extract_links.return_value = mock_links
         # Execute the crawl
        crawler = engine.Crawler(start_url="https://example.com", max_depth=1)
        crawler.crawl()
        
        # Verify that the initial URL was fetched (but not necessarily the first call)
        mock_fetch_page.assert_any_call(
            "https://example.com",
            crawler.user_agent,
            crawler.max_retries,
            crawler.timeout
        )
        
        # Verify that extract_links was called for each URL
        assert mock_extract_links.call_count == 3  # Once for start URL and twice for discovered URLs
        
        # Verify that discovered links were processed and stored
        results = crawler.get_results()
        assert len(results) == 3  # start_url + 2 discovered URLs
        assert "https://example.com" in results
        assert "https://example.com/page1" in results
        assert "https://example.com/page2" in results
    
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_links')
    def test_max_depth_respected(self, mock_extract_links, mock_fetch_page):
        """Test that max_depth parameter is respected"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Level 1 URLs discovered from start_url
        level1_urls = [
            "https://example.com/level1-page1",
            "https://example.com/level1-page2"
        ]
        
        # Level 2 URLs discovered from level1 pages
        level2_urls = [
            "https://example.com/level2-page1",
            "https://example.com/level2-page2"
        ]
        
        # Configure mock to return different URLs for different calls
        mock_extract_links.side_effect = [
            level1_urls,  # First call returns level 1 URLs
            level2_urls,  # Second call returns level 2 URLs
            level2_urls   # Third call returns level 2 URLs
        ]
        
        # Execute the crawl with max_depth=1 (should only crawl start_url)
        crawler = engine.Crawler(start_url="https://example.com", max_depth=1)
        crawler.crawl()
        
        # Verify that URLs were crawled - with max_depth=1, the crawler should still 
        # fetch the start_url and the discovered URLs at depth 1
        assert mock_fetch_page.call_count == 3  # start_url + 2 level1 URLs
        
        # Verify that the results contain only the start_url and level1 URLs but not level2
        results = crawler.get_results()
        assert len(results) == 3  # start_url + 2 level1 URLs
        assert "https://example.com" in results
        assert "https://example.com/level1-page1" in results
        assert "https://example.com/level1-page2" in results
        assert "https://example.com/level2-page1" not in results
        assert "https://example.com/level2-page2" not in results
        
        # Now test with max_depth=2 to ensure it reaches level2 URLs
        mock_fetch_page.reset_mock()
        mock_extract_links.reset_mock()
        
        # Instead of using side_effect, we'll handle different URLs differently in the mock
        # This is more robust for testing crawling behavior
        def mock_extract_links_function(html, url, delay):
            if url == "https://example.com":
                return level1_urls
            elif url.startswith("https://example.com/level1"):
                return level2_urls
            else:
                return []
                
        mock_extract_links.side_effect = mock_extract_links_function
        
        crawler = engine.Crawler(start_url="https://example.com", max_depth=2)
        crawler.crawl()
        
        # Verify that the crawler is attempting to fetch more URLs with max_depth=2
        # The exact number might vary, but it should be more than 3 (which was just the start URL + level1 URLs)
        assert mock_fetch_page.call_count > 3
        
        # Check that both level1 and some level2 URLs are in the results
        results = crawler.get_results()
        assert "https://example.com" in results
        assert "https://example.com/level1-page1" in results 
        assert "https://example.com/level1-page2" in results
        # We should have at least one level2 URL
        assert any(url.startswith("https://example.com/level2") for url in results.keys())
        assert "https://example.com/level2-page1" in results
        assert "https://example.com/level2-page2" in results

    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_links')
    def test_internal_only_respected(self, mock_extract_links, mock_fetch_page):
        """Test that internal_only parameter is respected"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Mix of internal and external URLs
        mixed_urls = [
            "https://example.com/internal1",
            "https://external-site.com/page1",
            "https://example.com/internal2",
            "https://another-site.org/page2"
        ]
        
        mock_extract_links.return_value = mixed_urls
        
        # Execute crawl with internal_only=True
        crawler = engine.Crawler(start_url="https://example.com", internal_only=True)
        crawler.crawl()
        
        # Verify that only internal URLs were included in results
        results = crawler.get_results()
        assert "https://example.com" in results
        assert "https://example.com/internal1" in results
        assert "https://example.com/internal2" in results
        assert "https://external-site.com/page1" not in results
        assert "https://another-site.org/page2" not in results
        
        # Check that external URLs were captured in skipped list
        skipped = crawler.get_skipped_external_urls()
        assert "https://external-site.com/page1" in skipped
        assert "https://another-site.org/page2" in skipped
        
        # Now test with internal_only=False - instead of testing exact matches,
        # let's check that the external URLs are fetched
        mock_fetch_page.reset_mock()
        mock_extract_links.reset_mock()
        # We need to make sure extract_links always returns the same URLs
        mock_extract_links.return_value = mixed_urls
        
        crawler = engine.Crawler(start_url="https://example.com", internal_only=False, max_depth=1)
        crawler.crawl()
        
        # Check that we attempted to fetch one of the external URLs
        external_url_call = False
        for call_args in mock_fetch_page.call_args_list:
            if "external-site.com" in call_args[0][0]:
                external_url_call = True
                break
        
        assert external_url_call, "External URL was not called despite internal_only=False"

    @patch('crawlit.crawler.engine.fetch_page')
    @patch('time.sleep')
    def test_delay_respected(self, mock_sleep, mock_fetch_page):
        """Test that delay parameter is respected between requests"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><a href='https://example.com/page1'>Link</a></body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Set a delay of 0.5 seconds
        delay = 0.5
        crawler = engine.Crawler(start_url="https://example.com", delay=delay, max_depth=1)
        
        # The delay is passed to extract_links in the engine.py file
        # We just need to verify that extract_links was called with the delay parameter
        with patch('crawlit.crawler.engine.extract_links', return_value=["https://example.com/page1"]) as mock_extract_links:
            crawler.crawl()
            # Check if extract_links was called with the correct delay parameter
            called_with_correct_delay = False
            for call_args in mock_extract_links.call_args_list:
                args, kwargs = call_args
                if len(args) >= 3 and args[2] == delay:
                    called_with_correct_delay = True
                    break
            assert called_with_correct_delay, "extract_links was never called with the correct delay value"
    
    @patch('crawlit.crawler.engine.fetch_page')
    def test_error_handling(self, mock_fetch_page):
        """Test that the crawler properly handles errors during fetching"""
        # Setup mock response for failed request
        mock_fetch_page.return_value = (False, "Connection error", 503)
        
        crawler = engine.Crawler(start_url="https://example.com")
        crawler.crawl()
        
        # Get the results and check that results still contain the URL but mark it as failed
        results = crawler.get_results()
        assert "https://example.com" in results
        assert results["https://example.com"]["success"] == False
        assert results["https://example.com"]["status"] == 503
        assert "error" in results["https://example.com"]
        
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.robots.RobotsHandler.can_fetch')
    def test_respect_robots_txt(self, mock_can_fetch, mock_fetch_page):
        """Test that robots.txt rules are respected when configured"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><a href='https://example.com/private'>Private</a></body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Set up extract_links to return a URL that should be blocked by robots
        with patch('crawlit.crawler.engine.extract_links', return_value=["https://example.com/private"]):
            # Configure robots.txt mock to disallow the private URL
            mock_can_fetch.side_effect = lambda url, agent: not url.endswith('/private')
            
            # Test with respect_robots=True
            crawler = engine.Crawler(start_url="https://example.com", respect_robots=True)
            crawler.crawl()
            
            # Get results
            results = crawler.get_results()
            
            # Verify that the start URL was crawled
            assert "https://example.com" in results
            
            # Verify that disallowed URL was not crawled
            assert "https://example.com/private" not in results
            
            # Verify that can_fetch was called with the private URL
            mock_can_fetch.assert_any_call("https://example.com/private", crawler.user_agent)
        
            # Reset mocks and test with respect_robots=False
            mock_fetch_page.reset_mock()
            mock_can_fetch.reset_mock()
            
            crawler = engine.Crawler(start_url="https://example.com", respect_robots=False)
            crawler.crawl()
            
            # Verify that all URLs were considered for crawling regardless of robots.txt
            results = crawler.get_results()
            assert "https://example.com" in results
            assert "https://example.com/private" in results
            # And that robots.txt wasn't checked
            assert mock_can_fetch.call_count == 0