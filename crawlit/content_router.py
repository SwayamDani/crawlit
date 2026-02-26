#!/usr/bin/env python3
"""
content_router.py - Content-type dispatch helper.

Centralises the mapping of HTTP ``Content-Type`` values to handler functions
so that adding support for new types (XML, JSON feeds, CSV, EPUB, …) never
requires modifying the engine core.

Usage example (custom pipeline)::

    from crawlit.content_router import ContentRouter

    router = ContentRouter()
    router.register("application/json", handle_json_feed)
    router.register("text/html",        handle_html)
    router.set_default(handle_unknown)

    result = router.route(response.headers["Content-Type"], response, artifact)

Engine usage::

    # engines build a router in __init__ and call it in _process_url:
    router = ContentRouter()
    router.register("text/html", self._handle_html)
    router.register("application/pdf", self._handle_pdf)
    links = router.route(content_type, url, depth, response, artifact) or []
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

ContentHandler = Callable[..., Any]


class ContentRouter:
    """
    Map HTTP content-types to handler callables.

    Registration is case-insensitive and strips parameters (``; charset=…``).

    Handlers are called via :meth:`route` with ``*args`` and ``**kwargs``
    forwarded verbatim; the caller controls the handler signature.

    Parameters
    ----------
    none.

    Examples
    --------
    >>> router = ContentRouter()
    >>> router.register("text/html", lambda url, html: parse_html(html))
    >>> router.register("application/pdf", lambda url, html: None)
    >>> router.route("text/html; charset=utf-8", url, html_bytes)
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, ContentHandler] = {}
        self._default: Optional[ContentHandler] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, content_type: str, handler: ContentHandler) -> "ContentRouter":
        """
        Register *handler* for *content_type*.

        *content_type* is normalised (lower-cased, parameters stripped) before
        storage.  Calling :meth:`register` twice for the same type overwrites
        the previous handler.

        Returns ``self`` for chaining::

            router.register("text/html", h1).register("application/pdf", h2)
        """
        key = self._normalise(content_type)
        self._handlers[key] = handler
        return self

    def set_default(self, handler: ContentHandler) -> "ContentRouter":
        """
        Set the fallback handler used when no registered type matches.

        Returns ``self`` for chaining.
        """
        self._default = handler
        return self

    def unregister(self, content_type: str) -> bool:
        """Remove the handler for *content_type*.  Returns ``True`` if found."""
        key = self._normalise(content_type)
        if key in self._handlers:
            del self._handlers[key]
            return True
        return False

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def route(self, content_type: str, *args: Any, **kwargs: Any) -> Any:
        """
        Dispatch to the handler registered for *content_type*.

        ``*args`` and ``**kwargs`` are forwarded unchanged to the handler.

        Returns whatever the handler returns, or ``None`` when no handler
        (not even the default) is registered.
        """
        handler = self.get_handler(content_type)
        if handler is None:
            logger.debug("ContentRouter: no handler for %r — skipping", content_type)
            return None
        return handler(*args, **kwargs)

    def has_handler(self, content_type: str) -> bool:
        """Return ``True`` if a specific or default handler is registered."""
        return self._normalise(content_type) in self._handlers or self._default is not None

    def get_handler(self, content_type: str) -> Optional[ContentHandler]:
        """Return the handler for *content_type*, or the default, or ``None``."""
        key = self._normalise(content_type)
        return self._handlers.get(key, self._default)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def registered_types(self) -> list:
        """Return the list of explicitly registered content-type strings."""
        return list(self._handlers.keys())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(content_type: str) -> str:
        """Strip parameters and lower-case: ``"text/HTML; charset=utf-8"`` → ``"text/html"``."""
        return content_type.split(";")[0].strip().lower()

    def __repr__(self) -> str:
        types = ", ".join(self._handlers) or "none"
        default = "set" if self._default else "none"
        return f"ContentRouter(types=[{types}], default={default})"
