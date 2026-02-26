#!/usr/bin/env python3
"""
page_artifact.py - Stable, versioned crawl result model.

Replaces ad-hoc result dicts with a consistent PageArtifact dataclass that
every engine, extractor, and pipeline works with.
"""

import dataclasses
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1"


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
    errors : list[str]
        Non-fatal error messages encountered during processing.
    crawl : CrawlMeta
        Graph / navigation context (depth, discovered_from, …).
    """

    schema_version: str = SCHEMA_VERSION
    url: str = ""
    fetched_at: Optional[datetime] = None
    http: HTTPInfo = dataclasses.field(default_factory=HTTPInfo)
    content: ContentInfo = dataclasses.field(default_factory=ContentInfo)
    links: List[str] = dataclasses.field(default_factory=list)
    extracted: Dict[str, Any] = dataclasses.field(default_factory=dict)
    downloads: List[DownloadRecord] = dataclasses.field(default_factory=list)
    errors: List[str] = dataclasses.field(default_factory=list)
    crawl: CrawlMeta = dataclasses.field(default_factory=CrawlMeta)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dictionary."""

        def _convert(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
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
            artifact.errors.append(str(result["error"]))

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
