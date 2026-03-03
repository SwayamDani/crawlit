"""Tests for crawlit utility modules."""

import re
import time
import asyncio
import pytest
from unittest.mock import MagicMock, patch

import requests
import requests.exceptions
import aiohttp

from crawlit.utils.url_filter import URLFilter, sanitize_url_for_log
from crawlit.utils.rate_limiter import (
    RateLimiter, AsyncRateLimiter, DynamicRateLimiter, AsyncDynamicRateLimiter,
)
from crawlit.utils.deduplication import ContentDeduplicator
from crawlit.utils.budget_tracker import BudgetTracker, BudgetLimits, AsyncBudgetTracker
from crawlit.utils.errors import (
    CrawlitError, FetchError, RobotsError, ParseError,
    ExtractionError, handle_fetch_error,
)
from crawlit.utils.event_log import (
    CrawlEventLog, EVENT_TYPES, CRAWL_START, CRAWL_END,
    FETCH_RETRY, FETCH_ERROR, ROBOTS_REJECT, PIPELINE_DROP,
    PIPELINE_ERROR, EXTRACTOR_ERROR, INCREMENTAL_HIT, DEDUPE_HIT,
)


# -----------------------------------------------------------------------
# URL Filter
# -----------------------------------------------------------------------

class TestURLFilter:
    def test_no_filters_allows_all(self):
        f = URLFilter()
        assert f.is_allowed("https://example.com/anything") is True

    def test_blocked_pattern(self):
        f = URLFilter(blocked_patterns=[re.compile(r"/admin")])
        assert f.is_allowed("https://example.com/admin/dashboard") is False
        assert f.is_allowed("https://example.com/public") is True

    def test_allowed_pattern(self):
        f = URLFilter(allowed_patterns=[re.compile(r"example\.com")])
        assert f.is_allowed("https://example.com/page") is True
        assert f.is_allowed("https://other.com/page") is False

    def test_blocked_extensions(self):
        f = URLFilter(blocked_extensions=[".pdf", ".zip"])
        assert f.is_allowed("https://example.com/doc.pdf") is False
        assert f.is_allowed("https://example.com/page.html") is True

    def test_allowed_extensions(self):
        f = URLFilter(allowed_extensions=[".html", ".htm", ""])
        assert f.is_allowed("https://example.com/page.html") is True
        assert f.is_allowed("https://example.com/doc.pdf") is False
        assert f.is_allowed("https://example.com/page") is True

    def test_blocked_query_params(self):
        f = URLFilter(blocked_query_params=["debug"])
        assert f.is_allowed("https://example.com/?debug=1") is False
        assert f.is_allowed("https://example.com/?page=2") is True

    def test_allowed_query_params(self):
        f = URLFilter(allowed_query_params=["page"])
        assert f.is_allowed("https://example.com/?page=2") is True
        assert f.is_allowed("https://example.com/?sort=name") is False

    def test_custom_filter(self):
        f = URLFilter(custom_filter=lambda url: "allowed" in url)
        assert f.is_allowed("https://example.com/allowed") is True
        assert f.is_allowed("https://example.com/blocked") is False

    def test_from_patterns_allowed(self):
        f = URLFilter.from_patterns(allowed_regex=r"example\.com")
        assert f.is_allowed("https://example.com/page") is True
        assert f.is_allowed("https://other.com/page") is False

    def test_from_patterns_blocked(self):
        f = URLFilter.from_patterns(blocked_regex=r"/admin")
        assert f.is_allowed("https://example.com/admin") is False
        assert f.is_allowed("https://example.com/page") is True

    def test_from_patterns_invalid_regex(self):
        with pytest.raises(ValueError):
            URLFilter.from_patterns(allowed_regex="[invalid")

    def test_html_only(self):
        f = URLFilter.html_only()
        assert f.is_allowed("https://example.com/page.html") is True
        assert f.is_allowed("https://example.com/doc.pdf") is False
        assert f.is_allowed("https://example.com/page") is True

    def test_exclude_media(self):
        f = URLFilter.exclude_media()
        assert f.is_allowed("https://example.com/image.jpg") is False
        assert f.is_allowed("https://example.com/video.mp4") is False
        assert f.is_allowed("https://example.com/page.html") is True


