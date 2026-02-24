#!/usr/bin/env python3
"""
session_manager.py - Session management for authenticated crawls
"""

import logging
from typing import Dict, Optional, Any, Union, Tuple
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
import aiohttp
from aiohttp import BasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages HTTP sessions for both synchronous and asynchronous crawling.
    Provides cookie persistence, authentication, and session reuse across requests.
    
    Supports multiple authentication methods:
    - Cookies
    - Custom headers (API keys, custom auth headers)
    - OAuth 2.0 Bearer tokens
    - Basic authentication
    - Digest authentication
    """
    
    def __init__(
        self, 
        user_agent: str = "crawlit/2.0",
        timeout: int = 10,
        max_retries: int = 3,
        verify_ssl: bool = True,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Union[Tuple[str, str], HTTPBasicAuth, HTTPDigestAuth]] = None,
        oauth_token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_header: str = "X-API-Key",
        pool_size: int = 10
    ) -> None:
        """
        Initialize the session manager.
        
        Args:
            user_agent: User agent string to use in requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            verify_ssl: Whether to verify SSL certificates
            cookies: Optional initial cookies to set
            headers: Optional custom headers to include in all requests
            auth: Optional authentication tuple (username, password) or HTTPBasicAuth/HTTPDigestAuth instance
            oauth_token: Optional OAuth 2.0 bearer token (will be added as Authorization: Bearer <token>)
            api_key: Optional API key (will be added as a custom header)
            api_key_header: Header name for API key (default: "X-API-Key")
            pool_size: Maximum number of connections to keep in pool (default: 10)
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.pool_size = pool_size
        self._sync_session: Optional[requests.Session] = None
        self._async_session: Optional[aiohttp.ClientSession] = None
        self._initial_cookies = cookies or {}
        
        # Authentication options
        self._custom_headers = headers or {}
        self._auth = auth
        self._oauth_token = oauth_token
        self._api_key = api_key
        self._api_key_header = api_key_header
        
        # Build headers dictionary
        self._build_headers()
    
    def _build_headers(self) -> Dict[str, str]:
        """Build the headers dictionary with all authentication headers."""
        headers = self._custom_headers.copy()
        
        # Add OAuth bearer token if provided
        if self._oauth_token:
            headers["Authorization"] = f"Bearer {self._oauth_token}"
            logger.debug("OAuth bearer token configured")
        
        # Add API key if provided
        if self._api_key:
            headers[self._api_key_header] = self._api_key
            logger.debug(f"API key configured in header: {self._api_key_header}")
        
        return headers
    
    def get_sync_session(self) -> requests.Session:
        """
        Get or create a synchronous requests.Session.
        
        Returns:
            A configured requests.Session instance
        """
        if self._sync_session is None:
            self._sync_session = requests.Session()
            
            # Set default headers
            default_headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            # Add custom headers (including auth headers)
            auth_headers = self._build_headers()
            default_headers.update(auth_headers)
            
            self._sync_session.headers.update(default_headers)
            
            # Set authentication if provided
            if self._auth:
                if isinstance(self._auth, (HTTPBasicAuth, HTTPDigestAuth)):
                    self._sync_session.auth = self._auth
                elif isinstance(self._auth, tuple) and len(self._auth) == 2:
                    self._sync_session.auth = HTTPBasicAuth(self._auth[0], self._auth[1])
                logger.debug("Basic/Digest authentication configured")
            
            # Set initial cookies if provided
            if self._initial_cookies:
                self._sync_session.cookies.update(self._initial_cookies)
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET", "HEAD"]
            )
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=self.pool_size,
                pool_maxsize=self.pool_size
            )
            self._sync_session.mount("http://", adapter)
            self._sync_session.mount("https://", adapter)
            
            # Set SSL verification
            self._sync_session.verify = self.verify_ssl
        
        return self._sync_session
    
    async def get_async_session(self) -> aiohttp.ClientSession:
        """
        Get or create an asynchronous aiohttp.ClientSession.
        
        Returns:
            A configured aiohttp.ClientSession instance
        """
        if self._async_session is None or self._async_session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            cookies = self._initial_cookies if self._initial_cookies else None
            
            # Build headers with authentication
            default_headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
            auth_headers = self._build_headers()
            default_headers.update(auth_headers)
            
            # Handle basic auth for async
            auth = None
            if self._auth:
                if isinstance(self._auth, tuple) and len(self._auth) == 2:
                    auth = BasicAuth(login=self._auth[0], password=self._auth[1])
                elif isinstance(self._auth, HTTPBasicAuth):
                    auth = BasicAuth(login=self._auth.username, password=self._auth.password)
                # Note: HTTPDigestAuth is not directly supported by aiohttp
                # Users should use custom headers for digest auth
            
            self._async_session = aiohttp.ClientSession(
                timeout=timeout,
                cookies=cookies,
                connector=aiohttp.TCPConnector(
                    ssl=self.verify_ssl,
                    limit=self.pool_size,
                    limit_per_host=self.pool_size
                ),
                headers=default_headers,
                auth=auth
            )
        
        return self._async_session
    
    def add_cookie(self, name: str, value: str, domain: Optional[str] = None) -> None:
        """
        Add a cookie to the session.
        
        Args:
            name: Cookie name
            value: Cookie value
            domain: Optional domain for the cookie
        """
        if self._sync_session:
            self._sync_session.cookies.set(name, value, domain=domain)
        
        # For async session, cookies are managed per request
        if name not in self._initial_cookies:
            self._initial_cookies[name] = value
    
    def add_header(self, name: str, value: str) -> None:
        """
        Add a custom header to the session.
        
        Args:
            name: Header name
            value: Header value
        """
        self._custom_headers[name] = value
        
        # Update existing sessions if they exist
        if self._sync_session:
            self._sync_session.headers[name] = value
        
        # Async session will be updated on next creation
        if self._async_session and not self._async_session.closed:
            # Note: aiohttp doesn't allow modifying headers after creation
            # We'll need to recreate the session
            logger.warning("Header added but async session already exists. Recreate session to apply.")
    
    def set_oauth_token(self, token: str) -> None:
        """
        Set or update the OAuth 2.0 bearer token.
        
        Args:
            token: OAuth bearer token
        """
        self._oauth_token = token
        
        # Update existing sessions
        if self._sync_session:
            self._sync_session.headers["Authorization"] = f"Bearer {token}"
        
        # Async session will be updated on next creation
        if self._async_session and not self._async_session.closed:
            logger.warning("OAuth token updated but async session already exists. Recreate session to apply.")
    
    def set_api_key(self, api_key: str, header_name: str = "X-API-Key") -> None:
        """
        Set or update the API key.
        
        Args:
            api_key: API key value
            header_name: Header name for the API key (default: "X-API-Key")
        """
        self._api_key = api_key
        self._api_key_header = header_name
        
        # Update existing sessions
        if self._sync_session:
            self._sync_session.headers[header_name] = api_key
        
        # Async session will be updated on next creation
        if self._async_session and not self._async_session.closed:
            logger.warning("API key updated but async session already exists. Recreate session to apply.")
    
    def get_cookies(self) -> Dict[str, str]:
        """
        Get all cookies from the session.
        
        Returns:
            Dictionary of cookie name-value pairs
        """
        if self._sync_session:
            return dict(self._sync_session.cookies)
        return self._initial_cookies.copy()
    
    def save_cookies(self, filepath: str, format: str = 'json') -> None:
        """
        Save current session cookies to file.
        
        Args:
            filepath: Path to save cookies
            format: Format ('json' or 'pickle')
        """
        from .cookie_persistence import save_cookies
        
        cookies = self.get_cookies()
        if cookies:
            save_cookies(cookies, filepath, format)
            logger.info(f"Saved {len(cookies)} cookies to {filepath}")
        else:
            logger.warning("No cookies to save")
    
    def load_cookies(self, filepath: str, format: str = 'auto') -> None:
        """
        Load cookies from file into session.
        
        Args:
            filepath: Path to load cookies from
            format: Format ('json', 'pickle', or 'auto')
        """
        from .cookie_persistence import load_cookies
        
        jar = load_cookies(filepath, format)
        cookies = jar.to_requests_cookies()
        
        # Update initial cookies
        self._initial_cookies.update(cookies)
        
        # Update existing sync session if it exists
        if self._sync_session:
            for name, value in cookies.items():
                self._sync_session.cookies.set(name, value)
        
        logger.info(f"Loaded {len(cookies)} cookies from {filepath}")
    
    def close_sync_session(self) -> None:
        """Close the synchronous session."""
        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None
    
    async def close_async_session(self) -> None:
        """Close the asynchronous session."""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
            self._async_session = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_sync_session()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_async_session()

