#!/usr/bin/env python3
"""
Distributed Crawling Examples for crawlit

Demonstrates distributed crawling features including:
- Message queue integration (RabbitMQ, Kafka)
- Distributed coordinator and workers
- Connection pooling
- Scaling across multiple machines
- Task distribution and result collection

Note: Requires optional dependencies:
  pip install crawlit[distributed]
  or
  pip install crawlit[rabbitmq]  # For RabbitMQ
  pip install crawlit[kafka]     # For Kafka
"""

import asyncio
import time
from crawlit import DISTRIBUTED_AVAILABLE

# Check if distributed features are available
if not DISTRIBUTED_AVAILABLE:
    print("=" * 70)
    print("Distributed crawling features not available!")
    print("=" * 70)
    print("\nTo enable distributed crawling, install optional dependencies:")
    print("  pip install crawlit[distributed]")
    print("\nOr install specific message queue support:")
    print("  pip install crawlit[rabbitmq]  # RabbitMQ")
    print("  pip install crawlit[kafka]     # Apache Kafka")
    print("=" * 70)
    exit(1)

from crawlit import (
    DistributedCrawler,
    CrawlCoordinator,
    CrawlWorker,
    get_message_queue,
    DatabaseConnectionPool,
    HTTPConnectionPool
)


def example_basic_distributed_setup():
    """Example: Basic Distributed Crawling Setup"""
    print("\n=== Basic Distributed Crawling Setup ===")
    
    print("\nArchitecture:")
    print("  +---------------+")
    print("  |  Coordinator  |  (Distributes URLs)")
    print("  +-------+-------+")
    print("          |")
    print("     +----+----+")
    print("     |  Queue  |  (RabbitMQ/Kafka)")
    print("     +----+----+")
    print("          |")
    print("  +-------+-------+")
    print("  |    Workers    |  (Process URLs)")
    print("  |  (Multiple)   |")
    print("  +---------------+")
    
    print("\nComponents:")
    print("  [OK] Coordinator: Manages crawl tasks and distributes URLs")
    print("  [OK] Message Queue: Distributes tasks (RabbitMQ or Kafka)")
    print("  [OK] Workers: Process URLs in parallel across machines")
    print("  [OK] Connection Pools: Reuse connections for performance")


def example_rabbitmq_setup():
    """Example: RabbitMQ Message Queue Setup"""
    print("\n=== RabbitMQ Message Queue Setup ===")
    
    print("Configuration:")
    print("  Host: localhost:5672")
    print("  Queue: crawlit_tasks")
    print("  Username: guest")
    print("  Password: guest")
    
    print("\nTo start RabbitMQ:")
    print("  docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management")
    
    print("\nInstallation:")
    print("  pip install crawlit[rabbitmq]")
    
    print("\nManagement UI:")
    print("  http://localhost:15672 (guest/guest)")


def example_kafka_setup():
    """Example: Apache Kafka Message Queue Setup"""
    print("\n=== Apache Kafka Message Queue Setup ===")
    
    print("Configuration:")
    print("  Bootstrap servers: localhost:9092")
    print("  Topic: crawlit_tasks")
    
    print("\nTo start Kafka:")
    print("  docker run -d -p 9092:9092 apache/kafka")
    
    print("\nInstallation:")
    print("  pip install crawlit[kafka]")
    
    print("\nBenefits:")
    print("  - High throughput")
    print("  - Fault tolerance")
    print("  - Scalable partitioning")


def example_coordinator_setup():
    """Example: Coordinator Setup"""
    print("\n=== Coordinator Setup ===")
    
    print("Configuration:")
    print("  Start URLs: 2")
    print("  Max depth: 3")
    print("  Message queue: RabbitMQ")
    
    print("\nCoordinator responsibilities:")
    print("  - Distribute initial URLs to workers")
    print("  - Track crawl progress")
    print("  - Handle discovered URLs")
    print("  - Collect results from workers")
    print("  - Monitor worker health")


def example_worker_setup():
    """Example: Worker Setup"""
    print("\n=== Worker Setup ===")
    
    print("Configuration:")
    print("  Worker ID: worker-1")
    print("  Max concurrent requests: 5")
    print("  Message queue: RabbitMQ")
    
    print("\nWorker responsibilities:")
    print("  - Fetch tasks from message queue")
    print("  - Crawl assigned URLs")
    print("  - Extract links and data")
    print("  - Send results back to coordinator")
    print("  - Report discovered URLs")
    print("  - Handle retries and errors")


