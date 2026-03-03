"""Tests for crawlit.pipelines (artifact_store, blob_store, edges_writer) and storage."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from crawlit.models.page_artifact import PageArtifact, CrawlJob


class TestArtifactStore:
    def test_init(self, tmp_path):
        from crawlit.pipelines.artifact_store import ArtifactStore
        store = ArtifactStore(store_dir=str(tmp_path / "store"))
        assert store is not None
        store.close()

    def test_process_artifact(self, tmp_path):
        from crawlit.pipelines.artifact_store import ArtifactStore
        store = ArtifactStore(store_dir=str(tmp_path / "store"))
        artifact = PageArtifact(
            url="https://example.com",
            fetched_at="2024-01-01T00:00:00Z",
            schema_version="1.0",
        )
        result = store.process(artifact)
        assert result is not None
        store.close()

    def test_write_run_manifest(self, tmp_path):
        from crawlit.pipelines.artifact_store import ArtifactStore
        job = CrawlJob(seed_urls=["https://example.com"])
        store = ArtifactStore(store_dir=str(tmp_path / "store"), job=job)
        manifest_files = list((tmp_path / "store").glob("*.json"))
        assert len(manifest_files) >= 1
        store.close()

    def test_close(self, tmp_path):
        from crawlit.pipelines.artifact_store import ArtifactStore
        store = ArtifactStore(store_dir=str(tmp_path / "store"))
        store.close()

    def test_repr(self, tmp_path):
        from crawlit.pipelines.artifact_store import ArtifactStore
        store = ArtifactStore(store_dir=str(tmp_path / "store"))
        assert "ArtifactStore" in repr(store)
        store.close()


class TestBlobStore:
    def test_init(self, tmp_path):
        from crawlit.pipelines.blob_store import BlobStore
        store = BlobStore(blobs_dir=str(tmp_path / "blobs"))
        assert store is not None

    def test_process_html_artifact(self, tmp_path):
        from crawlit.pipelines.blob_store import BlobStore
        store = BlobStore(blobs_dir=str(tmp_path / "blobs"))
        artifact = PageArtifact(
            url="https://example.com/page",
            fetched_at="2024-01-01T00:00:00Z",
            schema_version="1.0",
        )
        artifact.html = "<html><body>Hello</body></html>"
        result = store.process(artifact)
        assert result is not None

    def test_process_no_content(self, tmp_path):
        from crawlit.pipelines.blob_store import BlobStore
        store = BlobStore(blobs_dir=str(tmp_path / "blobs"))
        artifact = PageArtifact(
            url="https://example.com/page",
            fetched_at="2024-01-01T00:00:00Z",
            schema_version="1.0",
        )
        result = store.process(artifact)
        assert result is not None


class TestEdgesWriter:
    def test_init(self, tmp_path):
        from crawlit.pipelines.edges_writer import EdgesWriter
        writer = EdgesWriter(path=str(tmp_path / "edges.jsonl"))
        assert writer is not None
        writer.close()

    def test_process_artifact_no_discovered_from(self, tmp_path):
        from crawlit.pipelines.edges_writer import EdgesWriter
        writer = EdgesWriter(path=str(tmp_path / "edges.jsonl"))
        artifact = PageArtifact(
            url="https://example.com",
            fetched_at="2024-01-01T00:00:00Z",
            schema_version="1.0",
        )
        result = writer.process(artifact)
        assert result is not None
        writer.close()

    def test_close(self, tmp_path):
        from crawlit.pipelines.edges_writer import EdgesWriter
        writer = EdgesWriter(path=str(tmp_path / "edges.jsonl"))
        writer.close()


class TestStorageManager:
    def test_init_memory(self):
        from crawlit.utils.storage import StorageManager
        sm = StorageManager()
        assert sm is not None

    def test_init_disk(self, tmp_path):
        from crawlit.utils.storage import StorageManager
        sm = StorageManager(
            storage_dir=str(tmp_path / "storage"),
            enable_disk_storage=True,
        )
        assert sm is not None

    def test_store_html_flag(self):
        from crawlit.utils.storage import StorageManager
        sm = StorageManager(store_html_content=True)
        assert sm.store_html_content is True

    def test_store_html_disabled(self):
        from crawlit.utils.storage import StorageManager
        sm = StorageManager(store_html_content=False)
        assert sm.store_html_content is False
