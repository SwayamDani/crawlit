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

    def __init__(
        self,
        store_dir: "str | Path",
        job: Optional[CrawlJob] = None,
        write_blobs: bool = True,
        write_edges: bool = True,
    ) -> None:
        self._root = Path(store_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        if write_blobs:
            (self._root / self.BLOBS_DIR / "html").mkdir(parents=True, exist_ok=True)
            (self._root / self.BLOBS_DIR / "pdf").mkdir(parents=True, exist_ok=True)

        self._write_blobs = write_blobs
        self._write_edges = write_edges
        self._lock = threading.Lock()

        self._artifacts_fh = (self._root / self.ARTIFACTS_LOG).open(
            "a", encoding="utf-8"
        )
        self._edges_fh = (
            (self._root / self.EDGES_LOG).open("a", encoding="utf-8")
            if write_edges
            else None
        )

        if job is not None:
            self.write_run_manifest(job)

    # ------------------------------------------------------------------
    # Pipeline interface
    # ------------------------------------------------------------------

    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Write artifact to all configured outputs and return it unchanged."""
        self._append_artifact(artifact)
        if self._write_edges:
            self._append_edge(artifact)
        if self._write_blobs:
            self._save_blob(artifact)
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

    def _save_blob(self, artifact: PageArtifact) -> None:
        ct = (artifact.http.content_type or "").lower()
        raw = artifact.content.raw_html
        if not raw:
            return
        if "text/html" in ct:
            self._write_blob(artifact, raw.encode("utf-8", errors="replace"), "html", ".html")
        elif "application/pdf" in ct:
            self._write_blob(artifact, raw.encode("latin-1", errors="replace"), "pdf", ".pdf")

    def _write_blob(
        self, artifact: PageArtifact, data: bytes, subtype: str, ext: str
    ) -> None:
        sha = hashlib.sha256(data).hexdigest()
        subdir = self._root / self.BLOBS_DIR / subtype / sha[:2]
        with self._lock:
            subdir.mkdir(parents=True, exist_ok=True)
        dest = subdir / f"{sha}{ext}"
        if not dest.exists():
            try:
                dest.write_bytes(data)
            except Exception as exc:
                logger.warning(f"ArtifactStore: blob write failed ({dest}): {exc}")
                return
        # Update the artifact's content pointers in-place
        artifact.content.blob_path = str(dest)
        artifact.content.blob_sha256 = sha

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
