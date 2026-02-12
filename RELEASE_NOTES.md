# Crawlit Release Notes

## Version 0.2.0 (February 2026)

We are excited to announce version 0.2.0 of Crawlit with major enhancements and new features!

### 🎉 Major New Features

#### Advanced Extraction Features (NEW in 0.2.0)
- **Form Detection & Extraction**: Comprehensive form analysis with intelligent field detection
  - All form attributes (action, method, enctype, id, class, name)
  - All field types (text, email, password, select, textarea, radio, checkbox, file, etc.)
  - Label association (explicit via 'for' attribute and implicit parent labels)
  - Field attributes (required, readonly, disabled, maxlength, pattern, placeholder)
  - Special feature detection (CSRF tokens, file uploads, CAPTCHA)
  - Heuristic detection (login forms, search forms, contact forms)
  - Submit button text extraction
  - Fieldset extraction
- **Structured Data Extraction**: Extract rich semantic data from web pages
  - **JSON-LD**: Schema.org markup (recommended by Google)
  - **Microdata**: HTML5 embedded structured data
  - **RDFa**: Resource Description Framework in Attributes
  - **Open Graph Protocol**: Facebook/social media metadata
  - **Twitter Cards**: Twitter-specific metadata
  - Schema.org type detection and filtering
  - Nested item support
  - Multiple formats on same page
- **Advanced Language Detection**: Multi-method language identification
  - 6 detection methods: HTML lang, meta tags, URL patterns, character analysis, common words, title/meta
  - Support for 15+ languages (en, es, fr, de, it, pt, nl, ru, ja, zh, ar, pl, tr, sv, ko, etc.)
  - Character-based detection for non-Latin scripts (Japanese, Arabic, Russian, Chinese, Korean, etc.)
  - Common words frequency analysis
  - Weighted voting algorithm for high accuracy
  - Confidence scoring (0.0 to 1.0)
  - Multilingual page detection

#### Security Features (NEW in 0.2.0)
- **CSRF Token Handling**: Automatic extraction and management of CSRF tokens from forms, meta tags, and JavaScript
  - Support for 10+ frameworks (Django, Rails, ASP.NET, WordPress, Laravel, Drupal, etc.)
  - Automatic token inclusion in POST requests and headers
  - Global and per-URL token management
  - Statistics and monitoring
- **Security Headers Analysis**: Comprehensive analysis of 10+ security headers with ratings
  - HSTS, CSP, X-Frame-Options, X-Content-Type-Options, and more
  - Security ratings from A+ (Excellent) to F (Critical)
  - Vulnerability detection and specific recommendations
  - Detailed header-by-header analysis
- **WAF Detection**: Detect 17+ Web Application Firewalls
  - Cloudflare, AWS WAF, Akamai, Incapsula, ModSecurity, F5 BIG-IP, and more
  - Multi-method detection (headers, cookies, body patterns, server signatures)
  - Confidence scoring and detailed indicators
  - Adaptive crawling recommendations
- **Honeypot Detection**: Identify and avoid honeypot traps
  - 7 detection methods (invisible, hidden, off-screen, transparent, zero-dimension, etc.)
  - Risk level assessment (High, Medium, Low, None)
  - Confidence scoring for each detected honeypot
  - Actionable recommendations to avoid detection

#### Distributed Crawling & Performance (NEW in 0.2.0)
- **Message Queue Integration**: RabbitMQ and Apache Kafka support for distributed task management
- **Distributed Crawler**: Scale crawling across multiple machines and processes
- **Worker Pools**: Concurrent task processing with configurable worker count
- **Connection Pooling**: Reuse database and HTTP connections for 5-10x performance improvement
- **Automatic Scaling**: Dynamic worker management and load distribution
- **Fault Tolerance**: Task persistence, auto-recovery, and retry mechanisms
- **Enterprise Scale**: Handle thousands of URLs per second
- **Multi-Machine Support**: Deploy coordinator and workers on separate servers
- **Real-Time Monitoring**: Track progress, statistics, and worker health

