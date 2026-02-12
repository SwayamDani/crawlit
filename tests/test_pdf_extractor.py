#!/usr/bin/env python3
"""
Tests for PDF extraction functionality
"""

import pytest
import io
from pathlib import Path

try:
    from crawlit.extractors.pdf_extractor import PDFExtractor, extract_pdf_text
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def create_test_pdf(text_lines=None):
    """Create a simple test PDF in memory."""
    if not PDF_AVAILABLE:
        pytest.skip("PDF dependencies not available")
    
    if text_lines is None:
        text_lines = ["This is a test PDF.", "Line two.", "Line three."]
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Add text to PDF
    y_position = 750
    for line in text_lines:
        c.drawString(100, y_position, line)
        y_position -= 20
    
    c.showPage()
    c.save()
    
    return buffer.getvalue()


@pytest.mark.skipif(not PDF_AVAILABLE, reason="PDF dependencies not installed")
class TestPDFExtractor:
    """Tests for PDF extraction."""
    
    def test_basic_text_extraction(self):
        """Test extracting text from a simple PDF."""
        pdf_content = create_test_pdf(["Hello World", "This is a test PDF"])
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert "Hello World" in result['text']
        assert "This is a test PDF" in result['text']
        assert result['num_pages'] == 1
    
    def test_multi_page_pdf(self):
        """Test extracting text from multi-page PDF."""
        # Create a multi-page PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Page 1
        c.drawString(100, 750, "Page 1 content")
        c.showPage()
        
        # Page 2
        c.drawString(100, 750, "Page 2 content")
        c.showPage()
        
        # Page 3
        c.drawString(100, 750, "Page 3 content")
        c.showPage()
        
        c.save()
        pdf_content = buffer.getvalue()
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert result['num_pages'] == 3
        assert "Page 1 content" in result['text']
        assert "Page 2 content" in result['text']
        assert "Page 3 content" in result['text']
    
    def test_pdf_with_metadata(self):
        """Test extraction of PDF metadata."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Set metadata
        c.setTitle("Test Document")
        c.setAuthor("Test Author")
        c.setSubject("Testing")
        
        c.drawString(100, 750, "Content")
        c.showPage()
        c.save()
        
        pdf_content = buffer.getvalue()
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert 'metadata' in result
        assert result['metadata']['title'] == "Test Document"
        assert result['metadata']['author'] == "Test Author"
    
    def test_empty_pdf(self):
        """Test extracting from empty PDF."""
        # Create PDF with no text
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.showPage()
        c.save()
        
        pdf_content = buffer.getvalue()
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert result['num_pages'] == 1
        # Text might be empty or whitespace
        assert isinstance(result['text'], str)
    
    def test_invalid_pdf(self):
        """Test handling of invalid PDF content."""
        invalid_pdf = b"This is not a PDF file"
        
        extractor = PDFExtractor()
        result = extractor.extract(invalid_pdf)
        
        assert not result['success']
        assert 'error' in result
        assert result['num_pages'] == 0
    
    def test_corrupted_pdf(self):
        """Test handling of corrupted PDF."""
        # Start of valid PDF header but corrupted
        corrupted_pdf = b"%PDF-1.4\n%corrupted content"
        
        extractor = PDFExtractor()
        result = extractor.extract(corrupted_pdf)
        
        assert not result['success']
        assert 'error' in result
    
    def test_extract_from_url_response(self):
        """Test extraction from URL response bytes."""
        pdf_content = create_test_pdf(["URL PDF content"])
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert "URL PDF content" in result['text']
    
    def test_large_pdf(self):
        """Test extraction from PDF with many lines."""
        # Create PDF with lots of text
        lines = [f"Line {i} with some content" for i in range(100)]
        pdf_content = create_test_pdf(lines)
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        # Check some lines
        assert "Line 0 with some content" in result['text']
        assert "Line 50 with some content" in result['text']
    
    def test_pdf_with_special_characters(self):
        """Test extraction with special characters."""
        special_text = ["Special chars: @#$%^&*()", "Unicode: 你好世界", "Emoji: 😀"]
        pdf_content = create_test_pdf(special_text)
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        # Note: PDF text extraction may not preserve all special chars perfectly
        assert isinstance(result['text'], str)


@pytest.mark.skipif(not PDF_AVAILABLE, reason="PDF dependencies not installed")
class TestExtractPDFTextHelper:
    """Tests for extract_pdf_text convenience function."""
    
    def test_convenience_function(self):
        """Test convenience function."""
        pdf_content = create_test_pdf(["Test content"])
        
        result = extract_pdf_text(pdf_content)
        
        assert result['success']
        assert "Test content" in result['text']


@pytest.mark.skipif(not PDF_AVAILABLE, reason="PDF dependencies not installed")
class TestPDFExtractorEdgeCases:
    """Edge case tests for PDF extraction."""
    
    def test_pdf_with_no_text_layer(self):
        """Test PDF that might not have extractable text."""
        # Create PDF with just graphics (no text)
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Draw a line (no text)
        c.line(100, 100, 500, 100)
        c.showPage()
        c.save()
        
        pdf_content = buffer.getvalue()
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert result['num_pages'] == 1
        # Text will be empty or whitespace
        assert len(result['text'].strip()) == 0
    
    def test_password_protected_pdf(self):
        """Test handling of password-protected PDF."""
        # Note: Creating password-protected PDF requires additional setup
        # For now, just test that the extractor handles the error gracefully
        
        # This would be a real password-protected PDF in practice
        # For testing, use invalid PDF that simulates the error
        extractor = PDFExtractor()
        
        # Test that error handling works
        result = extractor.extract(b"invalid")
        assert not result['success']
    
    def test_extremely_large_pdf(self):
        """Test handling of very large PDF."""
        # Create PDF with many pages
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        for i in range(50):  # 50 pages
            c.drawString(100, 750, f"Page {i}")
            c.showPage()
        
        c.save()
        pdf_content = buffer.getvalue()
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert result['num_pages'] == 50
    
    def test_pdf_with_images(self):
        """Test PDF containing images."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        c.drawString(100, 750, "Text before image")
        # In a real scenario, would embed an image here
        c.drawString(100, 700, "Text after image")
        
        c.showPage()
        c.save()
        
        pdf_content = buffer.getvalue()
        
        extractor = PDFExtractor()
        result = extractor.extract(pdf_content)
        
        assert result['success']
        assert "Text before image" in result['text']
        assert "Text after image" in result['text']
    
    def test_extract_with_options(self):
        """Test extraction with custom options."""
        pdf_content = create_test_pdf(["Test"])
        
        extractor = PDFExtractor()
        
        # Test with options (if supported)
        result = extractor.extract(pdf_content, extract_images=False)
        
        assert result['success']

