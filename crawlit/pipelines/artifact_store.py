#!/usr/bin/env python3
"""
artifact_store.py - Complete, contract-defined artifact store pipeline.

Enforces the canonical output layout used by the finance crawler and any other
downstream consumer that reads crawlit output::

    <store_dir>/
        run.json          — CrawlJob metadata + SHA-256 of config snapshot
        artifacts.jsonl   — one PageArtifact JSON object per line
        blobs/
            html/<sha[:2]>/<sha>.html   — raw HTML blobs (content-addressed)
            pdf/<sha[:2]>/<sha>.pdf     — raw PDF blobs  (content-addressed)
        edges.jsonl       — site-graph navigation edges (from→to per line)

The layout is fixed and documented so that downstream tools (Spark jobs,
DuckDB queries, pandas pipelines, …) can rely on it without inspecting the
crawler code.

Usage::

    from crawlit.pipelines.artifact_store import ArtifactStore
    from crawlit import Crawler

    crawler = Crawler(
        "https://example.com",
        pipelines=[ArtifactStore("./runs/2026-02-26", job=crawler.job)],
    )

Note: pass ``job=crawler.job`` *after* constructing the Crawler so that
``run_id`` and ``seed_urls`` are already populated.  Alternatively call
:meth:`write_run_manifest` manually once the job is ready.
"""

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Optional, Any

from ..interfaces import Pipeline
from ..models.page_artifact import PageArtifact, CrawlJob
from .blob_store import BlobStore

logger = logging.getLogger(__name__)


class ArtifactStore(Pipeline):
    """
    Single pipeline stage that implements the full artifact store contract.

    Parameters
    ----------
    store_dir : str | Path
        Root output directory.  Created automatically.
    job : CrawlJob | None
        When provided the run manifest (``run.json``) is written immediately.
        You can also call :meth:`write_run_manifest` later.
    write_blobs : bool
        Save raw HTML / PDF content to the ``blobs/`` sub-tree.
        Defaults to ``True``.
    write_edges : bool
        Append navigation edges to ``edges.jsonl``.
        Defaults to ``True``.
    """

    #: Relative path names (public contract — do not change without a version bump)
    RUN_MANIFEST  = "run.json"
    ARTIFACTS_LOG = "artifacts.jsonl"
    EDGES_LOG     = "edges.jsonl"
    BLOBS_DIR     = "blobs"

    #: ``events.jsonl`` is part of the layout contract.
    EVENTS_LOG = "events.jsonl"

    def __init__(
        self,
        store_dir: "str | Path",
        job: Optional[CrawlJob] = None,
        write_blobs: bool = True,
        write_edges: bool = True,
        write_events: bool = True,
        hash_store=None,
    ) -> None:
        self._root = Path(store_dir)
        self._root.mkdir(parents=True, exist_ok=True)

        self._write_blobs = write_blobs
        self._write_edges = write_edges
        self._lock = threading.Lock()

        # Delegate blob writing to BlobStore (single implementation)
        self._blob_store: Optional[BlobStore] = None
        if write_blobs:
            self._blob_store = BlobStore(
                self._root / self.BLOBS_DIR, hash_store=hash_store
            )

        self._artifacts_fh = (self._root / self.ARTIFACTS_LOG).open(
            "a", encoding="utf-8"
        )
        self._edges_fh = (
            (self._root / self.EDGES_LOG).open("a", encoding="utf-8")
            if write_edges
            else None
        )

        # Auto-create a CrawlEventLog bound to this store directory
        self.event_log: Optional[Any] = None
        if write_events:
            from ..utils.event_log import CrawlEventLog
            self.event_log = CrawlEventLog(
                path=self._root / self.EVENTS_LOG,
                run_id=job.run_id if job else None,
            )

        if job is not None:
            self.write_run_manifest(job)

    # ------------------------------------------------------------------
    # Pipeline interface
    # ------------------------------------------------------------------

    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Write artifact to all configured outputs and return it unchanged."""
        if self._blob_store is not None:
            self._blob_store.process(artifact)
        self._append_artifact(artifact)
        if self._write_edges:
            self._append_edge(artifact)
        return artifact

    # ------------------------------------------------------------------
    # Run manifest
    # ------------------------------------------------------------------

    def write_run_manifest(self, job: CrawlJob) -> None:
        """
        Write ``run.json`` with job metadata and a short config snapshot hash.

        The ``config_snapshot_sha256`` field is a 16-character prefix of the
        SHA-256 of the JSON-serialised ``config_snapshot`` dict.  Downstream
        tools can compare this value to detect configuration drift between runs
        without comparing the full snapshot.

        Safe to call multiple times (overwrites the previous manifest).
        """
        data = job.to_dict()
        snapshot_str = json.dumps(data.get("config_snapshot", {}), sort_keys=True)
        data["config_snapshot_sha256"] = hashlib.sha256(
            snapshot_str.encode()
        ).hexdigest()[:16]
        data["store_layout_version"] = "1"
        data["outputs"] = {
            "artifacts": self.ARTIFACTS_LOG,
            "blobs": self.BLOBS_DIR if self._write_blobs else None,
            "edges": self.EDGES_LOG if self._write_edges else None,
            "events": self.EVENTS_LOG if self.event_log is not None else None,
        }
        manifest_path = self._root / self.RUN_MANIFEST
        with self._lock:
            manifest_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        logger.debug(f"ArtifactStore: wrote {manifest_path}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_artifact(self, artifact: PageArtifact) -> None:
        line = json.dumps(artifact.to_dict(), ensure_ascii=False)
        with self._lock:
            self._artifacts_fh.write(line + "\n")
            self._artifacts_fh.flush()

    def _append_edge(self, artifact: PageArtifact) -> None:
        if not artifact.crawl.discovered_from:
            return  # seed pages have no incoming edge
        edge = {
            "from_url": artifact.crawl.discovered_from,
            "to_url": artifact.url,
            "depth": artifact.crawl.depth,
            "method": artifact.crawl.discovery_method,
            "run_id": artifact.crawl.run_id,
            "source_type": artifact.source.type,
            "site": artifact.source.site,
        }
        line = json.dumps(edge, ensure_ascii=False)
        with self._lock:
            self._edges_fh.write(line + "\n")
            self._edges_fh.flush()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush and close all open file handles."""
        with self._lock:
            if self._artifacts_fh and not self._artifacts_fh.closed:
                self._artifacts_fh.close()
            if self._edges_fh and not self._edges_fh.closed:
                self._edges_fh.close()
        if self.event_log is not None:
            try:
                self.event_log.close()
            except Exception:
                pass

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return (
            f"ArtifactStore(store_dir={str(self._root)!r}, "
            f"blobs={self._write_blobs}, edges={self._write_edges})"
        )