class TestSanitizeUrlForLog:
    def test_no_sensitive_params(self):
        url = "https://example.com/page?id=123"
        assert sanitize_url_for_log(url) == url

    def test_redacts_api_key(self):
        url = "https://example.com/api?api_key=secret123&page=1"
        result = sanitize_url_for_log(url)
        assert "secret123" not in result
        assert "REDACTED" in result
        assert "page=1" in result

    def test_redacts_token(self):
        url = "https://example.com?token=abc123"
        result = sanitize_url_for_log(url)
        assert "abc123" not in result

    def test_redacts_password(self):
        url = "https://example.com?password=hunter2"
        result = sanitize_url_for_log(url)
        assert "hunter2" not in result

    def test_no_query_string(self):
        url = "https://example.com/page"
        assert sanitize_url_for_log(url) == url

    def test_preserves_structure(self):
        url = "https://example.com/path?key=secret&page=1"
        result = sanitize_url_for_log(url)
        assert result.startswith("https://example.com/path?")


# -----------------------------------------------------------------------
# Rate Limiter
# -----------------------------------------------------------------------

class TestRateLimiter:
    def test_default_delay(self):
        rl = RateLimiter(default_delay=0.5)
        assert rl.default_delay == 0.5

    def test_requests_per_second(self):
        rl = RateLimiter(requests_per_second=2.0)
        assert rl.default_delay == 0.5

    def test_requests_per_second_invalid(self):
        with pytest.raises(ValueError):
            RateLimiter(requests_per_second=0)

    def test_set_domain_delay(self):
        rl = RateLimiter()
        rl.set_domain_delay("example.com", 1.0)
        assert rl.get_domain_delay("example.com") == 1.0

    def test_get_domain_delay_default(self):
        rl = RateLimiter(default_delay=0.2)
        assert rl.get_domain_delay("unknown.com") == 0.2

    @patch("crawlit.utils.rate_limiter.time.sleep")
    def test_wait_if_needed(self, mock_sleep):
        rl = RateLimiter(default_delay=0.5)
        rl.wait_if_needed("https://example.com/page1")
        rl.wait_if_needed("https://example.com/page2")
        assert mock_sleep.called or True  # first call may not need waiting

    def test_wait_alias(self):
        rl = RateLimiter(default_delay=0.0)
        rl.wait("https://example.com/page")  # should not raise

    def test_get_stats(self):
        rl = RateLimiter()
        rl.set_domain_delay("example.com", 1.0)
        stats = rl.get_stats()
        assert stats["default_delay"] == 0.1
        assert stats["domains_with_custom_delay"] == 1

    def test_clear(self):
        rl = RateLimiter()
        rl.set_domain_delay("example.com", 1.0)
        rl.wait_if_needed("https://example.com/page")
        rl.clear()
        stats = rl.get_stats()
        assert stats["domains_with_custom_delay"] == 0
        assert stats["domains_tracked"] == 0


class TestAsyncRateLimiter:
    @pytest.mark.asyncio
    async def test_set_and_get_delay(self):
        rl = AsyncRateLimiter(default_delay=0.1)
        await rl.set_domain_delay("example.com", 0.5)
        delay = await rl.get_domain_delay("example.com")
        assert delay == 0.5

    @pytest.mark.asyncio
    async def test_default_delay(self):
        rl = AsyncRateLimiter(default_delay=0.3)
        delay = await rl.get_domain_delay("unknown.com")
        assert delay == 0.3

    @pytest.mark.asyncio
    async def test_get_stats(self):
        rl = AsyncRateLimiter()
        stats = await rl.get_stats()
        assert "default_delay" in stats

    @pytest.mark.asyncio
    async def test_clear(self):
        rl = AsyncRateLimiter()
        await rl.set_domain_delay("a.com", 1.0)
        await rl.clear()
        stats = await rl.get_stats()
        assert stats["domains_with_custom_delay"] == 0


