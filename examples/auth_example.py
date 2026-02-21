#!/usr/bin/env python3
"""
Authentication Examples for crawlit

Demonstrates various authentication methods:
- Basic Auth
- Bearer Token (OAuth/JWT)
- API Key (header/query)
- Custom Headers
- Digest Auth
"""

from crawlit import (
    Crawler,
    create_basic_auth,
    create_bearer_auth,
    create_api_key_auth,
    create_custom_auth,
    create_digest_auth,
    AuthManager,
    AuthConfig
)


def example_basic_auth():
    """Example: Basic Authentication"""
    print("\n=== Basic Authentication ===")
    
    # Create auth manager with Basic auth
    auth = create_basic_auth('username', 'password')
    
    # Add auth to headers
    headers = {'User-Agent': 'crawlit/2.0'}
    headers = auth.add_auth_to_headers(headers)
    
    print(f"Headers: {headers}")
    
    # Use with Crawler (manual)
    # Note: In actual usage, you'd integrate this into the fetcher
    print("Auth tuple:", auth.get_auth_for_requests())


def example_bearer_token():
    """Example: Bearer Token Authentication (OAuth/JWT)"""
    print("\n=== Bearer Token Authentication ===")
    
    # Create auth manager with Bearer token
    auth = create_bearer_auth('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')
    
    # Add auth to headers
    headers = auth.add_auth_to_headers()
    print(f"Headers: {headers}")


def example_api_key_header():
    """Example: API Key in Header"""
    print("\n=== API Key Authentication (Header) ===")
    
    # Create auth manager with API key in header
    auth = create_api_key_auth(
        api_key='your_api_key_here',
        key_name='X-API-Key',
        location='header'
    )
    
    # Add auth to headers
    headers = auth.add_auth_to_headers()
    print(f"Headers: {headers}")


def example_api_key_query():
    """Example: API Key in Query Parameters"""
    print("\n=== API Key Authentication (Query) ===")
    
    # Create auth manager with API key in query params
    auth = create_api_key_auth(
        api_key='your_api_key_here',
        key_name='api_key',
        location='query'
    )
    
    # Add auth to query parameters
    params = {'page': '1', 'limit': '10'}
    params = auth.add_auth_to_params(params)
    print(f"Query params: {params}")


def example_custom_headers():
    """Example: Custom Headers Authentication"""
    print("\n=== Custom Headers Authentication ===")
    
    # Create auth manager with custom headers
    custom_headers = {
        'X-Custom-Auth': 'custom_token',
        'X-Request-ID': 'req-12345',
        'X-Client-Version': '2.0'
    }
    auth = create_custom_auth(custom_headers)
    
    # Add auth to headers
    headers = auth.add_auth_to_headers()
    print(f"Headers: {headers}")


def example_digest_auth():
    """Example: Digest Authentication"""
    print("\n=== Digest Authentication ===")
    
    # Create auth manager with Digest auth
    auth = create_digest_auth('username', 'password')
    
    # Get auth object for requests
    auth_obj = auth.get_auth_object()
    print(f"Auth object: {auth_obj}")
    print(f"Type: {type(auth_obj).__name__}")


def example_manual_config():
    """Example: Manual AuthConfig"""
    print("\n=== Manual AuthConfig ===")
    
    # Create custom configuration
    config = AuthConfig(
        auth_type='api_key',
        api_key='my_secret_key',
        api_key_name='Authorization',
        api_key_location='header'
    )
    
    auth = AuthManager(config)
    headers = auth.add_auth_to_headers()
    print(f"Headers: {headers}")


def example_update_config():
    """Example: Update Auth Configuration"""
    print("\n=== Update Configuration ===")
    
    # Start with no auth
    auth = AuthManager()
    print(f"Initial: {auth.config.auth_type}")
    
    # Update to Bearer token
    auth.update_config(auth_type='bearer', token='new_token_123')
    headers = auth.add_auth_to_headers()
    print(f"Updated: {headers}")


def example_integration_scenario():
    """Example: Real-world Integration Scenario"""
    print("\n=== Integration Scenario ===")
    print("Scenario: Accessing a protected API with Bearer token")
    
    # Create auth
    auth = create_bearer_auth('your_jwt_token_here')
    
    # Prepare request
    base_headers = {
        'User-Agent': 'MyApp/1.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Add authentication
    headers = auth.add_auth_to_headers(base_headers)
    
    print("Final headers:")
    for key, value in headers.items():
        if key == 'Authorization':
            # Mask token for display
            print(f"  {key}: Bearer ****")
        else:
            print(f"  {key}: {value}")
    
    print("\nThese headers would be used with requests:")
    print("  response = requests.get(url, headers=headers)")


if __name__ == '__main__':
    print("=" * 60)
    print("Authentication Examples for crawlit")
    print("=" * 60)
    
    example_basic_auth()
    example_bearer_token()
    example_api_key_header()
    example_api_key_query()
    example_custom_headers()
    example_digest_auth()
    example_manual_config()
    example_update_config()
    example_integration_scenario()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)



