#!/usr/bin/env python3
"""
cookie_persistence.py - Cookie jar persistence for session continuity

Allows saving and loading cookies across crawl sessions for authenticated crawling.
"""

import logging
import json
import pickle
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import http.cookiejar as cookiejar

logger = logging.getLogger(__name__)


class CookieJar:
    """
    Cookie jar with persistence support.
    
    Supports saving/loading cookies in JSON or pickle format.
    """
    
    def __init__(self, cookies: Optional[Dict[str, str]] = None):
        """
        Initialize cookie jar.
        
        Args:
            cookies: Initial cookies as a dictionary
        """
        self.cookies = cookies or {}
    
    def set_cookie(self, name: str, value: str, domain: str = "", path: str = "/", 
                   expires: Optional[datetime] = None, secure: bool = False, 
                   httponly: bool = False) -> None:
        """
        Set a cookie with attributes.
        
        Args:
            name: Cookie name
            value: Cookie value
            domain: Cookie domain
            path: Cookie path
            expires: Expiration datetime
            secure: Secure flag
            httponly: HttpOnly flag
        """
        cookie_data = {
            'value': value,
            'domain': domain,
            'path': path,
            'secure': secure,
            'httponly': httponly
        }
        
        if expires:
            cookie_data['expires'] = expires.isoformat()
        
        self.cookies[name] = cookie_data
        logger.debug(f"Set cookie: {name} for domain {domain}")
    
    def get_cookie(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a cookie by name.
        
        Args:
            name: Cookie name
            
        Returns:
            Cookie data dictionary or None
        """
        return self.cookies.get(name)
    
    def delete_cookie(self, name: str) -> None:
        """
        Delete a cookie.
        
        Args:
            name: Cookie name
        """
        if name in self.cookies:
            del self.cookies[name]
            logger.debug(f"Deleted cookie: {name}")
    
    def clear(self) -> None:
        """Clear all cookies."""
        self.cookies.clear()
        logger.debug("Cleared all cookies")
    
    def filter_by_domain(self, domain: str) -> Dict[str, Any]:
        """
        Get cookies for a specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Dictionary of cookies for the domain
        """
        filtered = {}
        for name, cookie_data in self.cookies.items():
            if isinstance(cookie_data, dict):
                cookie_domain = cookie_data.get('domain', '')
                if domain.endswith(cookie_domain) or cookie_domain.endswith(domain):
                    filtered[name] = cookie_data
            else:
                # Simple string value (backward compatibility)
                filtered[name] = cookie_data
        return filtered
    
    def remove_expired(self) -> int:
        """
        Remove expired cookies.
        
        Returns:
            Number of cookies removed
        """
        now = datetime.now(timezone.utc)
        expired = []
        
        for name, cookie_data in self.cookies.items():
            if isinstance(cookie_data, dict) and 'expires' in cookie_data:
                try:
                    expires = datetime.fromisoformat(cookie_data['expires'])
                    if expires < now:
                        expired.append(name)
                except (ValueError, TypeError):
                    pass
        
        for name in expired:
            del self.cookies[name]
        
        if expired:
            logger.info(f"Removed {len(expired)} expired cookies")
        
        return len(expired)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert cookie jar to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'cookies': self.cookies,
            'saved_at': datetime.now(timezone.utc).isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CookieJar':
        """
        Create cookie jar from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            CookieJar instance
        """
        jar = cls(cookies=data.get('cookies', {}))
        return jar
    
    def save_json(self, filepath: str) -> None:
        """
        Save cookies to JSON file.
        
        Args:
            filepath: Path to save file
        """
        try:
            data = self.to_dict()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.cookies)} cookies to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save cookies to {filepath}: {e}")
            raise
    
    @classmethod
    def load_json(cls, filepath: str) -> 'CookieJar':
        """
        Load cookies from JSON file.
        
        Args:
            filepath: Path to load file
            
        Returns:
            CookieJar instance
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            jar = cls.from_dict(data)
            logger.info(f"Loaded {len(jar.cookies)} cookies from {filepath}")
            return jar
        except FileNotFoundError:
            logger.warning(f"Cookie file not found: {filepath}")
            return cls()
        except Exception as e:
            logger.error(f"Failed to load cookies from {filepath}: {e}")
            raise
    
    def save_pickle(self, filepath: str) -> None:
        """
        Save cookies to pickle file (more secure but not human-readable).
        
        Args:
            filepath: Path to save file
        """
        try:
            data = self.to_dict()
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"Saved {len(self.cookies)} cookies to {filepath} (pickle)")
        except Exception as e:
            logger.error(f"Failed to save cookies to {filepath}: {e}")
            raise
    
    @classmethod
    def load_pickle(cls, filepath: str) -> 'CookieJar':
        """
        Load cookies from pickle file.
        
        Args:
            filepath: Path to load file
            
        Returns:
            CookieJar instance
        """
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            jar = cls.from_dict(data)
            logger.info(f"Loaded {len(jar.cookies)} cookies from {filepath} (pickle)")
            return jar
        except FileNotFoundError:
            logger.warning(f"Cookie file not found: {filepath}")
            return cls()
        except Exception as e:
            logger.error(f"Failed to load cookies from {filepath}: {e}")
            raise
    
    def to_requests_cookies(self) -> Dict[str, str]:
        """
        Convert to simple dictionary for requests library.
        
        Returns:
            Dictionary of cookie name: value pairs
        """
        simple_cookies = {}
        for name, cookie_data in self.cookies.items():
            if isinstance(cookie_data, dict):
                simple_cookies[name] = cookie_data.get('value', '')
            else:
                # Simple string value
                simple_cookies[name] = cookie_data
        return simple_cookies
    
    def from_requests_cookies(self, requests_cookies: Any) -> None:
        """
        Import cookies from requests.cookies.RequestsCookieJar.
        
        Args:
            requests_cookies: RequestsCookieJar from requests library
        """
        for cookie in requests_cookies:
            expires = None
            if cookie.expires:
                try:
                    expires = datetime.fromtimestamp(cookie.expires, tz=timezone.utc)
                except Exception:
                    pass
            
            self.set_cookie(
                name=cookie.name,
                value=cookie.value,
                domain=cookie.domain or "",
                path=cookie.path or "/",
                expires=expires,
                secure=cookie.secure,
                httponly=cookie.has_nonstandard_attr('HttpOnly')
            )
        
        logger.debug(f"Imported {len(requests_cookies)} cookies from requests")
    
    def __len__(self) -> int:
        """Get number of cookies."""
        return len(self.cookies)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"CookieJar({len(self.cookies)} cookies)"


