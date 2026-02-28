# Database Integration

Crawlit provides comprehensive database integration capabilities for persisting crawled data. This guide covers all supported database backends, configuration options, performance optimization, and integration patterns.

## Table of Contents

1. [Overview](#overview)
2. [Supported Database Backends](#supported-database-backends)
3. [Database Setup and Configuration](#database-setup-and-configuration)
4. [Schema Definitions and Data Models](#schema-definitions-and-data-models)
5. [SQLite Integration](#sqlite-integration-built-in)
6. [PostgreSQL Integration](#postgresql-integration)
7. [MongoDB Integration](#mongodb-integration)
8. [Performance Optimization](#performance-optimization)
9. [Connection Pooling](#connection-pooling)
10. [Query Patterns and Data Retrieval](#query-patterns-and-data-retrieval)
11. [Pipeline Integration](#pipeline-integration)
12. [Migration and Backup Strategies](#migration-and-backup-strategies)
13. [Examples](#examples)
14. [Troubleshooting](#troubleshooting)

## Overview

Crawlit's database integration is built around a flexible backend architecture that supports multiple database types through a unified interface. The system provides:

- **Multiple Backend Support**: SQLite, PostgreSQL, and MongoDB
- **Unified API**: Consistent interface across all database types
- **Connection Pooling**: Efficient connection management for distributed crawling
- **Structured Data Models**: Well-defined schemas for crawl results
- **Performance Optimization**: Indexes, bulk operations, and query optimization
- **Pipeline Integration**: Seamless integration with crawling pipelines

## Supported Database Backends

### 1. SQLite (Built-in)
- **Dependencies**: None (built into Python)
- **Use Cases**: Local development, testing, small-scale crawling
- **Advantages**: Zero setup, portable, lightweight
- **Limitations**: Single-writer, not suitable for distributed crawling

### 2. PostgreSQL
- **Dependencies**: `psycopg2-binary`
- **Use Cases**: Production environments, structured data, complex queries
- **Advantages**: ACID compliance, advanced querying, JSON support
- **Installation**: `pip install crawlit[postgresql]`

### 3. MongoDB
- **Dependencies**: `pymongo`
- **Use Cases**: Unstructured data, flexible schemas, document storage
- **Advantages**: Schema flexibility, native JSON support, horizontal scaling
- **Installation**: `pip install crawlit[mongodb]`

## Database Setup and Configuration

### Installation Options

```bash
# SQLite (included by default)
pip install crawlit

# PostgreSQL support
pip install crawlit[postgresql]

# MongoDB support  
pip install crawlit[mongodb]

# All database backends
pip install crawlit[databases]
```

### Basic Configuration

Database backends are configured programmatically or through factory functions:

```python
from crawlit.utils.database import get_database_backend

# SQLite (default)
db = get_database_backend('sqlite', database_path='crawl_results.db')

# PostgreSQL
db = get_database_backend('postgresql', 
                         host='localhost', 
                         database='crawlit',
                         user='crawlit_user',
                         password='secure_password')

# MongoDB
db = get_database_backend('mongodb',
                         host='localhost',
                         database='crawlit',
                         collection='results')
```

### Backend Availability Checking

Before using a database backend, crawlit can verify availability and setup:

```python
from crawlit.utils.database import SQLiteBackend, PostgreSQLBackend, MongoDBBackend

# Check if PostgreSQL is available and configured
is_available, message = PostgreSQLBackend.check_availability(
    host='localhost',
    database='crawlit',
    user='crawlit_user',
    password='password'
)

if is_available:
    print("PostgreSQL is ready:", message)
else:
    print("Setup required:", message)
```

## Schema Definitions and Data Models

### Core Data Structure

Crawlit uses a structured data model based on the `PageArtifact` class:

```python
@dataclasses.dataclass
class PageArtifact:
    schema_version: str = "1"
    url: str = ""
    fetched_at: Optional[datetime] = None
    http: HTTPInfo = field(default_factory=HTTPInfo)
    content: ContentInfo = field(default_factory=ContentInfo)
    source: ArtifactSource = field(default_factory=ArtifactSource)
    links: List[str] = field(default_factory=list)
    extracted: Dict[str, Any] = field(default_factory=dict)
    downloads: List[DownloadRecord] = field(default_factory=list)
    errors: List[CrawlError] = field(default_factory=list)
    crawl: CrawlMeta = field(default_factory=CrawlMeta)
```

### Database Schema

All database backends use a consistent logical schema with two main tables:

#### `crawls` Table
```sql
-- Metadata about each crawl session
CREATE TABLE crawls (
    id INTEGER/SERIAL PRIMARY KEY,
    start_url TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    user_agent TEXT,
    max_depth INTEGER,
    total_urls INTEGER DEFAULT 0,
    successful_urls INTEGER DEFAULT 0,
    failed_urls INTEGER DEFAULT 0,
    metadata JSON/JSONB/TEXT
);
```

#### `results` Table  
```sql
-- Individual page results
CREATE TABLE results (
    id INTEGER/SERIAL PRIMARY KEY,
    crawl_id INTEGER REFERENCES crawls(id),
    url TEXT NOT NULL,
    status_code INTEGER,
    success BOOLEAN,
    depth INTEGER,
    title TEXT,
    content_type TEXT,
    html_content TEXT,
    links JSON/JSONB/TEXT,
    images JSON/JSONB/TEXT,
    keywords JSON/JSONB/TEXT,
    metadata JSON/JSONB/TEXT,
    timestamp TIMESTAMP NOT NULL
);
```

#### Indexes
Optimized indexes are created automatically:
- `idx_results_url` - Fast URL lookups
- `idx_results_crawl_id` - Efficient crawl filtering
- `idx_results_status` - Status code queries
- `idx_results_metadata` - JSON/document queries (PostgreSQL/MongoDB)

## SQLite Integration (Built-in)

SQLite is the default backend requiring no additional setup.

### Basic Usage

```python
from crawlit.utils.database import SQLiteBackend

# Initialize with custom database path
db = SQLiteBackend(database_path='my_crawls.db')

# Save crawl results
results = {
    'https://example.com': {
        'status': 200,
        'success': True,
        'depth': 0,
        'title': 'Example Domain',
        'content_type': 'text/html',
        'html_content': '<html>...</html>',
        'links': ['https://example.com/page1'],
        'images': [],
        'keywords': ['example', 'domain']
    }
}

metadata = {
    'start_url': 'https://example.com',
    'user_agent': 'crawlit/1.0',
    'max_depth': 2
}

crawl_id = db.save_results(results, metadata)

# Retrieve results
all_results = db.get_results({'crawl_id': crawl_id})
successful_only = db.get_results({'crawl_id': crawl_id, 'success': True})
```

### SQLite-Specific Features

- **JSON Storage**: Complex data stored as JSON text
- **Row Factory**: Results returned as dictionary-like objects
- **Automatic Database Creation**: Database file created if it doesn't exist
- **Thread Safety**: Uses connection-per-thread pattern

## PostgreSQL Integration

PostgreSQL provides enterprise-grade features for production crawling.

### Prerequisites

```bash
# Install PostgreSQL server (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Install Python driver
pip install crawlit[postgresql]
```

### Database Setup

```sql
-- Create database and user
CREATE DATABASE crawlit;
CREATE USER crawlit_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE crawlit TO crawlit_user;

-- Connect to crawlit database
\c crawlit

-- Grant schema permissions
GRANT ALL PRIVILEGES ON SCHEMA public TO crawlit_user;
```

### Usage Example

```python
from crawlit.utils.database import PostgreSQLBackend

# Initialize PostgreSQL backend
db = PostgreSQLBackend(
    host='localhost',
    port=5432,
    database='crawlit', 
    user='crawlit_user',
    password='secure_password'
)

# Automatic table creation and indexing
db.connect()

# Save results (same as SQLite)
crawl_id = db.save_results(results, metadata)

# Advanced querying with PostgreSQL features
results = db.get_results({
    'crawl_id': crawl_id,
    'status_code': 200,
    'success': True
})
```

### PostgreSQL-Specific Features

- **JSONB Support**: Native JSON storage with indexing
- **Advanced Indexing**: GIN indexes for JSON queries
- **ACID Compliance**: Full transaction support
- **Concurrent Access**: Multi-user, multi-process safe
- **Auto Database Creation**: Automatically creates missing databases

### Connection Configuration

```python
# SSL connections
db = PostgreSQLBackend(
    host='db.example.com',
    port=5432,
    database='crawlit',
    user='crawlit_user', 
    password='secure_password',
    sslmode='require'
)

# Connection pooling parameters
db = PostgreSQLBackend(
    host='localhost',
    database='crawlit',
    user='crawlit_user',
    password='secure_password',
    connect_timeout=10,
    command_timeout=30
)
```

## MongoDB Integration

MongoDB provides flexible document storage for unstructured crawl data.

### Prerequisites

```bash
# Install MongoDB (Ubuntu/Debian)
sudo apt-get install mongodb

# Or using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Install Python driver
pip install crawlit[mongodb]
```

### Usage Example

```python
from crawlit.utils.database import MongoDBBackend

# Initialize MongoDB backend
db = MongoDBBackend(
    host='localhost',
    port=27017,
    database='crawlit',
    collection='results'
)

# With authentication
db = MongoDBBackend(
    host='localhost',
    port=27017,
    database='crawlit',
    collection='results',
    username='crawlit_user',
    password='secure_password'
)

# Save results
crawl_id = db.save_results(results, metadata)

# Query with MongoDB-style filters
results = db.get_results({
    'crawl_id': crawl_id,
    'status': 200,
    'depth': {'$lte': 2}
})
```

### MongoDB-Specific Features

- **Document Model**: Native JSON document storage
- **Schema Flexibility**: No fixed schema requirements
- **Nested Data**: Complex nested structures supported
- **MongoDB Queries**: Full MongoDB query language support
- **GridFS Support**: Large file storage capabilities
- **Auto-Indexing**: Automatic index creation for performance

### Atlas Cloud Setup

```python
# MongoDB Atlas connection
db = MongoDBBackend(
    host='cluster0.example.mongodb.net',
    username='crawlit_user',
    password='secure_password',
    database='crawlit',
    ssl=True,
    authSource='admin',
    retryWrites=True,
    w='majority'
)
```

## Performance Optimization

### Database Indexing

All backends create optimized indexes automatically:

```python
# SQLite indexes
"""
CREATE INDEX idx_results_url ON results(url);
CREATE INDEX idx_results_crawl_id ON results(crawl_id);  
CREATE INDEX idx_results_status ON results(status_code);
"""

# PostgreSQL indexes (with JSONB support)
"""
CREATE INDEX idx_results_metadata ON results USING GIN(metadata);
CREATE INDEX idx_results_links ON results USING GIN(links);
"""

# MongoDB indexes
"""
db.results.createIndex({"url": 1})
db.results.createIndex({"crawl_id": 1})
db.results.createIndex({"status_code": 1})
db.results.createIndex({"timestamp": 1})
"""
```

### Bulk Operations

For large datasets, use bulk operations:

```python
# Batch saving for better performance
large_results = {f"https://example.com/page{i}": {...} for i in range(1000)}

# All backends optimize bulk inserts automatically
crawl_id = db.save_results(large_results, metadata)
```

### Query Optimization

```python
# Efficient filtering
# Instead of retrieving all and filtering in Python:
all_results = db.get_results()
successful = [r for r in all_results if r['success']]

# Use database filtering:
successful = db.get_results({'success': True})

# Combine filters to reduce result sets
recent_successful = db.get_results({
    'success': True,
    'status_code': 200,
    'crawl_id': specific_crawl_id
})
```

## Connection Pooling

For distributed and high-throughput crawling, use connection pooling:

### Database Connection Pool

```python
from crawlit.distributed.pool import DatabaseConnectionPool

# Create connection pool
pool = DatabaseConnectionPool(
    db_backend='postgresql',
    db_config={
        'host': 'localhost',
        'database': 'crawlit',
        'user': 'crawlit_user',
        'password': 'secure_password'
    },
    min_connections=2,
    max_connections=10,
    max_idle_time=300.0,
    connection_timeout=30.0
)

# Use with context manager
with pool.get_connection() as db:
    crawl_id = db.save_results(results, metadata)

# Or manually manage
db = pool.acquire()
try:
    crawl_id = db.save_results(results, metadata)
finally:
    pool.release(db)

# Pool statistics
stats = pool.get_stats()
print(f"Active connections: {stats['active_connections']}")
print(f"Total created: {stats['created']}")
print(f"Reused: {stats['reused']}")
```

### Pool Configuration

```python
# High-traffic configuration
pool = DatabaseConnectionPool(
    db_backend='postgresql',
    db_config={'host': 'db.example.com', ...},
    min_connections=5,      # Always keep 5 connections ready
    max_connections=50,     # Allow up to 50 concurrent connections
    max_idle_time=120.0,    # Close idle connections after 2 minutes
    connection_timeout=10.0  # Fail fast if pool is exhausted
)

# Low-resource configuration  
pool = DatabaseConnectionPool(
    db_backend='sqlite',
    db_config={'database_path': 'crawls.db'},
    min_connections=1,
    max_connections=2,      # SQLite doesn't benefit from many connections
    max_idle_time=600.0
)
```

## Query Patterns and Data Retrieval

### Basic Queries

```python
# Get all results from a crawl
results = db.get_results({'crawl_id': crawl_id})

# Filter by success status
successful = db.get_results({'success': True})
failed = db.get_results({'success': False})

# Filter by HTTP status
ok_results = db.get_results({'status_code': 200})
not_found = db.get_results({'status_code': 404})

# Filter by URL pattern
domain_results = db.get_results({'url': 'example.com'})  # Contains match
```

### Advanced Queries

```python
# MongoDB-style queries (MongoDB backend only)
recent_results = db.get_results({
    'timestamp': {'$gte': datetime.now() - timedelta(days=7)},
    'depth': {'$lte': 3},
    'status': {'$in': [200, 301, 302]}
})

# PostgreSQL JSON queries (requires raw SQL)
# Access backend connection directly for complex queries
db.connect()
db.cursor.execute("""
    SELECT url, title, metadata->'keywords' as keywords
    FROM results 
    WHERE crawl_id = %s 
    AND metadata->>'content_type' LIKE 'text/html%'
    ORDER BY timestamp DESC
    LIMIT 100
""", (crawl_id,))
```

### Aggregation Queries

```python
# Get crawl statistics
crawls = db.get_crawls(limit=10)
for crawl in crawls:
    print(f"Crawl {crawl['id']}: {crawl['successful_urls']}/{crawl['total_urls']} successful")

# Custom aggregations (backend-specific)
# SQLite
db.cursor.execute("""
    SELECT status_code, COUNT(*) as count
    FROM results WHERE crawl_id = ?
    GROUP BY status_code
    ORDER BY count DESC
""", (crawl_id,))

# MongoDB  
pipeline = [
    {'$match': {'crawl_id': crawl_id}},
    {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
]
stats = list(db.collection.aggregate(pipeline))
```

## Pipeline Integration

### Artifact Store Integration

Crawlit's database backends integrate seamlessly with the artifact store pipeline:

```python
from crawlit import Crawler
from crawlit.pipelines.artifact_store import ArtifactStore
from crawlit.utils.database import get_database_backend

# Create database-backed pipeline
class DatabasePipeline:
    def __init__(self, db_backend, **db_config):
        self.db = get_database_backend(db_backend, **db_config)
    
    def process_artifact(self, artifact):
        # Convert PageArtifact to database format
        result = {
            'url': artifact.url,
            'status': artifact.http.status,
            'success': artifact.http.status == 200 if artifact.http.status else False,
            'depth': artifact.crawl.depth,
            'title': artifact.extracted.get('title', ''),
            'content_type': artifact.http.content_type,
            'html_content': artifact.content.raw_html,
            'links': artifact.links,
            'images': artifact.extracted.get('images', []),
            'keywords': artifact.extracted.get('keywords', [])
        }
        
        # Save to database
        metadata = {
            'start_url': artifact.crawl.run_id,
            'user_agent': 'crawlit/1.0'
        }
        
        self.db.save_results({artifact.url: result}, metadata)

# Use in crawler
db_pipeline = DatabasePipeline('postgresql', host='localhost', database='crawlit')

crawler = Crawler(
    start_urls=['https://example.com'],
    pipelines=[
        ArtifactStore('./output'),  # File-based storage
        db_pipeline                 # Database storage
    ]
)
```

### Custom Pipeline Integration

```python
from crawlit.interfaces import Pipeline

class DatabaseStoragePipeline(Pipeline):
    def __init__(self, db_backend, **db_config):
        self.db = get_database_backend(db_backend, **db_config)
        self.batch_size = 100
        self.batch_results = {}
        
    def process_artifact(self, artifact):
        # Collect results in batches for efficiency
        result = self._artifact_to_result(artifact)
        self.batch_results[artifact.url] = result
        
        if len(self.batch_results) >= self.batch_size:
            self._flush_batch()
    
    def _flush_batch(self):
        if self.batch_results:
            self.db.save_results(self.batch_results)
            self.batch_results.clear()
    
    def close(self):
        # Flush remaining results
        self._flush_batch()
        self.db.disconnect()
```

## Migration and Backup Strategies

### Database Migration

```python
# Export from SQLite to PostgreSQL
from crawlit.utils.database import SQLiteBackend, PostgreSQLBackend

# Source database
sqlite_db = SQLiteBackend('old_crawls.db')

# Target database  
postgres_db = PostgreSQLBackend(
    host='localhost',
    database='crawlit_new',
    user='crawlit_user',
    password='password'
)

# Migrate all crawls
crawls = sqlite_db.get_crawls(limit=1000)
for crawl in crawls:
    results = sqlite_db.get_results({'crawl_id': crawl['id']})
    
    # Convert results format if needed
    formatted_results = {}
    for result in results:
        formatted_results[result['url']] = {
            'status': result['status_code'],
            'success': bool(result['success']),
            'depth': result['depth'],
            'title': result['title'],
            # ... other fields
        }
    
    # Save to new database
    new_crawl_id = postgres_db.save_results(formatted_results, crawl)
    print(f"Migrated crawl {crawl['id']} -> {new_crawl_id}")
```

### Backup Strategies

```python
import json
from datetime import datetime

def backup_database(db, backup_file):
    """Create JSON backup of database"""
    backup_data = {
        'created_at': datetime.now().isoformat(),
        'crawls': db.get_crawls(limit=10000),  
        'results': {}
    }
    
    # Export all results by crawl
    for crawl in backup_data['crawls']:
        crawl_id = crawl['id']
        results = db.get_results({'crawl_id': crawl_id})
        backup_data['results'][crawl_id] = results
    
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)

def restore_database(db, backup_file):
    """Restore database from JSON backup"""
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)
    
    # Clear existing data
    db.clear_results()
    
    # Restore each crawl
    for crawl in backup_data['crawls']:
        crawl_id = crawl['id']
        results = backup_data['results'].get(str(crawl_id), [])
        
        # Convert results back to expected format
        formatted_results = {}
        for result in results:
            formatted_results[result['url']] = result
        
        db.save_results(formatted_results, crawl)
```

## Examples

### Complete Crawling with Database Storage

```python
from crawlit import Crawler
from crawlit.utils.database import get_database_backend
from crawlit.interfaces import Pipeline

class DatabaseStoragePipeline(Pipeline):
    def __init__(self):
        self.db = get_database_backend('postgresql',
                                     host='localhost',
                                     database='crawlit',
                                     user='crawler',
                                     password='secure_password')
        self.results_batch = {}
        self.current_metadata = None
    
    def start_crawl(self, start_urls, config):
        self.current_metadata = {
            'start_url': start_urls[0] if start_urls else 'unknown',
            'user_agent': config.get('user_agent', 'crawlit/1.0'),
            'max_depth': config.get('max_depth', 0)
        }
    
    def process_artifact(self, artifact):
        result = {
            'status': artifact.http.status,
            'success': artifact.http.status == 200 if artifact.http.status else False,
            'depth': artifact.crawl.depth,
            'title': artifact.extracted.get('title', ''),
            'content_type': artifact.http.content_type,
            'html_content': artifact.content.raw_html,
            'links': artifact.links,
            'images': artifact.extracted.get('images', []),
            'keywords': artifact.extracted.get('keywords', [])
        }
        
        self.results_batch[artifact.url] = result
        
        # Batch save every 50 results
        if len(self.results_batch) >= 50:
            self._save_batch()
    
    def _save_batch(self):
        if self.results_batch:
            crawl_id = self.db.save_results(self.results_batch, self.current_metadata) 
            print(f"Saved batch of {len(self.results_batch)} results (crawl_id: {crawl_id})")
            self.results_batch.clear()
    
    def close(self):
        self._save_batch()  # Save remaining results
        self.db.disconnect()

# Run crawler with database storage
crawler = Crawler(
    start_urls=['https://example.com'],
    max_depth=3,
    pipelines=[DatabaseStoragePipeline()]
)

results = crawler.crawl()
print(f"Crawled {len(results)} pages with database persistence")
```

### Multi-Backend Storage

```python
class MultiDatabasePipeline(Pipeline):
    """Store results in multiple databases for redundancy"""
    
    def __init__(self):
        # Primary storage
        self.primary_db = get_database_backend('postgresql',
                                             host='primary-db.example.com',
                                             database='crawlit')
        
        # Backup storage
        self.backup_db = get_database_backend('mongodb',
                                            host='backup-db.example.com', 
                                            database='crawlit_backup')
        
        # Local cache
        self.cache_db = get_database_backend('sqlite',
                                           database_path='local_cache.db')
    
    def process_artifact(self, artifact):
        result = self._artifact_to_result(artifact)
        
        # Save to all backends (with error handling)
        for db_name, db in [('primary', self.primary_db), 
                           ('backup', self.backup_db),
                           ('cache', self.cache_db)]:
            try:
                db.save_results({artifact.url: result})
                print(f"Saved to {db_name} database: {artifact.url}")
            except Exception as e:
                print(f"Failed to save to {db_name}: {e}")
```

### Analytical Queries

```python
def analyze_crawl_results(db, crawl_id):
    """Generate comprehensive crawl analysis"""
    
    # Get basic statistics
    results = db.get_results({'crawl_id': crawl_id})
    total_pages = len(results)
    successful_pages = len([r for r in results if r['success']])
    
    print(f"Crawl Analysis for ID {crawl_id}")
    print(f"Total Pages: {total_pages}")
    print(f"Successful Pages: {successful_pages} ({successful_pages/total_pages*100:.1f}%)")
    
    # Status code distribution
    from collections import Counter
    status_counts = Counter(r['status_code'] for r in results)
    print("\nStatus Code Distribution:")
    for status, count in status_counts.most_common():
        print(f"  {status}: {count}")
    
    # Content type analysis
    content_types = Counter(r.get('content_type', 'unknown') for r in results)
    print("\nContent Types:")
    for content_type, count in content_types.most_common(5):
        print(f"  {content_type}: {count}")
    
    # Depth analysis
    depth_counts = Counter(r['depth'] for r in results)
    print("\nDepth Distribution:")
    for depth in sorted(depth_counts.keys()):
        print(f"  Depth {depth}: {depth_counts[depth]}")
    
    # Top domains by page count
    from urllib.parse import urlparse
    domains = Counter(urlparse(r['url']).netloc for r in results)
    print("\nTop Domains:")
    for domain, count in domains.most_common(10):
        print(f"  {domain}: {count}")

# Usage
db = get_database_backend('postgresql', host='localhost', database='crawlit')
analyze_crawl_results(db, crawl_id=123)
```

## Troubleshooting

### Common Issues

#### SQLite Database Locked

```python
# Issue: "database is locked" error
# Solution: Ensure proper connection management

class SafeSQLiteBackend(SQLiteBackend):
    def __init__(self, database_path, timeout=30.0):
        super().__init__(database_path)
        # Set busy timeout to handle concurrent access
        self.connect()
        self.conn.execute(f"PRAGMA busy_timeout = {timeout * 1000}")
        self.conn.commit()
```

#### PostgreSQL Connection Issues

```python
# Check PostgreSQL availability
is_available, message = PostgreSQLBackend.check_availability(
    host='localhost',
    database='crawlit',
    user='crawlit_user',
    password='password'
)

if not is_available:
    print("Setup Issues:")
    print(message)
    
    # Common solutions:
    # 1. Start PostgreSQL service: sudo systemctl start postgresql
    # 2. Create database: CREATE DATABASE crawlit;
    # 3. Create user: CREATE USER crawlit_user WITH PASSWORD 'password';
    # 4. Grant permissions: GRANT ALL PRIVILEGES ON DATABASE crawlit TO crawlit_user;
```

#### MongoDB Connection Issues

```python
# Check MongoDB availability
is_available, message = MongoDBBackend.check_availability(
    host='localhost',
    port=27017,
    database='crawlit'
)

if not is_available:
    print("MongoDB Setup Issues:")
    print(message)
    
    # Common solutions:
    # 1. Start MongoDB: sudo systemctl start mongod
    # 2. Docker: docker run -d -p 27017:27017 mongo:latest
    # 3. Check authentication if using auth
```

### Performance Issues

#### Slow Inserts

```python
# Problem: Individual inserts are slow
# Solution: Use batch inserts

# Instead of:
for url, result in results.items():
    db.save_results({url: result})

# Use:
db.save_results(results)  # Bulk insert
```

#### Memory Usage

```python
# Problem: Large result sets consuming memory
# Solution: Process in chunks

def process_large_crawl(db, crawl_id, chunk_size=1000):
    offset = 0
    while True:
        # Get chunk of results (implementation varies by backend)
        if hasattr(db, 'get_results_paginated'):
            chunk = db.get_results_paginated(
                {'crawl_id': crawl_id}, 
                limit=chunk_size, 
                offset=offset
            )
        else:
            # Fallback: get all and slice
            all_results = db.get_results({'crawl_id': crawl_id})
            chunk = all_results[offset:offset+chunk_size]
        
        if not chunk:
            break
            
        # Process chunk
        for result in chunk:
            process_result(result)
        
        offset += chunk_size
```

### Debugging

```python
import logging

# Enable database debugging
logging.getLogger('crawlit.utils.database').setLevel(logging.DEBUG)
logging.getLogger('crawlit.distributed.pool').setLevel(logging.DEBUG)

# Add custom handler for database operations
class DatabaseDebugHandler(logging.Handler):
    def emit(self, record):
        if 'database' in record.name.lower():
            print(f"DB DEBUG: {record.getMessage()}")

logger = logging.getLogger()
logger.addHandler(DatabaseDebugHandler())
```

### Testing Database Integration

```python
import pytest
import tempfile

@pytest.fixture
def test_db():
    """Fixture for testing with temporary SQLite database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = SQLiteBackend(database_path=db_path)
    yield db
    
    db.disconnect()
    os.unlink(db_path)

def test_save_and_retrieve(test_db):
    """Test basic database operations"""
    results = {
        'https://test.com': {
            'status': 200,
            'success': True,
            'depth': 0,
            'title': 'Test Page'
        }
    }
    
    crawl_id = test_db.save_results(results)
    retrieved = test_db.get_results({'crawl_id': crawl_id})
    
    assert len(retrieved) == 1
    assert retrieved[0]['url'] == 'https://test.com'
    assert retrieved[0]['status_code'] == 200
```

This comprehensive guide covers all aspects of database integration in crawlit. The flexible backend architecture allows you to choose the most appropriate database for your use case, from lightweight SQLite for development to enterprise PostgreSQL and flexible MongoDB for production deployments.