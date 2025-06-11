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

# Complex HTML with nested structures and more content
COMPLEX_HTML = """
<html>
    <head>
        <title>Complex Page with Multiple Sections and Nested Content</title>
        <meta name="description" content="This page tests complex HTML structures">
        <style>
            body { font-family: Arial; }
            .highlight { color: red; }
        </style>
        <script>
            function testFunction() {
                console.log("This should be ignored in keyword extraction");
            }
        </script>
    </head>
    <body>
        <header>
            <h1>Advanced Machine Learning Techniques</h1>
            <nav>
                <ul>
                    <li><a href="#">Home</a></li>
                    <li><a href="#">About</a></li>
                    <li><a href="#">Contact</a></li>
                </ul>
            </nav>
        </header>
        <main>
            <section>
                <h2>Neural Networks Architecture</h2>
                <p>Neural networks are computational models inspired by the human brain. 
                They consist of layers of interconnected nodes or neurons that process information.</p>
                <p>Deep learning involves neural networks with many layers that can learn 
                hierarchical representations of data.</p>
                <div class="highlight">
                    <p>Key concepts include backpropagation, activation functions, and gradient descent.</p>
                </div>
            </section>
            <section>
                <h2>Natural Language Processing</h2>
                <p>NLP combines linguistics, computer science, and artificial intelligence 
                to enable computers to process and understand human language.</p>
                <ul>
                    <li>Tokenization</li>
                    <li>Named Entity Recognition</li>
                    <li>Sentiment Analysis</li>
                    <li>Machine Translation</li>
                </ul>
            </section>
            <aside>
                <h3>Related Technologies</h3>
                <p>Computer vision, reinforcement learning, and generative models 
                are closely related to machine learning.</p>
            </aside>
        </main>
        <footer>
            <p>Copyright 2025 - Machine Learning Experts</p>
        </footer>
    </body>
</html>
"""

# HTML with non-English content and special characters
MULTILINGUAL_HTML = """
<html>
    <head>
        <title>Multilingual Content Test - 多语言内容测试</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>Multilingual Text Analysis - 多语言文本分析</h1>
        <p>English: Natural language processing techniques work across multiple languages.</p>
        <p>Spanish: El procesamiento del lenguaje natural funciona en varios idiomas.</p>
        <p>French: Le traitement du langage naturel fonctionne dans plusieurs langues.</p>
        <p>German: Die Verarbeitung natürlicher Sprache funktioniert in mehreren Sprachen.</p>
        <p>Chinese: 自然语言处理技术适用于多种语言。</p>
        <p>Russian: Методы обработки естественного языка работают на разных языках.</p>
        <p>Japanese: 自然言語処理技術は複数の言語で機能します。</p>
        <p>Arabic: تعمل تقنيات معالجة اللغة الطبيعية عبر لغات متعددة.</p>
    </body>
</html>
"""

# Malformed HTML with broken tags
MALFORMED_HTML = """
<html>
    <head>
        <title>Malformed HTML Test Page
    </head>
    <body>
        <h1>Testing with Broken HTML Structure
        <p>This paragraph tag is not properly closed
        <div>This div has no closing tag
        <ul>
            <li>Item 1
            <li>Item 2</li>
        <p>Another unclosed paragraph with <b>partially bold text
        </div>
    </body>
</html>
"""

