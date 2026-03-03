"""Tests for crawlit.crawler.parser module."""

import pytest

from crawlit.crawler.parser import extract_links, _process_url


class TestExtractLinks:
    BASE_URL = "https://example.com/page"

    def test_anchor_links(self):
        html = '<html><body><a href="/about">About</a><a href="/contact">Contact</a></body></html>'
        links = extract_links(html, self.BASE_URL)
        assert "https://example.com/about" in links
        assert "https://example.com/contact" in links

    def test_absolute_links(self):
        html = '<html><body><a href="https://other.com/page">Other</a></body></html>'
        links = extract_links(html, self.BASE_URL)
        assert "https://other.com/page" in links

    def test_relative_links(self):
        html = '<html><body><a href="subpage">Sub</a></body></html>'
        links = extract_links(html, self.BASE_URL)
        assert any("subpage" in l for l in links)

    def test_skips_javascript_links(self):
        html = '<a href="javascript:void(0)">Click</a>'
        links = extract_links(html, self.BASE_URL)
        assert len(links) == 0

    def test_skips_mailto_links(self):
        html = '<a href="mailto:test@example.com">Email</a>'
        links = extract_links(html, self.BASE_URL)
        assert len(links) == 0

    def test_skips_tel_links(self):
        html = '<a href="tel:+1234567890">Call</a>'
        links = extract_links(html, self.BASE_URL)
        assert len(links) == 0

    def test_skips_hash_links(self):
        html = '<a href="#section">Jump</a>'
        links = extract_links(html, self.BASE_URL)
        assert len(links) == 0

    def test_skips_data_links(self):
        html = '<a href="data:text/html,<h1>Hello</h1>">Data</a>'
        links = extract_links(html, self.BASE_URL)
        assert len(links) == 0

    def test_removes_fragments(self):
        html = '<a href="https://example.com/page#section">Link</a>'
        links = extract_links(html, self.BASE_URL)
        for link in links:
            assert "#" not in link

    def test_img_src_extraction(self):
        html = '<img src="/images/photo.jpg">'
        links = extract_links(html, self.BASE_URL)
        assert any("photo.jpg" in l for l in links)

    def test_script_src_extraction(self):
        html = '<script src="/js/app.js"></script>'
        links = extract_links(html, self.BASE_URL)
        assert any("app.js" in l for l in links)

    def test_link_href_extraction(self):
        html = '<link rel="stylesheet" href="/css/style.css">'
        links = extract_links(html, self.BASE_URL)
        assert any("style.css" in l for l in links)

    def test_iframe_src_extraction(self):
        html = '<iframe src="https://embed.example.com/widget"></iframe>'
        links = extract_links(html, self.BASE_URL)
        assert any("embed.example.com" in l for l in links)

    def test_form_action_extraction(self):
        html = '<form action="/submit"></form>'
        links = extract_links(html, self.BASE_URL)
        assert any("submit" in l for l in links)

    def test_deduplicated_links(self):
        html = '<a href="/page">A</a><a href="/page">B</a>'
        links = extract_links(html, self.BASE_URL)
        page_links = [l for l in links if l.endswith("/page")]
        assert len(page_links) == 1

    def test_empty_html(self):
        links = extract_links("", self.BASE_URL)
        assert links == []

    def test_bytes_input(self):
        html = b'<html><body><a href="/test">Test</a></body></html>'
        links = extract_links(html, self.BASE_URL)
        assert any("test" in l for l in links)

    def test_bytes_input_latin1(self):
        html = '<a href="/caf\xe9">Café</a>'.encode("latin-1")
        links = extract_links(html, self.BASE_URL)
        assert len(links) >= 0  # should not crash

    def test_no_links(self):
        html = "<html><body><p>No links here</p></body></html>"
        links = extract_links(html, self.BASE_URL)
        assert links == []

    def test_preserves_query_params(self):
        html = '<a href="/search?q=test&page=2">Search</a>'
        links = extract_links(html, self.BASE_URL)
        matching = [l for l in links if "q=test" in l]
        assert len(matching) == 1


class TestProcessUrl:
    BASE = "https://example.com/dir/"

    def test_relative_url(self):
        result = _process_url("page.html", self.BASE)
        assert result == "https://example.com/dir/page.html"

    def test_absolute_url(self):
        result = _process_url("https://other.com/path", self.BASE)
        assert result == "https://other.com/path"

    def test_empty_url(self):
        result = _process_url("", self.BASE)
        assert result is None

    def test_javascript_url(self):
        result = _process_url("javascript:alert(1)", self.BASE)
        assert result is None

    def test_mailto_url(self):
        result = _process_url("mailto:a@b.com", self.BASE)
        assert result is None

    def test_ftp_scheme_filtered(self):
        result = _process_url("ftp://files.example.com/data", self.BASE)
        assert result is None

    @pytest.mark.parametrize("url,expected_contains", [
        ("/about", "about"),
        ("../other", "other"),
        ("./here", "here"),
    ])
    def test_various_relative_urls(self, url, expected_contains):
        result = _process_url(url, self.BASE)
        assert result is not None
        assert expected_contains in result