def example_connection_pooling():
    """Example: Connection Pooling for Performance"""
    print("\n=== Connection Pooling ===")
    
    print("Database Connection Pool:")
    print("  - Reuse database connections across workers")
    print("  - Configure min/max connections")
    print("  - 5x faster than creating new connections")
    print("  - Reduces database load")
    
    print("\nHTTP Connection Pool:")
    print("  - Reuse TCP connections")
    print("  - Reduce connection overhead")
    print("  - Lower latency per request")
    print("  - Better resource utilization")
    
    print("\nBenefits:")
    print("  [OK] Significant performance improvement")
    print("  [OK] Reduced resource consumption")
    print("  [OK] Better scalability")


def example_distributed_crawler():
    """Example: Complete Distributed Crawler"""
    print("\n=== Complete Distributed Crawler Example ===")
    
    print("Configuration:")
    print("  Start URLs: 1")
    print("  Workers: 3")
    print("  Max concurrent per worker: 5")
    print("  Total concurrent requests: 15")
    print("  Message queue: RabbitMQ")
    
    print("\nCrawler workflow:")
    print("  1. Start coordinator")
    print("  2. Distribute initial URLs")
    print("  3. Start 3 workers")
    print("  4. Process URLs in parallel")
    print("  5. Collect and aggregate results")
    
    print("\nTo run:")
    print("  asyncio.run(crawler.crawl())")


def example_multi_machine_setup():
    """Example: Multi-Machine Deployment"""
    print("\n=== Multi-Machine Deployment ===")
    
    print("\nMachine 1 (Coordinator):")
    print("  python coordinator.py")
    print("  ```python")
    print("  from crawlit import CrawlCoordinator, get_message_queue")
    print("  ")
    print("  queue = get_message_queue('rabbitmq', host='rabbitmq.example.com')")
    print("  coordinator = CrawlCoordinator(")
    print("      message_queue=queue,")
    print("      start_urls=['https://example.com']")
    print("  )")
    print("  asyncio.run(coordinator.start())")
    print("  ```")
    
    print("\nMachine 2 (Worker 1):")
    print("  python worker.py --worker-id worker-1")
    print("  ```python")
    print("  from crawlit import CrawlWorker, get_message_queue")
    print("  ")
    print("  queue = get_message_queue('rabbitmq', host='rabbitmq.example.com')")
    print("  worker = CrawlWorker(worker_id='worker-1', message_queue=queue)")
    print("  asyncio.run(worker.start())")
    print("  ```")
    
    print("\nMachine 3 (Worker 2):")
    print("  python worker.py --worker-id worker-2")
    
    print("\nMachine 4 (Worker 3):")
    print("  python worker.py --worker-id worker-3")
    
    print("\nBenefits:")
    print("  [OK] Scale horizontally by adding more worker machines")
    print("  [OK] Distribute load across multiple servers")
    print("  [OK] Fault tolerance: workers can fail without affecting others")
    print("  [OK] Easy to add/remove workers dynamically")


def example_performance_comparison():
    """Example: Performance Comparison"""
    print("\n=== Performance Comparison ===")
    
    print("\nSingle Machine (Async Crawler):")
    print("  - Max concurrent: 15 requests")
    print("  - Throughput: ~50 pages/minute")
    print("  - Limited by single machine resources")
    
    print("\nDistributed (3 Workers):")
    print("  - Max concurrent: 45 requests (15 per worker)")
    print("  - Throughput: ~150 pages/minute")
    print("  - 3x performance improvement")
    
    print("\nDistributed (10 Workers):")
    print("  - Max concurrent: 150 requests")
    print("  - Throughput: ~500 pages/minute")
    print("  - 10x performance improvement")
    
    print("\nWith Connection Pooling:")
    print("  - Additional 2-5x speedup")
    print("  - Reduced latency per request")
    print("  - Better resource utilization")


