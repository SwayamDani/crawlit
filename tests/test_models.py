"""Tests for crawlit.models.page_artifact module."""

import dataclasses
from datetime import datetime, timezone

import pytest

from crawlit.models.page_artifact import (
    SCHEMA_VERSION,
    ERROR_CODES,
    CrawlError,
    CrawlJob,
    HTTPInfo,
    ContentInfo,
    DownloadRecord,
    CrawlMeta,
    ArtifactSource,
    PageArtifact,
)


class TestCrawlError:
    def test_basic_construction(self):
        err = CrawlError(code="FETCH_ERROR", message="Connection refused")
        assert err.code == "FETCH_ERROR"
        assert err.message == "Connection refused"
        assert err.source is None
        assert err.http_status is None

    def test_str_without_source(self):
        err = CrawlError(code="TIMEOUT", message="Timed out")
        assert str(err) == "[TIMEOUT] Timed out"

    def test_str_with_source(self):
        err = CrawlError(code="EXTRACTOR_ERROR", message="Parse failed", source="pdf_extractor")
        assert str(err) == "[EXTRACTOR_ERROR] (pdf_extractor) Parse failed"

    def test_fetch_factory_with_status(self):
        err = CrawlError.fetch("Not Found", http_status=404)
        assert err.code == "HTTP_ERROR"
        assert err.source == "engine"
        assert err.http_status == 404

    def test_fetch_factory_without_status(self):
        err = CrawlError.fetch("Connection refused")
        assert err.code == "FETCH_ERROR"
        assert err.http_status is None

    def test_extractor_factory(self):
        err = CrawlError.extractor("tables", "Invalid HTML")
        assert err.code == "EXTRACTOR_ERROR"
        assert err.source == "tables"
        assert err.message == "Invalid HTML"

    def test_pipeline_factory(self):
        err = CrawlError.pipeline("JSONLWriter", "IO error")
        assert err.code == "PIPELINE_ERROR"
        assert err.source == "JSONLWriter"

    def test_pdf_factory(self):
        err = CrawlError.pdf("Corrupt PDF")
        assert err.code == "PDF_ERROR"
        assert err.source == "pdf_extractor"

    def test_not_modified_factory(self):
        err = CrawlError.not_modified()
        assert err.code == "INCREMENTAL"
        assert err.http_status == 304
        assert "304" in err.message


class TestErrorCodes:
    def test_all_expected_codes(self):
        expected = {
            "FETCH_ERROR", "HTTP_ERROR", "TIMEOUT", "PARSE_ERROR",
            "EXTRACTOR_ERROR", "PIPELINE_ERROR", "PDF_ERROR",
            "INCREMENTAL", "UNKNOWN",
        }
        assert expected == ERROR_CODES


class TestCrawlJob:
    def test_auto_run_id(self):
        job = CrawlJob()
        assert job.run_id
        assert len(job.run_id) > 0

    def test_custom_values(self):
        job = CrawlJob(
            run_id="test-run",
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            seed_urls=["https://example.com"],
            config_snapshot={"max_depth": 3},
        )
        assert job.run_id == "test-run"
        assert job.seed_urls == ["https://example.com"]

    def test_to_dict(self):
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job = CrawlJob(run_id="run-1", started_at=now, seed_urls=["https://a.com"])
        d = job.to_dict()
        assert d["run_id"] == "run-1"
        assert d["started_at"] == now.isoformat()
        assert d["seed_urls"] == ["https://a.com"]

    def test_to_dict_none_started_at(self):
        job = CrawlJob(run_id="x")
        d = job.to_dict()
        assert d["started_at"] is None

    def test_unique_run_ids(self):
        j1, j2 = CrawlJob(), CrawlJob()
        assert j1.run_id != j2.run_id


class TestHTTPInfo:
    def test_defaults(self):
        info = HTTPInfo()
        assert info.status is None
        assert info.headers == {}
        assert info.content_type is None
        assert info.elapsed_ms is None
        assert info.response_bytes is None

    def test_custom(self):
        info = HTTPInfo(status=200, content_type="text/html", elapsed_ms=150.5)
        assert info.status == 200
        assert info.elapsed_ms == 150.5


class TestContentInfo:
    def test_defaults(self):
        info = ContentInfo()
        assert info.raw_html is None
        assert info.size_bytes == 0

    def test_with_content(self):
        info = ContentInfo(raw_html="<html></html>", encoding="utf-8", size_bytes=14)
        assert info.raw_html == "<html></html>"
        assert info.encoding == "utf-8"


class TestDownloadRecord:
    def test_defaults(self):
        rec = DownloadRecord()
        assert rec.url == ""
        assert rec.bytes_downloaded == 0

    def test_custom(self):
        rec = DownloadRecord(url="https://example.com/file.pdf", bytes_downloaded=1024)
        assert rec.bytes_downloaded == 1024


