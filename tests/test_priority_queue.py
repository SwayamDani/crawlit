#!/usr/bin/env python3
"""
Tests for priority queue functionality
"""

import pytest
import asyncio
from crawlit.utils.priority_queue import (
    URLPriorityQueue,
    AsyncURLPriorityQueue,
    BreadthFirstStrategy,
    DepthFirstStrategy,
    SitemapPriorityStrategy,
    URLPatternStrategy,
    CompositeStrategy,
    get_strategy
)


class TestPriorityStrategies:
    """Tests for priority calculation strategies."""
    
    def test_breadth_first_strategy(self):
        """Test breadth-first priority calculation."""
        strategy = BreadthFirstStrategy()
        
        # Lower depth = higher priority (lower value)
        priority_depth_0 = strategy.calculate_priority("http://example.com", 0)
        priority_depth_2 = strategy.calculate_priority("http://example.com", 2)
        
        assert priority_depth_0 < priority_depth_2
    
    def test_depth_first_strategy(self):
        """Test depth-first priority calculation."""
        strategy = DepthFirstStrategy()
        
        # Higher depth = higher priority (more negative value)
        priority_depth_0 = strategy.calculate_priority("http://example.com", 0)
        priority_depth_2 = strategy.calculate_priority("http://example.com", 2)
        
        assert priority_depth_0 > priority_depth_2
    
    def test_sitemap_priority_strategy(self):
        """Test sitemap-based priority calculation."""
        strategy = SitemapPriorityStrategy()
        
        # With sitemap priority
        metadata_high = {'sitemap_priority': 0.9}
        metadata_low = {'sitemap_priority': 0.1}
        
        priority_high = strategy.calculate_priority("http://example.com", 1, metadata_high)
        priority_low = strategy.calculate_priority("http://example.com", 1, metadata_low)
        
        # Higher sitemap priority = lower queue priority value
        assert priority_high < priority_low
        
        # Without sitemap priority, falls back to depth
        priority_no_metadata = strategy.calculate_priority("http://example.com", 1)
        assert priority_no_metadata == 1.0
    
    def test_url_pattern_strategy(self):
        """Test URL pattern-based priority calculation."""
        strategy = URLPatternStrategy(
            high_priority_patterns=[r'/important/.*', r'/admin/.*'],
            low_priority_patterns=[r'/archive/.*']
        )
        
        # High priority URL
        priority_important = strategy.calculate_priority("http://example.com/important/page", 2)
        
        # Low priority URL
        priority_archive = strategy.calculate_priority("http://example.com/archive/old", 2)
        
        # Normal URL
        priority_normal = strategy.calculate_priority("http://example.com/normal", 2)
        
        assert priority_important < priority_normal < priority_archive
    
    def test_composite_strategy(self):
        """Test composite strategy with multiple strategies."""
        bfs = BreadthFirstStrategy()
        pattern = URLPatternStrategy(high_priority_patterns=[r'/api/.*'])
        
        strategy = CompositeStrategy([
            (bfs, 0.7),
            (pattern, 0.3)
        ])
        
        priority = strategy.calculate_priority("http://example.com/api/data", 1)
        
        # Should be weighted combination
        assert isinstance(priority, float)
        assert priority > 0


class TestURLPriorityQueue:
    """Tests for synchronous URL priority queue."""
    
    def test_basic_queue_operations(self):
        """Test basic put and get operations."""
        queue = URLPriorityQueue()
        
        queue.put("http://example.com/page1", 1)
        queue.put("http://example.com/page2", 2)
        queue.put("http://example.com/page3", 0)
        
        assert not queue.empty()
        assert queue.qsize() == 3
        
        # Should get lowest depth first (breadth-first default)
        url, depth = queue.get()
        assert url == "http://example.com/page3"
        assert depth == 0
    
    def test_priority_ordering(self):
        """Test that URLs are retrieved in priority order."""
        queue = URLPriorityQueue(strategy=BreadthFirstStrategy())
        
        # Add URLs at different depths
        queue.put("http://example.com/deep", 5)
        queue.put("http://example.com/shallow", 1)
        queue.put("http://example.com/root", 0)
        queue.put("http://example.com/mid", 3)
        
        # Should get in order: 0, 1, 3, 5
        expected_depths = [0, 1, 3, 5]
        for expected_depth in expected_depths:
            url, depth = queue.get()
            assert depth == expected_depth
    
    def test_depth_first_ordering(self):
        """Test depth-first priority ordering."""
        queue = URLPriorityQueue(strategy=DepthFirstStrategy())
        
        queue.put("http://example.com/shallow", 1)
        queue.put("http://example.com/deep", 5)
        queue.put("http://example.com/mid", 3)
        
        # Should get deepest first
        url, depth = queue.get()
        assert depth == 5
        
        url, depth = queue.get()
        assert depth == 3
        
        url, depth = queue.get()
        assert depth == 1
    
    def test_fifo_for_equal_priority(self):
        """Test FIFO ordering when priorities are equal."""
        queue = URLPriorityQueue()
        
        # Add multiple URLs at same depth
        urls = [f"http://example.com/page{i}" for i in range(5)]
        for url in urls:
            queue.put(url, 1)
        
        # Should get in FIFO order
        for expected_url in urls:
            url, depth = queue.get()
            assert url == expected_url
    
    def test_metadata_preservation(self):
        """Test that metadata is preserved through queue."""
        queue = URLPriorityQueue(strategy=SitemapPriorityStrategy())
        
        metadata = {'sitemap_priority': 0.8, 'custom': 'value'}
        queue.put("http://example.com", 1, metadata)
        
        url, depth, retrieved_metadata = queue.get_with_metadata()
        
        assert url == "http://example.com"
        assert depth == 1
        assert retrieved_metadata['sitemap_priority'] == 0.8
        assert retrieved_metadata['custom'] == 'value'
    
    def test_empty_queue(self):
        """Test operations on empty queue."""
        queue = URLPriorityQueue()
        
        assert queue.empty()
        assert queue.qsize() == 0
        
        with pytest.raises(Exception):  # Should raise Empty exception
            queue.get(block=False)
    
    def test_maxsize(self):
        """Test queue with maximum size limit."""
        queue = URLPriorityQueue(maxsize=2)
        
        queue.put("http://example.com/1", 1, block=False)
        queue.put("http://example.com/2", 1, block=False)
        
        assert queue.full()
        
        # Should raise exception when full
        with pytest.raises(Exception):
            queue.put("http://example.com/3", 1, block=False)


