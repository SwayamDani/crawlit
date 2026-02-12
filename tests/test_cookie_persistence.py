#!/usr/bin/env python3
"""
Tests for cookie persistence functionality
"""

import pytest
import json
import pickle
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from crawlit.utils.cookie_persistence import CookieJar, save_cookies, load_cookies


class TestCookieJar:
    """Tests for CookieJar class."""
    
    def test_initialization(self):
        """Test cookie jar initialization."""
        jar = CookieJar()
        assert len(jar) == 0
        
        jar_with_cookies = CookieJar({'session': 'abc123'})
        assert len(jar_with_cookies) == 1
    
    def test_set_and_get_cookie(self):
        """Test setting and getting cookies."""
        jar = CookieJar()
        
        jar.set_cookie(
            'session_id',
            'xyz789',
            domain='example.com',
            path='/',
            secure=True
        )
        
        cookie = jar.get_cookie('session_id')
        assert cookie is not None
        assert cookie['value'] == 'xyz789'
        assert cookie['domain'] == 'example.com'
        assert cookie['secure'] is True
    
    def test_delete_cookie(self):
        """Test deleting cookies."""
        jar = CookieJar({'test': 'value'})
        
        assert jar.get_cookie('test') is not None
        
        jar.delete_cookie('test')
        assert jar.get_cookie('test') is None
    
    def test_clear_all_cookies(self):
        """Test clearing all cookies."""
        jar = CookieJar({
            'cookie1': 'value1',
            'cookie2': 'value2'
        })
        
        assert len(jar) == 2
        
        jar.clear()
        assert len(jar) == 0
    
    def test_filter_by_domain(self):
        """Test filtering cookies by domain."""
        jar = CookieJar()
        
        jar.set_cookie('cookie1', 'value1', domain='example.com')
        jar.set_cookie('cookie2', 'value2', domain='test.com')
        jar.set_cookie('cookie3', 'value3', domain='sub.example.com')
        
        # Filter for example.com domain
        filtered = jar.filter_by_domain('example.com')
        
        # Should include example.com and sub.example.com
        assert 'cookie1' in filtered
        assert 'cookie3' in filtered
        assert 'cookie2' not in filtered
    
    def test_remove_expired_cookies(self):
        """Test removing expired cookies."""
        jar = CookieJar()
        
        # Add expired cookie
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        jar.set_cookie('expired', 'value', expires=past_time)
        
        # Add valid cookie
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        jar.set_cookie('valid', 'value', expires=future_time)
        
        # Add cookie without expiration
        jar.set_cookie('no_expiry', 'value')
        
        assert len(jar) == 3
        
        removed_count = jar.remove_expired()
        
        assert removed_count == 1
        assert len(jar) == 2
        assert jar.get_cookie('expired') is None
        assert jar.get_cookie('valid') is not None
    
    def test_save_and_load_json(self):
        """Test saving and loading cookies as JSON."""
        jar = CookieJar()
        jar.set_cookie('session', 'abc123', domain='example.com')
        jar.set_cookie('user', 'john', domain='example.com', secure=True)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            # Save
            jar.save_json(filepath)
            
            # Load
            loaded_jar = CookieJar.load_json(filepath)
            
            assert len(loaded_jar) == 2
            assert loaded_jar.get_cookie('session')['value'] == 'abc123'
            assert loaded_jar.get_cookie('user')['secure'] is True
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_save_and_load_pickle(self):
        """Test saving and loading cookies as pickle."""
        jar = CookieJar()
        jar.set_cookie('data', 'sensitive', domain='secure.com', httponly=True)
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
            filepath = f.name
        
        try:
            # Save
            jar.save_pickle(filepath)
            
            # Load
            loaded_jar = CookieJar.load_pickle(filepath)
            
            assert len(loaded_jar) == 1
            cookie = loaded_jar.get_cookie('data')
            assert cookie['value'] == 'sensitive'
            assert cookie['httponly'] is True
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        jar = CookieJar.load_json('/nonexistent/file.json')
        assert len(jar) == 0  # Should return empty jar
    
    def test_to_requests_cookies(self):
        """Test converting to requests-compatible format."""
        jar = CookieJar()
        jar.set_cookie('cookie1', 'value1')
        jar.set_cookie('cookie2', 'value2')
        
        requests_cookies = jar.to_requests_cookies()
        
        assert isinstance(requests_cookies, dict)
        assert requests_cookies['cookie1'] == 'value1'
        assert requests_cookies['cookie2'] == 'value2'
    
    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        jar = CookieJar()
        jar.set_cookie('test', 'value', domain='example.com')
        
        # Convert to dict
        data = jar.to_dict()
        
        assert 'cookies' in data
        assert 'saved_at' in data
        
        # Recreate from dict
        new_jar = CookieJar.from_dict(data)
        
        assert len(new_jar) == 1
        assert new_jar.get_cookie('test')['value'] == 'value'


