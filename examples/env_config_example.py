#!/usr/bin/env python3
"""
Environment and Configuration Examples for crawlit

Demonstrates:
- Loading .env files
- Getting environment variables with type conversion
- Configuration file loading
- Configuration priority
"""

import os
import json
import tempfile
from crawlit import EnvLoader, ConfigLoader, load_env, getenv


def example_basic_env_loading():
    """Example: Basic Environment Variable Loading"""
    print("\n=== Basic Environment Variable Loading ===")
    
    # Set some environment variables
    os.environ['APP_NAME'] = 'MyApp'
    os.environ['APP_DEBUG'] = 'true'
    os.environ['APP_PORT'] = '8080'
    
    # Create loader
    loader = EnvLoader(auto_load=False)
    
    # Get values
    app_name = loader.get('APP_NAME')
    is_debug = loader.get_bool('APP_DEBUG')
    port = loader.get_int('APP_PORT')
    
    print(f"App Name: {app_name}")
    print(f"Debug Mode: {is_debug} (type: {type(is_debug).__name__})")
    print(f"Port: {port} (type: {type(port).__name__})")


def example_env_file_loading():
    """Example: Loading from .env File"""
    print("\n=== Loading from .env File ===")
    
    # Create a temporary .env file
    env_content = """
# Application Configuration
APP_NAME=MyAwesomeApp
APP_ENV=production
APP_DEBUG=false

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb

# API Keys
API_KEY=secret_key_12345
API_SECRET="secret with spaces"

# Features (comma-separated list)
ENABLED_FEATURES=feature1,feature2,feature3
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        env_file = f.name
    
    try:
        # Load the file
        loader = EnvLoader(auto_load=False)
        count = loader.load_env_file(env_file)
        print(f"Loaded {count} variables from .env file")
        
        # Access values
        print(f"APP_NAME: {loader.get('APP_NAME')}")
        print(f"APP_DEBUG: {loader.get_bool('APP_DEBUG')}")
        print(f"DB_PORT: {loader.get_int('DB_PORT')}")
        print(f"ENABLED_FEATURES: {loader.get_list('ENABLED_FEATURES')}")
    finally:
        os.unlink(env_file)


def example_type_conversion():
    """Example: Type Conversion"""
    print("\n=== Type Conversion ===")
    
    os.environ['INT_VAR'] = '42'
    os.environ['FLOAT_VAR'] = '3.14'
    os.environ['BOOL_VAR'] = 'yes'
    os.environ['LIST_VAR'] = 'apple,banana,cherry'
    
    loader = EnvLoader(auto_load=False)
    
    # Integer
    int_val = loader.get_int('INT_VAR')
    print(f"Integer: {int_val} (type: {type(int_val).__name__})")
    
    # Float
    float_val = loader.get_float('FLOAT_VAR')
    print(f"Float: {float_val} (type: {type(float_val).__name__})")
    
    # Boolean
    bool_val = loader.get_bool('BOOL_VAR')
    print(f"Boolean: {bool_val} (type: {type(bool_val).__name__})")
    
    # List
    list_val = loader.get_list('LIST_VAR')
    print(f"List: {list_val} (type: {type(list_val).__name__})")


def example_default_and_required():
    """Example: Default Values and Required Variables"""
    print("\n=== Default Values and Required Variables ===")
    
    loader = EnvLoader(auto_load=False)
    
    # With default value
    value = loader.get('NONEXISTENT_VAR', default='default_value')
    print(f"With default: {value}")
    
    # Required variable (will raise error)
    try:
        loader.get('REQUIRED_VAR', required=True)
    except ValueError as e:
        print(f"Required variable missing: {e}")


def example_config_file_loading():
    """Example: Loading from Configuration File"""
    print("\n=== Loading from Configuration File ===")
    
    # Create a temporary config file
    config_data = {
        'app': {
            'name': 'MyApp',
            'version': '1.0.0',
            'debug': False
        },
        'database': {
            'host': 'localhost',
            'port': 5432,
            'name': 'mydb'
        },
        'features': {
            'enable_caching': True,
            'enable_logging': True,
            'max_workers': 4
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_file = f.name
    
    try:
        # Load configuration
        loader = ConfigLoader(config_file=config_file, auto_load=True)
        
        # Access configuration sections
        app_config = loader.get_section('app')
        db_config = loader.get_section('database')
        
        print("App Config:")
        for key, value in app_config.items():
            print(f"  {key}: {value}")
        
        print("\nDatabase Config:")
        for key, value in db_config.items():
            print(f"  {key}: {value}")
        
        # Access specific values
        max_workers = loader.get('max_workers')
        print(f"\nMax Workers: {max_workers}")
    finally:
        os.unlink(config_file)


def example_configuration_priority():
    """Example: Configuration Priority (Env > Config File)"""
    print("\n=== Configuration Priority ===")
    
    # Create config file
    config_data = {
        'APP_MODE': 'production',
        'MAX_CONNECTIONS': 100
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_file = f.name
    
    try:
        # Override one value with environment variable
        os.environ['APP_MODE'] = 'development'
        
        loader = ConfigLoader(config_file=config_file, auto_load=True)
        
        # APP_MODE comes from environment (higher priority)
        app_mode = loader.get('APP_MODE')
        print(f"APP_MODE (from env): {app_mode}")
        
        # MAX_CONNECTIONS comes from config file
        max_conn = loader.get('MAX_CONNECTIONS')
        print(f"MAX_CONNECTIONS (from config): {max_conn}")
    finally:
        os.unlink(config_file)
        if 'APP_MODE' in os.environ:
            del os.environ['APP_MODE']


def example_prefix_filtering():
    """Example: Prefix Filtering"""
    print("\n=== Prefix Filtering ===")
    
    # Set environment variables with prefix
    os.environ['MYAPP_HOST'] = 'localhost'
    os.environ['MYAPP_PORT'] = '8080'
    os.environ['MYAPP_DEBUG'] = 'true'
    os.environ['OTHER_VAR'] = 'other'
    
    # Create loader with prefix
    loader = EnvLoader(auto_load=False, prefix='MYAPP_')
    
    # Get all variables with prefix
    myapp_vars = loader.get_all(prefix='MYAPP_')
    
    print("Variables with MYAPP_ prefix:")
    for key, value in myapp_vars.items():
        if key.startswith('MYAPP_'):
            print(f"  {key}: {value}")
    
    # Cleanup
    del os.environ['MYAPP_HOST']
    del os.environ['MYAPP_PORT']
    del os.environ['MYAPP_DEBUG']
    del os.environ['OTHER_VAR']


def example_convenience_functions():
    """Example: Convenience Functions"""
    print("\n=== Convenience Functions ===")
    
    # Create temp .env file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write('QUICK_VAR=quick_value\n')
        f.write('QUICK_INT=999\n')
        env_file = f.name
    
    try:
        # Use convenience function to load
        load_env(env_file)
        
        # Use convenience function to get
        value = getenv('QUICK_VAR')
        int_value = getenv('QUICK_INT', cast=int)
        
        print(f"QUICK_VAR: {value}")
        print(f"QUICK_INT: {int_value} (type: {type(int_value).__name__})")
    finally:
        os.unlink(env_file)
        if 'QUICK_VAR' in os.environ:
            del os.environ['QUICK_VAR']
        if 'QUICK_INT' in os.environ:
            del os.environ['QUICK_INT']


def example_real_world_scenario():
    """Example: Real-world Application Configuration"""
    print("\n=== Real-world Scenario ===")
    print("Scenario: Configuring a web crawler with env vars")
    
    # Simulate .env file
    os.environ['CRAWLIT_MAX_DEPTH'] = '5'
    os.environ['CRAWLIT_DELAY'] = '0.5'
    os.environ['CRAWLIT_USER_AGENT'] = 'MyCrawler/1.0'
    os.environ['CRAWLIT_RESPECT_ROBOTS'] = 'true'
    os.environ['CRAWLIT_PROXY'] = 'http://proxy.example.com:8080'
    
    # Load configuration
    loader = EnvLoader(auto_load=False, prefix='CRAWLIT_')
    
    # Extract configuration
    config = {
        'max_depth': loader.get_int('CRAWLIT_MAX_DEPTH', default=3),
        'delay': loader.get_float('CRAWLIT_DELAY', default=0.1),
        'user_agent': loader.get('CRAWLIT_USER_AGENT', default='crawlit/2.0'),
        'respect_robots': loader.get_bool('CRAWLIT_RESPECT_ROBOTS', default=True),
        'proxy': loader.get('CRAWLIT_PROXY', default=None)
    }
    
    print("Crawler Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value} ({type(value).__name__})")
    
    # Cleanup
    for key in list(os.environ.keys()):
        if key.startswith('CRAWLIT_'):
            del os.environ[key]


if __name__ == '__main__':
    print("=" * 60)
    print("Environment & Configuration Examples for crawlit")
    print("=" * 60)
    
    example_basic_env_loading()
    example_env_file_loading()
    example_type_conversion()
    example_default_and_required()
    example_config_file_loading()
    example_configuration_priority()
    example_prefix_filtering()
    example_convenience_functions()
    example_real_world_scenario()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)




