#!/usr/bin/env python3
"""
parser - HTML and sitemap parsing utilities

This module provides parsers for various web content formats.
"""

# Re-export sitemap parser from utils for backward compatibility
from crawlit.utils.sitemap import SitemapParser

__all__ = ['SitemapParser']
