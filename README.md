# crawlit - Modular, Ethical Python Web Crawler

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/SwayamDani/crawlit)

A powerful, modular, and ethical web crawler built in Python. Designed for web scraping, link extraction, content analysis, and website structure mapping with a focus on clean architecture, extensibility, and responsible crawling practices.

---

## Features

### Core Crawling
- **Sync & Async Engines** -- Both `Crawler` (synchronous) and `AsyncCrawler` (asynchronous) with identical APIs
- **JavaScript Rendering** -- Full SPA support (React, Vue, Angular) via Playwright with Chromium, Firefox, and WebKit
- **Depth & Domain Control** -- Max depth, internal-only, same-path-only crawling modes
- **Breadth-First Discovery** -- BFS crawling with configurable priority strategies
- **Multi-threaded** -- Thread pool support for concurrent requests in the sync crawler
- **Sitemap Discovery** -- Automatic sitemap parsing from robots.txt

### Ethical Crawling
- **Robots.txt Compliance** -- Automatic robots.txt respect with crawl-delay extraction
- **Per-Domain Rate Limiting** -- Global and per-domain delays with dynamic adjustment
- **Budget Tracking** -- Enforce limits on pages, bandwidth, and crawl time
- **Content Deduplication** -- SHA-256 based duplicate detection

### Data Extraction
- **HTML Tables** -- Complex table extraction with rowspan/colspan support, CSV/JSON export
- **Images** -- Image metadata extraction with surrounding text context
- **Keywords** -- Frequency-scored keyword and keyphrase extraction with heading priority
- **Forms** -- Full form analysis with field types, validation rules, CSRF/CAPTCHA detection
- **Structured Data** -- JSON-LD, Microdata, and RDFa extraction
- **Language Detection** -- Multi-method language identification
- **PDF Text** -- PDF text and table extraction with optional OCR
- **JS-Embedded Data** -- Extract `window.__data__` and inline JSON from script tags

### Security Analysis
- **Security Headers** -- HTTP security header scoring (HSTS, CSP, X-Frame-Options, etc.)
- **WAF Detection** -- Detect Cloudflare, AWS WAF, Akamai, Sucuri, Imperva, and more
- **CAPTCHA Detection** -- Identify reCAPTCHA v2/v3, hCaptcha, Cloudflare challenges
- **Honeypot Detection** -- Identify hidden honeypot form fields
- **CSRF Token Handling** -- Automatic CSRF token extraction and injection

### Data Persistence
- **Multiple Export Formats** -- JSON, CSV, TXT, HTML, JSONL
- **Database Storage** -- SQLite (built-in), PostgreSQL, MongoDB
- **Artifact Store** -- Structured output with blobs, edges, and event logs
- **Page Caching** -- Memory and disk-based caching with TTL
- **Crawl Resume** -- Save and restore crawl state for long-running jobs

### Extensibility
- **Plugin Architecture** -- Custom extractors, pipelines, fetchers, and priority strategies
- **Content Router** -- Route different content types to specialized handlers
- **Event Logging** -- Structured JSONL event stream for monitoring and debugging
- **Distributed Crawling** -- Scale with RabbitMQ or Apache Kafka message queues

---

## Installation

### From PyPI

```bash
# Core library
pip install crawlit

# With JavaScript rendering
pip install crawlit[js]
python -m playwright install chromium

# With database support
pip install crawlit[postgresql]
pip install crawlit[mongodb]

# With PDF extraction
pip install crawlit[pdf]

# With distributed crawling
pip install crawlit[rabbitmq]
pip install crawlit[kafka]

# With scheduled crawling
pip install crawlit[scheduler]

# Everything
pip install crawlit[all]
```

### From Source

```bash
git clone https://github.com/SwayamDani/crawlit.git
cd crawlit
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

---

## Quick Start

### Python API

```python
from crawlit import Crawler

crawler = Crawler(
    start_url="https://example.com",
    max_depth=3,
    internal_only=True,
    respect_robots=True
)
crawler.crawl()
results = crawler.get_results()
print(f"Crawled {len(results)} pages")
```

### Async Crawling

```python
import asyncio
from crawlit import AsyncCrawler

async def main():
    crawler = AsyncCrawler(
        start_url="https://example.com",
        max_depth=3,
        max_concurrent_requests=10
    )
    await crawler.crawl()
    results = await crawler.get_results()

asyncio.run(main())
```

### Command Line

```bash
# Basic crawl
crawlit --url https://example.com --depth 3 --output results.json

# With table and keyword extraction
crawlit --url https://example.com --extract-tables --extract-keywords --summary

# JavaScript-rendered SPA
crawlit --url https://react-app.com --use-js --js-wait-selector "#root"

# Async with concurrency
crawlit --url https://example.com --async --concurrency 15

# Save to database
crawlit --url https://example.com --database sqlite --db-path results.db
```

---

## Configuration

crawlit supports three configuration approaches:

### 1. Constructor Parameters

```python
crawler = Crawler(
    start_url="https://example.com",
    max_depth=5,
    delay=0.5,
    user_agent="MyBot/1.0",
    enable_table_extraction=True,
    enable_keyword_extraction=True
)
```

### 2. Config Object

```python
from crawlit import CrawlerConfig, FetchConfig, RateLimitConfig

config = CrawlerConfig(
    start_url="https://example.com",
    max_depth=5,
    fetch=FetchConfig(timeout=15, user_agent="MyBot/1.0"),
    rate_limit=RateLimitConfig(delay=0.5),
    enable_table_extraction=True
)
crawler = Crawler(config=config)
```

### 3. CLI Arguments

```bash
crawlit --url https://example.com --depth 5 --delay 0.5 --user-agent "MyBot/1.0" --extract-tables
```

---

## Plugin Architecture

crawlit is built around a plugin system with three extension points:

### Custom Extractor

```python
from crawlit import Extractor, PageArtifact

