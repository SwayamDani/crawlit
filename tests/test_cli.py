"""
test_cli.py - Tests for the crawlit CLI functionality
"""

import pytest
import os
import json
import csv
import subprocess
import sys
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
CRAWLIT_CLI = [sys.executable, os.path.join(PROJECT_ROOT, "crawlit", "crawlit.py")]


class TestCrawlitCLI:
    """Test suite for the crawlit command-line interface"""
    
    @pytest.fixture
    def mock_website(self, httpserver):
        """Create a mock website for testing"""
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
    
    def test_basic_cli_crawl(self, mock_website, tmp_path):
        """Test basic crawling functionality via CLI"""
        output_file = tmp_path / "results.json"
        
        # Run CLI command
        cmd = CRAWLIT_CLI + [
            "--url", mock_website,
            "--depth", "1",
            "--output", str(output_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that the command succeeded
        assert result.returncode == 0
        
        # Check that the output file was created
        assert output_file.exists()
        
        # Verify content of output file
        with open(output_file) as f:
            data = json.load(f)
            assert mock_website in data
            assert f"{mock_website}page1" in data
            assert f"{mock_website}page2" in data
            
        # Check stdout for expected messages
        assert "Starting crawl" in result.stdout
        assert "Crawl complete" in result.stdout
        assert "Results saved to" in result.stdout
    
    def test_output_formats(self, mock_website, tmp_path):
        """Test saving results in different formats via CLI"""
        formats = {
            "json": tmp_path / "results.json",
            "csv": tmp_path / "results.csv",
            "txt": tmp_path / "results.txt",
            "html": tmp_path / "results.html"
        }
        
        for fmt, output_file in formats.items():
            # Run CLI command
            cmd = CRAWLIT_CLI + [
                "--url", mock_website,
                "--depth", "1",
                "--output-format", fmt,
                "--output", str(output_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check that the command succeeded
            assert result.returncode == 0
            
            # Check that the output file was created
            assert output_file.exists()
            
            # Verify the file based on format
            if fmt == "json":
                with open(output_file) as f:
                    data = json.load(f)
                    assert isinstance(data, dict)
                    assert mock_website in data
            elif fmt == "csv":
                with open(output_file, 'r', newline='') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    assert len(rows) > 1  # Header + data rows
                    assert "URL" in rows[0]  # Check header
            elif fmt in ["txt", "html"]:
                with open(output_file) as f:
                    content = f.read()
                    assert mock_website in content
    
    def test_verbose_output(self, mock_website):
        """Test verbose output mode"""
        # Run with verbose flag
        cmd = CRAWLIT_CLI + [
            "--url", mock_website,
            "--depth", "1",
            "--verbose"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that the command succeeded
        assert result.returncode == 0
        
        # Verbose output should contain debug messages
        assert "[DEBUG]" in result.stdout
    
    def test_summary_option(self, mock_website, tmp_path):
        """Test --summary option"""
        output_file = tmp_path / "results.json"
        
        # Run with summary flag
        cmd = CRAWLIT_CLI + [
            "--url", mock_website,
            "--depth", "1",
            "--output", str(output_file),
            "--summary"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that the command succeeded
        assert result.returncode == 0
        
        # Summary should be in output
        assert "Crawl Summary" in result.stdout
        assert "Total URLs crawled:" in result.stdout
    
    def test_cli_help(self):
        """Test help output"""
        # Run with help flag
        cmd = CRAWLIT_CLI + ["--help"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that the command succeeded
        assert result.returncode == 0
        
        # Help output should contain usage information
        assert "usage:" in result.stdout
        assert "--url" in result.stdout
        assert "--depth" in result.stdout
        assert "--output-format" in result.stdout
    
    def test_pretty_json(self, mock_website, tmp_path):
        """Test --pretty-json flag"""
        # First without pretty-json
        regular_output = tmp_path / "regular.json"
        cmd = CRAWLIT_CLI + [
            "--url", mock_website,
            "--depth", "1",
            "--output", str(regular_output)
        ]
        subprocess.run(cmd, capture_output=True)
        
        # Then with pretty-json
        pretty_output = tmp_path / "pretty.json"
        cmd = CRAWLIT_CLI + [
            "--url", mock_website,
            "--depth", "1",
            "--output", str(pretty_output),
            "--pretty-json"
        ]
        subprocess.run(cmd, capture_output=True)
        
        # Read both files
        with open(regular_output) as f:
            regular_content = f.read()
        with open(pretty_output) as f:
            pretty_content = f.read()
        
        # Pretty JSON should have more newlines and indentation
        assert len(pretty_content) > len(regular_content)
        assert pretty_content.count('\n') > regular_content.count('\n')
    
    def test_user_agent_option(self, httpserver):
        """Test custom user agent option"""
        user_agent_received = [None]  # Use a list to allow modification in the handler
        
        def handler(request):
            user_agent_received[0] = request.headers.get('User-Agent')
            return 200, {'Content-Type': 'text/html'}, "<html><body>Test page</body></html>"
        
        httpserver.expect_request("/").respond_with_handler(handler)
        
        # Run with custom user agent
        custom_agent = "TestBot/1.0"
        cmd = CRAWLIT_CLI + [
            "--url", httpserver.url_for("/"),
            "--user-agent", custom_agent,
            "--depth", "0"  # Only crawl the start URL
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that the command succeeded
        assert result.returncode == 0
        
        # Verify that the custom user agent was used
        assert user_agent_received[0] == custom_agent
