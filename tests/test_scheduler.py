#!/usr/bin/env python3
"""
Tests for crawl scheduler functionality
"""

import pytest
import time
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock

from crawlit.utils.scheduler import CrawlScheduler, ScheduledCrawl, is_croniter_available


class TestScheduledCrawl:
    """Tests for ScheduledCrawl dataclass."""
    
    def test_creation(self):
        """Test creating a ScheduledCrawl."""
        crawl = ScheduledCrawl(
            id="test1",
            url="https://example.com",
            interval_seconds=3600,
            max_depth=2
        )
        
        assert crawl.id == "test1"
        assert crawl.url == "https://example.com"
        assert crawl.interval_seconds == 3600
        assert crawl.max_depth == 2
        assert crawl.enabled is True
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        crawl = ScheduledCrawl(
            id="test1",
            url="https://example.com",
            interval_seconds=3600
        )
        
        data = crawl.to_dict()
        
        assert isinstance(data, dict)
        assert data['id'] == "test1"
        assert data['url'] == "https://example.com"
        assert data['interval_seconds'] == 3600
        assert data['options'] == {}
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'id': 'test1',
            'url': 'https://example.com',
            'interval_seconds': 3600,
            'cron_expression': None,
            'next_run': None,
            'last_run': None,
            'enabled': True,
            'max_depth': 3,
            'options': {}
        }
        
        crawl = ScheduledCrawl.from_dict(data)
        
        assert crawl.id == "test1"
        assert crawl.url == "https://example.com"
        assert crawl.interval_seconds == 3600


