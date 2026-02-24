#!/usr/bin/env python3
"""
sitemap_parser - Re-export from utils.sitemap

For backward compatibility, this module re-exports the SitemapParser class
which is actually implemented in crawlit.utils.sitemap
"""

from crawlit.utils.sitemap import SitemapParser

__all__ = ['SitemapParser']
