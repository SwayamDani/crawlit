# crawlit Documentation Index

Welcome to the complete documentation for crawlit v1.0.0 - a powerful, modular, and ethical web crawler built in Python.

## Quick Navigation

### 🚀 Getting Started
- **[Getting Started](getting-started.md)** - Installation, first crawl, and core concepts
- **[CLI Reference](cli-reference.md)** - Complete command-line argument reference  
- **[Configuration](configuration.md)** - All configuration options and patterns

### 📊 Core Features  
- **[Extractors](extractors.md)** - Table, image, keyword, form, PDF, and structured data extraction
- **[Pipelines](pipelines.md)** - Built-in and custom pipeline stages
- **[Models](models.md)** - PageArtifact, CrawlJob, and data schema reference

### ⚡ Advanced Topics
- **[Async Crawling](async-crawling.md)** - AsyncCrawler usage and concurrency patterns  
- **[JavaScript Rendering](javascript-rendering.md)** - Playwright-based SPA crawling
- **[Authentication & Proxies](authentication-and-proxies.md)** - Auth methods and proxy rotation
- **[Rate Limiting & Budgets](rate-limiting-and-budgets.md)** - Rate limiting, budgets, and politeness

### 🔧 Integration & Storage
- **[Database Integration](database-integration.md)** - SQLite, PostgreSQL, and MongoDB storage
- **[Distributed Crawling](distributed-crawling.md)** - Multi-worker crawling with message queues
- **[Security](security.md)** - Security analysis features

### 🧩 Extensibility
- **[Plugins](plugins.md)** - Writing custom extractors, pipelines, and fetchers
- **[API Reference](api-reference.md)** - Complete class and function reference

## Documentation by Use Case

### For Web Scraping Beginners
1. Start with [Getting Started](getting-started.md) for basic concepts
2. Learn CLI usage with [CLI Reference](cli-reference.md) 
3. Understand data output with [Models](models.md)

### For Python Developers
1. Review [API Reference](api-reference.md) for programmatic usage
2. Explore [Configuration](configuration.md) for advanced setups
3. Check [Extractors](extractors.md) for data extraction capabilities

### For JavaScript/SPA Sites
1. Learn [JavaScript Rendering](javascript-rendering.md) for modern web apps
2. Configure [Authentication & Proxies](authentication-and-proxies.md) if needed
3. Use [Async Crawling](async-crawling.md) for better performance

### For Large-Scale Operations
1. Implement [Rate Limiting & Budgets](rate-limiting-and-budgets.md) for ethical crawling
2. Set up [Database Integration](database-integration.md) for data persistence
3. Scale with [Distributed Crawling](distributed-crawling.md)

### For Custom Solutions
1. Build custom extractors with [Plugins](plugins.md)
2. Process data with [Pipelines](pipelines.md)
3. Add security analysis with [Security](security.md) features

## Key Features Overview

### 🔍 **Content Extraction**
- **HTML Tables** - Complex table extraction with rowspan/colspan support
- **Images** - Metadata and context extraction
- **Keywords** - Frequency-scored keyword and keyphrase extraction  
- **Forms** - Complete form analysis with security detection
- **PDFs** - Text and table extraction with OCR support
- **Structured Data** - JSON-LD, Microdata, RDFa extraction

### 🚀 **Performance & Scale**  
- **Async Engine** - High-performance asynchronous crawling
- **JavaScript Rendering** - Full SPA support via Playwright
- **Distributed Crawling** - Multi-worker scaling with message queues
- **Caching** - Intelligent page caching and resume capabilities

### 🛡️ **Ethical & Secure**
- **Robots.txt Compliance** - Automatic respect for crawling rules
- **Rate Limiting** - Per-domain delays and politeness features  
- **Security Analysis** - WAF detection, security headers, CAPTCHA detection
- **Budget Controls** - Limits on pages, bandwidth, and crawl time

### 🔧 **Integration Ready**
- **Multiple Databases** - SQLite, PostgreSQL, MongoDB support
- **Export Formats** - JSON, CSV, JSONL, HTML output
- **Authentication** - Basic, Bearer, OAuth, and custom auth methods
- **Plugin System** - Extensible extractors, pipelines, and fetchers

## Version Information

This documentation covers **crawlit v1.0.0**, released February 27, 2026.

### What's New in v1.0.0
- Stable API with backward compatibility guarantees
- Complete async/await support throughout the codebase
- Enhanced JavaScript rendering with Playwright integration
- Comprehensive security analysis features
- Distributed crawling with RabbitMQ and Kafka support
- Advanced data extraction for modern web applications
- Production-ready database integrations
- Extensive plugin system for customization

### Compatibility
- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Operating Systems**: Windows, macOS, Linux
- **Databases**: SQLite 3.x, PostgreSQL 12+, MongoDB 4.4+
- **Message Queues**: RabbitMQ 3.8+, Apache Kafka 2.8+

## Getting Help

### Documentation Issues
If you find errors or gaps in this documentation:
- Open an issue on [GitHub](https://github.com/SwayamDani/crawlit/issues)
- Tag issues with `documentation` label
- Include the specific page and section

### Code Issues  
For bugs, feature requests, or usage questions:
- Check existing [GitHub Issues](https://github.com/SwayamDani/crawlit/issues)
- Review the [API Reference](api-reference.md) for detailed method documentation
- Look at examples in the [repository](https://github.com/SwayamDani/crawlit/tree/main/examples)

### Community Resources
- **Repository**: [https://github.com/SwayamDani/crawlit](https://github.com/SwayamDani/crawlit)
- **PyPI Package**: [https://pypi.org/project/crawlit/](https://pypi.org/project/crawlit/)
- **License**: MIT License (see [LICENSE](../LICENSE) file)

---

**Built and maintained by [Swayam Dani](https://github.com/SwayamDani)**

*crawlit - Modular, Ethical Python Web Crawler*