#### Database Integration (NEW in 0.2.0)
- **Multiple Database Backends**: Built-in support for SQLite, PostgreSQL, and MongoDB
- **SQLite**: Zero-configuration database perfect for local development (no external dependencies)
- **PostgreSQL**: Production-ready relational database with ACID compliance and advanced querying
- **MongoDB**: Flexible document storage for unstructured/semi-structured data
- **Query Support**: Filter results by URL, status code, success/failure, crawl ID
- **Metadata Tracking**: Store crawl configuration, statistics, and custom metadata
- **Crawl History**: Track multiple crawl sessions with timestamps and statistics
- **Easy Cleanup**: Delete specific crawls or clear all data
- **CLI Support**: Full command-line interface support with `--database` flag
- **Factory Pattern**: Flexible backend selection via configuration

#### JavaScript Rendering (NEW in 0.2.0)
- **Full SPA Support**: Crawl Single Page Applications built with React, Vue, Angular, Svelte, and more
- **Playwright Integration**: Support for Chromium, Firefox, and Webkit browser engines
- **Smart Waiting**: Wait for specific selectors or timeouts to ensure content is fully loaded
- **Sync & Async Support**: Works with both synchronous and asynchronous crawlers
- **Configurable Browsers**: Choose between different browser engines for testing
- **Headless Mode**: Fast, resource-efficient crawling with headless browsers
- **CLI Support**: Full command-line interface support with `--use-js` flag

#### Reliability & Performance
- **Exponential Backoff**: Intelligent retry logic with exponential backoff (2^retry, capped at 32s) for failed requests
- **Configurable Retries**: Customizable retry attempts with smart failure handling

#### Content Extraction (Initial 0.2.0 Features)
- **Image Extraction**: Extract and analyze images including metadata, dimensions, and accessibility information
  - New `image_extractor.py` module with `ImageTagParser` class
  - Support for image metadata (src, alt, width, height, etc.)
  - Decorative image identification for accessibility checking
  - Parent element context for better image understanding

- **Table Extraction**: Enhanced capabilities for extracting complex HTML tables
  - Support for complex table structures with rowspan and colspan
  - Multiple output formats (CSV, JSON, dictionaries)
  - Configurable minimum rows and columns

- **Keyword Extraction**: Extract and rank important terms from page content
  - Stop word filtering and customizable word length
  - Smart content weighting based on HTML structure
  - Keyphrase extraction for multi-word terms
  - Relevance scoring

- **Content Extraction**: Unified content extraction module
  - Metadata extraction (title, description, headings, canonical URLs)
  - Page type detection
  - Image context extraction
  - Optional extraction for performance optimization

#### Enhanced Authentication & Session Management
- **Expanded Authentication Options**: Support for OAuth tokens, API keys, Basic/Digest authentication, and custom headers
- **Dynamic Authentication**: Update authentication credentials during runtime
- **Session Persistence**: Improved cookie and session management

#### Advanced Rate Limiting
- **Per-Domain Rate Limiting**: Independent rate limits for each domain
- **Automatic Crawl-Delay Extraction**: Automatically respect `Crawl-delay` directives from robots.txt
- **Flexible Configuration**: Set custom delays per domain or use global defaults

#### Content Management
- **Page Caching**: Memory and disk-based caching with TTL support
- **Crawl Resume**: Save and resume interrupted crawls
- **Storage Management**: Optional HTML content storage (memory or disk-based) for memory optimization
- **Content Deduplication**: Skip pages with duplicate content using SHA-256 hashing with normalization

#### Sitemap Support
- **Automatic Discovery**: Discover sitemaps from robots.txt
- **Sitemap Parsing**: Parse XML sitemaps and sitemap index files
- **URL Extraction**: Extract URLs and metadata from sitemaps
- **Integration**: Seamlessly integrate sitemap URLs into crawl queue

#### Enhanced Logging
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Log Rotation**: Size-based and time-based log rotation
- **Configurable Levels**: Set different log levels per module
- **Contextual Logging**: Include function names, line numbers, and custom context

#### Progress Tracking
- **Real-time Monitoring**: Track crawl progress with callbacks
- **Statistics**: Get detailed statistics (crawled, failed, total URLs)
- **Integration**: Fully integrated into crawler engines

#### URL Filtering
- **Pattern Matching**: Filter URLs using regex patterns
- **Extension Filtering**: Allow or block specific file extensions
- **Query Parameter Filtering**: Filter based on query parameters
- **Factory Methods**: Pre-configured filters (HTML-only, exclude media, etc.)

#### Queue Management
- **Pause/Resume**: Pause and resume crawling operations
- **State Persistence**: Save and load crawl state
- **Queue Statistics**: Get detailed queue statistics
- **Size Limits**: Configure maximum queue size

