#!/usr/bin/env python3
"""
Simple tests for distributed crawling features (non-blocking only)
"""

import pytest


class TestDistributedImports:
    """Test that distributed modules can be imported"""
    
    def test_message_queue_module_import(self):
        """Test message queue module imports"""
        from crawlit.distributed import message_queue
        assert message_queue is not None
    
    def test_coordinator_module_import(self):
        """Test coordinator module imports"""
        from crawlit.distributed import coordinator
        assert coordinator is not None
    
    def test_pool_module_import(self):
        """Test pool module imports"""
        from crawlit.distributed import pool
        assert pool is not None
    
    def test_distributed_package_imports(self):
        """Test distributed package level imports"""
        try:
            from crawlit.distributed import (
                MessageQueue,
                get_message_queue,
                ConnectionPool,
                HTTPConnectionPool,
                DatabaseConnectionPool
            )
            assert MessageQueue is not None
            assert get_message_queue is not None
            assert ConnectionPool is not None
        except ImportError as e:
            pytest.skip(f"Distributed dependencies not installed: {e}")


class TestMessageQueueAvailability:
    """Test message queue availability checking"""
    
    def test_rabbitmq_availability_check_method_exists(self):
        """Test RabbitMQ has availability check method"""
        try:
            from crawlit.distributed.message_queue import RabbitMQBackend
            assert hasattr(RabbitMQBackend, 'check_availability')
            assert callable(RabbitMQBackend.check_availability)
        except ImportError:
            pytest.skip("RabbitMQ dependencies not installed")
    
    def test_kafka_availability_check_method_exists(self):
        """Test Kafka has availability check method"""
        try:
            from crawlit.distributed.message_queue import KafkaBackend
            assert hasattr(KafkaBackend, 'check_availability')
            assert callable(KafkaBackend.check_availability)
        except ImportError:
            pytest.skip("Kafka dependencies not installed")
    
    def test_get_message_queue_invalid_backend(self):
        """Test factory rejects invalid backend"""
        try:
            from crawlit.distributed.message_queue import get_message_queue
            
            with pytest.raises(ValueError, match="Unknown backend type"):
                get_message_queue('invalid_backend_xyz')
        except ImportError:
            pytest.skip("Message queue dependencies not installed")


class TestConnectionPoolBasics:
    """Test connection pool basic functionality"""
    
    def test_http_connection_pool_class_exists(self):
        """Test HTTPConnectionPool class exists"""
        from crawlit.distributed.pool import HTTPConnectionPool
        assert HTTPConnectionPool is not None
    
    def test_database_connection_pool_class_exists(self):
        """Test DatabaseConnectionPool class exists"""
        from crawlit.distributed.pool import DatabaseConnectionPool
        assert DatabaseConnectionPool is not None
    
    def test_http_pool_initialization(self):
        """Test HTTP pool can be initialized"""
        from crawlit.distributed.pool import HTTPConnectionPool
        
        pool = HTTPConnectionPool(
            min_connections=1,
            max_connections=3,
            max_idle_time=60.0
        )
        
        assert pool.min_connections == 1
        assert pool.max_connections == 3
        assert pool.max_idle_time == 60.0
        
        # Close immediately to avoid hanging
        pool.close_all()
    
    def test_http_pool_stats_structure(self):
        """Test that pool stats have correct structure"""
        from crawlit.distributed.pool import HTTPConnectionPool
        
        pool = HTTPConnectionPool(min_connections=1, max_connections=3)
        stats = pool.get_stats()
        
        assert 'created' in stats
        assert 'reused' in stats
        assert 'closed' in stats
        assert 'active_connections' in stats
        assert 'pool_size' in stats
        assert 'max_connections' in stats
        
        pool.close_all()


class TestCrawlTaskSerialization:
    """Test CrawlTask without coordinator"""
    
    def test_crawl_task_creation(self):
        """Test creating a crawl task"""
        from crawlit.distributed.coordinator import CrawlTask
        
        task = CrawlTask(
            url='https://example.com',
            depth=0,
            metadata={'priority': 'high'}
        )
        
        assert task.url == 'https://example.com'
        assert task.depth == 0
        assert task.metadata['priority'] == 'high'
        assert task.task_id is not None
        assert len(task.task_id) > 0
    
    def test_crawl_task_to_dict(self):
        """Test task serialization to dictionary"""
        from crawlit.distributed.coordinator import CrawlTask
        
        task = CrawlTask('https://example.com', depth=1)
        task_dict = task.to_dict()
        
        assert isinstance(task_dict, dict)
        assert task_dict['url'] == 'https://example.com'
        assert task_dict['depth'] == 1
        assert 'task_id' in task_dict
        assert 'created_at' in task_dict
        assert 'metadata' in task_dict
    
    def test_crawl_task_from_dict(self):
        """Test task deserialization from dictionary"""
        from crawlit.distributed.coordinator import CrawlTask
        
        task_dict = {
            'url': 'https://example.com',
            'depth': 2,
            'task_id': 'test_id_123',
            'created_at': 1234567890.0,
            'metadata': {'test': 'data'}
        }
        
        task = CrawlTask.from_dict(task_dict)
        
        assert task.url == 'https://example.com'
        assert task.depth == 2
        assert task.task_id == 'test_id_123'
        assert task.metadata['test'] == 'data'
    
    def test_crawl_task_roundtrip(self):
        """Test task serialization roundtrip"""
        from crawlit.distributed.coordinator import CrawlTask
        
        original = CrawlTask('https://example.com', depth=3, metadata={'key': 'value'})
        task_dict = original.to_dict()
        restored = CrawlTask.from_dict(task_dict)
        
        assert restored.url == original.url
        assert restored.depth == original.depth
        assert restored.task_id == original.task_id
        assert restored.metadata == original.metadata


class TestOptionalDependencies:
    """Test optional dependencies configuration"""
    
    def test_pyproject_has_distributed_deps(self):
        """Test that pyproject.toml includes distributed dependencies"""
        import os
        
        pyproject_path = 'pyproject.toml'
        if not os.path.exists(pyproject_path):
            pytest.skip("pyproject.toml not found")
        
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for distributed dependencies
            assert 'rabbitmq' in content.lower(), "Should have RabbitMQ dependency option"
            assert 'kafka' in content.lower(), "Should have Kafka dependency option"
            assert 'pika' in content or 'rabbitmq' in content, "Should specify pika for RabbitMQ"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