class PriceExtractor(Extractor):
    @property
    def name(self):
        return "prices"

    def extract(self, html_content, artifact):
        # Parse prices from HTML
        return [{"product": "Widget", "price": 9.99}]

crawler = Crawler(
    start_url="https://shop.example.com",
    extractors=[PriceExtractor()]
)
```

### Custom Pipeline

```python
from crawlit import Pipeline, PageArtifact

class FilterPipeline(Pipeline):
    def process(self, artifact):
        if artifact.http.status == 200:
            return artifact  # Keep
        return None  # Drop

crawler = Crawler(
    start_url="https://example.com",
    pipelines=[FilterPipeline()]
)
```

### Custom Fetcher

```python
from crawlit import Fetcher, FetchResult

class CachedFetcher(Fetcher):
    def fetch(self, url, headers=None):
        # Custom fetch logic with caching
        return FetchResult(success=True, url=url, status_code=200, text="...")
```

---

## Documentation

Full documentation is available in the [`docs/`](docs/) directory:

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, first crawl, and core concepts |
| [CLI Reference](docs/cli-reference.md) | Complete command-line argument reference |
| [Configuration](docs/configuration.md) | All configuration options and patterns |
| [Extractors](docs/extractors.md) | Table, image, keyword, form, PDF, and structured data extraction |
| [Pipelines](docs/pipelines.md) | Built-in and custom pipeline stages |
| [Async Crawling](docs/async-crawling.md) | AsyncCrawler usage and concurrency patterns |
| [JavaScript Rendering](docs/javascript-rendering.md) | Playwright-based SPA crawling |
| [Authentication & Proxies](docs/authentication-and-proxies.md) | Auth methods and proxy rotation |
| [Rate Limiting & Budgets](docs/rate-limiting-and-budgets.md) | Rate limiting, budgets, and politeness |
| [Database Integration](docs/database-integration.md) | SQLite, PostgreSQL, and MongoDB storage |
| [Security](docs/security.md) | Security analysis features |
| [Plugins](docs/plugins.md) | Writing custom extractors, pipelines, and fetchers |
| [Distributed Crawling](docs/distributed-crawling.md) | Multi-worker crawling with message queues |
| [Data Models](docs/models.md) | PageArtifact, CrawlJob, and data schema reference |
| [API Reference](docs/api-reference.md) | Complete class and function reference |

---

## Project Structure

```
crawlit/
├── crawlit.py              # CLI entry point
├── config.py               # Composable configuration dataclasses
├── interfaces.py           # Plugin ABCs (Extractor, Pipeline, Fetcher)
├── content_router.py       # Content-type dispatch
├── models/
│   └── page_artifact.py    # PageArtifact stable data model
├── crawler/
│   ├── engine.py           # Synchronous crawler
│   ├── async_engine.py     # Asynchronous crawler
│   ├── fetcher.py          # HTTP fetcher (sync)
│   ├── async_fetcher.py    # HTTP fetcher (async)
│   ├── parser.py           # HTML link extraction
│   ├── robots.py           # Robots.txt handler
│   └── js_renderer.py      # Playwright JS rendering
├── extractors/
│   ├── tables.py           # HTML table extraction
│   ├── image_extractor.py  # Image metadata extraction
│   ├── keyword_extractor.py # Keyword extraction
│   ├── forms.py            # Form analysis
│   ├── structured_data.py  # JSON-LD / Microdata / RDFa
│   ├── language.py         # Language detection
│   ├── pdf_extractor.py    # PDF text extraction
│   ├── content_extractor.py # Content & metadata extraction
│   └── js_embedded_data.py # JS-embedded data extraction
├── pipelines/
│   ├── jsonl_writer.py     # JSONL output
│   ├── blob_store.py       # Binary content storage
│   ├── edges_writer.py     # Navigation edge recording
│   └── artifact_store.py   # Complete artifact store
├── security/
│   ├── csrf.py             # CSRF token handling
│   ├── headers.py          # Security header analysis
│   ├── waf.py              # WAF detection
│   ├── honeypot.py         # Honeypot detection
│   └── captcha.py          # CAPTCHA detection
├── utils/
│   ├── rate_limiter.py     # Rate limiting
│   ├── budget.py           # Budget tracking
│   ├── session_manager.py  # HTTP session management
│   ├── url_filter.py       # URL filtering
│   ├── cache.py            # Page caching & resume
│   ├── storage.py          # HTML storage
│   ├── sitemap.py          # Sitemap parsing
│   ├── deduplication.py    # Content deduplication
│   ├── database.py         # Database backends
│   ├── proxy_manager.py    # Proxy rotation
│   ├── auth.py             # Authentication
│   ├── event_log.py        # Event logging
│   ├── content_hash_store.py # Cross-run deduplication
│   └── errors.py           # Custom exceptions
├── distributed/            # Distributed crawling (optional)
├── output/
│   └── formatters.py       # JSON/CSV/TXT/HTML formatters
└── tests/
```

---

## Requirements

- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Core**: requests, aiohttp, beautifulsoup4, nltk
- **Optional**: playwright (JS), psycopg2-binary (PostgreSQL), pymongo (MongoDB), pika (RabbitMQ), kafka-python (Kafka), pdfplumber (PDF), croniter (scheduling)

---

## Contributing

Contributions are welcome. Please open an issue or submit a pull request on [GitHub](https://github.com/SwayamDani/crawlit).

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

Built and maintained by **Swayam Dani**.
