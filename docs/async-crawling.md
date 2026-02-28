# Asynchronous Crawling with crawlit

This comprehensive guide covers the asynchronous crawling capabilities of crawlit, designed for high-performance web crawling scenarios where speed and efficiency are paramount.

## Table of Contents

1. [AsyncCrawler vs Crawler Overview](#asynccrawler-vs-crawler-overview)
2. [Concurrency Patterns and Best Practices](#concurrency-patterns-and-best-practices)
3. [Performance Optimization](#performance-optimization)
4. [Error Handling in Async Contexts](#error-handling-in-async-contexts)
5. [Session Management and Connection Pooling](#session-management-and-connection-pooling)
6. [Memory Management for Large Crawls](#memory-management-for-large-crawls)
7. [Async-Specific Configuration](#async-specific-configuration)
8. [Usage Examples](#usage-examples)
9. [Integration with Async Frameworks](#integration-with-async-frameworks)
10. [Debugging and Monitoring](#debugging-and-monitoring)

## AsyncCrawler vs Crawler Overview

### Core Architectural Differences

The `AsyncCrawler` provides asynchronous, concurrent web crawling capabilities compared to the synchronous `Crawler` class:

| Feature | Synchronous Crawler | AsyncCrawler |
|---------|-------------------|--------------|
| **Execution Model** | Sequential processing with optional threading | Coroutine-based concurrency |
| **I/O Handling** | Synchronous `requests` library | Asynchronous `aiohttp` |
| **Concurrency** | Thread-based parallelism | Event loop-based async/await |
| **Memory Efficiency** | Higher memory usage per thread | Lower memory footprint |
| **Performance** | Limited by thread overhead | Superior for I/O-bound operations |
| **Error Propagation** | Synchronous exception handling | Async context error handling |

### Key Async Components

```python
# Core async components
from crawlit.crawler.async_engine import AsyncCrawler
from crawlit.crawler.async_fetcher import fetch_page_async
from crawlit.utils.session_manager import SessionManager
```

### Basic Usage Comparison

```python
# Synchronous approach
from crawlit import Crawler

crawler = Crawler("https://example.com", max_depth=3)
results = crawler.crawl()

# Asynchronous approach  
import asyncio
from crawlit import AsyncCrawler

async def main():
    crawler = AsyncCrawler(
        "https://example.com", 
        max_depth=3,
        max_concurrent_requests=15
    )
    await crawler.crawl()
    return crawler.results

results = asyncio.run(main())
```

## Concurrency Patterns and Best Practices

### Worker-Queue Architecture

The `AsyncCrawler` uses a producer-consumer pattern with async workers:

```python
# Internal architecture (simplified)
async def _worker(self):
    """Worker task for processing URLs from the queue"""
    while True:
        current_url, depth = await self.queue.get()
        try:
            async with self.semaphore:  # Rate limiting
                await self._process_url(current_url, depth)
        finally:
            self.queue.task_done()
```

### Concurrency Control Patterns

#### 1. Semaphore-Based Rate Limiting

```python
crawler = AsyncCrawler(
    "https://example.com",
    max_concurrent_requests=10,  # Controls concurrent connections
    delay=0.1  # Global delay between requests
)
```

#### 2. Per-Domain Rate Limiting

```python
from crawlit.utils.rate_limiter import AsyncRateLimiter

rate_limiter = AsyncRateLimiter(
    default_delay=0.5,
    domain_delays={"heavy-site.com": 2.0}
)

crawler = AsyncCrawler(
    "https://example.com",
    rate_limiter=rate_limiter,
    use_per_domain_delay=True
)
```

#### 3. Budget-Based Crawling

```python
from crawlit.utils.budget_tracker import AsyncBudgetTracker

budget = AsyncBudgetTracker(
    max_pages=1000,
    max_bytes=50 * 1024 * 1024,  # 50MB
    max_time_minutes=30
)

crawler = AsyncCrawler(
    "https://example.com",
    budget_tracker=budget
)
```

### Best Practices for Concurrency

#### Optimal Concurrency Levels

```python
# Conservative: Good for most websites
crawler = AsyncCrawler(url, max_concurrent_requests=5)

# Moderate: For robust websites
crawler = AsyncCrawler(url, max_concurrent_requests=15)

# Aggressive: For high-capacity sites only
crawler = AsyncCrawler(url, max_concurrent_requests=25)
```

#### Respectful Crawling

```python
async def respectful_crawl():
    crawler = AsyncCrawler(
        "https://example.com",
        max_concurrent_requests=5,     # Moderate concurrency
        delay=0.5,                     # Half-second delay
        respect_robots=True,           # Honor robots.txt
        use_per_domain_delay=True      # Per-domain rate limiting
    )
    
    # Enable robots.txt crawl-delay recognition
    await crawler.crawl()
```

## Performance Optimization

### Connection Pooling Configuration

```python
from crawlit.utils.session_manager import SessionManager

# Optimized session manager
session_manager = SessionManager(
    timeout=15,           # Reasonable timeout
    pool_size=20,         # Connection pool size
    max_retries=2,        # Reduce retries for speed
    verify_ssl=True
)

crawler = AsyncCrawler(
    "https://example.com",
    session_manager=session_manager,
    max_concurrent_requests=15
)
```

### Memory-Optimized Configuration

```python
from crawlit.utils.storage import StorageManager

# Minimize memory usage
storage_manager = StorageManager(
    store_html_content=False,    # Don't store HTML in memory
    enable_disk_storage=True,    # Use disk for HTML storage
    max_memory_usage_mb=500      # Limit memory usage
)

crawler = AsyncCrawler(
    "https://example.com",
    storage_manager=storage_manager,
    retain_artifacts=False,       # Don't keep all artifacts in memory
    enable_content_deduplication=True  # Avoid duplicate processing
)
```

### High-Performance Pattern

```python
import asyncio
from crawlit import AsyncCrawler
from crawlit.utils.session_manager import SessionManager
from crawlit.utils.budget_tracker import AsyncBudgetTracker

async def high_performance_crawl(urls: list, max_pages_per_site: int = 500):
    """High-performance crawling of multiple sites"""
    
    session_manager = SessionManager(
        timeout=10,
        pool_size=30,
        max_retries=1
    )
    
    budget = AsyncBudgetTracker(
        max_pages=max_pages_per_site,
        max_time_minutes=20
    )
    
    # Create multiple crawler tasks
    tasks = []
    for url in urls:
        crawler = AsyncCrawler(
            url,
            max_depth=3,
            max_concurrent_requests=20,
            session_manager=session_manager,
            budget_tracker=budget,
            delay=0.1,
            retain_artifacts=False  # Memory optimization
        )
        tasks.append(crawler.crawl())
    
    # Run all crawls concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return [task.result() for task in tasks if not task.exception()]
```

## Error Handling in Async Contexts

### Comprehensive Error Handling

```python
import asyncio
import logging
from crawlit import AsyncCrawler
from crawlit.models.page_artifact import CrawlError

async def robust_crawl():
    crawler = AsyncCrawler(
        "https://example.com",
        max_concurrent_requests=10,
        max_retries=2
    )
    
    try:
        await crawler.crawl()
        
        # Check for crawl errors
        errors = []
        for url, result in crawler.results.items():
            if not result.get('success', False):
                errors.append({
                    'url': url,
                    'error': result.get('error'),
                    'status': result.get('status')
                })
        
        if errors:
            logging.warning(f"Encountered {len(errors)} errors during crawl")
            
        return crawler.results
        
    except asyncio.TimeoutError:
        logging.error("Crawl timed out")
        return None
    except Exception as e:
        logging.error(f"Crawl failed: {e}")
        return None
    finally:
        # Cleanup resources
        if hasattr(crawler, 'session_manager'):
            await crawler.session_manager.close_async_session()
```

### Error Recovery Patterns

```python
async def crawl_with_fallback(primary_url: str, fallback_urls: list):
    """Crawl with fallback URLs if primary fails"""
    
    for attempt, url in enumerate([primary_url] + fallback_urls):
        try:
            crawler = AsyncCrawler(
                url,
                max_concurrent_requests=5,
                timeout=15
            )
            await crawler.crawl()
            
            if crawler.results:
                logging.info(f"Successfully crawled {url} on attempt {attempt + 1}")
                return crawler.results
                
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < len(fallback_urls):
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    logging.error("All crawl attempts failed")
    return {}
```

## Session Management and Connection Pooling

### Advanced Session Configuration

```python
from crawlit.utils.session_manager import SessionManager
import aiohttp

# Advanced session with custom connector
async def create_optimized_crawler():
    # Custom connector for fine-tuned connection pooling
    connector = aiohttp.TCPConnector(
        limit=30,              # Total connection limit
        limit_per_host=10,     # Per-host connection limit
        ttl_dns_cache=300,     # DNS cache TTL
        use_dns_cache=True,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    
    session = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=15, connect=5),
        headers={"User-Agent": "MyBot/1.0"}
    )
    
    # Manual session management
    crawler = AsyncCrawler(
        "https://example.com",
        max_concurrent_requests=15
    )
    
    # Replace the default session manager
    crawler.session_manager._async_session = session
    
    try:
        await crawler.crawl()
        return crawler.results
    finally:
        await session.close()
```

### Authentication with Async Sessions

```python
async def authenticated_crawl():
    """Crawl with authentication"""
    
    session_manager = SessionManager(
        headers={"Authorization": "Bearer your_token"},
        cookies={"session_id": "your_session"},
        verify_ssl=True
    )
    
    crawler = AsyncCrawler(
        "https://protected.example.com",
        session_manager=session_manager,
        max_concurrent_requests=5
    )
    
    await crawler.crawl()
    return crawler.results
```

## Memory Management for Large Crawls

### Memory-Efficient Patterns

```python
from crawlit.utils.deduplication import ContentDeduplicator
from crawlit.utils.cache import PageCache

async def memory_efficient_large_crawl():
    """Optimized for crawling thousands of pages"""
    
    # Content deduplication to avoid processing duplicates
    deduplicator = ContentDeduplicator(
        enabled=True,
        max_cache_size=10000,
        similarity_threshold=0.95
    )
    
    # Page cache with LRU eviction
    page_cache = PageCache(
        max_size=1000,
        enable_disk_cache=True,
        cache_dir="./crawl_cache"
    )
    
    crawler = AsyncCrawler(
        "https://large-site.com",
        max_depth=5,
        max_concurrent_requests=20,
        
        # Memory management
        content_deduplicator=deduplicator,
        page_cache=page_cache,
        retain_artifacts=False,        # Don't keep all artifacts
        store_html_content=False,      # Don't store HTML in results
        
        # Processing efficiency
        enable_content_deduplication=True,
        max_queue_size=1000           # Limit queue size
    )
    
    await crawler.crawl()
    return crawler.results
```

### Streaming Results Pattern

```python
async def streaming_crawl_results():
    """Process results as they're generated"""
    
    class StreamingCrawler(AsyncCrawler):
        async def _process_url(self, url, depth):
            # Call parent processing
            await super()._process_url(url, depth)
            
            # Stream result immediately
            if url in self.results:
                await self.process_result_immediately(url, self.results[url])
                
                # Clear from memory to save space
                if not self.retain_artifacts:
                    del self.results[url]
        
        async def process_result_immediately(self, url, result):
            """Override this to process results as they arrive"""
            # Save to database, file, etc.
            print(f"Processed: {url} - Status: {result.get('status')}")
    
    crawler = StreamingCrawler(
        "https://example.com",
        max_concurrent_requests=15,
        retain_artifacts=False
    )
    
    await crawler.crawl()
```

## Async-Specific Configuration

### Complete Configuration Example

```python
import asyncio
from crawlit import AsyncCrawler
from crawlit.utils.session_manager import SessionManager
from crawlit.utils.rate_limiter import AsyncRateLimiter
from crawlit.utils.budget_tracker import AsyncBudgetTracker
from crawlit.utils.deduplication import ContentDeduplicator

async def fully_configured_crawler():
    """Comprehensive async crawler configuration"""
    
    # Session management
    session_manager = SessionManager(
        user_agent="MyBot/2.0 (+https://mysite.com/bot)",
        timeout=20,
        max_retries=2,
        pool_size=25,
        verify_ssl=True,
        headers={"Accept-Language": "en-US,en;q=0.9"}
    )
    
    # Rate limiting
    rate_limiter = AsyncRateLimiter(
        default_delay=0.5,
        domain_delays={
            "slow-site.com": 2.0,
            "fast-site.com": 0.1
        }
    )
    
    # Budget control
    budget = AsyncBudgetTracker(
        max_pages=5000,
        max_bytes=100 * 1024 * 1024,  # 100MB
        max_time_minutes=60
    )
    
    # Content deduplication
    deduplicator = ContentDeduplicator(
        enabled=True,
        similarity_threshold=0.90
    )
    
    crawler = AsyncCrawler(
        start_url="https://example.com",
        max_depth=4,
        max_concurrent_requests=15,
        
        # Core behavior
        internal_only=True,
        respect_robots=True,
        same_path_only=False,
        
        # Performance
        delay=0.2,
        timeout=15,
        max_retries=2,
        
        # Utilities
        session_manager=session_manager,
        rate_limiter=rate_limiter,
        budget_tracker=budget,
        content_deduplicator=deduplicator,
        
        # Features
        enable_content_extraction=True,
        enable_image_extraction=False,
        enable_table_extraction=False,
        use_sitemap=True,
        
        # Memory management
        retain_artifacts=False,
        store_html_content=False,
        enable_content_deduplication=True
    )
    
    await crawler.crawl()
    return crawler.results
```

### JavaScript Rendering Configuration

```python
async def js_enabled_crawl():
    """Async crawling with JavaScript rendering"""
    
    crawler = AsyncCrawler(
        "https://spa-app.com",
        max_concurrent_requests=3,  # Lower concurrency for JS rendering
        
        # JavaScript rendering
        use_js_rendering=True,
        js_wait_for_selector="[data-content-loaded]",
        js_wait_for_timeout=5000,
        js_browser_type="chromium"
    )
    
    await crawler.crawl()
    return crawler.results
```

## Usage Examples

### Simple Async Crawl

```python
import asyncio
from crawlit import AsyncCrawler

async def simple_crawl():
    crawler = AsyncCrawler(
        "https://example.com",
        max_depth=2,
        max_concurrent_requests=10
    )
    await crawler.crawl()
    
    print(f"Crawled {len(crawler.results)} pages")
    for url, result in crawler.results.items():
        print(f"{url}: {result.get('status')}")

asyncio.run(simple_crawl())
```

### Multiple Site Crawling

```python
async def crawl_multiple_sites():
    """Crawl multiple sites concurrently"""
    
    urls = [
        "https://site1.com",
        "https://site2.com", 
        "https://site3.com"
    ]
    
    async def crawl_site(url):
        crawler = AsyncCrawler(
            url,
            max_depth=2,
            max_concurrent_requests=8
        )
        await crawler.crawl()
        return {url: crawler.results}
    
    # Crawl all sites concurrently
    tasks = [crawl_site(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    # Combine results
    all_results = {}
    for result_dict in results:
        all_results.update(result_dict)
    
    return all_results
```

### Content Extraction with Async

```python
async def extract_content_async():
    """Comprehensive content extraction with async crawler"""
    
    crawler = AsyncCrawler(
        "https://news-site.com",
        max_depth=3,
        max_concurrent_requests=12,
        
        # Enable all content extraction
        enable_content_extraction=True,
        enable_image_extraction=True,
        enable_table_extraction=True,
        enable_keyword_extraction=True
    )
    
    await crawler.crawl()
    
    # Process extracted content
    articles = []
    for url, result in crawler.results.items():
        if result.get('success') and result.get('title'):
            articles.append({
                'url': url,
                'title': result.get('title'),
                'meta_description': result.get('meta_description'),
                'headings': result.get('headings'),
                'keywords': result.get('keywords'),
                'images': result.get('images_with_context', [])
            })
    
    return articles
```

### Sitemap-Based Crawling

```python
async def sitemap_crawl():
    """Crawl using sitemap for URL discovery"""
    
    crawler = AsyncCrawler(
        "https://example.com",
        max_depth=1,  # Shallow depth since we're using sitemap
        max_concurrent_requests=20,
        
        # Sitemap configuration
        use_sitemap=True,
        sitemap_urls=[
            "https://example.com/sitemap.xml",
            "https://example.com/news-sitemap.xml"
        ]
    )
    
    await crawler.crawl()
    print(f"Crawled {len(crawler.results)} pages via sitemap")
    return crawler.results
```

## Integration with Async Frameworks

### FastAPI Integration

```python
from fastapi import FastAPI, BackgroundTasks
from crawlit import AsyncCrawler
import asyncio

app = FastAPI()

# Store crawl results
crawl_results = {}

async def background_crawl(crawl_id: str, url: str):
    """Background crawl task"""
    crawler = AsyncCrawler(
        url,
        max_depth=3,
        max_concurrent_requests=10
    )
    
    await crawler.crawl()
    crawl_results[crawl_id] = {
        'status': 'completed',
        'pages': len(crawler.results),
        'results': crawler.results
    }

@app.post("/crawl/{crawl_id}")
async def start_crawl(crawl_id: str, url: str, background_tasks: BackgroundTasks):
    """Start a background crawl"""
    crawl_results[crawl_id] = {'status': 'running'}
    background_tasks.add_task(background_crawl, crawl_id, url)
    return {"crawl_id": crawl_id, "status": "started"}

@app.get("/crawl/{crawl_id}")
async def get_crawl_status(crawl_id: str):
    """Get crawl status and results"""
    return crawl_results.get(crawl_id, {'status': 'not_found'})

@app.post("/crawl/{crawl_id}/realtime")
async def realtime_crawl(crawl_id: str, url: str):
    """Real-time crawl with immediate results"""
    crawler = AsyncCrawler(
        url,
        max_depth=2,
        max_concurrent_requests=8
    )
    
    await crawler.crawl()
    
    return {
        'crawl_id': crawl_id,
        'pages_found': len(crawler.results),
        'results': crawler.results
    }
```

### Django Async Views

```python
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from crawlit import AsyncCrawler
import asyncio
import json

@method_decorator(csrf_exempt, name='dispatch')
class AsyncCrawlView(View):
    async def post(self, request):
        """Async Django view for crawling"""
        data = json.loads(request.body)
        url = data.get('url')
        max_depth = data.get('max_depth', 2)
        
        if not url:
            return JsonResponse({'error': 'URL required'}, status=400)
        
        try:
            crawler = AsyncCrawler(
                url,
                max_depth=max_depth,
                max_concurrent_requests=8,
                enable_content_extraction=True
            )
            
            await crawler.crawl()
            
            return JsonResponse({
                'success': True,
                'pages_crawled': len(crawler.results),
                'results': crawler.results
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
```

### aiohttp Server Integration

```python
from aiohttp import web, ClientSession
from crawlit import AsyncCrawler
import json

async def crawl_handler(request):
    """aiohttp handler for crawling"""
    data = await request.json()
    url = data.get('url')
    
    if not url:
        return web.json_response({'error': 'URL required'}, status=400)
    
    crawler = AsyncCrawler(
        url,
        max_depth=data.get('max_depth', 2),
        max_concurrent_requests=data.get('concurrency', 10)
    )
    
    await crawler.crawl()
    
    return web.json_response({
        'pages': len(crawler.results),
        'results': crawler.results
    })

# Create aiohttp application
app = web.Application()
app.router.add_post('/crawl', crawl_handler)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

## Debugging and Monitoring

### Comprehensive Logging Setup

```python
import logging
import asyncio
from crawlit import AsyncCrawler

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawl.log')
    ]
)

# Specific logger configuration
logger = logging.getLogger('crawlit.crawler.async_engine')
logger.setLevel(logging.DEBUG)

async def debug_crawl():
    """Crawl with comprehensive debugging"""
    
    crawler = AsyncCrawler(
        "https://example.com",
        max_depth=2,
        max_concurrent_requests=5
    )
    
    # Enable verbose logging
    crawler_logger = logging.getLogger('crawlit')
    crawler_logger.setLevel(logging.DEBUG)
    
    await crawler.crawl()
    
    # Debug information
    print(f"\nCrawl Statistics:")
    print(f"Total URLs processed: {len(crawler.visited_urls)}")
    print(f"Results collected: {len(crawler.results)}")
    print(f"Successful requests: {sum(1 for r in crawler.results.values() if r.get('success'))}")
    print(f"Failed requests: {sum(1 for r in crawler.results.values() if not r.get('success'))}")
    
    return crawler.results
```

### Performance Monitoring

```python
import time
import asyncio
import logging
from crawlit import AsyncCrawler
from crawlit.utils.budget_tracker import AsyncBudgetTracker

async def monitored_crawl():
    """Crawl with performance monitoring"""
    
    # Budget tracker for monitoring
    budget = AsyncBudgetTracker(
        max_pages=1000,
        max_time_minutes=30
    )
    
    crawler = AsyncCrawler(
        "https://example.com",
        max_depth=3,
        max_concurrent_requests=15,
        budget_tracker=budget
    )
    
    start_time = time.time()
    
    # Add monitoring
    class MonitoredCrawler(AsyncCrawler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.page_count = 0
            self.error_count = 0
            self.start_time = time.time()
        
        async def _process_url(self, url, depth):
            await super()._process_url(url, depth)
            
            self.page_count += 1
            if not self.results.get(url, {}).get('success', False):
                self.error_count += 1
            
            # Log progress every 50 pages
            if self.page_count % 50 == 0:
                elapsed = time.time() - self.start_time
                rate = self.page_count / elapsed if elapsed > 0 else 0
                logging.info(f"Progress: {self.page_count} pages, {rate:.1f} pages/sec, {self.error_count} errors")
    
    monitored_crawler = MonitoredCrawler(
        "https://example.com",
        max_depth=3,
        max_concurrent_requests=15,
        budget_tracker=budget
    )
    
    await monitored_crawler.crawl()
    
    elapsed = time.time() - start_time
    print(f"\nCrawl completed in {elapsed:.1f} seconds")
    print(f"Pages processed: {monitored_crawler.page_count}")
    print(f"Average rate: {monitored_crawler.page_count/elapsed:.1f} pages/sec")
    print(f"Error rate: {monitored_crawler.error_count/monitored_crawler.page_count*100:.1f}%")
    
    return monitored_crawler.results
```

### Health Check Pattern

```python
async def health_check_crawl():
    """Crawl with built-in health checks"""
    
    async def check_crawler_health(crawler):
        """Monitor crawler health during execution"""
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            if not hasattr(crawler, 'results'):
                continue
            
            success_rate = sum(1 for r in crawler.results.values() if r.get('success', False))
            total_pages = len(crawler.results)
            
            if total_pages > 0:
                success_percentage = (success_rate / total_pages) * 100
                logging.info(f"Health check: {success_percentage:.1f}% success rate ({success_rate}/{total_pages})")
                
                if success_percentage < 50 and total_pages > 20:
                    logging.warning("Low success rate detected - consider adjusting crawler settings")
    
    crawler = AsyncCrawler(
        "https://example.com",
        max_depth=3,
        max_concurrent_requests=10
    )
    
    # Start health monitoring
    health_task = asyncio.create_task(check_crawler_health(crawler))
    
    try:
        await crawler.crawl()
    finally:
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass
    
    return crawler.results
```

## Advanced Patterns

### Custom Async Pipeline

```python
from crawlit.interfaces import AsyncPipeline
from crawlit.models.page_artifact import PageArtifact

class AsyncAnalyticsPipeline(AsyncPipeline):
    """Custom async pipeline for real-time analytics"""
    
    async def process(self, artifact: PageArtifact) -> PageArtifact:
        """Process each page asynchronously"""
        
        # Extract metrics
        if artifact.content and artifact.content.raw_html:
            html = artifact.content.raw_html
            
            # Async analysis (e.g., send to analytics service)
            await self.send_to_analytics({
                'url': artifact.url,
                'content_length': len(html),
                'processed_at': artifact.fetched_at,
                'depth': artifact.crawl.depth
            })
        
        return artifact
    
    async def send_to_analytics(self, data):
        """Send data to analytics service"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            await session.post(
                "https://analytics.example.com/api/pageview",
                json=data
            )

async def crawl_with_custom_pipeline():
    """Use custom async pipeline"""
    
    pipeline = AsyncAnalyticsPipeline()
    
    crawler = AsyncCrawler(
        "https://example.com",
        max_concurrent_requests=10,
        pipelines=[pipeline]
    )
    
    await crawler.crawl()
    return crawler.results
```

## Troubleshooting Common Issues

### Memory Leaks

```python
async def memory_safe_crawl():
    """Pattern to avoid memory leaks"""
    
    crawler = AsyncCrawler(
        "https://example.com",
        max_concurrent_requests=10,
        retain_artifacts=False,      # Don't keep all artifacts
        store_html_content=False     # Don't store HTML
    )
    
    try:
        await crawler.crawl()
        
        # Process results immediately and clear
        results_copy = dict(crawler.results)
        crawler.results.clear()  # Clear to free memory
        
        return results_copy
    finally:
        # Ensure session cleanup
        if hasattr(crawler, 'session_manager'):
            await crawler.session_manager.close_async_session()
```

### Connection Pool Exhaustion

```python
async def connection_safe_crawl():
    """Avoid connection pool exhaustion"""
    
    from crawlit.utils.session_manager import SessionManager
    
    # Conservative connection settings
    session_manager = SessionManager(
        pool_size=10,        # Limited pool size
        timeout=15,          # Reasonable timeout
        max_retries=1        # Fewer retries
    )
    
    crawler = AsyncCrawler(
        "https://example.com",
        max_concurrent_requests=5,  # Conservative concurrency
        session_manager=session_manager,
        delay=0.5               # Ensure delays
    )
    
    await crawler.crawl()
    return crawler.results
```

This comprehensive guide covers the essential aspects of asynchronous crawling with crawlit. The async capabilities provide significant performance benefits for I/O-bound web crawling tasks while maintaining the same feature set as the synchronous crawler.