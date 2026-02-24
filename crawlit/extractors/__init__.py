"""
Extractors module for Crawlit.
This package contains various data extraction modules for the Crawlit web crawler.
"""

from .tables import extract_tables, tables_to_csv, tables_to_dict, tables_to_json
from .image_extractor import ImageTagParser
from .keyword_extractor import KeywordExtractor
from .content_extractor import ContentExtractor
from .forms import FormExtractor, Form, FormField, extract_forms
from .structured_data import StructuredDataExtractor, StructuredData, extract_structured_data
from .language import LanguageDetector, LanguageDetection, detect_language
from .pdf_extractor import PDFExtractor, extract_pdf_text, is_pdf_available

__all__ = [
    # Tables
    'extract_tables',
    'tables_to_csv',
    'tables_to_dict',
    'tables_to_json',
    
    # Images
    'ImageTagParser',
    
    # Keywords
    'KeywordExtractor',
    
    # Content
    'ContentExtractor',
    
    # Forms (NEW)
    'FormExtractor',
    'Form',
    'FormField',
    'extract_forms',
    
    # Structured Data (NEW)
    'StructuredDataExtractor',
    'StructuredData',
    'extract_structured_data',
    
    # Language Detection (NEW)
    'LanguageDetector',
    'LanguageDetection',
    'detect_language',
    
    # PDF Extraction (NEW)
    'PDFExtractor',
    'extract_pdf_text',
    'is_pdf_available',
]
