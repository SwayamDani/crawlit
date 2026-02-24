# 🕷️ crawlit - Modular, Ethical Python Web Crawler

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful, modular, and ethical web crawler built in Python. Designed for security testing, link extraction, and website structure mapping with a focus on clean architecture and extensibility.

## 🚀 Features

### Core Crawling
- **Modular Architecture**: Easily extend with custom modules and parsers
- **Synchronous & Asynchronous**: Both sync (`Crawler`) and async (`AsyncCrawler`) implementations
- **JavaScript Rendering**: Full support for SPAs and JavaScript-heavy websites (React, Vue, Angular) via Playwright
- **Multi-threaded Support**: Thread pool support for concurrent requests in sync crawler
- **Depth Control**: Set maximum crawl depth to prevent excessive resource usage
- **Domain Filtering**: Restrict crawling to specific domains or subdomains
- **BFS Strategy**: Breadth-first search crawling algorithm
- **Queue Management**: Pause/resume, save/load state, and queue size limits

### Ethical Crawling
- **Robots.txt Compliance**: Configurable robots.txt respect with automatic crawl-delay extraction
- **Rate Limiting**: Global and per-domain rate limiting with automatic crawl-delay support
- **Session Management**: Cookie persistence, SSL verification, and custom headers
- **Authentication**: Support for Basic/Digest Auth, OAuth tokens, API keys, and custom headers
- **Retry Logic**: Configurable retry attempts with exponential backoff

### Content Extraction
- **Advanced Table Extraction**: Extract tables with support for complex structures and cell spanning
- **Image Extraction**: Extract and analyze images including alt text and accessibility information
- **Keyword Extraction**: Identify key terms and phrases from webpage content
- **Content Extraction**: Optional metadata extraction (title, description, headings, canonical URLs)
- **Content Deduplication**: Skip pages with duplicate content using SHA-256 hashing
- **Form Detection**: Extract forms with field types, labels, validation rules, and special feature detection
- **Structured Data Extraction**: Extract JSON-LD, Microdata, RDFa, Open Graph, Twitter Cards
- **Advanced Language Detection**: Multi-method language detection beyond HTML lang attribute

### Data Management
- **Database Integration**: Built-in support for SQLite, PostgreSQL, and MongoDB
- **Page Caching**: Memory and disk-based caching with TTL support
- **Storage Management**: Optional HTML content storage (memory or disk-based)
- **Crawl Resume**: Save and resume interrupted crawls
- **Progress Tracking**: Real-time progress monitoring with callbacks
- **Multiple Output Formats**: Export results as JSON, CSV, TXT, or HTML

### Security Features
- **CSRF Token Handling**: Automatic extraction and management of CSRF tokens
- **Security Headers Analysis**: Comprehensive security header analysis with ratings (A+ to F)
- **WAF Detection**: Detect 17+ Web Application Firewalls (Cloudflare, AWS WAF, Akamai, etc.)
- **Honeypot Detection**: Identify and avoid honeypot traps designed to catch bots
- **Security Ratings**: Automated security scoring and vulnerability assessment
- **Framework Support**: Django, Rails, ASP.NET, WordPress, Laravel, and more

### Advanced Features
- **Sitemap Support**: Automatic sitemap discovery and parsing from robots.txt
- **URL Filtering**: Advanced URL filtering (patterns, extensions, query parameters)
- **Enhanced Logging**: Structured JSON logging, log rotation, configurable levels
- **Error Handling**: Comprehensive error handling with custom exceptions
- **Command Line Interface**: Simple, powerful CLI for easy usage
- **Programmatic API**: Use as a library in your own Python code

### Performance & Scalability
- **Distributed Crawling**: Scale across multiple machines with message queues
- **Message Queue Integration**: RabbitMQ and Apache Kafka support
- **Worker Pools**: Concurrent task processing with multiple workers
- **Connection Pooling**: Reuse database and HTTP connections for 5x performance
- **Enterprise Scale**: Handle thousands of requests per second

## 📋 Requirements

- Python 3.8+
- Dependencies (automatically installed with pip):
  - requests, aiohttp, beautifulsoup4, html5lib, nltk
  - playwright (optional, for JavaScript rendering)

### JavaScript Rendering Setup

To enable JavaScript rendering for SPAs and JS-heavy websites:

```bash
# Install Playwright
pip install playwright

# Install browser binaries (one-time setup)
python -m playwright install

# Or install just Chromium (recommended)
python -m playwright install chromium
```

## 🛠️ Installation

### From PyPI (recommended)