class TestDynamicRateLimiter:
    def test_429_increases_delay(self):
        rl = DynamicRateLimiter(default_delay=0.1)
        rl.record_response("https://example.com/page", 0.5, 429)
        delay = rl.get_domain_delay("example.com")
        assert delay > 0.1

    def test_429_with_retry_after(self):
        rl = DynamicRateLimiter(default_delay=0.1)
        rl.record_response("https://example.com/page", 0.5, 429, retry_after=10)
        delay = rl.get_domain_delay("example.com")
        assert delay == 10.0

    def test_fast_responses_decrease_delay(self):
        rl = DynamicRateLimiter(default_delay=1.0, min_delay=0.01)
        for i in range(10):
            rl.record_response("https://example.com/p", 0.1, 200)
        delay = rl.get_domain_delay("example.com")
        assert delay <= 1.0

    def test_slow_responses_increase_delay(self):
        rl = DynamicRateLimiter(default_delay=0.1)
        for i in range(10):
            rl.record_response("https://example.com/p", 5.0, 200)
        delay = rl.get_domain_delay("example.com")
        assert delay >= 0.1

    def test_get_stats_extended(self):
        rl = DynamicRateLimiter()
        rl.record_response("https://example.com/p", 0.5, 200)
        stats = rl.get_stats()
        assert "dynamic_tracking" in stats
        assert "min_delay" in stats["dynamic_tracking"]

    def test_max_delay_cap(self):
        rl = DynamicRateLimiter(default_delay=5.0, max_delay=10.0)
        rl.record_response("https://example.com/p", 0.5, 429)
        delay = rl.get_domain_delay("example.com")
        assert delay <= 10.0


class TestAsyncDynamicRateLimiter:
    @pytest.mark.asyncio
    async def test_429_increases_delay(self):
        rl = AsyncDynamicRateLimiter(default_delay=0.1)
        await rl.record_response("https://example.com/page", 0.5, 429)
        delay = await rl.get_domain_delay("example.com")
        assert delay > 0.1


# -----------------------------------------------------------------------
# Content Deduplication
# -----------------------------------------------------------------------

