#!/usr/bin/env python3
"""
edges_writer.py - Pipeline stage: write navigation edges to a JSONL file.

Each line records a directed (from_url → to_url) edge::

    {"from_url": "https://example.com/", "to_url": "https://example.com/about",
     "depth": 1, "method": "link"}

These edges can be used to reconstruct the site graph, analyse crawl coverage,
or feed graph-analysis tools.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional

from ..interfaces import Pipeline
from ..models.page_artifact import PageArtifact

logger = logging.getLogger(__name__)


class EdgesWriter(Pipeline):
    """
    Write ``(discovered_from → url)`` navigation edges to a JSONL file.

    Pages without a ``crawl.discovered_from`` value (seed URLs) produce no
    edge record.

    Parameters
    ----------
    path : str | Path
        Output file path.  Parent directories are created automatically.
    append : bool
        Open in append mode (default: ``True``).
    """

    def __init__(self, path, append: bool = True):
        self._path = Path(path)
        self._append = append
        self._lock = threading.Lock()
        self._fh = None
        self._open()

    def _open(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if self._append else "w"
        self._fh = self._path.open(mode, encoding="utf-8", buffering=1)

    def close(self):
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

    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        if not artifact.crawl.discovered_from:
            return artifact

        edge = {
            "from_url": artifact.crawl.discovered_from,
            "to_url": artifact.url,
            "depth": artifact.crawl.depth,
            "method": artifact.crawl.discovery_method or "link",
        }
        try:
            line = json.dumps(edge, ensure_ascii=False)
            with self._lock:
                if self._fh is None:
                    self._open()
                self._fh.write(line + "\n")
        except Exception as exc:
            logger.warning(f"EdgesWriter failed for {artifact.url}: {exc}")
        return artifact
