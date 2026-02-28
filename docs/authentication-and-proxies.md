# Authentication and Proxies in Crawlit

This comprehensive guide covers authentication methods and proxy management in crawlit, enabling you to crawl authenticated websites and use proxy networks effectively.

## Table of Contents

1. [Authentication Methods](#authentication-methods)
2. [Proxy Configuration and Rotation](#proxy-configuration-and-rotation)
3. [Session Management and Cookie Handling](#session-management-and-cookie-handling)
4. [CSRF Token Handling](#csrf-token-handling)
5. [Integration with Crawlers](#integration-with-crawlers)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Complete Examples](#complete-examples)

## Authentication Methods

Crawlit provides comprehensive authentication support through the `AuthManager` class, supporting multiple authentication schemes commonly used in modern web applications.

### Supported Authentication Types

#### 1. Basic Authentication

HTTP Basic Authentication using username and password.

```python
from crawlit.utils.auth import create_basic_auth, AuthManager, AuthConfig

# Method 1: Using convenience function
auth = create_basic_auth('username', 'password')

# Method 2: Using AuthConfig directly
config = AuthConfig(
    auth_type='basic',
    username='username',
    password='password'
)
auth = AuthManager(config)

# Add to request headers
headers = auth.add_auth_to_headers({'User-Agent': 'crawlit/1.0'})
# Headers now include: {'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='}

# Get auth object for requests library
auth_object = auth.get_auth_object()  # Returns HTTPBasicAuth instance
```

#### 2. Digest Authentication

HTTP Digest Authentication for enhanced security over Basic auth.

```python
from crawlit.utils.auth import create_digest_auth

auth = create_digest_auth('username', 'password')
auth_object = auth.get_auth_object()  # Returns HTTPDigestAuth instance
```

#### 3. Bearer Token Authentication (OAuth/JWT)

Modern token-based authentication using Bearer tokens.

```python
from crawlit.utils.auth import create_bearer_auth

# OAuth 2.0 token
oauth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
auth = create_bearer_auth(oauth_token)

headers = auth.add_auth_to_headers()
# Headers: {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'}
```

#### 4. API Key Authentication

API key authentication via headers or query parameters.

```python
from crawlit.utils.auth import create_api_key_auth

# API key in header (default: X-API-Key)
auth = create_api_key_auth('your-api-key-here')

# Custom header name
auth = create_api_key_auth('your-api-key', key_name='X-RapidAPI-Key', location='header')

# API key in query parameters
auth = create_api_key_auth('your-api-key', key_name='api_key', location='query')

# Add to request
headers = auth.add_auth_to_headers()  # For header-based auth
params = auth.add_auth_to_params()    # For query parameter auth
```

#### 5. Custom Headers Authentication

For custom authentication schemes or multiple headers.

```python
from crawlit.utils.auth import create_custom_auth

custom_headers = {
    'X-API-Key': 'your-api-key',
    'X-Client-ID': 'your-client-id',
    'X-Signature': 'calculated-signature'
}
auth = create_custom_auth(custom_headers)

headers = auth.add_auth_to_headers()
# Headers include all custom authentication headers
```

### Dynamic Authentication Updates

Authentication configurations can be updated dynamically during crawling:

```python
auth = create_bearer_auth('initial-token')

# Update token (e.g., after refresh)
auth.update_config(token='new-refreshed-token')

# Update multiple parameters
auth.update_config(
    auth_type='api_key',
    api_key='new-api-key',
    api_key_name='X-API-Token'
)
```

## Proxy Configuration and Rotation

Crawlit's proxy system provides robust proxy management with automatic rotation, health tracking, and failover capabilities.

### Proxy Types Supported

- **HTTP/HTTPS proxies**: `http://proxy.example.com:8080`
- **SOCKS5 proxies**: `socks5://proxy.example.com:1080`
- **SOCKS5 with DNS resolution**: `socks5h://proxy.example.com:1080`
- **Authenticated proxies**: `http://user:pass@proxy.example.com:8080`

### Single Proxy Usage

```python
from crawlit import Crawler

# Simple HTTP proxy
crawler = Crawler(
    'https://example.com',
    proxy='http://proxy.example.com:8080'
)

# Authenticated proxy
crawler = Crawler(
    'https://example.com',
    proxy='http://username:password@proxy.example.com:8080'
)

# SOCKS5 proxy
crawler = Crawler(
    'https://example.com',
    proxy='socks5://proxy.example.com:1080'
)
```

### Proxy Manager with Rotation

The `ProxyManager` class provides advanced proxy rotation and health management:

```python
from crawlit.utils.proxy_manager import ProxyManager, ProxyRotationStrategy

# Create proxy manager with rotation strategy
proxy_manager = ProxyManager(
    rotation_strategy=ProxyRotationStrategy.ROUND_ROBIN,
    max_failures=5,           # Max failures before marking proxy as down
    remove_failed=True,       # Remove failed proxies from rotation
    retry_failed_after=300    # Retry failed proxies after 5 minutes
)

# Add proxies in various formats
proxy_manager.add_proxy('http://proxy1.example.com:8080')
proxy_manager.add_proxy('http://user:pass@proxy2.example.com:8080')
proxy_manager.add_proxy({
    'host': 'proxy3.example.com',
    'port': 8080,
    'type': 'http',
    'username': 'user',
    'password': 'pass'
})

# Use with crawler
crawler = Crawler(
    'https://example.com',
    proxy_manager=proxy_manager
)
```

### Rotation Strategies

```python
from crawlit.utils.proxy_manager import ProxyRotationStrategy

# Available strategies:
strategies = [
    ProxyRotationStrategy.ROUND_ROBIN,     # Cycle through proxies in order
    ProxyRotationStrategy.RANDOM,          # Pick random proxy for each request
    ProxyRotationStrategy.LEAST_USED,      # Use proxy with fewest requests
    ProxyRotationStrategy.BEST_PERFORMANCE # Use proxy with best success rate
]

# Strategy comparison
proxy_manager = ProxyManager(rotation_strategy=ProxyRotationStrategy.LEAST_USED)
```

### Loading Proxies from Files

```python
from crawlit.utils.proxy_manager import load_proxies_from_file

# Load proxies from file (one per line)
# File format:
# http://proxy1.example.com:8080
# http://user:pass@proxy2.example.com:8080
# socks5://proxy3.example.com:1080
# # This is a comment
# 192.168.1.100:8080

proxies = load_proxies_from_file('proxies.txt')
proxy_manager = ProxyManager(proxies=proxies)
```

### Proxy Health Monitoring

```python
# Get detailed statistics
stats = proxy_manager.get_stats()
print(f"Total proxies: {stats['total_proxies']}")
print(f"Working proxies: {stats['working_proxies']}")

# Individual proxy stats
for proxy_stats in stats['proxies']:
    print(f"Proxy: {proxy_stats['host']}:{proxy_stats['port']}")
    print(f"  Requests: {proxy_stats['requests']}")
    print(f"  Failures: {proxy_stats['failures']}")
    print(f"  Success Rate: {proxy_stats['success_rate']:.1f}%")
    print(f"  Status: {'Working' if proxy_stats['is_working'] else 'Failed'}")

# Manual failure reporting (for integration)
proxy = proxy_manager.get_next_proxy()
try:
    # Make request with proxy
    pass
except Exception:
    proxy_manager.report_failure(proxy)
else:
    proxy_manager.report_success(proxy)
```

## Session Management and Cookie Handling

The `SessionManager` class provides unified session management for both synchronous and asynchronous crawling with authentication and cookie persistence.

### Basic Session Management

```python
from crawlit.utils.session_manager import SessionManager
from requests.auth import HTTPBasicAuth

# Initialize with authentication
session_manager = SessionManager(
    user_agent="MyBot/1.0",
    timeout=30,
    max_retries=3,
    verify_ssl=True,
    auth=('username', 'password'),           # Basic auth tuple
    oauth_token='bearer-token-here',         # OAuth token
    api_key='api-key-here',                  # API key
    api_key_header='X-API-Key',              # Custom header name
    headers={'Custom-Header': 'value'}       # Additional headers
)

# Get configured session
sync_session = session_manager.get_sync_session()
async_session = await session_manager.get_async_session()
```

### Cookie Persistence

```python
# Save cookies to file
session_manager.save_cookies('cookies.json', format='json')
session_manager.save_cookies('cookies.pkl', format='pickle')

# Load cookies from file
session_manager.load_cookies('cookies.json', format='json')
session_manager.load_cookies('cookies.pkl', format='pickle')

# Manual cookie management
session_manager.add_cookie('session_id', 'abc123', domain='example.com')
session_manager.add_cookie('preferences', 'dark_mode=1')

# Get all cookies
cookies = session_manager.get_cookies()
```

### Advanced Cookie Persistence

For complex cookie scenarios, use the `CookieJar` class directly:

```python
from crawlit.utils.cookie_persistence import CookieJar
from datetime import datetime, timedelta

cookie_jar = CookieJar()

# Set cookies with full attributes
cookie_jar.set_cookie(
    name='session_token',
    value='eyJhbGciOiJIUzI1NiI...',
    domain='example.com',
    path='/',
    expires=datetime.now() + timedelta(hours=1),
    secure=True,
    httponly=True
)

# Save cookies with metadata
cookie_jar.save('session_cookies.json', format='json')

# Load cookies
cookie_jar = CookieJar.load('session_cookies.json', format='json')

# Filter cookies by domain
login_cookies = cookie_jar.filter_by_domain('login.example.com')
```

### Dynamic Authentication Updates

```python
# Update OAuth token during crawling
session_manager.set_oauth_token('new-token-after-refresh')

# Update API key
session_manager.set_api_key('new-api-key', header_name='X-New-API-Key')
```

## CSRF Token Handling

Crawlit provides automatic CSRF token extraction and injection for protected forms and AJAX requests.

### Basic CSRF Handling

```python
from crawlit.security.csrf import CSRFTokenHandler

csrf_handler = CSRFTokenHandler()

# Extract tokens from a login page
login_html = """
<form method="post">
    <input type="hidden" name="csrf_token" value="abc123def456" />
    <input type="hidden" name="_token" value="xyz789token" />
</form>
"""

tokens = csrf_handler.extract_and_store('https://example.com/login', login_html)
# Extracted: {'csrf_token': 'abc123def456', '_token': 'xyz789token'}

# Automatically add tokens to form submission
form_data = {'username': 'user', 'password': 'pass'}
headers = {'User-Agent': 'crawlit/1.0'}

enhanced_data, enhanced_headers = csrf_handler.add_tokens_to_request(
    'https://example.com/login',
    data=form_data,
    headers=headers
)

# enhanced_data now includes CSRF tokens
# enhanced_headers include X-CSRF-Token header for AJAX compatibility
```

### Global CSRF Tokens

For API keys or session-wide tokens:

```python
# Set global tokens that apply to all requests
csrf_handler.set_global_token('api_key', 'global-api-key-123')
csrf_handler.set_global_token('client_id', 'your-client-id')

# These will be added to all requests automatically
```

### CSRF Integration with Sessions

```python
# Create session with CSRF handling
session_manager = SessionManager()
csrf_handler = CSRFTokenHandler()

# Login flow
login_response = session_manager.get_sync_session().get('https://example.com/login')
csrf_handler.extract_and_store('https://example.com/login', login_response.text)

# Submit protected form
form_data = {'username': 'user', 'password': 'secret'}
form_data, headers = csrf_handler.add_tokens_to_request(
    'https://example.com/login',
    data=form_data,
    headers={'X-Requested-With': 'XMLHttpRequest'}
)

response = session_manager.get_sync_session().post(
    'https://example.com/login',
    data=form_data,
    headers=headers
)
```

## Integration with Crawlers

### Synchronous Crawler with Full Authentication

```python
from crawlit import Crawler
from crawlit.utils.auth import create_bearer_auth
from crawlit.utils.proxy_manager import ProxyManager
from crawlit.utils.session_manager import SessionManager

# Setup authentication
auth = create_bearer_auth('your-oauth-token')

# Setup proxy rotation
proxy_manager = ProxyManager(rotation_strategy='least_used')
proxy_manager.add_proxy('http://proxy1.example.com:8080')
proxy_manager.add_proxy('http://proxy2.example.com:8080')

# Setup session with cookies
session_manager = SessionManager(
    user_agent='MyBot/2.0',
    oauth_token='your-oauth-token',
    cookies={'session_id': 'existing-session'}
)

# Create crawler
crawler = Crawler(
    start_url='https://api.example.com/protected',
    max_depth=3,
    session_manager=session_manager,
    proxy_manager=proxy_manager,
    delay=1.0  # Be respectful with delays
)

# Run crawl
results = crawler.crawl()
```

### Asynchronous Crawler with Authentication

```python
import asyncio
from crawlit import AsyncCrawler

async def main():
    # Setup session manager for async
    session_manager = SessionManager(
        oauth_token='your-token',
        api_key='your-api-key'
    )
    
    # Create async crawler
    crawler = AsyncCrawler(
        start_url='https://api.example.com',
        max_depth=2,
        max_concurrent_requests=10,
        session_manager=session_manager
    )
    
    # Crawl with authentication
    results = await crawler.crawl()
    return results

results = asyncio.run(main())
```

### Custom Fetcher Integration

For advanced control, integrate authentication with custom fetchers:

```python
from crawlit.fetchers.http_fetcher import HTTPFetcher
from crawlit.utils.auth import create_api_key_auth

class AuthenticatedFetcher(HTTPFetcher):
    def __init__(self, auth_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_manager = auth_manager
    
    def fetch(self, url, **kwargs):
        # Add authentication to all requests
        headers = kwargs.get('headers', {})
        headers = self.auth_manager.add_auth_to_headers(headers)
        
        params = kwargs.get('params', {})
        params = self.auth_manager.add_auth_to_params(params)
        
        kwargs['headers'] = headers
        kwargs['params'] = params
        
        return super().fetch(url, **kwargs)

# Use custom fetcher
auth = create_api_key_auth('your-api-key')
fetcher = AuthenticatedFetcher(auth)
```

## Best Practices

### 1. Authentication Security

```python
import os
from crawlit.utils.auth import create_bearer_auth

# ✅ DO: Use environment variables for credentials
oauth_token = os.getenv('OAUTH_TOKEN')
auth = create_bearer_auth(oauth_token)

# ❌ DON'T: Hardcode credentials in source code
# auth = create_bearer_auth('hardcoded-token-123')

# ✅ DO: Validate credentials before crawling
if not oauth_token:
    raise ValueError("OAUTH_TOKEN environment variable required")
```

### 2. Session and Cookie Management

```python
# ✅ DO: Save and restore session cookies
session_manager = SessionManager()
session_manager.load_cookies('previous_session.json')

# Crawl authenticated areas
crawler = Crawler(session_manager=session_manager)
results = crawler.crawl()

# Save session for next time
session_manager.save_cookies('session_after_crawl.json')

# ✅ DO: Handle cookie expiration gracefully
try:
    results = crawler.crawl()
except AuthenticationError:
    logger.info("Session expired, re-authenticating...")
    # Re-authenticate and retry
```

### 3. Proxy Management

```python
# ✅ DO: Monitor proxy health
proxy_manager = ProxyManager(
    max_failures=3,           # Conservative failure threshold
    remove_failed=True,       # Remove bad proxies
    retry_failed_after=600    # Retry after 10 minutes
)

# ✅ DO: Use appropriate rotation for your use case
# For rate-limited APIs: Use LEAST_USED or BEST_PERFORMANCE
# For general crawling: Use ROUND_ROBIN or RANDOM
proxy_manager = ProxyManager(rotation_strategy='least_used')

# ✅ DO: Respect rate limits even with proxies
crawler = Crawler(
    proxy_manager=proxy_manager,
    delay=2.0,                # Delay between requests
    max_concurrent_requests=5  # Limit concurrency
)
```

### 4. Token Refresh and Management

```python
import time
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self, refresh_callback):
        self.token = None
        self.expires_at = None
        self.refresh_callback = refresh_callback
    
    def get_valid_token(self):
        if not self.token or datetime.now() >= self.expires_at:
            self.refresh_token()
        return self.token
    
    def refresh_token(self):
        token_data = self.refresh_callback()
        self.token = token_data['access_token']
        self.expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])

# Usage
token_manager = TokenManager(lambda: oauth_refresh_request())

# Update auth with fresh tokens
auth = create_bearer_auth(token_manager.get_valid_token())
```

### 5. Error Handling and Retries

```python
import requests
from time import sleep

def robust_authenticated_crawl(urls, auth_manager, max_retries=3):
    session = requests.Session()
    results = []
    
    for url in urls:
        for attempt in range(max_retries):
            try:
                # Apply authentication
                headers = auth_manager.add_auth_to_headers()
                response = session.get(url, headers=headers, timeout=30)
                
                if response.status_code == 401:
                    logger.warning(f"Authentication failed for {url}")
                    # Implement token refresh logic here
                    continue
                
                response.raise_for_status()
                results.append(response.content)
                break
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {url}: {e}")
                if attempt < max_retries - 1:
                    sleep(2 ** attempt)  # Exponential backoff
                
    return results
```

## Troubleshooting

### Common Authentication Issues

#### 1. Invalid Credentials

```python
# Problem: Authentication fails with 401 Unauthorized
# Solution: Verify credentials and auth method

auth = create_basic_auth('username', 'password')
response = requests.get('https://api.example.com', auth=auth.get_auth_object())

if response.status_code == 401:
    print("Authentication failed - check credentials")
    print(f"Auth header: {auth.add_auth_to_headers()}")
```

#### 2. Token Expiration

```python
# Problem: Bearer token expires during long crawls
# Solution: Implement token refresh

class RefreshableAuth:
    def __init__(self, initial_token, refresh_func):
        self.auth = create_bearer_auth(initial_token)
        self.refresh_func = refresh_func
    
    def handle_auth_error(self):
        new_token = self.refresh_func()
        self.auth.update_config(token=new_token)
        return self.auth
```

#### 3. CSRF Token Issues

```python
# Problem: CSRF tokens not being extracted correctly
# Solution: Debug token extraction

csrf_handler = CSRFTokenHandler()
html_content = response.text

# Debug: Print HTML to verify token presence
print("HTML content:", html_content[:500])

# Extract tokens with logging
import logging
logging.getLogger('crawlit.security.csrf').setLevel(logging.DEBUG)

tokens = csrf_handler.extract_and_store(url, html_content)
print(f"Extracted tokens: {tokens}")
```

### Common Proxy Issues

#### 1. Proxy Connection Failures

```python
# Problem: Proxies fail to connect
# Solution: Test proxy connectivity

def test_proxy_connectivity(proxy_url):
    import requests
    try:
        response = requests.get(
            'http://httpbin.org/ip',
            proxies={'http': proxy_url, 'https': proxy_url},
            timeout=10
        )
        print(f"Proxy {proxy_url} working: {response.json()['origin']}")
        return True
    except Exception as e:
        print(f"Proxy {proxy_url} failed: {e}")
        return False

# Test each proxy
working_proxies = []
for proxy in proxy_list:
    if test_proxy_connectivity(proxy):
        working_proxies.append(proxy)
```

#### 2. Proxy Authentication Issues

```python
# Problem: Proxy requires authentication but fails
# Solution: Verify proxy auth format

# Correct format
proxy_with_auth = 'http://username:password@proxy.example.com:8080'

# Test authentication
proxy_manager = ProxyManager()
proxy_manager.add_proxy(proxy_with_auth)

# Check if proxy auth is being applied correctly
proxy = proxy_manager.get_next_proxy()
print(f"Proxy URL: {proxy.get_url()}")
```

#### 3. IP Leakage Detection

```python
# Problem: Real IP being exposed despite proxy usage
# Solution: Verify IP masking

def check_ip_leakage(proxy_manager):
    import requests
    
    # Test with proxy
    proxy_dict = proxy_manager.get_proxy_dict()
    response = requests.get('http://httpbin.org/ip', proxies=proxy_dict)
    proxy_ip = response.json()['origin']
    
    # Test without proxy
    response = requests.get('http://httpbin.org/ip')
    real_ip = response.json()['origin']
    
    if proxy_ip == real_ip:
        print("⚠️  IP LEAKAGE DETECTED!")
    else:
        print(f"✅ Proxy working - Real IP: {real_ip}, Proxy IP: {proxy_ip}")
```

### Session and Cookie Issues

#### 1. Cookie Persistence Problems

```python
# Problem: Cookies not persisting between requests
# Solution: Verify session configuration

session_manager = SessionManager(cookies={'debug': 'true'})

# Check if cookies are being maintained
session = session_manager.get_sync_session()
response = session.get('https://httpbin.org/cookies')
print("Cookies sent:", response.json())

# Save cookies after each important request
session_manager.save_cookies('debug_cookies.json')
```

#### 2. Session Expiration

```python
# Problem: Sessions expire during long crawls
# Solution: Implement session refresh

def refresh_session_if_needed(session_manager, test_url):
    response = session_manager.get_sync_session().get(test_url)
    if response.status_code == 401 or 'login' in response.url:
        logger.info("Session expired, refreshing...")
        # Implement login flow
        login_and_restore_session(session_manager)
        return True
    return False
```

## Complete Examples

### Example 1: E-commerce Site Scraping

```python
import os
import time
from crawlit import Crawler
from crawlit.utils.session_manager import SessionManager
from crawlit.utils.proxy_manager import ProxyManager
from crawlit.security.csrf import CSRFTokenHandler

class EcommerceScraper:
    def __init__(self):
        self.session_manager = SessionManager(
            user_agent='Mozilla/5.0 (compatible; EcommerceScraper/1.0)',
            timeout=30
        )
        
        self.proxy_manager = ProxyManager(
            rotation_strategy='least_used',
            max_failures=3
        )
        
        self.csrf_handler = CSRFTokenHandler()
        
        # Load proxies from file
        with open('proxies.txt') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    self.proxy_manager.add_proxy(line.strip())
    
    def login(self, username, password):
        """Login to the e-commerce site"""
        # Load existing cookies if available
        try:
            self.session_manager.load_cookies('ecommerce_session.json')
            logger.info("Loaded existing session cookies")
        except FileNotFoundError:
            logger.info("No existing session found, will login fresh")
        
        session = self.session_manager.get_sync_session()
        
        # Get login page and extract CSRF token
        login_url = 'https://example-shop.com/login'
        response = session.get(login_url)
        
        # Extract CSRF tokens
        self.csrf_handler.extract_and_store(login_url, response.text)
        
        # Prepare login data
        login_data = {
            'username': username,
            'password': password,
            'remember_me': '1'
        }
        
        # Add CSRF tokens
        login_data, headers = self.csrf_handler.add_tokens_to_request(
            login_url, 
            data=login_data,
            headers={'User-Agent': self.session_manager.user_agent}
        )
        
        # Submit login
        response = session.post(login_url, data=login_data, headers=headers)
        
        if 'dashboard' in response.url:
            logger.info("Login successful")
            self.session_manager.save_cookies('ecommerce_session.json')
            return True
        else:
            logger.error("Login failed")
            return False
    
    def scrape_products(self, categories):
        """Scrape products from specified categories"""
        if not self.login(os.getenv('SHOP_USERNAME'), os.getenv('SHOP_PASSWORD')):
            raise Exception("Failed to login")
        
        all_results = []
        
        for category in categories:
            logger.info(f"Scraping category: {category}")
            
            crawler = Crawler(
                start_url=f'https://example-shop.com/category/{category}',
                max_depth=3,
                session_manager=self.session_manager,
                proxy_manager=self.proxy_manager,
                delay=2.0,  # Respectful crawling
                max_pages=100
            )
            
            results = crawler.crawl()
            all_results.extend(results)
            
            # Short break between categories
            time.sleep(5)
        
        return all_results

# Usage
scraper = EcommerceScraper()
products = scraper.scrape_products(['electronics', 'books', 'clothing'])
```

### Example 2: API Crawling with Token Refresh

```python
import requests
import time
from datetime import datetime, timedelta
from crawlit import AsyncCrawler
from crawlit.utils.auth import create_bearer_auth
from crawlit.utils.session_manager import SessionManager

class APITokenManager:
    def __init__(self, client_id, client_secret, token_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.access_token = None
        self.expires_at = None
    
    def get_valid_token(self):
        if not self.access_token or datetime.now() >= self.expires_at:
            self._refresh_token()
        return self.access_token
    
    def _refresh_token(self):
        """Refresh the OAuth token"""
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'read:products read:categories'
        }
        
        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)
        self.expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 minute early
        
        logger.info(f"Token refreshed, expires at {self.expires_at}")

class APICrawler:
    def __init__(self, client_id, client_secret):
        self.token_manager = APITokenManager(
            client_id, client_secret, 
            'https://api.example.com/oauth/token'
        )
        
        self.session_manager = SessionManager(
            user_agent='APICrawler/1.0',
            timeout=60
        )
    
    async def crawl_with_auth(self, start_urls):
        """Crawl API endpoints with automatic token refresh"""
        results = []
        
        for url in start_urls:
            # Get fresh token
            token = self.token_manager.get_valid_token()
            
            # Update session with current token
            self.session_manager.set_oauth_token(token)
            
            # Create crawler with authenticated session
            crawler = AsyncCrawler(
                start_url=url,
                max_depth=2,
                max_concurrent_requests=10,
                session_manager=self.session_manager,
                delay=0.1  # API can handle faster requests
            )
            
            try:
                batch_results = await crawler.crawl()
                results.extend(batch_results)
                
            except Exception as e:
                if '401' in str(e):
                    logger.warning("Token expired during crawl, refreshing...")
                    # Force token refresh and retry
                    self.token_manager._refresh_token()
                    token = self.token_manager.get_valid_token()
                    self.session_manager.set_oauth_token(token)
                    
                    # Retry the crawl
                    batch_results = await crawler.crawl()
                    results.extend(batch_results)
                else:
                    raise
        
        return results

# Usage
import asyncio

async def main():
    crawler = APICrawler(
        client_id=os.getenv('API_CLIENT_ID'),
        client_secret=os.getenv('API_CLIENT_SECRET')
    )
    
    api_endpoints = [
        'https://api.example.com/v1/products',
        'https://api.example.com/v1/categories',
        'https://api.example.com/v1/inventory'
    ]
    
    results = await crawler.crawl_with_auth(api_endpoints)
    return results

results = asyncio.run(main())
```

### Example 3: Multi-Site Scraping with Different Auth Methods

```python
from dataclasses import dataclass
from typing import Dict, Any, List
from crawlit import Crawler
from crawlit.utils.auth import *
from crawlit.utils.session_manager import SessionManager
from crawlit.utils.proxy_manager import ProxyManager

@dataclass
class SiteConfig:
    name: str
    base_url: str
    auth_type: str
    auth_config: Dict[str, Any]
    custom_headers: Dict[str, str] = None

class MultiSiteCrawler:
    def __init__(self):
        self.sites = [
            SiteConfig(
                name='api_site',
                base_url='https://api.example.com',
                auth_type='bearer',
                auth_config={'token': os.getenv('API_BEARER_TOKEN')}
            ),
            SiteConfig(
                name='basic_auth_site',
                base_url='https://protected.example.com',
                auth_type='basic',
                auth_config={
                    'username': os.getenv('BASIC_USERNAME'),
                    'password': os.getenv('BASIC_PASSWORD')
                }
            ),
            SiteConfig(
                name='api_key_site',
                base_url='https://data.example.com',
                auth_type='api_key',
                auth_config={
                    'api_key': os.getenv('DATA_API_KEY'),
                    'key_name': 'X-API-Token',
                    'location': 'header'
                }
            ),
            SiteConfig(
                name='custom_auth_site',
                base_url='https://special.example.com',
                auth_type='custom',
                auth_config={'custom_headers': {
                    'X-Client-ID': os.getenv('CLIENT_ID'),
                    'X-Signature': self._calculate_signature(),
                    'X-Timestamp': str(int(time.time()))
                }}
            )
        ]
        
        # Shared proxy manager
        self.proxy_manager = ProxyManager(rotation_strategy='round_robin')
        self._load_proxies()
    
    def _load_proxies(self):
        """Load proxies from environment or file"""
        proxy_list = os.getenv('PROXY_LIST', '').split(',')
        for proxy in proxy_list:
            if proxy.strip():
                self.proxy_manager.add_proxy(proxy.strip())
    
    def _calculate_signature(self):
        """Calculate custom signature for special.example.com"""
        import hmac
        import hashlib
        
        secret = os.getenv('SPECIAL_SECRET', '')
        timestamp = str(int(time.time()))
        message = f"GET:/api/data:{timestamp}"
        
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _create_auth_manager(self, site_config: SiteConfig):
        """Create appropriate auth manager for site"""
        if site_config.auth_type == 'bearer':
            return create_bearer_auth(site_config.auth_config['token'])
        
        elif site_config.auth_type == 'basic':
            return create_basic_auth(
                site_config.auth_config['username'],
                site_config.auth_config['password']
            )
        
        elif site_config.auth_type == 'api_key':
            return create_api_key_auth(
                site_config.auth_config['api_key'],
                site_config.auth_config.get('key_name', 'X-API-Key'),
                site_config.auth_config.get('location', 'header')
            )
        
        elif site_config.auth_type == 'custom':
            return create_custom_auth(site_config.auth_config['custom_headers'])
        
        else:
            raise ValueError(f"Unknown auth type: {site_config.auth_type}")
    
    def crawl_site(self, site_config: SiteConfig, paths: List[str]) -> Dict[str, Any]:
        """Crawl a single site with its authentication method"""
        logger.info(f"Crawling {site_config.name} with {site_config.auth_type} auth")
        
        # Create auth manager
        auth_manager = self._create_auth_manager(site_config)
        
        # Setup session manager
        session_manager = SessionManager(
            user_agent=f'MultiSiteCrawler/1.0 ({site_config.name})',
            timeout=30
        )
        
        # Apply authentication to session
        if site_config.auth_type == 'bearer':
            session_manager.set_oauth_token(site_config.auth_config['token'])
        elif site_config.auth_type == 'api_key':
            session_manager.set_api_key(
                site_config.auth_config['api_key'],
                site_config.auth_config.get('key_name', 'X-API-Key')
            )
        
        # Add custom headers if specified
        if site_config.custom_headers:
            for name, value in site_config.custom_headers.items():
                session_manager.add_header(name, value)
        
        results = []
        for path in paths:
            full_url = f"{site_config.base_url.rstrip('/')}/{path.lstrip('/')}"
            
            crawler = Crawler(
                start_url=full_url,
                max_depth=2,
                session_manager=session_manager,
                proxy_manager=self.proxy_manager,
                delay=1.0
            )
            
            try:
                site_results = crawler.crawl()
                results.extend(site_results)
                logger.info(f"Successfully crawled {len(site_results)} pages from {site_config.name}")
                
            except Exception as e:
                logger.error(f"Failed to crawl {site_config.name}: {e}")
        
        return {
            'site': site_config.name,
            'results': results,
            'count': len(results)
        }
    
    def crawl_all_sites(self) -> List[Dict[str, Any]]:
        """Crawl all configured sites"""
        all_results = []
        
        for site_config in self.sites:
            # Define paths to crawl for each site
            if site_config.name == 'api_site':
                paths = ['/v1/data', '/v1/users', '/v1/products']
            elif site_config.name == 'basic_auth_site':
                paths = ['/protected', '/admin', '/reports']
            else:
                paths = ['/api', '/data']
            
            site_results = self.crawl_site(site_config, paths)
            all_results.append(site_results)
            
            # Brief pause between sites to be respectful
            time.sleep(2)
        
        return all_results

# Usage
if __name__ == '__main__':
    multi_crawler = MultiSiteCrawler()
    results = multi_crawler.crawl_all_sites()
    
    # Print summary
    for site_result in results:
        print(f"Site: {site_result['site']}")
        print(f"  Pages crawled: {site_result['count']}")
        print(f"  Success: {'✅' if site_result['results'] else '❌'}")
```

This comprehensive documentation covers all aspects of authentication and proxy management in crawlit, from basic usage to advanced integration scenarios. The examples demonstrate real-world use cases and best practices for secure, efficient crawling of authenticated websites and APIs.