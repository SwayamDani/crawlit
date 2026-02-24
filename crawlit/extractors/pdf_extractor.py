#!/usr/bin/env python3
"""
pdf_extractor.py - PDF text and metadata extraction

Extracts text and metadata from PDF files with optional OCR support.
"""

import logging
import io
from typing import Dict, List, Optional, Any, BinaryIO
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import PDF libraries
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.debug("pdfplumber not available")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.debug("PyPDF2 not available")

# Try to import OCR library (optional)
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.debug("OCR support not available (requires PIL and pytesseract)")


class PDFExtractor:
    """
    Extract text and metadata from PDF files.
    
    Supports multiple backends: pdfplumber (preferred) and PyPDF2.
    Optional OCR support for scanned PDFs.
    """
    
    def __init__(
        self,
        backend: str = 'auto',
        enable_ocr: bool = False,
        ocr_language: str = 'eng'
    ):
        """
        Initialize the PDF extractor.
        
        Args:
            backend: PDF extraction backend ('auto', 'pdfplumber', 'pypdf2')
            enable_ocr: Whether to use OCR for scanned PDFs
            ocr_language: Tesseract OCR language code
        """
        self.backend = backend
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        
        # Determine which backend to use
        if backend == 'auto':
            if PDFPLUMBER_AVAILABLE:
                self.backend = 'pdfplumber'
            elif PYPDF2_AVAILABLE:
                self.backend = 'pypdf2'
            else:
                raise ImportError("No PDF library available. Install pdfplumber or PyPDF2")
        
        if enable_ocr and not OCR_AVAILABLE:
            logger.warning("OCR requested but not available. Install PIL and pytesseract")
            self.enable_ocr = False
        
        logger.debug(f"PDF extractor initialized with backend: {self.backend}, OCR: {self.enable_ocr}")
    
    def extract(self, pdf_bytes: bytes, extract_images: bool = True) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF bytes.
        
        This is an alias for extract_from_bytes for backward compatibility with tests.
        
        Args:
            pdf_bytes: PDF file as bytes
            extract_images: Whether to extract images (currently ignored)
            
        Returns:
            Dictionary containing:
                - text: Extracted text content
                - num_pages: Number of pages
                - metadata: PDF metadata (title, author, etc.)
                - success: Boolean indicating success
                - error: Error message if failed
        """
        result = self.extract_from_bytes(pdf_bytes)
        # Add num_pages alias for backward compatibility
        if 'pages' in result:
            result['num_pages'] = result['pages']
        return result
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF bytes.
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Dictionary containing:
                - text: Extracted text content
                - pages: Number of pages
                - metadata: PDF metadata (title, author, etc.)
                - success: Boolean indicating success
                - error: Error message if failed
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            return self.extract_from_file(pdf_file)
        except Exception as e:
            logger.error(f"Failed to extract from PDF bytes: {e}")
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': str(e)
            }
    
    def extract_from_path(self, filepath: str) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF file path.
        
        Args:
            filepath: Path to PDF file
            
        Returns:
            Dictionary with extraction results
        """
        try:
            with open(filepath, 'rb') as f:
                return self.extract_from_file(f)
        except FileNotFoundError:
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': f'File not found: {filepath}'
            }
        except Exception as e:
            logger.error(f"Failed to extract from {filepath}: {e}")
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': str(e)
            }
    
    def extract_from_file(self, pdf_file: BinaryIO) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF file object.
        
        Args:
            pdf_file: File-like object containing PDF data
            
        Returns:
            Dictionary with extraction results
        """
        if self.backend == 'pdfplumber':
            return self._extract_with_pdfplumber(pdf_file)
        elif self.backend == 'pypdf2':
            return self._extract_with_pypdf2(pdf_file)
        else:
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': f'Unknown backend: {self.backend}'
            }
    
    def _extract_with_pdfplumber(self, pdf_file: BinaryIO) -> Dict[str, Any]:
        """Extract using pdfplumber (preferred method)."""
        if not PDFPLUMBER_AVAILABLE:
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': 'pdfplumber not available'
            }
        
        try:
            with pdfplumber.open(pdf_file) as pdf:
                text_content = []
                
                # Extract text from each page
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
                
                # Get metadata
                metadata = pdf.metadata or {}
                
                result = {
                    'text': '\n\n'.join(text_content),
                    'pages': len(pdf.pages),
                    'metadata': self._clean_metadata(metadata),
                    'success': True,
                    'error': None
                }
                
                logger.info(f"Extracted {len(pdf.pages)} pages from PDF using pdfplumber")
                return result
                
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': str(e)
            }
    
    def _extract_with_pypdf2(self, pdf_file: BinaryIO) -> Dict[str, Any]:
        """Extract using PyPDF2 (fallback method)."""
        if not PYPDF2_AVAILABLE:
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': 'PyPDF2 not available'
            }
        
        try:
            reader = PdfReader(pdf_file)
            text_content = []
            
            # Extract text from each page
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            
            # Get metadata
            metadata = reader.metadata or {}
            
            result = {
                'text': '\n\n'.join(text_content),
                'pages': len(reader.pages),
                'metadata': self._clean_metadata(metadata),
                'success': True,
                'error': None
            }
            
            logger.info(f"Extracted {len(reader.pages)} pages from PDF using PyPDF2")
            return result
            
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return {
                'text': '',
                'pages': 0,
                'metadata': {},
                'success': False,
                'error': str(e)
            }
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and format PDF metadata.
        
        Args:
            metadata: Raw PDF metadata
            
        Returns:
            Cleaned metadata dictionary
        """
        cleaned = {}
        
        # Common metadata fields (support both with and without leading slash)
        field_mapping = {
            '/Title': 'title',
            '/Author': 'author',
            '/Subject': 'subject',
            '/Creator': 'creator',
            '/Producer': 'producer',
            '/CreationDate': 'creation_date',
            '/ModDate': 'modification_date',
            '/Keywords': 'keywords',
            'Title': 'title',
            'Author': 'author',
            'Subject': 'subject',
            'Creator': 'creator',
            'Producer': 'producer',
            'CreationDate': 'creation_date',
            'ModDate': 'modification_date',
            'Keywords': 'keywords',
        }
        
        for key, value in metadata.items():
            # Use mapped name if available
            if key in field_mapping:
                clean_key = field_mapping[key]
            else:
                # Remove leading slash if present
                clean_key = key.lstrip('/') if isinstance(key, str) else str(key)
                clean_key = clean_key.lower()
            
            # Convert value to string if needed
            if value is not None:
                cleaned[clean_key] = str(value)
            if value is not None:
                cleaned[clean_key] = str(value)
        
        return cleaned
    
    def is_pdf(self, content_type: str = "", content: bytes = b"") -> bool:
        """
        Check if content is a PDF file.
        
        Args:
            content_type: MIME type from HTTP headers
            content: File content bytes
            
        Returns:
            True if content appears to be PDF
        """
        # Check content type
        if 'application/pdf' in content_type.lower():
            return True
        
        # Check magic number (PDF signature)
        if content and content.startswith(b'%PDF-'):
            return True
        
        return False


def extract_pdf_text(pdf_data: bytes, backend: str = 'auto', enable_ocr: bool = False) -> Dict[str, Any]:
    """
    Convenience function to extract text from PDF.
    
    Args:
        pdf_data: PDF file as bytes
        backend: PDF extraction backend ('auto', 'pdfplumber', 'pypdf2')
        enable_ocr: Whether to use OCR for scanned PDFs
        
    Returns:
        Dictionary with extraction results
    """
    extractor = PDFExtractor(backend=backend, enable_ocr=enable_ocr)
    return extractor.extract_from_bytes(pdf_data)


def is_pdf_available() -> bool:
    """
    Check if PDF extraction is available.
    
    Returns:
        True if at least one PDF library is available
    """
    return PDFPLUMBER_AVAILABLE or PYPDF2_AVAILABLE




