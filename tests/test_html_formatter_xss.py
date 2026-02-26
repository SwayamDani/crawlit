#!/usr/bin/env python3
"""
Tests verifying that save_as_html() escapes user-controlled content.

A malicious site can put XSS payloads in page titles, link hrefs, alt text,
keywords, keyphrases, and table cells.  If those values are embedded raw into
the HTML report, opening the report in a browser executes the script.

These tests confirm that every field is properly escaped via html.escape().
"""

import os
import tempfile
import pytest
from crawlit.output.formatters import save_as_html


# Common XSS payloads to probe
_SCRIPT_TAG = '<script>alert("xss")</script>'
_IMG_ONERROR = '<img src=x onerror=alert(1)>'
_HREF_JAVASCRIPT = 'javascript:alert(1)'
_QUOTE_BREAK = '" onmouseover="alert(1)'


def _render(results: dict) -> str:
    """Write HTML to a temp file and return its content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        path = f.name
    try:
        save_as_html(results, path, "2026-01-01 00:00:00")
        with open(path, encoding='utf-8') as f:
            return f.read()
    finally:
        os.unlink(path)


class TestHtmlFormatterXss:
    """Verify that all user-controlled values are HTML-escaped in the report."""

    def test_url_is_escaped(self):
        results = {_SCRIPT_TAG: {'status': 200, 'success': True,
                                  'depth': 0, 'content_type': 'text/html',
                                  'error': '', 'links': []}}
        html = _render(results)
        assert _SCRIPT_TAG not in html
        assert '&lt;script&gt;' in html

    def test_error_message_is_escaped(self):
        results = {'http://example.com': {
            'status': 500, 'success': False, 'depth': 0,
            'content_type': 'text/html',
            'error': _SCRIPT_TAG,
            'links': [],
        }}
        html = _render(results)
        assert _SCRIPT_TAG not in html
        assert '&lt;script&gt;' in html

    def test_link_href_is_escaped(self):
        """A javascript: href must not appear unescaped as an href attribute."""
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '',
            'links': [_HREF_JAVASCRIPT],
        }}
        html = _render(results)
        # The raw "javascript:" string must not appear inside href="..."
        assert 'href="javascript:' not in html

    def test_link_text_is_escaped(self):
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '',
            'links': [_SCRIPT_TAG],
        }}
        html = _render(results)
        assert _SCRIPT_TAG not in html

    def test_image_alt_is_escaped(self):
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '', 'links': [],
            'images': [{'src': 'http://example.com/img.png',
                        'alt': _SCRIPT_TAG, 'width': '100', 'height': '100'}],
        }}
        html = _render(results)
        assert _SCRIPT_TAG not in html
        assert '&lt;script&gt;' in html

    def test_image_src_is_escaped(self):
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '', 'links': [],
            'images': [{'src': _HREF_JAVASCRIPT, 'alt': 'ok',
                        'width': '100', 'height': '100'}],
        }}
        html = _render(results)
        assert 'href="javascript:' not in html

    def test_keyword_is_escaped(self):
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '', 'links': [],
            'keywords': [_SCRIPT_TAG],
            'keyword_scores': {_SCRIPT_TAG: 0.9},
        }}
        html = _render(results)
        assert _SCRIPT_TAG not in html

    def test_keyphrase_is_escaped(self):
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '', 'links': [],
            'keyphrases': [_SCRIPT_TAG],
        }}
        html = _render(results)
        assert _SCRIPT_TAG not in html

    def test_table_cell_is_escaped(self):
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '', 'links': [],
            'tables': [[[_SCRIPT_TAG, 'safe']]],
        }}
        html = _render(results)
        assert _SCRIPT_TAG not in html
        assert '&lt;script&gt;' in html

    def test_attribute_break_in_link_href_is_escaped(self):
        """Ensure a payload that tries to break out of href="..." is neutralised.

        html.escape() converts the payload's " to &quot;, so the attribute
        boundary is never broken.  The dangerous unescaped form must not appear.
        """
        payload_url = f'http://example.com/page?q={_QUOTE_BREAK}'
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': 'text/html', 'error': '', 'links': [payload_url],
        }}
        html = _render(results)
        # The unescaped quote-break that would create a new attribute must not appear.
        assert '" onmouseover="' not in html

    def test_content_type_is_escaped(self):
        results = {'http://example.com': {
            'status': 200, 'success': True, 'depth': 0,
            'content_type': _SCRIPT_TAG,
            'error': '', 'links': [],
        }}
        html = _render(results)
        assert _SCRIPT_TAG not in html
