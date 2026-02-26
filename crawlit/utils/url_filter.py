#!/usr/bin/env python3
"""
url_filter.py - Advanced URL filtering utilities
"""

import re
import logging
from typing import List, Optional, Pattern, Set, Callable
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


class URLFilter:
    """
    Advanced URL filtering with support for regex patterns, file extensions,
    query parameters, and custom filter functions.
    """
    
    def __init__(
        self,
        allowed_patterns: Optional[List[Pattern]] = None,
        blocked_patterns: Optional[List[Pattern]] = None,
        allowed_extensions: Optional[List[str]] = None,
        blocked_extensions: Optional[List[str]] = None,
        allowed_query_params: Optional[List[str]] = None,
        blocked_query_params: Optional[List[str]] = None,
        custom_filter: Optional[Callable[[str], bool]] = None
    ) -> None:
        """
        Initialize URL filter with various filtering options.
        
        Args:
            allowed_patterns: List of regex patterns that URLs must match (whitelist)
            blocked_patterns: List of regex patterns that URLs must not match (blacklist)
            allowed_extensions: List of file extensions to allow (e.g., ['.html', '.htm'])
            blocked_extensions: List of file extensions to block (e.g., ['.pdf', '.zip'])
            allowed_query_params: List of query parameter names that must be present
            blocked_query_params: List of query parameter names that must not be present
            custom_filter: Custom function that takes a URL and returns True if allowed
        """
        self.allowed_patterns: List[Pattern] = allowed_patterns or []
        self.blocked_patterns: List[Pattern] = blocked_patterns or []
        self.allowed_extensions: Set[str] = set(allowed_extensions or [])
        self.blocked_extensions: Set[str] = set(blocked_extensions or [])
        self.allowed_query_params: Set[str] = set(allowed_query_params or [])
        self.blocked_query_params: Set[str] = set(blocked_query_params or [])
        self.custom_filter: Optional[Callable[[str], bool]] = custom_filter
    
    def is_allowed(self, url: str) -> bool:
        """
        Check if a URL is allowed based on all configured filters.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL is allowed, False otherwise
        """
        # Check custom filter first
        if self.custom_filter and not self.custom_filter(url):
            logger.debug(f"URL blocked by custom filter: {url}")
            return False
        
        # Check blocked patterns (blacklist)
        for pattern in self.blocked_patterns:
            if pattern.search(url):
                logger.debug(f"URL blocked by pattern {pattern.pattern}: {url}")
                return False
        
        # Check allowed patterns (whitelist) - if any patterns are specified
        if self.allowed_patterns:
            matched = False
            for pattern in self.allowed_patterns:
                if pattern.search(url):
                    matched = True
                    break
            if not matched:
                logger.debug(f"URL not in allowed patterns: {url}")
                return False
        
        # Check file extensions
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Extract extension
        if '.' in path:
            ext = '.' + path.split('.')[-1]
        else:
            ext = ''
        
        # Check blocked extensions
        if ext and ext in self.blocked_extensions:
            logger.debug(f"URL blocked by extension {ext}: {url}")
            return False
        
        # Check allowed extensions (if specified)
        if self.allowed_extensions:
            # Empty extension is allowed if '' is in allowed_extensions
            if ext not in self.allowed_extensions:
                logger.debug(f"URL extension {ext} not in allowed list: {url}")
                return False
        
        # Check query parameters
        query_params = parse_qs(parsed.query)
        param_names = set(query_params.keys())
        
        # Check blocked query parameters
        if self.blocked_query_params and param_names.intersection(self.blocked_query_params):
            logger.debug(f"URL blocked by query parameters: {url}")
            return False
        
        # Check allowed query parameters (if specified)
        if self.allowed_query_params:
            if not param_names.intersection(self.allowed_query_params):
                logger.debug(f"URL missing required query parameters: {url}")
                return False
        
        return True
    
    @classmethod
    def from_patterns(
        cls,
        allowed_regex: Optional[str] = None,
        blocked_regex: Optional[str] = None,
        **kwargs
    ) -> 'URLFilter':
        """
        Create a URLFilter from regex pattern strings.

        Args:
            allowed_regex: Regex pattern string for allowed URLs
            blocked_regex: Regex pattern string for blocked URLs
            **kwargs: Additional arguments passed to __init__

        Returns:
            A configured URLFilter instance

        Raises:
            ValueError: If either regex string is invalid.

        Note:
            User-supplied patterns are compiled without a timeout.  A
            pathological expression such as ``(a+)+$`` can cause
            catastrophic backtracking (ReDoS) on long URLs.  Keep
            patterns simple and avoid unbounded nested quantifiers.
        """
        allowed_patterns = None
        if allowed_regex:
            try:
                allowed_patterns = [re.compile(allowed_regex)]
            except re.error as exc:
                raise ValueError(f"Invalid allowed_regex pattern {allowed_regex!r}: {exc}") from exc

        blocked_patterns = None
        if blocked_regex:
            try:
                blocked_patterns = [re.compile(blocked_regex)]
            except re.error as exc:
                raise ValueError(f"Invalid blocked_regex pattern {blocked_regex!r}: {exc}") from exc

        return cls(
            allowed_patterns=allowed_patterns,
            blocked_patterns=blocked_patterns,
            **kwargs
        )
    
    @classmethod
    def html_only(cls) -> 'URLFilter':
        """
        Create a filter that only allows HTML pages.
        
        Returns:
            A URLFilter configured to only allow HTML files
        """
        return cls(
            allowed_extensions=['.html', '.htm', ''],
            blocked_extensions=['.pdf', '.zip', '.jpg', '.png', '.gif', '.css', '.js']
        )
    
    @classmethod
    def exclude_media(cls) -> 'URLFilter':
        """
        Create a filter that excludes media files.
        
        Returns:
            A URLFilter configured to block common media file extensions
        """
        return cls(
            blocked_extensions=[
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
                '.mp4', '.avi', '.mov', '.wmv', '.flv',
                '.mp3', '.wav', '.ogg', '.m4a',
                '.pdf', '.zip', '.rar', '.tar', '.gz'
            ]
        )


# Query-parameter names that are commonly used for credentials / secrets and
# should be redacted before a URL is written to log files.
_SENSITIVE_PARAMS: Set[str] = {
    'api_key', 'apikey', 'api-key',
    'token', 'access_token', 'auth_token',
    'secret', 'client_secret',
    'password', 'passwd', 'pass',
    'key', 'private_key',
    'auth', 'authorization',
    'session', 'session_id', 'sessionid',
    'csrf', 'csrftoken', 'csrf_token',
    'signature', 'sig',
}

_REDACTED = 'REDACTED'


def sanitize_url_for_log(url: str) -> str:
    """
    Return a copy of *url* with sensitive query-parameter values replaced by
    ``REDACTED``.  The URL structure (scheme, host, path, …) is preserved so
    log entries remain useful for debugging while credentials are not leaked.

    Args:
        url: The URL to sanitize.

    Returns:
        URL string safe to write to log files.
    """
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url

        # Re-encode query string, masking sensitive parameter values
        pairs = []
        for part in parsed.query.split('&'):
            if '=' in part:
                name, _, value = part.partition('=')
                if name.lower() in _SENSITIVE_PARAMS:
                    pairs.append(f"{name}={_REDACTED}")
                else:
                    pairs.append(part)
            else:
                pairs.append(part)

        sanitized = urlunparse(parsed._replace(query='&'.join(pairs)))
        return sanitized
    except Exception:
        # Never let sanitization crash the caller
        return url