```bash
# Install the core library
pip install crawlit

# Install with CLI tool support
pip install crawlit[cli]

# Install with JavaScript rendering support
pip install crawlit[js]

# Install with database support
pip install crawlit[postgresql]  # PostgreSQL
pip install crawlit[mongodb]     # MongoDB
pip install crawlit[databases]   # All databases

# Install with distributed crawling
pip install crawlit[rabbitmq]    # RabbitMQ message queue
pip install crawlit[kafka]       # Apache Kafka
pip install crawlit[distributed] # All distributed features

# Install everything
pip install crawlit[all]         # All features
```

### From Source

```bash
# Clone the repository
git clone https://github.com/SwayamDani/crawlit.git
cd crawlit

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## 📘 Usage

### API Documentation

Full API documentation is available in the `docs` directory, including documentation for:
- Core crawler modules
- Extraction modules (tables, images, and keywords)
- Output formatters
- Command-line interface

To build and view the documentation:

```bash
# Install Sphinx and required packages
pip install sphinx sphinx_rtd_theme sphinxcontrib-napoleon

# Build the documentation
cd docs
make html  # On Windows: make.bat html

# View the documentation
# Open docs/_build/html/index.html in your browser
```

### As a Library in Your Python Code

#### Basic Usage

```python
from crawlit import Crawler, save_results, generate_summary_report

# Initialize the crawler with custom parameters
crawler = Crawler(
    start_url="https://example.com",
    max_depth=3,
    internal_only=True,
    user_agent="MyCustomBot/1.0",
    delay=0.5,
    respect_robots=True
)

# Start crawling
crawler.crawl()

# Get and process results
results = crawler.get_results()
print(f"Crawled {len(results)} URLs")

# Save results in different formats
save_results(results, "json", "crawl_results.json", pretty=True)
```

#### Advanced Usage with New Features

```python
from crawlit import (
    Crawler, 
    SessionManager, 
    URLFilter, 
    ProgressTracker, 
    RateLimiter,
    PageCache,
    StorageManager,
    SitemapParser,
    ContentDeduplicator,
    LoggingConfig
)

# Configure enhanced logging
logging_config = LoggingConfig(
    level="INFO",
    json_logging=True,
    log_file="crawl.log",
    rotation_size_mb=10
)
logging_config.apply()

# Set up session with authentication
session_manager = SessionManager(
    user_agent="MyBot/1.0",
    oauth_token="your-oauth-token",
    api_key="your-api-key",
    api_key_header="X-API-Key"
)

# Configure URL filtering
url_filter = URLFilter(
    allowed_patterns=[r".*example\.com.*"],
    blocked_extensions=[".pdf", ".zip"]
)

# Set up progress tracking
def progress_callback(stats):
    print(f"Progress: {stats['crawled']}/{stats['total']} URLs")

progress_tracker = ProgressTracker(callback=progress_callback)

# Configure per-domain rate limiting
rate_limiter = RateLimiter(default_delay=0.5)
rate_limiter.set_domain_delay("example.com", 1.0)  # Slower for specific domain

# Set up page caching
page_cache = PageCache(use_disk=True, cache_dir="./cache", ttl=3600)

# Configure storage (optional HTML content storage)
storage_manager = StorageManager(
    store_html_content=True,
    use_disk_storage=True,
    storage_dir="./html_storage"
)

# Set up content deduplication
content_deduplicator = ContentDeduplicator(
    min_content_length=100,
    normalize_content=True
)

# Initialize crawler with all features
crawler = Crawler(
    start_url="https://example.com",
    max_depth=3,
    session_manager=session_manager,
    url_filter=url_filter,
    progress_tracker=progress_tracker,
    rate_limiter=rate_limiter,
    page_cache=page_cache,
    storage_manager=storage_manager,
    content_deduplicator=content_deduplicator,
    use_per_domain_delay=True,
    enable_content_extraction=True,
    enable_content_deduplication=True,
    use_sitemap=True,  # Auto-discover sitemaps from robots.txt
    max_workers=4,  # Multi-threaded crawling
    max_queue_size=1000
)

# Start crawling
crawler.crawl()

# Pause and resume
crawler.pause()
# ... do something ...
crawler.resume()

# Save state for later resumption
crawler.save_state("crawl_state.json")

# Get results
results = crawler.get_results()
print(f"Crawled {len(results)} URLs")
```

#### Asynchronous Usage

```python
import asyncio
from crawlit import AsyncCrawler, AsyncRateLimiter

