#!/usr/bin/env python3
"""
Tests for authentication utilities
"""

import pytest
import base64
from crawlit.utils.auth import (
    AuthConfig,
    AuthManager,
    create_basic_auth,
    create_bearer_auth,
    create_api_key_auth,
    create_custom_auth,
    create_digest_auth,
    get_auth_tuple
)


class TestAuthConfig:
    """Test AuthConfig dataclass"""
    
    def test_basic_auth_config(self):
        """Test basic auth configuration"""
        config = AuthConfig(
            auth_type='basic',
            username='testuser',
            password='testpass'
        )
        assert config.auth_type == 'basic'
        assert config.username == 'testuser'
        assert config.password == 'testpass'
    
    def test_bearer_auth_config(self):
        """Test bearer auth configuration"""
        config = AuthConfig(
            auth_type='bearer',
            token='my_token_123'
        )
        assert config.auth_type == 'bearer'
        assert config.token == 'my_token_123'
    
    def test_api_key_auth_config(self):
        """Test API key auth configuration"""
        config = AuthConfig(
            auth_type='api_key',
            api_key='api_key_123',
            api_key_name='X-API-Key',
            api_key_location='header'
        )
        assert config.auth_type == 'api_key'
        assert config.api_key == 'api_key_123'
        assert config.api_key_name == 'X-API-Key'
        assert config.api_key_location == 'header'
    
    def test_invalid_auth_type(self):
        """Test invalid auth type raises error"""
        with pytest.raises(ValueError, match="Invalid auth_type"):
            AuthConfig(auth_type='invalid_type')
    
    def test_basic_auth_missing_credentials(self):
        """Test basic auth without credentials raises error"""
        with pytest.raises(ValueError, match="requires username and password"):
            AuthConfig(auth_type='basic', username='user')
    
    def test_bearer_auth_missing_token(self):
        """Test bearer auth without token raises error"""
        with pytest.raises(ValueError, match="requires token"):
            AuthConfig(auth_type='bearer')
    
    def test_api_key_auth_missing_key(self):
        """Test API key auth without key raises error"""
        with pytest.raises(ValueError, match="requires api_key"):
            AuthConfig(auth_type='api_key')