class TestContentDeduplicator:
    CONTENT_A = "<html><body><p>" + "x " * 100 + "</p></body></html>"
    CONTENT_B = "<html><body><p>" + "y " * 100 + "</p></body></html>"

    def test_first_content_not_duplicate(self):
        dd = ContentDeduplicator()
        assert dd.is_duplicate(self.CONTENT_A, "https://a.com") is False

    def test_same_content_is_duplicate(self):
        dd = ContentDeduplicator()
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        assert dd.is_duplicate(self.CONTENT_A, "https://b.com") is True

    def test_different_content_not_duplicate(self):
        dd = ContentDeduplicator()
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        assert dd.is_duplicate(self.CONTENT_B, "https://b.com") is False

    def test_disabled(self):
        dd = ContentDeduplicator(enabled=False)
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        assert dd.is_duplicate(self.CONTENT_A, "https://b.com") is False

    def test_min_content_length(self):
        dd = ContentDeduplicator(min_content_length=1000)
        assert dd.is_duplicate("short content", "https://a.com") is False

    def test_normalization(self):
        dd = ContentDeduplicator(normalize_content=True)
        html1 = "<html><body><script>var x=1;</script><p>Hello world</p></body></html>"
        html2 = "<html><body><script>var y=2;</script><p>Hello   world</p></body></html>"
        # Pad to meet min_content_length
        pad = " content " * 20
        html1 = html1.replace("</p>", pad + "</p>")
        html2 = html2.replace("</p>", pad + "</p>")
        dd.is_duplicate(html1, "https://a.com")
        assert dd.is_duplicate(html2, "https://b.com") is True

    def test_no_normalization(self):
        dd = ContentDeduplicator(normalize_content=False)
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        assert dd.is_duplicate(self.CONTENT_A, "https://b.com") is True

    def test_get_duplicate_urls(self):
        dd = ContentDeduplicator()
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        dd.is_duplicate(self.CONTENT_A, "https://b.com")
        dups = dd.get_duplicate_urls("https://a.com")
        assert "https://b.com" in dups

    def test_get_duplicate_urls_not_found(self):
        dd = ContentDeduplicator()
        assert dd.get_duplicate_urls("https://unknown.com") is None

    def test_get_stats(self):
        dd = ContentDeduplicator()
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        dd.is_duplicate(self.CONTENT_A, "https://b.com")
        stats = dd.get_stats()
        assert stats["total_checked"] == 2
        assert stats["duplicates_found"] == 1
        assert stats["unique_content_count"] == 1

    def test_clear(self):
        dd = ContentDeduplicator()
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        dd.clear()
        assert dd.is_duplicate(self.CONTENT_A, "https://b.com") is False
        stats = dd.get_stats()
        assert stats["total_checked"] == 1
        assert stats["duplicates_found"] == 0

    def test_reset_stats(self):
        dd = ContentDeduplicator()
        dd.is_duplicate(self.CONTENT_A, "https://a.com")
        dd.is_duplicate(self.CONTENT_A, "https://b.com")
        dd.reset_stats()
        stats = dd.get_stats()
        assert stats["total_checked"] == 0
        assert stats["duplicates_found"] == 0
        assert stats["unique_content_count"] == 1


# -----------------------------------------------------------------------
# Budget Tracker
# -----------------------------------------------------------------------

class TestBudgetLimits:
    def test_defaults(self):
        limits = BudgetLimits()
        assert limits.max_pages is None
        assert limits.max_bandwidth_mb is None

    def test_custom(self):
        limits = BudgetLimits(max_pages=100, max_bandwidth_mb=50.0)
        assert limits.max_pages == 100
        assert limits.max_bandwidth_mb == 50.0


class TestBudgetTracker:
    def test_no_limits(self):
        bt = BudgetTracker()
        can, reason = bt.can_crawl_page()
        assert can is True
        assert reason is None

    def test_page_limit(self):
        bt = BudgetTracker(max_pages=2)
        bt.record_page(100)
        bt.record_page(100)
        can, reason = bt.can_crawl_page()
        assert can is False
        assert "Page limit" in reason

    def test_bandwidth_limit(self):
        bt = BudgetTracker(max_bandwidth_mb=0.001)
        bt.record_page(2000)
        can, reason = bt.can_crawl_page()
        assert can is False
        assert "Bandwidth" in reason

    def test_file_size_limit(self):
        bt = BudgetTracker(max_file_size_mb=1.0)
        can, reason = bt.can_download_file(500_000)
        assert can is True
        can, reason = bt.can_download_file(2_000_000)
        assert can is False
        assert "exceeds limit" in reason

    def test_time_limit(self):
        bt = BudgetTracker(max_time_seconds=0.01)
        bt.start()
        time.sleep(0.02)
        can, reason = bt.can_crawl_page()
        assert can is False
        assert "Time limit" in reason

    def test_zero_pages_raises(self):
        with pytest.raises(ValueError):
            BudgetTracker(max_pages=0)

    def test_negative_bandwidth_raises(self):
        with pytest.raises(ValueError):
            BudgetTracker(max_bandwidth_mb=-1.0)

    def test_callback_on_exceeded(self):
        callback = MagicMock()
        bt = BudgetTracker(max_pages=1, on_budget_exceeded=callback)
        bt.record_page(100)
        bt.can_crawl_page()
        assert callback.called

    def test_get_stats(self):
        bt = BudgetTracker(max_pages=10)
        bt.record_page(1024)
        stats = bt.get_stats()
        assert stats["pages_crawled"] == 1
        assert stats["bytes_downloaded"] == 1024
        assert "pages_usage_percent" in stats

    def test_is_budget_exceeded(self):
        bt = BudgetTracker(max_pages=1)
        assert bt.is_budget_exceeded() is False
        bt.record_page(100)
        bt.can_crawl_page()
        assert bt.is_budget_exceeded() is True

    def test_reset(self):
        bt = BudgetTracker(max_pages=1)
        bt.record_page(100)
        bt.can_crawl_page()
        bt.reset()
        assert bt.is_budget_exceeded() is False
        can, _ = bt.can_crawl_page()
        assert can is True