async def main():
    # Async crawler with async rate limiter
    rate_limiter = AsyncRateLimiter(default_delay=0.5)
    
    crawler = AsyncCrawler(
        start_url="https://example.com",
        max_depth=3,
        rate_limiter=rate_limiter,
        use_per_domain_delay=True,
        max_concurrent_requests=10
    )
    
    await crawler.crawl()
    results = crawler.get_results()
    print(f"Crawled {len(results)} URLs")

asyncio.run(main())
```

#### JavaScript Rendering (SPAs & JS-Heavy Websites)

```python
from crawlit import Crawler

# Synchronous crawler with JavaScript rendering
crawler = Crawler(
    start_url="https://react-app-example.com",
    max_depth=2,
    use_js_rendering=True,  # Enable JavaScript rendering
    js_browser_type="chromium",  # chromium, firefox, or webkit
    js_wait_for_selector="#app",  # Wait for specific element (optional)
    js_wait_for_timeout=2000  # Additional wait in milliseconds (optional)
)

crawler.crawl()
results = crawler.get_results()
```

```python
import asyncio
from crawlit import AsyncCrawler

# Asynchronous crawler with JavaScript rendering
async def main():
    crawler = AsyncCrawler(
        start_url="https://vue-app-example.com",
        max_depth=2,
        use_js_rendering=True,
        js_browser_type="chromium",
        js_wait_for_selector=".main-content",
        max_concurrent_requests=5  # Control concurrency with JS rendering
    )
    
    await crawler.crawl()
    results = crawler.get_results()
    print(f"Crawled {len(results)} URLs from SPA")

asyncio.run(main())
```

**Supported Frameworks:**
- React (including Create React App, Next.js)
- Vue.js (including Nuxt.js)
- Angular
- Svelte
- Any JavaScript-rendered content

**Browser Options:**
- `chromium` (recommended, fastest)
- `firefox`
- `webkit` (Safari engine)

See the `examples/programmatic_usage.py` file for a complete example.

#### Database Integration

Store crawl results directly in databases instead of files:

```python
from crawlit import Crawler
from crawlit.utils.database import get_database_backend

# Option 1: SQLite (built-in, no extra dependencies)
db = get_database_backend('sqlite', database_path='crawl_results.db')

# Option 2: PostgreSQL (requires psycopg2-binary)
# db = get_database_backend('postgresql',
#     host='localhost',
#     database='crawlit',
#     user='postgres',
#     password='your_password'
# )

# Option 3: MongoDB (requires pymongo)
# db = get_database_backend('mongodb',
#     host='localhost',
#     database='crawlit',
#     collection='results'
# )

# Crawl a website
crawler = Crawler(
    start_url="https://example.com",
    max_depth=2
)

results = crawler.crawl()

# Save to database
metadata = {
    'start_url': crawler.start_url,
    'max_depth': crawler.max_depth,
    'user_agent': crawler.user_agent
}

crawl_id = db.save_results(results, metadata)
print(f"Saved {len(results)} pages to database (crawl_id: {crawl_id})")

# Query results
all_results = db.get_results({'crawl_id': crawl_id})
successful = db.get_results({'crawl_id': crawl_id, 'status_code': 200})
failed = db.get_results({'crawl_id': crawl_id, 'success': False})

# Get crawl history
crawls = db.get_crawls(limit=10)
for crawl in crawls:
    print(f"[{crawl['id']}] {crawl['start_url']} - {crawl['successful_urls']}/{crawl['total_urls']} successful")

# Cleanup
db.clear_results({'crawl_id': crawl_id})  # Delete specific crawl
# db.clear_results()  # Clear all results

db.disconnect()
```

**Database Features:**
- **SQLite**: Perfect for local development, no setup required
- **PostgreSQL**: Production-ready with ACID compliance and advanced querying
- **MongoDB**: Flexible document storage for unstructured data
- **Query Support**: Filter by URL, status code, success/failure, crawl ID
- **Metadata Tracking**: Store crawl configuration and statistics
- **Easy Cleanup**: Delete specific crawls or clear all data

See the `examples/database_integration.py` file for complete examples.

### Command Line Interface

If you installed with `pip install crawlit[cli]`, you can use the command-line interface:

```bash
# Basic usage
crawlit --url https://example.com

# Advanced options
crawlit --url https://example.com \
        --depth 3 \
        --output-format json \
        --output results.json \
        --delay 0.5 \
        --user-agent "crawlit/1.0" \
        --ignore-robots

# With new extraction features (v0.2.0+)
crawlit --url https://example.com \
        --user-agent "crawlit/2.0" \
        --extract-tables \
        --tables-output "./table_output" \
        --extract-images \
        --images-output "./image_output" \
        --extract-keywords \
        --keywords-output "keywords.json"

