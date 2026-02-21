#!/usr/bin/env python3
"""
html_parser.py - HTML parsing utilities
"""

import logging
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class HTMLParser:
    """
    HTML parser for extracting links, text, and other content from HTML documents.
    """
    
    def __init__(self, parser: str = "html.parser"):
        """
        Initialize the HTML parser.
        
        Args:
            parser: BeautifulSoup parser to use ('html.parser', 'lxml', 'html5lib')
        """
        self.parser = parser
    
    def parse(self, html: str, base_url: str) -> Dict[str, Any]:
        """
        Parse HTML content and extract useful information.
        
        Args:
            html: HTML content to parse
            base_url: Base URL for resolving relative links
            
        Returns:
            Dictionary containing:
                - links: List of absolute URLs found in the document
                - title: Page title
                - text: Extracted text content
                - meta: Meta tags
        """
        try:
            soup = BeautifulSoup(html, self.parser)
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Extract all links
            links = []
            for tag in soup.find_all('a', href=True):
                href = tag['href']
                # Convert to absolute URL
                absolute_url = urljoin(base_url, href)
                links.append(absolute_url)
            
            # Extract text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Extract meta tags
            meta = {}
            for tag in soup.find_all('meta'):
                name = tag.get('name') or tag.get('property')
                content = tag.get('content')
                if name and content:
                    meta[name] = content
            
            return {
                'links': links,
                'title': title,
                'text': text,
                'meta': meta,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return {
                'links': [],
                'title': '',
                'text': '',
                'meta': {},
                'success': False,
                'error': str(e)
            }
    
    def extract_links(self, html: str, base_url: str) -> List[str]:
        """
        Extract only links from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        result = self.parse(html, base_url)
        return result.get('links', [])
    
    def extract_text(self, html: str) -> str:
        """
        Extract only text content from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted text
        """
        try:
            soup = BeautifulSoup(html, self.parser)
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
