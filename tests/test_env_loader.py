#!/usr/bin/env python3
"""
Tests for environment variable and configuration loader
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from crawlit.utils.env_loader import (
    EnvLoader,
    ConfigLoader,
    load_env,
    getenv
)


class TestEnvLoader:
    """Test EnvLoader class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_vars = {}
        # Save existing env vars
        for key in ['TEST_VAR', 'TEST_INT', 'TEST_BOOL', 'TEST_LIST']:
            if key in os.environ:
                self.test_vars[key] = os.environ[key]
    
    def teardown_method(self):
        """Cleanup test environment"""
        # Restore env vars
        for key in ['TEST_VAR', 'TEST_INT', 'TEST_BOOL', 'TEST_LIST']:
            if key in self.test_vars:
                os.environ[key] = self.test_vars[key]
            elif key in os.environ:
                del os.environ[key]
    
    def test_basic_get(self):
        """Test basic get operation"""
        os.environ['TEST_VAR'] = 'test_value'
        
        loader = EnvLoader(auto_load=False)
        value = loader.get('TEST_VAR')
        
        assert value == 'test_value'
    
    def test_get_with_default(self):
        """Test get with default value"""
        loader = EnvLoader(auto_load=False)
        value = loader.get('NONEXISTENT_VAR', default='default_value')
        
        assert value == 'default_value'
    
    def test_get_required_missing(self):
        """Test get with required=True raises error"""
        loader = EnvLoader(auto_load=False)
        
        with pytest.raises(ValueError, match="Required environment variable"):
            loader.get('NONEXISTENT_VAR', required=True)
    
    def test_get_int(self):
        """Test integer conversion"""
        os.environ['TEST_INT'] = '42'
        
        loader = EnvLoader(auto_load=False)
        value = loader.get_int('TEST_INT')
        
        assert value == 42
        assert isinstance(value, int)
    
    def test_get_float(self):
        """Test float conversion"""
        os.environ['TEST_FLOAT'] = '3.14'
        
        loader = EnvLoader(auto_load=False)
        value = loader.get_float('TEST_FLOAT')
        
        assert value == 3.14
        assert isinstance(value, float)
    
    def test_get_bool_true_values(self):
        """Test boolean true values"""
        true_values = ['true', 'True', 'TRUE', 'yes', 'Yes', '1', 'on', 'enabled']
        loader = EnvLoader(auto_load=False)
        
        for val in true_values:
            os.environ['TEST_BOOL'] = val
            assert loader.get_bool('TEST_BOOL') is True
    
    def test_get_bool_false_values(self):
        """Test boolean false values"""
        false_values = ['false', 'False', 'FALSE', 'no', 'No', '0', 'off', 'disabled', '']
        loader = EnvLoader(auto_load=False)
        
        for val in false_values:
            os.environ['TEST_BOOL'] = val
            assert loader.get_bool('TEST_BOOL') is False
    
    def test_get_list(self):
        """Test list conversion"""
        os.environ['TEST_LIST'] = 'item1,item2,item3'
        
        loader = EnvLoader(auto_load=False)
        value = loader.get_list('TEST_LIST')
        
        assert value == ['item1', 'item2', 'item3']
        assert isinstance(value, list)
    
    def test_get_list_with_spaces(self):
        """Test list with spaces"""
        os.environ['TEST_LIST'] = 'item1, item2 , item3'
        
        loader = EnvLoader(auto_load=False)
        value = loader.get_list('TEST_LIST')
        
        assert value == ['item1', 'item2', 'item3']
    
    def test_load_env_file(self):
        """Test loading from .env file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('# Comment line\n')
            f.write('VAR1=value1\n')
            f.write('VAR2=value2\n')
            f.write('VAR3="quoted value"\n')
            f.write("VAR4='single quoted'\n")
            f.write('EMPTY_VAR=\n')
            f.name_path = f.name
        
        try:
            loader = EnvLoader(auto_load=False)
            count = loader.load_env_file(f.name_path)
            
            assert count == 5  # 5 valid lines (EMPTY_VAR counts)
            assert loader.get('VAR1') == 'value1'
            assert loader.get('VAR2') == 'value2'
            assert loader.get('VAR3') == 'quoted value'
            assert loader.get('VAR4') == 'single quoted'
            assert loader.get('EMPTY_VAR') == ''
        finally:
            os.unlink(f.name_path)
    
    def test_set_and_unset(self):
        """Test set and unset operations"""
        loader = EnvLoader(auto_load=False)
        
        # Set
        loader.set('NEW_VAR', 'new_value')
        assert loader.get('NEW_VAR') == 'new_value'
        assert os.environ['NEW_VAR'] == 'new_value'
        
        # Unset
        loader.unset('NEW_VAR')
        assert 'NEW_VAR' not in os.environ
    
    def test_get_all(self):
        """Test get_all operation"""
        os.environ['PREFIX_VAR1'] = 'value1'
        os.environ['PREFIX_VAR2'] = 'value2'
        os.environ['OTHER_VAR'] = 'other'
        
        loader = EnvLoader(auto_load=False, prefix='PREFIX_')
        all_vars = loader.get_all()
        
        assert 'PREFIX_VAR1' in all_vars
        assert 'PREFIX_VAR2' in all_vars
        
        # Cleanup
        del os.environ['PREFIX_VAR1']
        del os.environ['PREFIX_VAR2']
        del os.environ['OTHER_VAR']
    
    def test_clear(self):
        """Test clear operation"""
        loader = EnvLoader(auto_load=False)
        
        loader.set('TEMP_VAR1', 'value1')
        loader.set('TEMP_VAR2', 'value2')
        
        loader.clear()
        
        assert 'TEMP_VAR1' not in os.environ
        assert 'TEMP_VAR2' not in os.environ


class TestConfigLoader:
    """Test ConfigLoader class"""
    
    def test_load_json_config(self):
        """Test loading JSON configuration file"""
        config_data = {
            'app_name': 'TestApp',
            'debug': True,
            'port': 8080,
            'features': ['feature1', 'feature2']
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.name_path = f.name
        
        try:
            loader = ConfigLoader(auto_load=False)
            loaded = loader.load_config_file(f.name_path)
            
            assert loaded['app_name'] == 'TestApp'
            assert loaded['debug'] is True
            assert loaded['port'] == 8080
        finally:
            os.unlink(f.name_path)
    
    def test_config_priority(self):
        """Test configuration priority (env > config file)"""
        # Create config file
        config_data = {
            'CONFIG_VAR1': 'from_config',
            'CONFIG_VAR2': 'from_config'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            # Set env var (should override config)
            os.environ['CONFIG_VAR1'] = 'from_env'
            
            loader = ConfigLoader(config_file=config_file, auto_load=True)
            
            # CONFIG_VAR1 should come from env
            assert loader.get('CONFIG_VAR1') == 'from_env'
            
            # CONFIG_VAR2 should come from config
            assert loader.get('CONFIG_VAR2') == 'from_config'
        finally:
            os.unlink(config_file)
            if 'CONFIG_VAR1' in os.environ:
                del os.environ['CONFIG_VAR1']
    
    def test_get_section(self):
        """Test getting configuration section"""
        config_data = {
            'database': {
                'host': 'localhost',
                'port': 5432
            },
            'cache': {
                'enabled': True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            loader = ConfigLoader(config_file=config_file, auto_load=True)
            
            db_config = loader.get_section('database')
            assert db_config['host'] == 'localhost'
            assert db_config['port'] == 5432
            
            cache_config = loader.get_section('cache')
            assert cache_config['enabled'] is True
        finally:
            os.unlink(config_file)
    
    def test_to_dict(self):
        """Test getting all configuration as dict"""
        config_data = {'config_var': 'value'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            loader = ConfigLoader(config_file=config_file, auto_load=True)
            loader.set('env_var', 'env_value')
            
            all_config = loader.to_dict()
            
            assert 'config_var' in all_config
            assert 'env_var' in all_config
        finally:
            os.unlink(config_file)


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_load_env_function(self):
        """Test load_env convenience function"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('CONV_VAR=conv_value\n')
            env_file = f.name
        
        try:
            count = load_env(env_file)
            assert count == 1
            assert os.environ.get('CONV_VAR') == 'conv_value'
        finally:
            os.unlink(env_file)
            if 'CONV_VAR' in os.environ:
                del os.environ['CONV_VAR']
    
    def test_getenv_function(self):
        """Test getenv convenience function"""
        os.environ['GETENV_TEST'] = '42'
        
        value = getenv('GETENV_TEST', cast=int)
        assert value == 42
        assert isinstance(value, int)
        
        if 'GETENV_TEST' in os.environ:
            del os.environ['GETENV_TEST']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

