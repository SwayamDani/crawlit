#!/usr/bin/env python3
"""
Compatibility module for KafkaQueue.
Provides simplified interface expected by tests.
"""

from .message_queue import KafkaBackend


class KafkaQueue:
    """
    Simplified Kafka queue interface.
    Wraps KafkaBackend with a simpler API.
    """
    
    def __init__(self, topic: str = "crawlit_topic",
                 bootstrap_servers: str = "localhost:9092",
                 role: str = None,
                 group_id: str = None,
                 **kwargs):
        """
        Initialize Kafka queue.
        
        Args:
            topic: Kafka topic to use
            bootstrap_servers: Kafka bootstrap servers
            role: Role ('producer' or 'consumer') - not used, for API compatibility
            group_id: Consumer group ID (for consumers)
            **kwargs: Additional Kafka parameters
        """
        self.topic = topic
        self.group_id = group_id
        
        # Remove role from kwargs as it's not a Kafka parameter
        kwargs.pop('role', None)
        
        # Add group_id to kwargs if provided
        if group_id:
            kwargs['group_id'] = group_id
        
        self.backend = KafkaBackend(
            bootstrap_servers=bootstrap_servers,
            **kwargs
        )
        # Create topic on initialization
        self.backend.create_queue(topic)
        self._consuming = False
    
    def publish(self, message: dict, priority: int = 0):
        """
        Publish a message to the topic.
        
        Args:
            message: Message dictionary to publish
            priority: Message priority (not used in Kafka)
        """
        self.backend.publish(self.topic, message, priority)
    
    def consume(self, callback, max_messages=None, timeout=None):
        """
        Consume messages from the topic.
        
        Args:
            callback: Function to call for each message
            max_messages: Maximum number of messages to consume
            timeout: Timeout in seconds
        """
        self._consuming = True
        
        def wrapper(msg):
            if not self._consuming:
                return False
            result = callback(msg)
            return result if result is not None else True
        
        self.backend.consume(
            self.topic, wrapper,
            max_messages=max_messages,
            timeout=timeout
        )
    
    def stop_consuming(self):
        """Stop consuming messages."""
        self._consuming = False
    
    def get_message(self, timeout=None):
        """
        Get a single message from the topic.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Message dictionary or None if no message available
        """
        # For Kafka, we need to poll the consumer
        if not hasattr(self.backend, 'consumer') or self.backend.consumer is None:
            # Initialize consumer if not already done
            if not hasattr(self.backend, 'kafka_consumer_class'):
                return None
            
            from kafka import KafkaConsumer
            import json
            
            self.backend.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.backend.bootstrap_servers,
                group_id=self.group_id or 'crawlit_group',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                consumer_timeout_ms=timeout * 1000 if timeout else 1000
            )
        
        # Poll for a message
        try:
            for message in self.backend.consumer:
                return message.value
        except StopIteration:
            return None
        return None
    
    def close(self):
        """Close connection to Kafka."""
        self.backend.disconnect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
