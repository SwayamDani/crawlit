#!/usr/bin/env python3
"""
csrf.py - CSRF token extraction and handling

Automatically detects and handles CSRF tokens in forms and AJAX requests.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Set
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CSRFTokenExtractor:
    """
    Extracts CSRF tokens from HTML pages.
    
    Supports multiple token formats and naming conventions.
    """
    
    # Common CSRF token names
    COMMON_TOKEN_NAMES = {
        'csrf_token', 'csrftoken', '_csrf', 'csrf',
        'authenticity_token', '_token', 'token',
        'xsrf_token', 'xsrftoken', '_xsrf',
        '__RequestVerificationToken',  # ASP.NET
        'form_build_id',  # Drupal
        '_wpnonce',  # WordPress
    }
    
    # Meta tag names for CSRF tokens
    META_TAG_NAMES = {
        'csrf-token', 'csrf_token', 'x-csrf-token',
        'xsrf-token', 'xsrf_token', 'x-xsrf-token',
    }
    
    def __init__(self, html_content: str, url: str = ""):
        """
        Initialize CSRF token extractor.
        
        Args:
            html_content: HTML content to extract tokens from
            url: URL of the page (for logging)
        """
        self.html_content = html_content
        self.url = url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.tokens: Dict[str, str] = {}
    
    def extract_all_tokens(self) -> Dict[str, str]:
        """
        Extract all CSRF tokens from the page.
        
        Returns:
            Dictionary of token names to token values
        """
        # Extract from hidden form fields
        self._extract_from_forms()
        
        # Extract from meta tags
        self._extract_from_meta_tags()
        
        # Extract from inline JavaScript
        self._extract_from_javascript()
        
        # Extract from data attributes
        self._extract_from_data_attributes()
        
        if self.tokens:
            logger.debug(f"Found {len(self.tokens)} CSRF token(s) on {self.url}")
        
        return self.tokens
    
    def _extract_from_forms(self):
        """Extract CSRF tokens from hidden form fields"""
        forms = self.soup.find_all('form')
        
        for form in forms:
            # Look for hidden input fields with common CSRF names
            for name in self.COMMON_TOKEN_NAMES:
                field = form.find('input', {'type': 'hidden', 'name': name})
                if field and field.get('value'):
                    self.tokens[name] = field['value']
                    logger.debug(f"Found CSRF token '{name}' in form")
            
            # Also check for any hidden field with 'csrf' or 'token' in name
            hidden_fields = form.find_all('input', {'type': 'hidden'})
            for field in hidden_fields:
                field_name = field.get('name', '').lower()
                if ('csrf' in field_name or 'token' in field_name or 'xsrf' in field_name) and field.get('value'):
                    self.tokens[field['name']] = field['value']
    
    def _extract_from_meta_tags(self):
        """Extract CSRF tokens from meta tags"""
        meta_tags = self.soup.find_all('meta')
        
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            
            # Check common meta tag names
            if name in self.META_TAG_NAMES and content:
                self.tokens[name] = content
                logger.debug(f"Found CSRF token in meta tag '{name}'")
    
    def _extract_from_javascript(self):
        """Extract CSRF tokens from inline JavaScript"""
        scripts = self.soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            script_content = script.string
            
            # Common patterns for CSRF tokens in JavaScript
            patterns = [
                r'csrfToken\s*[=:]\s*["\']([^"\']+)["\']',
                r'csrf_token\s*[=:]\s*["\']([^"\']+)["\']',
                r'CSRF_TOKEN\s*[=:]\s*["\']([^"\']+)["\']',
                r'_token\s*[=:]\s*["\']([^"\']+)["\']',
                r'authenticity_token\s*[=:]\s*["\']([^"\']+)["\']',
                r'xsrfToken\s*[=:]\s*["\']([^"\']+)["\']',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                if matches:
                    # Use the pattern as a token name
                    token_name = pattern.split('\\')[0]
                    self.tokens[token_name] = matches[0]
                    logger.debug(f"Found CSRF token in JavaScript: {token_name}")
    
    def _extract_from_data_attributes(self):
        """Extract CSRF tokens from data-* attributes"""
        # Look for elements with data-csrf-token or similar
        for element in self.soup.find_all(attrs={'data-csrf-token': True}):
            value = element.get('data-csrf-token')
            if value:
                self.tokens['data-csrf-token'] = value
        
        for element in self.soup.find_all(attrs={'data-token': True}):
            value = element.get('data-token')
            if value:
                self.tokens['data-token'] = value
    
    def get_token(self, preferred_name: Optional[str] = None) -> Optional[str]:
        """
        Get a CSRF token, optionally with a preferred name.
        
        Args:
            preferred_name: Preferred token name to look for
            
        Returns:
            Token value or None if not found
        """
        if not self.tokens:
            self.extract_all_tokens()
        
        if preferred_name and preferred_name in self.tokens:
            return self.tokens[preferred_name]
        
        # Return any available token
        return next(iter(self.tokens.values())) if self.tokens else None
    
    def get_all_tokens(self) -> Dict[str, str]:
        """Get all extracted tokens"""
        if not self.tokens:
            self.extract_all_tokens()
        return self.tokens.copy()


class CSRFTokenHandler:
    """
    Handles CSRF tokens during crawling.
    
    Maintains a token store and automatically includes tokens in requests.
    """
    
    def __init__(self):
        """Initialize CSRF token handler"""
        self.token_store: Dict[str, Dict[str, str]] = {}  # URL -> tokens
        self.global_tokens: Dict[str, str] = {}  # Tokens that apply globally
    
    def extract_and_store(self, url: str, html_content: str) -> Dict[str, str]:
        """
        Extract CSRF tokens from a page and store them.
        
        Args:
            url: URL of the page
            html_content: HTML content
            
        Returns:
            Dictionary of extracted tokens
        """
        extractor = CSRFTokenExtractor(html_content, url)
        tokens = extractor.extract_all_tokens()
        
        if tokens:
            self.token_store[url] = tokens
            logger.info(f"Stored {len(tokens)} CSRF token(s) for {url}")
        
        return tokens
    
    def get_tokens_for_url(self, url: str) -> Dict[str, str]:
        """
        Get CSRF tokens for a specific URL.
        
        Args:
            url: URL to get tokens for
            
        Returns:
            Dictionary of tokens (combines URL-specific and global tokens)
        """
        tokens = self.global_tokens.copy()
        
        if url in self.token_store:
            tokens.update(self.token_store[url])
        
        return tokens
    
    def set_global_token(self, name: str, value: str):
        """
        Set a global CSRF token that applies to all requests.
        
        Args:
            name: Token name
            value: Token value
        """
        self.global_tokens[name] = value
        logger.debug(f"Set global CSRF token: {name}")
    
    def add_tokens_to_request(self, url: str, data: Optional[Dict[str, Any]] = None,
                             headers: Optional[Dict[str, str]] = None) -> tuple[Dict[str, Any], Dict[str, str]]:
        """
        Add CSRF tokens to request data and headers.
        
        Args:
            url: Target URL
            data: Request data (form data)
            headers: Request headers
            
        Returns:
            Tuple of (updated_data, updated_headers)
        """
        data = data or {}
        headers = headers or {}
        
        tokens = self.get_tokens_for_url(url)
        
        if tokens:
            # Add tokens to form data
            for name, value in tokens.items():
                if name not in data:
                    data[name] = value
            
            # Add tokens to headers (common for AJAX requests)
            if 'csrf_token' in tokens:
                headers['X-CSRF-Token'] = tokens['csrf_token']
            if 'xsrf_token' in tokens:
                headers['X-XSRF-Token'] = tokens['xsrf_token']
            
            logger.debug(f"Added {len(tokens)} CSRF token(s) to request for {url}")
        
        return data, headers
    
    def clear_tokens(self, url: Optional[str] = None):
        """
        Clear stored tokens.
        
        Args:
            url: Specific URL to clear tokens for (None = clear all)
        """
        if url:
            if url in self.token_store:
                del self.token_store[url]
                logger.debug(f"Cleared tokens for {url}")
        else:
            self.token_store.clear()
            self.global_tokens.clear()
            logger.debug("Cleared all CSRF tokens")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored tokens.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'urls_with_tokens': len(self.token_store),
            'global_tokens': len(self.global_tokens),
            'total_tokens': sum(len(tokens) for tokens in self.token_store.values()) + len(self.global_tokens),
            'token_names': list(set(
                list(self.global_tokens.keys()) +
                [name for tokens in self.token_store.values() for name in tokens.keys()]
            ))
        }


def extract_csrf_token(html_content: str, token_name: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to extract a CSRF token from HTML.
    
    Args:
        html_content: HTML content
        token_name: Optional specific token name to look for
        
    Returns:
        Token value or None
    """
    extractor = CSRFTokenExtractor(html_content)
    return extractor.get_token(token_name)


def extract_all_csrf_tokens(html_content: str) -> Dict[str, str]:
    """
    Convenience function to extract all CSRF tokens from HTML.
    
    Args:
        html_content: HTML content
        
    Returns:
        Dictionary of token names to values
    """
    extractor = CSRFTokenExtractor(html_content)
    return extractor.extract_all_tokens()



