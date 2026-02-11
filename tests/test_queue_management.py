#!/usr/bin/env python3
"""
Tests for queue management features
"""

import pytest
import os
import tempfile
from crawlit.crawler.engine import Crawler
from crawlit.utils.queue_manager import QueueManager
from collections import deque


class TestQueueManagement:
    """Test queue management features"""
    
    def test_pause_resume(self, mock_website):
        """Test pause and resume functionality"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1,
            max_queue_size=10
        )
        
        # Start crawling in a separate thread or use a small crawl
        # For this test, we'll just verify the methods exist and work
        assert crawler.is_paused() == False
        
        crawler.pause()
        assert crawler.is_paused() == True
        
        crawler.resume()
        assert crawler.is_paused() == False
    
    def test_max_queue_size(self, mock_website):
        """Test queue size limiting"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=0,
            max_queue_size=5
        )
        
        # Verify max_queue_size is set
        assert crawler.max_queue_size == 5
        
        # Start with one URL
        crawler.queue.append((mock_website, 0))
        
        # Add URLs up to the limit
        for i in range(5):
            crawler.queue.append((f"{mock_website}page{i}", 1))
        
        # Verify queue size
        assert len(crawler.queue) == 6  # 1 initial + 5 added
        
        # Try to add one more - should be blocked by the check in crawl()
        # (This is tested during actual crawling)
    
    def test_save_load_state(self, mock_website):
        """Test saving and loading crawler state"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=1
        )
        
        # Add some state
        crawler.queue.append((mock_website, 0))
        crawler.queue.append((f"{mock_website}page1", 1))
        crawler.visited_urls.add(mock_website)
        crawler.results[mock_website] = {
            'success': True,
            'status': 200,
            'depth': 0
        }
        
        # Save state
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            crawler.save_state(temp_path)
            
            # Verify file exists
            assert os.path.exists(temp_path)
            
            # Create new crawler and load state
            new_crawler = Crawler(
                start_url=mock_website,
                max_depth=1
            )
            new_crawler.load_state(temp_path)
            
            # Verify state was restored
            assert len(new_crawler.queue) == 2
            assert mock_website in new_crawler.visited_urls
            assert mock_website in new_crawler.results
            assert new_crawler.results[mock_website]['status'] == 200
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_get_queue_stats(self, mock_website):
        """Test queue statistics"""
        crawler = Crawler(
            start_url=mock_website,
            max_depth=2
        )
        
        # Add URLs at different depths
        crawler.queue.append((mock_website, 0))
        crawler.queue.append((f"{mock_website}page1", 1))
        crawler.queue.append((f"{mock_website}page2", 1))
        crawler.queue.append((f"{mock_website}page3", 2))
        
        stats = crawler.get_queue_stats()
        
        assert stats['size'] == 4
        assert stats['min_depth'] == 0
        assert stats['max_depth'] == 2
        assert stats['depths'][0] == 1
        assert stats['depths'][1] == 2
        assert stats['depths'][2] == 1
    
    def test_queue_manager_save_load(self):
        """Test QueueManager directly"""
        queue = deque([('https://example.com', 0), ('https://example.com/page1', 1)])
        visited_urls = {'https://example.com'}
        results = {
            'https://example.com': {
                'success': True,
                'status': 200
            }
        }
        metadata = {
            'start_url': 'https://example.com',
            'max_depth': 2
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Save
            QueueManager.save_state(queue, visited_urls, results, temp_path, metadata)
            
            # Load
            loaded_queue, loaded_visited, loaded_results, loaded_metadata = QueueManager.load_state(temp_path)
            
            # Verify
            assert len(loaded_queue) == 2
            assert list(loaded_queue) == list(queue)  # QueueManager converts lists back to tuples
            assert loaded_visited == visited_urls
            assert loaded_results == results
            assert loaded_metadata == metadata
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_queue_manager_stats(self):
        """Test QueueManager statistics"""
        queue = deque([
            ('https://example.com', 0),
            ('https://example.com/page1', 1),
            ('https://example.com/page2', 1),
            ('https://example.com/page3', 2)
        ])
        
        stats = QueueManager.get_queue_stats(queue)
        
        assert stats['size'] == 4
        assert stats['min_depth'] == 0
        assert stats['max_depth'] == 2
        assert stats['depths'][0] == 1
        assert stats['depths'][1] == 2
        assert stats['depths'][2] == 1
        
        # Test empty queue
        empty_queue = deque()
        empty_stats = QueueManager.get_queue_stats(empty_queue)
        assert empty_stats['size'] == 0
        assert empty_stats['min_depth'] is None
        assert empty_stats['max_depth'] is None

