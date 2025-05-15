"""
Extractors module for Crawlit.
This package contains various data extraction modules for the Crawlit web crawler.
"""

from .tables import extract_tables, tables_to_csv, tables_to_dict

__all__ = [
    'extract_tables',
    'tables_to_csv',
    'tables_to_dict',
]
