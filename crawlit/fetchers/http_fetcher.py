#!/usr/bin/env python3
"""
http_fetcher.py - Default Fetcher / AsyncFetcher implementations.

These wrap the existing ``fetch_page`` / ``fetch_page_async`` functions and
normalise their output into :class:`~crawlit.interfaces.FetchResult` objects.

They serve as the built-in fetch layer **and** as reference implementations
for custom :class:`~crawlit.interfaces.Fetcher` subclasses.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..interfaces import Fetcher, AsyncFetcher, FetchResult

logger = logging.getLogger(__name__)


class DefaultFetcher(Fetcher):
    """
    Synchronous HTTP fetcher backed by ``requests``.

    Thin wrapper around :func:`crawlit.crawler.fetcher.fetch_page` that
    normalises the return value into a :class:`~crawlit.interfaces.FetchResult`.

    Parameters
    ----------
    user_agent, max_retries, timeout, proxy, proxy_manager, use_js_rendering,
    js_wait_for_selector, js_wait_for_timeout, js_browser_type :
        Forwarded directly to ``fetch_page``.  See that function's docstring
        for details.
    session :
        Optional :class:`requests.Session` to reuse.
    """

    def __init__(
        self,
        user_agent: str = "crawlit/1.0",
        max_retries: int = 3,
        timeout: int = 10,
        session: Optional[Any] = None,
        proxy: Optional[str] = None,
        proxy_manager: Optional[Any] = None,
        use_js_rendering: bool = False,
        js_wait_for_selector: Optional[str] = None,
        js_wait_for_timeout: Optional[int] = None,
        js_browser_type: str = "chromium",
        max_response_bytes: Optional[int] = None,
    ):
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = session
        self.proxy = proxy
        self.proxy_manager = proxy_manager
        self.use_js_rendering = use_js_rendering
        self.js_wait_for_selector = js_wait_for_selector
        self.js_wait_for_timeout = js_wait_for_timeout
        self.js_browser_type = js_browser_type
        self.max_response_bytes = max_response_bytes

    def fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> FetchResult:
        from ..crawler.fetcher import fetch_page

        success, response_or_error, status_code = fetch_page(
            url=url,
            user_agent=self.user_agent,
            max_retries=self.max_retries,
            timeout=self.timeout,
            session=self.session,
            use_js_rendering=self.use_js_rendering,
            js_renderer=None,
            wait_for_selector=self.js_wait_for_selector,
            wait_for_timeout=self.js_wait_for_timeout,
            proxy=self.proxy,
            proxy_manager=self.proxy_manager,
            max_response_bytes=self.max_response_bytes,
            extra_headers=headers,
        )

        if status_code == 304:
            return FetchResult(
                success=False,
                url=url,
                status_code=304,
                not_modified=True,
                error="304 Not Modified",
            )

        if not success:
            return FetchResult(
                success=False,
                url=url,
                status_code=status_code or 0,
                error=str(response_or_error),
            )

        response = response_or_error
        resp_headers = dict(response.headers)
        content_type = response.headers.get("Content-Type", "")
        content_type_base = content_type.split(";")[0].strip().lower()

        text: Optional[str] = None
        raw_bytes: Optional[bytes] = None
        try:
            if "text" in content_type_base or "html" in content_type_base or "json" in content_type_base:
                text = response.text
            raw_bytes = response.content
        except Exception as exc:
            logger.warning(f"DefaultFetcher: failed to read body for {url}: {exc}")

        return FetchResult(
            success=True,
            url=url,
            status_code=status_code,
            headers=resp_headers,
            content_type=content_type or None,
            text=text,
            raw_bytes=raw_bytes,
        )


class DefaultAsyncFetcher(AsyncFetcher):
    """
    Asynchronous HTTP fetcher backed by ``aiohttp``.

    Thin wrapper around :func:`crawlit.crawler.async_fetcher.fetch_page_async`
    that normalises output into a :class:`~crawlit.interfaces.FetchResult`.
    """

    def __init__(
        self,
        user_agent: str = "crawlit/1.0",
        max_retries: int = 3,
        timeout: int = 10,
        session: Optional[Any] = None,
        proxy: Optional[str] = None,
        proxy_manager: Optional[Any] = None,
        use_js_rendering: bool = False,
        js_renderer: Optional[Any] = None,
        js_wait_for_selector: Optional[str] = None,
        js_wait_for_timeout: Optional[int] = None,
        max_response_bytes: Optional[int] = None,
    ):
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = session
        self.proxy = proxy
        self.proxy_manager = proxy_manager
        self.use_js_rendering = use_js_rendering
        self.js_renderer = js_renderer
        self.js_wait_for_selector = js_wait_for_selector
        self.js_wait_for_timeout = js_wait_for_timeout
        self.max_response_bytes = max_response_bytes

    async def fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> FetchResult:
        from ..crawler.async_fetcher import fetch_page_async

        success, response_or_error, status_code = await fetch_page_async(
            url=url,
            user_agent=self.user_agent,
            max_retries=self.max_retries,
            timeout=self.timeout,
            session=self.session,
            use_js_rendering=self.use_js_rendering,
            js_renderer=self.js_renderer,
            wait_for_selector=self.js_wait_for_selector,
            wait_for_timeout=self.js_wait_for_timeout,
            proxy=self.proxy,
            proxy_manager=self.proxy_manager,
            max_response_bytes=self.max_response_bytes,
            extra_headers=headers,
        )

        if status_code == 304:
            return FetchResult(
                success=False,
                url=url,
                status_code=304,
                not_modified=True,
                error="304 Not Modified",
            )

        if not success:
            return FetchResult(
                success=False,
                url=url,
                status_code=status_code or 0,
                error=str(response_or_error),
            )

        response = response_or_error
        resp_headers = dict(response.headers)
        content_type = response.headers.get("Content-Type", "")
        content_type_base = content_type.split(";")[0].strip().lower()

        text: Optional[str] = None
        raw_bytes: Optional[bytes] = None
        try:
            if "text" in content_type_base or "html" in content_type_base or "json" in content_type_base:
                text = await response.text()
            raw_bytes = await response.read()
        except Exception as exc:
            logger.warning(f"DefaultAsyncFetcher: failed to read body for {url}: {exc}")

        return FetchResult(
            success=True,
            url=url,
            status_code=status_code,
            headers=resp_headers,
            content_type=content_type or None,
            text=text,
            raw_bytes=raw_bytes,
        )
