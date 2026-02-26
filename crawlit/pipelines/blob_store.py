#!/usr/bin/env python3
"""
blob_store.py - Pipeline stage: save raw content blobs to a content-addressed store.

HTML and PDF bytes are saved under::

    <blobs_dir>/html/<sha256[:2]>/<sha256>.html
    <blobs_dir>/pdf/<sha256[:2]>/<sha256>.pdf

The artifact's ``content.blob_path`` and ``content.blob_sha256`` fields are
updated in-place so that downstream stages (e.g. :class:`JSONLWriter`) capture
the paths and checksums.
"""

import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional

from ..interfaces import Pipeline
from ..models.page_artifact import PageArtifact

logger = logging.getLogger(__name__)


class BlobStore(Pipeline):
    """
    Persist raw page content (HTML / PDF) to a content-addressed blob store.

    Parameters
    ----------
    blobs_dir : str | Path
        Root directory for blobs.  Sub-directories ``html/`` and ``pdf/`` are
        created automatically.
    """

    def __init__(self, blobs_dir):
        self._root = Path(blobs_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "html").mkdir(exist_ok=True)
        (self._root / "pdf").mkdir(exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Pipeline interface
    # ------------------------------------------------------------------

    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        content_type = (artifact.http.content_type or "").lower()
        if "text/html" in content_type and artifact.content.raw_html:
            self._save_html(artifact)
        elif "application/pdf" in content_type and artifact.content.raw_html:
            self._save_pdf(artifact)
        return artifact

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sha256_str(self, data: str) -> str:
        return hashlib.sha256(data.encode("utf-8", errors="replace")).hexdigest()

    def _write_file(self, dest: Path, data: bytes) -> bool:
        """Write *data* to *dest*; return True on success."""
        try:
            dest.write_bytes(data)
            return True
        except Exception as exc:
            logger.warning(f"BlobStore write failed ({dest}): {exc}")
            return False

    def _save_html(self, artifact: PageArtifact):
        sha = self._sha256_str(artifact.content.raw_html)
        subdir = self._root / "html" / sha[:2]
        with self._lock:
            subdir.mkdir(parents=True, exist_ok=True)
        dest = subdir / f"{sha}.html"
        if not dest.exists():
            self._write_file(dest, artifact.content.raw_html.encode("utf-8", errors="replace"))
        artifact.content.blob_path = str(dest)
        artifact.content.blob_sha256 = sha

    def _save_pdf(self, artifact: PageArtifact):
        sha = self._sha256_str(artifact.content.raw_html)
        subdir = self._root / "pdf" / sha[:2]
        with self._lock:
            subdir.mkdir(parents=True, exist_ok=True)
        dest = subdir / f"{sha}.pdf"
        if not dest.exists():
            # raw_html stores the original bytes encoded as latin-1 for PDFs
            self._write_file(dest, artifact.content.raw_html.encode("latin-1", errors="replace"))
        artifact.content.blob_path = str(dest)
        artifact.content.blob_sha256 = sha
