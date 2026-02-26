#!/usr/bin/env python3
"""
jsonl_writer.py - Pipeline stage: write one artifact per line to a JSONL file.

Each crawled page produces a single JSON line so the output can be streamed,
processed with ``jq``, imported into BigQuery, etc.

Thread-safe: a per-instance ``threading.Lock`` serialises concurrent writes
when the synchronous engine runs with ``max_workers > 1``.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional

from ..interfaces import Pipeline
from ..models.page_artifact import PageArtifact

logger = logging.getLogger(__name__)


class JSONLWriter(Pipeline):
    """
    Write each :class:`~crawlit.models.PageArtifact` as a JSON line to *path*.

    Parameters
    ----------
    path : str | Path
        Output file path.  Parent directories are created automatically.
    append : bool
        If ``True`` (default) open in append mode so that resuming a crawl
        does not overwrite previous output.
    """

    def __init__(self, path, append: bool = True):
        self._path = Path(path)
        self._append = append
        self._lock = threading.Lock()
        self._fh = None
        self._open()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if self._append else "w"
        self._fh = self._path.open(mode, encoding="utf-8", buffering=1)
        logger.debug(f"JSONLWriter opened {self._path} (mode={mode!r})")

    def close(self):
        """Flush and close the underlying file handle."""
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.flush()
                    self._fh.close()
                finally:
                    self._fh = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Pipeline interface
    # ------------------------------------------------------------------

    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        try:
            line = json.dumps(artifact.to_dict(), ensure_ascii=False, default=str)
            with self._lock:
                if self._fh is None:
                    self._open()
                self._fh.write(line + "\n")
        except Exception as exc:
            logger.warning(f"JSONLWriter failed for {artifact.url}: {exc}")
        return artifact
