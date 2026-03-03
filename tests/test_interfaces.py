"""Tests for crawlit.interfaces module."""

import pytest
from typing import Optional, Any, Dict

from crawlit.interfaces import (
    FetchRequest, FetchResult,
    Fetcher, AsyncFetcher,
    Extractor, AsyncExtractor,
    Pipeline, AsyncPipeline,
)
from crawlit.models.page_artifact import PageArtifact


class TestFetchRequest:
    def test_defaults(self):
        req = FetchRequest(url="https://example.com")
        assert req.url == "https://example.com"
        assert req.method == "GET"
        assert req.headers == {}
        assert req.params is None
        assert req.body is None
        assert req.timeout is None
        assert req.allow_js is False
        assert req.cookies is None
        assert req.proxy is None
        assert req.retries == 3

    def test_custom(self):
        req = FetchRequest(
            url="https://api.example.com",
            method="POST",
            headers={"Authorization": "Bearer token"},
            body=b'{"key": "value"}',
            timeout=30,
            allow_js=True,
            proxy="http://proxy:8080",
            retries=5,
        )
        assert req.method == "POST"
        assert req.body == b'{"key": "value"}'
        assert req.allow_js is True
        assert req.retries == 5


class TestFetchResult:
    def test_defaults(self):
        result = FetchResult()
        assert result.success is False
        assert result.url == ""
        assert result.status_code == 0
        assert result.headers == {}
        assert result.text is None
        assert result.raw_bytes is None
        assert result.error is None
        assert result.not_modified is False

    def test_success_result(self):
        result = FetchResult(
            success=True,
            url="https://example.com",
            status_code=200,
            content_type="text/html",
            text="<html></html>",
            elapsed_ms=150.0,
            response_bytes=1024,
        )
        assert result.success is True
        assert result.status_code == 200
        assert result.elapsed_ms == 150.0

    def test_error_result(self):
        result = FetchResult(
            success=False,
            url="https://fail.com",
            status_code=500,
            error="Internal Server Error",
        )
        assert result.success is False
        assert result.error == "Internal Server Error"

    def test_not_modified(self):
        result = FetchResult(success=True, not_modified=True, status_code=304)
        assert result.not_modified is True


class TestFetcherABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Fetcher()

    def test_concrete_implementation(self):
        class MyFetcher(Fetcher):
            def fetch(self, url, headers=None):
                return FetchResult(success=True, url=url, status_code=200)

        fetcher = MyFetcher()
        result = fetcher.fetch("https://example.com")
        assert result.success is True
        assert result.url == "https://example.com"


class TestAsyncFetcherABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AsyncFetcher()

    @pytest.mark.asyncio
    async def test_concrete_implementation(self):
        class MyAsyncFetcher(AsyncFetcher):
            async def fetch(self, url, headers=None):
                return FetchResult(success=True, url=url, status_code=200)

        fetcher = MyAsyncFetcher()
        result = await fetcher.fetch("https://example.com")
        assert result.success is True


class TestExtractorABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Extractor()

    def test_concrete_implementation(self):
        class PriceExtractor(Extractor):
            @property
            def name(self) -> str:
                return "prices"

            def extract(self, html_content, artifact):
                return [{"amount": 9.99}]

        ext = PriceExtractor()
        assert ext.name == "prices"
        result = ext.extract("<html></html>", PageArtifact())
        assert result == [{"amount": 9.99}]


class TestAsyncExtractorABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AsyncExtractor()

    @pytest.mark.asyncio
    async def test_concrete_implementation(self):
        class AsyncPriceExtractor(AsyncExtractor):
            @property
            def name(self) -> str:
                return "async_prices"

            async def extract(self, html_content, artifact):
                return [{"amount": 19.99}]

        ext = AsyncPriceExtractor()
        assert ext.name == "async_prices"
        result = await ext.extract("<html></html>", PageArtifact())
        assert result == [{"amount": 19.99}]


class TestPipelineABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Pipeline()

    def test_concrete_implementation(self):
        class LogPipeline(Pipeline):
            def __init__(self):
                self.processed = []

            def process(self, artifact):
                self.processed.append(artifact.url)
                return artifact

        pipe = LogPipeline()
        art = PageArtifact(url="https://example.com")
        result = pipe.process(art)
        assert result is art
        assert pipe.processed == ["https://example.com"]

    def test_pipeline_drop(self):
        class DropPipeline(Pipeline):
            def process(self, artifact):
                return None

        pipe = DropPipeline()
        result = pipe.process(PageArtifact(url="https://example.com"))
        assert result is None


class TestAsyncPipelineABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AsyncPipeline()

    @pytest.mark.asyncio
    async def test_concrete_implementation(self):
        class AsyncLogPipeline(AsyncPipeline):
            async def process(self, artifact):
                return artifact

        pipe = AsyncLogPipeline()
        art = PageArtifact(url="https://example.com")
        result = await pipe.process(art)
        assert result is art
