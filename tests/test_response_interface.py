#!/usr/bin/env python3
"""
test_response_interface.py - Test the unified response interface
"""

import pytest
import aiohttp
from unittest.mock import patch, MagicMock

from crawlit.crawler.fetcher import fetch_url
from crawlit.crawler.async_fetcher import fetch_url_async, ResponseLike

class TestResponseInterface:
    """Test the unified response interface between sync and async fetchers"""
    
    def test_sync_response_interface(self):
        """Test that synchronous fetch_url returns a requests.Response"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "Test content"
            mock_response.ok = True
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.content = b"Test content"
            
            mock_get.return_value = mock_response
            
            response = fetch_url("https://example.com")
            
            # Check that the response has the expected interface
            assert response.status_code == 200
            assert response.text == "Test content"
            assert response.ok == True
            assert response.headers == {'Content-Type': 'text/html'}
            assert response.content == b"Test content"
    
    @pytest.mark.asyncio
    async def test_async_response_interface(self):
        """Test that asynchronous fetch_url_async returns a ResponseLike object"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Create a mock response with the ResponseLike interface
            mock_response = ResponseLike(
                url="https://example.com",
                status_code=200,
                headers={'Content-Type': 'text/html'},
                text="Test content",
                is_binary=False
            )
            
            # Set up the mock to return our ResponseLike object
            mock_context = MagicMock()
            mock_context.__aenter__.return_value = mock_response
            mock_get.return_value = mock_context
            
            # Call fetch_url_async
            response = await fetch_url_async("https://example.com")
            
            # Check that the response has the expected interface
            assert response.status_code == 200
            assert response.status == 200  # Should have both sync and async properties
            assert await response.text() == "Test content"
            assert response.text_content == "Test content"
            assert response.headers == {'Content-Type': 'text/html'}
            assert response.ok == True
            
    def test_response_like_interface(self):
        """Test the ResponseLike class directly for API compatibility"""
        # Create a ResponseLike object
        response = ResponseLike(
            url="https://example.com",
            status_code=200,
            headers={'Content-Type': 'text/html'},
            text="Test content",
            is_binary=False
        )
        
        # Test the sync interface
        assert response.status_code == 200
        assert response.text_content == "Test content"
        assert response.headers == {'Content-Type': 'text/html'}
        assert response.ok == True
        
        # Test the raise_for_status method
        response_error = ResponseLike(
            url="https://example.com",
            status_code=404,
            headers={'Content-Type': 'text/html'},
            text="Not found",
            is_binary=False
        )
        
        with pytest.raises(aiohttp.ClientResponseError):
            response_error.raise_for_status()
            
    @pytest.mark.asyncio
    async def test_mixed_usage(self):
        """Test using ResponseLike in both sync and async contexts"""
        response = ResponseLike(
            url="https://example.com",
            status_code=200,
            headers={'Content-Type': 'text/html'},
            text="Test content",
            is_binary=False
        )
        
        # Sync usage
        sync_text = response.text_content
        
        # Async usage
        async_text = await response.text()
        
        # Both should be the same
        assert sync_text == async_text
