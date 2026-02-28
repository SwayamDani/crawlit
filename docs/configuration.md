# Configuration Documentation

This document provides a comprehensive guide to configuring crawlit for different web crawling scenarios. Crawlit supports multiple configuration methods and provides fine-grained control over crawling behavior, extraction features, and output formats.

## Table of Contents

1. [Configuration Methods](#configuration-methods)
2. [Configuration Classes](#configuration-classes)
3. [Environment Variables](#environment-variables)
4. [Command Line Arguments](#command-line-arguments)
5. [Configuration File Formats](#configuration-file-formats)
6. [Feature Configuration](#feature-configuration)
7. [Performance Tuning](#performance-tuning)
8. [Configuration Examples](#configuration-examples)
9. [Advanced Patterns](#advanced-patterns)
10. [Best Practices](#best-practices)

## Configuration Methods

Crawlit supports several configuration methods that can be used independently or combined:

### 1. Config Objects (Recommended)

The modern, structured approach using dataclass-based configuration objects:

```python
from crawlit.config import CrawlerConfig, FetchConfig, RateLimitConfig, OutputConfig
from crawlit.crawler.engine import Crawler

# Create configuration
config = CrawlerConfig(
    start_url="https://example.com",
    max_depth=5,
    fetch=FetchConfig(timeout=30, use_js_rendering=True),
    rate_limit=RateLimitConfig(delay=1.0),
    output=OutputConfig(write_jsonl=True, jsonl_path="results.jsonl")
)

# Use with crawler
crawler = Crawler(config=config)
results = crawler.crawl()
```

### 2. Direct Constructor Arguments

The legacy approach using keyword arguments (fully backward compatible):

```python
from crawlit.crawler.engine import Crawler

crawler = Crawler(
    start_url="https://example.com",
    max_depth=5,
    timeout=30,
    delay=1.0,
    user_agent="MyBot/1.0"
)
```

### 3. Command Line Interface

Direct execution via command line with extensive argument support:

```bash
python -m crawlit --url https://example.com --depth 5 --delay 1.0 --extract-tables --use-js
```

### 4. Environment Variables

Configuration through environment variables and `.env` files:

```bash
export CRAWLIT_START_URL="https://example.com"
export CRAWLIT_MAX_DEPTH=5
export CRAWLIT_DELAY=1.0
```

## Configuration Classes

### CrawlerConfig

The main configuration class that orchestrates all crawling behavior:

```python
@dataclasses.dataclass
class CrawlerConfig:
    """Top-level crawl configuration"""
    
    # Basic crawl parameters
    start_url: str = ""                           # Starting URL for the crawl
    max_depth: int = 3                           # Maximum crawl depth
    internal_only: bool = True                   # Restrict to same domain
    same_path_only: bool = False                 # Restrict to same path prefix
    respect_robots: bool = True                  # Honor robots.txt
    max_queue_size: Optional[int] = None         # URL queue size limit
    
    # Concurrency settings
    max_workers: Optional[int] = 1               # ThreadPoolExecutor workers (sync)
    max_concurrent_requests: int = 5             # Semaphore size (async)
    
    # Sub-configurations
    fetch: FetchConfig = FetchConfig()           # HTTP/rendering config
    rate_limit: RateLimitConfig = RateLimitConfig()  # Rate limiting config
    output: OutputConfig = OutputConfig()        # Output format config
    
    # Feature flags
    enable_image_extraction: bool = False
    enable_keyword_extraction: bool = False
    enable_table_extraction: bool = False
    enable_content_extraction: bool = False
    enable_content_deduplication: bool = False
    enable_incremental: bool = False
    enable_pdf_extraction: bool = False
    enable_js_embedded_data: bool = False
    enable_dom_features: bool = False
    
    # Sitemap support
    use_sitemap: bool = False
    sitemap_urls: List[str] = []
    
    # Budget limits
    max_pages: Optional[int] = None              # Maximum pages to crawl
    max_bytes: Optional[int] = None              # Maximum bandwidth
    max_time_seconds: Optional[float] = None     # Maximum crawl duration
```

### FetchConfig

Configuration for HTTP requests and JavaScript rendering:

```python
@dataclasses.dataclass
class FetchConfig:
    """HTTP fetch and rendering parameters"""
    
    # HTTP settings
    user_agent: str = "crawlit/1.0"              # User-Agent header
    max_retries: int = 3                         # Retry attempts
    timeout: int = 10                            # Request timeout (seconds)
    verify_ssl: bool = True                      # SSL certificate verification
    proxy: Optional[str] = None                  # Proxy server URL
    
    # JavaScript rendering (requires Playwright)
    use_js_rendering: bool = False               # Enable JS rendering
    js_wait_for_selector: Optional[str] = None   # CSS selector to wait for
    js_wait_for_timeout: Optional[int] = None    # Additional wait time (ms)
    js_browser_type: str = "chromium"            # Browser: chromium, firefox, webkit
```

### RateLimitConfig

Configuration for request rate limiting and delays:

```python
@dataclasses.dataclass
class RateLimitConfig:
    """Rate-limiting parameters"""
    
    delay: float = 0.1                           # Base delay between requests
    use_per_domain_delay: bool = True            # Per-domain rate limiting
    respect_robots_crawl_delay: bool = True      # Honor crawl-delay in robots.txt
```

### OutputConfig

Configuration for output formats and storage options:

```python
@dataclasses.dataclass
class OutputConfig:
    """Output and persistence parameters"""
    
    # HTML content storage
    store_html_content: bool = True              # Include HTML in results
    enable_disk_storage: bool = False            # Use disk vs memory storage
    storage_dir: Optional[str] = None            # Directory for disk storage
    
    # JSONL artifact stream (one artifact per line)
    write_jsonl: bool = False                    # Enable JSONL output
    jsonl_path: Optional[str] = None             # JSONL file path
    
    # Blob store (raw HTML/PDF files by content hash)
    write_blobs: bool = False                    # Enable blob storage
    blobs_dir: Optional[str] = None              # Blob storage directory
    
    # Navigation edge stream (URL relationships)
    write_edges: bool = False                    # Enable edge stream
    edges_path: Optional[str] = None             # Edge file path
```

## Environment Variables

Crawlit supports configuration through environment variables using the `EnvLoader` utility. Variables can be set directly in the environment or loaded from `.env` files.

### Supported Environment Variables

```bash
# Core crawling configuration
CRAWLIT_START_URL="https://example.com"
CRAWLIT_MAX_DEPTH=5
CRAWLIT_INTERNAL_ONLY=true
CRAWLIT_SAME_PATH_ONLY=false
CRAWLIT_RESPECT_ROBOTS=true
CRAWLIT_MAX_QUEUE_SIZE=1000

# Concurrency settings
CRAWLIT_MAX_WORKERS=4
CRAWLIT_MAX_CONCURRENT_REQUESTS=10

# HTTP configuration
CRAWLIT_USER_AGENT="MyBot/1.0"
CRAWLIT_MAX_RETRIES=3
CRAWLIT_TIMEOUT=30
CRAWLIT_VERIFY_SSL=true
CRAWLIT_PROXY="http://proxy.example.com:8080"

# JavaScript rendering
CRAWLIT_USE_JS_RENDERING=true
CRAWLIT_JS_BROWSER_TYPE="chromium"
CRAWLIT_JS_WAIT_FOR_TIMEOUT=5000

# Rate limiting
CRAWLIT_DELAY=1.0
CRAWLIT_USE_PER_DOMAIN_DELAY=true
CRAWLIT_RESPECT_ROBOTS_CRAWL_DELAY=true

# Output configuration
CRAWLIT_STORE_HTML_CONTENT=true
CRAWLIT_ENABLE_DISK_STORAGE=false
CRAWLIT_STORAGE_DIR="./storage"
CRAWLIT_WRITE_JSONL=true
CRAWLIT_JSONL_PATH="./results.jsonl"
CRAWLIT_WRITE_BLOBS=false
CRAWLIT_BLOBS_DIR="./blobs"

# Feature flags
CRAWLIT_ENABLE_IMAGE_EXTRACTION=true
CRAWLIT_ENABLE_KEYWORD_EXTRACTION=true
CRAWLIT_ENABLE_TABLE_EXTRACTION=true
CRAWLIT_ENABLE_CONTENT_EXTRACTION=true
CRAWLIT_ENABLE_PDF_EXTRACTION=true
CRAWLIT_ENABLE_JS_EMBEDDED_DATA=true

# Budget limits
CRAWLIT_MAX_PAGES=1000
CRAWLIT_MAX_BYTES=104857600  # 100MB
CRAWLIT_MAX_TIME_SECONDS=3600  # 1 hour
```

### Using .env Files

Create a `.env` file in your project directory:

```env
# .env file
CRAWLIT_START_URL=https://example.com
CRAWLIT_MAX_DEPTH=5
CRAWLIT_DELAY=1.0
CRAWLIT_ENABLE_CONTENT_EXTRACTION=true
CRAWLIT_WRITE_JSONL=true
CRAWLIT_JSONL_PATH=./output/results.jsonl
```

Load environment variables in your code:

```python
from crawlit.utils.env_loader import EnvLoader

# Load .env file
loader = EnvLoader('.env')
start_url = loader.get('CRAWLIT_START_URL', 'https://default.com')
max_depth = loader.get('CRAWLIT_MAX_DEPTH', 3, cast=int)
```

## Command Line Arguments

Crawlit provides extensive command-line argument support for all configuration options:

### Basic Arguments

```bash
# Basic crawling
python -m crawlit --url https://example.com --depth 3 --delay 1.0

# Output format and location
python -m crawlit --url https://example.com --output results.json --output-format json

# User agent and timeout
python -m crawlit --url https://example.com --user-agent "MyBot/1.0" --timeout 30
```

### Advanced Arguments

```bash
# JavaScript rendering
python -m crawlit --url https://example.com --use-js --js-browser chromium --js-wait-timeout 5000

# Feature extraction
python -m crawlit --url https://example.com --extract-tables --extract-images --extract-keywords

# Rate limiting and concurrency
python -m crawlit --url https://example.com --delay 2.0 --per-domain-delay --max-workers 4

# Budget limits
python -m crawlit --url https://example.com --max-pages 100 --max-bandwidth-mb 50 --max-time-seconds 1800

# Authentication
python -m crawlit --url https://example.com --auth-user admin --auth-password secret
python -m crawlit --url https://example.com --api-key "abc123" --api-key-header "Authorization"

# Proxy support
python -m crawlit --url https://example.com --proxy "http://proxy.example.com:8080"
```

### Complete Argument List

| Argument | Default | Description |
|----------|---------|-------------|
| `--url`, `-u` | *required* | Target website URL |
| `--depth`, `-d` | 3 | Maximum crawl depth |
| `--output`, `-O` | crawl_results.json | Output file path |
| `--output-format`, `-f` | json | Output format (json, csv, txt, html) |
| `--delay` | 0.1 | Delay between requests (seconds) |
| `--timeout` | 10 | Request timeout (seconds) |
| `--user-agent`, `-a` | crawlit/1.0 | Custom User-Agent string |
| `--allow-external`, `-e` | false | Allow external domain crawling |
| `--ignore-robots`, `-i` | false | Ignore robots.txt rules |
| `--async` | false | Enable asynchronous crawling |
| `--concurrency` | 15 | Max concurrent requests (async) |
| `--max-workers` | 1 | ThreadPoolExecutor workers (sync) |
| `--use-js`, `--javascript` | false | Enable JavaScript rendering |
| `--js-browser` | chromium | Browser type (chromium, firefox, webkit) |
| `--extract-tables`, `-t` | false | Extract HTML tables |
| `--extract-images`, `-img` | false | Extract image information |
| `--extract-keywords`, `-k` | false | Extract keywords |
| `--extract-content`, `-c` | false | Enable content extraction |
| `--proxy` | none | Proxy server URL |
| `--max-pages` | none | Maximum pages to crawl |
| `--max-bandwidth-mb` | none | Bandwidth limit (MB) |
| `--max-time-seconds` | none | Time limit (seconds) |

## Configuration File Formats

### JSON Configuration

Create a JSON configuration file:

```json
{
  "start_url": "https://example.com",
  "max_depth": 5,
  "fetch": {
    "user_agent": "MyBot/1.0",
    "timeout": 30,
    "use_js_rendering": true,
    "js_browser_type": "chromium"
  },
  "rate_limit": {
    "delay": 1.0,
    "use_per_domain_delay": true
  },
  "output": {
    "write_jsonl": true,
    "jsonl_path": "results.jsonl",
    "write_blobs": true,
    "blobs_dir": "blobs"
  },
  "enable_content_extraction": true,
  "enable_table_extraction": true,
  "max_pages": 1000
}
```

Load and use JSON configuration:

```python
import json
from crawlit.config import CrawlerConfig

# Load from JSON file
with open('config.json', 'r') as f:
    config_dict = json.load(f)

# Create config object
config = CrawlerConfig(**config_dict)
```

### YAML Configuration

YAML format for more readable configuration:

```yaml
# crawlit-config.yaml
start_url: "https://example.com"
max_depth: 5
internal_only: true
respect_robots: true

fetch:
  user_agent: "MyBot/1.0"
  timeout: 30
  max_retries: 5
  use_js_rendering: true
  js_browser_type: "chromium"
  js_wait_for_timeout: 3000

rate_limit:
  delay: 1.0
  use_per_domain_delay: true
  respect_robots_crawl_delay: true

output:
  store_html_content: true
  write_jsonl: true
  jsonl_path: "output/results.jsonl"
  write_blobs: true
  blobs_dir: "output/blobs"
  write_edges: true
  edges_path: "output/edges.jsonl"

# Feature flags
enable_content_extraction: true
enable_table_extraction: true
enable_image_extraction: true
enable_keyword_extraction: true
enable_pdf_extraction: true

# Budget limits
max_pages: 1000
max_bytes: 104857600  # 100MB
max_time_seconds: 3600  # 1 hour

# Sitemap support
use_sitemap: true
sitemap_urls:
  - "https://example.com/sitemap.xml"
  - "https://example.com/products-sitemap.xml"
```

## Feature Configuration

### Content Extraction

Configure detailed content extraction:

```python
from crawlit.config import CrawlerConfig
from crawlit.extractors.content_extractor import ContentExtractor

config = CrawlerConfig(
    start_url="https://example.com",
    enable_content_extraction=True,
    enable_dom_features=True
)

# Optional: customize content extractor
content_extractor = ContentExtractor()
# Content extractor uses default patterns but can be subclassed for customization
```

### Table Extraction

Configure table extraction with filtering:

```python
from crawlit.config import CrawlerConfig

config = CrawlerConfig(
    start_url="https://example.com",
    enable_table_extraction=True
)

# CLI equivalent with table-specific options:
# --extract-tables --min-rows 2 --min-columns 3 --tables-format csv
```

### Keyword Extraction

Configure keyword extraction with parameters:

```python
from crawlit.config import CrawlerConfig
from crawlit.extractors.keyword_extractor import KeywordExtractor

config = CrawlerConfig(
    start_url="https://example.com",
    enable_keyword_extraction=True
)

# Customize keyword extractor
keyword_extractor = KeywordExtractor(
    min_word_length=4,    # Minimum word length
    max_keywords=30       # Maximum keywords per page
)
```

### Image Extraction

Configure image extraction and processing:

```python
from crawlit.config import CrawlerConfig

config = CrawlerConfig(
    start_url="https://example.com",
    enable_image_extraction=True
)

# CLI equivalent:
# --extract-images --images-output ./images
```

### PDF Extraction

Enable PDF document processing:

```python
from crawlit.config import CrawlerConfig

config = CrawlerConfig(
    start_url="https://example.com",
    enable_pdf_extraction=True
)

# Requires: pip install pdfplumber
```

### JavaScript Data Extraction

Extract embedded JavaScript data:

```python
from crawlit.config import CrawlerConfig

config = CrawlerConfig(
    start_url="https://example.com",
    enable_js_embedded_data=True,
    fetch=FetchConfig(use_js_rendering=True)
)
```

## Performance Tuning

### Concurrency Configuration

For high-performance crawling:

```python
# Asynchronous crawling (recommended for I/O bound tasks)
from crawlit.crawler.async_engine import AsyncCrawler

config = CrawlerConfig(
    start_url="https://example.com",
    max_concurrent_requests=20,    # Adjust based on target server capacity
    rate_limit=RateLimitConfig(delay=0.1),  # Minimal delay for fast crawling
    fetch=FetchConfig(
        timeout=15,                # Reasonable timeout
        max_retries=2             # Fewer retries for speed
    )
)

crawler = AsyncCrawler(config=config)
```

```python
# Synchronous crawling with thread pool
from crawlit.crawler.engine import Crawler

config = CrawlerConfig(
    start_url="https://example.com",
    max_workers=8,                # Adjust based on CPU cores
    rate_limit=RateLimitConfig(
        delay=0.5,
        use_per_domain_delay=True
    )
)

crawler = Crawler(config=config)
```

### Memory Optimization

For large crawls, optimize memory usage:

```python
config = CrawlerConfig(
    start_url="https://example.com",
    enable_content_deduplication=True,  # Avoid duplicate content
    output=OutputConfig(
        store_html_content=False,       # Don't store HTML in memory
        enable_disk_storage=True,       # Use disk storage
        storage_dir="./storage",
        write_jsonl=True,               # Stream results to disk
        jsonl_path="./results.jsonl"
    ),
    max_queue_size=1000                 # Limit queue size
)
```

### Bandwidth Optimization

Minimize bandwidth usage:

```python
config = CrawlerConfig(
    start_url="https://example.com",
    max_bytes=52428800,                 # 50MB limit
    fetch=FetchConfig(
        timeout=10,                     # Fast timeout
        max_retries=1                   # Minimal retries
    ),
    enable_incremental=True             # Skip unchanged pages
)
```

## Configuration Examples

### Simple Blog Crawling

```python
from crawlit.config import CrawlerConfig, FetchConfig, OutputConfig

# Basic blog crawling with content extraction
config = CrawlerConfig(
    start_url="https://blog.example.com",
    max_depth=3,
    internal_only=True,
    enable_content_extraction=True,
    enable_keyword_extraction=True,
    output=OutputConfig(
        write_jsonl=True,
        jsonl_path="blog_content.jsonl"
    )
)
```

### E-commerce Site Crawling

```python
# E-commerce with table and image extraction
config = CrawlerConfig(
    start_url="https://shop.example.com",
    max_depth=4,
    enable_table_extraction=True,      # Product specifications
    enable_image_extraction=True,      # Product images
    enable_content_extraction=True,    # Product descriptions
    use_sitemap=True,                  # Discover products via sitemap
    rate_limit=RateLimitConfig(delay=2.0),  # Be respectful
    max_pages=5000
)
```

### JavaScript-Heavy SPA Crawling

```python
# Single Page Application with JavaScript rendering
config = CrawlerConfig(
    start_url="https://spa.example.com",
    max_depth=2,
    fetch=FetchConfig(
        use_js_rendering=True,
        js_browser_type="chromium",
        js_wait_for_timeout=5000,
        timeout=30
    ),
    enable_js_embedded_data=True,
    rate_limit=RateLimitConfig(delay=3.0)  # Longer delay for JS rendering
)
```

### Large-Scale Academic Crawling

```python
# Academic paper repository with PDF extraction
config = CrawlerConfig(
    start_url="https://papers.example.edu",
    max_depth=5,
    enable_pdf_extraction=True,
    enable_content_extraction=True,
    enable_content_deduplication=True,
    output=OutputConfig(
        enable_disk_storage=True,
        storage_dir="./academic_storage",
        write_jsonl=True,
        jsonl_path="./papers.jsonl",
        write_blobs=True,
        blobs_dir="./pdf_blobs"
    ),
    max_pages=10000,
    max_time_seconds=14400  # 4 hours
)
```

### Enterprise Distributed Crawling

```python
# High-performance enterprise crawling
config = CrawlerConfig(
    start_url="https://enterprise.example.com",
    max_depth=6,
    max_concurrent_requests=50,
    enable_content_extraction=True,
    enable_table_extraction=True,
    enable_image_extraction=True,
    enable_incremental=True,            # Resume capability
    output=OutputConfig(
        enable_disk_storage=True,
        write_jsonl=True,
        write_edges=True,               # URL relationship tracking
        write_blobs=True
    ),
    rate_limit=RateLimitConfig(
        delay=0.1,
        use_per_domain_delay=True
    ),
    max_pages=100000,
    max_bytes=1073741824,               # 1GB
    max_time_seconds=86400              # 24 hours
)
```

## Advanced Patterns

### Configuration Inheritance

Create base configurations and extend them:

```python
from crawlit.config import CrawlerConfig, FetchConfig, OutputConfig

# Base configuration
base_config = CrawlerConfig(
    max_depth=3,
    internal_only=True,
    fetch=FetchConfig(
        user_agent="MyBot/1.0",
        timeout=30
    ),
    output=OutputConfig(
        write_jsonl=True,
        store_html_content=False
    )
)

# Specialized for news sites
news_config = CrawlerConfig(
    **{**base_config.__dict__, **{
        'start_url': 'https://news.example.com',
        'enable_content_extraction': True,
        'enable_keyword_extraction': True,
        'max_pages': 1000
    }}
)

# Specialized for e-commerce
ecommerce_config = CrawlerConfig(
    **{**base_config.__dict__, **{
        'start_url': 'https://shop.example.com',
        'enable_table_extraction': True,
        'enable_image_extraction': True,
        'use_sitemap': True
    }}
)
```

### Dynamic Configuration

Build configurations dynamically based on site analysis:

```python
import requests
from urllib.parse import urljoin, urlparse
from crawlit.config import CrawlerConfig, FetchConfig

def create_adaptive_config(start_url: str) -> CrawlerConfig:
    """Create configuration adapted to the target site"""
    
    # Analyze robots.txt
    robots_url = urljoin(start_url, '/robots.txt')
    try:
        robots_response = requests.get(robots_url, timeout=10)
        crawl_delay = extract_crawl_delay(robots_response.text)
    except:
        crawl_delay = 1.0
    
    # Check for sitemap
    has_sitemap = 'sitemap:' in robots_response.text.lower()
    
    # Detect if site likely uses JavaScript
    try:
        page_response = requests.get(start_url, timeout=10)
        needs_js = 'spa' in page_response.text.lower() or 'react' in page_response.text.lower()
    except:
        needs_js = False
    
    return CrawlerConfig(
        start_url=start_url,
        max_depth=4 if has_sitemap else 3,
        use_sitemap=has_sitemap,
        fetch=FetchConfig(
            use_js_rendering=needs_js,
            timeout=30 if needs_js else 15
        ),
        rate_limit=RateLimitConfig(delay=max(crawl_delay, 1.0)),
        enable_content_extraction=True
    )

def extract_crawl_delay(robots_content: str) -> float:
    """Extract crawl delay from robots.txt"""
    for line in robots_content.split('\n'):
        if 'crawl-delay:' in line.lower():
            try:
                return float(line.split(':')[1].strip())
            except:
                pass
    return 1.0
```

### Configuration Validation

Implement configuration validation for production use:

```python
from crawlit.config import CrawlerConfig
from typing import List

def validate_config(config: CrawlerConfig) -> List[str]:
    """Validate configuration and return list of issues"""
    issues = []
    
    if not config.start_url:
        issues.append("start_url is required")
    
    if config.max_depth < 1:
        issues.append("max_depth must be >= 1")
    
    if config.rate_limit.delay < 0:
        issues.append("delay must be >= 0")
    
    if config.fetch.timeout < 1:
        issues.append("timeout must be >= 1")
    
    if config.fetch.use_js_rendering and config.rate_limit.delay < 1.0:
        issues.append("JS rendering requires delay >= 1.0 for stability")
    
    if config.max_concurrent_requests > 100:
        issues.append("max_concurrent_requests > 100 may overwhelm target server")
    
    if config.output.write_jsonl and not config.output.jsonl_path:
        issues.append("write_jsonl=True requires jsonl_path")
    
    return issues

# Usage
config = CrawlerConfig(start_url="https://example.com")
issues = validate_config(config)
if issues:
    print("Configuration issues:")
    for issue in issues:
        print(f"  - {issue}")
```

### Environment-Specific Configurations

Use different configurations for development, staging, and production:

```python
import os
from crawlit.config import CrawlerConfig, FetchConfig, RateLimitConfig

def get_config_for_environment() -> CrawlerConfig:
    """Get configuration based on environment"""
    
    env = os.getenv('ENVIRONMENT', 'development')
    
    if env == 'development':
        return CrawlerConfig(
            start_url="https://dev.example.com",
            max_depth=2,
            max_pages=100,
            rate_limit=RateLimitConfig(delay=0.5),
            fetch=FetchConfig(timeout=10),
            output=OutputConfig(write_jsonl=True, jsonl_path="dev_results.jsonl")
        )
    
    elif env == 'staging':
        return CrawlerConfig(
            start_url="https://staging.example.com",
            max_depth=3,
            max_pages=1000,
            rate_limit=RateLimitConfig(delay=1.0),
            fetch=FetchConfig(timeout=20),
            enable_content_extraction=True
        )
    
    elif env == 'production':
        return CrawlerConfig(
            start_url="https://example.com",
            max_depth=5,
            max_pages=10000,
            rate_limit=RateLimitConfig(delay=2.0, use_per_domain_delay=True),
            fetch=FetchConfig(timeout=30, max_retries=5),
            enable_content_extraction=True,
            enable_content_deduplication=True,
            output=OutputConfig(
                enable_disk_storage=True,
                write_jsonl=True,
                write_blobs=True
            )
        )
    
    else:
        raise ValueError(f"Unknown environment: {env}")
```

## Best Practices

### 1. Start Conservative, Scale Up

Begin with conservative settings and gradually increase based on target server capacity:

```python
# Start with conservative settings
initial_config = CrawlerConfig(
    start_url="https://example.com",
    max_depth=2,
    max_pages=100,
    rate_limit=RateLimitConfig(delay=2.0),
    fetch=FetchConfig(timeout=10, max_retries=2)
)

# Scale up after testing
production_config = CrawlerConfig(
    start_url="https://example.com",
    max_depth=5,
    max_pages=10000,
    rate_limit=RateLimitConfig(delay=1.0),
    fetch=FetchConfig(timeout=30, max_retries=5)
)
```

### 2. Use Appropriate Output Formats

Choose output formats based on your data processing pipeline:

```python
# For streaming processing
streaming_config = OutputConfig(
    write_jsonl=True,
    jsonl_path="stream_results.jsonl",
    store_html_content=False    # Save memory
)

# For batch processing
batch_config = OutputConfig(
    write_blobs=True,
    blobs_dir="./html_blobs",
    write_edges=True,
    edges_path="./navigation.jsonl"
)
```

### 3. Monitor and Adjust

Include monitoring and adaptive configuration:

```python
from crawlit.utils.budget_tracker import BudgetTracker

def create_monitored_config(start_url: str) -> CrawlerConfig:
    def budget_callback(reason: str, stats: dict):
        print(f"Budget limit reached: {reason}")
        print(f"Crawled {stats['pages_crawled']} pages, {stats['mb_downloaded']:.1f}MB")
    
    return CrawlerConfig(
        start_url=start_url,
        max_pages=1000,
        max_bytes=104857600,  # 100MB
        enable_content_extraction=True,
        budget_callback=budget_callback
    )
```

### 4. Handle Errors Gracefully

Configure robust error handling:

```python
config = CrawlerConfig(
    start_url="https://example.com",
    fetch=FetchConfig(
        max_retries=3,
        timeout=30,
        verify_ssl=True    # Enable SSL verification
    ),
    rate_limit=RateLimitConfig(
        delay=1.0,
        respect_robots_crawl_delay=True
    )
)
```

### 5. Document Your Configuration

Always document configuration choices:

```python
# Enterprise news crawler configuration
# Updated: 2024-01-15
# Purpose: Extract articles and metadata from news sites
config = CrawlerConfig(
    start_url="https://news.example.com",
    max_depth=4,                    # Articles typically 2-3 levels deep
    max_pages=5000,                 # Daily article limit
    enable_content_extraction=True,  # Need article text and metadata
    enable_keyword_extraction=True,  # For content categorization
    rate_limit=RateLimitConfig(
        delay=1.5,                  # Respectful crawling per robots.txt
        respect_robots_crawl_delay=True
    ),
    fetch=FetchConfig(
        user_agent="NewsBot/1.0 (contact@company.com)",  # Identify ourselves
        timeout=30,                 # News sites can be slow
        max_retries=3
    ),
    output=OutputConfig(
        write_jsonl=True,
        jsonl_path="./output/news_articles.jsonl",
        enable_disk_storage=True,   # Large volume of content
        storage_dir="./storage/news"
    )
)
```

This comprehensive configuration documentation should help you set up crawlit for any web crawling scenario, from simple content extraction to large-scale enterprise data collection.