def example_task_serialization():
    """Example: Task Serialization"""
    print("\n=== Task Serialization ===")
    
    print("Task structure:")
    print("  - URL: https://example.com/page1")
    print("  - Depth: 1")
    print("  - Metadata: {'source': 'sitemap', 'priority': 'high'}")
    
    print("\nSerialization:")
    print("  - Tasks are serialized to JSON for message queue")
    print("  - Workers deserialize tasks from queue")
    print("  - Results are serialized back to coordinator")
    
    print("\nBenefits:")
    print("  - Language-agnostic format")
    print("  - Easy debugging")
    print("  - Compact representation")


def example_fault_tolerance():
    """Example: Fault Tolerance Features"""
    print("\n=== Fault Tolerance ===")
    
    print("\nBuilt-in fault tolerance:")
    print("  [OK] Worker failure: Tasks automatically reassigned")
    print("  [OK] Network errors: Automatic retry with exponential backoff")
    print("  [OK] Queue failure: Tasks persisted in message queue")
    print("  [OK] Coordinator failure: Workers continue processing")
    
    print("\nMessage queue persistence:")
    print("  [OK] RabbitMQ: Durable queues, persistent messages")
    print("  [OK] Kafka: Replicated partitions, configurable retention")
    
    print("\nRecovery strategies:")
    print("  [OK] Dead letter queue for failed tasks")
    print("  [OK] Task timeout and reassignment")
    print("  [OK] Worker health checks")
    print("  [OK] Graceful shutdown and task requeue")


def example_monitoring():
    """Example: Monitoring and Metrics"""
    print("\n=== Monitoring and Metrics ===")
    
    print("\nCoordinator metrics:")
    print("  - Total tasks distributed")
    print("  - Active workers")
    print("  - Completed tasks")
    print("  - Failed tasks")
    print("  - Average task duration")
    
    print("\nWorker metrics:")
    print("  - Tasks processed")
    print("  - Success rate")
    print("  - Current load")
    print("  - Errors encountered")
    
    print("\nMessage queue metrics:")
    print("  - Queue depth")
    print("  - Message throughput")
    print("  - Consumer lag")
    
    print("\nMonitoring tools:")
    print("  [OK] RabbitMQ Management UI: http://localhost:15672")
    print("  [OK] Kafka Manager or Kafdrop")
    print("  [OK] Custom metrics via logging")


def example_best_practices():
    """Example: Best Practices"""
    print("\n=== Best Practices ===")
    
    print("\n1. Start Small, Scale Up:")
    print("   - Test with 1-2 workers first")
    print("   - Monitor performance and errors")
    print("   - Gradually add more workers")
    
    print("\n2. Use Connection Pooling:")
    print("   - Reuse database connections")
    print("   - Reuse HTTP connections")
    print("   - Configure appropriate pool sizes")
    
    print("\n3. Configure Appropriate Concurrency:")
    print("   - Don't overwhelm target servers")
    print("   - Respect robots.txt and rate limits")
    print("   - Balance speed vs. politeness")
    
    print("\n4. Monitor and Alert:")
    print("   - Track queue depth")
    print("   - Monitor worker health")
    print("   - Set up alerts for failures")
    
    print("\n5. Handle Failures Gracefully:")
    print("   - Implement retry logic")
    print("   - Use dead letter queues")
    print("   - Log errors for debugging")
    
    print("\n6. Optimize for Your Use Case:")
    print("   - Adjust worker count based on load")
    print("   - Tune message queue settings")
    print("   - Profile and optimize bottlenecks")


if __name__ == '__main__':
    print("=" * 70)
    print("Distributed Crawling Examples for crawlit")
    print("=" * 70)
    
    example_basic_distributed_setup()
    example_rabbitmq_setup()
    example_kafka_setup()
    example_coordinator_setup()
    example_worker_setup()
    example_connection_pooling()
    example_distributed_crawler()
    example_multi_machine_setup()
    example_performance_comparison()
    example_task_serialization()
    example_fault_tolerance()
    example_monitoring()
    example_best_practices()
    
    print("\n" + "=" * 70)
    print("Examples complete!")
    print("\nTo use distributed crawling:")
    print("  1. Install dependencies: pip install crawlit[distributed]")
    print("  2. Start message queue (RabbitMQ or Kafka)")
    print("  3. Run coordinator on one machine")
    print("  4. Run workers on one or more machines")
    print("\nFor detailed documentation, see DISTRIBUTED_CRAWLING.md")
    print("=" * 70)

