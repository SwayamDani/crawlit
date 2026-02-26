#!/usr/bin/env python3
"""
interfaces.py - Plugin interfaces for crawlit.

Defines abstract base classes for:

  * Fetcher / AsyncFetcher   – pluggable HTTP fetch layer
  * Extractor / AsyncExtractor  – attach derived data to PageArtifact.extracted
  * Pipeline  / AsyncPipeline   – post-process, persist, or filter artifacts

Inject plugins via the keyword arguments on ``Crawler`` / ``AsyncCrawler``::

    from crawlit import Crawler
    from crawlit.interfaces import Extractor, Fetcher, FetchResult
    from crawlit.models import PageArtifact

    class PriceExtractor(Extractor):
        @property
        def name(self) -> str:
            return "prices"

        def extract(self, html_content: str, artifact: PageArtifact):
            # … parse prices …
            return [{"amount": 9.99, "currency": "USD"}]

    crawler = Crawler("https://shop.example.com", extractors=[PriceExtractor()])
"""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .models.page_artifact import PageArtifact


# ---------------------------------------------------------------------------
# Fetch abstraction
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class FetchRequest:
    """
    A single HTTP request specification.

    Passed to :class:`Fetcher` / :class:`AsyncFetcher` implementations so that
    the engine never needs to grow additional fetch-specific keyword arguments.

    Attributes
    ----------
    url : str
        Target URL.
    method : str
        HTTP method (default ``"GET"``).
    headers : dict
        Per-request headers merged on top of the session defaults.
    params : dict | None
        URL query-string parameters.
    body : bytes | None
        Request body for POST/PUT requests.
    timeout : int | None
        Request-level timeout override in seconds.  ``None`` uses the
        session/engine default.
    allow_js : bool
        When ``True`` the fetcher should use JS rendering (if available).
    cookies : dict | None
        Per-request cookies.
    proxy : str | None
        Proxy URL for this specific request (overrides engine-level proxy).
    retries : int
        Maximum retry attempts on transient failures.
    """

    url: str
    method: str = "GET"
    headers: Dict[str, str] = dataclasses.field(default_factory=dict)
    params: Optional[Dict[str, str]] = None
    body: Optional[bytes] = None
    timeout: Optional[int] = None
    allow_js: bool = False
    cookies: Optional[Dict[str, str]] = None
    proxy: Optional[str] = None
    retries: int = 3


@dataclasses.dataclass
class FetchResult:
    """
    Normalised result of a single HTTP fetch operation.

    Decouples the engines from the underlying HTTP library so that custom
    :class:`Fetcher` implementations can swap in authenticated sessions,
    rotating proxies, mock responses, etc.

    Attributes
    ----------
    success : bool
        ``True`` when the server returned a usable 2xx response.
    url : str
        Final URL after any redirects.
    status_code : int
        HTTP status code (0 when the request never reached the server).
    headers : dict
        Response headers (lower-cased keys preferred).
    content_type : str | None
        Value of the ``Content-Type`` header, if present.
    text : str | None
        Decoded response body.  Populated for text/* content.
    raw_bytes : bytes | None
        Raw response body.  Populated for binary content (PDFs, images, …).
    error : str | None
        Error description when ``success`` is ``False``.
    not_modified : bool
        ``True`` when the server returned 304 Not Modified (incremental crawl).
    elapsed_ms : float | None
        Total request→response time in milliseconds.
    response_bytes : int | None
        Number of bytes received over the wire.
    """

    success: bool = False
    url: str = ""
    status_code: int = 0
    headers: Dict[str, str] = dataclasses.field(default_factory=dict)
    content_type: Optional[str] = None
    text: Optional[str] = None
    raw_bytes: Optional[bytes] = None
    error: Optional[str] = None
    not_modified: bool = False
    elapsed_ms: Optional[float] = None
    response_bytes: Optional[int] = None


class Fetcher(ABC):
    """
    Synchronous HTTP fetch interface.

    Implement :meth:`fetch` to return a :class:`FetchResult` for any URL.
    Inject an instance via ``Crawler(fetcher=my_fetcher)``.

    The built-in :class:`~crawlit.fetchers.DefaultFetcher` wraps the standard
    ``requests``-based implementation and is used when no custom fetcher is
    provided.

    Custom implementations are useful for:
      * Rotating proxies / authenticated sessions
      * API-token injection
      * Anti-bot / rate-limit bypass strategies
      * Unit testing without network access
    """

    @abstractmethod
    def fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> FetchResult:
        """Fetch *url* and return a :class:`FetchResult`."""


class AsyncFetcher(ABC):
    """
    Asynchronous HTTP fetch interface.

    Inject an instance via ``AsyncCrawler(fetcher=my_fetcher)``.
    """

    @abstractmethod
    async def fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> FetchResult:
        """Fetch *url* asynchronously and return a :class:`FetchResult`."""


# ---------------------------------------------------------------------------
# Extractor interface
# ---------------------------------------------------------------------------


class Extractor(ABC):
    """
    Synchronous extractor plugin.

    Implement :meth:`extract` to derive structured data from ``html_content``
    and attach it to ``artifact.extracted[self.name]``.

    .. note::
        The synchronous :class:`~crawlit.crawler.engine.Crawler` **only**
        accepts ``Extractor`` instances.  Passing an :class:`AsyncExtractor`
        will raise :class:`TypeError` at construction time.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier used as the key in ``artifact.extracted``."""

    @abstractmethod
    def extract(self, html_content: str, artifact: "PageArtifact") -> Any:
        """
        Extract data from *html_content*.

        The return value is stored by the engine under
        ``artifact.extracted[self.name]``.  Return ``None`` to store nothing.
        """


class AsyncExtractor(ABC):
    """
    Asynchronous variant of :class:`Extractor`.

    Compatible with :class:`~crawlit.crawler.async_engine.AsyncCrawler` only.
    The async engine also accepts synchronous :class:`Extractor` instances.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier used as the key in ``artifact.extracted``."""

    @abstractmethod
    async def extract(self, html_content: str, artifact: "PageArtifact") -> Any:
        """Extract data asynchronously and return it."""


# ---------------------------------------------------------------------------
# Pipeline interface
# ---------------------------------------------------------------------------


class Pipeline(ABC):
    """
    Synchronous pipeline stage.

    Each stage receives a fully-populated :class:`~crawlit.models.PageArtifact`
    and may persist it, enrich it, or drop it.

    Return ``None`` to drop the artifact from further pipeline processing
    (it will *not* propagate to subsequent stages).

    .. note::
        The synchronous :class:`~crawlit.crawler.engine.Crawler` **only**
        accepts ``Pipeline`` instances.  Passing an :class:`AsyncPipeline`
        will raise :class:`TypeError` at construction time.
    """

    @abstractmethod
    def process(self, artifact: "PageArtifact") -> Optional["PageArtifact"]:
        """
        Process *artifact*.

        Returns the (possibly modified) artifact, or ``None`` to drop it.
        """


class AsyncPipeline(ABC):
    """
    Asynchronous variant of :class:`Pipeline`.

    Compatible with :class:`~crawlit.crawler.async_engine.AsyncCrawler` only.
    The async engine also accepts synchronous :class:`Pipeline` instances.
    """

    @abstractmethod
    async def process(self, artifact: "PageArtifact") -> Optional["PageArtifact"]:
        """Process *artifact* asynchronously."""