class TestCookiePersistenceHelpers:
    """Tests for helper functions."""
    
    def test_save_cookies_from_dict(self):
        """Test saving cookies from dictionary."""
        cookies = {'session': 'abc', 'user': 'john'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            save_cookies(cookies, filepath, format='json')
            
            # Load and verify
            jar = load_cookies(filepath)
            assert len(jar) == 2
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_save_cookies_from_jar(self):
        """Test saving CookieJar directly."""
        jar = CookieJar({'test': 'value'})
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            save_cookies(jar, filepath, format='json')
            
            # Load and verify
            loaded_jar = load_cookies(filepath)
            assert len(loaded_jar) == 1
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_load_cookies_auto_format(self):
        """Test loading cookies with auto format detection."""
        jar = CookieJar({'test': 'value'})
        
        # Test JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = f.name
        
        try:
            jar.save_json(json_path)
            loaded = load_cookies(json_path, format='auto')
            assert len(loaded) == 1
        finally:
            Path(json_path).unlink(missing_ok=True)
        
        # Test Pickle
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
            pkl_path = f.name
        
        try:
            jar.save_pickle(pkl_path)
            loaded = load_cookies(pkl_path, format='auto')
            assert len(loaded) == 1
        finally:
            Path(pkl_path).unlink(missing_ok=True)
    
    def test_invalid_format(self):
        """Test handling of invalid format."""
        with pytest.raises(ValueError):
            save_cookies({'test': 'value'}, 'test.txt', format='invalid')


class TestCookieJarEdgeCases:
    """Edge case tests for cookie jar."""
    
    def test_empty_cookie_jar_operations(self):
        """Test operations on empty jar."""
        jar = CookieJar()
        
        assert jar.get_cookie('nonexistent') is None
        jar.delete_cookie('nonexistent')  # Should not raise error
        
        filtered = jar.filter_by_domain('example.com')
        assert len(filtered) == 0
        
        removed = jar.remove_expired()
        assert removed == 0
    
    def test_cookie_with_special_characters(self):
        """Test cookies with special characters in values."""
        jar = CookieJar()
        
        special_value = 'value with spaces & special=chars'
        jar.set_cookie('special', special_value)
        
        cookie = jar.get_cookie('special')
        assert cookie['value'] == special_value
    
    def test_large_number_of_cookies(self):
        """Test jar with many cookies."""
        jar = CookieJar()
        
        # Add 1000 cookies
        for i in range(1000):
            jar.set_cookie(f'cookie_{i}', f'value_{i}')
        
        assert len(jar) == 1000
        
        # Verify retrieval
        cookie = jar.get_cookie('cookie_500')
        assert cookie['value'] == 'value_500'
    
    def test_cookie_without_optional_fields(self):
        """Test cookies with minimal information."""
        jar = CookieJar()
        
        jar.set_cookie('minimal', 'value')
        
        cookie = jar.get_cookie('minimal')
        assert cookie['value'] == 'value'
        assert 'domain' in cookie
        assert 'path' in cookie
    
    def test_repr(self):
        """Test string representation."""
        jar = CookieJar()
        jar.set_cookie('test1', 'value1')
        jar.set_cookie('test2', 'value2')
        
        repr_str = repr(jar)
        assert 'CookieJar' in repr_str
        assert '2 cookies' in repr_str

