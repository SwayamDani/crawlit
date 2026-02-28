# Getting Started with crawlit

## Overview

crawlit is a powerful, modular web crawler designed for ethical and efficient web scraping. This guide will help you get started with your first crawl and understand the core concepts.

## Installation

### Quick Install

```bash
# Basic installation
pip install crawlit

# With JavaScript rendering support
pip install crawlit[js]
python -m playwright install chromium

# Full installation with all features
pip install crawlit[all]
```

### Development Installation

```bash
git clone https://github.com/SwayamDani/crawlit.git
cd crawlit
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .[all]
```

## Your First Crawl

### Python API - Basic Example

```python
from crawlit import Crawler

# Create a crawler instance
crawler = Crawler(
    start_url="https://example.com",
    max_depth=2,
    internal_only=True,
    respect_robots=True
)

# Start crawling
crawler.crawl()

# Get results
results = crawler.get_results()
print(f"Crawled {len(results)} pages")

# Access page data
for page in results:
    print(f"URL: {page.url}")
    print(f"Title: {page.metadata.get('title', 'N/A')}")
    print(f"Status: {page.http.status_code}")
    print("---")
```

### Command Line - Basic Example

```bash
# Simple crawl with JSON output
crawlit --url https://example.com --depth 2 --output results.json

# Crawl with table and keyword extraction
crawlit --url https://example.com --extract-tables --extract-keywords --summary

# View help for all options
crawlit --help
```

## Core Concepts

### 1. Crawler vs AsyncCrawler

crawlit provides both synchronous and asynchronous crawling engines:

```python
# Synchronous (simpler, good for most use cases)
from crawlit import Crawler
crawler = Crawler(start_url="https://example.com")
crawler.crawl()

# Asynchronous (better performance for large crawls)
import asyncio
from crawlit import AsyncCrawler

async def main():
    crawler = AsyncCrawler(start_url="https://example.com", max_concurrent_requests=10)
    await crawler.crawl()

asyncio.run(main())
```

### 2. Configuration

Three ways to configure crawlit:

```python
# 1. Constructor parameters
crawler = Crawler(
    start_url="https://example.com",
    max_depth=3,
    delay=1.0,
    user_agent="MyBot/1.0"
)

# 2. Config object (recommended for complex setups)
from crawlit import CrawlerConfig, FetchConfig, RateLimitConfig

config = CrawlerConfig(
    start_url="https://example.com",
    max_depth=3,
    fetch=FetchConfig(timeout=30, user_agent="MyBot/1.0"),
    rate_limit=RateLimitConfig(delay=1.0, per_domain=True)
)
crawler = Crawler(config=config)

# 3. CLI arguments
# crawlit --url https://example.com --depth 3 --delay 1.0 --user-agent "MyBot/1.0"
```

### 3. Extractors

Extractors are responsible for pulling specific data from web pages:

```python
# Enable built-in extractors
crawler = Crawler(
    start_url="https://example.com",
    enable_table_extraction=True,      # Extract HTML tables
    enable_keyword_extraction=True,    # Extract keywords/phrases
    enable_image_extraction=True,      # Extract image metadata
    enable_form_extraction=True,       # Analyze forms
    enable_structured_data_extraction=True  # JSON-LD, microdata, etc.
)
```

### 4. Page Artifacts

All crawled data is stored in `PageArtifact` objects:

```python
results = crawler.get_results()
for page in results:
    # Basic page info
    print(f"URL: {page.url}")
    print(f"Title: {page.metadata.get('title')}")
    print(f"Status: {page.http.status_code}")
    
    # Extracted data
    if page.tables:
        print(f"Found {len(page.tables)} tables")
    
    if page.keywords:
        print(f"Top keywords: {page.keywords[:5]}")
    
    if page.images:
        print(f"Found {len(page.images)} images")
```

## Ethical Crawling

crawlit is designed with ethical crawling in mind:

### Robots.txt Compliance

```python
# Automatically respect robots.txt (default: True)
crawler = Crawler(
    start_url="https://example.com",
    respect_robots=True,  # Follow robots.txt rules
    crawl_delay=None      # Use delay specified in robots.txt
)
```

### Rate Limiting

```python
# Configure delays to be respectful
crawler = Crawler(
    start_url="https://example.com",
    delay=1.0,           # 1 second between requests
    per_domain_delay=True, # Per-domain rate limiting
    max_budget_pages=1000  # Limit total pages crawled
)
```

### User Agent

```python
# Always identify your crawler
crawler = Crawler(
    start_url="https://example.com",
    user_agent="MyCompany-Crawler/1.0 (+https://mycompany.com/crawler.html)"
)
```

## Common Patterns

### 1. E-commerce Product Crawling

```python
from crawlit import Crawler

crawler = Crawler(
    start_url="https://shop.example.com",
    max_depth=3,
    internal_only=True,
    enable_structured_data_extraction=True,  # Product schema
    enable_image_extraction=True,            # Product images
    delay=2.0,  # Be respectful
    user_agent="ProductBot/1.0 (+https://mycompany.com/bot)"
)

crawler.crawl()
results = crawler.get_results()

for page in results:
    if page.structured_data:
        for schema in page.structured_data:
            if schema.get('@type') == 'Product':
                print(f"Product: {schema.get('name')}")
                print(f"Price: {schema.get('offers', {}).get('price')}")
```

### 2. News Site Analysis

```python
crawler = Crawler(
    start_url="https://news.example.com",
    max_depth=2,
    enable_keyword_extraction=True,
    enable_language_detection=True,
    same_path_only=True,  # Stay in news section
    delay=1.0
)

crawler.crawl()
results = crawler.get_results()

for page in results:
    if page.keywords:
        print(f"Article: {page.metadata.get('title')}")
        print(f"Top keywords: {[kw['keyword'] for kw in page.keywords[:5]]}")
        print(f"Language: {page.metadata.get('language')}")
```

### 3. JavaScript-Heavy SPA

```python
from crawlit import Crawler

# For React, Vue, Angular, etc.
crawler = Crawler(
    start_url="https://spa.example.com",
    use_js=True,
    js_wait_selector="#app",  # Wait for app to load
    js_wait_timeout=10000,    # 10 seconds max wait
    max_depth=2
)

crawler.crawl()
results = crawler.get_results()
```

## Output Formats

### JSON Output (default)

```python
crawler.save_results("results.json", format="json")
```

### CSV for Tables

```python
# Save extracted tables as CSV
crawler = Crawler(
    start_url="https://example.com",
    enable_table_extraction=True
)
crawler.crawl()
crawler.save_results("results.json", format="json")

# Tables are automatically saved as CSV files
```

### Database Storage

```python
# SQLite (built-in)
crawler = Crawler(
    start_url="https://example.com",
    database="sqlite",
    db_path="crawl.db"
)

# PostgreSQL
crawler = Crawler(
    start_url="https://example.com",
    database="postgresql",
    db_connection_string="postgresql://user:pass@localhost/crawlit"
)
```

## Next Steps

Now that you understand the basics:

1. **Explore [Configuration](configuration.md)** - Learn about all configuration options
2. **Check [Extractors](extractors.md)** - Dive deep into data extraction features  
3. **Read [CLI Reference](cli-reference.md)** - Complete command-line documentation
4. **Try [Async Crawling](async-crawling.md)** - Scale up with asynchronous crawling
5. **Build [Plugins](plugins.md)** - Create custom extractors and pipelines

## Need Help?

- Check the [API Reference](api-reference.md) for detailed class documentation
- Review [examples](../examples/) in the repository
- Open issues on [GitHub](https://github.com/SwayamDani/crawlit) for bugs or feature requests