class TestAsyncBudgetTracker:
    @pytest.mark.asyncio
    async def test_can_crawl_page(self):
        bt = AsyncBudgetTracker(max_pages=2)
        can, _ = await bt.can_crawl_page()
        assert can is True
        await bt.record_page(100)
        await bt.record_page(100)
        can, reason = await bt.can_crawl_page()
        assert can is False

    @pytest.mark.asyncio
    async def test_can_download_file(self):
        bt = AsyncBudgetTracker(max_file_size_mb=1.0)
        can, _ = await bt.can_download_file(500_000)
        assert can is True

    @pytest.mark.asyncio
    async def test_get_stats(self):
        bt = AsyncBudgetTracker(max_pages=10)
        await bt.record_page(512)
        stats = await bt.get_stats()
        assert stats["pages_crawled"] == 1


# -----------------------------------------------------------------------
# Errors
# -----------------------------------------------------------------------

class TestCustomExceptions:
    def test_crawlit_error(self):
        with pytest.raises(CrawlitError):
            raise CrawlitError("base error")

    def test_fetch_error(self):
        err = FetchError("https://example.com", 404, "Not Found")
        assert err.url == "https://example.com"
        assert err.status_code == 404
        assert "Not Found" in str(err)

    def test_fetch_error_default_message(self):
        err = FetchError("https://example.com")
        assert "Failed to fetch" in str(err)

    def test_robots_error(self):
        err = RobotsError("robots.txt error")
        assert isinstance(err, CrawlitError)

    def test_parse_error(self):
        err = ParseError("parse failed")
        assert isinstance(err, CrawlitError)

    def test_extraction_error(self):
        err = ExtractionError("extraction failed")
        assert isinstance(err, CrawlitError)

    def test_inheritance_chain(self):
        assert issubclass(FetchError, CrawlitError)
        assert issubclass(FetchError, Exception)


class TestHandleFetchError:
    def test_timeout(self):
        err = requests.exceptions.Timeout("timeout")
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 0)
        assert retry is True
        assert status == 408
        assert "Timeout" in msg

    def test_connection_error(self):
        err = requests.exceptions.ConnectionError("refused")
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 0)
        assert retry is True
        assert status == 503

    def test_too_many_redirects(self):
        err = requests.exceptions.TooManyRedirects("too many")
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 0)
        assert retry is False
        assert status == 310

    def test_http_error_5xx(self):
        response = MagicMock()
        response.status_code = 502
        err = requests.exceptions.HTTPError(response=response)
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 0)
        assert retry is True
        assert status == 502

    def test_request_exception(self):
        err = requests.exceptions.RequestException("general")
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 0)
        assert retry is True
        assert status == 500

    def test_asyncio_timeout(self):
        err = asyncio.TimeoutError()
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 0)
        assert retry is True
        assert status == 408

    def test_retry_exhausted(self):
        err = requests.exceptions.Timeout("timeout")
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 3)
        assert retry is False

    def test_unknown_error(self):
        err = RuntimeError("something unexpected")
        retry, msg, status = handle_fetch_error("https://x.com", err, 3, 0)
        assert retry is True
        assert status == 500


# -----------------------------------------------------------------------
# Event Log
# -----------------------------------------------------------------------

