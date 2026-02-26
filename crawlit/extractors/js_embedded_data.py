#!/usr/bin/env python3
"""
js_embedded_data.py - Extractor for script-embedded JSON data.

Detects and safely parses common patterns used by modern JavaScript frameworks
to embed server-side state in HTML responses:

    - ``window.__NEXT_DATA__``     (Next.js)
    - ``window.__APOLLO_STATE__``  (Apollo GraphQL)
    - ``window.__REDUX_STATE__``   (Redux)
    - ``window.__INITIAL_STATE__`` (various frameworks)
    - ``window.__DATA__``          (generic)
    - ``__NUXT__``                 (Nuxt.js)
    - ``<script type="application/json">`` blocks

Extracted payloads are stored under ``artifact.extracted["js_embedded_data"]``
as a dict keyed by pattern / element-id name.

Usage
-----
    from crawlit.extractors.js_embedded_data import JSEmbeddedDataExtractor
    crawler = Crawler("https://next.example.com", extractors=[JSEmbeddedDataExtractor()])
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ..interfaces import Extractor
from ..models.page_artifact import PageArtifact

try:
    from bs4 import BeautifulSoup

    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------

# (name, compiled regex) – patterns applied to each <script> block text
_WINDOW_PATTERNS: List[tuple] = [
    (
        "__NEXT_DATA__",
        re.compile(
            r"window\.__NEXT_DATA__\s*=\s*(\{.+?\})\s*;?\s*$",
            re.DOTALL | re.MULTILINE,
        ),
    ),
    (
        "__APOLLO_STATE__",
        re.compile(
            r"window\.__APOLLO_STATE__\s*=\s*(\{.+?\})\s*;?\s*$",
            re.DOTALL | re.MULTILINE,
        ),
    ),
    (
        "__REDUX_STATE__",
        re.compile(
            r"window\.__REDUX_STATE__\s*=\s*(\{.+?\})\s*;?\s*$",
            re.DOTALL | re.MULTILINE,
        ),
    ),
    (
        "__INITIAL_STATE__",
        re.compile(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*;?\s*$",
            re.DOTALL | re.MULTILINE,
        ),
    ),
    (
        "__DATA__",
        re.compile(
            r"window\.__DATA__\s*=\s*(\{.+?\})\s*;?\s*$",
            re.DOTALL | re.MULTILINE,
        ),
    ),
    (
        "__NUXT__",
        re.compile(
            r"__NUXT__\s*=\s*(\{.+?\})\s*;?\s*$",
            re.DOTALL | re.MULTILINE,
        ),
    ),
]

# Guard against pathological inputs
_MAX_HTML_CHARS = 2_000_000   # 2 MB – truncate before parsing
_MAX_SCRIPT_CHARS = 500_000   # per script block


# ---------------------------------------------------------------------------
# Core extraction logic (usable standalone)
# ---------------------------------------------------------------------------


def _try_parse_json(text: str) -> Optional[Any]:
    """Attempt to parse *text* as JSON; return ``None`` on failure."""
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        return None


def extract_js_embedded_data(html_content: str) -> Dict[str, Any]:
    """
    Extract script-embedded JSON data from *html_content*.

    Parameters
    ----------
    html_content : str
        Raw HTML of the page.

    Returns
    -------
    dict
        Discovered payloads keyed by pattern name or script element id.
        Empty dict if nothing was found or input is falsy.
    """
    results: Dict[str, Any] = {}

    if not html_content:
        return results

    truncated = html_content[:_MAX_HTML_CHARS]
    script_texts: List[str] = []

    if _BS4_AVAILABLE:
        try:
            soup = BeautifulSoup(truncated, "html.parser")
            for tag in soup.find_all("script"):
                stype = (tag.get("type") or "").lower()
                text = tag.string or ""
                if not text:
                    continue

                # Inline JSON blocks (<script type="application/json"> etc.)
                if "application/json" in stype or "application/ld+json" in stype:
                    parsed = _try_parse_json(text)
                    if parsed is not None:
                        # Use id/class as key when available
                        key = tag.get("id") or tag.get("class") or "json_block"
                        if isinstance(key, list):
                            key = "_".join(str(k) for k in key)
                        # Avoid overwriting earlier blocks with same key
                        base_key = str(key)
                        final_key = base_key
                        suffix = 1
                        while final_key in results:
                            final_key = f"{base_key}_{suffix}"
                            suffix += 1
                        results[final_key] = parsed
                else:
                    script_texts.append(text[:_MAX_SCRIPT_CHARS])
        except Exception as exc:
            logger.debug(f"BeautifulSoup error in js_embedded_data: {exc}")
    else:
        # Fallback: crude regex to pull script block bodies
        for m in re.finditer(
            r"<script[^>]*>(.*?)</script>",
            truncated,
            re.DOTALL | re.IGNORECASE,
        ):
            script_texts.append(m.group(1)[:_MAX_SCRIPT_CHARS])

    # Apply window-variable patterns to each script block
    for script_text in script_texts:
        for name, pattern in _WINDOW_PATTERNS:
            if name in results:
                continue
            m = pattern.search(script_text)
            if m:
                parsed = _try_parse_json(m.group(1))
                if parsed is not None:
                    results[name] = parsed

    return results


# ---------------------------------------------------------------------------
# Extractor plugin
# ---------------------------------------------------------------------------


class JSEmbeddedDataExtractor(Extractor):
    """
    Plugin extractor for script-embedded JSON / framework state.

    Attach to a crawler::

        extractor = JSEmbeddedDataExtractor()
        crawler = Crawler("https://nextjs-app.example.com", extractors=[extractor])

    Results are stored under ``artifact.extracted["js_embedded_data"]``.
    """

    @property
    def name(self) -> str:
        return "js_embedded_data"

    def extract(self, html_content: str, artifact: PageArtifact) -> Dict[str, Any]:
        try:
            return extract_js_embedded_data(html_content)
        except Exception as exc:
            logger.warning(f"JSEmbeddedDataExtractor failed for {artifact.url}: {exc}")
            artifact.errors.append(f"js_embedded_data extraction failed: {exc}")
            return {}
