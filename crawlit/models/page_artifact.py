#!/usr/bin/env python3
"""
page_artifact.py - Stable, versioned crawl result model.

Replaces ad-hoc result dicts with a consistent PageArtifact dataclass that
every engine, extractor, and pipeline works with.
"""

import dataclasses
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

SCHEMA_VERSION = "1"

# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

#: Valid error codes used in :class:`CrawlError`.
ERROR_CODES = {
    "FETCH_ERROR",    # Network / connection failure
    "HTTP_ERROR",     # Non-success HTTP status (4xx/5xx other than 304)
    "TIMEOUT",        # Request timed out
    "PARSE_ERROR",    # HTML / XML parsing failure
    "EXTRACTOR_ERROR",# Plugin extractor raised an exception
    "PIPELINE_ERROR", # Pipeline stage raised an exception
    "PDF_ERROR",      # PDF extraction failure
    "INCREMENTAL",    # 304 Not Modified (informational, not a real error)
    "UNKNOWN",        # Catch-all for unclassified errors
}


@dataclasses.dataclass
class CrawlError:
    """
    Structured error record attached to a :class:`PageArtifact`.

    Replaces bare string error messages with a typed, queryable object.

    Parameters
    ----------
    code : str
        One of the canonical :data:`ERROR_CODES` strings.
    message : str
        Human-readable description of the problem.
    source : str | None
        Component that raised the error (extractor name, pipeline class, "engine").
    http_status : int | None
        HTTP status code when relevant.
    """

    code: str
    message: str
    source: Optional[str] = None
    http_status: Optional[int] = None

    def __str__(self) -> str:
        parts = [f"[{self.code}]"]
        if self.source:
            parts.append(f"({self.source})")
        parts.append(self.message)
        return " ".join(parts)

    @classmethod
    def fetch(cls, message: str, http_status: Optional[int] = None) -> "CrawlError":
        """Convenience constructor for fetch / HTTP errors."""
        code = "HTTP_ERROR" if http_status else "FETCH_ERROR"
        return cls(code=code, message=message, source="engine", http_status=http_status)

    @classmethod
    def extractor(cls, name: str, message: str) -> "CrawlError":
        """Convenience constructor for extractor errors."""
        return cls(code="EXTRACTOR_ERROR", message=message, source=name)

    @classmethod
    def pipeline(cls, name: str, message: str) -> "CrawlError":
        """Convenience constructor for pipeline errors."""
        return cls(code="PIPELINE_ERROR", message=message, source=name)

    @classmethod
    def pdf(cls, message: str) -> "CrawlError":
        """Convenience constructor for PDF extraction errors."""
        return cls(code="PDF_ERROR", message=message, source="pdf_extractor")

    @classmethod
    def not_modified(cls) -> "CrawlError":
        """304 Not Modified — content unchanged since last crawl."""
        return cls(code="INCREMENTAL", message="304 Not Modified", http_status=304)


# ---------------------------------------------------------------------------
# Job-level metadata
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class CrawlJob:
    """
    Run-level metadata shared across all artifacts from a single crawl job.

    Attach an instance to :class:`~crawlit.crawler.engine.Crawler` via the
    ``run_id=`` parameter (or it will be auto-generated).

    Fields
    ------
    run_id : str
        UUID-based identifier for this crawl run.  Stable across restarts when
        you pass the same string.
    started_at : datetime | None
        UTC timestamp when the crawl was started.
    seed_urls : list[str]
        Starting URL(s) provided to the crawler.
    config_snapshot : dict
        JSON-serialisable snapshot of the crawler configuration for
        reproducibility.
    """

    run_id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    started_at: Optional[datetime] = None
    seed_urls: List[str] = dataclasses.field(default_factory=list)
    config_snapshot: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "seed_urls": self.seed_urls,
            "config_snapshot": self.config_snapshot,
        }


# ---------------------------------------------------------------------------
# Per-page sub-records
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class HTTPInfo:
    """HTTP response metadata."""

    status: Optional[int] = None
    headers: Dict[str, str] = dataclasses.field(default_factory=dict)
    content_type: Optional[str] = None
    redirected_from: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    cache_control: Optional[str] = None


@dataclasses.dataclass
class ContentInfo:
    """Page content metadata and optional storage references."""

    raw_html: Optional[str] = None
    text: Optional[str] = None
    blob_path: Optional[str] = None
    blob_sha256: Optional[str] = None
    encoding: Optional[str] = None
    size_bytes: int = 0


@dataclasses.dataclass
class DownloadRecord:
    """Record of a file downloaded during the crawl."""

    url: str = ""
    bytes_downloaded: int = 0
    sha256: Optional[str] = None
    saved_path: Optional[str] = None
    parse_status: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None


