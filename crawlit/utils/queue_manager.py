#!/usr/bin/env python3
"""
queue_manager.py - Queue management utilities for crawler state persistence
"""

import json
import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Utility class for managing crawler queue state, including save/load functionality.
    """
    
    @staticmethod
    def save_state(
        queue: deque,
        visited_urls: Set[str],
        results: Dict[str, Any],
        filepath: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save crawler state to a JSON file.
        
        Args:
            queue: The URL queue (deque of (url, depth) tuples)
            visited_urls: Set of visited URLs
            results: Crawl results dictionary
            filepath: Path to save the state file
            metadata: Optional metadata to include (e.g., start_url, max_depth)
        """
        # Convert deque to list for JSON serialization
        queue_list = list(queue)
        
        # Convert set to list for JSON serialization
        visited_urls_list = list(visited_urls)
        
        # Prepare state dictionary
        state = {
            'queue': queue_list,
            'visited_urls': visited_urls_list,
            'results': results,
            'metadata': metadata or {},
            'saved_at': datetime.now().isoformat()
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"Crawler state saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save crawler state: {e}")
            raise
    
    @staticmethod
    def load_state(filepath: str) -> Tuple[deque, Set[str], Dict[str, Any], Dict[str, Any]]:
        """
        Load crawler state from a JSON file.
        
        Args:
            filepath: Path to the state file
            
        Returns:
            Tuple of (queue, visited_urls, results, metadata)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Reconstruct deque from list, converting lists back to tuples
            queue_data = state.get('queue', [])
            queue = deque([tuple(item) if isinstance(item, list) else item for item in queue_data])
            
            # Reconstruct set from list
            visited_urls = set(state.get('visited_urls', []))
            
            # Get results and metadata
            results = state.get('results', {})
            metadata = state.get('metadata', {})
            
            logger.info(f"Crawler state loaded from {filepath}")
            logger.info(f"  - Queue size: {len(queue)}")
            logger.info(f"  - Visited URLs: {len(visited_urls)}")
            logger.info(f"  - Results: {len(results)}")
            
            return queue, visited_urls, results, metadata
        except FileNotFoundError:
            logger.error(f"State file not found: {filepath}")
            raise
        except Exception as e:
            logger.error(f"Failed to load crawler state: {e}")
            raise
    
    @staticmethod
    def get_queue_stats(queue: deque) -> Dict[str, Any]:
        """
        Get statistics about the queue.
        
        Args:
            queue: The URL queue
            
        Returns:
            Dictionary with queue statistics
        """
        if not queue:
            return {
                'size': 0,
                'depths': {},
                'min_depth': None,
                'max_depth': None
            }
        
        depths = {}
        min_depth = float('inf')
        max_depth = float('-inf')
        
        for url, depth in queue:
            depths[depth] = depths.get(depth, 0) + 1
            min_depth = min(min_depth, depth)
            max_depth = max(max_depth, depth)
        
        return {
            'size': len(queue),
            'depths': depths,
            'min_depth': int(min_depth) if min_depth != float('inf') else None,
            'max_depth': int(max_depth) if max_depth != float('-inf') else None
        }

