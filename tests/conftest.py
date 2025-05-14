"""
conftest.py - Pytest fixtures and configuration for the crawlit test suite
"""

import pytest
import sys
import os
from unittest.mock import MagicMock

# Add project root to sys.path if needed for imports in tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_response():
    """Create a mock HTTP response object"""
    response = MagicMock()
    response.status_code = 200
    response.headers = {'Content-Type': 'text/html; charset=utf-8'}
    response.text = "<html><body><a href='https://example.com/page1'>Link 1</a></body></html>"
    return response

# Import pytest-httpserver fixture for realistic HTTP testing
try:
    from pytest_httpserver import HTTPServer
    
    @pytest.fixture
    def httpserver():
        """Fixture for the HTTP server"""
        with HTTPServer() as server:
            yield server
except ImportError:
    # Provide a helpful message if pytest-httpserver is not installed
    @pytest.fixture
    def httpserver():
        pytest.skip("pytest-httpserver is required for this test")
        yield None