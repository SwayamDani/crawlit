# CLI Features - Complete Guide

All library features are now available through the CLI! Here's a comprehensive guide:

## 🔐 Authentication

### Basic Authentication
```bash
crawlit --url https://api.example.com \
  --auth-user myusername \
  --auth-password mypassword
```

### OAuth 2.0 Bearer Token
```bash
crawlit --url https://api.example.com \
  --oauth-token "your-bearer-token-here"
```

### API Key Authentication
```bash
crawlit --url https://api.example.com \
  --api-key "your-api-key" \
  --api-key-header "X-API-Key"
```

### Custom Headers
```bash
crawlit --url https://example.com \
  --custom-header "X-Custom-Auth:secret123" \
  --custom-header "X-Request-ID:abc-123"
```

## 💰 Budget Tracking

Limit your crawl by pages, bandwidth, time, or file size:

```bash
crawlit --url https://example.com \
  --max-pages 100 \
  --max-bandwidth-mb 50.0 \
  --max-time-seconds 300 \
  --max-file-size-mb 10.0
```

When any limit is reached, the crawler stops gracefully with statistics.

## 💾 Caching & Resume

### Enable Page Caching
```bash
# Memory cache
crawlit --url https://example.com --use-cache --cache-ttl 3600

# Disk cache (persists across runs)
crawlit --url https://example.com \
  --use-cache \
  --enable-disk-cache \
  --cache-dir ./my_cache \
  --cache-ttl 7200
```

### Save & Resume Crawls
```bash
# Save state after crawling
crawlit --url https://example.com \
  --depth 5 \
  --save-state crawl_state.json

# Resume from saved state
crawlit --url https://example.com \
  --resume-from crawl_state.json
```

## 🔄 Content Deduplication

Avoid crawling duplicate content:

```bash
crawlit --url https://example.com \
  --enable-deduplication \
  --dedup-min-length 100 \
  --dedup-normalize
```

## 🎯 URL Filtering

### Allow Only Specific Patterns
```bash
crawlit --url https://example.com \
  --allowed-pattern ".*example\.com/blog/.*" \
  --allowed-pattern ".*example\.com/docs/.*"
```

### Block Specific Patterns
```bash
crawlit --url https://example.com \
  --blocked-pattern ".*example\.com/admin/.*" \
  --blocked-pattern ".*example\.com/private/.*"
```

### Block File Extensions
```bash
crawlit --url https://example.com \
  --blocked-extension .pdf \
  --blocked-extension .zip \
  --blocked-extension .exe
```

### Same Path Only
```bash
crawlit --url https://example.com/blog/ \
  --same-path-only  # Only crawls URLs under /blog/
```

## 🚀 Multi-Threading & Concurrency

### Synchronous Multi-Threading
```bash
crawlit --url https://example.com \
  --max-workers 4 \
  --max-queue-size 1000
```

### Asynchronous Crawling
```bash
crawlit --url https://example.com \
  --async \
  --concurrency 20
```

## ⏱️ Rate Limiting

### Per-Domain Delays
```bash
crawlit --url https://example.com \
  --per-domain-delay \
  --domain-delay "example.com:1.0" \
  --domain-delay "api.example.com:2.0"
```

## 🗺️ Sitemap Support

```bash
# Auto-discover sitemaps from robots.txt
crawlit --url https://example.com --use-sitemap

# Use specific sitemap URLs
crawlit --url https://example.com \
  --sitemap-url https://example.com/sitemap.xml \
  --sitemap-url https://example.com/sitemap-blog.xml
```

## 💿 Storage Options

### Disable HTML Storage (Save Memory)
```bash
crawlit --url https://example.com --no-store-html
```

### Use Disk Storage
```bash
crawlit --url https://example.com \
  --use-disk-storage \
  --storage-dir ./html_files
```

## 🎭 Complete Example - All Features

Here's a comprehensive example using multiple features:

```bash
crawlit --url https://api.example.com \
  --depth 3 \
  --max-workers 4 \
  --max-queue-size 1000 \
  \
  --auth-user apiuser \
  --auth-password secret123 \
  --custom-header "X-Client-ID:my-app" \
  \
  --max-pages 500 \
  --max-bandwidth-mb 100 \
  --max-time-seconds 600 \
  \
  --use-cache \
  --enable-disk-cache \
  --cache-dir ./.cache \
  --save-state crawl_state.json \
  \
  --enable-deduplication \
  --dedup-min-length 200 \
  \
  --allowed-pattern ".*api\.example\.com/v1/.*" \
  --blocked-extension .pdf \
  --blocked-extension .zip \
  \
  --per-domain-delay \
  --domain-delay "api.example.com:1.0" \
  \
  --use-sitemap \
  \
  --extract-tables \
  --extract-keywords \
  --extract-images \
  \
  --use-js \
  --js-browser chromium \
  \
  --proxy-file proxies.txt \
  --proxy-rotation round-robin \
  \
  --database sqlite \
  --db-path results.db \
  \
  --output results.json \
  --output-format json \
  --summary \
  --verbose
```

## 📊 Feature Comparison

| Feature | Library API | CLI | Notes |
|---------|------------|-----|-------|
| Basic Crawling | ✅ | ✅ | Core functionality |
| Authentication | ✅ | ✅ | OAuth, API keys, Basic auth |
| Budget Tracking | ✅ | ✅ | Pages, bandwidth, time limits |
| Caching | ✅ | ✅ | Memory & disk cache |
| Resume/Save State | ✅ | ✅ | Pause and continue crawls |
| Content Deduplication | ✅ | ✅ | Skip duplicate pages |
| URL Filtering | ✅ | ✅ | Pattern matching, extensions |
| Multi-threading | ✅ | ✅ | Configurable workers |
| Rate Limiting | ✅ | ✅ | Per-domain delays |
| Sitemap Support | ✅ | ✅ | Auto-discovery & explicit |
| Storage Options | ✅ | ✅ | Memory or disk |
| JS Rendering | ✅ | ✅ | Playwright integration |
| Proxy Support | ✅ | ✅ | Single & rotation |
| Database Integration | ✅ | ✅ | SQLite, PostgreSQL, MongoDB |
| Content Extraction | ✅ | ✅ | Tables, images, keywords |
| Async Mode | ✅ | ✅ | High-performance crawling |
| Distributed Crawling | ✅ | ❌ | Requires library API |

**100% feature parity** for single-machine crawling! Only distributed/coordinated crawling requires the library API.

## 🔧 Tips

1. **Start Simple**: Begin with basic options, add features as needed
2. **Budget Limits**: Always use budget limits in production
3. **Caching**: Enable caching for repeated crawls of same sites
4. **Multi-threading**: Use `--max-workers 4` for 4x speed (adjust based on your CPU)
5. **Async Mode**: Use `--async --concurrency 20` for maximum speed
6. **Authentication**: Test auth with a single page first (`--depth 0`)
7. **Deduplication**: Enable for sites with lots of duplicate content
8. **Disk Storage**: Use for large crawls to save memory

## 📚 Get Help

```bash
# See all options
crawlit --help

# Get version
crawlit --version
```
