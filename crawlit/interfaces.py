#!/usr/bin/env python3
"""
interfaces.py - Plugin interfaces for crawlit.

Defines abstract base classes for:

  * Extractor / AsyncExtractor  – attach derived data to PageArtifact.extracted
  * Pipeline  / AsyncPipeline   – post-process, persist, or filter artifacts

Inject plugins via the ``extractors=`` and ``pipelines=`` keyword arguments
on ``Crawler`` / ``AsyncCrawler``::

    from crawlit import Crawler
    from crawlit.interfaces import Extractor
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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .models.page_artifact import PageArtifact


# ---------------------------------------------------------------------------
# Extractor interface
# ---------------------------------------------------------------------------


class Extractor(ABC):
    """
    Synchronous extractor plugin.

    Implement :meth:`extract` to derive structured data from ``html_content``
    and attach it to ``artifact.extracted[self.name]``.
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
    """Asynchronous variant of :class:`Extractor`."""

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
    """

    @abstractmethod
    def process(self, artifact: "PageArtifact") -> Optional["PageArtifact"]:
        """
        Process *artifact*.

        Returns the (possibly modified) artifact, or ``None`` to drop it.
        """


class AsyncPipeline(ABC):
    """Asynchronous variant of :class:`Pipeline`."""

    @abstractmethod
    async def process(self, artifact: "PageArtifact") -> Optional["PageArtifact"]:
        """Process *artifact* asynchronously."""