# Crawl a Single Page Application (SPA) with JavaScript rendering
crawlit --url https://react-app.com \
        --use-js \
        --js-browser chromium \
        --js-wait-selector "#root" \
        --depth 2 \
        --output spa_results.json

# Save results to a database
crawlit --url https://example.com \
        --database sqlite \
        --db-path my_crawls.db \
        --depth 2

# Save to PostgreSQL
crawlit --url https://example.com \
        --database postgresql \
        --db-host localhost \
        --db-name crawlit \
        --db-user postgres \
        --db-password mypassword

# Save to MongoDB
crawlit --url https://example.com \
        --database mongodb \
        --db-host localhost \
        --db-name crawlit \
        --db-collection results
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--url`, `-u` | Target website URL | Required |
| `--depth`, `-d` | Maximum crawl depth | 3 |
| `--output-format`, `-f` | Output format (json, csv, txt, html) | json |
| `--output`, `-O` | File to save results | crawl_results.json |
| `--pretty-json`, `-p` | Enable pretty-print JSON with indentation | False |
| `--ignore-robots`, `-i` | Ignore robots.txt rules | False |
| `--delay` | Delay between requests (seconds) | 0.1 |
| `--user-agent`, `-a` | Custom User-Agent string | crawlit/1.0 |
| `--allow-external`, `-e` | Allow crawling URLs outside initial domain | False |
| `--summary`, `-s` | Show a summary of crawl results | False |
| `--verbose`, `-v` | Verbose output | False |
| `--extract-keywords`, `-k` | Extract keywords from crawled pages | False |
| `--keywords-output` | File to save extracted keywords | keywords.json |
| `--max-keywords` | Maximum number of keywords to extract per page | 20 |
| `--min-word-length` | Minimum length of words to consider as keywords | 3 |
| `--extract-images`, `-img` | Extract images from crawled pages | False |
| `--images-output` | Directory to save extracted images data | image_output/ |
| `--extract-tables`, `-t` | Extract tables from crawled pages | False |
| `--tables-output` | Directory to save extracted tables | table_output/ |
| `--tables-format` | Format to save extracted tables (csv or json) | csv |
| `--min-rows` | Minimum number of rows for a table to be extracted | 1 |
| `--min-columns` | Minimum number of columns for a table to be extracted | 2 |
| `--max-table-depth` | Maximum depth to extract tables from | Same as max crawl depth |
| `--use-js`, `--javascript` | Enable JavaScript rendering for SPAs | False |
| `--js-browser` | Browser type (chromium, firefox, webkit) | chromium |
| `--js-wait-selector` | CSS selector to wait for | None |
| `--js-wait-timeout` | Additional wait timeout in milliseconds | None |
| `--database`, `--db` | Database backend (sqlite, postgresql, mongodb) | None |
| `--db-path` | Database file path (SQLite) | crawl_results.db |
| `--db-host` | Database host (PostgreSQL/MongoDB) | localhost |
| `--db-port` | Database port | 5432 (PostgreSQL) / 27017 (MongoDB) |
| `--db-name` | Database name | crawlit |
| `--db-user` | Database username (PostgreSQL) | postgres |
| `--db-password` | Database password | (empty) |
| `--db-collection` | Collection name (MongoDB) | results |
| `--help`, `-h` | Show help message | - |

## 📊 Advanced Table Extraction

Crawlit includes powerful HTML table extraction capabilities:

```python
from crawlit.extractors.tables import extract_tables

# Extract tables with minimum rows and columns filters
tables = extract_tables(html_content, min_rows=2, min_columns=3)

# Convert tables to CSV
from crawlit.extractors.tables import tables_to_csv
tables_to_csv(tables, base_filename="extracted_tables", output_dir="output")

# Convert to dictionaries using first row as headers
from crawlit.extractors.tables import tables_to_dict
table_dicts = tables_to_dict(tables)

# Convert to JSON
from crawlit.extractors.tables import tables_to_json
tables_to_json(tables, base_filename="extracted_tables")
```

The advanced table extraction provides:
- Smart handling of `<thead>` and `<tbody>` sections
- Full support for `rowspan` and `colspan` attributes
- Consistent column count across all rows
- Thorough cell content cleaning (HTML entities, whitespace, etc.)

For examples, see `examples/enhanced_table_extraction.py` and `examples/rowspan_colspan_example.py`.

## 🔍 Keyword Extraction

Crawlit 2.0 includes sophisticated keyword extraction capabilities:

```python
from crawlit import Crawler
from crawlit.extractors.keyword_extractor import KeywordExtractor

