#!/usr/bin/env python3
"""
message_queue.py - Message queue abstraction for distributed crawling

Supports RabbitMQ and Kafka for task distribution across workers.
"""

import logging
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)


class MessageQueue(ABC):
    """Abstract base class for message queue backends"""
    
    @classmethod
    @abstractmethod
    def check_availability(cls, **config) -> tuple[bool, str]:
        """
        Check if message queue is available and properly configured.
        
        Returns:
            tuple: (is_available: bool, message: str)
        """
        pass
    
    @abstractmethod
    def connect(self):
        """Establish connection to message queue"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection to message queue"""
        pass
    
    @abstractmethod
    def publish(self, queue_name: str, message: Dict[str, Any], priority: int = 0):
        """
        Publish a message to a queue.
        
        Args:
            queue_name: Name of the queue
            message: Message data (will be JSON serialized)
            priority: Message priority (0-9, higher = more priority)
        """
        pass
    
    @abstractmethod
    def consume(self, queue_name: str, callback: Callable[[Dict[str, Any]], bool],
                max_messages: Optional[int] = None, timeout: Optional[int] = None):
        """
        Consume messages from a queue.
        
        Args:
            queue_name: Name of the queue
            callback: Function to call for each message. Return True to ack, False to nack.
            max_messages: Maximum number of messages to consume (None = infinite)
            timeout: Timeout in seconds (None = no timeout)
        """
        pass
    
    @abstractmethod
    def get_queue_size(self, queue_name: str) -> int:
        """Get the number of messages in a queue"""
        pass
    
    @abstractmethod
    def purge_queue(self, queue_name: str):
        """Remove all messages from a queue"""
        pass
    
    @abstractmethod
    def create_queue(self, queue_name: str, **kwargs):
        """Create a queue if it doesn't exist"""
        pass
    
    @abstractmethod
    def delete_queue(self, queue_name: str):
        """Delete a queue"""
        pass