class TestCrawlMeta:
    def test_defaults(self):
        meta = CrawlMeta()
        assert meta.depth == 0
        assert meta.discovered_from is None
        assert meta.discovery_method is None
        assert meta.run_id is None

    def test_custom(self):
        meta = CrawlMeta(depth=2, discovered_from="https://a.com", discovery_method="link")
        assert meta.depth == 2
        assert meta.discovery_method == "link"


class TestArtifactSource:
    def test_defaults(self):
        src = ArtifactSource()
        assert src.type == "unknown"
        assert src.site is None

    def test_custom(self):
        src = ArtifactSource(type="seed", site="example.com")
        assert src.type == "seed"
        assert src.site == "example.com"


class TestPageArtifact:
    def test_defaults(self):
        art = PageArtifact()
        assert art.schema_version == SCHEMA_VERSION
        assert art.url == ""
        assert art.fetched_at is None
        assert isinstance(art.http, HTTPInfo)
        assert isinstance(art.content, ContentInfo)
        assert isinstance(art.source, ArtifactSource)
        assert art.links == []
        assert art.extracted == {}
        assert art.downloads == []
        assert art.errors == []
        assert isinstance(art.crawl, CrawlMeta)

    def test_validate_minimal_valid(self):
        art = PageArtifact(
            url="https://example.com",
            fetched_at=datetime.now(timezone.utc),
        )
        problems = art.validate_minimal()
        assert problems == []

    def test_validate_minimal_missing_url(self):
        art = PageArtifact(fetched_at=datetime.now(timezone.utc))
        problems = art.validate_minimal()
        assert any("url is required" in p for p in problems)

    def test_validate_minimal_invalid_url_scheme(self):
        art = PageArtifact(url="ftp://example.com", fetched_at=datetime.now(timezone.utc))
        problems = art.validate_minimal()
        assert any("http" in p for p in problems)

    def test_validate_minimal_missing_fetched_at(self):
        art = PageArtifact(url="https://example.com")
        problems = art.validate_minimal()
        assert any("fetched_at" in p for p in problems)

    def test_validate_minimal_wrong_schema(self):
        art = PageArtifact(
            url="https://example.com",
            fetched_at=datetime.now(timezone.utc),
            schema_version="99",
        )
        problems = art.validate_minimal()
        assert any("schema_version" in p for p in problems)

    def test_add_error_crawl_error(self):
        art = PageArtifact(url="https://example.com")
        err = CrawlError.fetch("Timeout", 408)
        art.add_error(err)
        assert len(art.errors) == 1
        assert art.errors[0].code == "HTTP_ERROR"

    def test_add_error_string(self):
        art = PageArtifact(url="https://example.com")
        art.add_error("Something broke", code="UNKNOWN", source="test")
        assert len(art.errors) == 1
        assert art.errors[0].message == "Something broke"
        assert art.errors[0].source == "test"

    def test_copy_independence(self):
        art = PageArtifact(
            url="https://example.com",
            links=["https://a.com"],
            extracted={"key": "value"},
        )
        copy = art.copy()
        copy.links.append("https://b.com")
        copy.extracted["key2"] = "v2"
        copy.http.status = 404

        assert len(art.links) == 1
        assert "key2" not in art.extracted
        assert art.http.status is None

    def test_to_dict(self):
        now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        art = PageArtifact(
            url="https://example.com",
            fetched_at=now,
            http=HTTPInfo(status=200),
            links=["https://example.com/about"],
        )
        d = art.to_dict()
        assert d["url"] == "https://example.com"
        assert d["fetched_at"] == now.isoformat()
        assert d["http"]["status"] == 200
        assert d["links"] == ["https://example.com/about"]

    def test_to_dict_with_errors(self):
        art = PageArtifact(url="https://example.com")
        art.add_error(CrawlError.fetch("Timeout", 408))
        d = art.to_dict()
        assert len(d["errors"]) == 1
        assert d["errors"][0]["code"] == "HTTP_ERROR"
        assert d["errors"][0]["http_status"] == 408

    def test_from_legacy_result(self):
        legacy = {
            "status": 200,
            "headers": {"Content-Type": "text/html"},
            "content_type": "text/html",
            "html_content": "<html></html>",
            "links": ["https://example.com/a"],
            "depth": 2,
            "title": "Test Page",
            "keywords": ["test"],
            "error": None,
        }
        art = PageArtifact.from_legacy_result("https://example.com", legacy)
        assert art.schema_version == "legacy"
        assert art.url == "https://example.com"
        assert art.http.status == 200
        assert art.content.raw_html == "<html></html>"
        assert art.links == ["https://example.com/a"]
        assert art.crawl.depth == 2
        assert art.extracted["title"] == "Test Page"
        assert art.extracted["keywords"] == ["test"]
        assert art.source.site == "example.com"

    def test_from_legacy_result_with_error(self):
        legacy = {"error": "Connection refused", "status": None, "depth": 0}
        art = PageArtifact.from_legacy_result("https://fail.com", legacy)
        assert len(art.errors) == 1
        assert "Connection refused" in art.errors[0].message

    def test_independent_instances(self):
        a = PageArtifact()
        b = PageArtifact()
        a.links.append("https://x.com")
        assert b.links == []
