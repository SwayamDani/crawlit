"""
conftest.py - Pytest fixtures and configuration for the crawlit test suite
"""

import pytest
import sys
import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

# Ensure tests/logs directory exists (required by pytest.ini log configuration)
os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)

# Add project root to sys.path if needed for imports in tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Get the project root directory for CLI testing
PROJECT_ROOT = Path(__file__).parent.parent
CRAWLIT_CLI = [sys.executable, os.path.join(PROJECT_ROOT, "crawlit", "crawlit.py")]

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

@pytest.fixture
def mock_website(httpserver):
    """Create a standard mock website for testing"""
    # Main page with links
    main_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Site</title></head>
    <body>
        <h1>Test Website</h1>
        <ul>
            <li><a href="/page1">Page 1</a></li>
            <li><a href="/page2">Page 2</a></li>
            <li><a href="https://external-site.com/page">External Link</a></li>
        </ul>
    </body>
    </html>
    """
    
    # Page 1 content
    page1_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Page 1</title></head>
    <body>
        <h1>Page 1</h1>
        <p>This is page 1 content</p>
        <a href="/">Back to home</a>
    </body>
    </html>
    """
    
    # Page 2 content
    page2_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Page 2</title></head>
    <body>
        <h1>Page 2</h1>
        <p>This is page 2 content</p>
        <a href="/">Back to home</a>
    </body>
    </html>
    """
    
    # Configure the server endpoints
    httpserver.expect_request("/").respond_with_data(main_html, content_type="text/html")
    httpserver.expect_request("/page1").respond_with_data(page1_html, content_type="text/html")
    httpserver.expect_request("/page2").respond_with_data(page2_html, content_type="text/html")
    
    # Setup robots.txt
    robots_txt = """
    User-agent: *
    Allow: /
    """
    httpserver.expect_request("/robots.txt").respond_with_data(robots_txt, content_type="text/plain")
    
    return httpserver.url_for("/")

@pytest.fixture
def run_cli_command():
    """Fixture to run CLI commands easily and return results"""
    def _run_command(args):
        """Run a CLI command with the given arguments"""
        cmd = CRAWLIT_CLI + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    return _run_command

@pytest.fixture
def cli_temp_dir():
    """Create a temporary directory for CLI test outputs"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)