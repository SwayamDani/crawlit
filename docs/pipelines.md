# Crawlit Pipeline System

The crawlit pipeline system provides a modular, extensible framework for processing web crawl data. Pipelines operate on fully-populated `PageArtifact` objects and can modify, enrich, filter, or persist crawl results. This guide covers the architecture, built-in components, and patterns for developing custom pipeline stages.

## Table of Contents

- [Pipeline Architecture](#pipeline-architecture)
- [Built-in Pipeline Components](#built-in-pipeline-components)  
- [Pipeline Interface and Base Classes](#pipeline-interface-and-base-classes)
- [Custom Pipeline Development](#custom-pipeline-development)
- [Pipeline Chaining and Order](#pipeline-chaining-and-order)
- [Data Transformation Patterns](#data-transformation-patterns)
- [Output Formatting Pipelines](#output-formatting-pipelines)
- [Storage Pipelines](#storage-pipelines)
- [Integration with Crawlers](#integration-with-crawlers)
- [Performance Considerations](#performance-considerations)
- [Examples of Complex Pipeline Workflows](#examples-of-complex-pipeline-workflows)

## Pipeline Architecture

### Data Flow Overview

The crawlit pipeline system follows a sequential processing model where each crawled page flows through a chain of processing stages:

```
PageArtifact → Pipeline1 → Pipeline2 → Pipeline3 → ... → Final Result
```

**Key characteristics:**

- **Sequential Processing**: Pipelines run in the order they are configured
- **Artifact Transformation**: Each stage can modify the `PageArtifact` or return `None` to drop it
- **Error Isolation**: Failing stages don't corrupt other pipeline stages (snapshot/restore)
- **Thread Safety**: Built-in pipelines use locks for concurrent access
- **Sync/Async Support**: Both synchronous and asynchronous pipeline stages are supported

### Core Concepts

1. **PageArtifact**: The standardized data structure containing crawl results, metadata, extracted data, and HTTP information
2. **Pipeline Stages**: Individual processing components that implement the `Pipeline` or `AsyncPipeline` interface
3. **Artifact Filtering**: Pipelines can drop artifacts by returning `None`
4. **State Preservation**: Each stage receives a copy of the artifact to prevent cross-stage corruption
5. **Event Logging**: Built-in tracking for pipeline success, errors, and dropped artifacts

## Built-in Pipeline Components

Crawlit provides four core pipeline implementations that handle common crawl output scenarios:

### JSONLWriter

Writes each `PageArtifact` as a single JSON line to a file for streaming processing.

```python
from crawlit.pipelines import JSONLWriter

# Basic usage
pipeline = JSONLWriter("output/crawl_results.jsonl")

# With custom options
pipeline = JSONLWriter(
    path="output/results.jsonl",
    append=True  # Default: True (resume-friendly)
)
```

**Features:**
- Thread-safe concurrent writes with locking
- Automatic directory creation
- Resume-friendly append mode
- UTF-8 encoding with `ensure_ascii=False`
- Automatic file handle management

**Output Format:**
```json
{"url": "https://example.com", "content": {"text": "..."}, "extracted": {...}}
{"url": "https://example.com/page2", "content": {"text": "..."}, "extracted": {...}}
```

### BlobStore

Content-addressed storage for raw HTML and PDF content with deduplication support.

```python
from crawlit.pipelines import BlobStore
from crawlit.utils import ContentHashStore

# Basic blob storage
blob_store = BlobStore("./blobs")

# With cross-run deduplication
hash_store = ContentHashStore("./dedup.db")
blob_store = BlobStore("./blobs", hash_store=hash_store)
```

**Storage Layout:**
```
blobs/
├── html/
│   ├── ab/
│   │   └── abc123...def.html
│   └── cd/
│       └── cdef456...789.html
└── pdf/
    ├── 12/
    │   └── 123abc...xyz.pdf
    └── 34/
        └── 345def...abc.pdf
```

**Features:**
- Content-addressed storage (SHA-256 based)
- Automatic HTML/PDF detection via content-type
- Cross-run deduplication with `ContentHashStore`
- Thread-safe directory creation and writing
- Populates `artifact.content.blob_path` and `artifact.content.blob_sha256`

### EdgesWriter

Captures site navigation structure by recording crawl relationships.

```python
from crawlit.pipelines import EdgesWriter

edges_writer = EdgesWriter("output/site_edges.jsonl")
```

**Output Format:**
```json
{"from_url": "https://example.com/", "to_url": "https://example.com/about", "depth": 1, "method": "link"}
{"from_url": "https://example.com/about", "to_url": "https://example.com/contact", "depth": 2, "method": "link"}
```

**Use Cases:**
- Site structure analysis
- Graph visualization
- Coverage analysis  
- Link relationship tracking

### ArtifactStore

Complete, contract-defined storage implementation combining all output types.

```python
from crawlit.pipelines import ArtifactStore

# Full-featured artifact store
store = ArtifactStore(
    store_dir="./runs/2024-01-01",
    job=crawler.job,  # Pass after crawler creation
    write_blobs=True,
    write_edges=True,
    write_events=True
)
```

**Generated Layout:**
```
runs/2024-01-01/
├── run.json              # Job metadata + config snapshot
├── artifacts.jsonl       # All PageArtifacts 
├── edges.jsonl          # Navigation edges
├── events.jsonl         # Operational events
└── blobs/               # Content-addressed blobs
    ├── html/
    └── pdf/
```

**Features:**
- Fixed, documented layout contract for downstream tools
- Integrated `BlobStore` for content storage  
- Optional `CrawlEventLog` for operational monitoring
- Run manifest with config snapshot hash
- Thread-safe concurrent writes

## Pipeline Interface and Base Classes

### Synchronous Pipeline Interface

```python
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class CustomPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """
        Process the artifact and return it (possibly modified) or None to drop it.
        
        Args:
            artifact: The PageArtifact to process
            
        Returns:
            Modified artifact or None to drop from further processing
        """
        # Your processing logic here
        return artifact
```

### Asynchronous Pipeline Interface

```python
from crawlit.interfaces import AsyncPipeline

class AsyncCustomPipeline(AsyncPipeline):
    async def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """
        Process the artifact asynchronously.
        
        Supports async operations like API calls, database writes, etc.
        """
        # Your async processing logic
        await some_async_operation(artifact)
        return artifact
```

### Pipeline Contract

**Input**: Fully-populated `PageArtifact` with:
- HTTP response data (`artifact.http`)
- Raw content (`artifact.content.raw_html`) 
- Extracted data (`artifact.extracted`)
- Crawl metadata (`artifact.crawl`)

**Output Options**:
- **Return modified artifact**: Continue to next pipeline stage
- **Return `None`**: Drop artifact from further processing 
- **Raise exception**: Error logged, artifact restored to pre-stage state

**Thread Safety**: Built-in pipelines handle concurrent access with locks. Custom pipelines should implement their own synchronization if needed.

## Custom Pipeline Development

### Basic Pipeline Template

```python
import logging
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

logger = logging.getLogger(__name__)

class CustomPipeline(Pipeline):
    def __init__(self, **kwargs):
        # Initialize configuration
        self.some_setting = kwargs.get('some_setting', 'default')
        
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Process the artifact"""
        try:
            # Your processing logic
            self._do_processing(artifact)
            return artifact
            
        except Exception as exc:
            logger.warning(f"CustomPipeline failed for {artifact.url}: {exc}")
            return artifact  # or None to drop
    
    def _do_processing(self, artifact: PageArtifact):
        """Implement your custom logic here"""
        pass
```

### Content Filtering Pipeline

```python
from typing import Optional, Set
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class ContentFilterPipeline(Pipeline):
    """Filter artifacts based on content quality and domain rules"""
    
    def __init__(self, 
                 min_content_length: int = 100,
                 blocked_domains: Set[str] = None,
                 required_keywords: Set[str] = None):
        self.min_content_length = min_content_length
        self.blocked_domains = blocked_domains or set()
        self.required_keywords = required_keywords or set()
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Apply filtering rules"""
        
        # Domain filtering
        if any(domain in artifact.url for domain in self.blocked_domains):
            return None
            
        # Content length filtering  
        text_content = artifact.content.text or ""
        if len(text_content) < self.min_content_length:
            return None
            
        # Keyword filtering
        if self.required_keywords:
            text_lower = text_content.lower()
            if not any(keyword.lower() in text_lower for keyword in self.required_keywords):
                return None
        
        # Add quality metadata
        quality_score = self._calculate_quality_score(artifact)
        if 'filter_metadata' not in artifact.extracted:
            artifact.extracted['filter_metadata'] = {}
        artifact.extracted['filter_metadata']['quality_score'] = quality_score
        
        return artifact
    
    def _calculate_quality_score(self, artifact: PageArtifact) -> float:
        """Calculate content quality score (0.0 to 1.0)"""
        score = 0.0
        
        # Content length factor
        content_length = len(artifact.content.text or "")
        score += min(content_length / 1000, 1.0) * 0.4
        
        # Extraction success factor
        successful_extractions = sum(
            1 for value in artifact.extracted.values()
            if value and not (isinstance(value, dict) and value.get('error'))
        )
        score += min(successful_extractions / 5, 1.0) * 0.3
        
        # HTTP status factor
        if artifact.http.status_code == 200:
            score += 0.3
            
        return min(score, 1.0)
```

### Data Enrichment Pipeline

```python
import re
from typing import Optional, Dict, Any
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class DataEnrichmentPipeline(Pipeline):
    """Enrich artifacts with additional derived data"""
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Add enriched data to the artifact"""
        
        enrichments = self._generate_enrichments(artifact)
        
        # Add to extracted data
        if 'enrichments' not in artifact.extracted:
            artifact.extracted['enrichments'] = {}
        artifact.extracted['enrichments'].update(enrichments)
        
        return artifact
    
    def _generate_enrichments(self, artifact: PageArtifact) -> Dict[str, Any]:
        """Generate enrichment data"""
        text_content = artifact.content.text or ""
        
        return {
            'word_count': len(text_content.split()),
            'paragraph_count': len(text_content.split('\n\n')),
            'email_addresses': self._extract_emails(text_content),
            'phone_numbers': self._extract_phones(text_content),
            'readability_score': self._calculate_readability(text_content),
            'language_detected': self._detect_language(text_content)
        }
    
    def _extract_emails(self, text: str) -> list:
        """Extract email addresses"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    def _extract_phones(self, text: str) -> list:
        """Extract phone numbers"""
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?[2-9]\d{2}[-.\s]?\d{4}'
        return re.findall(phone_pattern, text)
    
    def _calculate_readability(self, text: str) -> float:
        """Simple readability score"""
        if not text:
            return 0.0
        
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        
        if sentences == 0:
            return 0.0
            
        # Simple approximation of reading ease
        avg_sentence_length = words / sentences
        return max(0.0, min(100.0, 100 - avg_sentence_length))
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection (placeholder)"""
        # In practice, use langdetect or similar library
        return "en"  # Default to English
```

### Async Database Pipeline

```python
import asyncio
import asyncpg
from typing import Optional
from crawlit.interfaces import AsyncPipeline
from crawlit.models import PageArtifact

class AsyncDatabasePipeline(AsyncPipeline):
    """Store artifacts in PostgreSQL database asynchronously"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._pool = None
    
    async def _get_pool(self):
        """Lazy connection pool initialization"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10
            )
        return self._pool
    
    async def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Store artifact in database"""
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO crawl_results 
                    (url, title, content_length, extracted_data, crawled_at, status_code)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (url) DO UPDATE SET
                        title = EXCLUDED.title,
                        content_length = EXCLUDED.content_length,
                        extracted_data = EXCLUDED.extracted_data,
                        crawled_at = EXCLUDED.crawled_at,
                        status_code = EXCLUDED.status_code
                ''', 
                    artifact.url,
                    artifact.content.title or "",
                    len(artifact.content.text or ""),
                    json.dumps(artifact.extracted),
                    artifact.fetched_at,
                    artifact.http.status_code
                )
                
            return artifact
            
        except Exception as exc:
            logger.warning(f"Database storage failed for {artifact.url}: {exc}")
            return artifact  # Don't drop on storage failure
```

## Pipeline Chaining and Order

### Basic Chaining

Pipelines execute in the order they are listed in the crawler configuration:

```python
from crawlit import Crawler
from crawlit.pipelines import JSONLWriter, BlobStore, EdgesWriter

crawler = Crawler(
    "https://example.com",
    pipelines=[
        BlobStore("./blobs"),           # 1. Store raw content first
        ContentFilterPipeline(),       # 2. Filter/quality check
        DataEnrichmentPipeline(),      # 3. Add derived data
        JSONLWriter("./results.jsonl"), # 4. Write final artifacts
        EdgesWriter("./edges.jsonl")   # 5. Record navigation
    ]
)
```

### Order Considerations

**Early Stage Pipelines:**
- Content storage (BlobStore) - preserve raw data before any filtering
- Validation and error handling pipelines
- Content normalization

**Middle Stage Pipelines:**  
- Filtering and quality control pipelines
- Data enrichment and derivation
- Content transformation

**Late Stage Pipelines:**
- Output formatting (JSONLWriter)
- Final storage and archival
- Notification and reporting

### Conditional Processing

```python
class ConditionalPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Only process certain content types
        content_type = artifact.http.content_type or ""
        
        if "text/html" not in content_type:
            return artifact  # Pass through non-HTML
            
        # Process HTML content
        self._process_html_content(artifact)
        return artifact
```

## Data Transformation Patterns

### In-Place Modification

Modify the existing artifact structure:

```python
def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
    # Add new extracted data
    artifact.extracted['timestamps'] = {
        'processed_at': datetime.now().isoformat(),
        'fetch_time': artifact.fetched_at.isoformat()
    }
    
    # Modify existing content
    if artifact.content.text:
        artifact.content.text = self._clean_text(artifact.content.text)
    
    return artifact
```

### Derived Data Addition

Add computed fields without modifying original data:

```python
def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
    # Calculate derived metrics
    text = artifact.content.text or ""
    
    metrics = {
        'char_count': len(text),
        'word_count': len(text.split()),
        'unique_words': len(set(text.lower().split())),
        'avg_word_length': sum(len(word) for word in text.split()) / len(text.split()) if text.split() else 0
    }
    
    # Add as separate extracted data
    artifact.extracted['text_metrics'] = metrics
    return artifact
```

### Content Normalization

Standardize content format across different sources:

```python
class ContentNormalizationPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Normalize encoding
        if artifact.content.raw_html:
            artifact.content.raw_html = self._normalize_encoding(artifact.content.raw_html)
        
        # Standardize extracted data structure
        if 'links' in artifact.extracted:
            artifact.extracted['links'] = self._normalize_links(artifact.extracted['links'])
            
        # Clean and standardize text content
        if artifact.content.text:
            artifact.content.text = self._normalize_text(artifact.content.text)
            
        return artifact
    
    def _normalize_encoding(self, html: str) -> str:
        """Ensure consistent UTF-8 encoding"""
        # Implementation details...
        return html
    
    def _normalize_links(self, links: list) -> list:
        """Standardize link data structure"""
        normalized = []
        for link in links:
            if isinstance(link, str):
                normalized.append({'url': link, 'text': '', 'rel': ''})
            elif isinstance(link, dict):
                normalized.append({
                    'url': link.get('href', link.get('url', '')),
                    'text': link.get('text', ''),
                    'rel': link.get('rel', '')
                })
        return normalized
```

## Output Formatting Pipelines

### CSV Export Pipeline

```python
import csv
import threading
from pathlib import Path
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class CSVExportPipeline(Pipeline):
    """Export selected artifact data to CSV format"""
    
    def __init__(self, output_path: str, fields: list = None):
        self.output_path = Path(output_path)
        self.fields = fields or ['url', 'title', 'status_code', 'content_length']
        self.lock = threading.Lock()
        self._header_written = False
        
        # Create output directory
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Export artifact data to CSV"""
        try:
            row_data = self._extract_row_data(artifact)
            
            with self.lock:
                mode = 'a' if self._header_written else 'w'
                with open(self.output_path, mode, newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fields)
                    
                    if not self._header_written:
                        writer.writeheader()
                        self._header_written = True
                    
                    writer.writerow(row_data)
                    
        except Exception as exc:
            logger.warning(f"CSV export failed for {artifact.url}: {exc}")
            
        return artifact
    
    def _extract_row_data(self, artifact: PageArtifact) -> dict:
        """Extract data for CSV row"""
        row = {}
        
        for field in self.fields:
            if field == 'url':
                row[field] = artifact.url
            elif field == 'title':
                row[field] = artifact.content.title or ""
            elif field == 'status_code':
                row[field] = artifact.http.status_code
            elif field == 'content_length':
                row[field] = len(artifact.content.text or "")
            elif field == 'fetch_time':
                row[field] = artifact.fetched_at.isoformat()
            elif field in artifact.extracted:
                # Handle extracted data
                value = artifact.extracted[field]
                if isinstance(value, (dict, list)):
                    row[field] = str(value)  # Serialize complex types
                else:
                    row[field] = value
            else:
                row[field] = ""  # Default empty value
                
        return row
```

### XML Export Pipeline

```python
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class XMLExportPipeline(Pipeline):
    """Export artifacts to XML format"""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.lock = threading.Lock()
        self.artifacts_collected = []
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Collect artifacts for XML export"""
        with self.lock:
            self.artifacts_collected.append(artifact)
        return artifact
    
    def finalize(self):
        """Write collected artifacts to XML file"""
        root = ET.Element("crawl_results")
        
        for artifact in self.artifacts_collected:
            artifact_elem = ET.SubElement(root, "artifact")
            
            # Basic info
            ET.SubElement(artifact_elem, "url").text = artifact.url
            ET.SubElement(artifact_elem, "title").text = artifact.content.title or ""
            ET.SubElement(artifact_elem, "status_code").text = str(artifact.http.status_code)
            ET.SubElement(artifact_elem, "fetched_at").text = artifact.fetched_at.isoformat()
            
            # Content info
            content_elem = ET.SubElement(artifact_elem, "content")
            content_elem.set("length", str(len(artifact.content.text or "")))
            
            # Extracted data
            extracted_elem = ET.SubElement(artifact_elem, "extracted_data")
            for key, value in artifact.extracted.items():
                item_elem = ET.SubElement(extracted_elem, "item")
                item_elem.set("name", key)
                item_elem.text = str(value)
        
        # Pretty print and save
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(pretty)
```

## Storage Pipelines

### File System Storage

The built-in `BlobStore` provides content-addressed file storage. For custom file organization:

```python
import shutil
from pathlib import Path
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class OrganizedFilePipeline(Pipeline):
    """Store artifacts in organized directory structure"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Store artifact with organized structure"""
        
        # Create directory structure based on URL
        url_parts = artifact.url.replace("://", "/").split("/")
        domain = url_parts[1] if len(url_parts) > 1 else "unknown"
        
        domain_dir = self.base_dir / domain
        domain_dir.mkdir(exist_ok=True)
        
        # Save HTML content
        if artifact.content.raw_html:
            html_file = domain_dir / f"page_{hash(artifact.url) & 0x7FFFFFFF}.html"
            html_file.write_text(artifact.content.raw_html, encoding='utf-8')
            
        # Save extracted data as JSON
        import json
        json_file = domain_dir / f"data_{hash(artifact.url) & 0x7FFFFFFF}.json"
        json_file.write_text(json.dumps(artifact.to_dict(), indent=2), encoding='utf-8')
        
        return artifact
```

### Database Storage Backends

#### SQLite Storage

```python
import sqlite3
import json
import threading
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class SQLiteStoragePipeline(Pipeline):
    """Store artifacts in SQLite database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    domain TEXT,
                    title TEXT,
                    status_code INTEGER,
                    content_type TEXT,
                    content_length INTEGER,
                    text_content TEXT,
                    extracted_data TEXT,
                    fetched_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_url ON artifacts(url)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_domain ON artifacts(domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_fetched_at ON artifacts(fetched_at)')
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Store artifact in SQLite database"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO artifacts 
                        (url, domain, title, status_code, content_type, content_length, 
                         text_content, extracted_data, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        artifact.url,
                        self._extract_domain(artifact.url),
                        artifact.content.title or "",
                        artifact.http.status_code,
                        artifact.http.content_type or "",
                        len(artifact.content.text or ""),
                        artifact.content.text or "",
                        json.dumps(artifact.extracted),
                        artifact.fetched_at
                    ))
                    
        except Exception as exc:
            logger.warning(f"SQLite storage failed for {artifact.url}: {exc}")
            
        return artifact
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc
```

#### MongoDB Storage

```python
from pymongo import MongoClient
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class MongoDBStoragePipeline(Pipeline):
    """Store artifacts in MongoDB collection"""
    
    def __init__(self, connection_string: str, database: str, collection: str):
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
        self.collection = self.db[collection]
        
        # Create indexes for common queries
        self.collection.create_index("url", unique=True)
        self.collection.create_index("fetched_at")
        self.collection.create_index("http.status_code")
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Store artifact in MongoDB"""
        try:
            # Convert artifact to dict for MongoDB storage
            doc = artifact.to_dict()
            
            # Upsert document (insert or update)
            self.collection.replace_one(
                {"url": artifact.url},
                doc,
                upsert=True
            )
            
        except Exception as exc:
            logger.warning(f"MongoDB storage failed for {artifact.url}: {exc}")
            
        return artifact
```

### Cloud Storage Integration

```python
import boto3
import json
from typing import Optional
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class S3StoragePipeline(Pipeline):
    """Store artifacts in Amazon S3"""
    
    def __init__(self, bucket_name: str, prefix: str = "", aws_profile: str = None):
        self.bucket_name = bucket_name
        self.prefix = prefix
        
        session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
        self.s3_client = session.client('s3')
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Store artifact in S3"""
        try:
            # Generate S3 key based on URL and timestamp
            key_parts = [self.prefix] if self.prefix else []
            key_parts.extend([
                artifact.fetched_at.strftime("%Y/%m/%d"),
                f"{hash(artifact.url) & 0x7FFFFFFF}.json"
            ])
            s3_key = "/".join(key_parts)
            
            # Upload artifact JSON
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(artifact.to_dict(), default=str),
                ContentType='application/json',
                Metadata={
                    'url': artifact.url,
                    'status_code': str(artifact.http.status_code),
                    'content_type': artifact.http.content_type or ""
                }
            )
            
            # Store S3 location in artifact for reference
            if 'storage' not in artifact.extracted:
                artifact.extracted['storage'] = {}
            artifact.extracted['storage']['s3_location'] = f"s3://{self.bucket_name}/{s3_key}"
            
        except Exception as exc:
            logger.warning(f"S3 storage failed for {artifact.url}: {exc}")
            
        return artifact
```

## Integration with Crawlers

### Synchronous Crawler Integration

```python
from crawlit import Crawler
from crawlit.pipelines import JSONLWriter, BlobStore, EdgesWriter

# Configure pipelines
pipelines = [
    BlobStore("./blobs"),
    ContentFilterPipeline(min_content_length=200),
    DataEnrichmentPipeline(),
    JSONLWriter("./results.jsonl"),
    EdgesWriter("./edges.jsonl")
]

# Create crawler with pipelines
crawler = Crawler(
    "https://example.com",
    max_depth=3,
    pipelines=pipelines
)

# Start crawling
crawler.crawl()
```

### Asynchronous Crawler Integration

```python
import asyncio
from crawlit import AsyncCrawler

# Mix of sync and async pipelines
pipelines = [
    BlobStore("./blobs"),                    # Sync pipeline
    AsyncDatabasePipeline(connection_string), # Async pipeline
    ContentFilterPipeline(),                 # Sync pipeline  
    JSONLWriter("./results.jsonl")           # Sync pipeline
]

async def main():
    crawler = AsyncCrawler(
        "https://example.com",
        max_depth=3,
        max_concurrent_requests=10,
        pipelines=pipelines
    )
    
    await crawler.crawl()

asyncio.run(main())
```

### Pipeline Configuration Patterns

#### Environment-Based Configuration

```python
import os
from crawlit.pipelines import ArtifactStore, JSONLWriter

def create_pipelines():
    """Create pipelines based on environment"""
    pipelines = []
    
    # Always include content storage
    pipelines.append(BlobStore("./blobs"))
    
    # Add format-specific outputs based on environment
    if os.getenv("OUTPUT_FORMAT") == "jsonl":
        pipelines.append(JSONLWriter("./output/results.jsonl"))
    elif os.getenv("OUTPUT_FORMAT") == "artifact_store":
        pipelines.append(ArtifactStore("./output/store"))
    
    # Add database storage in production
    if os.getenv("ENVIRONMENT") == "production":
        db_pipeline = SQLiteStoragePipeline("./crawl_data.db")
        pipelines.append(db_pipeline)
    
    return pipelines
```

#### Configuration from File

```python
import yaml
from typing import List
from crawlit.interfaces import Pipeline

def load_pipeline_config(config_path: str) -> List[Pipeline]:
    """Load pipeline configuration from YAML file"""
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    pipelines = []
    
    for pipeline_config in config['pipelines']:
        pipeline_type = pipeline_config['type']
        pipeline_args = pipeline_config.get('args', {})
        
        if pipeline_type == 'jsonl_writer':
            pipelines.append(JSONLWriter(**pipeline_args))
        elif pipeline_type == 'blob_store':
            pipelines.append(BlobStore(**pipeline_args))
        elif pipeline_type == 'content_filter':
            pipelines.append(ContentFilterPipeline(**pipeline_args))
        # Add more pipeline types as needed
    
    return pipelines

# Example YAML config:
# pipelines:
#   - type: blob_store
#     args:
#       blobs_dir: "./blobs"
#   - type: content_filter  
#     args:
#       min_content_length: 500
#   - type: jsonl_writer
#     args:
#       path: "./output/results.jsonl"
```

### Pipeline Event Handling

```python
from crawlit.utils.event_log import CrawlEventLog

class MonitoringPipeline(Pipeline):
    """Pipeline that logs operational events"""
    
    def __init__(self, event_log: CrawlEventLog):
        self.event_log = event_log
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Process with event logging"""
        
        # Log successful processing
        self.event_log.custom_event(
            "PIPELINE_SUCCESS", 
            {"url": artifact.url, "pipeline": "monitoring"}
        )
        
        # Check for quality thresholds
        content_length = len(artifact.content.text or "")
        if content_length < 100:
            self.event_log.custom_event(
                "QUALITY_WARNING",
                {"url": artifact.url, "content_length": content_length}
            )
        
        return artifact
```

## Performance Considerations

### Threading and Concurrency

**Built-in Pipeline Thread Safety:**
- `JSONLWriter`, `BlobStore`, `EdgesWriter`, `ArtifactStore` use internal locks
- Safe for use with multi-threaded synchronous crawler
- Custom pipelines should implement their own synchronization

```python
import threading

class ThreadSafePipeline(Pipeline):
    def __init__(self):
        self.lock = threading.Lock()
        self.shared_resource = {}
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        with self.lock:
            # Thread-safe operations on shared resources
            self.shared_resource[artifact.url] = artifact.fetched_at
        return artifact
```

### Memory Management

**Large Content Handling:**
```python
class MemoryEfficientPipeline(Pipeline):
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Process content in chunks for large texts
        text = artifact.content.text or ""
        
        if len(text) > 1_000_000:  # 1MB threshold
            # Process in chunks to avoid memory spikes
            results = []
            chunk_size = 100_000
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                results.append(self._process_chunk(chunk))
            
            artifact.extracted['chunked_results'] = results
        else:
            artifact.extracted['results'] = self._process_text(text)
        
        return artifact
```

**Resource Cleanup:**
```python
class ResourceManagedPipeline(Pipeline):
    def __init__(self):
        self.file_handle = None
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Process artifact
        return artifact
    
    def __enter__(self):
        self.file_handle = open("pipeline_output.txt", "w")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_handle:
            self.file_handle.close()

# Usage with context manager
with ResourceManagedPipeline() as pipeline:
    crawler = Crawler("https://example.com", pipelines=[pipeline])
    crawler.crawl()
```

### Optimization Strategies

**Batched Processing:**
```python
class BatchedPipeline(Pipeline):
    """Process artifacts in batches for efficiency"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.batch = []
        self.lock = threading.Lock()
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Collect artifacts for batch processing"""
        
        with self.lock:
            self.batch.append(artifact)
            
            if len(self.batch) >= self.batch_size:
                self._process_batch(self.batch.copy())
                self.batch.clear()
        
        return artifact
    
    def _process_batch(self, artifacts: List[PageArtifact]):
        """Process a batch of artifacts efficiently"""
        # Batch operations like bulk database inserts
        urls = [a.url for a in artifacts]
        texts = [a.content.text or "" for a in artifacts]
        
        # Efficient bulk processing
        results = self._bulk_analyze(urls, texts)
        
        # Update artifacts with results
        for artifact, result in zip(artifacts, results):
            artifact.extracted['batch_analysis'] = result
    
    def finalize(self):
        """Process remaining artifacts in final batch"""
        if self.batch:
            self._process_batch(self.batch)
            self.batch.clear()
```

**Caching and Deduplication:**
```python
import hashlib
from typing import Dict, Any

class CachedPipeline(Pipeline):
    """Cache expensive operations to avoid reprocessing"""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        # Create cache key from content hash
        content = artifact.content.text or ""
        cache_key = hashlib.md5(content.encode()).hexdigest()
        
        if cache_key in self.cache:
            # Use cached result
            artifact.extracted['expensive_analysis'] = self.cache[cache_key]
        else:
            # Perform expensive operation
            result = self._expensive_analysis(content)
            self.cache[cache_key] = result
            artifact.extracted['expensive_analysis'] = result
        
        return artifact
    
    def _expensive_analysis(self, content: str) -> Dict[str, Any]:
        """Simulate expensive processing operation"""
        import time
        time.sleep(0.1)  # Simulate processing time
        return {'analysis_complete': True, 'content_hash': hashlib.md5(content.encode()).hexdigest()}
```

### Async Pipeline Performance

**Connection Pooling:**
```python
import aiohttp
from crawlit.interfaces import AsyncPipeline

class APIEnrichmentPipeline(AsyncPipeline):
    """Async pipeline with connection pooling"""
    
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
        self.session = None
    
    async def __aenter__(self):
        # Create async HTTP session with connection pooling
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Enrich artifact with external API data"""
        try:
            async with self.session.post(
                self.api_endpoint,
                json={"text": artifact.content.text or ""}
            ) as response:
                enrichment_data = await response.json()
                artifact.extracted['api_enrichment'] = enrichment_data
                
        except Exception as exc:
            logger.warning(f"API enrichment failed for {artifact.url}: {exc}")
        
        return artifact

# Usage with async context manager
async def main():
    async with APIEnrichmentPipeline("https://api.example.com/analyze") as pipeline:
        crawler = AsyncCrawler("https://example.com", pipelines=[pipeline])
        await crawler.crawl()
```

## Examples of Complex Pipeline Workflows

### E-commerce Site Analysis

```python
"""Complete e-commerce crawling pipeline workflow"""

from crawlit import Crawler
from crawlit.pipelines import BlobStore, JSONLWriter, EdgesWriter

# Custom pipelines for e-commerce analysis
class EcommerceProductExtractor(Pipeline):
    """Extract product information from e-commerce pages"""
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        html = artifact.content.raw_html or ""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract product information
        product_data = {
            'name': self._extract_product_name(soup),
            'price': self._extract_price(soup),
            'description': self._extract_description(soup),
            'images': self._extract_images(soup),
            'availability': self._extract_availability(soup),
            'reviews': self._extract_reviews(soup)
        }
        
        # Only keep artifacts that contain product data
        if product_data['name'] or product_data['price']:
            artifact.extracted['product'] = product_data
            return artifact
        else:
            return None  # Drop non-product pages

class ProductCategoryClassifier(Pipeline):
    """Classify products into categories"""
    
    def __init__(self):
        self.category_keywords = {
            'electronics': ['phone', 'laptop', 'tablet', 'computer'],
            'clothing': ['shirt', 'pants', 'dress', 'shoes'],
            'books': ['book', 'novel', 'textbook', 'guide'],
            'home': ['furniture', 'kitchen', 'bedding', 'decor']
        }
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        if 'product' not in artifact.extracted:
            return artifact
            
        product = artifact.extracted['product']
        text = f"{product.get('name', '')} {product.get('description', '')}".lower()
        
        # Classify based on keywords
        categories = []
        for category, keywords in self.category_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)
        
        product['categories'] = categories
        return artifact

class PriceHistoryPipeline(Pipeline):
    """Track price changes over time"""
    
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                url TEXT,
                price REAL,
                timestamp TIMESTAMP,
                PRIMARY KEY (url, timestamp)
            )
        ''')
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        product = artifact.extracted.get('product', {})
        price_str = product.get('price', '')
        
        # Extract numeric price
        price_match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
        if price_match:
            price = float(price_match.group())
            
            with self.lock:
                self.db.execute(
                    'INSERT OR IGNORE INTO price_history VALUES (?, ?, ?)',
                    (artifact.url, price, artifact.fetched_at)
                )
                self.db.commit()
                
                # Add price history to artifact
                cursor = self.db.execute(
                    'SELECT price, timestamp FROM price_history WHERE url = ? ORDER BY timestamp',
                    (artifact.url,)
                )
                history = [{'price': row[0], 'timestamp': row[1]} for row in cursor.fetchall()]
                product['price_history'] = history
        
        return artifact

# Complete e-commerce pipeline
def create_ecommerce_pipeline():
    return [
        BlobStore("./ecommerce_blobs"),
        EcommerceProductExtractor(),
        ProductCategoryClassifier(), 
        PriceHistoryPipeline("./price_history.db"),
        JSONLWriter("./ecommerce_products.jsonl"),
        EdgesWriter("./ecommerce_navigation.jsonl")
    ]

# Usage
crawler = Crawler(
    "https://shop.example.com",
    max_depth=4,
    pipelines=create_ecommerce_pipeline()
)
```

### News Website Monitoring

```python
"""News monitoring with content analysis and alerting"""

import smtplib
from email.mime.text import MimeText
from datetime import datetime, timedelta

class NewsContentAnalyzer(Pipeline):
    """Analyze news articles for key metrics"""
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        html = artifact.content.raw_html or ""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract article metadata
        article_data = {
            'headline': self._extract_headline(soup),
            'author': self._extract_author(soup),
            'publish_date': self._extract_publish_date(soup),
            'word_count': len((artifact.content.text or "").split()),
            'categories': self._extract_categories(soup),
            'sentiment': self._analyze_sentiment(artifact.content.text or "")
        }
        
        # Only process actual news articles
        if article_data['headline'] and article_data['word_count'] > 100:
            artifact.extracted['article'] = article_data
            return artifact
        else:
            return None

class TrendingTopicTracker(Pipeline):
    """Track trending topics across articles"""
    
    def __init__(self):
        self.topic_counts = {}
        self.lock = threading.Lock()
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        article = artifact.extracted.get('article', {})
        text = f"{article.get('headline', '')} {artifact.content.text or ''}"
        
        # Extract topics/entities (simplified example)
        topics = self._extract_topics(text)
        
        with self.lock:
            for topic in topics:
                self.topic_counts[topic] = self.topic_counts.get(topic, 0) + 1
        
        article['topics'] = topics
        article['trending_score'] = sum(self.topic_counts.get(topic, 0) for topic in topics)
        
        return artifact

class BreakingNewsDetector(Pipeline):
    """Detect breaking news and send alerts"""
    
    def __init__(self, alert_threshold: int = 10):
        self.alert_threshold = alert_threshold
        self.recent_articles = []
        self.lock = threading.Lock()
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        article = artifact.extracted.get('article', {})
        
        # Check for breaking news indicators
        headline = article.get('headline', '').lower()
        breaking_indicators = ['breaking', 'urgent', 'alert', 'developing']
        
        is_breaking = any(indicator in headline for indicator in breaking_indicators)
        
        with self.lock:
            # Track recent articles
            now = datetime.now()
            self.recent_articles = [
                (timestamp, title) for timestamp, title in self.recent_articles
                if now - timestamp < timedelta(hours=1)
            ]
            
            if is_breaking or article.get('trending_score', 0) > self.alert_threshold:
                self._send_alert(artifact, article)
                article['alert_sent'] = True
        
        return artifact
    
    def _send_alert(self, artifact: PageArtifact, article: dict):
        """Send breaking news alert"""
        subject = f"Breaking News Alert: {article.get('headline', 'Untitled')}"
        body = f"""
        Breaking news detected:
        
        URL: {artifact.url}
        Headline: {article.get('headline', 'N/A')}
        Author: {article.get('author', 'N/A')}
        Trending Score: {article.get('trending_score', 0)}
        
        Full text: {artifact.content.text[:500]}...
        """
        
        # In practice, integrate with email, Slack, etc.
        print(f"ALERT: {subject}")

# News monitoring pipeline
def create_news_pipeline():
    return [
        BlobStore("./news_content"),
        NewsContentAnalyzer(),
        TrendingTopicTracker(),
        BreakingNewsDetector(alert_threshold=15),
        JSONLWriter("./news_analysis.jsonl"),
        EdgesWriter("./news_navigation.jsonl")
    ]
```

### Research Data Collection

```python
"""Academic paper and research data collection pipeline"""

class AcademicPaperExtractor(Pipeline):
    """Extract academic paper metadata and content"""
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        html = artifact.content.raw_html or ""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract academic metadata
        paper_data = {
            'title': self._extract_title(soup),
            'authors': self._extract_authors(soup),
            'abstract': self._extract_abstract(soup),
            'doi': self._extract_doi(soup),
            'keywords': self._extract_keywords(soup),
            'publication_date': self._extract_pub_date(soup),
            'journal': self._extract_journal(soup),
            'citations': self._extract_citations(soup),
            'references': self._extract_references(soup)
        }
        
        # Validate academic content
        if paper_data['title'] and (paper_data['abstract'] or paper_data['doi']):
            artifact.extracted['paper'] = paper_data
            return artifact
        else:
            return None

class CitationNetworkBuilder(Pipeline):
    """Build citation networks between papers"""
    
    def __init__(self, graph_db_path: str):
        import networkx as nx
        self.graph = nx.DiGraph()
        self.db_path = graph_db_path
        self.lock = threading.Lock()
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        paper = artifact.extracted.get('paper', {})
        paper_id = paper.get('doi') or artifact.url
        
        with self.lock:
            # Add paper as node
            self.graph.add_node(paper_id, **paper)
            
            # Add citation edges
            for citation in paper.get('citations', []):
                if citation.get('doi'):
                    self.graph.add_edge(paper_id, citation['doi'])
            
            # Calculate network metrics for this paper
            paper['citation_count'] = len(paper.get('citations', []))
            paper['reference_count'] = len(paper.get('references', []))
            
            if paper_id in self.graph:
                paper['in_degree'] = self.graph.in_degree(paper_id)
                paper['out_degree'] = self.graph.out_degree(paper_id)
        
        return artifact
    
    def finalize(self):
        """Save citation network"""
        import pickle
        with open(self.db_path, 'wb') as f:
            pickle.dump(self.graph, f)

class ResearchTopicClassifier(Pipeline):
    """Classify papers by research topics using ML"""
    
    def __init__(self):
        # In practice, load pre-trained topic model
        self.topic_model = self._load_topic_model()
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        paper = artifact.extracted.get('paper', {})
        
        # Combine text for topic classification
        text_for_classification = " ".join([
            paper.get('title', ''),
            paper.get('abstract', ''),
            " ".join(paper.get('keywords', []))
        ])
        
        if text_for_classification.strip():
            topics = self._classify_topics(text_for_classification)
            paper['research_topics'] = topics
            paper['primary_topic'] = topics[0] if topics else 'unknown'
        
        return artifact

# Research collection pipeline
def create_research_pipeline():
    return [
        BlobStore("./research_content"),
        AcademicPaperExtractor(),
        CitationNetworkBuilder("./citation_network.pkl"),
        ResearchTopicClassifier(),
        JSONLWriter("./research_papers.jsonl"),
        EdgesWriter("./research_navigation.jsonl")
    ]
```

### Multi-Stage Data Processing Workflow

```python
"""Complex multi-stage processing with conditional paths"""

class ContentTypeRouter(Pipeline):
    """Route artifacts to different processing paths based on content type"""
    
    def __init__(self):
        self.routes = {
            'html': HTMLProcessingPipeline(),
            'pdf': PDFProcessingPipeline(),
            'api': APIResponsePipeline()
        }
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        content_type = artifact.http.content_type or ""
        
        if "text/html" in content_type:
            return self.routes['html'].process(artifact)
        elif "application/pdf" in content_type:
            return self.routes['pdf'].process(artifact)
        elif "application/json" in content_type:
            return self.routes['api'].process(artifact)
        else:
            # Default processing
            artifact.extracted['content_type'] = 'unknown'
            return artifact

class QualityGatesPipeline(Pipeline):
    """Multi-stage quality validation with progressive filtering"""
    
    def __init__(self):
        self.quality_gates = [
            self._gate_1_basic_validation,
            self._gate_2_content_quality,
            self._gate_3_extraction_success,
            self._gate_4_business_rules
        ]
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        quality_report = {'gates_passed': 0, 'failed_gate': None, 'issues': []}
        
        for i, gate in enumerate(self.quality_gates):
            passed, issues = gate(artifact)
            
            if passed:
                quality_report['gates_passed'] = i + 1
            else:
                quality_report['failed_gate'] = i + 1
                quality_report['issues'].extend(issues)
                break
        
        artifact.extracted['quality_report'] = quality_report
        
        # Only pass artifacts that meet minimum quality thresholds
        if quality_report['gates_passed'] >= 2:
            return artifact
        else:
            return None
    
    def _gate_1_basic_validation(self, artifact: PageArtifact) -> tuple:
        """Basic HTTP and content validation"""
        issues = []
        
        if artifact.http.status_code != 200:
            issues.append(f"Non-200 status code: {artifact.http.status_code}")
        
        if not artifact.content.text or len(artifact.content.text) < 50:
            issues.append("Insufficient text content")
        
        return len(issues) == 0, issues

# Complete multi-stage workflow
def create_comprehensive_pipeline():
    return [
        # Stage 1: Raw data preservation
        BlobStore("./raw_content"),
        
        # Stage 2: Content routing and specialized processing
        ContentTypeRouter(),
        
        # Stage 3: Quality gates and filtering
        QualityGatesPipeline(),
        
        # Stage 4: Data enrichment
        DataEnrichmentPipeline(),
        
        # Stage 5: Multiple output formats
        JSONLWriter("./processed_data.jsonl"),
        CSVExportPipeline("./processed_data.csv"),
        
        # Stage 6: Storage and archival
        SQLiteStoragePipeline("./comprehensive_data.db"),
        
        # Stage 7: Navigation and relationships
        EdgesWriter("./site_structure.jsonl")
    ]
```

This comprehensive pipeline documentation covers all aspects of the crawlit pipeline system, from basic concepts to advanced implementation patterns. The examples demonstrate real-world usage scenarios and provide a foundation for developing custom pipeline solutions for specific crawling requirements.