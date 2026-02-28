# CLI Reference

This document provides a comprehensive reference for all command-line options available in the crawlit CLI. crawlit is a modular, ethical Python web crawler with extensive configuration options for different use cases.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Core Options](#core-options)
- [Output Options](#output-options)
- [Performance & Concurrency](#performance--concurrency)
- [Rate Limiting](#rate-limiting)
- [Authentication](#authentication)
- [Content Extraction](#content-extraction)
- [JavaScript Rendering](#javascript-rendering)
- [Proxy Support](#proxy-support)
- [Database Integration](#database-integration)
- [Budget & Resource Limits](#budget--resource-limits)
- [Caching & Resume](#caching--resume)
- [URL Filtering](#url-filtering)
- [Storage Options](#storage-options)
- [Advanced Features](#advanced-features)
- [Configuration Files](#configuration-files)
- [Exit Codes](#exit-codes)
- [Examples](#examples)

## Basic Usage

### Syntax

```bash
crawlit --url URL [OPTIONS]
python -m crawlit --url URL [OPTIONS]
```

### Minimal Example

```bash
crawlit --url https://example.com
```

## Core Options

### Required Arguments

| Option | Short | Description |
|--------|-------|-------------|
| `--url` | `-u` | Target website URL (required) |

### Basic Crawling Control

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--depth` | `-d` | int | 3 | Maximum crawl depth |
| `--delay` | | float | 0.1 | Delay between requests (seconds) |
| `--timeout` | | int | 10 | Request timeout in seconds |
| `--user-agent` | `-a` | str | "crawlit/1.0" | Custom User-Agent string |
| `--allow-external` | `-e` | flag | false | Allow crawling URLs outside the initial domain |
| `--ignore-robots` | `-i` | flag | false | Ignore robots.txt rules when crawling |
| `--verbose` | `-v` | flag | false | Verbose output |
| `--summary` | `-s` | flag | false | Show a summary of crawl results at the end |

### Examples

```bash
# Basic crawl with custom depth and delay
crawlit --url https://example.com --depth 5 --delay 0.5

# Allow external domains and ignore robots.txt
crawlit --url https://example.com --allow-external --ignore-robots

# Verbose output with custom user agent
crawlit --url https://example.com --verbose --user-agent "MyBot/2.0"
```

## Output Options

### Format and Location

| Option | Short | Type | Default | Choices | Description |
|--------|-------|------|---------|---------|-------------|
| `--output-format` | `-f` | str | "json" | json, csv, txt, html | Output format |
| `--output` | `-O` | str | "crawl_results.json" | | File to save results |
| `--pretty-json` | `-p` | flag | false | | Enable pretty-print JSON with indentation |

### Examples

```bash
# Save as CSV with custom filename
crawlit --url https://example.com --output-format csv --output results.csv

# Pretty-printed JSON output
crawlit --url https://example.com --pretty-json --output formatted_results.json

# HTML report format
crawlit --url https://example.com --output-format html --output report.html
```

## Performance & Concurrency

### Synchronous vs Asynchronous

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--async` | flag | false | Enable asynchronous crawling for faster performance |
| `--concurrency` | int | 15 | Maximum number of concurrent requests for async crawling |
| `--max-workers` | int | 1 | Maximum number of worker threads (sync mode) |
| `--max-queue-size` | int | None | Maximum size of URL queue |

### Examples

```bash
# Enable async crawling with high concurrency
crawlit --url https://example.com --async --concurrency 25

# Multi-threaded synchronous crawling
crawlit --url https://example.com --max-workers 4

# Limit queue size to control memory usage
crawlit --url https://example.com --max-queue-size 1000
```

## Rate Limiting

### Per-Domain Control

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--per-domain-delay` | flag | true | Enable per-domain rate limiting |
| `--domain-delay` | str | None | Set delay for specific domain (format: 'domain:delay') |

### Examples

```bash
# Custom delays for specific domains
crawlit --url https://example.com \
  --domain-delay "api.example.com:2.0" \
  --domain-delay "slow.example.com:5.0"

# Disable per-domain delays
crawlit --url https://example.com --per-domain-delay false
```

## Authentication

### Basic Authentication

| Option | Type | Description |
|--------|------|-------------|
| `--auth-user` | str | Username for basic authentication |
| `--auth-password` | str | Password for basic authentication |

### Token-Based Authentication

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--oauth-token` | str | None | OAuth 2.0 bearer token |
| `--api-key` | str | None | API key for authentication |
| `--api-key-header` | str | "X-API-Key" | Header name for API key |

### Custom Headers

| Option | Type | Description |
|--------|------|-------------|
| `--custom-header` | str | Custom header in format 'Name:Value' (repeatable) |

### Examples

```bash
# Basic authentication
crawlit --url https://example.com --auth-user myuser --auth-password mypass

# OAuth token authentication
crawlit --url https://api.example.com --oauth-token "Bearer abc123..."

# API key with custom header
crawlit --url https://api.example.com --api-key "key123" --api-key-header "Authorization"

# Multiple custom headers
crawlit --url https://example.com \
  --custom-header "X-Custom:value1" \
  --custom-header "X-Another:value2"
```

## Content Extraction

### Table Extraction

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--extract-tables` | `-t` | flag | false | Extract HTML tables from crawled pages |
| `--tables-output` | | str | "table_output" | Directory to save extracted tables |
| `--tables-format` | | str | "csv" | Format to save tables (csv, json) |
| `--min-rows` | | int | 1 | Minimum number of rows for extraction |
| `--min-columns` | | int | 2 | Minimum number of columns for extraction |
| `--max-table-depth` | | int | None | Maximum depth to extract tables from |

### Image Extraction

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--extract-images` | `-img` | flag | false | Extract images from crawled pages |
| `--images-output` | | str | "image_output" | Directory to save image information |

### Keyword Extraction

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--extract-keywords` | `-k` | flag | false | Extract keywords from crawled pages |
| `--keywords-output` | | str | "keywords.json" | File to save extracted keywords |
| `--max-keywords` | | int | 20 | Maximum number of keywords to extract per page |
| `--min-word-length` | | int | 3 | Minimum length of words to consider as keywords |

### Comprehensive Content Extraction

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--extract-content` | `-c` | flag | false | Enable comprehensive content extraction |
| `--content-output` | | str | "content_extraction.json" | File to save extracted content data |
| `--extract-headings` | | flag | false | Extract heading tags (h1-h6) |
| `--extract-metadata` | | flag | false | Extract meta tags (title, description, keywords) |
| `--extract-images-context` | | flag | false | Extract surrounding text context for images |
| `--detect-page-type` | | flag | false | Auto-detect page type based on URL patterns |

### Examples

```bash
# Extract tables with specific requirements
crawlit --url https://example.com \
  --extract-tables \
  --tables-format json \
  --min-rows 3 \
  --min-columns 2 \
  --tables-output ./extracted_tables

# Extract keywords and images
crawlit --url https://example.com \
  --extract-keywords \
  --extract-images \
  --max-keywords 50 \
  --keywords-output site_keywords.json

# Comprehensive content extraction
crawlit --url https://example.com \
  --extract-content \
  --extract-headings \
  --extract-metadata \
  --detect-page-type \
  --content-output full_content.json
```

## JavaScript Rendering

### Browser Options

| Option | Type | Default | Choices | Description |
|--------|------|---------|---------|-------------|
| `--use-js` or `--javascript` | flag | false | | Enable JavaScript rendering (requires Playwright) |
| `--js-browser` | str | "chromium" | chromium, firefox, webkit | Browser type for JS rendering |
| `--js-wait-selector` | str | None | | CSS selector to wait for |
| `--js-wait-timeout` | int | None | | Additional timeout (ms) after page load |

### Examples

```bash
# Basic JavaScript rendering
crawlit --url https://spa-example.com --use-js

# Use Firefox with specific wait conditions
crawlit --url https://dynamic-site.com \
  --use-js \
  --js-browser firefox \
  --js-wait-selector ".content-loaded" \
  --js-wait-timeout 5000
```

## Proxy Support

### Single Proxy

| Option | Type | Description |
|--------|------|-------------|
| `--proxy` | str | Single proxy (format: http://host:port or socks5://host:port) |

### Proxy Rotation

| Option | Type | Default | Choices | Description |
|--------|------|---------|---------|-------------|
| `--proxy-file` | str | None | | File containing list of proxies (one per line) |
| `--proxy-rotation` | str | "round-robin" | round-robin, random, least-used, best-performance | Proxy rotation strategy |

### Examples

```bash
# Single proxy
crawlit --url https://example.com --proxy "http://proxy.example.com:8080"

# Proxy rotation from file
crawlit --url https://example.com \
  --proxy-file ./proxies.txt \
  --proxy-rotation random
```

## Database Integration

### Database Selection

| Option | Type | Default | Choices | Description |
|--------|------|---------|---------|-------------|
| `--database` or `--db` | str | None | sqlite, postgresql, mongodb | Database backend to store crawl results |

### SQLite Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--db-path` | str | "crawl_results.db" | Database file path (for SQLite) |

### PostgreSQL/MongoDB Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--db-host` | str | "localhost" | Database host |
| `--db-port` | int | None | Database port (5432 for PostgreSQL, 27017 for MongoDB) |
| `--db-name` | str | "crawlit" | Database name |
| `--db-user` | str | "postgres" | Database username |
| `--db-password` | str | "" | Database password |
| `--db-collection` | str | "results" | Collection name (for MongoDB) |

### Examples

```bash
# SQLite database
crawlit --url https://example.com --database sqlite --db-path ./crawl.db

# PostgreSQL with custom credentials
crawlit --url https://example.com \
  --database postgresql \
  --db-host db.example.com \
  --db-port 5432 \
  --db-name webcrawl \
  --db-user crawler \
  --db-password secret123

# MongoDB with authentication
crawlit --url https://example.com \
  --database mongodb \
  --db-host mongo.example.com \
  --db-name crawldb \
  --db-collection pages
```

## Budget & Resource Limits

### Crawl Limits

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--max-pages` | int | None | Maximum number of pages to crawl |
| `--max-bandwidth-mb` | float | None | Maximum bandwidth in megabytes |
| `--max-time-seconds` | float | None | Maximum crawl time in seconds |
| `--max-file-size-mb` | float | None | Maximum file size per request in megabytes |

### Examples

```bash
# Budget-limited crawl
crawlit --url https://example.com \
  --max-pages 1000 \
  --max-bandwidth-mb 100 \
  --max-time-seconds 3600 \
  --max-file-size-mb 10
```

## Caching & Resume

### Caching Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--use-cache` | flag | false | Enable page caching to avoid re-fetching |
| `--enable-disk-cache` | flag | false | Enable disk-based caching (persists across runs) |
| `--cache-dir` | str | ".crawlit_cache" | Directory for disk-based cache |
| `--cache-ttl` | int | 3600 | Cache time-to-live in seconds |

### Resume Functionality

| Option | Type | Description |
|--------|------|-------------|
| `--save-state` | str | Save crawl state to file for later resumption |
| `--resume-from` | str | Resume crawl from previously saved state file |

### Incremental Crawling

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--incremental` | flag | false | Enable incremental crawling using ETags/Last-Modified |
| `--incremental-db` | str | "./incremental_crawl.db" | SQLite database for incremental crawl state |

### Examples

```bash
# Enable caching with custom settings
crawlit --url https://example.com \
  --use-cache \
  --enable-disk-cache \
  --cache-ttl 7200 \
  --cache-dir ./my_cache

# Save state for resumption
crawlit --url https://example.com --save-state ./crawl_state.json

# Resume from saved state
crawlit --url https://example.com --resume-from ./crawl_state.json

# Incremental crawling
crawlit --url https://example.com \
  --incremental \
  --incremental-db ./incremental.db
```

## URL Filtering

### Pattern-Based Filtering

| Option | Type | Description |
|--------|------|-------------|
| `--allowed-pattern` | str | Regex pattern for allowed URLs (repeatable) |
| `--blocked-pattern` | str | Regex pattern for blocked URLs (repeatable) |
| `--blocked-extension` | str | File extension to block (repeatable) |
| `--same-path-only` | flag | Restrict crawling to URLs with same path prefix as start URL |

### Content Deduplication

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--enable-deduplication` | flag | false | Enable content deduplication to skip duplicate pages |
| `--dedup-min-length` | int | 100 | Minimum content length for deduplication |
| `--dedup-normalize` | flag | true | Normalize content before deduplication |

### Examples

```bash
# Allow only specific URL patterns
crawlit --url https://example.com \
  --allowed-pattern ".*\/articles\/.*" \
  --allowed-pattern ".*\/blog\/.*"

# Block certain patterns and file types
crawlit --url https://example.com \
  --blocked-pattern ".*\/admin\/.*" \
  --blocked-extension ".pdf" \
  --blocked-extension ".zip"

# Same path restriction with deduplication
crawlit --url https://example.com/blog/ \
  --same-path-only \
  --enable-deduplication \
  --dedup-min-length 200
```

## Storage Options

### HTML Content Storage

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--no-store-html` | flag | false | Don't store HTML content in results (saves memory) |
| `--use-disk-storage` | flag | false | Store HTML content on disk instead of memory |
| `--storage-dir` | str | ".crawlit_storage" | Directory for disk-based HTML storage |

### Examples

```bash
# Memory-efficient crawling
crawlit --url https://example.com --no-store-html

# Disk-based storage for large crawls
crawlit --url https://example.com \
  --use-disk-storage \
  --storage-dir ./html_storage
```

## Advanced Features

### Sitemap Support

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--use-sitemap` | flag | false | Discover and use sitemaps for URL discovery |
| `--sitemap-url` | str | None | Explicit sitemap URL to parse (repeatable) |

### Examples

```bash
# Auto-discover sitemaps
crawlit --url https://example.com --use-sitemap

# Use specific sitemap URLs
crawlit --url https://example.com \
  --sitemap-url https://example.com/sitemap.xml \
  --sitemap-url https://example.com/news-sitemap.xml
```

## Configuration Files

While crawlit primarily uses command-line arguments, you can create wrapper scripts or use environment variables for complex configurations:

### Environment Variables

```bash
# Set default user agent
export CRAWLIT_USER_AGENT="MyBot/2.0"

# Set default delay
export CRAWLIT_DELAY="0.5"
```

### Wrapper Script Example

```bash
#!/bin/bash
# crawl-config.sh

crawlit \
  --url "$1" \
  --depth 5 \
  --async \
  --concurrency 20 \
  --extract-tables \
  --extract-keywords \
  --use-cache \
  --enable-disk-cache \
  --output-format json \
  --pretty-json \
  --summary
```

## Exit Codes

crawlit uses standard exit codes to indicate the result of the crawl operation:

| Exit Code | Description |
|-----------|-------------|
| 0 | Success - crawl completed without errors |
| 1 | General error - crawl failed due to an error |

### Error Types

When errors occur during crawling, they are classified using these error codes:

| Error Code | Description |
|------------|-------------|
| `FETCH_ERROR` | Network or connection failure |
| `HTTP_ERROR` | Non-success HTTP status (4xx/5xx except 304) |
| `TIMEOUT` | Request timed out |
| `PARSE_ERROR` | HTML/XML parsing failure |
| `EXTRACTOR_ERROR` | Plugin extractor raised an exception |
| `PIPELINE_ERROR` | Pipeline stage raised an exception |
| `PDF_ERROR` | PDF extraction failure |
| `INCREMENTAL` | 304 Not Modified (informational, not a real error) |
| `UNKNOWN` | Catch-all for unclassified errors |

## Examples

### Basic Website Crawl

```bash
# Simple crawl with results summary
crawlit --url https://example.com --depth 3 --summary
```

### News Site Data Extraction

```bash
# Extract articles with comprehensive content analysis
crawlit --url https://news.example.com \
  --depth 4 \
  --extract-content \
  --extract-headings \
  --extract-metadata \
  --extract-keywords \
  --max-keywords 30 \
  --output-format json \
  --output news_extraction.json \
  --pretty-json
```

### E-commerce Site Table Extraction

```bash
# Extract product tables and pricing data
crawlit --url https://shop.example.com \
  --extract-tables \
  --tables-format csv \
  --min-rows 2 \
  --min-columns 3 \
  --tables-output ./product_tables \
  --allowed-pattern ".*\/products\/.*" \
  --blocked-extension ".pdf"
```

### High-Performance Async Crawl

```bash
# Fast async crawl with caching and rate limiting
crawlit --url https://example.com \
  --async \
  --concurrency 30 \
  --use-cache \
  --enable-disk-cache \
  --per-domain-delay \
  --domain-delay "api.example.com:1.0" \
  --max-pages 5000 \
  --max-bandwidth-mb 500 \
  --save-state ./crawl_state.json
```

### API Crawl with Authentication

```bash
# Crawl API endpoints with token authentication
crawlit --url https://api.example.com \
  --oauth-token "Bearer eyJ..." \
  --custom-header "Accept:application/json" \
  --extract-keywords \
  --output-format json \
  --timeout 30 \
  --delay 0.5
```

### JavaScript-Heavy Site

```bash
# Crawl SPA with JavaScript rendering
crawlit --url https://spa.example.com \
  --use-js \
  --js-browser chromium \
  --js-wait-selector ".app-loaded" \
  --js-wait-timeout 10000 \
  --extract-content \
  --extract-headings \
  --timeout 60
```

### Large-Scale Crawl with Database Storage

```bash
# Enterprise-scale crawl with PostgreSQL storage
crawlit --url https://enterprise.example.com \
  --database postgresql \
  --db-host db.internal \
  --db-name webcrawl \
  --db-user crawler \
  --db-password $DB_PASSWORD \
  --async \
  --concurrency 50 \
  --max-workers 8 \
  --use-disk-storage \
  --enable-deduplication \
  --max-pages 100000 \
  --max-time-seconds 86400 \
  --incremental \
  --verbose
```

---

*This reference covers all available CLI options in crawlit. For additional help, run `crawlit --help` or visit the [documentation](./README.md).*