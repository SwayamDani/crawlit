# Distributed Crawling

## Overview

crawlit supports distributed crawling across multiple workers using message queues for coordination. This enables horizontal scaling for large-scale web crawling operations while maintaining consistency and avoiding duplicate work.

## Architecture

The distributed crawling system consists of:

- **Coordinator** - Manages the crawl job and distributes URLs to workers
- **Workers** - Execute crawling tasks and report results back
- **Message Queue** - Handles communication between coordinator and workers
- **Shared Storage** - Stores results and maintains crawl state

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Coordinator │────▶│ Message     │────▶│   Worker 1  │
│             │     │   Queue     │     │             │
│   Job Mgmt  │     │             │     │ Crawling    │
│   URL Mgr   │     │ RabbitMQ/   │     │ Extraction  │
│ Result Agg  │◀────│   Kafka     │◀────│   Storage   │
└─────────────┘     │             │     └─────────────┘
                    │             │     ┌─────────────┐
                    │             │────▶│   Worker 2  │
                    │             │     │             │
                    │             │     │ Crawling    │
                    │             │◀────│ Extraction  │
                    └─────────────┘     │   Storage   │
                                        └─────────────┘
```

## Message Queue Support

### RabbitMQ Integration

Install RabbitMQ support:

```bash
pip install crawlit[rabbitmq]
```

Configuration:

```python
from crawlit.distributed import RabbitMQCoordinator, RabbitMQWorker

# Coordinator setup
coordinator = RabbitMQCoordinator(
    start_url="https://example.com",
    rabbitmq_url="amqp://localhost:5672",
    queue_name="crawlit_jobs",
    max_depth=3,
    num_workers=5
)

# Worker setup  
worker = RabbitMQWorker(
    worker_id="worker-001",
    rabbitmq_url="amqp://localhost:5672",
    queue_name="crawlit_jobs",
    result_queue="crawlit_results"
)
```

### Kafka Integration

Install Kafka support:

```bash
pip install crawlit[kafka]
```

Configuration:

```python
from crawlit.distributed import KafkaCoordinator, KafkaWorker

# Coordinator setup
coordinator = KafkaCoordinator(
    start_url="https://example.com",
    bootstrap_servers=["localhost:9092"],
    topic_prefix="crawlit",
    max_depth=3,
    num_workers=5
)

# Worker setup
worker = KafkaWorker(
    worker_id="worker-001", 
    bootstrap_servers=["localhost:9092"],
    topic_prefix="crawlit"
)
```

## Coordinator Setup

The coordinator manages job distribution and result aggregation:

```python
from crawlit.distributed import DistributedCrawler

# Basic distributed crawler
crawler = DistributedCrawler(
    start_url="https://large-site.com",
    backend="rabbitmq",
    backend_config={
        "url": "amqp://user:pass@localhost:5672",
        "queue_name": "crawlit_jobs"
    },
    max_depth=5,
    num_workers=10,
    max_pages_per_worker=1000
)

# Start the crawl
crawler.start()

# Monitor progress
while not crawler.is_complete():
    status = crawler.get_status()
    print(f"Progress: {status.pages_crawled}/{status.estimated_pages}")
    time.sleep(10)

# Get final results
results = crawler.get_results()
```

### Coordinator Configuration

```python
coordinator_config = {
    # Job distribution
    "batch_size": 50,              # URLs per batch sent to workers
    "max_queue_size": 10000,       # Max URLs in queue
    "worker_timeout": 300,         # Worker response timeout
    
    # Load balancing
    "load_balance_strategy": "round_robin",  # round_robin, least_loaded
    "max_pages_per_worker": 1000,
    "worker_health_check_interval": 30,
    
    # Fault tolerance
    "retry_failed_urls": True,
    "max_retries": 3,
    "dead_letter_queue": True,
    
    # State management
    "checkpoint_interval": 100,    # Save state every N pages
    "resume_from_checkpoint": True
}
```

## Worker Setup

Workers execute crawling tasks received from the coordinator:

```python
from crawlit.distributed import CrawlWorker