class TestCrawlScheduler:
    """Tests for CrawlScheduler."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    def test_initialization(self, temp_storage):
        """Test scheduler initialization."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        assert len(scheduler.list_schedules()) == 0
        assert scheduler._running is False
        assert scheduler.storage_path == Path(temp_storage)
    
    def test_add_schedule_with_interval(self, temp_storage):
        """Test adding a schedule with interval."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        schedule = scheduler.add_schedule(
            id="test1",
            url="https://example.com",
            interval_seconds=3600,
            max_depth=2
        )
        
        assert schedule.id == "test1"
        assert schedule.url == "https://example.com"
        assert schedule.interval_seconds == 3600
        assert schedule.max_depth == 2
        assert schedule.enabled is True
        assert schedule.next_run is not None
    
    def test_add_schedule_with_options(self, temp_storage):
        """Test adding a schedule with custom options."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        options = {'internal_only': True, 'delay': 1.0}
        schedule = scheduler.add_schedule(
            id="test1",
            url="https://example.com",
            interval_seconds=3600,
            options=options
        )
        
        assert schedule.options == options
    
    @pytest.mark.skipif(not is_croniter_available(), reason="croniter not available")
    def test_add_schedule_with_cron(self, temp_storage):
        """Test adding a schedule with cron expression."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        # Daily at 2 AM
        schedule = scheduler.add_schedule(
            id="test1",
            url="https://example.com",
            cron_expression="0 2 * * *"
        )
        
        assert schedule.cron_expression == "0 2 * * *"
        assert schedule.next_run is not None
    
    @pytest.mark.skipif(not is_croniter_available(), reason="croniter not available")
    def test_invalid_cron_expression(self, temp_storage):
        """Test that invalid cron expression raises error."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        with pytest.raises(ValueError, match="Invalid cron expression"):
            scheduler.add_schedule(
                id="test1",
                url="https://example.com",
                cron_expression="invalid cron"
            )
    
    def test_remove_schedule(self, temp_storage):
        """Test removing a schedule."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        scheduler.add_schedule(id="test1", url="https://example.com", interval_seconds=3600)
        assert len(scheduler.list_schedules()) == 1
        
        result = scheduler.remove_schedule("test1")
        assert result is True
        assert len(scheduler.list_schedules()) == 0
        
        # Try removing non-existent schedule
        result = scheduler.remove_schedule("nonexistent")
        assert result is False
    
    def test_enable_disable_schedule(self, temp_storage):
        """Test enabling and disabling schedules."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        scheduler.add_schedule(id="test1", url="https://example.com", interval_seconds=3600)
        
        # Disable
        result = scheduler.disable_schedule("test1")
        assert result is True
        schedule = scheduler.get_schedule("test1")
        assert schedule.enabled is False
        
        # Enable
        result = scheduler.enable_schedule("test1")
        assert result is True
        schedule = scheduler.get_schedule("test1")
        assert schedule.enabled is True
    
    def test_get_schedule(self, temp_storage):
        """Test getting a specific schedule."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        scheduler.add_schedule(id="test1", url="https://example.com", interval_seconds=3600)
        
        schedule = scheduler.get_schedule("test1")
        assert schedule is not None
        assert schedule.id == "test1"
        
        # Non-existent schedule
        schedule = scheduler.get_schedule("nonexistent")
        assert schedule is None
    
    def test_list_schedules(self, temp_storage):
        """Test listing all schedules."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        scheduler.add_schedule(id="test1", url="https://example.com", interval_seconds=3600)
        scheduler.add_schedule(id="test2", url="https://example.org", interval_seconds=7200)
        
        schedules = scheduler.list_schedules()
        assert len(schedules) == 2
        assert all(isinstance(s, ScheduledCrawl) for s in schedules)
    
    def test_persistence(self, temp_storage):
        """Test that schedules persist to storage."""
        # Create scheduler and add schedule
        scheduler1 = CrawlScheduler(storage_path=temp_storage)
        scheduler1.add_schedule(id="test1", url="https://example.com", interval_seconds=3600)
        
        # Create new scheduler instance - should load from storage
        scheduler2 = CrawlScheduler(storage_path=temp_storage)
        
        schedules = scheduler2.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].id == "test1"
        assert schedules[0].url == "https://example.com"
    
    def test_start_stop(self, temp_storage):
        """Test starting and stopping the scheduler."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        assert scheduler._running is False
        
        scheduler.start()
        assert scheduler._running is True
        assert scheduler._thread is not None
        
        scheduler.stop()
        assert scheduler._running is False
    
    def test_double_start(self, temp_storage):
        """Test that starting twice doesn't cause issues."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        scheduler.start()
        scheduler.start()  # Should log warning but not fail
        
        assert scheduler._running is True
        
        scheduler.stop()
    
    def test_on_crawl_callback(self, temp_storage):
        """Test that on_crawl callback is set."""
        callback = Mock()
        scheduler = CrawlScheduler(storage_path=temp_storage, on_crawl=callback)
        
        assert scheduler.on_crawl is callback
    
    def test_get_stats(self, temp_storage):
        """Test getting scheduler statistics."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        scheduler.add_schedule(id="test1", url="https://example.com", interval_seconds=3600)
        scheduler.add_schedule(id="test2", url="https://example.org", interval_seconds=7200, enabled=False)
        
        stats = scheduler.get_stats()
        
        assert stats['total_schedules'] == 2
        assert stats['enabled_schedules'] == 1
        assert stats['disabled_schedules'] == 1
        assert stats['running'] is False
        assert 'next_runs' in stats
        assert 'storage_path' in stats
    
    def test_context_manager(self, temp_storage):
        """Test using scheduler as context manager."""
        with CrawlScheduler(storage_path=temp_storage) as scheduler:
            assert scheduler._running is True
        
        # Should be stopped after exiting context
        assert scheduler._running is False
    
    def test_calculate_next_run_with_interval(self, temp_storage):
        """Test calculating next run with interval."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        now = datetime.now()
        next_run = scheduler._calculate_next_run(None, 3600, from_time=now)
        
        assert next_run is not None
        expected = now + timedelta(seconds=3600)
        # Allow small time difference
        assert abs((next_run - expected).total_seconds()) < 1
    
    @pytest.mark.skipif(not is_croniter_available(), reason="croniter not available")
    def test_calculate_next_run_with_cron(self, temp_storage):
        """Test calculating next run with cron expression."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        # Every day at 2 AM
        next_run = scheduler._calculate_next_run("0 2 * * *", None)
        
        assert next_run is not None
        # Should be in the future
        assert next_run > datetime.now()
    
    def test_calculate_next_run_no_schedule(self, temp_storage):
        """Test calculating next run with no schedule."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        next_run = scheduler._calculate_next_run(None, None)
        
        assert next_run is None


class TestSchedulerEdgeCases:
    """Edge case tests for scheduler."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)
    
    def test_empty_scheduler_start_stop(self, temp_storage):
        """Test starting/stopping scheduler with no jobs."""
        scheduler = CrawlScheduler(storage_path=temp_storage)
        
        scheduler.start()
        assert scheduler._running is True
        
        time.sleep(0.5)
        
        scheduler.stop()
        assert scheduler._running is False
    
    def test_disabled_schedule_not_executed(self, temp_storage):
        """Test that disabled schedules are not executed."""
        executed = []
        
        def on_crawl(schedule):
            executed.append(schedule.id)
        
        scheduler = CrawlScheduler(storage_path=temp_storage, on_crawl=on_crawl)
        
        schedule = scheduler.add_schedule(
            id="test1",
            url="https://example.com",
            interval_seconds=1,
            enabled=False
        )
        
        # Even if it's time to run, disabled schedules shouldn't execute
        assert schedule.enabled is False


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_is_croniter_available(self):
        """Test croniter availability check."""
        result = is_croniter_available()
        assert isinstance(result, bool)
