# Crawlit Release Notes

## Version 0.2.0 (February 2026)

We are excited to announce version 0.2.0 of Crawlit with major enhancements and new features!

### 🎉 Major New Features

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
