#!/usr/bin/env python3
"""
auth.py - Authentication utilities for web crawling

Provides authentication helpers for various authentication schemes:
- Basic Authentication
- Digest Authentication
- Bearer Token (OAuth/JWT)
- API Key (header/query parameter)
- Custom Headers
"""

import logging
import base64
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """
    Configuration for authentication.
    
    Supports multiple authentication methods:
    - Basic: username + password
    - Digest: username + password
    - Bearer: token
    - API Key: key + location (header/query)
    - Custom: custom headers
    """
    auth_type: str  # 'basic', 'digest', 'bearer', 'api_key', 'custom', 'none'
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    api_key_name: str = 'X-API-Key'
    api_key_location: str = 'header'  # 'header' or 'query'
    custom_headers: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """Validate configuration"""
        valid_types = ['basic', 'digest', 'bearer', 'api_key', 'custom', 'none']
        if self.auth_type not in valid_types:
            raise ValueError(f"Invalid auth_type: {self.auth_type}. Must be one of {valid_types}")
        
        # Validate required fields
        if self.auth_type in ['basic', 'digest']:
            if not self.username or not self.password:
                raise ValueError(f"{self.auth_type} auth requires username and password")
        
        elif self.auth_type == 'bearer':
            if not self.token:
                raise ValueError("Bearer auth requires token")
        
        elif self.auth_type == 'api_key':
            if not self.api_key:
                raise ValueError("API key auth requires api_key")
            if self.api_key_location not in ['header', 'query']:
                raise ValueError("api_key_location must be 'header' or 'query'")
        
        elif self.auth_type == 'custom':
            if not self.custom_headers:
                raise ValueError("Custom auth requires custom_headers")


class AuthManager:
    """
    Manages authentication for web requests.
    
    Provides methods to add authentication to requests based on the configured auth type.
    """
    
    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialize AuthManager.
        
        Args:
            config: AuthConfig instance or None for no authentication
        """
        self.config = config or AuthConfig(auth_type='none')
        logger.debug(f"AuthManager initialized with auth_type: {self.config.auth_type}")
    
    def get_auth_for_requests(self) -> Optional[Tuple[str, str]]:
        """
        Get authentication tuple for requests library.
        
        Returns:
            Tuple of (username, password) for Basic/Digest auth, or None
        """
        if self.config.auth_type in ['basic', 'digest']:
            return (self.config.username, self.config.password)
        return None
    
    def get_auth_object(self) -> Optional[Any]:
        """
        Get authentication object for requests library.
        
        Returns:
            HTTPBasicAuth, HTTPDigestAuth, or None
        """
        if self.config.auth_type == 'basic':
            return HTTPBasicAuth(self.config.username, self.config.password)
        elif self.config.auth_type == 'digest':
            return HTTPDigestAuth(self.config.username, self.config.password)
        return None
    
    def add_auth_to_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Add authentication to request headers.
        
        Args:
            headers: Existing headers dictionary or None
            
        Returns:
            Headers dictionary with authentication added
        """
        headers = headers or {}
        
        if self.config.auth_type == 'bearer':
            # Add Bearer token
            headers['Authorization'] = f'Bearer {self.config.token}'
            logger.debug("Added Bearer token to headers")
        
        elif self.config.auth_type == 'api_key' and self.config.api_key_location == 'header':
            # Add API key to header
            headers[self.config.api_key_name] = self.config.api_key
            logger.debug(f"Added API key to header: {self.config.api_key_name}")
        
        elif self.config.auth_type == 'custom':
            # Add custom headers
            if self.config.custom_headers:
                headers.update(self.config.custom_headers)
                logger.debug(f"Added {len(self.config.custom_headers)} custom headers")
        
        elif self.config.auth_type == 'basic':
            # Manual Basic auth header (alternative to using auth parameter)
            credentials = f"{self.config.username}:{self.config.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f'Basic {encoded}'
            logger.debug("Added Basic auth to headers")
        
        return headers
    
    def add_auth_to_params(self, params: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Add authentication to query parameters.
        
        Args:
            params: Existing parameters dictionary or None
            
        Returns:
            Parameters dictionary with authentication added
        """
        params = params or {}
        
        if self.config.auth_type == 'api_key' and self.config.api_key_location == 'query':
            # Add API key to query parameters
            params[self.config.api_key_name] = self.config.api_key
            logger.debug(f"Added API key to query params: {self.config.api_key_name}")
        
        return params
    
    def update_config(self, **kwargs):
        """
        Update authentication configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"Updated auth config: {key}")
            else:
                logger.warning(f"Unknown auth config parameter: {key}")


# Convenience functions

def create_basic_auth(username: str, password: str) -> AuthManager:
    """
    Create AuthManager with Basic authentication.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        AuthManager configured for Basic auth
    """
    config = AuthConfig(
        auth_type='basic',
        username=username,
        password=password
    )
    return AuthManager(config)


def create_bearer_auth(token: str) -> AuthManager:
    """
    Create AuthManager with Bearer token authentication.
    
    Args:
        token: Bearer token (OAuth/JWT)
        
    Returns:
        AuthManager configured for Bearer auth
    """
    config = AuthConfig(
        auth_type='bearer',
        token=token
    )
    return AuthManager(config)


def create_api_key_auth(api_key: str, key_name: str = 'X-API-Key', 
                        location: str = 'header') -> AuthManager:
    """
    Create AuthManager with API key authentication.
    
    Args:
        api_key: API key value
        key_name: Name of the API key parameter/header
        location: 'header' or 'query'
        
    Returns:
        AuthManager configured for API key auth
    """
    config = AuthConfig(
        auth_type='api_key',
        api_key=api_key,
        api_key_name=key_name,
        api_key_location=location
    )
    return AuthManager(config)


def create_custom_auth(headers: Dict[str, str]) -> AuthManager:
    """
    Create AuthManager with custom headers.
    
    Args:
        headers: Dictionary of custom headers
        
    Returns:
        AuthManager configured for custom auth
    """
    config = AuthConfig(
        auth_type='custom',
        custom_headers=headers
    )
    return AuthManager(config)


def create_digest_auth(username: str, password: str) -> AuthManager:
    """
    Create AuthManager with Digest authentication.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        AuthManager configured for Digest auth
    """
    config = AuthConfig(
        auth_type='digest',
        username=username,
        password=password
    )
    return AuthManager(config)


# Legacy support - simple auth tuple
def get_auth_tuple(username: str, password: str) -> Tuple[str, str]:
    """
    Get simple (username, password) tuple for requests.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        Tuple of (username, password)
    """
    return (username, password)

