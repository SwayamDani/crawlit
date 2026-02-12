#!/usr/bin/env python3
"""
priority_queue.py - Priority queue implementation for intelligent URL ordering

Provides priority-based URL queuing for more efficient crawling strategies.
"""

import logging
import threading
import asyncio
from typing import Tuple, Optional, Dict, Any, Callable
from queue import PriorityQueue as ThreadSafePriorityQueue, Empty
from dataclasses import dataclass, field
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)


@dataclass(order=True)
class PrioritizedURL:
    """
    A URL with priority information for queue ordering.
    
    Lower priority values are processed first.
    """
    priority: float
    url: str = field(compare=False)
    depth: int = field(compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)
    
    def to_tuple(self) -> Tuple[str, int]:
        """Convert to simple (url, depth) tuple for compatibility."""
        return (self.url, self.depth)


class PriorityStrategy:
    """Base class for priority calculation strategies."""
    
    def calculate_priority(self, url: str, depth: int, metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate priority for a URL.
        
        Args:
            url: The URL to prioritize
            depth: Current crawl depth
            metadata: Optional metadata about the URL
            
        Returns:
            Priority value (lower = higher priority)
        """
        raise NotImplementedError


class BreadthFirstStrategy(PriorityStrategy):
    """Prioritize URLs by depth (breadth-first search)."""
    
    def calculate_priority(self, url: str, depth: int, metadata: Optional[Dict[str, Any]] = None) -> float:
        """Lower depth = higher priority."""
        return float(depth)


class DepthFirstStrategy(PriorityStrategy):
    """Prioritize URLs by negative depth (depth-first search)."""
    
    def calculate_priority(self, url: str, depth: int, metadata: Optional[Dict[str, Any]] = None) -> float:
        """Higher depth = higher priority."""
        return -float(depth)


class SitemapPriorityStrategy(PriorityStrategy):
    """Prioritize URLs based on sitemap priority values."""
    
    def calculate_priority(self, url: str, depth: int, metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        Use sitemap priority if available, otherwise fall back to depth.
        
        Sitemap priorities range from 0.0 (lowest) to 1.0 (highest).
        We invert them so higher sitemap priority = lower queue priority.
        """
        if metadata and 'sitemap_priority' in metadata:
            sitemap_priority = metadata['sitemap_priority']
            # Invert: 1.0 becomes 0.0, 0.0 becomes 1.0
            return 1.0 - sitemap_priority
        # Fallback to depth-based priority
        return float(depth)


class URLPatternStrategy(PriorityStrategy):
    """Prioritize URLs based on pattern matching."""
    
    def __init__(self, high_priority_patterns: list = None, low_priority_patterns: list = None):
        """
        Initialize with URL patterns.
        
        Args:
            high_priority_patterns: List of regex patterns for high-priority URLs
            low_priority_patterns: List of regex patterns for low-priority URLs
        """
        self.high_priority_patterns = [re.compile(p) for p in (high_priority_patterns or [])]
        self.low_priority_patterns = [re.compile(p) for p in (low_priority_patterns or [])]
    
    def calculate_priority(self, url: str, depth: int, metadata: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate priority based on URL patterns.
        
        High-priority patterns get lower values, low-priority patterns get higher values.
        """
        # Check high-priority patterns
        for pattern in self.high_priority_patterns:
            if pattern.search(url):
                return float(depth) * 0.5  # Boost priority
        
        # Check low-priority patterns
        for pattern in self.low_priority_patterns:
            if pattern.search(url):
                return float(depth) * 2.0  # Reduce priority
        
        # Default: use depth
        return float(depth)


class CompositeStrategy(PriorityStrategy):
    """Combine multiple strategies with weights."""
    
    def __init__(self, strategies: list[Tuple[PriorityStrategy, float]]):
        """
        Initialize with weighted strategies.
        
        Args:
            strategies: List of (strategy, weight) tuples
        """
        self.strategies = strategies
        total_weight = sum(weight for _, weight in strategies)
        # Normalize weights
        self.strategies = [(strategy, weight / total_weight) for strategy, weight in strategies]
    
    def calculate_priority(self, url: str, depth: int, metadata: Optional[Dict[str, Any]] = None) -> float:
        """Calculate weighted average of all strategy priorities."""
        total = 0.0
        for strategy, weight in self.strategies:
            priority = strategy.calculate_priority(url, depth, metadata)
            total += priority * weight
        return total


class URLPriorityQueue:
    """
    Thread-safe priority queue for URLs.
    
    Supports different prioritization strategies for intelligent crawling.
    """
    
    def __init__(
        self,
        strategy: Optional[PriorityStrategy] = None,
        maxsize: int = 0
    ):
        """
        Initialize the priority queue.
        
        Args:
            strategy: Priority calculation strategy (default: BreadthFirstStrategy)
            maxsize: Maximum queue size (0 = unlimited)
        """
        self.strategy = strategy or BreadthFirstStrategy()
        self._queue = ThreadSafePriorityQueue(maxsize=maxsize)
        self._lock = threading.Lock()
        self._counter = 0  # For FIFO ordering when priorities are equal
        
        logger.debug(f"Priority queue initialized with {self.strategy.__class__.__name__}")
    
    def put(
        self,
        url: str,
        depth: int,
        metadata: Optional[Dict[str, Any]] = None,
        block: bool = True,
        timeout: Optional[float] = None
    ) -> None:
        """
        Add a URL to the priority queue.
        
        Args:
            url: URL to add
            depth: Crawl depth
            metadata: Optional metadata for priority calculation
            block: Whether to block if queue is full
            timeout: Timeout for blocking put
        """
        priority = self.strategy.calculate_priority(url, depth, metadata)
        
        # Use counter for FIFO ordering when priorities are equal
        with self._lock:
            counter = self._counter
            self._counter += 1
        
        # Create prioritized item: (priority, counter, (url, depth, metadata))
        item = (priority, counter, (url, depth, metadata or {}))
        self._queue.put(item, block=block, timeout=timeout)
        
        logger.debug(f"Added to queue: {url} (priority={priority:.3f}, depth={depth})")
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Tuple[str, int]:
        """
        Get the highest-priority URL from the queue.
        
        Args:
            block: Whether to block if queue is empty
            timeout: Timeout for blocking get
            
        Returns:
            Tuple of (url, depth)
        """
        try:
            priority, counter, (url, depth, metadata) = self._queue.get(block=block, timeout=timeout)
            logger.debug(f"Retrieved from queue: {url} (priority={priority:.3f}, depth={depth})")
            return url, depth
        except Empty:
            raise
    
    def get_with_metadata(self, block: bool = True, timeout: Optional[float] = None) -> Tuple[str, int, Dict[str, Any]]:
        """
        Get the highest-priority URL with metadata from the queue.
        
        Args:
            block: Whether to block if queue is empty
            timeout: Timeout for blocking get
            
        Returns:
            Tuple of (url, depth, metadata)
        """
        try:
            priority, counter, (url, depth, metadata) = self._queue.get(block=block, timeout=timeout)
            logger.debug(f"Retrieved from queue: {url} (priority={priority:.3f}, depth={depth})")
            return url, depth, metadata
        except Empty:
            raise
    
    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()
    
    def qsize(self) -> int:
        """Get the approximate queue size."""
        return self._queue.qsize()
    
    def full(self) -> bool:
        """Check if the queue is full."""
        return self._queue.full()


class AsyncURLPriorityQueue:
    """
    Asyncio-compatible priority queue for URLs.
    
    Supports different prioritization strategies for intelligent crawling.
    """
    
    def __init__(
        self,
        strategy: Optional[PriorityStrategy] = None,
        maxsize: int = 0
    ):
        """
        Initialize the async priority queue.
        
        Args:
            strategy: Priority calculation strategy (default: BreadthFirstStrategy)
            maxsize: Maximum queue size (0 = unlimited)
        """
        self.strategy = strategy or BreadthFirstStrategy()
        self._queue = asyncio.PriorityQueue(maxsize=maxsize)
        self._counter = 0  # For FIFO ordering when priorities are equal
        self._lock = asyncio.Lock()
        
        logger.debug(f"Async priority queue initialized with {self.strategy.__class__.__name__}")
    
    async def put(
        self,
        url: str,
        depth: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a URL to the priority queue.
        
        Args:
            url: URL to add
            depth: Crawl depth
            metadata: Optional metadata for priority calculation
        """
        priority = self.strategy.calculate_priority(url, depth, metadata)
        
        # Use counter for FIFO ordering when priorities are equal
        async with self._lock:
            counter = self._counter
            self._counter += 1
        
        # Create prioritized item: (priority, counter, (url, depth, metadata))
        item = (priority, counter, (url, depth, metadata or {}))
        await self._queue.put(item)
        
        logger.debug(f"Added to async queue: {url} (priority={priority:.3f}, depth={depth})")
    
    async def get(self) -> Tuple[str, int]:
        """
        Get the highest-priority URL from the queue.
        
        Returns:
            Tuple of (url, depth)
        """
        priority, counter, (url, depth, metadata) = await self._queue.get()
        logger.debug(f"Retrieved from async queue: {url} (priority={priority:.3f}, depth={depth})")
        return url, depth
    
    async def get_with_metadata(self) -> Tuple[str, int, Dict[str, Any]]:
        """
        Get the highest-priority URL with metadata from the queue.
        
        Returns:
            Tuple of (url, depth, metadata)
        """
        priority, counter, (url, depth, metadata) = await self._queue.get()
        logger.debug(f"Retrieved from async queue: {url} (priority={priority:.3f}, depth={depth})")
        return url, depth, metadata
    
    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()
    
    def qsize(self) -> int:
        """Get the approximate queue size."""
        return self._queue.qsize()
    
    def full(self) -> bool:
        """Check if the queue is full."""
        return self._queue.full()
    
    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete."""
        self._queue.task_done()
    
    async def join(self) -> None:
        """Block until all items in the queue have been received and processed."""
        await self._queue.join()


def get_strategy(strategy_name: str, **kwargs) -> PriorityStrategy:
    """
    Factory function to get a priority strategy by name.
    
    Args:
        strategy_name: Name of the strategy
        **kwargs: Additional arguments for the strategy
        
    Returns:
        PriorityStrategy instance
    """
    strategies = {
        'breadth-first': BreadthFirstStrategy,
        'depth-first': DepthFirstStrategy,
        'sitemap-priority': SitemapPriorityStrategy,
        'url-pattern': URLPatternStrategy,
    }
    
    if strategy_name not in strategies:
        logger.warning(f"Unknown strategy '{strategy_name}', using breadth-first")
        return BreadthFirstStrategy()
    
    strategy_class = strategies[strategy_name]
    try:
        return strategy_class(**kwargs)
    except TypeError:
        # Strategy doesn't accept kwargs
        return strategy_class()