class TestAuthManager:
    """Test AuthManager class"""
    
    def test_no_auth(self):
        """Test manager with no authentication"""
        manager = AuthManager()
        assert manager.config.auth_type == 'none'
        assert manager.get_auth_for_requests() is None
        assert manager.get_auth_object() is None
        
        headers = manager.add_auth_to_headers()
        assert 'Authorization' not in headers
    
    def test_basic_auth(self):
        """Test basic authentication"""
        config = AuthConfig(
            auth_type='basic',
            username='user',
            password='pass'
        )
        manager = AuthManager(config)
        
        # Test auth tuple
        auth_tuple = manager.get_auth_for_requests()
        assert auth_tuple == ('user', 'pass')
        
        # Test auth object
        auth_obj = manager.get_auth_object()
        assert auth_obj is not None
        
        # Test headers
        headers = manager.add_auth_to_headers()
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Basic ')
        
        # Verify the Base64 encoding
        encoded = headers['Authorization'].split(' ')[1]
        decoded = base64.b64decode(encoded).decode()
        assert decoded == 'user:pass'
    
    def test_bearer_auth(self):
        """Test bearer token authentication"""
        config = AuthConfig(
            auth_type='bearer',
            token='my_secret_token'
        )
        manager = AuthManager(config)
        
        headers = manager.add_auth_to_headers()
        assert headers['Authorization'] == 'Bearer my_secret_token'
    
    def test_api_key_header(self):
        """Test API key in header"""
        config = AuthConfig(
            auth_type='api_key',
            api_key='key123',
            api_key_name='X-API-Key',
            api_key_location='header'
        )
        manager = AuthManager(config)
        
        headers = manager.add_auth_to_headers()
        assert headers['X-API-Key'] == 'key123'
    
    def test_api_key_query(self):
        """Test API key in query parameters"""
        config = AuthConfig(
            auth_type='api_key',
            api_key='key123',
            api_key_name='api_key',
            api_key_location='query'
        )
        manager = AuthManager(config)
        
        params = manager.add_auth_to_params()
        assert params['api_key'] == 'key123'
    
    def test_custom_headers(self):
        """Test custom headers authentication"""
        config = AuthConfig(
            auth_type='custom',
            custom_headers={
                'X-Custom-Header': 'value1',
                'X-Another-Header': 'value2'
            }
        )
        manager = AuthManager(config)
        
        headers = manager.add_auth_to_headers()
        assert headers['X-Custom-Header'] == 'value1'
        assert headers['X-Another-Header'] == 'value2'
    
    def test_digest_auth(self):
        """Test digest authentication"""
        config = AuthConfig(
            auth_type='digest',
            username='user',
            password='pass'
        )
        manager = AuthManager(config)
        
        auth_obj = manager.get_auth_object()
        assert auth_obj is not None
    
    def test_update_config(self):
        """Test updating configuration"""
        manager = AuthManager()
        
        manager.update_config(auth_type='bearer', token='new_token')
        assert manager.config.auth_type == 'bearer'


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_create_basic_auth(self):
        """Test create_basic_auth function"""
        manager = create_basic_auth('user', 'pass')
        assert manager.config.auth_type == 'basic'
        assert manager.config.username == 'user'
        assert manager.config.password == 'pass'
    
    def test_create_bearer_auth(self):
        """Test create_bearer_auth function"""
        manager = create_bearer_auth('token123')
        assert manager.config.auth_type == 'bearer'
        assert manager.config.token == 'token123'
    
    def test_create_api_key_auth(self):
        """Test create_api_key_auth function"""
        manager = create_api_key_auth('key123', 'X-API-Key', 'header')
        assert manager.config.auth_type == 'api_key'
        assert manager.config.api_key == 'key123'
        assert manager.config.api_key_name == 'X-API-Key'
        assert manager.config.api_key_location == 'header'
    
    def test_create_custom_auth(self):
        """Test create_custom_auth function"""
        headers = {'X-Custom': 'value'}
        manager = create_custom_auth(headers)
        assert manager.config.auth_type == 'custom'
        assert manager.config.custom_headers == headers
    
    def test_create_digest_auth(self):
        """Test create_digest_auth function"""
        manager = create_digest_auth('user', 'pass')
        assert manager.config.auth_type == 'digest'
        assert manager.config.username == 'user'
    
    def test_get_auth_tuple(self):
        """Test get_auth_tuple function"""
        auth_tuple = get_auth_tuple('user', 'pass')
        assert auth_tuple == ('user', 'pass')


class TestAuthIntegration:
    """Test auth integration scenarios"""
    
    def test_add_auth_to_existing_headers(self):
        """Test adding auth to existing headers"""
        manager = create_bearer_auth('token123')
        
        existing_headers = {
            'User-Agent': 'MyApp/1.0',
            'Accept': 'application/json'
        }
        
        headers = manager.add_auth_to_headers(existing_headers)
        
        # Should have both existing and auth headers
        assert headers['User-Agent'] == 'MyApp/1.0'
        assert headers['Accept'] == 'application/json'
        assert headers['Authorization'] == 'Bearer token123'
    
    def test_add_api_key_to_existing_params(self):
        """Test adding API key to existing params"""
        manager = create_api_key_auth('key123', 'api_key', 'query')
        
        existing_params = {
            'page': '1',
            'limit': '10'
        }
        
        params = manager.add_auth_to_params(existing_params)
        
        # Should have both existing and auth params
        assert params['page'] == '1'
        assert params['limit'] == '10'
        assert params['api_key'] == 'key123'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])




