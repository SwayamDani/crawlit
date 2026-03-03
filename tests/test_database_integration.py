"""
Database integration tests using real SQLite (no mocks).

Exercises crawlit.utils.database SQLiteBackend and get_database_backend
with an actual SQLite database (in-memory or temp file).
"""

import json
import pytest

from crawlit.utils.database import (
    SQLiteBackend,
    get_database_backend,
    DatabaseBackend,
)


# ---------------------------------------------------------------------------
# Sample crawl results (realistic structure used by crawler)
# ---------------------------------------------------------------------------

def _sample_results():
    """Crawl results dict as produced by the crawler (url -> result)."""
    return {
        "https://example.com/": {
            "url": "https://example.com/",
            "status": 200,
            "success": True,
            "depth": 0,
            "title": "Example Domain",
            "content_type": "text/html",
            "html_content": "<html><body>Example</body></html>",
            "links": ["https://example.com/about", "https://example.com/contact"],
            "images": ["https://example.com/logo.png"],
            "keywords": ["example", "domain"],
        },
        "https://example.com/about": {
            "url": "https://example.com/about",
            "status": 200,
            "success": True,
            "depth": 1,
            "title": "About",
            "content_type": "text/html",
            "html_content": "<html><body>About us</body></html>",
            "links": [],
            "images": [],
            "keywords": [],
        },
        "https://example.com/404": {
            "url": "https://example.com/404",
            "status": 404,
            "success": False,
            "depth": 1,
            "title": "",
            "content_type": "text/html",
            "html_content": "",
            "links": [],
            "images": [],
            "keywords": [],
        },
    }


def _sample_metadata():
    return {
        "start_url": "https://example.com/",
        "user_agent": "crawlit/1.0",
        "max_depth": 2,
        "respect_robots": True,
    }


# ---------------------------------------------------------------------------
# SQLiteBackend – real database (temp file)
# ---------------------------------------------------------------------------