# Option 1: Use the crawler with crawlit/2.0 user agent for automatic keyword extraction
crawler = Crawler(
    start_url="https://example.com",
    user_agent="crawlit/2.0",  # Required for keyword extraction
    max_depth=2
)
crawler.crawl()
results = crawler.get_results()

# Access extracted keywords from results
for url, data in results.items():
    if 'keywords' in data:
        print(f"Keywords for {url}: {data['keywords']}")
    if 'keyphrases' in data:
        print(f"Key phrases: {data['keyphrases']}")

# Option 2: Use the keyword extractor directly on HTML content
extractor = KeywordExtractor(min_word_length=4, max_keywords=10)
html_content = "<html><body><h1>Keyword Extraction Example</h1><p>This demonstrates advanced keyword extraction capability.</p></body></html>"

# Get keywords with scores
keywords_data = extractor.extract_keywords(html_content, include_scores=True)
print(f"Keywords: {keywords_data['keywords']}")
print(f"Scores: {keywords_data['scores']}")

# Get multi-word phrases
keyphrases = extractor.extract_keyphrases(html_content)
print(f"Key phrases: {keyphrases}")
```

The keyword extraction offers:
- Smart weighting of content based on HTML structure (headings, titles, etc.)
- Automatic filtering of common stop words
- Multi-word phrase extraction for more context-rich keywords
- Scoring based on frequency and relevance
- Integration with crawl results

For a complete example, see `examples/keyword_extraction.py`.

## 🖼️ Image Extraction

Crawlit v0.2.0 introduces comprehensive image extraction capabilities:

```python
from crawlit import Crawler
from crawlit.extractors.image_extractor import ImageTagParser

# Option 1: Using the crawler for automatic image extraction
crawler = Crawler(
    start_url="https://example.com",
    max_depth=2
)
crawler.crawl()
results = crawler.get_results()

# Access extracted images from results
for url, data in results.items():
    if 'images' in data:
        for img in data['images']:
            print(f"Image URL: {img.get('src')}")
            print(f"Alt text: {img.get('alt', 'None')}")
            if 'width' in img and 'height' in img:
                print(f"Dimensions: {img['width']}x{img['height']}")
            print(f"Decorative: {img.get('decorative', False)}")

# Option 2: Use the image extractor directly on HTML content
from html.parser import HTMLParser
parser = ImageTagParser()
html_content = "<html><body><img src='example.jpg' alt='Example'></body></html>"
parser.feed(html_content)
images = parser.images
```

The image extraction feature provides:
- Complete metadata extraction (src, alt, width, height, etc.)
- Parent element context to understand image placement
- Accessibility analysis (identifying decorative images missing alt text)
- Integration with crawl results

For a complete example, see `examples/image_extraction.py`.

## 🔐 Authentication

Crawlit provides comprehensive authentication utilities for various auth methods.

### Authentication Manager

```python
from crawlit import create_basic_auth, create_bearer_auth, create_api_key_auth

# Basic Authentication
auth = create_basic_auth('username', 'password')
headers = auth.add_auth_to_headers()

# Bearer Token (OAuth/JWT)
auth = create_bearer_auth('your_jwt_token')
headers = auth.add_auth_to_headers()
# Result: {'Authorization': 'Bearer your_jwt_token'}

# API Key (in header)
auth = create_api_key_auth('your_api_key', 'X-API-Key', 'header')
headers = auth.add_auth_to_headers()

# API Key (in query parameter)
auth = create_api_key_auth('your_api_key', 'api_key', 'query')
params = auth.add_auth_to_params({'page': '1'})

# Custom Headers
from crawlit import create_custom_auth
auth = create_custom_auth({
    'X-Custom-Auth': 'token',
    'X-Request-ID': 'req-123'
})
headers = auth.add_auth_to_headers()

# Digest Authentication
from crawlit import create_digest_auth
auth = create_digest_auth('username', 'password')
auth_obj = auth.get_auth_object()
```

See `examples/auth_example.py` for more examples.

## 🔧 Environment & Configuration

Load configuration from environment variables, .env files, and JSON config files.

### Basic Environment Loading

```python
from crawlit import EnvLoader, load_env

# Load .env file
load_env('.env')

# Type-safe variable access
loader = EnvLoader()
port = loader.get_int('PORT', default=8080)
debug = loader.get_bool('DEBUG', default=False)
features = loader.get_list('FEATURES')  # comma-separated
```

### Configuration File Loading

```python
from crawlit import ConfigLoader

# Load from JSON config with env variable override
loader = ConfigLoader(
    env_file='.env',
    config_file='config.json',
    auto_load=True
)

# Access configuration (priority: env > .env > config file > default)
db_host = loader.get('db_host', default='localhost')
db_port = loader.get_int('db_port', default=5432)

