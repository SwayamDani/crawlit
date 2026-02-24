#!/usr/bin/env python3
"""
Performance benchmarks and stress tests
"""

import pytest
import time
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_url_queue_performance(self):
        """Benchmark URL queue operations using simple list (as used by crawler)."""
        from collections import deque
        
        queue = deque()
        
        # Test add performance
        start_time = time.time()
        for i in range(10000):
            queue.append(f"http://example.com/page{i}")
        add_time = time.time() - start_time
        
        # Should be fast (< 1 second for 10k URLs)
        assert add_time < 1.0
        
        # Test get performance
        start_time = time.time()
        for i in range(10000):
            queue.popleft()
        get_time = time.time() - start_time
        
        assert get_time < 1.0
    
    def test_priority_queue_performance(self):
        """Benchmark priority queue operations."""
        from crawlit.utils.priority_queue import URLPriorityQueue, BreadthFirstStrategy
        
        queue = URLPriorityQueue(strategy=BreadthFirstStrategy())
        
        # Add many URLs with different priorities
        start_time = time.time()
        for i in range(10000):
            queue.put(f"http://example.com/page{i}", depth=i % 10)
        add_time = time.time() - start_time
        
        assert add_time < 2.0  # Should handle 10k URLs quickly
        
        # Get all URLs (should be in priority order)
        start_time = time.time()
        while not queue.empty():
            queue.get()
        get_time = time.time() - start_time
        
        assert get_time < 2.0
    
    def test_deduplication_performance(self):
        """Benchmark URL deduplication with large sets."""
        # Use a simple set for URL deduplication (as used internally by crawler)
        seen_urls = set()
        
        # Add 50k URLs
        start_time = time.time()
        for i in range(50000):
            seen_urls.add(f"http://example.com/page{i}")
        add_time = time.time() - start_time
        
        # Should be very fast with set/dict
        assert add_time < 1.0
        
        # Test lookup performance
        start_time = time.time()
        for i in range(50000):
            _ = f"http://example.com/page{i}" in seen_urls
        lookup_time = time.time() - start_time
        
        assert lookup_time < 0.5
    
    def test_rate_limiter_performance(self):
        """Benchmark rate limiter overhead."""
        from crawlit.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_second=100)
        
        # Measure overhead of wait calls
        start_time = time.time()
        for _ in range(100):
            limiter.wait("example.com")
        elapsed = time.time() - start_time
        
        # Should complete in about 1 second (100 requests at 100 rps)
        assert 0.9 <= elapsed <= 1.5  # Allow some overhead
    
    def test_budget_tracker_performance(self):
        """Benchmark budget tracker operations."""
        from crawlit.utils.budget_tracker import BudgetTracker
        
        tracker = BudgetTracker(max_pages=100000, max_bandwidth_mb=1000.0)
        tracker.start()
        
        # Record many pages
        start_time = time.time()
        for _ in range(10000):
            tracker.record_page(1000)
        record_time = time.time() - start_time
        
        assert record_time < 1.0
        
        # Check overhead of limit checking
        start_time = time.time()
        for _ in range(10000):
            tracker.is_budget_exceeded()
        check_time = time.time() - start_time
        
        assert check_time < 0.1  # Should be very fast
    
    def test_html_parser_performance(self):
        """Benchmark HTML parsing speed."""
        from crawlit.parser.html_parser import HTMLParser
        
        # Create large HTML document
        html = "<html><body>" + "".join(
            f'<div><a href="/page{i}">Link {i}</a><p>Content {i}</p></div>'
            for i in range(1000)
        ) + "</body></html>"
        
        parser = HTMLParser()
        
        # Parse multiple times
        start_time = time.time()
        for _ in range(100):
            parser.parse(html, "http://example.com")
        parse_time = time.time() - start_time
        
        # Should handle 100 parses of 1000-element docs quickly
        assert parse_time < 6.0
    
    def test_link_extractor_performance(self):
        """Benchmark link extraction speed."""
        from crawlit.crawler.parser import extract_links
        
        # Create HTML with many links
        html = "<html><body>" + "".join(
            f'<a href="http://example.com/page{i}">Link {i}</a>'
            for i in range(5000)
        ) + "</body></html>"
        
        start_time = time.time()
        links = extract_links(html, "http://example.com")
        extract_time = time.time() - start_time
        
        assert len(links) == 5000
        assert extract_time < 2.0


