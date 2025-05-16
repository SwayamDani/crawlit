#!/usr/bin/env python3
"""
Test module for keyword extraction functionality
"""

import pytest
from pathlib import Path
import tempfile
import json
import os

from crawlit.extractors.keyword_extractor import KeywordExtractor

# Sample HTML content for testing
SAMPLE_HTML = """
<html>
    <head>
        <title>Test Page for Keyword Extraction</title>
    </head>
    <body>
        <h1>Python Web Crawler Testing</h1>
        <p>This is a sample page to test the keyword extraction capabilities.
        The crawler should identify important keywords like Python, crawler, and extraction.
        Keywords are important for understanding the content of a page.</p>
        
        <h2>Important Features</h2>
        <ul>
            <li>Keyword extraction</li>
            <li>Natural language processing</li>
            <li>Content analysis</li>
        </ul>
    </body>
</html>
"""

class TestKeywordExtractor:
    """Test suite for the KeywordExtractor class"""
    
    def test_initialization(self):
        """Test keyword extractor initialization with default and custom parameters"""
        # Default parameters
        extractor = KeywordExtractor()
        assert extractor.min_word_length == 3
        assert extractor.max_keywords == 20
        
        # Custom parameters
        extractor = KeywordExtractor(min_word_length=4, max_keywords=10)
        assert extractor.min_word_length == 4
        assert extractor.max_keywords == 10
    
    def test_extract_text_from_html(self):
        """Test extraction of text content from HTML"""
        extractor = KeywordExtractor()
        text = extractor.extract_text_from_html(SAMPLE_HTML)
        
        # Check that the text contains content from the HTML
        assert "Test Page for Keyword Extraction" in text
        assert "Python Web Crawler Testing" in text
        assert "sample page to test the keyword extraction" in text
        
        # Check that HTML tags are removed
        assert "<h1>" not in text
        assert "<p>" not in text
        assert "<ul>" not in text
    
    def test_tokenize_text(self):
        """Test tokenization of text into valid words"""
        extractor = KeywordExtractor(min_word_length=4)  # Only words >= 4 chars
        text = "This is a test of the tokenization process with some stop-words like and or but!"
        tokens = extractor.tokenize_text(text)
        
        # Check that short words and stop words are removed
        assert "this" not in tokens  # Stop word
        assert "is" not in tokens     # Stop word and too short
        assert "a" not in tokens      # Stop word and too short
        assert "and" not in tokens    # Stop word
        assert "or" not in tokens     # Stop word and too short
        assert "but" not in tokens    # Stop word and too short
        
        # Check that valid words are included
        assert "test" in tokens
        assert "tokenization" in tokens
        assert "process" in tokens
        assert "some" in tokens
        assert "stopwords" in tokens
        
        # Check that punctuation is removed
        for token in tokens:
            assert all(char not in token for char in "!.,;:?-")
    
    def test_extract_keywords(self):
        """Test keyword extraction from HTML content"""
        extractor = KeywordExtractor(max_keywords=10)
        result = extractor.extract_keywords(SAMPLE_HTML)
        
        # Check that we got keywords in the result
        assert "keywords" in result
        assert len(result["keywords"]) > 0
        assert len(result["keywords"]) <= 10  # Respect max_keywords
        
        # Check that relevant keywords are extracted
        keywords = result["keywords"]
        relevant_words = ["python", "crawler", "extraction", "keywords", "content"]
        assert any(word in keywords for word in relevant_words)
        
        # Test with scores
        result_with_scores = extractor.extract_keywords(SAMPLE_HTML, include_scores=True)
        assert "scores" in result_with_scores
        assert len(result_with_scores["scores"]) == len(result_with_scores["keywords"])
        
        # Check that all scores are between 0 and 1
        for score in result_with_scores["scores"].values():
            assert 0 <= score <= 1
    
    def test_extract_keyphrases(self):
        """Test extraction of multi-word phrases"""
        extractor = KeywordExtractor()
        keyphrases = extractor.extract_keyphrases(SAMPLE_HTML)
        
        # Check that we got some keyphrases
        assert len(keyphrases) > 0
        
        # Check that the phrases are multi-word
        assert all(" " in phrase for phrase in keyphrases)
        
        # Check that relevant phrases are extracted
        relevant_phrases = ["keyword extraction", "natural language processing", "content analysis"]
        assert any(phrase in " ".join(keyphrases) for phrase in relevant_phrases)
    
    def test_with_minimal_content(self):
        """Test extraction with minimal HTML content"""
        minimal_html = "<html><body>Small text.</body></html>"
        extractor = KeywordExtractor()
        
        # Keywords
        result = extractor.extract_keywords(minimal_html)
        assert result["keywords"] == []  # No words meet criteria
        
        # Keyphrases
        phrases = extractor.extract_keyphrases(minimal_html)
        assert phrases == []  # No phrases meet criteria
