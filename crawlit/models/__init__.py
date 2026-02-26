"""crawlit.models - Stable data models for crawl results."""

from .page_artifact import (
    SCHEMA_VERSION,
    PageArtifact,
    HTTPInfo,
    ContentInfo,
    DownloadRecord,
    CrawlMeta,
)

__all__ = [
    "SCHEMA_VERSION",
    "PageArtifact",
    "HTTPInfo",
    "ContentInfo",
    "DownloadRecord",
    "CrawlMeta",
]