# Get configuration section
db_config = loader.get_section('database')
```

### .env File Format

```bash
# .env example
APP_NAME=MyApp
APP_DEBUG=true
APP_PORT=8080

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb

# Features (comma-separated)
FEATURES=feature1,feature2,feature3

# Quoted values
API_KEY="secret key with spaces"
```

See `examples/env_config_example.py` for more examples.

## 🔐 Session Management

Crawlit supports multiple authentication methods:

```python
from crawlit import Crawler, SessionManager

# OAuth token authentication
session_manager = SessionManager(
    user_agent="MyBot/1.0",
    oauth_token="your-oauth-token"
)

# API key authentication
session_manager = SessionManager(
    user_agent="MyBot/1.0",
    api_key="your-api-key",
    api_key_header="X-API-Key"  # Optional, defaults to "Authorization"
)

# Basic authentication
from requests.auth import HTTPBasicAuth
session_manager = SessionManager(
    user_agent="MyBot/1.0",
    auth=HTTPBasicAuth("username", "password")
)

# Custom headers
session_manager = SessionManager(
    user_agent="MyBot/1.0",
    headers={"X-Custom-Header": "value"}
)

# Combine multiple methods
session_manager = SessionManager(
    user_agent="MyBot/1.0",
    oauth_token="token",
    api_key="key",
    headers={"X-Custom": "value"}
)

# Use with crawler
crawler = Crawler(
    start_url="https://example.com",
    session_manager=session_manager
)
```

## ⚡ Rate Limiting

### Per-Domain Rate Limiting

```python
from crawlit import Crawler, RateLimiter

# Create rate limiter with default delay
rate_limiter = RateLimiter(default_delay=0.5)

# Set custom delays for specific domains
rate_limiter.set_domain_delay("example.com", 1.0)
rate_limiter.set_domain_delay("api.example.com", 2.0)

# Use with crawler (automatically respects robots.txt crawl-delay)
crawler = Crawler(
    start_url="https://example.com",
    rate_limiter=rate_limiter,
    use_per_domain_delay=True
)
```

The crawler automatically extracts and respects `Crawl-delay` directives from robots.txt files.

## 🗺️ Sitemap Support

```python
from crawlit import Crawler

# Auto-discover sitemaps from robots.txt
crawler = Crawler(
    start_url="https://example.com",
    use_sitemap=True  # Automatically discovers and parses sitemaps
)

# Or provide explicit sitemap URLs
crawler = Crawler(
    start_url="https://example.com",
    use_sitemap=True,
    sitemap_urls=[
        "https://example.com/sitemap.xml",
        "https://example.com/sitemap-news.xml"
    ]
)
```

## 📊 Progress Tracking

```python
from crawlit import Crawler, ProgressTracker

def progress_callback(stats):
    print(f"Crawled: {stats['crawled']}, Failed: {stats['failed']}, Total: {stats['total']}")
    print(f"Success Rate: {stats['success_rate']:.2f}%")

progress_tracker = ProgressTracker(callback=progress_callback)

crawler = Crawler(
    start_url="https://example.com",
    progress_tracker=progress_tracker
)

crawler.crawl()

# Get final statistics
stats = progress_tracker.get_stats()
print(f"Final stats: {stats}")
```

## 🔍 URL Filtering

```python
from crawlit import Crawler, URLFilter

# Filter by patterns
url_filter = URLFilter(
    allowed_patterns=[r".*example\.com.*"],
    blocked_patterns=[r".*admin.*"]
)

# Filter by file extensions
url_filter = URLFilter(
    allowed_extensions=[".html", ".htm"],
    blocked_extensions=[".pdf", ".zip"]
)

# Use factory methods
url_filter = URLFilter.html_only()  # Only HTML pages
url_filter = URLFilter.exclude_media()  # Exclude images, videos, etc.

# Use with crawler
crawler = Crawler(
    start_url="https://example.com",
    url_filter=url_filter
)
```

## 💾 Caching & Resume

```python
from crawlit import Crawler, PageCache, CrawlResume

# Set up page caching
page_cache = PageCache(
    use_disk=True,
    cache_dir="./cache",
    ttl=3600  # Cache for 1 hour
)

crawler = Crawler(
    start_url="https://example.com",
    page_cache=page_cache
)

# Save state for resumption
crawler.save_state("crawl_state.json")

# Later, resume from saved state
crawler.load_state("crawl_state.json")
crawler.crawl()  # Continues from where it left off
```

## 🗄️ Storage Management

```python
from crawlit import Crawler, StorageManager

