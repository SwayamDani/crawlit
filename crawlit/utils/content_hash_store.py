#!/usr/bin/env python3
"""
content_hash_store.py - Persistent, cross-run content deduplication using SQLite.

The in-memory :class:`~crawlit.utils.deduplication.ContentDeduplicator` cannot
detect duplicates across separate crawler invocations.  This module provides a
lightweight SQLite-backed store that persists content hashes between runs.

Usage::

    from crawlit.utils.content_hash_store import ContentHashStore

    store = ContentHashStore("./runs/dedup.db")

    sha, is_new = store.record(url, html_content, run_id=job.run_id)
    if not is_new:
        print("Duplicate — blob already at", store.get_blob_path(html_content))

Wire into :class:`~crawlit.pipelines.blob_store.BlobStore`::

    BlobStore(blobs_dir="./blobs", hash_store=ContentHashStore("./dedup.db"))
"""

import hashlib
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS content_hashes (
    sha256           TEXT PRIMARY KEY,
    url              TEXT NOT NULL,
    blob_path        TEXT,
    first_seen_at    TEXT NOT NULL,
    run_id           TEXT
);
CREATE INDEX IF NOT EXISTS idx_url ON content_hashes (url);
CREATE INDEX IF NOT EXISTS idx_run  ON content_hashes (run_id);
"""


class ContentHashStore:
    """
    SQLite-backed store for cross-run content deduplication.

    Every unique piece of content is recorded by its SHA-256 hash together
    with the URL where it was first seen, the path of any saved blob, and
    the run-ID of the crawl that first encountered it.

    Thread-safe: a single :class:`threading.Lock` serialises all writes.

    Parameters
    ----------
    db_path : str | Path
        Path to the SQLite database file.  Created automatically if absent.
    """

    def __init__(self, db_path: "str | Path") -> None:
        self._db_path = str(Path(db_path))
        self._lock = threading.Lock()
        self._setup_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def hash_content(content: str) -> str:
        """Return the SHA-256 hex digest of *content* (UTF-8 encoded)."""
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    def is_duplicate(self, content: str) -> bool:
        """Return ``True`` if *content* has been seen in any previous run."""
        sha = self.hash_content(content)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM content_hashes WHERE sha256 = ?", (sha,)
            ).fetchone()
        return row is not None

    def record(
        self,
        url: str,
        content: str,
        blob_path: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """
        Record the content hash for *url*.

        Returns ``(sha256, is_new)`` where *is_new* is ``True`` when this is
        the first time the hash has been seen.  If the hash already exists the
        row is left unchanged (first-seen semantics).

        Parameters
        ----------
        url : str
            Canonical URL of the page.
        content : str
            Raw HTML or text body to hash.
        blob_path : str | None
            Path of the saved blob (populated by :class:`BlobStore`).
        run_id : str | None
            Current crawl run identifier.
        """
        sha = self.hash_content(content)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT sha256 FROM content_hashes WHERE sha256 = ?", (sha,)
            ).fetchone()
            if existing:
                return sha, False
            conn.execute(
                """INSERT INTO content_hashes (sha256, url, blob_path, first_seen_at, run_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (sha, url, blob_path, now, run_id),
            )
            conn.commit()
        return sha, True

    def update_blob_path(self, sha256: str, blob_path: str) -> None:
        """Update the ``blob_path`` for an existing hash entry."""
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE content_hashes SET blob_path = ? WHERE sha256 = ?",
                (blob_path, sha256),
            )
            conn.commit()

    def get_blob_path(self, content: str) -> Optional[str]:
        """
        Return the blob path recorded for *content*, or ``None`` if unknown.

        Useful to avoid re-writing a blob when the content was seen in a
        previous run.
        """
        sha = self.hash_content(content)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT blob_path FROM content_hashes WHERE sha256 = ?", (sha,)
            ).fetchone()
        return row[0] if row else None

    def stats(self) -> dict:
        """Return a summary dict: total hashes, unique runs, date range."""
        with self._lock, self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM content_hashes").fetchone()[0]
            runs = conn.execute(
                "SELECT COUNT(DISTINCT run_id) FROM content_hashes"
            ).fetchone()[0]
            earliest = conn.execute(
                "SELECT MIN(first_seen_at) FROM content_hashes"
            ).fetchone()[0]
        return {"total_hashes": total, "unique_runs": runs, "earliest": earliest}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _setup_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        # check_same_thread=False is safe because we serialise via self._lock.
        return sqlite3.connect(self._db_path, check_same_thread=False)
