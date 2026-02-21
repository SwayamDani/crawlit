#!/usr/bin/env python3
"""
Tests for enhanced authentication features
"""

import pytest
from crawlit.utils.session_manager import SessionManager
from crawlit.crawler.engine import Crawler
from requests.auth import HTTPBasicAuth


class TestSessionManagerAuth:
    """Test authentication features in SessionManager"""
    
    def test_basic_auth(self):
        """Test basic authentication"""
        sm = SessionManager(auth=("username", "password"))
        session = sm.get_sync_session()
        
        assert session.auth is not None
        assert isinstance(session.auth, HTTPBasicAuth)
        assert session.auth.username == "username"
        assert session.auth.password == "password"
    
    def test_oauth_token(self):
        """Test OAuth bearer token"""
        token = "test-oauth-token-12345"
        sm = SessionManager(oauth_token=token)
        session = sm.get_sync_session()
        
        assert "Authorization" in session.headers
        assert session.headers["Authorization"] == f"Bearer {token}"
    
    def test_api_key(self):
        """Test API key authentication"""
        api_key = "test-api-key-12345"
        sm = SessionManager(api_key=api_key)
        session = sm.get_sync_session()
        
        assert "X-API-Key" in session.headers
        assert session.headers["X-API-Key"] == api_key
    
    def test_custom_api_key_header(self):
        """Test API key with custom header name"""
        api_key = "test-key"
        sm = SessionManager(api_key=api_key, api_key_header="Authorization")
        session = sm.get_sync_session()
        
        assert "Authorization" in session.headers
        assert session.headers["Authorization"] == api_key
    
    def test_custom_headers(self):
        """Test custom headers"""
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "X-Another-Header": "another-value"
        }
        sm = SessionManager(headers=custom_headers)
        session = sm.get_sync_session()
        
        for key, value in custom_headers.items():
            assert key in session.headers
            assert session.headers[key] == value
    
    def test_multiple_auth_methods(self):
        """Test combining multiple authentication methods"""
        sm = SessionManager(
            oauth_token="oauth-token",
            api_key="api-key",
            headers={"X-Custom": "value"},
            cookies={"session": "cookie-value"}
        )
        session = sm.get_sync_session()
        
        assert "Authorization" in session.headers
        assert session.headers["Authorization"] == "Bearer oauth-token"
        assert "X-API-Key" in session.headers
        assert session.headers["X-API-Key"] == "api-key"
        assert "X-Custom" in session.headers
        assert "session" in session.cookies
    
    def test_set_oauth_token_dynamically(self):
        """Test setting OAuth token after session creation"""
        sm = SessionManager()
        session = sm.get_sync_session()
        
        # Initially no auth
        assert "Authorization" not in session.headers
        
        # Set OAuth token
        sm.set_oauth_token("new-token")
        
        # Should be updated in existing session
        assert "Authorization" in session.headers
        assert session.headers["Authorization"] == "Bearer new-token"
    
    def test_set_api_key_dynamically(self):
        """Test setting API key after session creation"""
        sm = SessionManager()
        session = sm.get_sync_session()
        
        # Initially no API key
        assert "X-API-Key" not in session.headers
        
        # Set API key
        sm.set_api_key("new-key")
        
        # Should be updated in existing session
        assert "X-API-Key" in session.headers
        assert session.headers["X-API-Key"] == "new-key"
    
    def test_add_header_dynamically(self):
        """Test adding custom header after session creation"""
        sm = SessionManager()
        session = sm.get_sync_session()
        
        # Add header
        sm.add_header("X-Test", "test-value")
        
        # Should be updated in existing session
        assert "X-Test" in session.headers
        assert session.headers["X-Test"] == "test-value"


class TestCrawlerWithAuth:
    """Test crawler integration with authentication"""
    
    @pytest.fixture
    def mock_website(self, httpserver):
        """Create a simple mock website for authentication testing"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Auth Test Site</title></head>
        <body>
            <h1>Authentication Test Website</h1>
            <p>This is a test page for authentication.</p>
        </body>
        </html>
        """
        
        httpserver.expect_request("/").respond_with_data(
            html,
            content_type="text/html"
        )
        
        return httpserver.url_for("/")
    
    def test_crawler_with_oauth(self, mock_website):
        """Test crawler with OAuth token"""
        sm = SessionManager(oauth_token="test-oauth-token")
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            session_manager=sm
        )
        
        # Verify session has OAuth token
        session = crawler.session_manager.get_sync_session()
        assert "Authorization" in session.headers
        assert "Bearer test-oauth-token" in session.headers["Authorization"]
    
    def test_crawler_with_api_key(self, mock_website):
        """Test crawler with API key"""
        sm = SessionManager(api_key="test-api-key", api_key_header="X-API-Key")
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            session_manager=sm
        )
        
        # Verify session has API key
        session = crawler.session_manager.get_sync_session()
        assert "X-API-Key" in session.headers
        assert session.headers["X-API-Key"] == "test-api-key"
    
    def test_crawler_with_basic_auth(self, mock_website):
        """Test crawler with basic authentication"""
        sm = SessionManager(auth=("user", "pass"))
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            session_manager=sm
        )
        
        # Verify session has basic auth
        session = crawler.session_manager.get_sync_session()
        assert session.auth is not None
        assert isinstance(session.auth, HTTPBasicAuth)
    
    def test_crawler_with_custom_headers(self, mock_website):
        """Test crawler with custom headers"""
        custom_headers = {
            "X-Custom-Auth": "custom-value",
            "X-Request-ID": "12345"
        }
        sm = SessionManager(headers=custom_headers)
        
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            session_manager=sm
        )
        
        # Verify session has custom headers
        session = crawler.session_manager.get_sync_session()
        for key, value in custom_headers.items():
            assert key in session.headers
            assert session.headers[key] == value


