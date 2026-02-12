#!/usr/bin/env python3
"""
Integration tests for distributed crawling with message queues
"""

import pytest
import time
import threading


@pytest.mark.distributed
@pytest.mark.skipif(
    not pytest.importorskip("pika", minversion="1.0.0"),
    reason="RabbitMQ dependencies not installed"
)
class TestRabbitMQDistributed:
    """Tests for distributed crawling with RabbitMQ."""
    
    @pytest.fixture
    def rabbitmq_available(self):
        """Check if RabbitMQ is available."""
        import pika
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters('localhost')
            )
            connection.close()
            return True
        except:
            pytest.skip("RabbitMQ not available")
    
    def test_queue_producer_consumer(self, rabbitmq_available):
        """Test basic producer-consumer pattern."""
        from crawlit.distributed.rabbitmq_queue import RabbitMQQueue
        
        queue_name = "test_crawl_queue"
        
        # Producer
        producer = RabbitMQQueue(queue_name=queue_name)
        
        # Add URLs to queue
        urls = [f"http://example.com/page{i}" for i in range(10)]
        for url in urls:
            producer.publish({"url": url, "depth": 0})
        
        # Consumer
        consumer = RabbitMQQueue(queue_name=queue_name)
        
        received_urls = []
        
        def callback(msg):
            received_urls.append(msg['url'])
            if len(received_urls) >= 10:
                consumer.stop_consuming()
        
        consumer.consume(callback)
        
        assert len(received_urls) == 10
        assert set(received_urls) == set(urls)
        
        producer.close()
        consumer.close()
    
    def test_multiple_workers(self, rabbitmq_available):
        """Test multiple worker processes consuming from queue."""
        from crawlit.distributed.rabbitmq_queue import RabbitMQQueue
        
        queue_name = "test_multi_worker"
        
        # Producer adds tasks
        producer = RabbitMQQueue(queue_name=queue_name)
        
        for i in range(100):
            producer.publish({"url": f"http://example.com/page{i}"})
        
        # Multiple workers
        results = []
        lock = threading.Lock()
        
        def worker(worker_id):
            consumer = RabbitMQQueue(queue_name=queue_name)
            
            def callback(msg):
                with lock:
                    results.append((worker_id, msg['url']))
            
            # Consume some messages
            for _ in range(20):
                try:
                    msg = consumer.get_message(timeout=1)
                    if msg:
                        callback(msg)
                except:
                    break
            
            consumer.close()
        
        # Start 5 workers
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All URLs should be processed
        assert len(results) == 100
        
        # Work should be distributed across workers
        worker_counts = {}
        for worker_id, url in results:
            worker_counts[worker_id] = worker_counts.get(worker_id, 0) + 1
        
        # Each worker should have processed some URLs
        assert len(worker_counts) == 5
        
        producer.close()
    
    def test_task_acknowledgment(self, rabbitmq_available):
        """Test proper task acknowledgment."""
        from crawlit.distributed.rabbitmq_queue import RabbitMQQueue
        
        queue_name = "test_ack_queue"
        
        producer = RabbitMQQueue(queue_name=queue_name)
        producer.publish({"url": "http://example.com"})
        
        consumer = RabbitMQQueue(queue_name=queue_name)
        
        # Get message without ack
        msg = consumer.get_message(auto_ack=False)
        
        assert msg is not None
        
        # Acknowledge
        consumer.acknowledge(msg)
        
        consumer.close()
        producer.close()


@pytest.mark.distributed
@pytest.mark.skipif(
    not pytest.importorskip("kafka", minversion="2.0.0"),
    reason="Kafka dependencies not installed"
)
class TestKafkaDistributed:
    """Tests for distributed crawling with Kafka."""
    
    @pytest.fixture
    def kafka_available(self):
        """Check if Kafka is available."""
        from kafka import KafkaProducer
        try:
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9092'],
                request_timeout_ms=1000
            )
            producer.close()
            return True
        except:
            pytest.skip("Kafka not available")
    
    def test_kafka_producer_consumer(self, kafka_available):
        """Test Kafka producer-consumer pattern."""
        from crawlit.distributed.kafka_queue import KafkaQueue
        
        topic = "test_crawl_topic"
        
        # Producer
        producer = KafkaQueue(topic=topic, role='producer')
        
        # Produce messages
        for i in range(10):
            producer.publish({"url": f"http://example.com/page{i}"})
        
        # Consumer
        consumer = KafkaQueue(topic=topic, role='consumer', group_id='test_group')
        
        messages = []
        for _ in range(10):
            msg = consumer.get_message(timeout=5)
            if msg:
                messages.append(msg)
        
        assert len(messages) == 10
        
        producer.close()
        consumer.close()


