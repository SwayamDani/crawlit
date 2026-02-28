# API Reference

This comprehensive reference documents all public classes, methods, and functions in the crawlit library.

## Table of Contents

- [Core Crawler Classes](#core-crawler-classes)
  - [Crawler](#crawler)
  - [AsyncCrawler](#asynccrawler)
- [Configuration](#configuration)
  - [CrawlerConfig](#crawlerconfig)
  - [FetchConfig](#fetchconfig)
  - [RateLimitConfig](#ratelimitconfig)
  - [OutputConfig](#outputconfig)
- [Data Models](#data-models)
  - [PageArtifact](#pageartifact)
  - [CrawlJob](#crawljob)
  - [HTTPInfo](#httpinfo)
  - [ContentInfo](#contentinfo)
  - [CrawlError](#crawlerror)
- [Plugin Interfaces](#plugin-interfaces)
  - [Extractor/AsyncExtractor](#extractorasyncextractor)
  - [Pipeline/AsyncPipeline](#pipelineasyncpipeline)
  - [Fetcher/AsyncFetcher](#fetcherasyncfetcher)
- [Built-in Extractors](#built-in-extractors)
- [Built-in Pipelines](#built-in-pipelines)
- [Utility Classes](#utility-classes)
- [Fetcher Implementations](#fetcher-implementations)
- [Security Features](#security-features)
- [Distributed Crawling](#distributed-crawling)
- [Error Handling](#error-handling)

---

## Core Crawler Classes

### Crawler

**Class:** `crawlit.Crawler`

The main synchronous crawler class that manages the crawling process.

#### Constructor

```python
Crawler(
    start_url: str,
    max_depth: int = 3,
    internal_only: bool = True,
    user_agent: str = "crawlit/1.0",
    max_retries: int = 3,
    timeout: int = 10,
    delay: float = 0.1,
    respect_robots: bool = True,
    enable_image_extraction: bool = False,
    enable_keyword_extraction: bool = False,
    enable_table_extraction: bool = False,
    enable_content_extraction: bool = False,
    same_path_only: bool = False,
    max_queue_size: Optional[int] = None,
    max_workers: Optional[int] = 1,
    progress_tracker: Optional[ProgressTracker] = None,
    url_filter: Optional[URLFilter] = None,
    session_manager: Optional[SessionManager] = None,
    page_cache: Optional[PageCache] = None,
    storage_manager: Optional[StorageManager] = None,
    store_html_content: bool = True,
    use_sitemap: bool = False,
    sitemap_urls: Optional[List[str]] = None,
    rate_limiter: Optional[RateLimiter] = None,
    use_per_domain_delay: bool = True,
    content_deduplicator: Optional[ContentDeduplicator] = None,
    enable_content_deduplication: bool = False,
    use_js_rendering: bool = False,
    # ... additional parameters
)
```

#### Parameters

- **start_url** (`str`): The starting URL for the crawler
- **max_depth** (`int`, default=3): Maximum depth of crawling from the start URL
- **internal_only** (`bool`, default=True): Whether to restrict crawling to the same domain
- **user_agent** (`str`, default="crawlit/1.0"): User-Agent string for HTTP requests
- **max_retries** (`int`, default=3): Maximum number of retry attempts for failed requests
- **timeout** (`int`, default=10): Request timeout in seconds
- **delay** (`float`, default=0.1): Delay between requests in seconds
- **respect_robots** (`bool`, default=True): Whether to respect robots.txt rules
- **max_workers** (`int`, default=1): Number of worker threads for concurrent crawling

#### Methods

##### `crawl()`

```python
def crawl() -> None
```

Start the crawling process. This method blocks until crawling is complete.

**Example:**
```python
from crawlit import Crawler

crawler = Crawler("https://example.com", max_depth=2)
crawler.crawl()
results = crawler.get_results()
```

##### `get_results()`

```python
def get_results() -> Dict[str, Dict[str, Any]]
```

Get the crawl results as a dictionary mapping URLs to extracted data.

**Returns:** Dictionary with URLs as keys and extracted page data as values.

##### `get_artifacts()`

```python
def get_artifacts() -> Dict[str, PageArtifact]
```

Get crawl results as PageArtifact objects for structured access.

**Returns:** Dictionary mapping URLs to PageArtifact instances.

##### `get_skipped_external_urls()`

```python
def get_skipped_external_urls() -> List[str]
```

Get list of external URLs that were skipped during crawling.

##### `is_valid_url()`

```python
def is_valid_url(self, url: str) -> bool
```

Check if a URL is valid according to the crawler's configuration.

**Parameters:**
- **url** (`str`): URL to validate

**Returns:** `True` if the URL is valid, `False` otherwise.

##### `pause()`

```python
def pause() -> None
```

Pause the crawling process. Can be resumed by calling `crawl()` again.

#### Attributes

- **start_url** (`str`): The starting URL
- **max_depth** (`int`): Maximum crawling depth
- **visited_urls** (`set`): Set of URLs already visited
- **results** (`dict`): Dictionary containing crawl results

---

### AsyncCrawler

**Class:** `crawlit.AsyncCrawler`

Asynchronous version of the crawler for high-performance concurrent crawling.

#### Constructor

```python
AsyncCrawler(
    start_url: str,
    max_depth: int = 3,
    internal_only: bool = True,
    user_agent: str = "crawlit/1.0",
    max_retries: int = 3,
    timeout: int = 10,
    delay: float = 0.1,
    respect_robots: bool = True,
    max_concurrent_requests: int = 5,
    # ... similar parameters to Crawler
)
```

#### Key Differences from Crawler

- **max_concurrent_requests** (`int`, default=5): Maximum number of concurrent HTTP requests
- All methods return awaitable coroutines
- Uses async/await syntax

#### Methods

##### `crawl()`

```python
async def crawl() -> None
```

Start the asynchronous crawling process.

**Example:**
```python
import asyncio
from crawlit import AsyncCrawler

async def main():
    crawler = AsyncCrawler("https://example.com", max_concurrent_requests=10)
    await crawler.crawl()
    results = crawler.get_results()

asyncio.run(main())
```

---

## Configuration

### CrawlerConfig

**Class:** `crawlit.config.CrawlerConfig`

Composable configuration object for crawler settings.

```python
@dataclasses.dataclass
class CrawlerConfig:
    start_url: str = ""
    max_depth: int = 3
    internal_only: bool = True
    same_path_only: bool = False
    respect_robots: bool = True
    max_queue_size: Optional[int] = None
    max_workers: Optional[int] = 1
    max_concurrent_requests: int = 5
    
    # Sub-configurations
    fetch: FetchConfig = field(default_factory=FetchConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    # Feature flags
    enable_image_extraction: bool = False
    enable_keyword_extraction: bool = False
    enable_table_extraction: bool = False
    enable_content_extraction: bool = False
    enable_content_deduplication: bool = False
    
    # Budget limits
    max_pages: Optional[int] = None
    max_bytes: Optional[int] = None
    max_time_seconds: Optional[float] = None
```

**Example:**
```python
from crawlit import Crawler
from crawlit.config import CrawlerConfig, FetchConfig, OutputConfig

config = CrawlerConfig(
    start_url="https://example.com",
    max_depth=5,
    fetch=FetchConfig(timeout=30, user_agent="MyBot/2.0"),
    output=OutputConfig(
        write_jsonl=True,
        jsonl_path="output/crawl.jsonl"
    ),
    enable_content_extraction=True
)

crawler = Crawler(config=config)
```

### FetchConfig

**Class:** `crawlit.config.FetchConfig`

Configuration for HTTP fetching behavior.

```python
@dataclasses.dataclass
class FetchConfig:
    user_agent: str = "crawlit/1.0"
    max_retries: int = 3
    timeout: int = 10
    verify_ssl: bool = True
    proxy: Optional[str] = None
    
    # JavaScript rendering
    use_js_rendering: bool = False
    js_wait_for_selector: Optional[str] = None
    js_wait_for_timeout: Optional[int] = None
    js_browser_type: str = "chromium"
```

### RateLimitConfig

**Class:** `crawlit.config.RateLimitConfig`

Configuration for rate limiting behavior.

```python
@dataclasses.dataclass
class RateLimitConfig:
    delay: float = 0.1
    use_per_domain_delay: bool = True
    respect_robots_crawl_delay: bool = True
```

### OutputConfig

**Class:** `crawlit.config.OutputConfig`

Configuration for output and persistence.

```python
@dataclasses.dataclass
class OutputConfig:
    store_html_content: bool = True
    enable_disk_storage: bool = False
    storage_dir: Optional[str] = None
    
    # JSONL output
    write_jsonl: bool = False
    jsonl_path: Optional[str] = None
    
    # Blob storage
    write_blobs: bool = False
    blobs_dir: Optional[str] = None
    
    # Edge list
    write_edges: bool = False
    edges_path: Optional[str] = None
```

---

## Data Models

### PageArtifact

**Class:** `crawlit.models.PageArtifact`

Main data structure representing a crawled page with all extracted information.

```python
@dataclasses.dataclass
class PageArtifact:
    url: str
    html_content: Optional[str] = None
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    
    # Structured extraction results
    extracted: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    http: HTTPInfo = field(default_factory=HTTPInfo)
    content: ContentInfo = field(default_factory=ContentInfo)
    crawl: CrawlMeta = field(default_factory=CrawlMeta)
    download: Optional[DownloadRecord] = None
    
    # Error tracking
    errors: List[CrawlError] = field(default_factory=list)
```

#### Methods

##### `to_dict()`

```python
def to_dict() -> Dict[str, Any]
```

Convert the artifact to a dictionary for serialization.

##### `add_error()`

```python
def add_error(self, error: CrawlError) -> None
```

Add an error to the artifact's error list.

##### `has_errors()`

```python
def has_errors(self) -> bool
```

Check if the artifact has any errors.

**Example:**
```python
from crawlit import Crawler

crawler = Crawler("https://example.com")
crawler.crawl()

artifacts = crawler.get_artifacts()
for url, artifact in artifacts.items():
    print(f"URL: {artifact.url}")
    print(f"Title: {artifact.title}")
    print(f"Status: {artifact.status_code}")
    
    if artifact.extracted.get("tables"):
        print(f"Tables found: {len(artifact.extracted['tables'])}")
```

### CrawlJob

**Class:** `crawlit.models.CrawlJob`

Metadata about a complete crawl run.

```python
@dataclasses.dataclass
class CrawlJob:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: Optional[datetime] = None
    seed_urls: List[str] = field(default_factory=list)
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
```

### HTTPInfo

**Class:** `crawlit.models.HTTPInfo`

HTTP response metadata and timing information.

```python
@dataclasses.dataclass
class HTTPInfo:
    status: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: Optional[str] = None
    redirected_from: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    cache_control: Optional[str] = None
    elapsed_ms: Optional[float] = None
```

### ContentInfo

**Class:** `crawlit.models.ContentInfo`

Content analysis and metadata.

```python
@dataclasses.dataclass
class ContentInfo:
    size_bytes: Optional[int] = None
    text_content: Optional[str] = None
    language: Optional[str] = None
    charset: Optional[str] = None
    content_hash: Optional[str] = None
```

### CrawlError

**Class:** `crawlit.models.CrawlError`

Structured error information.

```python
@dataclasses.dataclass
class CrawlError:
    code: str
    message: str
    source: Optional[str] = None
    http_status: Optional[int] = None
```

#### Class Methods

##### `fetch()`

```python
@classmethod
def fetch(cls, message: str, http_status: Optional[int] = None) -> "CrawlError"
```

Create a fetch/HTTP error.

##### `extractor()`

```python
@classmethod
def extractor(cls, name: str, message: str) -> "CrawlError"
```

Create an extractor error.

##### `pipeline()`

```python
@classmethod
def pipeline(cls, name: str, message: str) -> "CrawlError"
```

Create a pipeline error.

---

## Plugin Interfaces

### Extractor/AsyncExtractor

**Classes:** `crawlit.interfaces.Extractor`, `crawlit.interfaces.AsyncExtractor`

Base classes for creating custom content extractors.

#### Extractor

```python
from abc import ABC, abstractmethod

class Extractor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this extractor."""
        
    @abstractmethod
    def extract(self, html_content: str, artifact: PageArtifact) -> Any:
        """Extract data from HTML content."""
```

#### AsyncExtractor

```python
class AsyncExtractor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this extractor."""
        
    @abstractmethod
    async def extract(self, html_content: str, artifact: PageArtifact) -> Any:
        """Extract data from HTML content asynchronously."""
```

**Example:**
```python
from crawlit.interfaces import Extractor
from crawlit.models import PageArtifact
from bs4 import BeautifulSoup

class PriceExtractor(Extractor):
    @property
    def name(self) -> str:
        return "prices"
    
    def extract(self, html_content: str, artifact: PageArtifact):
        soup = BeautifulSoup(html_content, 'html.parser')
        prices = []
        
        for price_elem in soup.select('.price'):
            price_text = price_elem.get_text().strip()
            # Parse price...
            prices.append({"text": price_text})
        
        return prices

# Use with crawler
from crawlit import Crawler

crawler = Crawler(
    "https://shop.example.com",
    extractors=[PriceExtractor()]
)
```

### Pipeline/AsyncPipeline

**Classes:** `crawlit.interfaces.Pipeline`, `crawlit.interfaces.AsyncPipeline`

Base classes for creating custom processing pipelines.

#### Pipeline

```python
class Pipeline(ABC):
    @abstractmethod
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Process an artifact. Return None to filter it out."""
```

#### AsyncPipeline  

```python
class AsyncPipeline(ABC):
    @abstractmethod
    async def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Process an artifact asynchronously."""
```

**Example:**
```python
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class FilterByCategoryPipeline(Pipeline):
    def __init__(self, categories):
        self.categories = categories
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Filter based on extracted category
        extracted_category = artifact.extracted.get("category")
        if extracted_category in self.categories:
            return artifact
        return None  # Filter out

# Usage
crawler = Crawler(
    "https://example.com",
    pipelines=[FilterByCategoryPipeline(["electronics", "books"])]
)
```

### Fetcher/AsyncFetcher

**Classes:** `crawlit.interfaces.Fetcher`, `crawlit.interfaces.AsyncFetcher`

Custom HTTP fetching implementations.

#### FetchRequest

```python
@dataclasses.dataclass
class FetchRequest:
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Optional[Dict[str, str]] = None
    body: Optional[bytes] = None
    timeout: Optional[int] = None
    allow_js: bool = False
    cookies: Optional[Dict[str, str]] = None
    proxy: Optional[str] = None
    retries: int = 3
```

#### FetchResult

```python
@dataclasses.dataclass
class FetchResult:
    success: bool = False
    url: str = ""
    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: Optional[str] = None
    text: Optional[str] = None
    raw_bytes: Optional[bytes] = None
    error: Optional[str] = None
    not_modified: bool = False
    elapsed_ms: Optional[float] = None
    response_bytes: Optional[int] = None
```

#### Fetcher Interface

```python
class Fetcher(ABC):
    @abstractmethod
    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> FetchResult:
        """Fetch a URL and return result."""
```

---

## Built-in Extractors

### Table Extraction

#### `extract_tables()`

```python
def extract_tables(
    html_content: str,
    min_rows: int = 1,
    min_columns: int = 1
) -> List[List[List[str]]]
```

Extract HTML tables from content.

**Parameters:**
- **html_content** (`str`): HTML content to parse
- **min_rows** (`int`): Minimum rows required for table inclusion
- **min_columns** (`int`): Minimum columns required

**Returns:** List of tables, each table is a list of rows, each row is a list of cell values.

**Example:**
```python
from crawlit import Crawler

crawler = Crawler(
    "https://example.com",
    enable_table_extraction=True
)
crawler.crawl()

# Tables available in artifact.extracted["tables"]
for url, artifact in crawler.get_artifacts().items():
    tables = artifact.extracted.get("tables", [])
    print(f"Found {len(tables)} tables in {url}")
```

#### Helper Functions

##### `tables_to_csv()`

```python
def tables_to_csv(tables: List[List[List[str]]], output_dir: str) -> List[str]
```

Save tables as CSV files.

##### `tables_to_dict()`

```python
def tables_to_dict(table: List[List[str]], has_header: bool = True) -> List[Dict[str, str]]
```

Convert table to list of dictionaries.

### Image Extraction

#### `ImageTagParser`

```python
class ImageTagParser:
    def parse_images(self, html_content: str, base_url: str = "") -> List[Dict[str, Any]]
```

Extract image information from HTML.

### Keyword Extraction

#### `KeywordExtractor`

```python
class KeywordExtractor:
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]
```

Extract keywords from text content.

### Form Extraction

#### `extract_forms()`

```python
def extract_forms(html_content: str) -> List[Form]
```

Extract form information from HTML.

#### `Form` and `FormField`

```python
@dataclasses.dataclass
class FormField:
    name: str
    field_type: str
    value: str
    required: bool
    
@dataclasses.dataclass
class Form:
    action: str
    method: str
    fields: List[FormField]
```

### Structured Data Extraction

#### `extract_structured_data()`

```python
def extract_structured_data(html_content: str) -> List[StructuredData]
```

Extract JSON-LD, microdata, and RDFa structured data.

### Language Detection

#### `detect_language()`

```python
def detect_language(text: str) -> LanguageDetection
```

Detect the language of text content.

### PDF Extraction

#### `extract_pdf_text()`

```python
def extract_pdf_text(pdf_content: bytes) -> str
```

Extract text from PDF content.

#### `is_pdf_available()`

```python
def is_pdf_available() -> bool
```

Check if PDF extraction dependencies are available.

### JavaScript Embedded Data

#### `extract_js_embedded_data()`

```python
def extract_js_embedded_data(html_content: str) -> Dict[str, Any]
```

Extract data embedded in JavaScript variables and objects.

---

## Built-in Pipelines

### JSONLWriter

**Class:** `crawlit.pipelines.JSONLWriter`

Write artifacts as JSON Lines format.

```python
class JSONLWriter(Pipeline):
    def __init__(self, path, append: bool = True):
        """
        Write artifacts to JSONL file.
        
        Args:
            path: Output file path
            append: Append to existing file if True
        """
```

**Example:**
```python
from crawlit import Crawler
from crawlit.pipelines import JSONLWriter

crawler = Crawler(
    "https://example.com",
    pipelines=[JSONLWriter("output/crawl.jsonl")]
)
```

### BlobStore

**Class:** `crawlit.pipelines.BlobStore`

Store raw content (HTML, PDF) by content hash.

```python
class BlobStore(Pipeline):
    def __init__(self, directory: str):
        """Store content blobs in directory."""
```

### EdgesWriter

**Class:** `crawlit.pipelines.EdgesWriter`

Write navigation edges (from_url → to_url) to file.

```python
class EdgesWriter(Pipeline):
    def __init__(self, path: str):
        """Write link edges to file."""
```

### ArtifactStore

**Class:** `crawlit.pipelines.ArtifactStore`

Store structured artifacts in database or file system.

---

## Utility Classes

### RateLimiter / AsyncRateLimiter

**Classes:** `crawlit.utils.RateLimiter`, `crawlit.utils.AsyncRateLimiter`

Per-domain rate limiting.

```python
class RateLimiter:
    def __init__(self, default_delay: float = 0.1):
        """Initialize rate limiter."""
    
    def set_domain_delay(self, domain: str, delay: float) -> None:
        """Set custom delay for domain."""
    
    def wait_if_needed(self, url: str) -> None:
        """Wait if needed to respect rate limits."""
```

### URLFilter

**Class:** `crawlit.utils.URLFilter`

Filter URLs based on patterns and rules.

```python
class URLFilter:
    def should_crawl(self, url: str, base_url: str) -> bool:
        """Check if URL should be crawled."""
```

### ProgressTracker

**Class:** `crawlit.utils.ProgressTracker`

Track crawling progress and statistics.

```python
class ProgressTracker:
    def update(self, processed: int, total: int, current_url: str = "") -> None:
        """Update progress information."""
```

### SessionManager

**Class:** `crawlit.utils.SessionManager`

Manage HTTP sessions with authentication and cookies.

```python
class SessionManager:
    def get_session(self, domain: str) -> requests.Session:
        """Get session for domain."""
```

### ContentDeduplicator

**Class:** `crawlit.utils.ContentDeduplicator`

Detect and handle duplicate content.

```python
class ContentDeduplicator:
    def is_duplicate(self, content: str) -> bool:
        """Check if content is duplicate."""
```

### BudgetTracker / AsyncBudgetTracker

**Classes:** `crawlit.utils.BudgetTracker`, `crawlit.utils.AsyncBudgetTracker`

Track resource usage against configured limits.

```python
class BudgetTracker:
    def __init__(self, limits: BudgetLimits):
        """Initialize budget tracker."""
    
    def check_budget(self, pages: int, bytes_: int, time_: float) -> bool:
        """Check if within budget limits."""
```

### URLPriorityQueue / AsyncURLPriorityQueue

**Classes:** `crawlit.utils.URLPriorityQueue`, `crawlit.utils.AsyncURLPriorityQueue`

Priority-based URL queuing with pluggable strategies.

#### Priority Strategies

- **BreadthFirstStrategy**: Breadth-first traversal
- **DepthFirstStrategy**: Depth-first traversal  
- **SitemapPriorityStrategy**: Prioritize sitemap URLs
- **URLPatternStrategy**: Pattern-based prioritization
- **CompositeStrategy**: Combine multiple strategies

### SitemapParser

**Class:** `crawlit.utils.SitemapParser`

Parse XML sitemaps and extract URLs.

```python
class SitemapParser:
    def parse_sitemap(self, sitemap_content: str) -> List[str]:
        """Parse sitemap and return URLs."""
```

#### Helper Functions

##### `get_sitemaps_from_robots()`

```python
def get_sitemaps_from_robots(robots_url: str) -> List[str]
```

Extract sitemap URLs from robots.txt.

---

## Fetcher Implementations

### DefaultFetcher / DefaultAsyncFetcher

**Classes:** `crawlit.fetchers.DefaultFetcher`, `crawlit.fetchers.DefaultAsyncFetcher`

Built-in HTTP fetchers using requests/aiohttp.

```python
class DefaultFetcher(Fetcher):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = "crawlit/1.0",
        verify_ssl: bool = True,
        proxy: Optional[str] = None
    ):
        """Initialize default fetcher."""
```

---

## Security Features

### CSRF Protection

#### `CSRFTokenExtractor`

```python
class CSRFTokenExtractor:
    def extract_token(self, html_content: str) -> Optional[str]:
        """Extract CSRF token from HTML."""
```

#### `CSRFTokenHandler`

```python
class CSRFTokenHandler:
    def handle_csrf(self, session, response) -> None:
        """Handle CSRF token extraction and injection."""
```

### Security Headers Analysis

#### `analyze_security_headers()`

```python
def analyze_security_headers(headers: Dict[str, str]) -> SecurityRating
```

Analyze HTTP response headers for security indicators.

### WAF Detection

#### `detect_waf()`

```python
def detect_waf(response_headers: Dict[str, str], content: str) -> WAFType
```

Detect Web Application Firewall presence.

### Captcha Detection

#### `detect_captcha()`

```python
def detect_captcha(html_content: str) -> CaptchaType
```

Detect CAPTCHA challenges in HTML content.

### Honeypot Detection

#### `detect_honeypots()`

```python
def detect_honeypots(html_content: str) -> bool
```

Detect potential honeypot traps.

---

## Distributed Crawling

**Note:** Requires `crawlit[distributed]` installation.

### DistributedCrawler

**Class:** `crawlit.distributed.DistributedCrawler`

Crawler that coordinates with distributed workers.

```python
class DistributedCrawler:
    def __init__(self, message_queue: MessageQueue):
        """Initialize distributed crawler."""
```

### CrawlWorker

**Class:** `crawlit.distributed.CrawlWorker`

Worker process for distributed crawling.

```python
class CrawlWorker:
    def start(self) -> None:
        """Start worker process."""
```

### Message Queues

#### `RabbitMQBackend`

```python
class RabbitMQBackend(MessageQueue):
    def __init__(self, connection_url: str):
        """RabbitMQ message queue backend."""
```

#### `KafkaBackend`

```python
class KafkaBackend(MessageQueue):
    def __init__(self, bootstrap_servers: List[str]):
        """Kafka message queue backend."""
```

---

## Error Handling

### Exception Hierarchy

```python
class CrawlitError(Exception):
    """Base exception for crawlit."""

class FetchError(CrawlitError):
    """HTTP fetch related errors."""

class RobotsError(CrawlitError):
    """Robots.txt parsing errors."""

class ParseError(CrawlitError):
    """HTML parsing errors."""

class ExtractionError(CrawlitError):
    """Content extraction errors."""
```

### Error Handling Functions

#### `handle_fetch_error()`

```python
def handle_fetch_error(error: Exception, url: str) -> CrawlError
```

Convert fetch exceptions to structured errors.

---

## Constants and Enums

### Schema Version

```python
SCHEMA_VERSION = "1"  # PageArtifact schema version
```

### Error Codes

```python
ERROR_CODES = {
    "FETCH_ERROR",
    "HTTP_ERROR", 
    "TIMEOUT",
    "PARSE_ERROR",
    "EXTRACTOR_ERROR",
    "PIPELINE_ERROR",
    "PDF_ERROR",
    "INCREMENTAL",
    "UNKNOWN",
}
```

### Event Types

```python
EVENT_TYPES = {
    "CRAWL_START",
    "CRAWL_END", 
    "FETCH_RETRY",
    "FETCH_ERROR",
    "ROBOTS_REJECT",
    "PIPELINE_DROP",
    "PIPELINE_ERROR",
    "EXTRACTOR_ERROR",
    "INCREMENTAL_HIT",
    "DEDUPE_HIT",
}
```

---

## Usage Examples

### Basic Crawling

```python
from crawlit import Crawler

# Simple crawl
crawler = Crawler("https://example.com", max_depth=2)
crawler.crawl()

# Get results
artifacts = crawler.get_artifacts()
for url, artifact in artifacts.items():
    print(f"{url}: {artifact.title}")
```

### Advanced Configuration

```python
from crawlit import Crawler
from crawlit.config import CrawlerConfig, FetchConfig, OutputConfig
from crawlit.pipelines import JSONLWriter, BlobStore

config = CrawlerConfig(
    start_url="https://news.example.com",
    max_depth=3,
    fetch=FetchConfig(
        timeout=30,
        use_js_rendering=True
    ),
    output=OutputConfig(
        write_jsonl=True,
        jsonl_path="output/articles.jsonl",
        write_blobs=True,
        blobs_dir="output/content"
    ),
    enable_content_extraction=True,
    enable_table_extraction=True,
    max_pages=1000
)

crawler = Crawler(config=config)
crawler.crawl()
```

### Custom Extractors and Pipelines

```python
from crawlit import Crawler
from crawlit.interfaces import Extractor, Pipeline
from crawlit.models import PageArtifact

class ArticleExtractor(Extractor):
    @property
    def name(self) -> str:
        return "articles"
    
    def extract(self, html_content: str, artifact: PageArtifact):
        # Extract article-specific data
        return {"author": "...", "publish_date": "..."}

class DatabasePipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> PageArtifact:
        # Save to database
        return artifact

crawler = Crawler(
    "https://news.example.com",
    extractors=[ArticleExtractor()],
    pipelines=[DatabasePipeline()]
)
```

### Async Crawling

```python
import asyncio
from crawlit import AsyncCrawler

async def main():
    crawler = AsyncCrawler(
        "https://example.com",
        max_concurrent_requests=20,
        enable_content_extraction=True
    )
    
    await crawler.crawl()
    
    artifacts = crawler.get_artifacts()
    print(f"Crawled {len(artifacts)} pages")

asyncio.run(main())
```

This comprehensive API reference provides complete documentation of crawlit's public interface. For implementation details and examples, see the individual module documentation and the [Getting Started Guide](getting-started.md).