# Configure worker
worker = CrawlWorker(
    worker_id="worker-001",
    backend="rabbitmq",
    backend_config={
        "url": "amqp://localhost:5672",
        "queue_name": "crawlit_jobs",
        "result_queue": "crawlit_results"
    },
    
    # Crawler configuration for this worker
    crawler_config={
        "user_agent": "DistributedCrawler/1.0",
        "delay": 1.0,
        "timeout": 30,
        "enable_table_extraction": True,
        "enable_keyword_extraction": True
    }
)

# Start worker (blocking)
worker.start()
```

### Worker Configuration

```python
worker_config = {
    # Performance
    "max_concurrent_requests": 5,
    "batch_processing": True,
    "result_batch_size": 10,
    
    # Resource management
    "max_memory_mb": 512,
    "max_pages_per_session": 1000,
    "restart_after_pages": 5000,
    
    # Health reporting
    "health_report_interval": 60,
    "performance_metrics": True,
    
    # Error handling
    "continue_on_error": True,
    "error_threshold": 0.1,  # Stop if >10% of requests fail
}
```

## Load Balancing Strategies

### Round Robin

```python
# Distribute URLs evenly across workers
coordinator = DistributedCrawler(
    start_url="https://example.com",
    load_balance_strategy="round_robin"
)
```

### Least Loaded

```python
# Send work to workers with least current load
coordinator = DistributedCrawler(
    start_url="https://example.com", 
    load_balance_strategy="least_loaded",
    load_metrics=["cpu_usage", "memory_usage", "queue_size"]
)
```

### Domain-Based Partitioning

```python
# Route URLs based on domain to ensure politeness per domain
coordinator = DistributedCrawler(
    start_url="https://example.com",
    load_balance_strategy="domain_partition",
    per_domain_workers=True
)
```

## State Synchronization

### URL Deduplication

```python
from crawlit.distributed import RedisURLStore, DatabaseURLStore

# Redis-based URL tracking
url_store = RedisURLStore(
    host="localhost",
    port=6379,
    db=0,
    ttl=3600  # URLs expire after 1 hour
)

coordinator = DistributedCrawler(
    start_url="https://example.com",
    url_store=url_store,
    deduplication=True
)

# Database-based URL tracking  
url_store = DatabaseURLStore(
    connection_string="postgresql://user:pass@localhost/crawlit",
    table_name="crawled_urls"
)
```

### Result Aggregation

```python
from crawlit.distributed import ResultAggregator

# Aggregate results from multiple workers
aggregator = ResultAggregator(
    storage_backend="postgresql",
    connection_string="postgresql://user:pass@localhost/crawlit",
    
    # Result processing
    merge_duplicates=True,
    validate_results=True,
    export_formats=["json", "csv"]
)

coordinator = DistributedCrawler(
    start_url="https://example.com",
    result_aggregator=aggregator
)
```

## Monitoring and Health Checks

### Worker Health Monitoring

```python
from crawlit.distributed import HealthMonitor

monitor = HealthMonitor(
    check_interval=30,
    metrics=["cpu_usage", "memory_usage", "pages_per_minute"],
    
    # Alert thresholds
    cpu_threshold=80,
    memory_threshold=90,
    error_rate_threshold=0.1
)

# Integrate with coordinator
coordinator = DistributedCrawler(
    start_url="https://example.com",
    health_monitor=monitor,
    auto_scale=True  # Automatically add/remove workers
)
```

### Performance Metrics

```python
# Enable comprehensive metrics collection
coordinator = DistributedCrawler(
    start_url="https://example.com",
    metrics_enabled=True,
    metrics_backend="prometheus",  # or "influxdb", "statsd"
    metrics_config={
        "host": "localhost",
        "port": 9090
    }
)