@pytest.mark.asyncio
class TestAsyncURLPriorityQueue:
    """Tests for asynchronous URL priority queue."""
    
    async def test_async_basic_operations(self):
        """Test basic async queue operations."""
        queue = AsyncURLPriorityQueue()
        
        await queue.put("http://example.com/page1", 1)
        await queue.put("http://example.com/page2", 2)
        await queue.put("http://example.com/page3", 0)
        
        assert not queue.empty()
        assert queue.qsize() == 3
        
        # Should get lowest depth first
        url, depth = await queue.get()
        assert url == "http://example.com/page3"
        assert depth == 0
    
    async def test_async_priority_ordering(self):
        """Test async priority ordering."""
        queue = AsyncURLPriorityQueue(strategy=DepthFirstStrategy())
        
        await queue.put("http://example.com/shallow", 1)
        await queue.put("http://example.com/deep", 5)
        await queue.put("http://example.com/mid", 3)
        
        # Should get deepest first
        url, depth = await queue.get()
        assert depth == 5
    
    async def test_async_task_done_join(self):
        """Test task_done and join functionality."""
        queue = AsyncURLPriorityQueue()
        
        await queue.put("http://example.com/1", 1)
        await queue.put("http://example.com/2", 2)
        
        async def worker():
            await queue.get()
            queue.task_done()
            await queue.get()
            queue.task_done()
        
        worker_task = asyncio.create_task(worker())
        
        # Wait for all tasks to be processed
        await queue.join()
        await worker_task
        
        assert queue.empty()
    
    async def test_async_metadata(self):
        """Test metadata handling in async queue."""
        queue = AsyncURLPriorityQueue()
        
        metadata = {'source': 'sitemap'}
        await queue.put("http://example.com", 1, metadata)
        
        url, depth, retrieved_metadata = await queue.get_with_metadata()
        
        assert url == "http://example.com"
        assert retrieved_metadata['source'] == 'sitemap'


class TestStrategyFactory:
    """Tests for strategy factory function."""
    
    def test_get_breadth_first_strategy(self):
        """Test getting breadth-first strategy."""
        strategy = get_strategy('breadth-first')
        assert isinstance(strategy, BreadthFirstStrategy)
    
    def test_get_depth_first_strategy(self):
        """Test getting depth-first strategy."""
        strategy = get_strategy('depth-first')
        assert isinstance(strategy, DepthFirstStrategy)
    
    def test_get_sitemap_strategy(self):
        """Test getting sitemap priority strategy."""
        strategy = get_strategy('sitemap-priority')
        assert isinstance(strategy, SitemapPriorityStrategy)
    
    def test_get_url_pattern_strategy(self):
        """Test getting URL pattern strategy with kwargs."""
        strategy = get_strategy(
            'url-pattern',
            high_priority_patterns=[r'/api/.*']
        )
        assert isinstance(strategy, URLPatternStrategy)
    
    def test_unknown_strategy(self):
        """Test handling of unknown strategy name."""
        strategy = get_strategy('nonexistent-strategy')
        # Should fall back to BreadthFirstStrategy
        assert isinstance(strategy, BreadthFirstStrategy)


class TestPriorityQueueEdgeCases:
    """Edge case tests for priority queue."""
    
    def test_large_queue(self):
        """Test queue with many items."""
        queue = URLPriorityQueue()
        
        # Add 1000 URLs
        for i in range(1000):
            queue.put(f"http://example.com/page{i}", i % 10)
        
        assert queue.qsize() == 1000
        
        # Verify they come out in priority order
        prev_depth = -1
        for _ in range(1000):
            url, depth = queue.get()
            assert depth >= prev_depth
            prev_depth = depth
    
    def test_duplicate_urls(self):
        """Test handling of duplicate URLs."""
        queue = URLPriorityQueue()
        
        # Add same URL multiple times
        queue.put("http://example.com/page", 1)
        queue.put("http://example.com/page", 2)
        queue.put("http://example.com/page", 3)
        
        # All should be in queue (deduplication is crawler's job)
        assert queue.qsize() == 3
    
    def test_very_deep_urls(self):
        """Test with very deep URLs."""
        queue = URLPriorityQueue()
        
        queue.put("http://example.com/very/deep/url", 100)
        queue.put("http://example.com/shallow", 1)
        
        # Shallow should come first
        url, depth = queue.get()
        assert depth == 1