def save_cookies(cookies: Any, filepath: str, format: str = 'json') -> None:
    """
    Save cookies to file.
    
    Args:
        cookies: Cookies (dict, RequestsCookieJar, or CookieJar)
        filepath: Path to save file
        format: Format ('json' or 'pickle')
    """
    jar = CookieJar()
    
    if isinstance(cookies, CookieJar):
        jar = cookies
    elif isinstance(cookies, dict):
        jar.cookies = cookies
    else:
        # Try to import from requests cookies
        try:
            jar.from_requests_cookies(cookies)
        except Exception as e:
            logger.error(f"Failed to convert cookies: {e}")
            raise
    
    if format == 'json':
        jar.save_json(filepath)
    elif format == 'pickle':
        jar.save_pickle(filepath)
    else:
        raise ValueError(f"Unknown format: {format}")


def load_cookies(filepath: str, format: str = 'auto') -> CookieJar:
    """
    Load cookies from file.
    
    Args:
        filepath: Path to load file
        format: Format ('json', 'pickle', or 'auto' to detect)
        
    Returns:
        CookieJar instance
    """
    if format == 'auto':
        # Detect format from extension
        path = Path(filepath)
        if path.suffix in ['.pkl', '.pickle']:
            format = 'pickle'
        else:
            format = 'json'
    
    if format == 'json':
        return CookieJar.load_json(filepath)
    elif format == 'pickle':
        return CookieJar.load_pickle(filepath)
    else:
        raise ValueError(f"Unknown format: {format}")