# Access real-time metrics
metrics = coordinator.get_metrics()
print(f"Pages/sec: {metrics.pages_per_second}")
print(f"Active workers: {metrics.active_workers}")
print(f"Queue depth: {metrics.queue_depth}")
```

## Fault Tolerance

### Worker Failure Handling

```python
coordinator = DistributedCrawler(
    start_url="https://example.com",
    
    # Fault tolerance settings
    worker_timeout=300,           # Consider worker dead after 5 minutes
    max_worker_failures=3,        # Max failures before removing worker
    retry_failed_batches=True,    # Retry work from failed workers
    
    # Auto-recovery
    auto_restart_workers=True,
    worker_restart_delay=60,
    
    # Dead letter handling
    dead_letter_queue="crawlit_failed",
    max_dead_letter_retries=5
)
```

### Checkpoint and Resume

```python
# Enable checkpointing for large crawls
coordinator = DistributedCrawler(
    start_url="https://example.com",
    
    # Checkpointing
    checkpoint_enabled=True,
    checkpoint_interval=1000,     # Every 1000 pages
    checkpoint_storage="redis",   # or "file", "database"
    
    # Resume capability
    resume_crawl_id="large_crawl_001",
    auto_resume=True
)

# Manual checkpoint
coordinator.save_checkpoint()

# Resume from checkpoint
coordinator = DistributedCrawler.resume_from_checkpoint(
    crawl_id="large_crawl_001"
)
```

## Deployment Patterns

### Docker Compose Setup

```yaml
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: crawlit
      RABBITMQ_DEFAULT_PASS: password

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  coordinator:
    image: crawlit:latest
    command: python -m crawlit.distributed.coordinator
    environment:
      CRAWLIT_BACKEND: rabbitmq
      CRAWLIT_RABBITMQ_URL: amqp://crawlit:password@rabbitmq:5672
      CRAWLIT_START_URL: https://example.com
    depends_on:
      - rabbitmq
      - redis

  worker:
    image: crawlit:latest
    command: python -m crawlit.distributed.worker
    environment:
      CRAWLIT_BACKEND: rabbitmq
      CRAWLIT_RABBITMQ_URL: amqp://crawlit:password@rabbitmq:5672
      CRAWLIT_WORKER_ID: worker-${HOSTNAME}
    depends_on:
      - rabbitmq
      - redis
    deploy:
      replicas: 5
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crawlit-coordinator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crawlit-coordinator
  template:
    metadata:
      labels:
        app: crawlit-coordinator
    spec:
      containers:
      - name: coordinator
        image: crawlit:latest
        command: ["python", "-m", "crawlit.distributed.coordinator"]
        env:
        - name: CRAWLIT_BACKEND
          value: "rabbitmq"
        - name: CRAWLIT_RABBITMQ_URL
          valueFrom:
            secretKeyRef:
              name: crawlit-secrets
              key: rabbitmq-url

---
apiVersion: apps/v1  
kind: Deployment
metadata:
  name: crawlit-worker
spec:
  replicas: 10
  selector:
    matchLabels:
      app: crawlit-worker
  template:
    metadata:
      labels:
        app: crawlit-worker
    spec:
      containers:
      - name: worker
        image: crawlit:latest
        command: ["python", "-m", "crawlit.distributed.worker"]
        env:
        - name: CRAWLIT_BACKEND
          value: "rabbitmq"
        - name: CRAWLIT_RABBITMQ_URL
          valueFrom:
            secretKeyRef:
              name: crawlit-secrets  
              key: rabbitmq-url
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

### AWS ECS Deployment

```json
{
  "family": "crawlit-distributed",
  "taskDefinition": {
    "containerDefinitions": [
      {
        "name": "crawlit-coordinator",
        "image": "your-account.dkr.ecr.region.amazonaws.com/crawlit:latest",
        "command": ["python", "-m", "crawlit.distributed.coordinator"],
        "environment": [
          {"name": "CRAWLIT_BACKEND", "value": "rabbitmq"},
          {"name": "CRAWLIT_RABBITMQ_URL", "value": "amqp://user:pass@mq.region.amazonaws.com:5672"}
        ],
        "logConfiguration": {
          "logDriver": "awslogs",
          "options": {
            "awslogs-group": "/ecs/crawlit",
            "awslogs-region": "us-east-1"
          }
        }
      }
    ]
  },
  "serviceName": "crawlit-coordinator",
  "desiredCount": 1
}
```

## Performance Scaling

### Horizontal Scaling Guidelines

