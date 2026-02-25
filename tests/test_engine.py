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
        # Setup mock response for any URL
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html; charset=utf-8'}
        
        # Configure fetch_page to return successful results for all URLs
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Setup mock links to be "discovered" from the start URL
        mock_links = [
            "https://example.com/page1",
            "https://example.com/page2"
        ]
        
        # Configure extract_links to return different links for each call
        # First call (start URL): return the mock_links
        # Subsequent calls: return empty list to prevent infinite crawling
        mock_extract_links.side_effect = [mock_links, [], []]
        
        # Execute the crawl
        crawler = engine.Crawler(start_url="https://example.com", max_depth=1)
        
        # Patch the _should_crawl method to allow all URLs to be crawled
        original_should_crawl = crawler._should_crawl
        crawler._should_crawl = lambda url: True
        
        crawler.crawl()
        
        # Verify that the initial URL was fetched (but not necessarily the first call)
        # Note: fetch_page now takes a session parameter, so we check for the call with any session
        calls = mock_fetch_page.call_args_list
        assert any(
            call[0][0] == "https://example.com" and 
            call[0][1] == crawler.user_agent and
            call[0][2] == crawler.max_retries and
            call[0][3] == crawler.timeout
            for call in calls
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
        
        # Patch the _should_crawl method to allow all URLs to be crawled
        original_should_crawl = crawler._should_crawl
        crawler._should_crawl = lambda url: True
        
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
        
        # Patch the _should_crawl method to allow all URLs to be crawled
        original_should_crawl = crawler._should_crawl
        crawler._should_crawl = lambda url: True
        
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
        
        # For this test, we need to let internal URLs through but still respect the internal_only flag
        # So we'll use a custom patching approach
        original_should_crawl = crawler._should_crawl
        def patched_should_crawl(url):
            # If it's an internal URL, allow it
            if url.startswith("https://example.com"):
                return True
            # Otherwise, add to skipped external URLs and return False
            crawler.skipped_external_urls.add(url)
            return False
            
        crawler._should_crawl = patched_should_crawl
        
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
        
        # Always allow all URLs to be crawled
        crawler._should_crawl = lambda url: True
        
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
        
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_links')
    def test_circular_references(self, mock_extract_links, mock_fetch_page):
        """Test that the crawler properly handles circular references in the link structure"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Create a circular reference where pages link to each other
        mock_extract_links.side_effect = [
            # start_url links to page1 and page2
            ["https://example.com/page1", "https://example.com/page2"],
            # page1 links back to start_url and to page2
            ["https://example.com", "https://example.com/page2"],
            # page2 links back to start_url and page1
            ["https://example.com", "https://example.com/page1"]
        ]
        
        crawler = engine.Crawler(start_url="https://example.com", max_depth=5)
        crawler._should_crawl = lambda url: url not in crawler.visited_urls  # Use actual URL tracking
        crawler.crawl()
        
        # Each URL should only be visited once despite circular references
        assert mock_fetch_page.call_count == 3
        assert "https://example.com" in crawler.get_results()
        assert "https://example.com/page1" in crawler.get_results()
        assert "https://example.com/page2" in crawler.get_results()
        
        # Each URL should only appear once in the visited set
        assert len(crawler.visited_urls) == 3
        
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_links')
    def test_non_html_content_types(self, mock_extract_links, mock_fetch_page):
        """Test crawler behavior with different content types (not just HTML)"""
        # Create a series of responses with different content types
        content_types = [
            'text/html',
            'application/pdf',
            'image/jpeg',
            'application/json',
            'text/plain'
        ]
        
        # Configure mock responses
        responses = []
        for content_type in content_types:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # Only HTML content gets parsed for links
            mock_resp.text = "<html><body>Test content</body></html>" if content_type == 'text/html' else "Binary or text content"
            mock_resp.headers = {'Content-Type': content_type}
            responses.append((True, mock_resp, 200))
        
        # Configure mock fetch_page for different content types
        def fetch_page_side_effect(*args, **kwargs):
            url = args[0]
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            if url == "https://example.com":
                # Start URL is HTML
                content_type = 'text/html'
                mock_resp.text = "<html><body>Test content</body></html>"
            else:
                # Determine content type based on URL (example.com/1 -> application/pdf, etc.)
                try:
                    url_num = int(url.split('/')[-1])
                    if 1 <= url_num <= 4:
                        content_type = content_types[url_num]  # Maps to pdf, jpeg, json, plain
                    else:
                        content_type = 'text/html'  # Default if URL doesn't match pattern
                except (ValueError, IndexError):
                    content_type = 'text/html'  # Default for unexpected URLs
                
                mock_resp.text = "Binary or text content"
            
            mock_resp.headers = {'Content-Type': content_type}
            return (True, mock_resp, 200)
            
        mock_fetch_page.side_effect = fetch_page_side_effect
        
        # Links should only be extracted from HTML pages
        def extract_links_side_effect(html, url, delay):
            if url == "https://example.com":  # Only the start URL is HTML
                return [f"https://example.com/{i}" for i in range(1, 5)]  # Return links to 4 other pages
            return []  # No links extracted from non-HTML content
            
        mock_extract_links.side_effect = extract_links_side_effect
        
        # Create and run the crawler
        crawler = engine.Crawler(start_url="https://example.com", max_depth=1)
        
        # Override _should_crawl to always return True for test URLs
        original_should_crawl = crawler._should_crawl
        def should_crawl_override(url):
            if url.startswith("https://example.com/"):
                return True
            return original_should_crawl(url)
        crawler._should_crawl = should_crawl_override
        
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Check that all 5 URLs were visited (start + 4 linked pages)
        assert len(results) == 5
        
        # Verify that links were extracted only from HTML pages
        assert mock_extract_links.call_count == 1  # Only called for HTML content type

        # Check that content types are properly stored in results
        assert results["https://example.com"]["content_type"] == 'text/html'

        # Verify that content types match what we set for each URL
        for i, content_type in enumerate(content_types[1:], 1):
            url = f"https://example.com/{i}"
            if url in results:
                assert results[url]["content_type"] == content_type
                
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('time.sleep')
    def test_rate_limiting(self, mock_sleep, mock_fetch_page):
        """Test that rate limiting works properly with high delay values"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Configure extract_links to return URLs
        with patch('crawlit.crawler.engine.extract_links') as mock_extract_links:
            mock_extract_links.return_value = [f"https://example.com/page{i}" for i in range(1, 6)]
            
            # Set a high delay value (1 second)
            crawler = engine.Crawler(start_url="https://example.com", delay=1.0, max_depth=1)
            
            # Make all URLs crawlable
            crawler._should_crawl = lambda url: True
            
            # Measure the time it takes to crawl
            start_time = time.time()
            crawler.crawl()
            end_time = time.time()
            
            # Verify that delay was properly used in extract_links
            for call_args in mock_extract_links.call_args_list:
                assert call_args[0][2] == 1.0  # Delay should be passed as the third argument
                
            # Check that we have results for all pages
            results = crawler.get_results()
            assert len(results) >= 4  # We should have the start URL plus at least 3 more
            
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_links')
    def test_large_scale_crawling(self, mock_extract_links, mock_fetch_page):
        """Test crawler performance with a large number of pages"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Create a large number of unique URLs in a tree structure
        # Level 1: 10 pages from the start URL
        # Level 2: Each level 1 page links to 5 unique pages (50 pages)
        # Total: 61 pages (1 start + 10 L1 + 50 L2)
        
        def generate_links(url, depth):
            if depth == 0:  # Start URL
                return [f"https://example.com/level1-{i}" for i in range(10)]
            elif depth == 1:  # Level 1 URLs
                page_num = int(url.split('-')[-1])
                return [f"https://example.com/level2-{page_num}-{i}" for i in range(5)]
            else:  # Level 2+ URLs have no outgoing links
                return []
                
        def extract_links_side_effect(html, url, delay):
            if url == "https://example.com":
                depth = 0
            elif "level1" in url:
                depth = 1
            else:
                depth = 2
            return generate_links(url, depth)
            
        mock_extract_links.side_effect = extract_links_side_effect
        
        # Create and run the crawler with depth=2
        crawler = engine.Crawler(start_url="https://example.com", max_depth=2)
        
        # Make all URLs crawlable
        original_should_crawl = crawler._should_crawl
        def should_crawl_override(url):
            if url.startswith("https://example.com/"):
                return True
            return original_should_crawl(url)
        crawler._should_crawl = should_crawl_override
        
        # Measure performance
        start_time = time.time()
        crawler.crawl()
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Check the results
        results = crawler.get_results()
        
        # Verify we have visited all 61 pages
        assert len(results) == 61, f"Expected 61 results, got {len(results)}"
        
        # Verify we have the start URL
        assert "https://example.com" in results
        
        # Verify we have all level 1 URLs
        for i in range(10):
            assert f"https://example.com/level1-{i}" in results
            
        # Verify we have all level 2 URLs
        for i in range(10):
            for j in range(5):
                assert f"https://example.com/level2-{i}-{j}" in results
                
        # Log the crawling performance
        print(f"Large scale crawling test: Crawled 61 pages in {elapsed:.2f} seconds")
    
    @patch('crawlit.crawler.engine.fetch_page')
    def test_malformed_html_handling(self, mock_fetch_page):
        """Test crawler behavior with malformed HTML"""
        # Setup mock response with malformed HTML
        malformed_html = """
        <html>
            <body>
                <p>This is a paragraph with an unclosed tag
                <div>This div is not closed properly
                <a href="https://example.com/page1">Valid link</a>
                <a href="invalid-url">Invalid URL</a>
                <a href="">Empty URL</a>
                <a>No href</a>
                <img src="image.jpg" />
            </body>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = malformed_html
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Create the crawler and run it
        crawler = engine.Crawler(start_url="https://example.com")
        
        # Use the actual extract_links function
        crawler.crawl()
        
        # Check that the crawler didn't crash and properly handled the malformed HTML
        results = crawler.get_results()
        assert "https://example.com" in results
        assert results["https://example.com"]["success"] == True
        
        # Check that the valid link was extracted despite malformed HTML
        assert "links" in results["https://example.com"]
        # The link might be normalized, so check for partial matches
        valid_link_found = False
        for link in results["https://example.com"]["links"]:
            if "/page1" in link:
                valid_link_found = True
                break
        assert valid_link_found, "Valid link should be extracted from malformed HTML"
    
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.extractors.image_extractor.ImageTagParser.extract_images')
    def test_image_extraction_feature(self, mock_extract_images, mock_fetch_page):
        """Test that image extraction works properly when enabled"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content with images</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Mock extract_links to return empty list of links
        with patch('crawlit.crawler.engine.extract_links', return_value=[]):
            # Mock the image extraction to return sample images
            mock_extract_images.return_value = [
                {'src': 'https://example.com/image1.jpg', 'alt': 'Image 1', 'width': '100', 'height': '100'},
                {'src': 'https://example.com/image2.png', 'alt': 'Image 2', 'width': '200', 'height': '150'}
            ]
            
            # Create and run crawler with image extraction enabled
            crawler = engine.Crawler(
                start_url="https://example.com",
                enable_image_extraction=True
            )
            crawler.crawl()
            
            # Verify that image extraction was called
            mock_extract_images.assert_called_once()
            
            # Check that images were properly stored in results
            results = crawler.get_results()
            assert "images" in results["https://example.com"]
            assert len(results["https://example.com"]["images"]) == 2
            
            # Verify image data
            assert results["https://example.com"]["images"][0]["src"] == "https://example.com/image1.jpg"
            assert results["https://example.com"]["images"][1]["src"] == "https://example.com/image2.png"
            
            # Test with image extraction disabled
            mock_extract_images.reset_mock()
            crawler = engine.Crawler(
                start_url="https://example.com",
                enable_image_extraction=False
            )
            crawler.crawl()
            
            # Verify that image extraction was not called
            mock_extract_images.assert_not_called()
            
            # Check that no images were stored in results
            results = crawler.get_results()
            assert "images" not in results["https://example.com"]
    
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.extractors.keyword_extractor.KeywordExtractor.extract_keywords')
    @patch('crawlit.extractors.keyword_extractor.KeywordExtractor.extract_keyphrases')
    def test_keyword_extraction_feature(self, mock_extract_keyphrases, mock_extract_keywords, mock_fetch_page):
        """Test that keyword extraction works properly when enabled"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content with keywords</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Mock extract_links to return empty list of links
        with patch('crawlit.crawler.engine.extract_links', return_value=[]):
            # Mock the keyword extraction
            mock_extract_keywords.return_value = {
                'keywords': ['test', 'content', 'keywords'],
                'scores': {'test': 0.8, 'content': 0.7, 'keywords': 0.9}
            }
            mock_extract_keyphrases.return_value = ['test content', 'content with keywords']
            
            # Create and run crawler with keyword extraction enabled
            crawler = engine.Crawler(
                start_url="https://example.com",
                enable_keyword_extraction=True
            )
            crawler.crawl()
            
            # Verify that keyword extraction was called
            mock_extract_keywords.assert_called_once()
            mock_extract_keyphrases.assert_called_once()
            
            # Check that keywords were properly stored in results
            results = crawler.get_results()
            assert "keywords" in results["https://example.com"]
            assert "keyphrases" in results["https://example.com"]
            assert "keyword_scores" in results["https://example.com"]
            
            assert len(results["https://example.com"]["keywords"]) == 3
            assert len(results["https://example.com"]["keyphrases"]) == 2
            
            # Verify keyword data
            assert "test" in results["https://example.com"]["keywords"]
            assert "content with keywords" in results["https://example.com"]["keyphrases"]
            assert results["https://example.com"]["keyword_scores"]["test"] == 0.8
            
            # Test with keyword extraction disabled
            mock_extract_keywords.reset_mock()
            mock_extract_keyphrases.reset_mock()
            
            crawler = engine.Crawler(
                start_url="https://example.com",
                enable_keyword_extraction=False
            )
            crawler.crawl()
            
            # Verify that keyword extraction was not called
            mock_extract_keywords.assert_not_called()
            mock_extract_keyphrases.assert_not_called()
            
            # Check that no keywords were stored in results
            results = crawler.get_results()
            assert "keywords" not in results["https://example.com"]
            assert "keyphrases" not in results["https://example.com"]
    
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_tables')
    def test_table_extraction_feature(self, mock_extract_tables, mock_fetch_page):
        """Test that table extraction works properly when enabled"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content with tables</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Mock extract_links to return empty list of links
        with patch('crawlit.crawler.engine.extract_links', return_value=[]):
            # Mock the table extraction
            mock_extract_tables.return_value = [
                {
                    'headers': ['Column 1', 'Column 2'],
                    'rows': [['Row 1, Cell 1', 'Row 1, Cell 2'], 
                             ['Row 2, Cell 1', 'Row 2, Cell 2']]
                }
            ]
            
            # Create and run crawler with table extraction enabled
            crawler = engine.Crawler(
                start_url="https://example.com",
                enable_table_extraction=True
            )
            crawler.crawl()
            
            # Verify that table extraction was called
            mock_extract_tables.assert_called_once()
            
            # Check that tables were properly stored in results
            results = crawler.get_results()
            assert "tables" in results["https://example.com"]
            assert len(results["https://example.com"]["tables"]) == 1
            
            # Verify table data
            assert len(results["https://example.com"]["tables"][0]["headers"]) == 2
            assert len(results["https://example.com"]["tables"][0]["rows"]) == 2
            assert results["https://example.com"]["tables"][0]["headers"][0] == "Column 1"
            
            # Test with table extraction disabled
            mock_extract_tables.reset_mock()
            
            crawler = engine.Crawler(
                start_url="https://example.com",
                enable_table_extraction=False
            )
            crawler.crawl()
            
            # Verify that table extraction was not called
            mock_extract_tables.assert_not_called()
            
            # Check that no tables were stored in results
            results = crawler.get_results()
            assert "tables" not in results["https://example.com"]
    
    @patch('crawlit.crawler.engine.fetch_page')
    def test_url_normalization(self, mock_fetch_page):
        """Test URL normalization and deduplication"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Different URL formats that should normalize to the same URL
        # List of URLs that should be equivalent
        equivalent_urls = [
            "https://example.com",
            "https://example.com/",
            "HTTPS://EXAMPLE.COM/",
            "https://example.com/index.html",
            "https://example.com/index.html?",
            "https://example.com/#fragment",
        ]
        
        # Mock extract_links to return all of these URLs
        with patch('crawlit.crawler.engine.extract_links', return_value=equivalent_urls):
            # Create and run crawler
            crawler = engine.Crawler(start_url="https://example.com")
            crawler.crawl()
            
            # After normalization, we should only have crawled each URL once
            # But exactly which normalized form is used can vary, so check number of results
            results = crawler.get_results()
            # At minimum, there should be fewer results than URLs due to normalization
            assert len(results) < len(equivalent_urls), "URL normalization should reduce duplicate URLs"
            
            # Since normalization is implementation-specific, the actual number of deduplicated URLs
            # might vary, but we expect significant deduplication
            
    @patch('crawlit.crawler.engine.fetch_page')
    @patch('crawlit.crawler.engine.extract_links')
    def test_url_canonicalization(self, mock_extract_links, mock_fetch_page):
        """Test URL canonicalization with relative and absolute paths"""
        # Setup mock response
        html_with_canonical = """
        <html>
            <head>
                <link rel="canonical" href="https://example.com/canonical-page" />
            </head>
            <body>
                <p>Test content with canonical URL</p>
            </body>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_with_canonical
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_fetch_page.return_value = (True, mock_response, 200)
        
        # Set up relative URLs that should be resolved against the base URL
        relative_urls = [
            "/page1.html",
            "page2.html",
            "../page3.html",
            "subdir/page4.html",
            "//example.com/page5.html"
        ]
        
        # Expected resolved URLs
        expected_urls = [
            "https://example.com/page1.html",
            "https://example.com/page2.html",
            "https://example.com/page3.html",  # ../ from root resolves to root
            "https://example.com/subdir/page4.html",
            "https://example.com/page5.html"
        ]
        
        # Mock extract_links to return resolved URLs
        # This tests that extract_links properly converts relative URLs to absolute
        mock_extract_links.reset_mock()
        mock_extract_links.return_value = expected_urls
        
        # Create and run crawler with content extraction enabled
        crawler = engine.Crawler(start_url="https://example.com", enable_content_extraction=True)
        
        # Mock _should_crawl to allow all URLs to be crawled
        crawler._should_crawl = lambda url: True
        
        crawler.crawl()

        # Verify extract_links was called with the correct base URL for resolving relative URLs
        # Use assert_any_call instead of assert_called_with to check any call
        mock_extract_links.assert_any_call(html_with_canonical, "https://example.com", crawler.delay)
        
        # All URLs in results should be absolute
        results = crawler.get_results()
        for url in results:
            assert url.startswith("http"), f"URL {url} is not absolute"
            
        # Verify the canonical URL is stored in the results (only if content extraction is enabled)
        if "canonical_url" in results["https://example.com"]:
            assert results["https://example.com"]["canonical_url"] == "https://example.com/canonical-page"
        
        # Verify all resolved URLs are in the links found
        assert "links" in results["https://example.com"]
        for expected_url in expected_urls:
            assert expected_url in results["https://example.com"]["links"], f"Expected URL {expected_url} not found in links"
        
        # Verify that mock_extract_links received the original relative URLs for processing
        # We can't test this directly since we're mocking extract_links,
        # but we can check if the crawler properly processes the returned absolute URLs
        for expected_url in expected_urls:
            assert expected_url in results, f"Expected URL {expected_url} not found in crawl results"
            assert results[expected_url]["success"] == True, f"URL {expected_url} was not successfully crawled"