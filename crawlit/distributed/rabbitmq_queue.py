#!/usr/bin/env python3
"""
Compatibility module for RabbitMQQueue.
Provides simplified interface expected by tests.
"""

from .message_queue import RabbitMQBackend


class RabbitMQQueue:
    """
    Simplified RabbitMQ queue interface.
    Wraps RabbitMQBackend with a simpler API.
    """
    
    def __init__(self, queue_name: str = "crawlit_queue", 
                 host: str = "localhost", port: int = 5672,
                 username: str = "guest", password: str = "guest", **kwargs):
        """
        Initialize RabbitMQ queue.
        
        Args:
            queue_name: Name of the queue to use
            host: RabbitMQ host
            port: RabbitMQ port
            username: Username for authentication
            password: Password for authentication
            **kwargs: Additional connection parameters
        """
        self.queue_name = queue_name
        self.backend = RabbitMQBackend(
            host=host, port=port,
            username=username, password=password,
            **kwargs
        )
        # Create queue on initialization
        self.backend.create_queue(queue_name)
        self._consuming = False
    
    def publish(self, message: dict, priority: int = 0):
        """
        Publish a message to the queue.
        
        Args:
            message: Message dictionary to publish
            priority: Message priority (0-9)
        """
        self.backend.publish(self.queue_name, message, priority)
    
    def consume(self, callback, max_messages=None, timeout=None):
        """
        Consume messages from the queue.
        
        Args:
            callback: Function to call for each message
            max_messages: Maximum number of messages to consume
            timeout: Timeout in seconds
        """
        self._consuming = True
        
        def wrapper(msg):
            if not self._consuming:
                # Stop the backend's channel from consuming
                if hasattr(self.backend, 'channel') and self.backend.channel:
                    self.backend.channel.stop_consuming()
                return False
            result = callback(msg)
            # Check again after callback in case stop_consuming was called
            if not self._consuming and hasattr(self.backend, 'channel') and self.backend.channel:
                self.backend.channel.stop_consuming()
            return result if result is not None else True
        
        self.backend.consume(
            self.queue_name, wrapper,
            max_messages=max_messages,
            timeout=timeout
        )
    
    def stop_consuming(self):
        """Stop consuming messages."""
        self._consuming = False
        # Also stop the backend's channel immediately
        if hasattr(self.backend, 'channel') and self.backend.channel:
            try:
                self.backend.channel.stop_consuming()
            except Exception:
                pass  # Ignore errors if already stopped
    
    def get_message(self, timeout=None, auto_ack=True):
        """
        Get a single message from the queue.
        
        Args:
            timeout: Timeout in seconds (None = no timeout)
            auto_ack: Whether to automatically acknowledge the message
            
        Returns:
            Message dictionary or None if no message available
        """
        self.backend.connect()
        
        method_frame, properties, body = self.backend.channel.basic_get(
            queue=self.queue_name,
            auto_ack=auto_ack
        )
        
        if method_frame:
            import json
            message = json.loads(body)
            # Store delivery tag for manual acknowledgment
            if not auto_ack:
                message['_delivery_tag'] = method_frame.delivery_tag
            return message
        return None
    
    def acknowledge(self, message):
        """
        Manually acknowledge a message.
        
        Args:
            message: Message dictionary (must contain _delivery_tag)
        """
        if '_delivery_tag' in message:
            self.backend.channel.basic_ack(delivery_tag=message['_delivery_tag'])
    
    def get_size(self):
        """Get number of messages in queue."""
        return self.backend.get_queue_size(self.queue_name)
    
    def purge(self):
        """Remove all messages from queue."""
        self.backend.purge_queue(self.queue_name)
    
    def close(self):
        """Close connection to RabbitMQ."""
        self.backend.disconnect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
