"""Shared fixtures for crawlit test suite."""

import os
import json
import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crawlit.models.page_artifact import (
    PageArtifact, CrawlError, CrawlJob, HTTPInfo,
    ContentInfo, DownloadRecord, CrawlMeta, ArtifactSource,
)
from crawlit.config import CrawlerConfig, FetchConfig, RateLimitConfig, OutputConfig


# ---------------------------------------------------------------------------
# pytest-asyncio configuration
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

SIMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="Test page description">
    <meta name="keywords" content="test, crawlit, python">
    <title>Test Page Title</title>
    <link rel="canonical" href="https://example.com/test">
</head>
<body>
    <h1>Main Heading</h1>
    <p>This is a test paragraph with some content for keyword extraction testing purposes.</p>
    <p>Another paragraph with more detailed content about web crawling and data extraction.</p>
    <a href="/about">About</a>
    <a href="/contact">Contact</a>
    <a href="https://external.com/page">External Link</a>
    <a href="javascript:void(0)">JS Link</a>
    <a href="mailto:test@example.com">Email</a>
    <a href="#section">Anchor</a>
    <img src="/images/logo.png" alt="Logo" width="200" height="100">
    <img src="/images/banner.jpg" alt="Banner">
</body>
</html>"""


TABLE_HTML = """<html><body>
<table>
    <thead>
        <tr><th>Name</th><th>Age</th><th>City</th></tr>
    </thead>
    <tbody>
        <tr><td>Alice</td><td>30</td><td>New York</td></tr>
        <tr><td>Bob</td><td>25</td><td>London</td></tr>
        <tr><td>Charlie</td><td>35</td><td>Paris</td></tr>
    </tbody>
</table>
</body></html>"""


FORM_HTML = """<html><body>
<form id="login-form" action="/login" method="POST" class="auth-form">
    <label for="username">Username</label>
    <input type="text" id="username" name="username" required placeholder="Enter username">
    <label for="password">Password</label>
    <input type="password" id="password" name="password" required minlength="8">
    <input type="hidden" name="csrf_token" value="abc123">
    <input type="submit" value="Log In">
</form>
<form id="search-form" action="/search" method="GET">
    <input type="text" name="q" placeholder="Search...">
    <button type="submit">Search</button>
</form>
<form id="upload-form" action="/upload" method="POST" enctype="multipart/form-data">
    <input type="file" name="document">
    <input type="submit" value="Upload">
</form>
</body></html>"""


STRUCTURED_DATA_HTML = """<html>
<head>
    <meta property="og:title" content="OG Title">
    <meta property="og:description" content="OG Description">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Twitter Title">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Test Article",
        "author": {"@type": "Person", "name": "Test Author"}
    }
    </script>
</head>
<body>
    <div itemscope itemtype="https://schema.org/Product">
        <span itemprop="name">Test Product</span>
        <span itemprop="price">29.99</span>
    </div>
</body>
</html>"""


JS_EMBEDDED_HTML = """<html><head>
<script>
window.__NEXT_DATA__ = {"props": {"pageProps": {"data": "test"}}};
</script>
<script type="application/json" id="app-data">
{"key": "value", "nested": {"a": 1}}
</script>
</head><body><p>Content</p></body></html>"""


@pytest.fixture
def simple_html():
    return SIMPLE_HTML


@pytest.fixture
def table_html():
    return TABLE_HTML


@pytest.fixture
def form_html():
    return FORM_HTML


@pytest.fixture
def structured_data_html():
    return STRUCTURED_DATA_HTML


@pytest.fixture
def js_embedded_html():
    return JS_EMBEDDED_HTML


# ---------------------------------------------------------------------------
# Mock response fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_response():
    """Create a mock requests.Response-like object."""
    response = MagicMock()
    response.status_code = 200
    response.text = SIMPLE_HTML
    response.content = SIMPLE_HTML.encode("utf-8")
    response.headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": str(len(SIMPLE_HTML)),
    }
    response.url = "https://example.com/test"
    response.ok = True
    response.encoding = "utf-8"
    return response


@pytest.fixture
def mock_response_404():
    """Create a 404 mock response."""
    response = MagicMock()
    response.status_code = 404
    response.text = "Not Found"
    response.content = b"Not Found"
    response.headers = {"Content-Type": "text/html"}
    response.url = "https://example.com/missing"
    response.ok = False
    return response


# ---------------------------------------------------------------------------
# PageArtifact fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_artifact():
    """Create a fully populated PageArtifact."""
    return PageArtifact(
        url="https://example.com/test",
        fetched_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        http=HTTPInfo(
            status=200,
            headers={"content-type": "text/html"},
            content_type="text/html",
        ),
        content=ContentInfo(
            raw_html=SIMPLE_HTML,
            encoding="utf-8",
            size_bytes=len(SIMPLE_HTML),
        ),
        links=["https://example.com/about", "https://example.com/contact"],
        crawl=CrawlMeta(depth=1, discovered_from="https://example.com"),
    )


@pytest.fixture
def sample_results():
    """Sample legacy crawl results dict for formatter tests."""
    return {
        "https://example.com": {
            "status": 200,
            "depth": 0,
            "content_type": "text/html",
            "links": ["https://example.com/about", "https://example.com/contact"],
            "success": True,
            "error": "",
            "images": [{"src": "/logo.png", "alt": "Logo"}],
            "keywords": ["python", "crawling"],
            "keyword_scores": {"python": 0.15, "crawling": 0.10},
            "keyphrases": ["web crawling"],
            "tables": [[["Name", "Value"], ["A", "1"]]],
            "html_content": SIMPLE_HTML,
        },
        "https://example.com/about": {
            "status": 200,
            "depth": 1,
            "content_type": "text/html",
            "links": [],
            "success": True,
            "error": "",
            "images": [],
            "keywords": [],
            "keyphrases": [],
            "tables": [],
        },
    }


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_config():
    return CrawlerConfig()


@pytest.fixture
def custom_config():
    return CrawlerConfig(
        start_url="https://example.com",
        max_depth=5,
        fetch=FetchConfig(timeout=30, user_agent="TestBot/1.0"),
        rate_limit=RateLimitConfig(delay=0.5),
        output=OutputConfig(write_jsonl=True, jsonl_path="out/test.jsonl"),
        enable_content_extraction=True,
        enable_table_extraction=True,
    )
