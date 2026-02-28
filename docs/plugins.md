# Crawlit Plugin Development Guide

This guide covers how to extend crawlit's functionality by creating custom plugins. Crawlit provides a flexible plugin architecture that allows you to customize data extraction, content processing, and HTTP fetching behavior.

## Table of Contents

1. [Plugin Architecture Overview](#plugin-architecture-overview)
2. [Plugin Interfaces and Base Classes](#plugin-interfaces-and-base-classes)
3. [Extractor Plugin Development](#extractor-plugin-development)
4. [Pipeline Plugin Development](#pipeline-plugin-development)
5. [Fetcher Plugin Development](#fetcher-plugin-development)
6. [Plugin Registration and Lifecycle](#plugin-registration-and-lifecycle)
7. [Best Practices](#best-practices)
8. [Testing Custom Plugins](#testing-custom-plugins)
9. [Performance Considerations](#performance-considerations)
10. [Plugin Examples](#plugin-examples)
11. [Plugin Distribution and Packaging](#plugin-distribution-and-packaging)

## Plugin Architecture Overview

Crawlit's plugin system is built around three core extension points:

- **Extractors**: Extract structured data from HTML content and attach it to page artifacts
- **Pipelines**: Process, enrich, filter, or persist page artifacts after crawling
- **Fetchers**: Handle HTTP requests with custom authentication, proxies, or mock responses

All plugins implement abstract base classes defined in `crawlit.interfaces` and can be registered with the crawler at initialization time. The system supports both synchronous and asynchronous variants for optimal performance.

### Plugin Flow

```
URL → Fetcher → HTML Content → Extractors → Page Artifact → Pipelines → Final Output
```

## Plugin Interfaces and Base Classes

### Core Classes

All plugin interfaces are defined in `crawlit.interfaces`:

```python
from crawlit.interfaces import (
    Fetcher, AsyncFetcher, FetchRequest, FetchResult,
    Extractor, AsyncExtractor,
    Pipeline, AsyncPipeline
)
from crawlit.models import PageArtifact
```

### Synchronous vs Asynchronous Variants

- **Synchronous Crawler**: Only accepts `Fetcher`, `Extractor`, and `Pipeline` instances
- **Asynchronous Crawler**: Accepts both sync and async variants, but prefers async for better performance

## Extractor Plugin Development

Extractors derive structured data from HTML content and attach it to the page artifact's `extracted` dictionary.

### Basic Extractor Interface

```python
from abc import ABC, abstractmethod
from typing import Any
from crawlit.interfaces import Extractor
from crawlit.models import PageArtifact

class CustomExtractor(Extractor):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the extracted data"""
        pass
    
    @abstractmethod
    def extract(self, html_content: str, artifact: PageArtifact) -> Any:
        """Extract data from HTML and return it"""
        pass
```

### Example: Price Extractor

```python
import re
from bs4 import BeautifulSoup
from crawlit.interfaces import Extractor
from crawlit.models import PageArtifact

class PriceExtractor(Extractor):
    def __init__(self, currency_symbols=None):
        self.currency_symbols = currency_symbols or ['$', '€', '£', '¥']
        
    @property
    def name(self) -> str:
        return "prices"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        """Extract price information from the page"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            prices = []
            
            # Look for common price patterns
            price_patterns = [
                r'[\$€£¥]\s*\d+(?:\.\d{2})?',  # Currency symbols
                r'\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP|JPY)',  # With currency codes
            ]
            
            text = soup.get_text()
            for pattern in price_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                prices.extend(matches)
            
            # Look for structured data prices
            price_elements = soup.find_all(['span', 'div'], 
                                         attrs={'class': re.compile(r'price|cost|amount')})
            for elem in price_elements:
                if elem.text.strip():
                    prices.append(elem.text.strip())
            
            return {
                'raw_prices': prices,
                'count': len(prices),
                'extracted_at': artifact.crawl_meta.timestamp.isoformat()
            }
            
        except Exception as exc:
            artifact.errors.append(f"Price extraction failed: {exc}")
            return {'error': str(exc)}
```

### Async Extractor Example

```python
import asyncio
from crawlit.interfaces import AsyncExtractor
from crawlit.models import PageArtifact

class AsyncSentimentExtractor(AsyncExtractor):
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    @property
    def name(self) -> str:
        return "sentiment"
    
    async def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        """Perform async sentiment analysis"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()
            
            # Simulate async API call
            sentiment_score = await self._analyze_sentiment(text_content[:1000])
            
            return {
                'sentiment_score': sentiment_score,
                'text_length': len(text_content),
                'analyzed_at': artifact.crawl_meta.timestamp.isoformat()
            }
            
        except Exception as exc:
            artifact.errors.append(f"Sentiment extraction failed: {exc}")
            return {'error': str(exc)}
    
    async def _analyze_sentiment(self, text: str) -> float:
        """Mock sentiment analysis - replace with real API call"""
        await asyncio.sleep(0.1)  # Simulate API latency
        return 0.5  # Neutral sentiment
```

### Built-in Extractor Example

The codebase includes a complete example in `js_embedded_data.py`:

```python
from crawlit.interfaces import Extractor
from crawlit.models import PageArtifact

class JSEmbeddedDataExtractor(Extractor):
    @property
    def name(self) -> str:
        return "js_embedded_data"

    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        try:
            return extract_js_embedded_data(html_content)
        except Exception as exc:
            logger.warning(f"JSEmbeddedDataExtractor failed for {artifact.url}: {exc}")
            artifact.errors.append(f"js_embedded_data extraction failed: {exc}")
            return {}
```

## Pipeline Plugin Development

Pipelines process fully-populated PageArtifacts and can modify, enrich, filter, or persist them.

### Basic Pipeline Interface

```python
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class CustomPipeline(Pipeline):
    @abstractmethod
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """
        Process the artifact and return it, or None to drop it
        """
        pass
```

### Example: Content Filter Pipeline

```python
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class ContentFilterPipeline(Pipeline):
    def __init__(self, min_content_length: int = 100, blocked_domains: list = None):
        self.min_content_length = min_content_length
        self.blocked_domains = set(blocked_domains or [])
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Filter artifacts based on content quality and domain"""
        
        # Check domain blacklist
        if any(domain in artifact.url for domain in self.blocked_domains):
            return None  # Drop this artifact
            
        # Check content length
        if len(artifact.content_info.text_content or "") < self.min_content_length:
            return None  # Drop short content
            
        # Add quality score
        quality_score = self._calculate_quality_score(artifact)
        if 'metadata' not in artifact.extracted:
            artifact.extracted['metadata'] = {}
        artifact.extracted['metadata']['quality_score'] = quality_score
        
        return artifact
    
    def _calculate_quality_score(self, artifact: PageArtifact) -> float:
        """Calculate content quality score"""
        score = 0.0
        
        # Factor in content length
        content_length = len(artifact.content_info.text_content or "")
        score += min(content_length / 1000, 1.0) * 0.3
        
        # Factor in number of links
        if artifact.extracted.get('links'):
            score += min(len(artifact.extracted['links']) / 10, 1.0) * 0.2
            
        # Factor in presence of structured data
        if artifact.extracted.get('structured_data'):
            score += 0.3
            
        # Factor in successful extraction count
        successful_extractions = sum(1 for key, value in artifact.extracted.items() 
                                   if value and not isinstance(value, dict) or 
                                   not value.get('error'))
        score += min(successful_extractions / 5, 1.0) * 0.2
        
        return min(score, 1.0)
```

### Example: Database Storage Pipeline

```python
import sqlite3
import json
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class DatabaseStoragePipeline(Pipeline):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS crawl_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    content_length INTEGER,
                    extracted_data TEXT,
                    crawled_at TIMESTAMP,
                    status_code INTEGER
                )
            ''')
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Store artifact in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO crawl_results 
                    (url, title, content_length, extracted_data, crawled_at, status_code)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    artifact.url,
                    artifact.content_info.title,
                    len(artifact.content_info.text_content or ""),
                    json.dumps(artifact.extracted),
                    artifact.crawl_meta.timestamp,
                    artifact.http_info.status_code
                ))
                
        except Exception as exc:
            artifact.errors.append(f"Database storage failed: {exc}")
            
        return artifact  # Always pass through
```

### Built-in Pipeline Example

The codebase includes `JSONLWriter` as a complete example:

```python
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class JSONLWriter(Pipeline):
    def __init__(self, path, append: bool = True):
        self._path = Path(path)
        self._append = append
        self._lock = threading.Lock()

    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        try:
            line = json.dumps(artifact.to_dict(), ensure_ascii=False, default=str)
            with self._lock:
                if self._fh is None:
                    self._open()
                self._fh.write(line + "\n")
        except Exception as exc:
            logger.warning(f"JSONLWriter failed for {artifact.url}: {exc}")
        return artifact
```

## Fetcher Plugin Development

Fetchers handle HTTP requests and return normalized FetchResult objects. They're useful for custom authentication, proxy rotation, or mock responses.

### Basic Fetcher Interface

```python
from typing import Dict, Optional
from crawlit.interfaces import Fetcher, FetchResult

class CustomFetcher(Fetcher):
    @abstractmethod
    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> FetchResult:
        """Fetch URL and return normalized result"""
        pass
```

### Example: Authenticated Fetcher

```python
import requests
from typing import Dict, Optional
from crawlit.interfaces import Fetcher, FetchResult

class AuthenticatedFetcher(Fetcher):
    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> FetchResult:
        """Fetch with API key authentication"""
        request_headers = {
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'crawlit-authenticated/1.0'
        }
        
        if headers:
            request_headers.update(headers)
            
        try:
            response = self.session.get(
                url, 
                headers=request_headers,
                timeout=self.timeout
            )
            
            return FetchResult(
                success=response.status_code < 400,
                url=response.url,
                status_code=response.status_code,
                headers=dict(response.headers),
                content_type=response.headers.get('Content-Type'),
                text=response.text if 'text' in response.headers.get('Content-Type', '') else None,
                raw_bytes=response.content,
                elapsed_ms=response.elapsed.total_seconds() * 1000,
                response_bytes=len(response.content)
            )
            
        except Exception as exc:
            return FetchResult(
                success=False,
                url=url,
                error=str(exc)
            )
```

### Example: Mock Fetcher for Testing

```python
from typing import Dict, Optional
from crawlit.interfaces import Fetcher, FetchResult

class MockFetcher(Fetcher):
    def __init__(self):
        self.responses = {}
        
    def set_response(self, url: str, html_content: str, status_code: int = 200):
        """Set mock response for a URL"""
        self.responses[url] = {
            'content': html_content,
            'status_code': status_code
        }
    
    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> FetchResult:
        """Return mock response"""
        if url in self.responses:
            mock_resp = self.responses[url]
            return FetchResult(
                success=mock_resp['status_code'] < 400,
                url=url,
                status_code=mock_resp['status_code'],
                text=mock_resp['content'],
                content_type='text/html'
            )
        else:
            return FetchResult(
                success=False,
                url=url,
                status_code=404,
                error="URL not found in mock responses"
            )
```

## Plugin Registration and Lifecycle

### Registering Plugins

Plugins are registered when creating a Crawler instance:

```python
from crawlit import Crawler

# Create plugin instances
price_extractor = PriceExtractor()
content_filter = ContentFilterPipeline(min_content_length=200)
auth_fetcher = AuthenticatedFetcher(api_key="your-key")

# Register with crawler
crawler = Crawler(
    start_url="https://example.com",
    extractors=[price_extractor, js_extractor],
    pipelines=[content_filter, db_storage],
    fetcher=auth_fetcher
)

# For async crawler
from crawlit import AsyncCrawler

async_crawler = AsyncCrawler(
    start_url="https://example.com",
    extractors=[async_sentiment_extractor],  # Can mix sync and async
    pipelines=[storage_pipeline],
    fetcher=async_auth_fetcher
)
```

### Plugin Execution Order

1. **Fetcher**: Called first to retrieve page content
2. **Extractors**: All extractors process the HTML concurrently
3. **Pipelines**: Execute sequentially in registration order

### Error Handling

Plugins should handle errors gracefully:

```python
def extract(self, html_content: str, artifact: PageArtifact) -> dict:
    try:
        # Your extraction logic
        return extracted_data
    except Exception as exc:
        # Log error to artifact
        artifact.errors.append(f"ExtractorName failed: {exc}")
        # Return empty result or partial data
        return {}
```

## Best Practices

### Design Guidelines

1. **Single Responsibility**: Each plugin should have one clear purpose
2. **Robust Error Handling**: Always handle exceptions gracefully
3. **Performance Awareness**: Minimize processing time for large crawls
4. **Resource Management**: Clean up connections, files, etc.
5. **Thread Safety**: Use locks for shared resources in sync plugins

### Code Style

```python
class WellDesignedExtractor(Extractor):
    def __init__(self, config: dict = None):
        # Validate configuration
        self.config = config or {}
        self._validate_config()
    
    @property
    def name(self) -> str:
        return "well_designed"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        """Extract data with clear documentation"""
        try:
            # Validate inputs
            if not html_content or not html_content.strip():
                return {}
                
            # Process with clear steps
            soup = self._parse_html(html_content)
            raw_data = self._extract_raw_data(soup)
            processed_data = self._process_data(raw_data)
            
            # Return structured result
            return {
                'data': processed_data,
                'metadata': {
                    'extracted_at': artifact.crawl_meta.timestamp.isoformat(),
                    'extractor_version': '1.0.0'
                }
            }
            
        except Exception as exc:
            logger.warning(f"Extraction failed for {artifact.url}: {exc}")
            artifact.errors.append(f"{self.name} extraction failed: {exc}")
            return {'error': str(exc)}
    
    def _validate_config(self):
        """Validate plugin configuration"""
        # Implementation details
        pass
```

### Performance Tips

1. **Lazy Imports**: Import heavy dependencies only when needed
2. **Caching**: Cache compiled regexes, parsers, etc.
3. **Batch Processing**: Process multiple items together when possible
4. **Async Where Possible**: Use async variants for I/O operations

## Testing Custom Plugins

### Unit Testing Framework

```python
import unittest
from crawlit.models import PageArtifact, HTTPInfo, ContentInfo, CrawlMeta
from datetime import datetime

class TestPriceExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = PriceExtractor()
        self.sample_html = """
        <div class="price">$29.99</div>
        <span class="cost">€45.50</span>
        """
        
        # Create mock artifact
        self.artifact = PageArtifact(
            url="https://example.com/test",
            http_info=HTTPInfo(status_code=200),
            content_info=ContentInfo(text_content="test content"),
            crawl_meta=CrawlMeta(timestamp=datetime.now())
        )
    
    def test_price_extraction(self):
        """Test basic price extraction"""
        result = self.extractor.extract(self.sample_html, self.artifact)
        
        self.assertIn('raw_prices', result)
        self.assertEqual(len(result['raw_prices']), 2)
        self.assertIn('$29.99', result['raw_prices'])
        self.assertIn('€45.50', result['raw_prices'])
    
    def test_empty_content(self):
        """Test handling of empty content"""
        result = self.extractor.extract("", self.artifact)
        self.assertEqual(result['count'], 0)
    
    def test_error_handling(self):
        """Test error handling with malformed HTML"""
        malformed_html = "<div><broken>"
        result = self.extractor.extract(malformed_html, self.artifact)
        # Should not raise exception
        self.assertIsInstance(result, dict)
```

### Integration Testing

```python
def test_extractor_integration():
    """Test extractor with real crawler"""
    from crawlit import Crawler
    
    # Use mock fetcher for predictable testing
    mock_fetcher = MockFetcher()
    mock_fetcher.set_response(
        "https://example.com",
        "<div class='price'>$19.99</div>"
    )
    
    # Create crawler with plugins
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=1,
        extractors=[PriceExtractor()],
        pipelines=[TestPipeline()],
        fetcher=mock_fetcher
    )
    
    crawler.crawl()
    results = crawler.get_results()
    
    # Verify extraction worked
    page_data = results["https://example.com"]
    assert "prices" in page_data["extracted"]
    assert "$19.99" in page_data["extracted"]["prices"]["raw_prices"]
```

## Performance Considerations

### Memory Management

```python
class EfficientExtractor(Extractor):
    def __init__(self, max_content_size: int = 1_000_000):
        self.max_content_size = max_content_size
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        # Truncate large content to prevent memory issues
        if len(html_content) > self.max_content_size:
            html_content = html_content[:self.max_content_size]
            
        # Use generators for large datasets
        for item in self._extract_items(html_content):
            yield self._process_item(item)
```

### Concurrency Considerations

```python
import threading
from crawlit.interfaces import Pipeline

class ThreadSafePipeline(Pipeline):
    def __init__(self):
        self._lock = threading.Lock()
        self._shared_resource = {}
    
    def process(self, artifact: PageArtifact) -> PageArtifact:
        with self._lock:
            # Access shared resource safely
            self._shared_resource[artifact.url] = artifact.to_dict()
        return artifact
```

### Async Performance

```python
import aiofiles
from crawlit.interfaces import AsyncPipeline

class AsyncFilePipeline(AsyncPipeline):
    async def process(self, artifact: PageArtifact) -> PageArtifact:
        # Use async file operations
        async with aiofiles.open(f"output/{artifact.url_hash}.json", 'w') as f:
            await f.write(json.dumps(artifact.to_dict()))
        return artifact
```

## Plugin Examples

### E-commerce Data Extractor

```python
class EcommerceExtractor(Extractor):
    @property
    def name(self) -> str:
        return "ecommerce"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        product_data = {
            'name': self._extract_product_name(soup),
            'price': self._extract_price(soup),
            'availability': self._extract_availability(soup),
            'rating': self._extract_rating(soup),
            'reviews': self._extract_review_count(soup),
            'images': self._extract_product_images(soup),
            'description': self._extract_description(soup)
        }
        
        return {k: v for k, v in product_data.items() if v is not None}
```

### SEO Analysis Pipeline

```python
class SEOAnalysisPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> PageArtifact:
        seo_data = {
            'title_length': len(artifact.content_info.title or ""),
            'meta_description_length': len(artifact.content_info.meta_description or ""),
            'h1_count': len(artifact.extracted.get('headings', {}).get('h1', [])),
            'internal_links': self._count_internal_links(artifact),
            'external_links': self._count_external_links(artifact),
            'image_alt_missing': self._count_images_without_alt(artifact),
        }
        
        if 'seo' not in artifact.extracted:
            artifact.extracted['seo'] = {}
        artifact.extracted['seo'].update(seo_data)
        
        return artifact
```

### Rate-Limited API Fetcher

```python
import time
from crawlit.interfaces import Fetcher

class RateLimitedApiFetcher(Fetcher):
    def __init__(self, api_key: str, requests_per_minute: int = 60):
        self.api_key = api_key
        self.min_interval = 60.0 / requests_per_minute
        self.last_request = 0
        
    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> FetchResult:
        # Enforce rate limiting
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
            
        self.last_request = time.time()
        
        # Make authenticated request
        auth_headers = {'X-API-Key': self.api_key}
        if headers:
            auth_headers.update(headers)
            
        return self._make_request(url, auth_headers)
```

## Plugin Distribution and Packaging

### Package Structure

```
my_crawlit_plugin/
├── setup.py
├── README.md
├── requirements.txt
├── my_crawlit_plugin/
│   ├── __init__.py
│   ├── extractors.py
│   ├── pipelines.py
│   └── fetchers.py
└── tests/
    ├── test_extractors.py
    ├── test_pipelines.py
    └── test_fetchers.py
```

### setup.py Example

```python
from setuptools import setup, find_packages

setup(
    name="my-crawlit-plugin",
    version="1.0.0",
    description="Custom extractors and pipelines for crawlit",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "crawlit>=1.0.0",
        "beautifulsoup4",
        "requests",
    ],
    extras_require={
        "dev": ["pytest", "pytest-asyncio"],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8+",
    ],
)
```

### Entry Points for Discovery

```python
# In setup.py
entry_points={
    "crawlit.extractors": [
        "ecommerce = my_crawlit_plugin.extractors:EcommerceExtractor",
        "seo = my_crawlit_plugin.extractors:SEOExtractor",
    ],
    "crawlit.pipelines": [
        "database = my_crawlit_plugin.pipelines:DatabasePipeline",
        "analytics = my_crawlit_plugin.pipelines:AnalyticsPipeline",
    ],
}
```

### Plugin Registry

```python
# Allow plugins to register themselves
class PluginRegistry:
    _extractors = {}
    _pipelines = {}
    _fetchers = {}
    
    @classmethod
    def register_extractor(cls, name: str, extractor_class):
        cls._extractors[name] = extractor_class
    
    @classmethod
    def get_extractor(cls, name: str):
        return cls._extractors.get(name)
    
    @classmethod
    def list_extractors(cls):
        return list(cls._extractors.keys())

# Usage
PluginRegistry.register_extractor("prices", PriceExtractor)
price_extractor = PluginRegistry.get_extractor("prices")()
```

This comprehensive guide covers all aspects of developing, testing, and distributing plugins for crawlit. The plugin architecture provides powerful extension points while maintaining clean interfaces and good performance characteristics.