# Store HTML content in memory (default)
storage_manager = StorageManager(store_html_content=True)

# Disable HTML content storage (save memory)
storage_manager = StorageManager(store_html_content=False)

# Store HTML content on disk
storage_manager = StorageManager(
    store_html_content=True,
    use_disk_storage=True,
    storage_dir="./html_storage"
)

crawler = Crawler(
    start_url="https://example.com",
    storage_manager=storage_manager
)
```

## 🔄 Content Deduplication

```python
from crawlit import Crawler, ContentDeduplicator

# Set up content deduplication
content_deduplicator = ContentDeduplicator(
    min_content_length=100,  # Minimum content length to consider
    normalize_content=True   # Normalize content (remove whitespace, etc.)
)

crawler = Crawler(
    start_url="https://example.com",
    content_deduplicator=content_deduplicator,
    enable_content_deduplication=True
)

# Get deduplication statistics
stats = content_deduplicator.get_stats()
print(f"Duplicate pages found: {stats['duplicates']}")
```

## 📝 Enhanced Logging

```python
from crawlit import LoggingConfig, configure_logging

# Configure structured JSON logging
logging_config = LoggingConfig(
    level="INFO",
    json_logging=True,
    log_file="crawl.log",
    rotation_size_mb=10,  # Rotate when file reaches 10MB
    rotation_time="midnight"  # Or rotate daily at midnight
)

logging_config.apply()

# Or use convenience function
configure_logging(
    level="INFO",
    log_file="crawl.log",
    json_logging=True
)

# Use contextual logging
from crawlit import log_with_context

log_with_context("INFO", "Starting crawl", {"url": "https://example.com"})
```

## 🧵 Multi-threaded Crawling

```python
from crawlit import Crawler

# Enable multi-threaded crawling (sync crawler only)
crawler = Crawler(
    start_url="https://example.com",
    max_workers=4  # Use 4 worker threads
)

# Single-threaded (default)
crawler = Crawler(
    start_url="https://example.com",
    max_workers=1  # Or omit for default
)
```

## ⏸️ Pause & Resume

```python
from crawlit import Crawler

crawler = Crawler(start_url="https://example.com")

# Start crawling in background thread
import threading
thread = threading.Thread(target=crawler.crawl)
thread.start()

# Pause crawling
crawler.pause()

# Check if paused
if crawler.is_paused():
    print("Crawler is paused")

# Resume crawling
crawler.resume()

# Get queue statistics
stats = crawler.get_queue_stats()
print(f"Queue size: {stats['size']}")
```

## 🔒 Proxy Support

Crawlit provides comprehensive proxy support with rotation, health tracking, and multiple strategies.

### Basic Proxy Usage

```python
from crawlit import Crawler

# Single proxy
crawler = Crawler(
    'https://example.com',
    proxy='http://proxy.example.com:8080'
)

# With authentication
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

```python
from crawlit import Crawler, ProxyManager

# Create proxy manager
proxy_manager = ProxyManager(rotation_strategy='round-robin')

# Add proxies
proxy_manager.add_proxy('http://proxy1.example.com:8080')
proxy_manager.add_proxy('http://proxy2.example.com:8080', proxy_type='https')
proxy_manager.add_proxy('socks5://proxy3.example.com:1080', proxy_type='socks5')

# With authentication
proxy_manager.add_proxy(
    'http://proxy4.example.com:8080',
    username='user',
    password='pass'
)

# Use with crawler
crawler = Crawler(
    'https://example.com',
    proxy_manager=proxy_manager
)
```

### Load Proxies from File

```python
# Create proxies.txt with one proxy per line:
# http://proxy1.example.com:8080
# http://user:pass@proxy2.example.com:8080
# socks5://proxy3.example.com:1080

proxy_manager = ProxyManager(rotation_strategy='least-used')
count = proxy_manager.load_from_file('proxies.txt')
print(f"Loaded {count} proxies")

crawler = Crawler('https://example.com', proxy_manager=proxy_manager)
```

### Rotation Strategies

- **round-robin**: Rotate proxies in order
- **random**: Select random proxy for each request
- **least-used**: Use the proxy with fewest requests
- **best-performance**: Use the proxy with best success rate

### Health Tracking & Statistics

```python
# Check proxy statistics
stats = proxy_manager.get_stats()
print(f"Total proxies: {stats['total_proxies']}")
print(f"Working proxies: {stats['working_proxies']}")
print(f"Rotation strategy: {stats['rotation_strategy']}")

# Get working proxy count
working_count = proxy_manager.get_working_count()
print(f"Working proxies: {working_count}")

# Get next proxy (automatically handles rotation)
proxy = proxy_manager.get_next_proxy()
if proxy:
    print(f"Selected proxy: {proxy.url}")
```

