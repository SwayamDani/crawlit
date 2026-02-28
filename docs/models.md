# Crawlit Data Models

> **Comprehensive reference for understanding crawlit's data structures and schemas**

Crawlit uses a structured, versioned data model centered around the [`PageArtifact`](../crawlit/models/page_artifact.py) class. This approach replaces ad-hoc result dictionaries with consistent, type-safe data structures that work seamlessly across engines, extractors, and pipelines.

## Table of Contents

- [Core Architecture](#core-architecture)
- [PageArtifact - The Central Model](#pageartifact---the-central-model)
- [Nested Data Structures](#nested-data-structures)
- [Error Handling Model](#error-handling-model)
- [Job and Run Metadata](#job-and-run-metadata)
- [Data Validation and Type Safety](#data-validation-and-type-safety)
- [Serialization and Formats](#serialization-and-formats)
- [Model Evolution and Versioning](#model-evolution-and-versioning)
- [Integration with Extractors](#integration-with-extractors)
- [Integration with Pipelines](#integration-with-pipelines)
- [Custom Model Extensions](#custom-model-extensions)
- [Performance Considerations](#performance-considerations)
- [Working Examples](#working-examples)
- [Schema Reference](#schema-reference)
- [Migration Guide](#migration-guide)

## Core Architecture

Crawlit's data model follows these design principles:

- **Single Source of Truth**: All crawl results flow through `PageArtifact`
- **Immutable by Default**: Use `.copy()` for safe pipeline chaining
- **Structured Errors**: Replace string errors with typed `CrawlError` objects
- **Forward Compatibility**: Schema versioning enables gradual migration
- **Rich Metadata**: Capture HTTP timing, content metrics, and provenance
- **Extensible**: The `extracted` dict accommodates any extractor payload

```python
from crawlit.models import PageArtifact, CrawlError, HTTPInfo

# Every crawl result is a PageArtifact
artifact = PageArtifact(
    url="https://example.com",
    fetched_at=datetime.utcnow(),
    http=HTTPInfo(status=200, content_type="text/html"),
    content=ContentInfo(text="<html>...</html>"),
    extracted={"title": "Example Page", "links": ["https://..."]}
)
```

## PageArtifact - The Central Model

The `PageArtifact` dataclass is the cornerstone of crawlit's data model, representing a single crawled page with all associated metadata and extracted data.

### Core Fields

```python
@dataclasses.dataclass
class PageArtifact:
    schema_version: str = SCHEMA_VERSION  # Current: "1"
    url: str = ""                         # Canonical URL
    fetched_at: Optional[datetime] = None # UTC timestamp
    http: HTTPInfo                        # Response metadata
    content: ContentInfo                  # Content and storage
    source: ArtifactSource               # Discovery provenance
    links: List[str]                     # Outbound links found
    extracted: Dict[str, Any]            # Extractor payloads
    downloads: List[DownloadRecord]      # Downloaded files
    errors: List[CrawlError]             # Structured error log
    crawl: CrawlMeta                     # Navigation context
```

### Essential Properties

| Field | Type | Purpose |
|-------|------|---------|
| `url` | `str` | The canonical URL that was crawled |
| `fetched_at` | `datetime` | UTC timestamp of when the page was fetched |
| `http` | `HTTPInfo` | HTTP response metadata (status, headers, timing) |
| `content` | `ContentInfo` | Page content and storage metadata |
| `extracted` | `dict` | Structured data extracted by extractors |
| `errors` | `List[CrawlError]` | Non-fatal errors encountered during processing |

## Nested Data Structures

### HTTPInfo - Response Metadata

Captures comprehensive HTTP response information including performance metrics:

```python
@dataclasses.dataclass
class HTTPInfo:
    status: Optional[int] = None          # HTTP status code
    headers: Dict[str, str]               # Response headers
    content_type: Optional[str] = None    # MIME type
    redirected_from: Optional[str] = None # Original URL if redirected
    etag: Optional[str] = None            # ETag for caching
    last_modified: Optional[str] = None   # Last-Modified header
    cache_control: Optional[str] = None   # Cache-Control directives
    
    # Performance Metrics (milliseconds)
    elapsed_ms: Optional[float] = None    # Total request time
    ttfb_ms: Optional[float] = None       # Time to first byte
    
    # Size Metrics (bytes)
    response_bytes: Optional[int] = None  # Total bytes received
```

**Use Cases:**
- Performance monitoring and optimization
- Cache validation with ETags and Last-Modified
- Content-type based routing in pipelines
- Network debugging and retry logic

### ContentInfo - Page Content

Manages page content with flexible storage options:

```python
@dataclasses.dataclass
class ContentInfo:
    raw_html: Optional[str] = None        # Inline HTML content
    text: Optional[str] = None            # Extracted text content
    blob_path: Optional[str] = None       # External storage path
    blob_sha256: Optional[str] = None     # Content hash for deduplication
    encoding: Optional[str] = None        # Character encoding
    size_bytes: int = 0                   # Content size
```

**Storage Patterns:**
- **Inline**: Small pages stored in `raw_html`
- **External**: Large content referenced via `blob_path`
- **Encrypted**: Use `blob_sha256` for content verification

### ArtifactSource - Discovery Provenance

Tracks how and where URLs were discovered:

```python
@dataclasses.dataclass
class ArtifactSource:
    type: str = "unknown"                 # Discovery method
    site: Optional[str] = None            # Source domain/name
```

**Discovery Types:**
- `"seed"` - Directly provided start URL
- `"html_link"` - Found in `<a href>` on another page  
- `"sitemap"` - Discovered via sitemap.xml
- `"api"` - Injected programmatically
- `"unknown"` - Unclassified source

### DownloadRecord - File Downloads

Tracks files downloaded during crawling:

```python
@dataclasses.dataclass
class DownloadRecord:
    url: str = ""                         # Download URL
    bytes_downloaded: int = 0             # Size in bytes
    sha256: Optional[str] = None          # Content hash
    saved_path: Optional[str] = None      # Local file path
    parse_status: Optional[str] = None    # Processing result
    content_type: Optional[str] = None    # MIME type
    error: Optional[str] = None           # Error if failed
```

### CrawlMeta - Navigation Context

Provides crawl graph and discovery context:

```python
@dataclasses.dataclass
class CrawlMeta:
    depth: int = 0                        # Distance from seed URLs
    discovered_from: Optional[str] = None # Parent page URL
    discovery_method: Optional[str] = None # How it was found
    run_id: Optional[str] = None          # Job identifier
```

## Error Handling Model

### CrawlError - Structured Error Records

Replaces string error messages with typed, queryable error objects:

```python
@dataclasses.dataclass
class CrawlError:
    code: str                             # Canonical error code
    message: str                          # Human-readable description
    source: Optional[str] = None          # Component that failed
    http_status: Optional[int] = None     # HTTP status when relevant
```

### Error Categories

| Code | Description | Source | Use Case |
|------|-------------|---------|----------|
| `FETCH_ERROR` | Network/connection failure | engine | Retry logic |
| `HTTP_ERROR` | Non-success HTTP status | engine | Status-based filtering |
| `TIMEOUT` | Request timed out | engine | Performance tuning |
| `PARSE_ERROR` | HTML/XML parsing failed | engine | Content validation |
| `EXTRACTOR_ERROR` | Plugin extractor failed | extractor | Debug extraction |
| `PIPELINE_ERROR` | Pipeline stage failed | pipeline | Process monitoring |
| `PDF_ERROR` | PDF extraction failed | pdf_extractor | PDF handling |
| `INCREMENTAL` | 304 Not Modified | engine | Cache hits |

### Working with Errors

```python
from crawlit.models import CrawlError

# Add structured errors
artifact.add_error(CrawlError.fetch("Connection refused", 503))
artifact.add_error(CrawlError.extractor("pdf", "Corrupted PDF file"))

# Query errors by type
fetch_errors = [e for e in artifact.errors if e.code == "FETCH_ERROR"]
has_http_errors = any(e.code == "HTTP_ERROR" for e in artifact.errors)

# Error-based filtering in pipelines
def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
    if any(e.code in {"FETCH_ERROR", "HTTP_ERROR"} for e in artifact.errors):
        logger.warning(f"Skipping {artifact.url} due to fetch errors")
        return None
    return artifact
```

## Job and Run Metadata

### CrawlJob - Run-Level Context

Shared metadata across all artifacts from a single crawl job:

```python
@dataclasses.dataclass
class CrawlJob:
    run_id: str                           # UUID-based job identifier
    started_at: Optional[datetime] = None # Job start time
    seed_urls: List[str]                  # Starting URLs
    config_snapshot: Dict[str, Any]       # Configuration for reproducibility
```

**Usage Patterns:**
- Attach to crawler via `run_id` parameter
- Track crawl sessions across restarts
- Enable reproducible crawls with config snapshots
- Group artifacts by job in analytics

## Data Validation and Type Safety

### Built-in Validation

The `PageArtifact.validate_minimal()` method performs essential validation:

```python
def validate_minimal(self) -> List[str]:
    """Returns list of validation errors, empty = valid"""
    problems = []
    
    # URL validation
    if not self.url:
        problems.append("url is required")
    elif not self.url.startswith(("http://", "https://")):
        problems.append(f"url must start with http:// or https://")
    
    # Schema version check
    if self.schema_version != SCHEMA_VERSION:
        problems.append("schema_version mismatch")
    
    # Timestamp requirement
    if self.fetched_at is None:
        problems.append("fetched_at is required")
    
    return problems
```

### Custom Validation in Pipelines

```python
class ValidationPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        errors = artifact.validate_minimal()
        if errors:
            logger.error(f"Invalid artifact {artifact.url}: {errors}")
            return None  # Drop invalid artifacts
        
        # Custom business logic validation
        if not artifact.extracted.get("title"):
            artifact.add_error("Missing title extraction", "VALIDATION_ERROR")
        
        return artifact
```

### Type Safety with mypy

Crawlit's models are fully typed and mypy-compatible:

```python
# Type-safe extractor implementation
class TitleExtractor(Extractor):
    @property
    def name(self) -> str:
        return "title"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> Optional[str]:
        # Return type is enforced
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('title')
        return title_tag.text.strip() if title_tag else None
```

## Serialization and Formats

### JSON Serialization

The `to_dict()` method provides complete JSON serialization:

```python
# Convert to dictionary
data = artifact.to_dict()

# Serialize to JSON
import json
json_str = json.dumps(data, ensure_ascii=False, default=str)

# Human-readable JSON
pretty_json = json.dumps(data, indent=2, ensure_ascii=False, default=str)
```

### Serialization Features

- **DateTime Handling**: Automatic ISO 8601 formatting
- **Nested Dataclasses**: Recursive conversion to dictionaries
- **Error Objects**: Structured representation of `CrawlError` instances
- **Unicode Support**: `ensure_ascii=False` preserves international text

### Example Serialized Output

```json
{
  "schema_version": "1",
  "url": "https://example.com/article",
  "fetched_at": "2024-01-15T10:30:00.123456Z",
  "http": {
    "status": 200,
    "content_type": "text/html; charset=utf-8",
    "elapsed_ms": 245.7,
    "response_bytes": 15420
  },
  "content": {
    "size_bytes": 15420,
    "encoding": "utf-8",
    "blob_path": "/storage/content/abc123.html"
  },
  "extracted": {
    "title": "Example Article Title",
    "meta_description": "Article description...",
    "tables": [{"headers": ["Name", "Value"], "rows": [...]}]
  },
  "errors": [],
  "crawl": {
    "depth": 1,
    "run_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Model Evolution and Versioning

### Schema Versioning Strategy

Crawlit uses explicit schema versioning for forward compatibility:

```python
SCHEMA_VERSION = "1"  # Current schema version

class PageArtifact:
    schema_version: str = SCHEMA_VERSION
```

### Backward Compatibility

The `from_legacy_result()` method enables gradual migration:

```python
# Migrate from old result dictionaries
legacy_result = {
    "html_content": "<html>...",
    "status": 200,
    "links": ["https://..."],
    "title": "Page Title"
}

# Convert to modern PageArtifact
artifact = PageArtifact.from_legacy_result("https://example.com", legacy_result)
assert artifact.schema_version == "legacy"  # Special marker

# Validate and potentially upgrade
if artifact.schema_version == "legacy":
    artifact.schema_version = SCHEMA_VERSION
    artifact.fetched_at = datetime.utcnow()
```

### Version Migration Patterns

```python
def migrate_artifact(artifact: PageArtifact) -> PageArtifact:
    """Migrate artifacts to current schema version."""
    if artifact.schema_version == "legacy":
        # Upgrade from legacy format
        artifact.schema_version = SCHEMA_VERSION
        artifact.fetched_at = artifact.fetched_at or datetime.utcnow()
        # Add required fields...
    
    elif artifact.schema_version == "0":
        # Migrate from v0 to v1
        # Handle breaking changes...
        artifact.schema_version = "1"
    
    return artifact
```

## Integration with Extractors

### Extractor Interface

Extractors enrich artifacts by populating the `extracted` dictionary:

```python
from crawlit.interfaces import Extractor
from crawlit.models import PageArtifact

class PriceExtractor(Extractor):
    @property
    def name(self) -> str:
        return "prices"  # Key in artifact.extracted
    
    def extract(self, html_content: str, artifact: PageArtifact) -> List[dict]:
        # Parse prices from HTML
        prices = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for price_elem in soup.find_all(class_='price'):
            price_data = {
                'amount': float(price_elem.get('data-amount', 0)),
                'currency': price_elem.get('data-currency', 'USD'),
                'text': price_elem.text.strip()
            }
            prices.append(price_data)
        
        return prices
```

### Extractor Results in Artifacts

```python
# After extraction, the artifact contains:
artifact.extracted = {
    "prices": [
        {"amount": 19.99, "currency": "USD", "text": "$19.99"},
        {"amount": 29.99, "currency": "USD", "text": "$29.99"}
    ],
    "title": "Product Page",
    "meta_description": "Great products at low prices"
}
```

### Built-in Extractors

Common extractors populate standard keys:

| Extractor | Key | Data Type | Description |
|-----------|-----|-----------|-------------|
| Basic HTML | `title` | `str` | Page title |
| Basic HTML | `meta_description` | `str` | Meta description |
| Basic HTML | `images` | `List[dict]` | Image elements |
| Table | `tables` | `List[dict]` | HTML tables |
| PDF | `pdf_data` | `dict` | PDF text and metadata |
| JS Embedded | `js_embedded_data` | `dict` | JSON-LD, Next.js data |

## Integration with Pipelines

### Pipeline Interface

Pipelines receive fully-populated artifacts and can modify, persist, or filter them:

```python
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class ContentFilterPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Filter by content type
        if artifact.http.content_type != "text/html":
            return None  # Drop non-HTML content
        
        # Enrich with computed fields
        artifact.extracted['word_count'] = len(artifact.content.text.split())
        
        # Add processing timestamp
        artifact.extracted['processed_at'] = datetime.utcnow().isoformat()
        
        return artifact
```

### Safe Pipeline Chaining

Use `.copy()` to prevent pipeline interference:

```python
class SafePipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Create independent copy for modification
        modified = artifact.copy()
        
        # Safe to modify without affecting other pipelines
        modified.extracted['pipeline_id'] = self.__class__.__name__
        modified.extracted['processed_at'] = datetime.utcnow().isoformat()
        
        return modified
```

### Built-in Pipelines

| Pipeline | Purpose | Artifact Usage |
|----------|---------|----------------|
| `JSONLWriter` | Export to JSONL | Uses `artifact.to_dict()` |
| `BlobStore` | External storage | Updates `content.blob_path` |
| `EdgesWriter` | Link graph export | Uses `links` and `crawl.discovered_from` |
| `DatabaseWriter` | SQL persistence | Accesses all artifact fields |

## Custom Model Extensions

### Extending with Composition

Add domain-specific metadata without modifying core models:

```python
from dataclasses import dataclass
from crawlit.models import PageArtifact

@dataclass
class EcommerceArtifact:
    """E-commerce specific extension."""
    base: PageArtifact
    product_id: Optional[str] = None
    category: Optional[str] = None
    price_history: List[dict] = field(default_factory=list)
    
    def add_price_point(self, price: float, currency: str = "USD"):
        self.price_history.append({
            'price': price,
            'currency': currency,
            'recorded_at': datetime.utcnow().isoformat()
        })

# Usage in extractors
class EcommerceExtractor(Extractor):
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        # Extract e-commerce data
        ecommerce_data = {
            'product_id': extract_product_id(html_content),
            'category': extract_category(html_content),
            'current_price': extract_price(html_content)
        }
        return ecommerce_data
```

### Custom Artifact Builders

Create factory functions for domain-specific artifacts:

```python
def create_news_artifact(url: str, article_data: dict) -> PageArtifact:
    """Create artifact optimized for news articles."""
    artifact = PageArtifact(url=url, fetched_at=datetime.utcnow())
    
    # Standard news fields
    artifact.extracted.update({
        'headline': article_data.get('title'),
        'byline': article_data.get('author'),
        'publish_date': article_data.get('published'),
        'article_text': article_data.get('content'),
        'tags': article_data.get('tags', []),
        'category': article_data.get('section')
    })
    
    # News-specific metadata
    artifact.source.type = "news_feed"
    artifact.source.site = extract_publisher(url)
    
    return artifact
```

## Performance Considerations

### Memory Optimization

Large content should use external storage:

```python
class LargeContentPipeline(Pipeline):
    def __init__(self, size_threshold: int = 100_000):
        self.size_threshold = size_threshold
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        if artifact.content.size_bytes > self.size_threshold:
            # Move large content to blob storage
            if artifact.content.raw_html:
                blob_path = self.save_to_storage(artifact.content.raw_html)
                artifact.content.blob_path = blob_path
                artifact.content.raw_html = None  # Free memory
        
        return artifact
```

### Efficient Serialization

For high-throughput scenarios, consider streaming serialization:

```python
import orjson  # Fast JSON library

class FastJSONLWriter(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Use orjson for faster serialization
        data = artifact.to_dict()
        json_bytes = orjson.dumps(data)
        
        with open(self.output_path, 'ab') as f:
            f.write(json_bytes + b'\n')
        
        return artifact
```

### Selective Field Copying

Copy only required fields for memory efficiency:

```python
def lightweight_copy(artifact: PageArtifact) -> dict:
    """Create minimal copy with essential fields only."""
    return {
        'url': artifact.url,
        'status': artifact.http.status,
        'title': artifact.extracted.get('title'),
        'fetched_at': artifact.fetched_at.isoformat() if artifact.fetched_at else None
    }
```

## Working Examples

### Basic Artifact Creation

```python
from datetime import datetime
from crawlit.models import PageArtifact, HTTPInfo, ContentInfo

# Create a simple artifact
artifact = PageArtifact(
    url="https://example.com",
    fetched_at=datetime.utcnow(),
    http=HTTPInfo(
        status=200,
        content_type="text/html",
        elapsed_ms=150.5
    ),
    content=ContentInfo(
        raw_html="<html><title>Example</title></html>",
        size_bytes=1024,
        encoding='utf-8'
    )
)

# Validate the artifact
errors = artifact.validate_minimal()
if errors:
    print(f"Validation errors: {errors}")
```

### Processing Pipeline Example

```python
class ArticleProcessingPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Skip non-HTML content
        if not artifact.http.content_type.startswith("text/html"):
            return None
        
        # Extract word count
        if artifact.content.text:
            word_count = len(artifact.content.text.split())
            artifact.extracted['word_count'] = word_count
        
        # Add processing metadata
        artifact.extracted['processed_by'] = 'article_pipeline'
        artifact.extracted['processed_at'] = datetime.utcnow().isoformat()
        
        # Filter short articles
        if artifact.extracted.get('word_count', 0) < 100:
            logger.info(f"Skipping short article: {artifact.url}")
            return None
        
        return artifact
```

### Error Handling Example

```python
from crawlit.models import CrawlError

def robust_extraction(html_content: str, artifact: PageArtifact) -> PageArtifact:
    """Demonstrate error handling in extraction."""
    try:
        # Attempt extraction
        title = extract_title(html_content)
        artifact.extracted['title'] = title
    except Exception as e:
        artifact.add_error(
            CrawlError.extractor("title_extractor", f"Title extraction failed: {e}")
        )
    
    try:
        # Attempt table extraction
        tables = extract_tables(html_content)
        artifact.extracted['tables'] = tables
    except Exception as e:
        artifact.add_error(
            CrawlError.extractor("table_extractor", f"Table extraction failed: {e}")
        )
    
    return artifact
```

## Schema Reference

### Complete Field Reference

```yaml
PageArtifact:
  schema_version: str              # Schema version identifier
  url: str                         # Canonical page URL
  fetched_at: datetime | null      # UTC fetch timestamp
  
  http:                           # HTTP response metadata
    status: int | null             # HTTP status code
    headers: dict[str, str]        # Response headers
    content_type: str | null       # MIME type
    redirected_from: str | null    # Original URL if redirected
    etag: str | null               # ETag value
    last_modified: str | null      # Last-Modified header
    cache_control: str | null      # Cache-Control header
    elapsed_ms: float | null       # Total request time (ms)
    ttfb_ms: float | null          # Time to first byte (ms)
    response_bytes: int | null     # Response size (bytes)
  
  content:                        # Page content information
    raw_html: str | null           # Inline HTML content
    text: str | null               # Extracted text
    blob_path: str | null          # External storage path
    blob_sha256: str | null        # Content hash
    encoding: str | null           # Character encoding
    size_bytes: int                # Content size
  
  source:                         # Discovery provenance
    type: str                      # Discovery method
    site: str | null               # Source site/domain
  
  links: list[str]                # Outbound links found
  
  extracted: dict[str, any]       # Extractor payloads
  
  downloads: list[DownloadRecord] # Downloaded files
    - url: str                     # Download URL
      bytes_downloaded: int        # Size downloaded
      sha256: str | null           # Content hash
      saved_path: str | null       # Local file path
      parse_status: str | null     # Processing status
      content_type: str | null     # MIME type
      error: str | null            # Error message
  
  errors: list[CrawlError]        # Structured error records
    - code: str                    # Error code
      message: str                 # Error description
      source: str | null           # Error source component
      http_status: int | null      # HTTP status if applicable
  
  crawl:                          # Navigation context
    depth: int                     # Distance from seed
    discovered_from: str | null    # Parent page URL
    discovery_method: str | null   # How URL was found
    run_id: str | null             # Job identifier
```

### JSON Schema (Draft 7)

For external integrations, here's the JSON Schema specification:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PageArtifact",
  "type": "object",
  "required": ["schema_version", "url"],
  "properties": {
    "schema_version": {"type": "string"},
    "url": {"type": "string", "format": "uri"},
    "fetched_at": {"type": ["string", "null"], "format": "date-time"},
    "http": {
      "type": "object",
      "properties": {
        "status": {"type": ["integer", "null"]},
        "headers": {"type": "object"},
        "content_type": {"type": ["string", "null"]},
        "elapsed_ms": {"type": ["number", "null"]},
        "response_bytes": {"type": ["integer", "null"]}
      }
    },
    "content": {
      "type": "object", 
      "properties": {
        "raw_html": {"type": ["string", "null"]},
        "size_bytes": {"type": "integer"}
      }
    },
    "extracted": {"type": "object"},
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["code", "message"],
        "properties": {
          "code": {"type": "string"},
          "message": {"type": "string"},
          "source": {"type": ["string", "null"]},
          "http_status": {"type": ["integer", "null"]}
        }
      }
    }
  }
}
```

## Migration Guide

### From Legacy Results

If you're migrating from crawlit's legacy dictionary-based results:

```python
# Old format
legacy_result = {
    'url': 'https://example.com',
    'html_content': '<html>...',
    'status': 200,
    'title': 'Page Title',
    'links': ['https://...']
}

# Convert to PageArtifact
artifact = PageArtifact.from_legacy_result(
    url=legacy_result['url'], 
    result=legacy_result
)

# Update schema version after validation
if artifact.validate_minimal():
    artifact.schema_version = SCHEMA_VERSION
    artifact.fetched_at = datetime.utcnow()
```

### Upgrading Existing Code

1. **Replace result dictionaries** with `PageArtifact` instances
2. **Update extractors** to use the new interface
3. **Modify pipelines** to work with structured artifacts  
4. **Use structured errors** instead of string messages
5. **Leverage validation** for data quality assurance

### Best Practices for Migration

- **Gradual rollout**: Use `from_legacy_result()` during transition
- **Validation first**: Always validate artifacts after conversion
- **Error handling**: Convert string errors to `CrawlError` objects
- **Testing**: Verify pipeline compatibility with new models
- **Schema evolution**: Plan for future schema changes

---

This comprehensive model system enables crawlit to provide consistent, type-safe, and extensible data structures that scale from simple crawls to complex data processing pipelines. The structured approach ensures reliability, maintainability, and forward compatibility as your crawling requirements evolve.