#!/usr/bin/env python3
"""
coordinator.py - Distributed crawling coordination

Manages distributed crawl operations across multiple workers using message queues.
"""

import logging
import time
import hashlib
import threading
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urlparse
from datetime import datetime

from .message_queue import MessageQueue, get_message_queue

logger = logging.getLogger(__name__)


class CrawlTask:
    """Represents a crawl task"""
    
    def __init__(self, url: str, depth: int = 0, metadata: Optional[Dict[str, Any]] = None):
        self.url = url
        self.depth = depth
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.task_id = self._generate_task_id()
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        data = f"{self.url}:{self.depth}:{self.created_at}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'url': self.url,
            'depth': self.depth,
            'metadata': self.metadata,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrawlTask':
        """Create from dictionary"""
        task = cls(
            url=data['url'],
            depth=data['depth'],
            metadata=data.get('metadata', {})
        )
        task.task_id = data.get('task_id', task.task_id)
        task.created_at = data.get('created_at', task.created_at)
        return task


class CrawlCoordinator:
    """
    Coordinates distributed crawling across multiple workers.
    
    Features:
    - URL deduplication across workers
    - Task distribution via message queue
    - Progress tracking
    - Worker management
    """
    
    def __init__(self, message_queue: MessageQueue,
                 task_queue: str = "crawl_tasks",
                 result_queue: str = "crawl_results",
                 max_depth: int = 3,
                 internal_only: bool = True,
                 start_url: Optional[str] = None):
        """
        Initialize coordinator.
        
        Args:
            message_queue: Message queue instance
            task_queue: Name of task queue
            result_queue: Name of result queue
            max_depth: Maximum crawl depth
            internal_only: Restrict to same domain
            start_url: Starting URL
        """
        self.mq = message_queue
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.max_depth = max_depth
        self.internal_only = internal_only
        self.start_url = start_url
        
        # State tracking
        self.visited_urls: Set[str] = set()
        self.in_progress_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.results: Dict[str, Any] = {}
        
        # Statistics
        self.stats = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'urls_visited': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Create queues
        self.mq.create_queue(task_queue)
        self.mq.create_queue(result_queue)
        
        logger.info(f"Coordinator initialized (task_queue={task_queue}, result_queue={result_queue})")
    
    def add_task(self, url: str, depth: int = 0, priority: int = 0, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a crawl task to the queue.
        
        Args:
            url: URL to crawl
            depth: Current depth
            priority: Task priority (higher = more important)
            metadata: Additional metadata
        """
        with self._lock:
            # Check if already visited or in progress
            if url in self.visited_urls or url in self.in_progress_urls:
                logger.debug(f"URL already processed or in progress: {url}")
                return
            
            # Check depth limit
            if depth > self.max_depth:
                logger.debug(f"URL exceeds max depth: {url} (depth={depth})")
                return
            
            # Check domain restriction
            if self.internal_only and self.start_url:
                start_domain = urlparse(self.start_url).netloc
                url_domain = urlparse(url).netloc
                if start_domain != url_domain:
                    logger.debug(f"URL outside domain: {url}")
                    return
            
            # Create task
            task = CrawlTask(url=url, depth=depth, metadata=metadata)
            
            # Publish to queue
            self.mq.publish(self.task_queue, task.to_dict(), priority=priority)
            
            # Mark as in progress
            self.in_progress_urls.add(url)
            
            # Update stats
            self.stats['tasks_created'] += 1
            
            logger.debug(f"Task created: {url} (depth={depth}, priority={priority})")
    
    def process_result(self, result: Dict[str, Any]) -> bool:
        """
        Process a result from a worker.
        
        Args:
            result: Result dictionary from worker
            
        Returns:
            bool: True if processed successfully
        """
        try:
            url = result.get('url')
            success = result.get('success', False)
            depth = result.get('depth', 0)
            links = result.get('links', [])
            
            with self._lock:
                # Move from in-progress to visited
                if url in self.in_progress_urls:
                    self.in_progress_urls.remove(url)
                self.visited_urls.add(url)
                
                # Store result
                self.results[url] = result
                
                # Update stats
                if success:
                    self.stats['tasks_completed'] += 1
                    self.stats['urls_visited'] += 1
                else:
                    self.stats['tasks_failed'] += 1
                    self.failed_urls.add(url)
            
            # Add new tasks for discovered links (outside the lock to avoid deadlock)
            if success and depth < self.max_depth:
                for link in links:
                    self.add_task(link, depth=depth + 1, priority=max(0, 10 - depth))
            
            logger.debug(f"Result processed: {url} (success={success}, links={len(links)})")
            return True
            
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            return False
    
    def start_crawl(self, start_url: str, max_tasks: Optional[int] = None):
        """
        Start a distributed crawl.
        
        Args:
            start_url: Starting URL
            max_tasks: Maximum number of tasks to create (None = unlimited)
        """
        self.start_url = start_url
        self.stats['start_time'] = time.time()
        
        logger.info(f"Starting distributed crawl from: {start_url}")
        
        # Add initial task
        self.add_task(start_url, depth=0, priority=10)
        
        # Monitor progress
        logger.info(f"Initial task added to queue. Workers should start processing.")
        logger.info(f"Use get_stats() to monitor progress.")
    
    def listen_for_results(self, timeout: Optional[int] = None, max_results: Optional[int] = None):
        """
        Listen for results from workers.
        
        Args:
            timeout: Timeout in seconds (None = no timeout)
            max_results: Maximum number of results to process
        """
        logger.info("Listening for results from workers...")
        
        def result_callback(message: Dict[str, Any]) -> bool:
            return self.process_result(message)
        
        self.mq.consume(
            self.result_queue,
            callback=result_callback,
            max_messages=max_results,
            timeout=timeout
        )
        
        self.stats['end_time'] = time.time()
        logger.info("Finished listening for results")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current crawl statistics"""
        with self._lock:
            stats = self.stats.copy()
            stats['urls_in_queue'] = self.mq.get_queue_size(self.task_queue)
            stats['urls_in_progress'] = len(self.in_progress_urls)
            stats['urls_visited'] = len(self.visited_urls)
            stats['urls_failed'] = len(self.failed_urls)
            
            if stats['start_time'] and stats['end_time']:
                stats['duration'] = stats['end_time'] - stats['start_time']
            elif stats['start_time']:
                stats['duration'] = time.time() - stats['start_time']
            
            return stats
    
    def get_results(self) -> Dict[str, Any]:
        """Get all crawl results"""
        with self._lock:
            return self.results.copy()
    
    def wait_for_completion(self, check_interval: int = 5, max_wait: Optional[int] = None):
        """
        Wait for all tasks to complete.
        
        Args:
            check_interval: How often to check (seconds)
            max_wait: Maximum time to wait (seconds)
        """
        start_wait = time.time()
        
        logger.info("Waiting for all tasks to complete...")
        
        while True:
            stats = self.get_stats()
            
            # Check if done
            if stats['urls_in_queue'] == 0 and stats['urls_in_progress'] == 0:
                logger.info("All tasks completed!")
                break
            
            # Check timeout
            if max_wait and (time.time() - start_wait) > max_wait:
                logger.warning(f"Wait timeout reached ({max_wait}s)")
                break
            
            # Log progress
            logger.info(f"In progress: queue={stats['urls_in_queue']}, "
                       f"processing={stats['urls_in_progress']}, "
                       f"visited={stats['urls_visited']}")
            
            time.sleep(check_interval)
    
    def shutdown(self):
        """Shutdown coordinator"""
        logger.info("Shutting down coordinator...")
        self.stats['end_time'] = time.time()
        logger.info(f"Final stats: {self.get_stats()}")


class CrawlWorker:
    """
    Worker that processes crawl tasks from a message queue.
    
    Features:
    - Pulls tasks from queue
    - Performs actual crawling
    - Publishes results back to queue
    """
    
    def __init__(self, message_queue: MessageQueue,
                 task_queue: str = "crawl_tasks",
                 result_queue: str = "crawl_results",
                 worker_id: Optional[str] = None,
                 crawler_config: Optional[Dict[str, Any]] = None):
        """
        Initialize worker.
        
        Args:
            message_queue: Message queue instance
            task_queue: Name of task queue
            result_queue: Name of result queue
            worker_id: Unique worker identifier
            crawler_config: Configuration for crawler
        """
        self.mq = message_queue
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.worker_id = worker_id or f"worker_{id(self)}"
        self.crawler_config = crawler_config or {}
        
        # Statistics
        self.stats = {
            'tasks_processed': 0,
            'tasks_succeeded': 0,
            'tasks_failed': 0,
            'start_time': None,
            'last_task_time': None
        }
        
        self._running = False
        
        logger.info(f"Worker initialized: {self.worker_id}")
    
    def _crawl_url(self, task: CrawlTask) -> Dict[str, Any]:
        """
        Perform actual crawling of a URL.
        
        Args:
            task: Crawl task
            
        Returns:
            Result dictionary
        """
        from ..crawler.fetcher import fetch_page
        from ..crawler.parser import extract_links
        
        logger.info(f"[{self.worker_id}] Crawling: {task.url} (depth={task.depth})")
        
        try:
            # Fetch page
            response = fetch_page(
                task.url,
                user_agent=self.crawler_config.get('user_agent', 'crawlit/1.0 (distributed)'),
                max_retries=self.crawler_config.get('max_retries', 3),
                timeout=self.crawler_config.get('timeout', 10),
                **self.crawler_config
            )
            
            if not response or not response.get('success'):
                return {
                    'task_id': task.task_id,
                    'url': task.url,
                    'depth': task.depth,
                    'success': False,
                    'error': response.get('error', 'Unknown error') if response else 'No response',
                    'worker_id': self.worker_id,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Extract links
            html_content = response.get('html_content', '')
            links = extract_links(html_content, task.url) if html_content else []
            
            # Build result
            result = {
                'task_id': task.task_id,
                'url': task.url,
                'depth': task.depth,
                'success': True,
                'status': response.get('status', 0),
                'title': response.get('title', ''),
                'links': links,
                'worker_id': self.worker_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add optional fields if configured
            if self.crawler_config.get('include_html', False):
                result['html_content'] = html_content
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error crawling {task.url}: {e}")
            return {
                'task_id': task.task_id,
                'url': task.url,
                'depth': task.depth,
                'success': False,
                'error': str(e),
                'worker_id': self.worker_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def process_task(self, task_data: Dict[str, Any]) -> bool:
        """
        Process a single task.
        
        Args:
            task_data: Task data from queue
            
        Returns:
            bool: True if processed successfully
        """
        try:
            # Convert to CrawlTask
            task = CrawlTask.from_dict(task_data)
            
            # Crawl the URL
            result = self._crawl_url(task)
            
            # Publish result
            self.mq.publish(self.result_queue, result)
            
            # Update stats
            self.stats['tasks_processed'] += 1
            if result['success']:
                self.stats['tasks_succeeded'] += 1
            else:
                self.stats['tasks_failed'] += 1
            self.stats['last_task_time'] = time.time()
            
            logger.debug(f"[{self.worker_id}] Task completed: {task.url}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error processing task: {e}")
            self.stats['tasks_failed'] += 1
            return False
    
    def start(self, max_tasks: Optional[int] = None, timeout: Optional[int] = None):
        """
        Start processing tasks.
        
        Args:
            max_tasks: Maximum number of tasks to process
            timeout: Timeout in seconds
        """
        self._running = True
        self.stats['start_time'] = time.time()
        
        logger.info(f"[{self.worker_id}] Starting to process tasks from '{self.task_queue}'")
        
        try:
            self.mq.consume(
                self.task_queue,
                callback=self.process_task,
                max_messages=max_tasks,
                timeout=timeout
            )
        except KeyboardInterrupt:
            logger.info(f"[{self.worker_id}] Interrupted by user")
        finally:
            self._running = False
            logger.info(f"[{self.worker_id}] Stopped. Stats: {self.stats}")
    
    def stop(self):
        """Stop processing tasks"""
        self._running = False
        logger.info(f"[{self.worker_id}] Stopping...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        stats = self.stats.copy()
        if stats['start_time']:
            stats['uptime'] = time.time() - stats['start_time']
        return stats


class DistributedCrawler:
    """
    High-level interface for distributed crawling.
    
    Combines coordinator and worker management.
    """
    
    def __init__(self, message_queue_type: str = "rabbitmq",
                 mq_config: Optional[Dict[str, Any]] = None,
                 coordinator_config: Optional[Dict[str, Any]] = None,
                 worker_config: Optional[Dict[str, Any]] = None):
        """
        Initialize distributed crawler.
        
        Args:
            message_queue_type: Type of message queue ('rabbitmq' or 'kafka')
            mq_config: Message queue configuration
            coordinator_config: Coordinator configuration
            worker_config: Worker configuration
        """
        # Initialize message queue
        mq_config = mq_config or {}
        self.mq = get_message_queue(message_queue_type, **mq_config)
        
        # Initialize coordinator
        coordinator_config = coordinator_config or {}
        self.coordinator = CrawlCoordinator(self.mq, **coordinator_config)
        
        # Store worker config for later
        self.worker_config = worker_config or {}
        
        logger.info("Distributed crawler initialized")
    
    def crawl(self, start_url: str, num_workers: int = 3,
              max_tasks: Optional[int] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform a distributed crawl.
        
        Args:
            start_url: Starting URL
            num_workers: Number of worker processes
            max_tasks: Maximum tasks per worker
            timeout: Timeout per worker
            
        Returns:
            Dictionary of crawl results
        """
        import multiprocessing
        
        logger.info(f"Starting distributed crawl with {num_workers} workers")
        
        # Start coordinator
        self.coordinator.start_crawl(start_url, max_tasks=max_tasks)
        
        # Start workers in separate processes
        processes = []
        for i in range(num_workers):
            worker = CrawlWorker(
                message_queue=self.mq,
                task_queue=self.coordinator.task_queue,
                result_queue=self.coordinator.result_queue,
                worker_id=f"worker_{i}",
                crawler_config=self.worker_config
            )
            
            process = multiprocessing.Process(
                target=worker.start,
                args=(max_tasks, timeout)
            )
            process.start()
            processes.append(process)
            logger.info(f"Started worker_{i} (PID: {process.pid})")
        
        # Wait for workers to finish
        for process in processes:
            process.join()
        
        logger.info("All workers completed")
        
        # Get results
        return self.coordinator.get_results()
    
    def shutdown(self):
        """Shutdown distributed crawler"""
        self.coordinator.shutdown()
        self.mq.disconnect()
        logger.info("Distributed crawler shut down")