```python
# Calculate optimal worker count
def calculate_workers(target_pages, pages_per_worker_per_hour=1000, target_hours=1):
    return math.ceil(target_pages / (pages_per_worker_per_hour * target_hours))

# Example: crawl 100k pages in 2 hours  
optimal_workers = calculate_workers(100000, target_hours=2)
print(f"Recommended workers: {optimal_workers}")

coordinator = DistributedCrawler(
    start_url="https://large-site.com",
    num_workers=optimal_workers,
    auto_scale=True,
    scale_up_threshold=0.8,    # Add workers if queue >80% full
    scale_down_threshold=0.2   # Remove workers if queue <20% full
)
```

### Resource Optimization

```python
# Configure workers for different resource constraints
coordinator = DistributedCrawler(
    start_url="https://example.com",
    
    # Worker resource profiles
    worker_profiles={
        "small": {
            "max_concurrent_requests": 2,
            "memory_limit_mb": 256,
            "pages_per_session": 500
        },
        "medium": {
            "max_concurrent_requests": 5, 
            "memory_limit_mb": 512,
            "pages_per_session": 1000
        },
        "large": {
            "max_concurrent_requests": 10,
            "memory_limit_mb": 1024,
            "pages_per_session": 2000
        }
    },
    
    # Auto-assign profiles based on worker resources
    auto_profile_assignment=True
)
```

## Best Practices

### 1. Start Small, Scale Up

```python
# Begin with a small distributed setup
coordinator = DistributedCrawler(
    start_url="https://example.com",
    num_workers=3,
    max_depth=2,
    test_run=True  # Limited crawl to test setup
)

# Scale up based on performance
if coordinator.average_pages_per_second > 5:
    coordinator.scale_workers(10)
```

### 2. Domain-Aware Distribution

```python
# Respect per-domain politeness in distributed setup
coordinator = DistributedCrawler(
    start_url="https://example.com",
    per_domain_workers=True,      # Assign domains to specific workers
    domain_delay=2.0,             # 2 second delay per domain
    max_workers_per_domain=2      # Max 2 workers per domain
)
```

### 3. Monitor and Adjust

```python
# Continuous monitoring and adjustment
coordinator = DistributedCrawler(
    start_url="https://example.com",
    
    # Monitoring
    performance_monitoring=True,
    alert_on_slow_workers=True,
    alert_on_high_error_rate=True,
    
    # Auto-adjustment
    dynamic_batching=True,        # Adjust batch size based on worker performance
    adaptive_delays=True,         # Adjust delays based on server response
    auto_retry_tuning=True        # Adjust retry logic based on success rates
)
```

### 4. Graceful Shutdown

```python
import signal

coordinator = DistributedCrawler(start_url="https://example.com")

def shutdown_handler(signum, frame):
    print("Shutting down gracefully...")
    coordinator.stop_graceful()  # Finish current work
    coordinator.save_checkpoint()
    exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

coordinator.start()
```

## Troubleshooting

### Common Issues

1. **Workers Not Connecting**
   ```python
   # Check message queue connectivity
   coordinator.test_connectivity()
   
   # Verify worker registration
   active_workers = coordinator.get_active_workers()
   print(f"Active workers: {len(active_workers)}")
   ```

2. **Duplicate Results**
   ```python
   # Enable stronger deduplication
   coordinator = DistributedCrawler(
       start_url="https://example.com",
       deduplication_method="content_hash",  # vs "url" 
       deduplication_storage="redis"         # Shared across workers
   )
   ```

3. **Worker Performance Issues**
   ```python
   # Monitor worker performance
   worker_stats = coordinator.get_worker_stats()
   for worker_id, stats in worker_stats.items():
       if stats.pages_per_minute < 10:
           print(f"Slow worker: {worker_id}")
           coordinator.restart_worker(worker_id)
   ```

4. **Memory Issues with Large Crawls**
   ```python
   # Configure memory management
   coordinator = DistributedCrawler(
       start_url="https://example.com",
       
       # Memory optimization
       streaming_results=True,       # Don't hold all results in memory
       result_batch_size=100,        # Process results in batches
       worker_memory_limit=512,      # MB per worker
       garbage_collection_interval=1000  # Pages between GC
   )
   ```

This distributed crawling system enables crawlit to scale from single-machine crawls to enterprise-grade distributed operations handling millions of pages across multiple workers and data centers.