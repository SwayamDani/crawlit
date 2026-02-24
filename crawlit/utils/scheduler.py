#!/usr/bin/env python3
"""
scheduler.py - Crawl scheduling with cron-like syntax

Enables scheduling recurring crawls with persistent configuration.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)

# Try to import croniter for cron expression parsing
try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False
    logger.debug("croniter not available - cron scheduling will be limited")


@dataclass
class ScheduledCrawl:
    """Configuration for a scheduled crawl."""
    id: str
    url: str
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    enabled: bool = True
    max_depth: int = 3
    options: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if data['options'] is None:
            data['options'] = {}
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledCrawl':
        """Create from dictionary."""
        return cls(**data)


class CrawlScheduler:
    """
    Scheduler for recurring crawls with cron-like syntax.
    
    Supports:
    - Cron expressions (requires croniter)
    - Simple interval-based scheduling
    - Persistent schedule storage
    - Concurrent crawl execution
    """
    
    def __init__(
        self,
        storage_path: str = './crawl_schedules.json',
        on_crawl: Optional[Callable[[ScheduledCrawl], Any]] = None
    ):
        """
        Initialize the crawl scheduler.
        
        Args:
            storage_path: Path to JSON file for storing schedules
            on_crawl: Callback to execute when a crawl is due
        """
        self.storage_path = Path(storage_path)
        self.on_crawl = on_crawl
        
        # Schedule storage
        self.schedules: Dict[str, ScheduledCrawl] = {}
        
        # Scheduler state
        self._running = False
        self._thread = None
        
        # Load existing schedules
        self._load_schedules()
        
        logger.debug(f"Crawl scheduler initialized: storage={storage_path}")
    
    def add_schedule(
        self,
        id: str,
        url: str,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        max_depth: int = 3,
        options: Optional[Dict[str, Any]] = None,
        enabled: bool = True
    ) -> ScheduledCrawl:
        """
        Add a new crawl schedule.
        
        Args:
            id: Unique identifier for the schedule
            url: URL to crawl
            cron_expression: Cron expression (e.g., "0 2 * * *")
            interval_seconds: Interval in seconds (alternative to cron)
            max_depth: Maximum crawl depth
            options: Additional crawl options
            enabled: Whether schedule is enabled
            
        Returns:
            ScheduledCrawl object
        """
        # Validate cron expression if provided
        if cron_expression and not CRONITER_AVAILABLE:
            raise ImportError("croniter required for cron expressions. Install with: pip install croniter")
        
        if cron_expression and CRONITER_AVAILABLE:
            try:
                # Validate cron expression
                croniter(cron_expression)
            except Exception as e:
                raise ValueError(f"Invalid cron expression '{cron_expression}': {e}")
        
        # Calculate next run time
        next_run = self._calculate_next_run(cron_expression, interval_seconds)
        
        schedule = ScheduledCrawl(
            id=id,
            url=url,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            next_run=next_run.isoformat() if next_run else None,
            max_depth=max_depth,
            options=options or {},
            enabled=enabled
        )
        
        self.schedules[id] = schedule
        self._save_schedules()
        
        logger.info(f"Added schedule '{id}' for {url} (next run: {next_run})")
        return schedule
    
    def remove_schedule(self, id: str) -> bool:
        """
        Remove a schedule.
        
        Args:
            id: Schedule identifier
            
        Returns:
            True if schedule was removed
        """
        if id in self.schedules:
            del self.schedules[id]
            self._save_schedules()
            logger.info(f"Removed schedule '{id}'")
            return True
        return False
    
    def enable_schedule(self, id: str) -> bool:
        """Enable a schedule."""
        if id in self.schedules:
            self.schedules[id].enabled = True
            self._save_schedules()
            logger.info(f"Enabled schedule '{id}'")
            return True
        return False
    
    def disable_schedule(self, id: str) -> bool:
        """Disable a schedule."""
        if id in self.schedules:
            self.schedules[id].enabled = False
            self._save_schedules()
            logger.info(f"Disabled schedule '{id}'")
            return True
        return False
    
    def get_schedule(self, id: str) -> Optional[ScheduledCrawl]:
        """Get a schedule by ID."""
        return self.schedules.get(id)
    
    def list_schedules(self) -> List[ScheduledCrawl]:
        """Get all schedules."""
        return list(self.schedules.values())
    
    def start(self, daemon: bool = True) -> None:
        """
        Start the scheduler in a background thread.
        
        Args:
            daemon: Whether to run as daemon thread
        """
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=daemon)
        self._thread.start()
        
        logger.info("Crawl scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info("Crawl scheduler stopped")
    
    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Check all schedules
                now = datetime.now()
                
                for schedule_id, schedule in list(self.schedules.items()):
                    if not schedule.enabled:
                        continue
                    
                    if not schedule.next_run:
                        continue
                    
                    next_run = datetime.fromisoformat(schedule.next_run)
                    
                    if now >= next_run:
                        # Time to run this crawl
                        logger.info(f"Executing scheduled crawl '{schedule_id}' for {schedule.url}")
                        
                        # Execute crawl
                        if self.on_crawl:
                            try:
                                self.on_crawl(schedule)
                            except Exception as e:
                                logger.error(f"Error executing crawl '{schedule_id}': {e}")
                        
                        # Update schedule
                        schedule.last_run = now.isoformat()
                        next_run = self._calculate_next_run(
                            schedule.cron_expression,
                            schedule.interval_seconds,
                            from_time=now
                        )
                        schedule.next_run = next_run.isoformat() if next_run else None
                        
                        self._save_schedules()
                
                # Sleep for a bit before checking again
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def _calculate_next_run(
        self,
        cron_expression: Optional[str],
        interval_seconds: Optional[int],
        from_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Calculate the next run time.
        
        Args:
            cron_expression: Cron expression
            interval_seconds: Interval in seconds
            from_time: Calculate from this time (default: now)
            
        Returns:
            Next run datetime or None
        """
        if from_time is None:
            from_time = datetime.now()
        
        if cron_expression and CRONITER_AVAILABLE:
            try:
                cron = croniter(cron_expression, from_time)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(f"Error calculating next run from cron '{cron_expression}': {e}")
                return None
        
        if interval_seconds:
            return from_time + timedelta(seconds=interval_seconds)
        
        return None
    
    def _load_schedules(self) -> None:
        """Load schedules from storage."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for schedule_data in data:
                schedule = ScheduledCrawl.from_dict(schedule_data)
                self.schedules[schedule.id] = schedule
            
            logger.info(f"Loaded {len(self.schedules)} schedules from {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
    
    def _save_schedules(self) -> None:
        """Save schedules to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = [schedule.to_dict() for schedule in self.schedules.values()]
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self.schedules)} schedules to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scheduler statistics.
        
        Returns:
            Dictionary with statistics
        """
        enabled_count = sum(1 for s in self.schedules.values() if s.enabled)
        disabled_count = len(self.schedules) - enabled_count
        
        # Get next runs
        next_runs = []
        for schedule in self.schedules.values():
            if schedule.enabled and schedule.next_run:
                next_runs.append({
                    'id': schedule.id,
                    'url': schedule.url,
                    'next_run': schedule.next_run
                })
        
        # Sort by next run time
        next_runs.sort(key=lambda x: x['next_run'])
        
        return {
            'total_schedules': len(self.schedules),
            'enabled_schedules': enabled_count,
            'disabled_schedules': disabled_count,
            'running': self._running,
            'next_runs': next_runs[:5],  # Show next 5 runs
            'storage_path': str(self.storage_path)
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def is_croniter_available() -> bool:
    """Check if croniter is available for cron expressions."""
    return CRONITER_AVAILABLE