class RabbitMQBackend(MessageQueue):
    """
    RabbitMQ message queue backend.
    
    Features:
    - Reliable message delivery
    - Message acknowledgment
    - Priority queues
    - Durable queues
    
    Requires: pika
    """
    
    def __init__(self, host: str = "localhost", port: int = 5672,
                 username: str = "guest", password: str = "guest",
                 virtual_host: str = "/", **kwargs):
        """
        Initialize RabbitMQ backend.
        
        Args:
            host: RabbitMQ host
            port: RabbitMQ port (default: 5672)
            username: Username
            password: Password
            virtual_host: Virtual host
            **kwargs: Additional pika connection parameters
        """
        try:
            import pika
            self.pika = pika
        except ImportError:
            raise ImportError(
                "RabbitMQ support requires pika. "
                "Install with: pip install crawlit[rabbitmq] or pip install pika"
            )
        
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.kwargs = kwargs
        
        self.connection = None
        self.channel = None
        self.connect()
    
    @classmethod
    def check_availability(cls, **config) -> tuple[bool, str]:
        """Check if RabbitMQ is available"""
        # Check if pika is installed
        try:
            import pika
        except ImportError:
            return (False,
                    "[ERROR] RabbitMQ support not installed.\n\n"
                    "To use RabbitMQ, install the required dependency:\n"
                    "  pip install crawlit[rabbitmq]\n"
                    "  OR\n"
                    "  pip install pika\n")
        
        # Check if we can connect
        host = config.get('host', 'localhost')
        port = config.get('port', 5672)
        username = config.get('username', 'guest')
        password = config.get('password', 'guest')
        virtual_host = config.get('virtual_host', '/')
        
        try:
            credentials = pika.PlainCredentials(username, password)
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=virtual_host,
                credentials=credentials,
                connection_attempts=1,
                socket_timeout=3
            )
            connection = pika.BlockingConnection(parameters)
            connection.close()
            
            return (True, f"[OK] RabbitMQ is available at {host}:{port}")
        
        except pika.exceptions.AMQPConnectionError as e:
            error_msg = str(e)
            
            if "connection refused" in error_msg.lower():
                return (False,
                        f"[ERROR] Cannot connect to RabbitMQ at {host}:{port}\n\n"
                        "RabbitMQ server is not running or not accessible.\n\n"
                        "Setup instructions:\n"
                        "1. Install RabbitMQ:\n"
                        "   Ubuntu/Debian: sudo apt-get install rabbitmq-server\n"
                        "   macOS: brew install rabbitmq\n"
                        "   Windows: Download from https://www.rabbitmq.com/download.html\n\n"
                        "2. Start RabbitMQ:\n"
                        "   Linux: sudo systemctl start rabbitmq-server\n"
                        "   macOS: brew services start rabbitmq\n"
                        "   Windows: Start via Services app\n\n"
                        "Alternative: Use Docker:\n"
                        "   docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management\n")
            
            elif "authentication" in error_msg.lower() or "access refused" in error_msg.lower():
                return (False,
                        f"[ERROR] RabbitMQ authentication failed\n\n"
                        "The username or password is incorrect.\n\n"
                        "Default credentials: username='guest', password='guest'\n"
                        "Note: 'guest' user can only connect from localhost.\n\n"
                        "To create a new user:\n"
                        "  sudo rabbitmqctl add_user myuser mypassword\n"
                        "  sudo rabbitmqctl set_permissions -p / myuser '.*' '.*' '.*'\n")
            
            else:
                return (False, f"[ERROR] RabbitMQ error: {error_msg}\n")
        
        except Exception as e:
            return (False, f"[ERROR] Unexpected error checking RabbitMQ: {e}\n")
    
    def connect(self):
        """Establish connection to RabbitMQ"""
        if self.connection is None or self.connection.is_closed:
            credentials = self.pika.PlainCredentials(self.username, self.password)
            parameters = self.pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials,
                **self.kwargs
            )
            self.connection = self.pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info(f"Connected to RabbitMQ: {self.host}:{self.port}")
    
    def disconnect(self):
        """Close connection to RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
    
    def create_queue(self, queue_name: str, durable: bool = True, 
                    max_priority: int = 10, **kwargs):
        """
        Create a queue in RabbitMQ.
        
        Args:
            queue_name: Name of the queue
            durable: Whether queue survives broker restart
            max_priority: Maximum message priority (0-255)
            **kwargs: Additional queue arguments
        """
        self.connect()
        
        arguments = {'x-max-priority': max_priority}
        arguments.update(kwargs.get('arguments', {}))
        
        self.channel.queue_declare(
            queue=queue_name,
            durable=durable,
            arguments=arguments
        )
        logger.debug(f"Queue '{queue_name}' created/verified")
    
    def delete_queue(self, queue_name: str):
        """Delete a queue from RabbitMQ"""
        self.connect()
        self.channel.queue_delete(queue=queue_name)
        logger.info(f"Queue '{queue_name}' deleted")
    
    def publish(self, queue_name: str, message: Dict[str, Any], priority: int = 0):
        """Publish a message to RabbitMQ queue"""
        self.connect()
        
        # Ensure queue exists
        self.create_queue(queue_name)
        
        # Serialize message
        body = json.dumps(message)
        
        # Publish with priority
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=body,
            properties=self.pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                priority=priority
            )
        )
        logger.debug(f"Published message to '{queue_name}' (priority={priority})")
    
    def consume(self, queue_name: str, callback: Callable[[Dict[str, Any]], bool],
                max_messages: Optional[int] = None, timeout: Optional[int] = None):
        """Consume messages from RabbitMQ queue"""
        self.connect()
        
        # Ensure queue exists
        self.create_queue(queue_name)
        
        messages_processed = 0
        start_time = time.time()
        
        def on_message(channel, method, properties, body):
            nonlocal messages_processed
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                channel.stop_consuming()
                return
            
            # Check max messages
            if max_messages and messages_processed >= max_messages:
                channel.stop_consuming()
                return
            
            try:
                # Deserialize message
                message = json.loads(body)
                
                # Call user callback
                success = callback(message)
                
                # Acknowledge or reject
                if success:
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    messages_processed += 1
                else:
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # Set QoS (prefetch count)
        self.channel.basic_qos(prefetch_count=1)
        
        # Start consuming
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message
        )
        
        logger.info(f"Starting to consume from '{queue_name}'")
        self.channel.start_consuming()
    
    def get_queue_size(self, queue_name: str) -> int:
        """Get the number of messages in a queue"""
        self.connect()
        result = self.channel.queue_declare(queue=queue_name, passive=True)
        return result.method.message_count
    
    def purge_queue(self, queue_name: str):
        """Remove all messages from a queue"""
        self.connect()
        self.channel.queue_purge(queue=queue_name)
        logger.info(f"Purged queue '{queue_name}'")


class KafkaBackend(MessageQueue):
    """
    Apache Kafka message queue backend.
    
    Features:
    - High throughput
    - Distributed architecture
    - Message persistence
    - Partitioning support
    
    Requires: kafka-python
    """
    
    def __init__(self, bootstrap_servers: List[str] = None,
                 client_id: str = "crawlit",
                 group_id: str = "crawlit_workers",
                 **kwargs):
        """
        Initialize Kafka backend.
        
        Args:
            bootstrap_servers: List of Kafka brokers (default: ['localhost:9092'])
            client_id: Client identifier
            group_id: Consumer group ID
            **kwargs: Additional Kafka parameters
        """
        try:
            from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
            from kafka.admin import NewTopic
            self.kafka_producer_class = KafkaProducer
            self.kafka_consumer_class = KafkaConsumer
            self.kafka_admin_class = KafkaAdminClient
            self.new_topic_class = NewTopic
        except ImportError:
            raise ImportError(
                "Kafka support requires kafka-python. "
                "Install with: pip install crawlit[kafka] or pip install kafka-python"
            )
        
        self.bootstrap_servers = bootstrap_servers or ['localhost:9092']
        self.client_id = client_id
        self.group_id = group_id
        self.kwargs = kwargs
        
        self.producer = None
        self.consumer = None
        self.admin_client = None
        self.connect()
    
    @classmethod
    def check_availability(cls, **config) -> tuple[bool, str]:
        """Check if Kafka is available"""
        # Check if kafka-python is installed
        try:
            from kafka import KafkaProducer
            from kafka.errors import NoBrokersAvailable
        except ImportError:
            return (False,
                    "[ERROR] Kafka support not installed.\n\n"
                    "To use Kafka, install the required dependency:\n"
                    "  pip install crawlit[kafka]\n"
                    "  OR\n"
                    "  pip install kafka-python\n")
        
        # Check if we can connect
        bootstrap_servers = config.get('bootstrap_servers', ['localhost:9092'])
        
        try:
            # Try to create a producer (will fail if Kafka not available)
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=3000,
                api_version_auto_timeout_ms=3000
            )
            producer.close()
            
            servers_str = ', '.join(bootstrap_servers)
            return (True, f"[OK] Kafka is available at {servers_str}")
        
        except NoBrokersAvailable:
            servers_str = ', '.join(bootstrap_servers)
            return (False,
                    f"[ERROR] Cannot connect to Kafka at {servers_str}\n\n"
                    "Kafka server is not running or not accessible.\n\n"
                    "Setup instructions:\n"
                    "1. Install Kafka:\n"
                    "   Download from: https://kafka.apache.org/downloads\n\n"
                    "2. Start Zookeeper:\n"
                    "   bin/zookeeper-server-start.sh config/zookeeper.properties\n\n"
                    "3. Start Kafka:\n"
                    "   bin/kafka-server-start.sh config/server.properties\n\n"
                    "Alternative: Use Docker:\n"
                    "   docker run -d -p 9092:9092 \\\n"
                    "     -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \\\n"
                    "     confluentinc/cp-kafka\n")
        
        except Exception as e:
            return (False, f"[ERROR] Unexpected error checking Kafka: {e}\n")
    
    def connect(self):
        """Establish connection to Kafka"""
        if self.producer is None:
            self.producer = self.kafka_producer_class(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                **self.kwargs
            )
            logger.info(f"Connected to Kafka: {self.bootstrap_servers}")
        
        if self.admin_client is None:
            self.admin_client = self.kafka_admin_class(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"{self.client_id}_admin"
            )
    
    def disconnect(self):
        """Close connection to Kafka"""
        if self.producer:
            self.producer.close()
            self.producer = None
        
        if self.consumer:
            self.consumer.close()
            self.consumer = None
        
        if self.admin_client:
            self.admin_client.close()
            self.admin_client = None
        
        logger.info("Kafka connection closed")
    
    def create_queue(self, queue_name: str, num_partitions: int = 3,
                    replication_factor: int = 1, **kwargs):
        """
        Create a topic (queue) in Kafka.
        
        Args:
            queue_name: Name of the topic
            num_partitions: Number of partitions
            replication_factor: Replication factor
            **kwargs: Additional topic configuration
        """
        self.connect()
        
        topic = self.new_topic_class(
            name=queue_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            topic_configs=kwargs
        )
        
        try:
            self.admin_client.create_topics([topic])
            logger.debug(f"Topic '{queue_name}' created")
        except Exception as e:
            # Topic might already exist
            logger.debug(f"Topic '{queue_name}' already exists or error: {e}")
    
    def delete_queue(self, queue_name: str):
        """Delete a topic from Kafka"""
        self.connect()
        self.admin_client.delete_topics([queue_name])
        logger.info(f"Topic '{queue_name}' deleted")
    
    def publish(self, queue_name: str, message: Dict[str, Any], priority: int = 0):
        """
        Publish a message to Kafka topic.
        
        Note: Kafka doesn't support priorities natively. Priority is stored in message.
        """
        self.connect()
        
        # Add priority to message
        message_with_priority = {
            '_priority': priority,
            **message
        }
        
        # Send message
        future = self.producer.send(queue_name, message_with_priority)
        future.get(timeout=10)  # Wait for send to complete
        
        logger.debug(f"Published message to topic '{queue_name}'")
    
    def consume(self, queue_name: str, callback: Callable[[Dict[str, Any]], bool],
                max_messages: Optional[int] = None, timeout: Optional[int] = None):
        """Consume messages from Kafka topic"""
        # Create consumer if not exists
        if self.consumer is None:
            self.consumer = self.kafka_consumer_class(
                queue_name,
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                enable_auto_commit=False,
                **self.kwargs
            )
        
        messages_processed = 0
        start_time = time.time()
        
        logger.info(f"Starting to consume from topic '{queue_name}'")
        
        try:
            for message in self.consumer:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    break
                
                # Check max messages
                if max_messages and messages_processed >= max_messages:
                    break
                
                try:
                    # Extract message value
                    msg_value = message.value
                    
                    # Remove internal priority field
                    if '_priority' in msg_value:
                        del msg_value['_priority']
                    
                    # Call user callback
                    success = callback(msg_value)
                    
                    # Commit offset if successful
                    if success:
                        self.consumer.commit()
                        messages_processed += 1
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        finally:
            if self.consumer:
                self.consumer.close()
                self.consumer = None
    
    def get_queue_size(self, queue_name: str) -> int:
        """
        Get the approximate number of messages in a topic.
        
        Note: This is an approximation based on partition offsets.
        """
        self.connect()
        
        # Create temporary consumer
        consumer = self.kafka_consumer_class(
            queue_name,
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{self.group_id}_temp"
        )
        
        # Get end offsets and current offsets
        partitions = consumer.partitions_for_topic(queue_name)
        if not partitions:
            consumer.close()
            return 0
        
        topic_partitions = [
            self.kafka_consumer_class.TopicPartition(queue_name, p)
            for p in partitions
        ]
        
        end_offsets = consumer.end_offsets(topic_partitions)
        beginning_offsets = consumer.beginning_offsets(topic_partitions)
        
        total = sum(end_offsets.values()) - sum(beginning_offsets.values())
        
        consumer.close()
        return int(total)
    
    def purge_queue(self, queue_name: str):
        """
        Purge a topic (delete and recreate).
        
        Note: Kafka doesn't support direct purging, so we delete and recreate.
        """
        try:
            self.delete_queue(queue_name)
            time.sleep(1)  # Wait for deletion to propagate
            self.create_queue(queue_name)
            logger.info(f"Purged topic '{queue_name}'")
        except Exception as e:
            logger.error(f"Error purging topic: {e}")


def get_message_queue(backend_type: str, check_setup: bool = True, **config) -> MessageQueue:
    """
    Factory function to get appropriate message queue backend.
    
    Args:
        backend_type: Type of backend ('rabbitmq', 'kafka')
        check_setup: Whether to check if message queue is properly set up
        **config: Configuration parameters for the backend
        
    Returns:
        MessageQueue instance
        
    Raises:
        ValueError: If backend type is unknown
        RuntimeError: If message queue is not available (when check_setup=True)
        
    Example:
        >>> mq = get_message_queue('rabbitmq', host='localhost')
        >>> mq = get_message_queue('kafka', bootstrap_servers=['localhost:9092'])
    """
    backends = {
        'rabbitmq': RabbitMQBackend,
        'rabbit': RabbitMQBackend,  # Alias
        'kafka': KafkaBackend,
    }
    
    backend_class = backends.get(backend_type.lower())
    if not backend_class:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Supported: {', '.join(set(backends.keys()))}"
        )
    
    # Check if message queue is available
    if check_setup:
        is_available, message = backend_class.check_availability(**config)
        
        if not is_available:
            logger.error(message)
            raise RuntimeError(
                f"Message queue backend '{backend_type}' is not available or not properly set up.\n\n"
                f"{message}"
            )
        else:
            logger.info(message)
    
    return backend_class(**config)

