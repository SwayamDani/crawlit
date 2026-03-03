"""Tests for crawlit pipeline modules."""

import json
import pytest
from datetime import datetime, timezone

from crawlit.pipelines.jsonl_writer import JSONLWriter
from crawlit.interfaces import Pipeline
from crawlit.models.page_artifact import PageArtifact, HTTPInfo, ContentInfo


class TestJSONLWriter:
    def test_implements_pipeline(self):
        assert issubclass(JSONLWriter, Pipeline)

    def test_writes_artifact(self, tmp_path):
        path = tmp_path / "artifacts.jsonl"
        writer = JSONLWriter(str(path))
        art = PageArtifact(
            url="https://example.com",
            fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            http=HTTPInfo(status=200),
        )
        result = writer.process(art)
        writer.close()

        assert result is art  # process returns the artifact
        content = path.read_text().strip()
        record = json.loads(content)
        assert record["url"] == "https://example.com"
        assert record["http"]["status"] == 200

    def test_multiple_artifacts(self, tmp_path):
        path = tmp_path / "artifacts.jsonl"
        writer = JSONLWriter(str(path))
        for i in range(5):
            art = PageArtifact(url=f"https://example.com/page{i}")
            writer.process(art)
        writer.close()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 5

    def test_append_mode(self, tmp_path):
        path = tmp_path / "artifacts.jsonl"
        writer1 = JSONLWriter(str(path), append=True)
        writer1.process(PageArtifact(url="https://a.com"))
        writer1.close()

        writer2 = JSONLWriter(str(path), append=True)
        writer2.process(PageArtifact(url="https://b.com"))
        writer2.close()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_overwrite_mode(self, tmp_path):
        path = tmp_path / "artifacts.jsonl"
        writer1 = JSONLWriter(str(path), append=False)
        writer1.process(PageArtifact(url="https://a.com"))
        writer1.close()

        writer2 = JSONLWriter(str(path), append=False)
        writer2.process(PageArtifact(url="https://b.com"))
        writer2.close()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1
        assert "b.com" in lines[0]

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "artifacts.jsonl"
        writer = JSONLWriter(str(path))
        writer.process(PageArtifact(url="https://example.com"))
        writer.close()
        assert path.exists()

    def test_close_idempotent(self, tmp_path):
        path = tmp_path / "artifacts.jsonl"
        writer = JSONLWriter(str(path))
        writer.process(PageArtifact(url="https://example.com"))
        writer.close()
        writer.close()  # should not raise

    def test_json_content_valid(self, tmp_path):
        path = tmp_path / "artifacts.jsonl"
        writer = JSONLWriter(str(path))
        art = PageArtifact(
            url="https://example.com",
            fetched_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            http=HTTPInfo(status=200, content_type="text/html"),
            content=ContentInfo(raw_html="<html></html>", size_bytes=13),
            links=["https://example.com/about"],
        )
        writer.process(art)
        writer.close()

        record = json.loads(path.read_text().strip())
        assert record["schema_version"] == "1"
        assert record["links"] == ["https://example.com/about"]
        assert record["content"]["raw_html"] == "<html></html>"
