# Rate Limiting and Budgets

**Respectful Crawling with Resource Management**

Crawlit provides comprehensive rate limiting and budget tracking capabilities to ensure ethical, respectful web crawling while managing resource consumption. This guide covers all aspects of rate limiting strategies, budget enforcement, and politeness features.

## Table of Contents

1. [Overview](#overview)
2. [Rate Limiting Strategies](#rate-limiting-strategies)
3. [Per-Domain vs Global Rate Limiting](#per-domain-vs-global-rate-limiting)
4. [Budget Tracking](#budget-tracking)
5. [Robots.txt Integration](#robotstxt-integration)
6. [Dynamic Rate Adjustment](#dynamic-rate-adjustment)
7. [Politeness Features](#politeness-features)
8. [Configuration Options](#configuration-options)
9. [Performance Impact and Optimization](#performance-impact-and-optimization)
10. [Monitoring and Logging](#monitoring-and-logging)
11. [Examples for Different Scenarios](#examples-for-different-scenarios)
12. [Integration with Async Crawling](#integration-with-async-crawling)

## Overview

Crawlit's rate limiting and budget system ensures your crawling activities are:

- **Respectful**: Honor robots.txt, crawl-delay directives, and server response times
- **Controlled**: Enforce limits on pages, bandwidth, time, and file sizes
- **Adaptive**: Dynamic adjustment based on server performance and error rates
- **Efficient**: Per-domain tracking with minimal overhead
- **Compliant**: Automatic robots.txt parsing and rule enforcement

## Rate Limiting Strategies

### Basic Rate Limiting

The foundation of respectful crawling is controlling request frequency to prevent server overload.

```python
from crawlit.utils.rate_limiter import RateLimiter, AsyncRateLimiter
from crawlit import Crawler, AsyncCrawler

# Synchronous rate limiting
rate_limiter = RateLimiter(default_delay=0.5)  # 0.5 second delay between requests

crawler = Crawler(
    start_url="https://example.com",
    rate_limiter=rate_limiter,
    max_depth=3
)

# Alternative: specify requests per second
rate_limiter = RateLimiter(requests_per_second=2.0)  # 2 requests per second max

# Async rate limiting  
async_limiter = AsyncRateLimiter(default_delay=0.5)

async_crawler = AsyncCrawler(
    start_url="https://example.com", 
    rate_limiter=async_limiter,
    max_depth=3
)
```

### Rate Limiting Configuration

```python
# CLI usage
crawlit --url https://example.com --delay 0.5 --per-domain-delay

# Programmatic usage
rate_limiter = RateLimiter(
    default_delay=0.1,  # Default delay for all domains
    requests_per_second=None  # Alternative: use requests_per_second=10
)

# Set custom delays for specific domains
rate_limiter.set_domain_delay("api.example.com", 2.0)  # Slower for APIs
rate_limiter.set_domain_delay("cdn.example.com", 0.05)  # Faster for CDNs
```

## Per-Domain vs Global Rate Limiting

### Per-Domain Rate Limiting (Recommended)

Per-domain rate limiting tracks delays separately for each domain, enabling efficient crawling across multiple sites while respecting each site's requirements.

```python
from crawlit.utils.rate_limiter import RateLimiter

# Per-domain rate limiter (default behavior)
limiter = RateLimiter(default_delay=0.5)

# Different delays for different types of domains
limiter.set_domain_delay("api.slowsite.com", 2.0)      # API endpoint - be gentle
limiter.set_domain_delay("cdn.fastsite.com", 0.1)      # CDN - can handle more
limiter.set_domain_delay("social.media.com", 1.0)      # Social media - moderate

# Use with crawler
crawler = Crawler(
    start_url="https://example.com",
    rate_limiter=limiter,
    allow_external_urls=True  # Enable crawling across domains
)
```

### Global Rate Limiting

For scenarios where you need overall request rate control regardless of domain:

```python
# Implement global limiting by setting same delay for all domains
class GlobalRateLimiter(RateLimiter):
    def get_domain_delay(self, domain: str) -> float:
        return self.default_delay  # Always use default delay
    
global_limiter = GlobalRateLimiter(default_delay=1.0)
```

## Budget Tracking

Budget tracking enforces limits on crawling resources to prevent runaway crawls and manage costs.

### Budget Types

1. **Page Count Budget**: Limit total pages crawled
2. **Bandwidth Budget**: Limit total data downloaded (MB)
3. **Time Budget**: Limit total crawling time (seconds)
4. **File Size Budget**: Limit individual file download sizes (MB)

### Basic Budget Setup

```python
from crawlit.utils.budget_tracker import BudgetTracker, AsyncBudgetTracker

# Synchronous budget tracking
budget = BudgetTracker(
    max_pages=100,              # Stop after 100 pages
    max_bandwidth_mb=50.0,      # Stop after 50MB downloaded
    max_time_seconds=300,       # Stop after 5 minutes
    max_file_size_mb=10.0       # Skip files larger than 10MB
)

# Budget exceeded callback
def budget_callback(reason, stats):
    print(f"Budget limit reached: {reason}")
    print(f"Crawled {stats['pages_crawled']} pages")
    print(f"Downloaded {stats['mb_downloaded']:.2f} MB")

budget = BudgetTracker(
    max_pages=50,
    on_budget_exceeded=budget_callback
)

crawler = Crawler(
    start_url="https://example.com",
    budget_tracker=budget
)
```

### Budget with Async Crawling

```python
from crawlit.utils.budget_tracker import AsyncBudgetTracker

async def run_budget_crawler():
    budget = AsyncBudgetTracker(
        max_pages=200,
        max_bandwidth_mb=100.0,
        max_time_seconds=600
    )
    
    crawler = AsyncCrawler(
        start_url="https://example.com",
        budget_tracker=budget,
        max_depth=3
    )
    
    results = await crawler.crawl()
    
    # Check final statistics
    stats = await budget.get_stats()
    print(f"Final usage: {stats['pages_usage_percent']:.1f}% of page budget")
    print(f"Bandwidth used: {stats['mb_downloaded']:.2f} MB")

import asyncio
asyncio.run(run_budget_crawler())
```

### CLI Budget Options

```bash
# Page limit
crawlit --url https://example.com --max-pages 100

# Bandwidth limit (MB)
crawlit --url https://example.com --max-bandwidth-mb 50

# Time limit (seconds)
crawlit --url https://example.com --max-time-seconds 300

# File size limit (MB)
crawlit --url https://example.com --max-file-size-mb 10

# Combined limits
crawlit --url https://example.com \
    --max-pages 100 \
    --max-bandwidth-mb 25 \
    --max-time-seconds 600 \
    --delay 0.5
```

## Robots.txt Integration

Crawlit automatically handles robots.txt files and respects crawl-delay directives for ethical crawling.

### Automatic Robots.txt Compliance

```python
from crawlit import Crawler

# Robots.txt compliance is enabled by default
crawler = Crawler(
    start_url="https://example.com",
    respect_robots=True,  # Default: True
    max_depth=3
)

# Disable robots.txt (not recommended)
crawler = Crawler(
    start_url="https://example.com",
    respect_robots=False,  # Override robots.txt
    max_depth=3
)
```

### Crawl-Delay Extraction

Crawlit automatically extracts and applies crawl-delay directives from robots.txt:

```python
from crawlit.crawler.robots import RobotsHandler, AsyncRobotsHandler

# Synchronous robots.txt handling
robots = RobotsHandler()

# Check if URL is allowed
can_crawl = robots.can_fetch(
    url="https://example.com/page", 
    user_agent="crawlit/1.0"
)

# Extract crawl-delay for domain
delay = robots.get_crawl_delay(
    url="https://example.com/page",
    user_agent="crawlit/1.0"
)
print(f"Recommended delay: {delay}s")

# Async robots.txt handling
async def check_robots_async():
    robots = AsyncRobotsHandler()
    
    can_crawl = await robots.can_fetch(
        url="https://example.com/page",
        user_agent="crawlit/1.0"
    )
    
    delay = await robots.get_crawl_delay(
        url="https://example.com/page",
        user_agent="crawlit/1.0"
    )
    
    return can_crawl, delay

# Integration with rate limiter
rate_limiter = RateLimiter(default_delay=0.5)

# The crawler automatically applies robots.txt crawl-delay
# and updates the rate limiter accordingly
```

### Example robots.txt Handling

Given this robots.txt file:
```
User-agent: *
Disallow: /private/
Allow: /private/public/
Crawl-delay: 2

User-agent: crawlit
Crawl-delay: 1
```

Crawlit will:
- Skip URLs under `/private/` (except `/private/public/`)
- Apply 1-second delay for user-agent "crawlit"  
- Apply 2-second delay for other user-agents
- Cache robots.txt for 1 hour to avoid repeated requests

## Dynamic Rate Adjustment

Dynamic rate limiters automatically adjust crawling speed based on server response times and error rates.

### Dynamic Rate Limiter Features

```python
from crawlit.utils.rate_limiter import DynamicRateLimiter, AsyncDynamicRateLimiter

# Synchronous dynamic rate limiting
dynamic_limiter = DynamicRateLimiter(
    default_delay=0.5,          # Starting delay
    min_delay=0.1,              # Minimum delay (fastest)
    max_delay=10.0,             # Maximum delay (slowest)
    sensitivity='medium',        # Adjustment sensitivity: 'low', 'medium', 'high'
    adjustment_factor=1.5       # Multiplier for delay adjustments
)

crawler = Crawler(
    start_url="https://example.com",
    rate_limiter=dynamic_limiter
)

# The limiter automatically adjusts based on:
# - HTTP 429 (Too Many Requests) responses → Increase delay significantly
# - High error rates (>30%) → Increase delay moderately  
# - Slow response times (>2s average) → Increase delay slightly
# - Fast responses (<0.5s) + low errors → Decrease delay
```

### Response Recording

The crawler automatically records response metrics, but you can also log manually:

```python
import time

# Manual response recording
start_time = time.time()
# ... make request ...
response_time = time.time() - start_time

dynamic_limiter.record_response(
    url="https://example.com/page",
    response_time=response_time,
    status_code=200,
    retry_after=None  # From Retry-After header if present
)

# Handle 429 responses with Retry-After
if response.status_code == 429:
    retry_after = response.headers.get('Retry-After')
    dynamic_limiter.record_response(
        url=url,
        response_time=response_time,
        status_code=429,
        retry_after=int(retry_after) if retry_after else None
    )
```

### Sensitivity Settings

```python
# Conservative (slow to adjust)
conservative_limiter = DynamicRateLimiter(sensitivity='low')

# Balanced (default)
balanced_limiter = DynamicRateLimiter(sensitivity='medium')  

# Aggressive (quick to adjust)
aggressive_limiter = DynamicRateLimiter(sensitivity='high')
```

## Politeness Features

### Comprehensive Politeness Configuration

```python
from crawlit import Crawler
from crawlit.utils.rate_limiter import DynamicRateLimiter
from crawlit.utils.budget_tracker import BudgetTracker

# Maximum politeness configuration
polite_crawler = Crawler(
    start_url="https://example.com",
    max_depth=3,
    
    # Rate limiting
    rate_limiter=DynamicRateLimiter(
        default_delay=1.0,      # Conservative 1-second default delay
        min_delay=0.5,          # Never go faster than 0.5s
        max_delay=30.0,         # Allow up to 30s for problem servers
        sensitivity='medium'
    ),
    
    # Robots.txt compliance
    respect_robots=True,        # Honor robots.txt rules
    
    # Resource limits
    budget_tracker=BudgetTracker(
        max_pages=500,          # Reasonable page limit
        max_bandwidth_mb=100,   # Bandwidth limit
        max_time_seconds=3600,  # 1-hour time limit
        max_file_size_mb=20     # Skip very large files
    ),
    
    # Request politeness
    user_agent="crawlit/1.0 (+https://yoursite.com/about-crawler)",
    timeout=30,                 # Generous timeout
    allow_external_urls=False,  # Stay within original domain
    max_workers=1              # Single-threaded for gentleness
)
```

### Ethical Crawling Best Practices

1. **Always respect robots.txt**: Keep `respect_robots=True`
2. **Use reasonable delays**: Start with 0.5-1.0 seconds between requests
3. **Set resource limits**: Prevent runaway crawls with budgets
4. **Identify your crawler**: Use descriptive User-Agent strings
5. **Monitor server response**: Use dynamic rate limiting
6. **Limit concurrency**: Avoid overwhelming servers
7. **Handle errors gracefully**: Back off on repeated failures

## Configuration Options

### Rate Limiter Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_delay` | float | 0.1 | Default delay between requests (seconds) |
| `requests_per_second` | float | None | Alternative rate specification |
| `min_delay` | float | 0.05 | Minimum delay (dynamic limiter only) |
| `max_delay` | float | 10.0 | Maximum delay (dynamic limiter only) |
| `sensitivity` | str | 'medium' | Adjustment sensitivity: 'low', 'medium', 'high' |
| `adjustment_factor` | float | 1.5 | Multiplier for delay changes |

### Budget Tracker Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_pages` | int | None | Maximum pages to crawl |
| `max_bandwidth_mb` | float | None | Maximum bandwidth (MB) |
| `max_time_seconds` | float | None | Maximum time (seconds) |
| `max_file_size_mb` | float | None | Maximum file size (MB) |
| `on_budget_exceeded` | callable | None | Callback when budget exceeded |

### CLI Configuration Examples

```bash
# Conservative crawling
crawlit --url https://example.com \
    --delay 2.0 \
    --max-pages 50 \
    --max-bandwidth-mb 10 \
    --per-domain-delay \
    --timeout 30

# Fast but controlled crawling
crawlit --url https://example.com \
    --delay 0.2 \
    --max-pages 1000 \
    --max-time-seconds 1800 \
    --async \
    --concurrency 10

# API-focused crawling
crawlit --url https://api.example.com \
    --delay 1.0 \
    --max-pages 100 \
    --max-file-size-mb 5 \
    --user-agent "MyBot/1.0 (+https://mysite.com/bot)"
```

## Performance Impact and Optimization

### Rate Limiting Overhead

Rate limiting adds minimal overhead:

- **Memory**: ~100 bytes per tracked domain
- **CPU**: Negligible (simple timestamp calculations)
- **Disk**: None (in-memory only)

```python
# Check rate limiter statistics
stats = rate_limiter.get_stats()
print(f"Tracking {stats['domains_tracked']} domains")
print(f"Custom delays: {stats['domains_with_custom_delay']}")
```

### Budget Tracking Overhead

Budget tracking is lightweight:

```python
# Get budget usage statistics
stats = budget_tracker.get_stats()
print(f"Pages: {stats['pages_crawled']}/{stats['limits']['max_pages']}")
print(f"Bandwidth: {stats['mb_downloaded']:.2f}/{stats['limits']['max_bandwidth_mb']} MB")
print(f"Time usage: {stats.get('time_usage_percent', 0):.1f}%")
```

### Optimization Tips

1. **Use appropriate delays**: Don't over-throttle fast, reliable sites
2. **Enable per-domain limiting**: More efficient than global limiting
3. **Set reasonable budgets**: Avoid checking limits too frequently
4. **Monitor dynamic adjustments**: Ensure they're working as expected

## Monitoring and Logging

### Rate Limiting Logs

Enable debug logging to monitor rate limiting:

```python
import logging
logging.getLogger('crawlit.utils.rate_limiter').setLevel(logging.DEBUG)

# Logs will show:
# DEBUG: Set delay for example.com: 2.0s
# DEBUG: Rate limiting: waiting 0.745s for example.com
# INFO: High error rate (35.2%) for api.example.com, increased delay to 2.40s
# WARNING: Rate limit hit for example.com, increased delay to 5.00s
```

### Budget Tracking Logs

```python
import logging
logging.getLogger('crawlit.utils.budget_tracker').setLevel(logging.INFO)

# Logs will show:
# INFO: Budget tracker initialized: pages=100, bandwidth=50.0MB, time=300s
# DEBUG: Budget: pages=45, bandwidth=23.45MB
# WARNING: Budget exceeded: Page limit reached (100 pages)
```

### Statistical Monitoring

```python
# Real-time monitoring during crawl
async def monitor_crawl():
    while crawler.is_running:
        # Rate limiter stats
        rate_stats = await rate_limiter.get_stats()
        
        # Budget stats  
        budget_stats = await budget_tracker.get_stats()
        
        print(f"Domains tracked: {rate_stats['domains_tracked']}")
        print(f"Pages crawled: {budget_stats['pages_crawled']}")
        print(f"Bandwidth used: {budget_stats['mb_downloaded']:.2f} MB")
        
        await asyncio.sleep(30)  # Check every 30 seconds
```

## Examples for Different Scenarios

### Scenario 1: E-commerce Site Crawling

```python
from crawlit import Crawler
from crawlit.utils.rate_limiter import DynamicRateLimiter
from crawlit.utils.budget_tracker import BudgetTracker

# E-commerce sites often have rate limiting and large catalogs
ecommerce_limiter = DynamicRateLimiter(
    default_delay=1.0,      # Start conservatively
    min_delay=0.3,          # Don't go too fast
    max_delay=20.0,         # Handle aggressive rate limiting
    sensitivity='high'      # Quick to adapt
)

budget = BudgetTracker(
    max_pages=5000,         # Large catalog
    max_bandwidth_mb=500,   # Lots of images
    max_time_seconds=7200   # 2 hours max
)

crawler = Crawler(
    start_url="https://shop.example.com",
    rate_limiter=ecommerce_limiter,
    budget_tracker=budget,
    max_depth=4,
    respect_robots=True
)
```

### Scenario 2: News Site Crawling

```python
# News sites typically allow faster crawling
news_limiter = RateLimiter(default_delay=0.3)

# Focus on recent articles
budget = BudgetTracker(
    max_pages=1000,
    max_time_seconds=1800,  # 30 minutes
    max_file_size_mb=5      # Skip large media files
)

crawler = Crawler(
    start_url="https://news.example.com",
    rate_limiter=news_limiter,
    budget_tracker=budget,
    max_depth=2
)
```

### Scenario 3: API Endpoint Crawling

```python
# APIs often have strict rate limits
api_limiter = RateLimiter(default_delay=2.0)

# API responses are typically small but valuable
budget = BudgetTracker(
    max_pages=500,          # Limited endpoints
    max_bandwidth_mb=10,    # Small JSON responses
    max_time_seconds=3600
)

crawler = Crawler(
    start_url="https://api.example.com/v1/",
    rate_limiter=api_limiter,
    budget_tracker=budget,
    user_agent="DataBot/1.0 (+https://mycompany.com/bot-info)",
    max_depth=3
)
```

### Scenario 4: Academic/Research Site

```python
# Research sites value thoroughness over speed
research_limiter = DynamicRateLimiter(
    default_delay=2.0,      # Very conservative
    min_delay=1.0,          # Always polite
    max_delay=60.0,         # Very patient
    sensitivity='low'       # Slow to adjust
)

budget = BudgetTracker(
    max_pages=10000,        # Comprehensive crawl
    max_bandwidth_mb=1000,  # PDFs and papers
    max_time_seconds=86400, # 24 hours
    max_file_size_mb=50     # Large academic PDFs
)

crawler = Crawler(
    start_url="https://research.university.edu",
    rate_limiter=research_limiter,
    budget_tracker=budget,
    max_depth=5,
    user_agent="AcademicBot/1.0 (+https://university.edu/research-bot)"
)
```

## Integration with Async Crawling

### Async Rate Limiting

```python
from crawlit import AsyncCrawler
from crawlit.utils.rate_limiter import AsyncDynamicRateLimiter
from crawlit.utils.budget_tracker import AsyncBudgetTracker

async def async_crawl_with_limits():
    # Async-optimized components
    rate_limiter = AsyncDynamicRateLimiter(
        default_delay=0.5,
        min_delay=0.1,
        max_delay=10.0,
        sensitivity='medium'
    )
    
    budget = AsyncBudgetTracker(
        max_pages=1000,
        max_bandwidth_mb=100,
        max_time_seconds=1800
    )
    
    crawler = AsyncCrawler(
        start_url="https://example.com",
        rate_limiter=rate_limiter,
        budget_tracker=budget,
        max_depth=3,
        max_concurrent_requests=10  # Controlled concurrency
    )
    
    results = await crawler.crawl()
    
    # Get final statistics
    rate_stats = await rate_limiter.get_stats()
    budget_stats = await budget.get_stats()
    
    print(f"Crawled {len(results)} pages")
    print(f"Rate limiter tracked {rate_stats['domains_tracked']} domains")
    print(f"Used {budget_stats['pages_usage_percent']:.1f}% of page budget")
    
    return results

# Run the async crawler
results = asyncio.run(async_crawl_with_limits())
```

### Advanced Async Scenarios

```python
async def multi_domain_crawl():
    """Crawl multiple domains with individual rate limiting"""
    
    rate_limiter = AsyncDynamicRateLimiter(default_delay=0.5)
    
    # Set domain-specific delays
    await rate_limiter.set_domain_delay("api.fastsite.com", 0.2)
    await rate_limiter.set_domain_delay("slow.archive.org", 3.0) 
    await rate_limiter.set_domain_delay("social.media.com", 1.0)
    
    budget = AsyncBudgetTracker(
        max_pages=5000,
        max_bandwidth_mb=500,
        max_time_seconds=7200
    )
    
    urls = [
        "https://api.fastsite.com",
        "https://slow.archive.org", 
        "https://social.media.com"
    ]
    
    all_results = []
    
    for url in urls:
        crawler = AsyncCrawler(
            start_url=url,
            rate_limiter=rate_limiter,  # Shared limiter
            budget_tracker=budget,      # Shared budget
            max_depth=2,
            allow_external_urls=True
        )
        
        results = await crawler.crawl()
        all_results.extend(results)
        
        # Check if budget exceeded
        if await budget.is_budget_exceeded():
            print(f"Budget exceeded, stopping crawl")
            break
    
    return all_results
```

### Concurrent Domain Management

```python
async def concurrent_domain_crawl():
    """Safely crawl multiple domains concurrently"""
    
    shared_limiter = AsyncRateLimiter(default_delay=0.5) 
    shared_budget = AsyncBudgetTracker(max_pages=2000)
    
    async def crawl_domain(domain):
        crawler = AsyncCrawler(
            start_url=f"https://{domain}",
            rate_limiter=shared_limiter,
            budget_tracker=shared_budget,
            max_depth=2
        )
        return await crawler.crawl()
    
    domains = ["example1.com", "example2.com", "example3.com"]
    
    # Crawl domains concurrently but with shared rate limiting
    tasks = [crawl_domain(domain) for domain in domains]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

---

## Summary

Crawlit's rate limiting and budget system provides comprehensive tools for ethical, controlled web crawling:

- **Multiple rate limiting strategies** from simple delays to dynamic adjustment
- **Flexible budget controls** for pages, bandwidth, time, and file sizes  
- **Automatic robots.txt compliance** with crawl-delay extraction
- **Per-domain intelligence** for efficient multi-site crawling
- **Async/await support** for high-performance scenarios
- **Rich monitoring and logging** for operational visibility

By combining these features thoughtfully, you can create crawling solutions that are both effective and respectful of target websites and their resources.

**Key Principles:**
1. Start with conservative settings and adjust based on site behavior
2. Always respect robots.txt unless absolutely necessary  
3. Use dynamic rate limiting for adaptive behavior
4. Set reasonable budgets to prevent resource exhaustion
5. Monitor logs and statistics to optimize performance
6. Be a good internet citizen - crawl responsibly

For additional examples and use cases, see the [examples](../examples/) directory and [quickstart guide](quickstart.rst).