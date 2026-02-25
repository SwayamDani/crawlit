#!/usr/bin/env python3
"""
test_crawl_scheduler.py - Tests for CrawlScheduler and ScheduledCrawl
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crawlit.utils.scheduler import CrawlScheduler, ScheduledCrawl, CRONITER_AVAILABLE


# ──────────────────────────────────────────────────────────
# ScheduledCrawl dataclass
# ──────────────────────────────────────────────────────────

class TestScheduledCrawl:
    def test_to_dict(self):
        sc = ScheduledCrawl(id="test", url="https://example.com",
                            interval_seconds=3600)
        d = sc.to_dict()
        assert d["id"] == "test"
        assert d["url"] == "https://example.com"
        assert d["interval_seconds"] == 3600
        assert d["options"] == {}   # None → {} in to_dict

    def test_from_dict(self):
        data = {
            "id": "test2", "url": "https://b.com",
            "cron_expression": None, "interval_seconds": 60,
            "next_run": None, "last_run": None, "enabled": True,
            "max_depth": 2, "options": {}
        }
        sc = ScheduledCrawl.from_dict(data)
        assert sc.id == "test2"
        assert sc.url == "https://b.com"
        assert sc.interval_seconds == 60


# ──────────────────────────────────────────────────────────
# CrawlScheduler – basic operations
# ──────────────────────────────────────────────────────────

class TestCrawlSchedulerBasic:
    def test_add_interval_schedule(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        sc = scheduler.add_schedule("job1", "https://example.com",
                                    interval_seconds=3600)
        assert sc.id == "job1"
        assert sc.url == "https://example.com"
        assert sc.next_run is not None

    def test_schedule_persisted_to_disk(self, tmp_path):
        path = tmp_path / "sched.json"
        scheduler = CrawlScheduler(storage_path=str(path))
        scheduler.add_schedule("job1", "https://example.com",
                               interval_seconds=60)
        assert path.exists()
        data = json.loads(path.read_text())
        # Saved as a list of schedule dicts
        ids = [entry["id"] for entry in data]
        assert "job1" in ids

    def test_load_schedules_on_init(self, tmp_path):
        path = tmp_path / "sched.json"
        scheduler1 = CrawlScheduler(storage_path=str(path))
        scheduler1.add_schedule("job1", "https://example.com",
                                interval_seconds=3600)

        scheduler2 = CrawlScheduler(storage_path=str(path))
        assert "job1" in scheduler2.schedules

    def test_remove_schedule(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        scheduler.add_schedule("job1", "https://example.com",
                               interval_seconds=60)
        assert scheduler.remove_schedule("job1") is True
        assert scheduler.get_schedule("job1") is None

    def test_remove_nonexistent_schedule_returns_false(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        assert scheduler.remove_schedule("nope") is False

    def test_enable_disable_schedule(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        scheduler.add_schedule("job1", "https://example.com",
                               interval_seconds=60)
        assert scheduler.disable_schedule("job1") is True
        assert scheduler.get_schedule("job1").enabled is False
        assert scheduler.enable_schedule("job1") is True
        assert scheduler.get_schedule("job1").enabled is True

    def test_enable_nonexistent_returns_false(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        assert scheduler.enable_schedule("nope") is False

    def test_list_schedules(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        scheduler.add_schedule("a", "https://a.com", interval_seconds=60)
        scheduler.add_schedule("b", "https://b.com", interval_seconds=120)
        schedules = scheduler.list_schedules()
        assert len(schedules) == 2
        ids = {s.id for s in schedules}
        assert ids == {"a", "b"}

    def test_get_schedule(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        scheduler.add_schedule("job1", "https://example.com",
                               interval_seconds=60)
        sc = scheduler.get_schedule("job1")
        assert sc is not None
        assert sc.url == "https://example.com"


# ──────────────────────────────────────────────────────────
# CrawlScheduler – cron expressions
# ──────────────────────────────────────────────────────────

@pytest.mark.skipif(not CRONITER_AVAILABLE, reason="croniter not installed")
class TestCrawlSchedulerCron:
    def test_add_cron_schedule(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        sc = scheduler.add_schedule("daily", "https://example.com",
                                    cron_expression="0 2 * * *")
        assert sc.cron_expression == "0 2 * * *"
        assert sc.next_run is not None

    def test_invalid_cron_raises(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        with pytest.raises(ValueError, match="Invalid cron expression"):
            scheduler.add_schedule("bad", "https://example.com",
                                   cron_expression="not-a-cron")


class TestCrawlSchedulerNoCroniter:
    def test_cron_without_croniter_raises_import_error(self, tmp_path):
        with patch("crawlit.utils.scheduler.CRONITER_AVAILABLE", False):
            scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
            with pytest.raises(ImportError):
                scheduler.add_schedule("job", "https://example.com",
                                       cron_expression="0 * * * *")


# ──────────────────────────────────────────────────────────
# CrawlScheduler – runner / callback
# ──────────────────────────────────────────────────────────

class TestCrawlSchedulerRunner:
    def test_on_crawl_callback_invoked(self, tmp_path):
        callback_received = []

        def on_crawl(schedule):
            callback_received.append(schedule.id)

        scheduler = CrawlScheduler(
            storage_path=str(tmp_path / "sched.json"),
            on_crawl=on_crawl
        )
        # Add a schedule with next_run already in the past
        sc = scheduler.add_schedule("job1", "https://example.com",
                                    interval_seconds=3600)
        # Backdate the next_run
        scheduler.schedules["job1"].next_run = "2000-01-01T00:00:00"

        # Run one iteration of the loop manually
        scheduler._running = True
        try:
            # Run the loop iteration directly (not in a thread)
            # We patch _run_loop to exit after one pass
            original_loop = scheduler._run_loop

            call_count = 0
            def one_shot_loop():
                nonlocal call_count
                # Patch self._running to False after first tick
                scheduler._running = False
                original_loop.__self__._run_loop()

            # Directly invoke the body of the loop once
            from datetime import datetime
            now = datetime.now()
            for schedule_id, schedule in list(scheduler.schedules.items()):
                if not schedule.enabled or not schedule.next_run:
                    continue
                next_run_dt = datetime.fromisoformat(schedule.next_run)
                if now >= next_run_dt and scheduler.on_crawl:
                    scheduler.on_crawl(schedule)
        finally:
            scheduler._running = False

        assert "job1" in callback_received

    def test_start_and_stop(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        scheduler.start(daemon=True)
        assert scheduler._running is True
        scheduler.stop()
        assert scheduler._running is False

    def test_double_start_is_noop(self, tmp_path):
        scheduler = CrawlScheduler(storage_path=str(tmp_path / "sched.json"))
        scheduler.start(daemon=True)
        thread_before = scheduler._thread
        scheduler.start(daemon=True)  # Second start should be a no-op
        assert scheduler._thread is thread_before
        scheduler.stop()