# Empty HTML
EMPTY_HTML = "<html><body></body></html>"

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
        assert "some" not in tokens  
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
    
    def test_complex_html_structure(self):
        """Test extraction from complex HTML with nested elements and diverse content"""
        extractor = KeywordExtractor(max_keywords=15)
        result = extractor.extract_keywords(COMPLEX_HTML)
        
        # Check basic result properties
        assert "keywords" in result
        assert len(result["keywords"]) > 0
        
        # Check for specific domain-related terms from the complex HTML
        important_terms = ["neural", "networks", "learning", "machine", "processing", 
                         "language", "layers", "deep", "computational"]
        found_terms = [term for term in important_terms if term in result["keywords"]]
        
        # At least 5 of the important terms should be found
        assert len(found_terms) >= 5, f"Only found these terms: {found_terms}"
        
        # Test that script content is ignored
        assert "console" not in result["keywords"]
        assert "function" not in result["keywords"]
        
        # Test keyphrases extraction from complex HTML
        keyphrases = extractor.extract_keyphrases(COMPLEX_HTML)
        assert len(keyphrases) > 0
        
        # Check for specific important phrases
        important_phrases = ["neural networks", "machine learning", "natural language", 
                           "deep learning", "artificial intelligence"]
        found_phrases = [phrase for phrase in important_phrases 
                       if any(phrase in kp for kp in keyphrases)]
        
        # At least 2 important phrases should be found
        assert len(found_phrases) >= 2, f"Only found these phrases: {found_phrases}"
    
    def test_multilingual_content(self):
        """Test extraction with non-English content and special characters"""
        extractor = KeywordExtractor(min_word_length=4, max_keywords=30)
        result = extractor.extract_keywords(MULTILINGUAL_HTML)
        
        # Basic result validation
        assert "keywords" in result
        assert len(result["keywords"]) > 0
        
        # Check for common words across languages
        multilingual_terms = ["natural", "language", "processing", "languages"]
        found_terms = [term for term in multilingual_terms if term in result["keywords"]]
        assert len(found_terms) >= 2, f"Only found these multilingual terms: {found_terms}"
        
        # Make sure non-English terms are present
        non_english_sample = ["idiomas", "funktioniert", "traitement", "языках"]
        # We only need to find at least one non-English term to validate it works with non-English
        assert any(term in " ".join(result["keywords"]) for term in non_english_sample), \
               "No non-English terms found"
    
    def test_malformed_html(self):
        """Test robustness with malformed HTML"""
        extractor = KeywordExtractor()
        
        # Should not raise exceptions with malformed HTML
        try:
            result = extractor.extract_keywords(MALFORMED_HTML)
            keyphrases = extractor.extract_keyphrases(MALFORMED_HTML)
            
            # Basic validation
            assert "keywords" in result
            assert isinstance(keyphrases, list)
            
            # Should still extract some content despite malformation
            assert len(result["keywords"]) > 0
        except Exception as e:
            pytest.fail(f"Extraction failed with malformed HTML: {str(e)}")
    
    def test_empty_content(self):
        """Test behavior with empty HTML content"""
        extractor = KeywordExtractor()
        
        # Test with completely empty HTML
        empty_result = extractor.extract_keywords(EMPTY_HTML)
        assert empty_result["keywords"] == []
        
        # Test with whitespace HTML
        whitespace_html = "<html><body>   </body></html>"
        whitespace_result = extractor.extract_keywords(whitespace_html)
        assert whitespace_result["keywords"] == []
        
        # Test with only HTML comments
        comment_html = "<html><body><!-- This is just a comment --></body></html>"
        comment_result = extractor.extract_keywords(comment_html)
        assert comment_result["keywords"] == []
    
    def test_tag_prioritization(self):
        """Test that HTML tags are correctly prioritized in keyword extraction"""
        # HTML with the same keyword in different tags to test priority weighting
        priority_html = """
        <html>
            <head>
                <title>Priority unique_title_word Test</title>
            </head>
            <body>
                <h1>Priority unique_h1_word Test</h1>
                <h2>Priority unique_h2_word Test</h2>
                <h3>Priority unique_h3_word Test</h3>
                <p>Priority unique_p_word Test</p>
            </body>
        </html>
        """
        
        extractor = KeywordExtractor(max_keywords=10)
        result = extractor.extract_keywords(priority_html, include_scores=True)
        
        # Get the ranks of the unique words
        keywords = result["keywords"]
        scores = result["scores"]
        
        # Find positions of unique words
        unique_words = {
            "title": "unique_title_word",
            "h1": "unique_h1_word",
            "h2": "unique_h2_word", 
            "h3": "unique_h3_word",
            "p": "unique_p_word"
        }
        
        found_words = {tag: word for tag, word in unique_words.items() if word in keywords}
        
        # If all words are found, check priority order
        if len(found_words) >= 4:  # Need most of them to verify ordering
            # Title should have higher score than h1, h1 higher than h2, etc.
            title_score = scores.get(unique_words["title"], 0)
            h1_score = scores.get(unique_words["h1"], 0)
            h2_score = scores.get(unique_words["h2"], 0)
            p_score = scores.get(unique_words["p"], 0)
            
            # Verify the priority weighting is reflected in scores
            assert title_score >= h1_score, "Title should have priority over h1"
            assert h1_score >= h2_score, "h1 should have priority over h2"
            assert h2_score >= p_score, "h2 should have priority over p"
    
    def test_stress_with_large_content(self):
        """Test performance with larger HTML content"""
        # Generate large HTML content
        large_html = "<html><body><div>"
        for i in range(500):  # 500 paragraphs
            large_html += f"<p>This is paragraph {i} with some random keywords like algorithm analysis computation performance optimization testing reliability assessment validation verification implementation deployment integration architecture design pattern architecture {i}</p>"
        large_html += "</div></body></html>"
        
        extractor = KeywordExtractor(max_keywords=30)
        
        # Extraction should complete within a reasonable time
        import time
        start_time = time.time()
        result = extractor.extract_keywords(large_html)
        keyphrases = extractor.extract_keyphrases(large_html)
        end_time = time.time()
        
        # Basic validation
        assert "keywords" in result
        assert len(result["keywords"]) > 0
        assert len(keyphrases) > 0
        
        # Time check - should complete within reasonable time (adjust if needed)
        assert end_time - start_time < 10, "Keyword extraction took too long with large content"
    
    def test_custom_stop_words(self):
        """Test tokenization with different stop word configurations"""
        # Since we can't modify the stop words directly, this tests the behavior
        # Create text with known stop words and valid words
        text = "This is an example of text with Python and algorithms and programming"
        
        # Default behavior - should filter out stop words
        extractor = KeywordExtractor(min_word_length=3)
        tokens = extractor.tokenize_text(text)
        
        # Standard stop words should be removed
        assert "this" not in tokens
        assert "and" not in tokens
        assert "with" not in tokens
        
        # Content words should remain
        assert "python" in tokens
        assert "algorithms" in tokens
        assert "programming" in tokens
        assert "example" in tokens
    
    def test_numeric_content_filtering(self):
        """Test handling of numeric content"""
        # HTML with mixed text and numbers
        numeric_html = """
        <html>
            <body>
                <h1>Statistics Report</h1>
                <p>The test achieved a 95% success rate with 500 iterations.</p>
                <p>Version 2.0.1 was released on 2025-05-15.</p>
                <p>The algorithm processed 10000 records in 3.5 seconds.</p>
            </body>
        </html>
        """
        
        extractor = KeywordExtractor()
        result = extractor.extract_keywords(numeric_html)
        
        # Check that pure numbers are filtered
        assert "500" not in result["keywords"]
        assert "10000" not in result["keywords"]
        assert "95" not in result["keywords"]
        assert "3.5" not in result["keywords"]
        
        # But text content is extracted
        assert "statistics" in result["keywords"]
        assert "success" in result["keywords"]
        assert "algorithm" in result["keywords"]
        assert "records" in result["keywords"]
    
    def test_serialization_to_json(self):
        """Test that extraction results can be properly serialized to JSON"""
        extractor = KeywordExtractor()
        result = extractor.extract_keywords(SAMPLE_HTML, include_scores=True)
        
        # Try to serialize to JSON
        try:
            json_str = json.dumps(result)
            # Parse back to verify
            parsed = json.loads(json_str)
            
            # Verify structure is preserved
            assert "keywords" in parsed
            assert "scores" in parsed
            assert isinstance(parsed["keywords"], list)
            assert isinstance(parsed["scores"], dict)
            assert len(parsed["keywords"]) == len(parsed["scores"])
        except Exception as e:
            pytest.fail(f"JSON serialization failed: {str(e)}")
    
    def test_footer_content_ignored(self):
        """Test that content inside <footer> is ignored for keyword extraction"""
        html_with_footer = """
        <html>
            <body>
                <h1>Main Content</h1>
                <p>This is the main body of the page.</p>
                <footer>
                    <p>Footer should not be included as keyword.</p>
                    <p>Copyright 2025 Footer Company</p>
                </footer>
            </body>
        </html>
        """
        extractor = KeywordExtractor()
        result = extractor.extract_keywords(html_with_footer)
        # Footer words should not appear
        for word in ["footer", "copyright", "company", "included"]:
            assert word not in result["keywords"], f"Footer word '{word}' should not be in keywords: {result['keywords']}"
        # Main content words should appear
        assert "main" in result["keywords"]
        assert "content" in result["keywords"]
        assert "body" in result["keywords"]