@dataclasses.dataclass
class CrawlMeta:
    """Crawl graph / navigation context for a page."""

    depth: int = 0
    discovered_from: Optional[str] = None
    # "seed" | "link" | "sitemap"
    discovery_method: Optional[str] = None
    # Inherited from engine's CrawlJob
    run_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level artifact
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class PageArtifact:
    """
    A stable, versioned record of one crawled page.

    Fields
    ------
    schema_version : str
        Version of this schema for forward-compatibility checks.
    url : str
        Canonical URL of the page.
    fetched_at : datetime | None
        UTC timestamp when the page was fetched.
    http : HTTPInfo
        HTTP response metadata (status, headers, content-type, ETags, …).
    content : ContentInfo
        Content storage metadata and optional inline raw HTML.
    links : list[str]
        Outbound links discovered on this page.
    extracted : dict[str, Any]
        Extractor payloads keyed by extractor name (e.g. "pdf", "tables",
        "js_embedded_data", …).
    downloads : list[DownloadRecord]
        Files downloaded while processing this page.
    errors : list[CrawlError]
        Structured error records for non-fatal problems encountered during
        processing.  Use :meth:`add_error` to append.
    crawl : CrawlMeta
        Graph / navigation context (depth, discovered_from, run_id, …).
    """

    schema_version: str = SCHEMA_VERSION
    url: str = ""
    fetched_at: Optional[datetime] = None
    http: HTTPInfo = dataclasses.field(default_factory=HTTPInfo)
    content: ContentInfo = dataclasses.field(default_factory=ContentInfo)
    links: List[str] = dataclasses.field(default_factory=list)
    extracted: Dict[str, Any] = dataclasses.field(default_factory=dict)
    downloads: List[DownloadRecord] = dataclasses.field(default_factory=list)
    errors: List[CrawlError] = dataclasses.field(default_factory=list)
    crawl: CrawlMeta = dataclasses.field(default_factory=CrawlMeta)

    # ------------------------------------------------------------------
    # Error helpers
    # ------------------------------------------------------------------

    def add_error(self, error: Union["CrawlError", str], code: str = "UNKNOWN",
                  source: Optional[str] = None) -> None:
        """
        Append a structured error.

        Accepts either a :class:`CrawlError` instance (preferred) or a plain
        string for backwards compatibility.

            artifact.add_error(CrawlError.fetch("Connection refused", 503))
            artifact.add_error("Something went wrong")   # auto-wrapped
        """
        if isinstance(error, CrawlError):
            self.errors.append(error)
        else:
            self.errors.append(CrawlError(code=code, message=str(error), source=source))

    # ------------------------------------------------------------------
    # Copy helper (safe pipeline chaining)
    # ------------------------------------------------------------------

    def copy(self) -> "PageArtifact":
        """
        Return a shallow copy with independent mutable containers.

        ``http``, ``content``, and ``crawl`` sub-objects are shared (they are
        treated as immutable once set by the engine); ``links``, ``extracted``,
        ``downloads``, and ``errors`` are copied so that one pipeline stage
        cannot corrupt a later stage's view.
        """
        return PageArtifact(
            schema_version=self.schema_version,
            url=self.url,
            fetched_at=self.fetched_at,
            http=self.http,
            content=self.content,
            links=list(self.links),
            extracted=dict(self.extracted),
            downloads=list(self.downloads),
            errors=list(self.errors),
            crawl=self.crawl,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dictionary."""

        def _convert(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, CrawlError):
                d: Dict[str, Any] = {"code": obj.code, "message": obj.message}
                if obj.source is not None:
                    d["source"] = obj.source
                if obj.http_status is not None:
                    d["http_status"] = obj.http_status
                return d
            if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                return {k: _convert(v) for k, v in dataclasses.asdict(obj).items()}
            if isinstance(obj, list):
                return [_convert(i) for i in obj]
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            return obj

        return _convert(dataclasses.asdict(self))

    # ------------------------------------------------------------------
    # Backward-compatibility bridge
    # ------------------------------------------------------------------

    @classmethod
    def from_legacy_result(cls, url: str, result: Dict[str, Any]) -> "PageArtifact":
        """
        Build a PageArtifact from a legacy crawl result dict.

        This enables gradual migration: callers that still receive the old
        ``{url: {...}}`` result dict can wrap it in a PageArtifact for use
        with pipelines and extractors.
        """
        artifact = cls(url=url)
        artifact.http = HTTPInfo(
            status=result.get("status"),
            headers=result.get("headers") or {},
            content_type=result.get("content_type"),
        )
        artifact.content = ContentInfo(
            raw_html=result.get("html_content"),
        )
        artifact.links = list(result.get("links") or [])
        artifact.crawl = CrawlMeta(depth=result.get("depth", 0))
        if result.get("error"):
            artifact.add_error(str(result["error"]))

        # Lift legacy extraction fields into the extracted dict
        for key in (
            "title",
            "meta_description",
            "meta_keywords",
            "canonical_url",
            "language",
            "headings",
            "images",
            "images_with_context",
            "keywords",
            "keyword_scores",
            "keyphrases",
            "tables",
            "forms",
            "structured_data",
            "page_type",
            "last_modified",
            "pdf_data",
        ):
            if result.get(key) is not None:
                artifact.extracted[key] = result[key]
        return artifact