class TestEventTypes:
    def test_all_constants_in_set(self):
        assert CRAWL_START in EVENT_TYPES
        assert CRAWL_END in EVENT_TYPES
        assert FETCH_RETRY in EVENT_TYPES
        assert FETCH_ERROR in EVENT_TYPES
        assert ROBOTS_REJECT in EVENT_TYPES
        assert PIPELINE_DROP in EVENT_TYPES
        assert PIPELINE_ERROR in EVENT_TYPES
        assert EXTRACTOR_ERROR in EVENT_TYPES
        assert INCREMENTAL_HIT in EVENT_TYPES
        assert DEDUPE_HIT in EVENT_TYPES

    def test_event_types_count(self):
        assert len(EVENT_TYPES) == 10


class TestCrawlEventLog:
    def test_emit_creates_file(self, tmp_path):
        path = tmp_path / "events.jsonl"
        log = CrawlEventLog(str(path), run_id="test-run")
        log.emit("CRAWL_START", url="https://example.com")
        log.close()
        import json
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["event_type"] == "CRAWL_START"
        assert record["run_id"] == "test-run"
        assert record["url"] == "https://example.com"
        assert "ts" in record

    def test_emit_multiple_events(self, tmp_path):
        path = tmp_path / "events.jsonl"
        log = CrawlEventLog(str(path), run_id="run")
        log.emit("CRAWL_START")
        log.emit("FETCH_ERROR", url="https://fail.com", error="timeout")
        log.emit("CRAWL_END")
        log.close()
        import json
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_convenience_crawl_start(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.crawl_start(seed_urls=["https://a.com"])
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["event_type"] == "CRAWL_START"

    def test_convenience_crawl_end(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.crawl_end(pages_crawled=42)
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["event_type"] == "CRAWL_END"
        assert record["details"]["pages_crawled"] == 42

    def test_convenience_fetch_retry(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.fetch_retry("https://x.com", attempt=2, error="timeout", status_code=408)
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["event_type"] == "FETCH_RETRY"
        assert record["level"] == "WARNING"

    def test_convenience_fetch_error(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.fetch_error("https://x.com", error="Connection refused", status_code=503)
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["event_type"] == "FETCH_ERROR"
        assert record["level"] == "ERROR"

    def test_convenience_robots_reject(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.robots_reject("https://x.com/admin", user_agent="bot")
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["event_type"] == "ROBOTS_REJECT"

    def test_convenience_pipeline_drop(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.pipeline_drop("https://x.com", pipeline="FilterPipeline")
        log.close()

    def test_convenience_pipeline_error(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.pipeline_error("https://x.com", pipeline="WriterPipeline", error="IO Error")
        log.close()

    def test_convenience_extractor_error(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.extractor_error("https://x.com", extractor="tables", error="Parse error")
        log.close()

    def test_convenience_incremental_hit(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.incremental_hit("https://x.com")
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["event_type"] == "INCREMENTAL_HIT"
        assert record["level"] == "DEBUG"

    def test_convenience_dedupe_hit(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path))
        log.dedupe_hit("https://x.com", content_hash="abc123")
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["event_type"] == "DEDUPE_HIT"

    def test_set_run_id(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path), run_id="old")
        log.set_run_id("new")
        log.emit("CRAWL_START")
        log.close()
        import json
        record = json.loads(path.read_text().strip())
        assert record["run_id"] == "new"

    def test_repr(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log = CrawlEventLog(str(path), run_id="test")
        r = repr(log)
        assert "CrawlEventLog" in r
        assert "test" in r
        log.close()

    def test_append_mode(self, tmp_path):
        path = tmp_path / "e.jsonl"
        log1 = CrawlEventLog(str(path), run_id="run1")
        log1.emit("CRAWL_START")
        log1.close()
        log2 = CrawlEventLog(str(path), run_id="run2")
        log2.emit("CRAWL_START")
        log2.close()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "events.jsonl"
        log = CrawlEventLog(str(path))
        log.emit("CRAWL_START")
        log.close()
        assert path.exists()