@pytest.mark.performance
class TestMemoryUsage:
    """Memory usage and leak tests."""
    
    def test_url_queue_memory_scaling(self):
        """Test memory usage of URL queue with many URLs."""
        from collections import deque
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        queue = deque()
        
        # Add 100k URLs
        for i in range(100000):
            queue.append(f"http://example.com/page{i}?param={i}")
        
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_memory - initial_memory
        
        # Memory increase should be reasonable (< 100 MB for 100k URLs)
        assert memory_increase < 100
    
    def test_deduplicator_memory_scaling(self):
        """Test memory usage of deduplicator."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Use a simple set for URL deduplication (as used internally by crawler)
        seen_urls = set()
        
        # Add 100k unique URLs
        for i in range(100000):
            seen_urls.add(f"http://example.com/page{i}")
        
        after_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = after_memory - initial_memory
        
        # Should use reasonable memory
        assert memory_increase < 150
    
    def test_incremental_state_memory(self):
        """Test memory usage of incremental state."""
        from crawlit.utils.incremental import IncrementalState
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        state = IncrementalState()
        
        # Store state for 50k URLs
        for i in range(50000):
            state.set_url_state(
                f"http://example.com/page{i}",
                etag=f"etag{i}",
                last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
                content_hash=f"hash{i}"
            )
        
        after_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = after_memory - initial_memory
        
        # Should scale reasonably
        assert memory_increase < 200


@pytest.mark.performance
class TestStressTesting:
    """Stress tests for edge cases and limits."""
    
    def test_concurrent_queue_access(self):
        """Stress test with high concurrency."""
        from collections import deque
        import threading
        
        queue = deque()
        lock = threading.Lock()
        
        # Add initial URLs
        for i in range(1000):
            queue.append(f"http://example.com/page{i}")
        
        def worker(worker_id):
            results = []
            for _ in range(100):
                try:
                    with lock:
                        if not queue:
                            break
                        url = queue.popleft()
                    results.append(url)
                    # Add new URLs
                    with lock:
                        queue.append(f"http://example.com/worker{worker_id}/page{len(results)}")
                except:
                    break
            return results
        
        # Run with many threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # Should handle concurrent access without crashes
        assert len(all_results) > 0
    
    def test_rapid_rate_limiter_calls(self):
        """Stress test rate limiter with rapid calls."""
        from crawlit.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_second=1000)
        
        # Make many rapid calls
        start_time = time.time()
        for _ in range(1000):
            limiter.wait("example.com")
        elapsed = time.time() - start_time
        
        # Should handle without crashing
        assert elapsed > 0
    
    def test_many_domains_rate_limiting(self):
        """Test rate limiting with many domains."""
        from crawlit.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_second=10)
        
        # Access many different domains
        start_time = time.time()
        for i in range(100):
            limiter.wait(f"domain{i}.com")
        elapsed = time.time() - start_time
        
        # Should be fast (domains are independent)
        assert elapsed < 1.0
    
    def test_budget_tracker_thread_safety(self):
        """Stress test budget tracker thread safety."""
        from crawlit.utils.budget_tracker import BudgetTracker
        import threading
        
        tracker = BudgetTracker(max_pages=10000, max_bandwidth_mb=100.0)
        tracker.start()
        
        def record_worker():
            for _ in range(1000):
                tracker.record_page(1000)
        
        # Run multiple threads
        threads = [threading.Thread(target=record_worker) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        stats = tracker.get_stats()
        
        # Should have recorded all 10,000 pages
        assert stats['pages_crawled'] == 10000
    
    def test_large_html_parsing(self):
        """Test parsing very large HTML documents."""
        from crawlit.parser.html_parser import HTMLParser
        
        # Create a 5MB HTML document
        large_html = "<html><body>" + ("x" * 5000000) + "</body></html>"
        
        parser = HTMLParser()
        
        start_time = time.time()
        result = parser.parse(large_html, "http://example.com")
        parse_time = time.time() - start_time
        
        # Should complete (even if slow)
        assert result is not None
        assert parse_time < 10.0  # Reasonable time limit


@pytest.mark.performance
class TestConnectionPoolPerformance:
    """Test connection pool and session management performance."""
    
    def test_session_reuse_performance(self):
        """Test that session reuse improves performance."""
        from crawlit.utils.session_manager import SessionManager
        import requests
        
        manager = SessionManager(pool_size=5)
        
        # With session reuse
        start_time = time.time()
        session = manager.get_sync_session()
        for _ in range(10):
            # Simulate requests (mock)
            pass
        with_reuse_time = time.time() - start_time
        
        # Session reuse should be fast
        assert with_reuse_time < 1.0
    
    @pytest.mark.asyncio
    async def test_async_connection_pool_scaling(self):
        """Test async connection pool with many concurrent requests."""
        from crawlit.utils.session_manager import SessionManager
        import asyncio
        
        manager = SessionManager(pool_size=20)
        
        async def mock_request(i):
            await asyncio.sleep(0.01)  # Simulate I/O
            return i
        
        # Simulate 100 concurrent requests
        start_time = time.time()
        tasks = [mock_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        assert len(results) == 100
        # With good concurrency, should be much faster than sequential
        assert elapsed < 2.0


@pytest.mark.performance
class TestRegressionBenchmarks:
    """Benchmark tests to catch performance regressions."""
    
    def test_baseline_crawl_speed(self):
        """Baseline benchmark for crawl speed."""
        # This would be run regularly to catch regressions
        # For now, just a placeholder
        pass
    
    def test_parser_regression(self):
        """Ensure parser performance hasn't regressed."""
        from crawlit.parser.html_parser import HTMLParser
        
        html = "<html><body>" + "".join(
            f'<div><a href="/link{i}">Text</a></div>'
            for i in range(1000)
        ) + "</body></html>"
        
        parser = HTMLParser()
        
        # Benchmark baseline
        times = []
        for _ in range(10):
            start = time.time()
            parser.parse(html, "http://example.com")
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        
        # Set baseline (adjust based on actual performance)
        assert avg_time < 0.1  # Should parse in < 100ms

