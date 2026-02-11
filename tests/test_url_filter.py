"""
Tests for URL filtering functionality
"""

import pytest
import re
from crawlit.utils.url_filter import URLFilter


class TestURLFilter:
    """Test cases for URLFilter class"""
    
    def test_basic_allowed_pattern(self):
        """Test basic pattern matching"""
        filter_obj = URLFilter.from_patterns(allowed_regex=r'example\.com')
        
        assert filter_obj.is_allowed('https://example.com/page') is True
        assert filter_obj.is_allowed('https://other.com/page') is False
    
    def test_basic_blocked_pattern(self):
        """Test blocked pattern matching"""
        filter_obj = URLFilter.from_patterns(blocked_regex=r'admin')
        
        assert filter_obj.is_allowed('https://example.com/page') is True
        assert filter_obj.is_allowed('https://example.com/admin') is False
    
    def test_file_extension_filtering(self):
        """Test file extension filtering"""
        filter_obj = URLFilter(
            allowed_extensions=['.html', '.htm'],
            blocked_extensions=['.pdf', '.zip']
        )
        
        assert filter_obj.is_allowed('https://example.com/page.html') is True
        assert filter_obj.is_allowed('https://example.com/page.pdf') is False
        assert filter_obj.is_allowed('https://example.com/page.zip') is False
    
    def test_query_parameter_filtering(self):
        """Test query parameter filtering"""
        filter_obj = URLFilter(
            allowed_query_params=['page', 'id']
        )
        
        assert filter_obj.is_allowed('https://example.com/page?page=1') is True
        assert filter_obj.is_allowed('https://example.com/page?id=123') is True
        assert filter_obj.is_allowed('https://example.com/page?other=value') is False
    
    def test_html_only_filter(self):
        """Test HTML-only filter factory"""
        filter_obj = URLFilter.html_only()
        
        assert filter_obj.is_allowed('https://example.com/page.html') is True
        assert filter_obj.is_allowed('https://example.com/page') is True
        assert filter_obj.is_allowed('https://example.com/image.jpg') is False
        assert filter_obj.is_allowed('https://example.com/file.pdf') is False
    
    def test_exclude_media_filter(self):
        """Test exclude media filter factory"""
        filter_obj = URLFilter.exclude_media()
        
        assert filter_obj.is_allowed('https://example.com/page.html') is True
        assert filter_obj.is_allowed('https://example.com/image.jpg') is False
        assert filter_obj.is_allowed('https://example.com/video.mp4') is False
    
    def test_custom_filter(self):
        """Test custom filter function"""
        def custom_filter(url: str) -> bool:
            return 'allowed' in url
        
        filter_obj = URLFilter(custom_filter=custom_filter)
        
        assert filter_obj.is_allowed('https://example.com/allowed/page') is True
        assert filter_obj.is_allowed('https://example.com/blocked/page') is False
    
    def test_combined_filters(self):
        """Test multiple filters working together"""
        filter_obj = URLFilter(
            allowed_patterns=[re.compile(r'example\.com')],
            blocked_extensions=['.pdf'],
            custom_filter=lambda url: 'test' not in url
        )
        
        assert filter_obj.is_allowed('https://example.com/page.html') is True
        assert filter_obj.is_allowed('https://example.com/page.pdf') is False
        assert filter_obj.is_allowed('https://example.com/test/page') is False
        assert filter_obj.is_allowed('https://other.com/page.html') is False

