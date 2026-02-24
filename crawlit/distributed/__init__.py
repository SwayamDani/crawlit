#!/usr/bin/env python3
"""
Distributed crawling support for crawlit

Provides message queue integration, worker pools, and distributed coordination.
"""

from .message_queue import (
    MessageQueue,
    RabbitMQBackend,
    KafkaBackend,
    get_message_queue
)

from .coordinator import (
    DistributedCrawler,
    CrawlWorker,
    CrawlCoordinator
)

from .pool import (
    ConnectionPool,
    DatabaseConnectionPool,
    HTTPConnectionPool
)

__all__ = [
    # Message queue
    'MessageQueue',
    'RabbitMQBackend',
    'KafkaBackend',
    'get_message_queue',
    
    # Distributed crawling
    'DistributedCrawler',
    'CrawlWorker',
    'CrawlCoordinator',
    
    # Connection pooling
    'ConnectionPool',
    'DatabaseConnectionPool',
    'HTTPConnectionPool',
]