### CLI Usage

```bash
# Single proxy
crawlit --url https://example.com --proxy http://proxy.example.com:8080

# Proxy file with rotation
crawlit --url https://example.com \\
    --proxy-file proxies.txt \\
    --proxy-rotation round-robin

# Available strategies: round-robin, random, least-used, best-performance
```

## 🌐 JavaScript Rendering

Crawlit now includes powerful JavaScript rendering capabilities using Playwright, enabling you to crawl:

- **Single Page Applications (SPAs)**: React, Vue, Angular, Svelte
- **Dynamic Content**: AJAX-loaded content, infinite scroll
- **JavaScript-Heavy Sites**: Modern web applications with client-side routing

### Features

- **Multiple Browser Engines**: Chromium (recommended), Firefox, Webkit
- **Smart Waiting**: Wait for specific selectors or timeouts
- **Full Page Rendering**: Get the complete DOM after JavaScript execution
- **Headless Mode**: Fast, resource-efficient crawling
- **Async Support**: Works with both sync and async crawlers

### Example Use Cases

```python
from crawlit import Crawler

# Crawl a React application
crawler = Crawler(
    start_url="https://reactjs.org",
    use_js_rendering=True,
    js_wait_for_selector="#main-content",
    max_depth=2
)

# Crawl with additional wait time for animations
crawler = Crawler(
    start_url="https://vue-app.com",
    use_js_rendering=True,
    js_wait_for_timeout=3000,  # Wait 3 seconds for animations
    max_depth=2
)

# Use Firefox engine for testing
crawler = Crawler(
    start_url="https://angular-app.com",
    use_js_rendering=True,
    js_browser_type="firefox",
    max_depth=2
)
```

### Performance Considerations

- JavaScript rendering is slower than static HTML fetching
- Use `js_wait_for_selector` to minimize wait times
- Consider reducing `max_concurrent_requests` for async crawling with JS
- Chromium is generally the fastest browser engine

## 🏗️ Project Structure

```
crawlit/
├── crawlit.py           # CLI entry point
├── requirements.txt     # Project dependencies
├── crawler/             # Core crawler modules
│   ├── __init__.py
│   ├── engine.py        # Synchronous crawler engine
│   ├── async_engine.py  # Asynchronous crawler engine
│   ├── fetcher.py       # HTTP request handling (sync)
│   ├── async_fetcher.py # HTTP request handling (async)
│   ├── js_renderer.py   # JavaScript rendering with Playwright
│   ├── parser.py        # HTML parsing and link extraction
│   └── robots.py        # Robots.txt parser with crawl-delay support
├── extractors/          # Data extraction modules
│   ├── __init__.py
│   ├── content_extractor.py  # Unified content extraction
│   ├── image_extractor.py    # Image extraction and analysis
│   ├── keyword_extractor.py  # Keyword and keyphrase extraction
│   └── tables.py            # Advanced table extraction
├── utils/               # Utility modules
│   ├── __init__.py
│   ├── session_manager.py   # Session management with auth
│   ├── url_filter.py         # Advanced URL filtering
│   ├── progress.py           # Progress tracking
│   ├── queue_manager.py      # Queue state management
│   ├── cache.py              # Page caching and resume
│   ├── storage.py            # HTML content storage
│   ├── sitemap.py            # Sitemap parsing
│   ├── rate_limiter.py       # Per-domain rate limiting
│   ├── deduplication.py      # Content deduplication
│   ├── logging_config.py     # Enhanced logging
│   └── errors.py             # Custom exceptions
├── output/              # Output formatters
│   ├── __init__.py
│   └── formatters.py    # Output formatting functions
├── examples/            # Example usage
│   ├── programmatic_usage.py  # Example of using as a library
│   ├── authenticated_crawling.py  # Authentication examples
│   └── extraction_coverage_demo.py  # Extraction features demo
└── tests/               # Unit and integration tests
    └── __init__.py
```

## 📅 Project Timeline

- **May 2025**: Initial structure and CLI setup
- **May 15, 2025**: v0.2.0 release with image extraction, table extraction, and keyword extraction features
- **June 2025**: Core functionality complete (HTTP handling, parsing, domain control)
- **June 30, 2025**: Project completion target with all core features

## 🤝 Contributing

Contributions will be welcome after the core functionality is complete. Please check back after June 30, 2025, for contribution guidelines.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

Built and maintained by Swayam Dani

---

**Note**: This project is under active development with completion targeted for June 30, 2025.