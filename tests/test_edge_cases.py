"""
Tests for edge cases and error scenarios
"""

import pytest
from crawlit.crawler.engine import Crawler
from crawlit.extractors.tables import extract_tables
from crawlit.extractors.keyword_extractor import KeywordExtractor
from crawlit.utils.errors import handle_fetch_error, FetchError
import requests
import aiohttp


class TestEdgeCases:
    """Test cases for edge cases and error scenarios"""
    
    def test_malformed_html_parsing(self):
        """Test handling of malformed HTML"""
        malformed_html = "<html><body><p>Unclosed tag<div>Nested</body>"
        
        # Should not raise exception
        extractor = KeywordExtractor()
        keywords = extractor.extract_keywords(malformed_html)
        
        # Should return empty or partial results, not crash
        assert isinstance(keywords, dict)
        assert 'keywords' in keywords
    
    def test_empty_html_content(self):
        """Test handling of empty HTML"""
        extractor = KeywordExtractor()
        keywords = extractor.extract_keywords("")
        
        assert isinstance(keywords, dict)
        assert keywords.get('keywords', []) == []
    
    def test_very_large_html(self):
        """Test handling of very large HTML content"""
        # Create a large HTML string
        large_html = "<html><body>" + "<p>Content</p>" * 10000 + "</body></html>"
        
        extractor = KeywordExtractor()
        keywords = extractor.extract_keywords(large_html)
        
        # Should handle without memory issues
        assert isinstance(keywords, dict)
    
    def test_encoding_issues(self):
        """Test handling of encoding issues"""
        # HTML with various encodings
        html_with_encoding = "<html><body><p>Test with émojis 🎉 and special chars: ñ, ü</p></body></html>"
        
        extractor = KeywordExtractor()
        keywords = extractor.extract_keywords(html_with_encoding)
        
        # Should handle encoding gracefully
        assert isinstance(keywords, dict)
    
    def test_table_with_malformed_structure(self):
        """Test table extraction with malformed table structure"""
        malformed_table = """
        <table>
            <tr><td>Cell 1</td><td>Cell 2</td></tr>
            <tr><td>Cell 3</td></tr>  <!-- Missing cell -->
            <tr><td colspan="2">Spanning cell</td></tr>
        </table>
        """
        
        tables = extract_tables(malformed_table)
        
        # Should handle malformed structure gracefully
        assert isinstance(tables, list)
    
    def test_table_with_nested_tables(self):
        """Test table extraction with nested tables"""
        nested_table = """
        <table>
            <tr><td>Outer cell</td></tr>
            <tr><td>
                <table>
                    <tr><td>Inner cell</td></tr>
                </table>
            </td></tr>
        </table>
        """
        
        tables = extract_tables(nested_table)
        
        # Should extract only top-level tables
        assert isinstance(tables, list)
    
    def test_handle_fetch_error_timeout(self):
        """Test error handling for timeout errors"""
        error = requests.exceptions.Timeout("Request timed out")
        should_retry, message, status = handle_fetch_error(
            "https://example.com",
            error,
            max_retries=3,
            retry_count=1
        )
        
        assert should_retry is True
        assert status == 408
        assert "timeout" in message.lower()
    
    def test_handle_fetch_error_connection(self):
        """Test error handling for connection errors"""
        error = requests.exceptions.ConnectionError("Connection failed")
        should_retry, message, status = handle_fetch_error(
            "https://example.com",
            error,
            max_retries=3,
            retry_count=1
        )
        
        assert should_retry is True
        assert status == 503
    
    def test_handle_fetch_error_http_5xx(self):
        """Test error handling for 5xx HTTP errors"""
        response = requests.Response()
        response.status_code = 500
        error = requests.exceptions.HTTPError(response=response)
        
        should_retry, message, status = handle_fetch_error(
            "https://example.com",
            error,
            max_retries=3,
            retry_count=1
        )
        
        assert should_retry is True
        assert status == 500
    
    def test_handle_fetch_error_http_4xx(self):
        """Test error handling for 4xx HTTP errors"""
        response = requests.Response()
        response.status_code = 404
        error = requests.exceptions.HTTPError(response=response)
        
        should_retry, message, status = handle_fetch_error(
            "https://example.com",
            error,
            max_retries=3,
            retry_count=1
        )
        
        assert should_retry is False
        assert status == 404
    
    def test_crawler_with_invalid_url(self):
        """Test crawler handling of invalid URLs"""
        # URLs with disallowed schemes (not http/https) must be rejected early
        # to prevent SSRF attacks.
        with pytest.raises(ValueError, match="Only 'http' and 'https' schemes"):
            Crawler(
                start_url="not-a-valid-url",
                max_depth=1
            )
    
    def test_extract_keywords_minimal_content(self):
        """Test keyword extraction with minimal content"""
        extractor = KeywordExtractor()
        
        # Very short content
        keywords = extractor.extract_keywords("<html><body><p>Hi</p></body></html>")
        
        # Should return empty or minimal results
        assert isinstance(keywords, dict)
        assert 'keywords' in keywords
    
    def test_extract_keywords_only_stopwords(self):
        """Test keyword extraction with only stopwords"""
        extractor = KeywordExtractor()
        
        html = "<html><body><p>the the the and and or</p></body></html>"
        keywords = extractor.extract_keywords(html)
        
        # Should filter out stopwords
        assert isinstance(keywords, dict)
        # Keywords list should be empty or very short
        assert len(keywords.get('keywords', [])) <= 1