#### Threading Support
- **Multi-threaded Crawling**: Thread pool support for concurrent requests in sync crawler
- **Configurable Workers**: Set number of worker threads
- **Thread Safety**: All operations are thread-safe

#### Optional Content Extraction
- **Performance Optimization**: Content extraction is now optional (disabled by default)
- **On-Demand Extraction**: Enable only when needed to improve performance

### 🔧 Improvements

- **Robots.txt Enhancement**: Extract and respect `Crawl-delay` directives
- **Error Handling**: Improved error handling with custom exceptions
- **Type Hints**: Added comprehensive type hints throughout the codebase
- **Code Organization**: Better modularity and separation of concerns
- **Backward Compatibility**: All changes maintain backward compatibility
- Updated documentation with examples for all new features
- New examples demonstrating each feature
- Extended CLI with options for new extraction capabilities

### 📚 Documentation

- Updated README with comprehensive feature documentation
- Added examples for all new features
- Enhanced API documentation
- Updated release notes
- Added documentation for the extractors module

### 🐛 Bug Fixes

- Fixed exception handling in async fetcher
- Fixed sitemap test issues
- Fixed content extraction tests
- Fixed table extraction CLI test
- Fixed URL canonicalization test

### 🔄 Migration Guide

#### For Basic Users
No changes required! All existing code continues to work.

#### For Advanced Users

**New Optional Parameters:**
```python
# Old way (still works)
crawler = Crawler(start_url="https://example.com", max_depth=3)

# New way (with optional features)
crawler = Crawler(
    start_url="https://example.com",
    max_depth=3,
    enable_content_extraction=True,  # Now optional
    use_sitemap=True,  # New feature
    max_workers=4,  # New threading support
    use_per_domain_delay=True  # New rate limiting
)
```

**Content Extraction:**
Content extraction is now disabled by default. To enable:
```python
crawler = Crawler(
    start_url="https://example.com",
    enable_content_extraction=True  # Enable if needed
)
```

**JavaScript Rendering (NEW):**
For Single Page Applications and JavaScript-heavy sites:
```python
crawler = Crawler(
    start_url="https://react-app.com",
    use_js_rendering=True,  # Enable JavaScript rendering
    js_browser_type="chromium",  # chromium, firefox, or webkit
    js_wait_for_selector="#root"  # Optional: wait for specific element
)
```

Install Playwright for JavaScript rendering:
```bash
pip install playwright
python -m playwright install chromium
```

**Rate Limiting:**
```python
from crawlit import RateLimiter

rate_limiter = RateLimiter(default_delay=0.5)
rate_limiter.set_domain_delay("example.com", 1.0)

crawler = Crawler(
    start_url="https://example.com",
    rate_limiter=rate_limiter,
    use_per_domain_delay=True
)
```

---

## Version 0.1.0 (May 2025)

We are pleased to announce the first public release of Crawlit - a modular, ethical Python web crawler.

### Features

- **Modular Architecture**: Easily extend with custom modules and parsers
- **Ethical Crawling**: Configurable robots.txt compliance and rate limiting
- **Depth Control**: Set maximum crawl depth to prevent excessive resource usage
- **Domain Filtering**: Restrict crawling to specific domains or subdomains
- **Robust Error Handling**: Gracefully manage connection issues and malformed pages
- **Multiple Output Formats**: Export results as JSON, CSV, or plain text
- **Detailed Logging**: Comprehensive logging of all crawler activities
- **Command Line Interface**: Simple, powerful CLI for easy usage
- **Programmatic API**: Use as a library in your own Python code

### Installation

```bash
# Install the core library
pip install crawlit

# Install with CLI tool support
pip install crawlit[cli]
```

### Documentation

Comprehensive API documentation is now available in the `docs` directory. To build and view the documentation:

```bash
# Install Sphinx and required packages
pip install sphinx sphinx_rtd_theme sphinxcontrib-napoleon

# Build the documentation
cd docs
make html  # On Windows: make.bat html

# View the documentation
# Open docs/_build/html/index.html in your browser
```

### Known Issues

- Limited support for JavaScript-rendered content
- No advanced request throttling based on domain (fixed in v0.2.0)

### Acknowledgments

Thanks to all the early testers and contributors who helped make this release possible.