class TestSQLiteBackendReal:
    """Tests against a real SQLite database (no mocks)."""

    def test_check_availability(self):
        ok, msg = SQLiteBackend.check_availability()
        assert ok is True
        assert "SQLite" in msg
        assert "OK" in msg or "available" in msg.lower()

    def test_connect_save_get_roundtrip(self, tmp_path):
        db_path = tmp_path / "crawlit_test.db"
        backend = SQLiteBackend(database_path=str(db_path))
        assert backend.conn is not None

        results = _sample_results()
        metadata = _sample_metadata()
        crawl_id = backend.save_results(results, metadata)
        assert crawl_id is not None
        assert isinstance(crawl_id, int)
        assert crawl_id >= 1

        fetched = backend.get_results()
        assert len(fetched) == 3
        urls = {r["url"] for r in fetched}
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
        assert "https://example.com/404" in urls

        one = next(r for r in fetched if r["url"] == "https://example.com/")
        assert one["status_code"] == 200
        assert one["success"] == 1
        assert one["depth"] == 0
        assert one["title"] == "Example Domain"
        assert one["content_type"] == "text/html"
        assert one["html_content"] == "<html><body>Example</body></html>"
        assert one["links"] == ["https://example.com/about", "https://example.com/contact"]
        assert one["images"] == ["https://example.com/logo.png"]
        assert one["keywords"] == ["example", "domain"]

        failed = next(r for r in fetched if r["url"] == "https://example.com/404")
        assert failed["status_code"] == 404
        assert failed["success"] == 0

        backend.disconnect()
        assert backend.conn is None

    def test_get_results_filter_by_crawl_id(self, tmp_path):
        db_path = tmp_path / "filter_test.db"
        backend = SQLiteBackend(database_path=str(db_path))
        results = _sample_results()
        metadata = _sample_metadata()
        crawl_id = backend.save_results(results, metadata)

        # second crawl with one page
        results2 = {"https://example.com/other": {
            "url": "https://example.com/other",
            "status": 200,
            "success": True,
            "depth": 0,
            "title": "Other",
            "content_type": "text/html",
            "html_content": "<p>Other</p>",
            "links": [],
            "images": [],
            "keywords": [],
        }}
        crawl_id2 = backend.save_results(results2, metadata)

        all_results = backend.get_results()
        assert len(all_results) == 4

        first_crawl = backend.get_results(filters={"crawl_id": crawl_id})
        assert len(first_crawl) == 3
        assert all(r["crawl_id"] == crawl_id for r in first_crawl)

        second_crawl = backend.get_results(filters={"crawl_id": crawl_id2})
        assert len(second_crawl) == 1
        assert second_crawl[0]["url"] == "https://example.com/other"

        backend.disconnect()

    def test_get_results_filter_by_success(self, tmp_path):
        db_path = tmp_path / "success_filter.db"
        backend = SQLiteBackend(database_path=str(db_path))
        results = _sample_results()
        backend.save_results(results, _sample_metadata())

        successful = backend.get_results(filters={"success": True})
        assert len(successful) == 2
        assert all(r["success"] == 1 for r in successful)

        failed = backend.get_results(filters={"success": False})
        assert len(failed) == 1
        assert failed[0]["url"] == "https://example.com/404"

        backend.disconnect()

    def test_get_crawls(self, tmp_path):
        db_path = tmp_path / "crawls.db"
        backend = SQLiteBackend(database_path=str(db_path))
        backend.save_results(_sample_results(), _sample_metadata())
        backend.save_results({"https://a.com": {
            "url": "https://a.com",
            "status": 200,
            "success": True,
            "depth": 0,
            "title": "A",
            "content_type": "text/html",
            "html_content": "",
            "links": [],
            "images": [],
            "keywords": [],
        }}, {"start_url": "https://a.com"})

        crawls = backend.get_crawls(limit=10)
        assert len(crawls) == 2
        assert all("id" in c and "start_url" in c and "timestamp" in c for c in crawls)
        start_urls = {c["start_url"] for c in crawls}
        assert "https://example.com/" in start_urls
        assert "https://a.com" in start_urls

        backend.disconnect()

    def test_clear_results_all(self, tmp_path):
        db_path = tmp_path / "clear_all.db"
        backend = SQLiteBackend(database_path=str(db_path))
        backend.save_results(_sample_results(), _sample_metadata())
        assert len(backend.get_results()) == 3

        backend.clear_results()
        assert len(backend.get_results()) == 0
        assert len(backend.get_crawls()) == 0
        backend.disconnect()

    def test_clear_results_by_crawl_id(self, tmp_path):
        db_path = tmp_path / "clear_one.db"
        backend = SQLiteBackend(database_path=str(db_path))
        crawl_id1 = backend.save_results(_sample_results(), _sample_metadata())
        results2 = {"https://example.com/extra": {
            "url": "https://example.com/extra",
            "status": 200,
            "success": True,
            "depth": 0,
            "title": "",
            "content_type": "text/html",
            "html_content": "",
            "links": [],
            "images": [],
            "keywords": [],
        }}
        crawl_id2 = backend.save_results(results2, _sample_metadata())
        assert len(backend.get_results()) == 4

        backend.clear_results(filters={"crawl_id": crawl_id1})
        remaining = backend.get_results()
        assert len(remaining) == 1
        assert remaining[0]["url"] == "https://example.com/extra"
        assert len(backend.get_crawls()) == 1
        backend.disconnect()

    def test_save_results_with_minimal_result(self, tmp_path):
        db_path = tmp_path / "minimal.db"
        backend = SQLiteBackend(database_path=str(db_path))
        results = {"https://minimal.com": {}}
        crawl_id = backend.save_results(results, {"start_url": "https://minimal.com"})
        assert crawl_id is not None
        fetched = backend.get_results()
        assert len(fetched) == 1
        row = fetched[0]
        assert row["url"] == "https://minimal.com"
        assert row["status_code"] == 0
        assert row["success"] == 0
        assert row["depth"] == 0
        assert row["title"] == ""
        assert row["links"] == []
        assert row["images"] == []
        assert row["keywords"] == []
        backend.disconnect()

    def test_in_memory_database(self):
        backend = SQLiteBackend(database_path=":memory:")
        ok, _ = SQLiteBackend.check_availability()
        assert ok is True
        backend.save_results(_sample_results(), _sample_metadata())
        assert len(backend.get_results()) == 3
        backend.disconnect()


# ---------------------------------------------------------------------------
# get_database_backend factory
# ---------------------------------------------------------------------------

class TestGetDatabaseBackend:
    """Tests for get_database_backend with real SQLite."""

    def test_get_sqlite_backend_with_temp_path(self, tmp_path):
        db_path = tmp_path / "factory_test.db"
        backend = get_database_backend("sqlite", check_setup=True, database_path=str(db_path))
        assert isinstance(backend, SQLiteBackend)
        assert backend.database_path == str(db_path)
        backend.save_results(_sample_results(), _sample_metadata())
        assert len(backend.get_results()) == 3
        backend.disconnect()

    def test_get_sqlite_backend_check_setup_false(self, tmp_path):
        db_path = tmp_path / "no_check.db"
        backend = get_database_backend("sqlite", check_setup=False, database_path=str(db_path))
        assert isinstance(backend, SQLiteBackend)
        backend.disconnect()

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError) as exc_info:
            get_database_backend("unknown", check_setup=False)
        assert "Unknown backend type" in str(exc_info.value)
        assert "unknown" in str(exc_info.value).lower()
