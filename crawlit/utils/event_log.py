#!/usr/bin/env python3
"""
event_log.py - Run-scoped operational event log.

Writes a lightweight ``events.jsonl`` stream that records every operationally
significant event during a crawl run.  One JSON object per line::

    {"run_id": "abc", "ts": "…", "level": "INFO",
     "event_type": "FETCH_RETRY", "url": "https://…", "details": {…}}

Event types
-----------
CRAWL_START       — job began (emitted once by the engine)
CRAWL_END         — job finished (emitted once by the engine)
FETCH_RETRY       — a fetch failed and will be retried
FETCH_ERROR       — final fetch failure after all retries exhausted
ROBOTS_REJECT     — URL disallowed by robots.txt
PIPELINE_DROP     — a pipeline stage returned None (artifact filtered out)
PIPELINE_ERROR    — a pipeline stage raised an exception
EXTRACTOR_ERROR   — an extractor plugin raised an exception
INCREMENTAL_HIT   — server returned 304 Not Modified
DEDUPE_HIT        — content body matched a previously seen hash

Usage::

    from crawlit.utils.event_log import CrawlEventLog

    log = CrawlEventLog("./runs/2026/events.jsonl", run_id="abc123")
    log.emit("ROBOTS_REJECT", url="https://example.com/private",
             details={"user_agent": "crawlit/1.0"})

Inject into the crawler::

    crawler = Crawler("https://example.com", event_log=log)

The :class:`~crawlit.pipelines.ArtifactStore` automatically creates an
``events.jsonl`` inside its store directory when you pass ``event_log=True``.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public event-type constants
# ---------------------------------------------------------------------------

CRAWL_START     = "CRAWL_START"
CRAWL_END       = "CRAWL_END"
FETCH_RETRY     = "FETCH_RETRY"
FETCH_ERROR     = "FETCH_ERROR"
ROBOTS_REJECT   = "ROBOTS_REJECT"
PIPELINE_DROP   = "PIPELINE_DROP"
PIPELINE_ERROR  = "PIPELINE_ERROR"
EXTRACTOR_ERROR = "EXTRACTOR_ERROR"
INCREMENTAL_HIT = "INCREMENTAL_HIT"
DEDUPE_HIT      = "DEDUPE_HIT"

#: All valid event types (for validation / documentation).
EVENT_TYPES = {
    CRAWL_START,
    CRAWL_END,
    FETCH_RETRY,
    FETCH_ERROR,
    ROBOTS_REJECT,
    PIPELINE_DROP,
    PIPELINE_ERROR,
    EXTRACTOR_ERROR,
    INCREMENTAL_HIT,
    DEDUPE_HIT,
}


class CrawlEventLog:
    """
    Thread-safe, append-only JSONL event log for a single crawl run.

    Parameters
    ----------
    path : str | Path
        Destination file path.  Parent directories are created automatically.
        The file is opened in append mode so multiple runs can share a file
        (distinguished by ``run_id``).
    run_id : str | None
        Crawl run identifier stamped on every event.  Pass the same value as
        ``Crawler(run_id=…)`` so events can be joined with artifact records.
    """

    def __init__(self, path: "str | Path", run_id: Optional[str] = None) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._lock = threading.Lock()
        self._fh = self._path.open("a", encoding="utf-8")

    # ------------------------------------------------------------------
    # Core emit
    # ------------------------------------------------------------------

    def emit(
        self,
        event_type: str,
        url: str = "",
        level: str = "INFO",
        **details: Any,
    ) -> None:
        """
        Write one event record.

        Parameters
        ----------
        event_type : str
            One of the ``EVENT_TYPES`` constants (e.g. ``FETCH_RETRY``).
        url : str
            The URL the event relates to.
        level : str
            Severity: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``.
        **details
            Arbitrary key-value pairs serialised into the ``details`` object.
            Common keys: ``attempt``, ``error``, ``status_code``,
            ``pipeline``, ``extractor``, ``hash``.
        """
        record: Dict[str, Any] = {
            "run_id": self._run_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event_type": event_type,
            "url": url,
            "details": details if details else {},
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()

    # ------------------------------------------------------------------
    # Convenience methods matching each event type
    # ------------------------------------------------------------------

    def crawl_start(self, seed_urls: list, **details: Any) -> None:
        """Emit ``CRAWL_START``."""
        self.emit(CRAWL_START, url="", seed_urls=seed_urls, **details)

    def crawl_end(self, pages_crawled: int = 0, **details: Any) -> None:
        """Emit ``CRAWL_END``."""
        self.emit(CRAWL_END, url="", pages_crawled=pages_crawled, **details)

    def fetch_retry(self, url: str, attempt: int, error: str,
                    status_code: Optional[int] = None) -> None:
        """Emit ``FETCH_RETRY`` (called inside the fetch retry loop)."""
        self.emit(
            FETCH_RETRY, url=url, level="WARNING",
            attempt=attempt, error=error, status_code=status_code,
        )

    def fetch_error(self, url: str, error: str,
                    status_code: Optional[int] = None) -> None:
        """Emit ``FETCH_ERROR`` (final failure after all retries)."""
        self.emit(
            FETCH_ERROR, url=url, level="ERROR",
            error=error, status_code=status_code,
        )

    def robots_reject(self, url: str, user_agent: str = "") -> None:
        """Emit ``ROBOTS_REJECT``."""
        self.emit(ROBOTS_REJECT, url=url, level="INFO", user_agent=user_agent)

    def pipeline_drop(self, url: str, pipeline: str) -> None:
        """Emit ``PIPELINE_DROP`` when a stage returns ``None``."""
        self.emit(PIPELINE_DROP, url=url, level="INFO", pipeline=pipeline)

    def pipeline_error(self, url: str, pipeline: str, error: str) -> None:
        """Emit ``PIPELINE_ERROR`` when a stage raises an exception."""
        self.emit(PIPELINE_ERROR, url=url, level="WARNING",
                  pipeline=pipeline, error=error)

    def extractor_error(self, url: str, extractor: str, error: str) -> None:
        """Emit ``EXTRACTOR_ERROR``."""
        self.emit(EXTRACTOR_ERROR, url=url, level="WARNING",
                  extractor=extractor, error=error)

    def incremental_hit(self, url: str) -> None:
        """Emit ``INCREMENTAL_HIT`` (304 Not Modified)."""
        self.emit(INCREMENTAL_HIT, url=url, level="DEBUG")

    def dedupe_hit(self, url: str, content_hash: str = "") -> None:
        """Emit ``DEDUPE_HIT`` when duplicate content is detected."""
        self.emit(DEDUPE_HIT, url=url, level="INFO", hash=content_hash)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def set_run_id(self, run_id: str) -> None:
        """Update the run_id stamped on subsequent events."""
        self._run_id = run_id

    def close(self) -> None:
        """Flush and close the underlying file handle."""
        with self._lock:
            if not self._fh.closed:
                self._fh.flush()
                self._fh.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"CrawlEventLog(path={str(self._path)!r}, run_id={self._run_id!r})"
