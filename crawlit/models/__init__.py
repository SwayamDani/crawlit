"""crawlit.models - Stable data models for crawl results."""

from .page_artifact import (
    SCHEMA_VERSION,
    ERROR_CODES,
    CrawlError,
    CrawlJob,
    PageArtifact,
    HTTPInfo,
    ContentInfo,
    DownloadRecord,
    CrawlMeta,
)

__all__ = [
    "SCHEMA_VERSION",
    "ERROR_CODES",
    "CrawlError",
    "CrawlJob",
    "PageArtifact",
    "HTTPInfo",
    "ContentInfo",
    "DownloadRecord",
    "CrawlMeta",
]