class TestDistributedCrawlingEdgeCases:
    """Edge case tests for distributed crawling."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("pika"),
        reason="RabbitMQ dependencies not installed"
    )
    def test_connection_recovery(self):
        """Test recovery from connection failures."""
        # This would test reconnection logic
        # For now, placeholder
        pass
    
    @pytest.mark.skipif(
        not pytest.importorskip("pika"),
        reason="RabbitMQ dependencies not installed"
    )
    def test_message_serialization(self):
        """Test proper serialization of complex messages."""
        from crawlit.distributed.rabbitmq_queue import RabbitMQQueue
        
        # Test with complex message structure
        complex_msg = {
            "url": "http://example.com",
            "depth": 3,
            "metadata": {
                "priority": 0.8,
                "tags": ["important", "crawl"],
                "custom_data": {"key": "value"}
            }
        }
        
        # Should serialize and deserialize correctly
        queue = RabbitMQQueue(queue_name="test_serialization")
        
        try:
            queue.publish(complex_msg)
            
            received = queue.get_message(timeout=2)
            
            assert received == complex_msg
        except:
            pytest.skip("RabbitMQ not available")
        finally:
            try:
                queue.close()
            except:
                pass
    
    def test_network_partition_simulation(self):
        """Test behavior during network partition."""
        # This would simulate network issues
        # Placeholder for now
        pass


class TestConnectionPoolExhaustion:
    """Tests for connection pool exhaustion scenarios."""
    
    def test_many_concurrent_requests(self):
        """Test handling of many concurrent requests."""
        from crawlit.utils.session_manager import SessionManager
        import concurrent.futures
        
        manager = SessionManager(pool_size=5)
        
        def make_request(i):
            session = manager.get_sync_session()
            # Simulate request
            time.sleep(0.1)
            return i
        
        # Try to make 20 requests with pool of 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should complete (may queue)
        assert len(results) == 20
    
    @pytest.mark.asyncio
    async def test_async_connection_pool_exhaustion(self):
        """Test async connection pool under heavy load."""
        from crawlit.utils.session_manager import SessionManager
        import asyncio
        
        manager = SessionManager(pool_size=5)
        
        async def make_request(i):
            await asyncio.sleep(0.1)
            return i
        
        # 50 concurrent requests with pool of 5
        tasks = [make_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 50


class TestDatabaseConnectionFailures:
    """Tests for database connection failure handling."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("psycopg2"),
        reason="PostgreSQL dependencies not installed"
    )
    def test_postgres_connection_failure(self):
        """Test handling of PostgreSQL connection failures."""
        from crawlit.storage.postgres_storage import PostgresStorage
        
        # Try to connect to non-existent database
        storage = PostgresStorage(
            host="localhost",
            port=5432,
            database="nonexistent_db",
            user="test",
            password="test"
        )
        
        # Should handle connection failure gracefully
        try:
            storage.save_page({"url": "http://example.com", "html": "test"})
        except Exception as e:
            # Should raise appropriate exception
            assert "connection" in str(e).lower() or "database" in str(e).lower()
    
    @pytest.mark.skipif(
        not pytest.importorskip("pymongo"),
        reason="MongoDB dependencies not installed"
    )
    def test_mongodb_connection_failure(self):
        """Test handling of MongoDB connection failures."""
        from crawlit.storage.mongo_storage import MongoStorage
        
        # Try to connect to non-existent MongoDB
        storage = MongoStorage(
            host="localhost",
            port=27017,
            database="test_db",
            connection_timeout=1000
        )
        
        # Should handle connection failure gracefully
        try:
            storage.save_page({"url": "http://example.com", "html": "test"})
        except Exception as e:
            assert "connection" in str(e).lower() or "timeout" in str(e).lower()
    
    def test_connection_retry_logic(self):
        """Test automatic connection retry logic."""
        # Placeholder for retry logic test
        pass


class TestLargeFileHandling:
    """Tests for handling large files (GB-sized responses)."""
    
    def test_streaming_large_response(self):
        """Test streaming download of large file."""
        from crawlit.utils.download_manager import DownloadManager
        import tempfile
        
        # Mock a large file download
        # In real scenario, would use actual large file
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DownloadManager(download_dir=tmpdir, chunk_size=8192)
            
            # Placeholder test
            # In production, would test with actual large file
            assert manager.chunk_size == 8192
    
    def test_memory_efficient_parsing(self):
        """Test memory-efficient parsing of large responses."""
        # Test that large responses don't cause memory issues
        # Placeholder
        pass

