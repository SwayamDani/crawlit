#!/usr/bin/env python3
"""
blob_store.py - Pipeline stage: save raw content blobs to a content-addressed store.

HTML and PDF bytes are saved under::

    <blobs_dir>/html/<sha256[:2]>/<sha256>.html
    <blobs_dir>/pdf/<sha256[:2]>/<sha256>.pdf

The artifact's ``content.blob_path`` and ``content.blob_sha256`` fields are
updated in-place so that downstream stages (e.g. :class:`JSONLWriter`) capture
the paths and checksums.

Cross-run deduplication
-----------------------
Pass a :class:`~crawlit.utils.content_hash_store.ContentHashStore` instance
via ``hash_store=`` to avoid re-writing blobs that were already saved in
a previous crawl run::

    from crawlit.utils.content_hash_store import ContentHashStore
    store = BlobStore("./blobs", hash_store=ContentHashStore("./dedup.db"))
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
    hash_store : ContentHashStore | None
        Optional persistent hash store for cross-run deduplication.  When set,
        blobs whose SHA-256 is already recorded are skipped (no re-write), and
        the artifact's ``content.blob_path`` is populated from the stored path.
    """

    def __init__(self, blobs_dir, hash_store=None):
        self._root = Path(blobs_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "html").mkdir(exist_ok=True)
        (self._root / "pdf").mkdir(exist_ok=True)
        self._lock = threading.Lock()
        self._hash_store = hash_store  # Optional[ContentHashStore]

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

    def _sha256_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _write_file(self, dest: Path, data: bytes) -> bool:
        """Write *data* to *dest*; return True on success."""
        try:
            dest.write_bytes(data)
            return True
        except Exception as exc:
            logger.warning(f"BlobStore write failed ({dest}): {exc}")
            return False

    def _save_html(self, artifact: PageArtifact):
        data = artifact.content.raw_html.encode("utf-8", errors="replace")
        sha = self._sha256_bytes(data)

        # Cross-run dedup: check persistent store first
        if self._hash_store is not None:
            existing_path = self._hash_store.get_blob_path(artifact.content.raw_html)
            if existing_path:
                artifact.content.blob_path = existing_path
                artifact.content.blob_sha256 = sha
                return

        subdir = self._root / "html" / sha[:2]
        with self._lock:
            subdir.mkdir(parents=True, exist_ok=True)
        dest = subdir / f"{sha}.html"
        # Content-addressed: same hash guarantees same content, so
        # unconditional write is safe and avoids TOCTOU race.
        self._write_file(dest, data)

        artifact.content.blob_path = str(dest)
        artifact.content.blob_sha256 = sha

        if self._hash_store is not None:
            self._hash_store.update_blob_path(sha, str(dest))

    def _save_pdf(self, artifact: PageArtifact):
        # raw_html stores the original bytes encoded as latin-1 for PDFs
        data = artifact.content.raw_html.encode("latin-1", errors="replace")
        sha = self._sha256_bytes(data)

        if self._hash_store is not None:
            existing_path = self._hash_store.get_blob_path(artifact.content.raw_html)
            if existing_path:
                artifact.content.blob_path = existing_path
                artifact.content.blob_sha256 = sha
                return

        subdir = self._root / "pdf" / sha[:2]
        with self._lock:
            subdir.mkdir(parents=True, exist_ok=True)
        dest = subdir / f"{sha}.pdf"
        # Content-addressed: same hash guarantees same content, so
        # unconditional write is safe and avoids TOCTOU race.
        self._write_file(dest, data)

        artifact.content.blob_path = str(dest)
        artifact.content.blob_sha256 = sha

        if self._hash_store is not None:
            self._hash_store.update_blob_path(sha, str(dest))
