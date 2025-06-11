#!/usr/bin/env python3
"""
test_content_extractor.py - Unit tests for unified content extractor
"""

import pytest
import asyncio
from unittest.mock import MagicMock

from crawlit.extractors.content_extractor import ContentExtractor

# Sample HTML content for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="Test page description">
    <meta name="keywords" content="test, page, keywords">
    <title>Test Page Title</title>
    <link rel="canonical" href="https://example.com/canonical">
</head>
<body>
    <h1>Main Heading</h1>
    <p>This is a paragraph with some text.</p>
    
    <figure>
        <img src="/images/test1.jpg" alt="Test Image 1" width="800" height="600">
        <figcaption>This is a test image with caption</figcaption>
    </figure>
    
    <h2>Secondary Heading</h2>
    <p>Another paragraph</p>
    <img src="/images/test2.jpg" alt="Test Image 2">
    <p>Text after the second image</p>
    
    <a href="/link1">
        <img src="/images/test3.jpg" alt="Test Image in Link">
    </a>
</body>
</html>
"""

class TestContentExtractor:
    """Test cases for the unified ContentExtractor class"""
    
    def setup_method(self):
        """Set up test case"""
        self.extractor = ContentExtractor()
        self.url = "https://example.com/test"
        
        # Mock response for sync requests
        self.sync_response = MagicMock()
        self.sync_response.status_code = 200
        self.sync_response.headers = {"Content-Type": "text/html", "Last-Modified": "Wed, 28 May 2025 12:00:00 GMT"}
        
        # Mock response for async requests
        self.async_response = MagicMock()
        self.async_response.status = 200
        self.async_response.headers = {"Content-Type": "text/html", "Last-Modified": "Wed, 28 May 2025 12:00:00 GMT"}
    
    def test_sync_extract_content(self):
        """Test synchronous content extraction"""
        result = self.extractor.extract_content(SAMPLE_HTML, self.url, self.sync_response)
        
        # Test basic metadata extraction
        assert result["title"] == "Test Page Title"
        assert result["meta_description"] == "Test page description"
        assert len(result["meta_keywords"]) == 3
        assert result["canonical_url"] == "https://example.com/canonical"
        assert result["language"] == "en"
        assert result["http_status"] == 200
        
        # Test headings extraction
        assert len(result["headings"]) == 2
        assert result["headings"][0]["text"] == "Main Heading"
        assert result["headings"][1]["text"] == "Secondary Heading"
        
        # Test images extraction
        assert len(result["images_with_context"]) == 3
        
        # Image with caption should have highest relevance score
        captioned_img = result["images_with_context"][0]
        assert "test1.jpg" in captioned_img["src"]
        assert "caption" in captioned_img["caption"]
        assert captioned_img["relevance_score"] > 0
        
        # Image inside anchor should have related link
        linked_img = next(img for img in result["images_with_context"] if "test3.jpg" in img["src"])
        assert len(linked_img["related_links"]) > 0
    
    @pytest.mark.asyncio
    async def test_async_extract_content(self):
        """Test asynchronous content extraction"""
        result = await self.extractor.extract_content_async(SAMPLE_HTML, self.url, self.async_response)
        
        # Test basic metadata extraction
        assert result["title"] == "Test Page Title"
        assert result["meta_description"] == "Test page description"
        assert len(result["meta_keywords"]) == 3
        assert result["canonical_url"] == "https://example.com/canonical"
        assert result["language"] == "en"
        assert result["http_status"] == 200
        
        # Test headings extraction
        assert len(result["headings"]) == 2
        assert result["headings"][0]["text"] == "Main Heading"
        assert result["headings"][1]["text"] == "Secondary Heading"
        
        # Test images extraction
        assert len(result["images_with_context"]) == 3
        
        # Image with caption should have highest relevance score
        captioned_img = result["images_with_context"][0]
        assert "test1.jpg" in captioned_img["src"]
        assert "caption" in captioned_img["caption"]
        assert captioned_img["relevance_score"] > 0
        
        # Image inside anchor should have related link
        linked_img = next(img for img in result["images_with_context"] if "test3.jpg" in img["src"])
        assert len(linked_img["related_links"]) > 0
    
    def test_error_handling(self):
        """Test error handling in content extraction"""
        # Test with malformed HTML
        broken_html = "<html><broken>"
        result = self.extractor.extract_content(broken_html, self.url)
        
        # Content extraction should not fail even with broken HTML
        assert "title" in result
        assert result["title"] is None
        
        # Test with binary data that can't be decoded
        binary_data = b'\xff\xfe\x00\x00\xff'  # Invalid UTF-8/16
        result = self.extractor.extract_content(binary_data, self.url)
        assert "title" in result

    def test_extract_images_with_context(self):
        """Test detailed extraction of images with context"""
        result = self.extractor.extract_content(SAMPLE_HTML, self.url)
        images = result["images_with_context"]
        
        # Should extract 3 images
        assert len(images) == 3
        
        # First image should have a caption and highest relevance
        assert images[0]["caption"] != ""
        assert images[0]["width"] == "800"
        assert images[0]["height"] == "600"
        
        # Images should have position information
        for img in images:
            assert "position" in img
            assert "relative_position" in img["position"]
            assert "total_images" in img["position"]
            assert img["position"]["total_images"] == 3
