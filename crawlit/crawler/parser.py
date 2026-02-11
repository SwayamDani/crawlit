#!/usr/bin/env python3
"""
parser.py - HTML parsing and link extraction using BeautifulSoup
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_links(
    html_content: str, 
    base_url: str, 
    delay: float = 0.1
) -> List[str]:
    """
    Extract links from HTML content from various elements using BeautifulSoup
    
    Args:
        html_content: The HTML content to parse
        base_url: The base URL for resolving relative links
        delay: Delay in seconds to be polite to the server (not used here)
        
    Returns:
        list: List of absolute URLs found in the HTML
    """
    # Note: The delay parameter is not used here anymore.
    # Delay handling is managed at the crawler engine level between HTTP requests.
    # This avoids double delays (one for fetching, one for parsing).
    
    # Convert to string if bytes
    if isinstance(html_content, bytes):
        try:
            html_content = html_content.decode('utf-8')
        except UnicodeDecodeError:
            html_content = html_content.decode('latin-1')
    
    links = set()  # Using a set to avoid duplicates
    
    # Dictionary of elements and their attributes that may contain URLs
    elements_to_extract = {
        'a': 'href',
        'img': 'src',
        'script': 'src',
        'link': 'href',
        'iframe': 'src',
        'video': 'src',
        'audio': 'src',
        'source': 'src',
        'form': 'action'
    }
    
    # Parse the HTML with BeautifulSoup
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract links from each element type
        for tag_name, attr_name in elements_to_extract.items():
            for element in soup.find_all(tag_name):
                if element.has_attr(attr_name):
                    url = element[attr_name].strip()
                    
                    # Process the URL
                    processed_url = _process_url(url, base_url)
                    if processed_url:
                        links.add(processed_url)
    except Exception as e:
        logger.error(f"Error parsing HTML content with BeautifulSoup: {e}")
    
    return list(links)

def _process_url(url: str, base_url: str) -> Optional[str]:
    """
    Process a URL: normalize, filter, and convert to absolute
    
    Args:
        url: The URL to process
        base_url: The base URL for resolving relative links
        
    Returns:
        str: Processed URL or None if URL should be filtered out
    """
    # Skip empty links, javascript links, mailto links, tel links, etc.
    if (not url or 
        url.startswith(('javascript:', 'mailto:', 'tel:', '#', 'data:'))):
        return None
            
    # Convert relative URLs to absolute
    absolute_url = urljoin(base_url, url)
    
    # Parse the URL
    parsed = urlparse(absolute_url)
    
    # Skip non-HTTP URLs
    if parsed.scheme not in ('http', 'https'):
        return None
    
    # Normalize the URL (remove fragments, etc.)
    normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        normalized_url += f"?{parsed.query}"
    
    # Remove trailing slashes for consistency unless the path is just "/"
    if normalized_url.endswith('/') and normalized_url[-2] != '/':
        normalized_url = normalized_url[:-1]
    
    return normalized_url