#!/usr/bin/env python3
"""
Test exponential backoff functionality
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from crawlit.crawler.fetcher import fetch_page


class TestExponentialBackoff:
    """Test exponential backoff in retry logic"""
    
    @patch('crawlit.crawler.fetcher.requests.get')
    @patch('crawlit.crawler.fetcher.time.sleep')
    def test_exponential_backoff_on_server_error(self, mock_sleep, mock_get):
        """Test that exponential backoff is used on server errors"""
        # Create mock response with 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Call fetch_page with retries
        success, response, status = fetch_page(
            "http://example.com",
            max_retries=3,
            timeout=5
        )
        
        # Should have failed after retries
        assert success == False
        
        # Check that sleep was called with exponential backoff
        # First retry: 2^1 = 2 seconds
        # Second retry: 2^2 = 4 seconds  
        # Third retry: 2^3 = 8 seconds
        assert mock_sleep.call_count >= 3
        
        # Verify exponential progression
        sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_times[0] == 2  # 2^1
        assert sleep_times[1] == 4  # 2^2
        assert sleep_times[2] == 8  # 2^3
    
    @patch('crawlit.crawler.fetcher.requests.get')
    @patch('crawlit.crawler.fetcher.time.sleep')
    def test_exponential_backoff_on_connection_error(self, mock_sleep, mock_get):
        """Test exponential backoff on connection errors"""
        import requests
        
        # Simulate connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        # Call fetch_page
        success, response, status = fetch_page(
            "http://example.com",
            max_retries=2,
            timeout=5
        )
        
        # Should have failed
        assert success == False
        
        # Check that sleep was called with exponential backoff
        assert mock_sleep.call_count >= 2
        
        sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_times[0] == 2  # 2^1
        assert sleep_times[1] == 4  # 2^2
    
    @patch('crawlit.crawler.fetcher.requests.get')
    @patch('crawlit.crawler.fetcher.time.sleep')
    def test_exponential_backoff_capped_at_32_seconds(self, mock_sleep, mock_get):
        """Test that backoff is capped at 32 seconds"""
        # Create mock response with 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Call with many retries to test cap
        success, response, status = fetch_page(
            "http://example.com",
            max_retries=10,  # More retries to test cap
            timeout=5
        )
        
        # Should have failed
        assert success == False
        
        # Get all sleep times
        sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
        
        # Check that no sleep time exceeds 32 seconds (the cap)
        assert all(t <= 32 for t in sleep_times)
        
        # Verify at least one hit the cap
        # 2^5 = 32, so retry 5 and onwards should be capped
        if len(sleep_times) >= 5:
            assert sleep_times[4] == 32  # 2^5 would be 32
            if len(sleep_times) >= 6:
                assert sleep_times[5] == 32  # Should stay at cap
    
    @patch('crawlit.crawler.fetcher.requests.get')
    @patch('crawlit.crawler.fetcher.time.sleep')
    def test_no_backoff_on_success(self, mock_sleep, mock_get):
        """Test that no backoff occurs on successful request"""
        # Create successful mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Success</html>"
        mock_response.content = b"<html>Success</html>"
        mock_get.return_value = mock_response
        
        # Call fetch_page
        success, response, status = fetch_page(
            "http://example.com",
            max_retries=3,
            timeout=5
        )
        
        # Should have succeeded
        assert success == True
        
        # No sleep should have been called
        assert mock_sleep.call_count == 0
    
    @patch('crawlit.crawler.fetcher.requests.get')
    @patch('crawlit.crawler.fetcher.time.sleep')
    def test_no_backoff_on_4xx_error(self, mock_sleep, mock_get):
        """Test that no retry/backoff occurs on 4xx client errors"""
        # Create mock response with 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        # Call fetch_page
        success, response, status = fetch_page(
            "http://example.com",
            max_retries=3,
            timeout=5
        )
        
        # Should have failed immediately
        assert success == False
        assert status == 404
        
        # No retry should occur for 4xx, so no sleep
        assert mock_sleep.call_count == 0


@pytest.mark.asyncio
class TestAsyncExponentialBackoff:
    """Test exponential backoff in async retry logic"""
    
    @patch('crawlit.crawler.async_fetcher.aiohttp.ClientSession')
    @patch('crawlit.crawler.async_fetcher.asyncio.sleep')
    async def test_async_exponential_backoff_on_server_error(self, mock_sleep, mock_session_class):
        """Test async exponential backoff on server errors"""
        from crawlit.crawler.async_fetcher import fetch_page_async
        
        # Create mock response with 500 error
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.headers = {'Content-Type': 'text/html'}
        
        # Mock session.get() to return the mock response directly
        # The response doesn't need to be a context manager in this structure
        mock_get = MagicMock()
        
        # Properly mock async context manager for response
        async def response_aenter(*args, **kwargs):
            return mock_response
        
        async def response_aexit(*args, **kwargs):
            return None
        
        # Mock the response returned by get to be a context manager
        mock_get_result = MagicMock()
        mock_get_result.__aenter__ = response_aenter
        mock_get_result.__aexit__ = response_aexit
        mock_get.return_value = mock_get_result
        
        # Mock session
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Properly mock async context manager for session
        async def session_aenter(*args, **kwargs):
            return mock_session
        
        async def session_aexit(*args, **kwargs):
            return None
        
        mock_session_class.return_value.__aenter__ = session_aenter
        mock_session_class.return_value.__aexit__ = session_aexit
        
        # Make sleep async
        async def async_sleep(duration):
            pass
        mock_sleep.side_effect = async_sleep
        
        # Call fetch_page_async
        success, response, status = await fetch_page_async(
            "http://example.com",
            max_retries=3,
            timeout=5
        )
        
        # Should have failed
        assert success == False
        
        # Check that sleep was called with exponential backoff
        assert mock_sleep.call_count >= 3
        
        # Verify exponential progression
        sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_times[0] == 2  # 2^1
        assert sleep_times[1] == 4  # 2^2
        assert sleep_times[2] == 8  # 2^3


class TestExponentialBackoffDocumentation:
    """Test that documentation accurately describes exponential backoff"""
    
    def test_readme_mentions_exponential_backoff(self):
        """Test that README mentions exponential backoff"""
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # README should mention exponential backoff
        assert 'exponential backoff' in content.lower()
    
    def test_release_notes_mention_exponential_backoff(self):
        """Test that release notes mention exponential backoff"""
        with open('RELEASE_NOTES.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Release notes should mention exponential backoff
        assert 'exponential backoff' in content.lower() or 'backoff' in content.lower()

