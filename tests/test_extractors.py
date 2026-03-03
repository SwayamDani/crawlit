"""Tests for all extractor modules in crawlit.extractors."""

import json
import os
import pytest

from crawlit.extractors.tables import (
    extract_tables, filter_tables, tables_to_csv, tables_to_dict,
    tables_to_json, clean_cell_content, get_url_safe_filename,
)
from crawlit.extractors.image_extractor import ImageTagParser, ImageExtractor
from crawlit.extractors.keyword_extractor import KeywordExtractor
from crawlit.extractors.forms import (
    FormExtractor, FormField, Form, extract_forms,
)
from crawlit.extractors.content_extractor import ContentExtractor


# -----------------------------------------------------------------------
# Table Extractor
# -----------------------------------------------------------------------

class TestCleanCellContent:
    def test_html_tags_removed(self):
        assert clean_cell_content("<b>Bold</b>") == "Bold"

    def test_wikipedia_refs_removed(self):
        assert clean_cell_content("Value[1][2]") == "Value"

    def test_whitespace_normalized(self):
        assert clean_cell_content("  hello   world  ") == "hello world"

    def test_nbsp_replaced(self):
        assert clean_cell_content("hello\xa0world") == "hello world"

    def test_empty_string(self):
        assert clean_cell_content("") == ""


class TestExtractTables:
    def test_simple_table(self, table_html):
        tables = extract_tables(table_html)
        assert len(tables) == 1
        assert tables[0][0] == ["Name", "Age", "City"]
        assert tables[0][1] == ["Alice", "30", "New York"]

    def test_empty_html(self):
        assert extract_tables("") == []

    def test_no_tables(self):
        assert extract_tables("<html><body><p>No tables</p></body></html>") == []

    def test_min_rows_filter(self):
        html = "<table><tr><td>Only row</td></tr></table>"
        assert extract_tables(html, min_rows=2) == []

    def test_min_columns_filter(self):
        html = "<table><tr><td>A</td></tr><tr><td>B</td></tr></table>"
        assert extract_tables(html, min_columns=2) == []

    def test_rowspan(self):
        html = """<table>
            <tr><td rowspan="2">Merged</td><td>A</td></tr>
            <tr><td>B</td></tr>
        </table>"""
        tables = extract_tables(html)
        assert len(tables) == 1
        assert tables[0][0][0] == "Merged"
        assert tables[0][1][0] == ""

    def test_colspan(self):
        html = """<table>
            <tr><td colspan="2">Wide</td></tr>
            <tr><td>Left</td><td>Right</td></tr>
        </table>"""
        tables = extract_tables(html)
        assert len(tables) == 1
        assert tables[0][0][0] == "Wide"

    def test_nested_tables_only_top_level(self):
        html = """<table><tr><td>
            <table><tr><td>Nested</td></tr></table>
        </td></tr></table>"""
        tables = extract_tables(html)
        assert len(tables) == 1

    def test_header_cells(self):
        html = "<table><tr><th>Header</th></tr><tr><td>Data</td></tr></table>"
        tables = extract_tables(html)
        assert tables[0][0] == ["Header"]
        assert tables[0][1] == ["Data"]


class TestFilterTables:
    def test_filter_by_min_rows(self):
        tables = [
            [["A"], ["B"]],
            [["X"]],
        ]
        result = filter_tables(tables, min_rows=2, min_cols=1)
        assert len(result) == 1

    def test_filter_by_min_cols(self):
        tables = [
            [["A", "B"], ["C", "D"]],
            [["X"], ["Y"]],
        ]
        result = filter_tables(tables, min_rows=1, min_cols=2)
        assert len(result) == 1


class TestTablesToCsv:
    def test_csv_output(self, tmp_path):
        tables = [[["Name", "Age"], ["Alice", "30"]]]
        files = tables_to_csv(tables, "test", str(tmp_path))
        assert len(files) == 1
        assert os.path.exists(files[0])
        with open(files[0]) as f:
            content = f.read()
        assert "Name" in content
        assert "Alice" in content

    def test_empty_tables(self, tmp_path):
        files = tables_to_csv([[]], "test", str(tmp_path))
        assert files == []


class TestTablesToDict:
    def test_basic_conversion(self):
        tables = [[["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]]
        result = tables_to_dict(tables)
        assert len(result) == 1
        assert result[0][0]["name"] == "Alice"
        assert result[0][0]["age"] == "30"

    def test_single_row_table_skipped(self):
        tables = [[["Header Only"]]]
        result = tables_to_dict(tables)
        assert result == []


class TestTablesToJson:
    def test_json_output(self, tmp_path):
        tables = [[["Name", "Age"], ["Alice", "30"]]]
        files = tables_to_json(tables, "test", str(tmp_path))
        assert len(files) == 1
        with open(files[0]) as f:
            data = json.load(f)
        assert data["headers"] == ["Name", "Age"]
        assert data["data"][0]["Name"] == "Alice"


class TestGetUrlSafeFilename:
    def test_basic(self):
        name = get_url_safe_filename("https://example.com/blog/post", 2)
        assert "example_com" in name
        assert "depth2" in name

    def test_root_url(self):
        name = get_url_safe_filename("https://example.com/", 0)
        assert "index" in name or "example_com" in name

    def test_long_path_truncated(self):
        name = get_url_safe_filename("https://example.com/" + "a" * 100, 0)
        assert len(name) < 120


# -----------------------------------------------------------------------
# Image Extractor
# -----------------------------------------------------------------------

class TestImageExtractor:
    def test_alias(self):
        assert ImageExtractor is ImageTagParser

    def test_basic_extraction(self):
        html = '<img src="/photo.jpg" alt="Photo" width="640" height="480">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert len(images) == 1
        assert images[0]["src"] == "/photo.jpg"
        assert images[0]["alt"] == "Photo"
        assert images[0]["width"] == 640
        assert images[0]["height"] == 480

    def test_no_src_skipped(self):
        html = '<img alt="No source">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert len(images) == 0

    def test_empty_src_skipped(self):
        html = '<img src="" alt="Empty">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert len(images) == 0

    def test_inside_iframe_skipped(self):
        html = '<iframe><img src="/hidden.jpg" alt="Hidden"></iframe>'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert len(images) == 0

    def test_decorative_icon_skipped(self):
        html = '<img src="/icon.svg" class="inline-icon" width="12" height="12" alt="">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert len(images) == 0

    def test_multiple_images(self):
        html = '<img src="/a.jpg" alt="A"><img src="/b.jpg" alt="B">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert len(images) == 2

    def test_decorative_flag(self):
        html = '<img src="/pic.jpg">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert images[0]["decorative"] is True

    def test_non_decorative_with_alt(self):
        html = '<img src="/pic.jpg" alt="A real photo">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert images[0]["decorative"] is False

    def test_parent_tag_context(self):
        html = '<figure><img src="/pic.jpg" alt="Fig"></figure>'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert images[0]["parent_tag"] == "figure"

    def test_class_list_to_string(self):
        html = '<img src="/x.jpg" class="img-responsive lazy" alt="X">'
        parser = ImageTagParser()
        images = parser.extract_images(html)
        assert "img-responsive" in images[0]["class"]
        assert "lazy" in images[0]["class"]

    def test_feed_method(self):
        html = '<img src="/feed.jpg" alt="Feed">'
        parser = ImageTagParser()
        parser.feed(html)
        assert len(parser.images) == 1

    def test_empty_html(self):
        parser = ImageTagParser()
        images = parser.extract_images("")
        assert images == []

    def test_none_html(self):
        parser = ImageTagParser()
        images = parser.extract_images(None)
        assert images == []


# -----------------------------------------------------------------------
# Keyword Extractor
# -----------------------------------------------------------------------

class TestKeywordExtractor:
    CONTENT_HTML = """<html><head><title>Python Web Crawling Guide</title></head>
    <body>
        <h1>Python Web Crawling</h1>
        <p>Python is a popular programming language for web crawling and data extraction.
        Python provides many libraries for web scraping and crawling. Python web crawling
        is essential for data collection. Web crawling with Python enables automated data
        extraction from websites. Python libraries like requests and BeautifulSoup make
        web crawling straightforward and efficient. Python web scrapers can handle complex
        websites with dynamic content loading.</p>
    </body></html>"""

    def test_extract_keywords(self):
        ext = KeywordExtractor()
        result = ext.extract_keywords(self.CONTENT_HTML)
        assert "keywords" in result
        assert len(result["keywords"]) > 0

    def test_extract_keywords_with_scores(self):
        ext = KeywordExtractor()
        result = ext.extract_keywords(self.CONTENT_HTML, include_scores=True)
        assert "scores" in result
        assert len(result["scores"]) > 0
        for score in result["scores"].values():
            assert 0 < score <= 1

    def test_extract_text_from_html(self):
        ext = KeywordExtractor()
        text = ext.extract_text_from_html(self.CONTENT_HTML)
        assert "Python" in text or "python" in text.lower()
        assert "<html>" not in text

    def test_title_weighted(self):
        ext = KeywordExtractor()
        text = ext.extract_text_from_html(self.CONTENT_HTML)
        count = text.lower().count("python web crawling guide")
        assert count >= 3  # title repeated 3x

    def test_tokenize_removes_stop_words(self):
        ext = KeywordExtractor()
        tokens = ext.tokenize_text("the quick brown fox jumps over the lazy dog")
        assert "the" not in tokens
        assert "over" not in tokens
        assert "quick" in tokens

    def test_tokenize_removes_short_words(self):
        ext = KeywordExtractor(min_word_length=4)
        tokens = ext.tokenize_text("go run fly execute")
        assert "go" not in tokens
        assert "run" not in tokens
        assert "execute" in tokens

    def test_tokenize_removes_digits(self):
        ext = KeywordExtractor()
        tokens = ext.tokenize_text("page 123 content 456")
        assert "123" not in tokens
        assert "456" not in tokens

    def test_min_content_threshold(self):
        ext = KeywordExtractor()
        result = ext.extract_keywords("<html><body><p>Short</p></body></html>")
        assert result["keywords"] == []

    def test_max_keywords_limit(self):
        ext = KeywordExtractor(max_keywords=5)
        result = ext.extract_keywords(self.CONTENT_HTML)
        assert len(result["keywords"]) <= 5

    def test_extract_keyphrases(self):
        ext = KeywordExtractor()
        phrases = ext.extract_keyphrases(self.CONTENT_HTML, min_phrase_freq=2)
        assert isinstance(phrases, list)

    def test_keyphrases_min_content(self):
        ext = KeywordExtractor()
        phrases = ext.extract_keyphrases("<html><body><p>tiny</p></body></html>")
        assert phrases == []


# -----------------------------------------------------------------------
# Form Extractor
# -----------------------------------------------------------------------

class TestFormExtractor:
    def test_extract_all_forms(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        forms = ext.extract_all_forms()
        assert len(forms) == 3

    def test_login_form(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        forms = ext.extract_all_forms()
        login = forms[0]
        assert login.form_id == "login-form"
        assert login.method == "POST"
        assert login.action == "https://example.com/login"
        assert login.has_csrf_token is True
        assert login.submit_button_text == "Log In"

    def test_password_field_detected(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        forms = ext.extract_all_forms()
        login = forms[0]
        pwd_fields = [f for f in login.fields if f.field_type == "password"]
        assert len(pwd_fields) == 1
        assert pwd_fields[0].required is True
        assert pwd_fields[0].minlength == 8

    def test_search_form(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        forms = ext.extract_all_forms()
        search = forms[1]
        assert search.form_id == "search-form"
        assert search.method == "GET"

    def test_file_upload_form(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        forms = ext.extract_all_forms()
        upload = forms[2]
        assert upload.has_file_upload is True
        assert upload.enctype == "multipart/form-data"

    def test_get_login_forms(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        ext.extract_all_forms()
        login_forms = ext.get_login_forms()
        assert len(login_forms) >= 1

    def test_get_search_forms(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        ext.extract_all_forms()
        search_forms = ext.get_search_forms()
        assert len(search_forms) >= 1

    def test_get_form_by_id(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        ext.extract_all_forms()
        form = ext.get_form_by_id("login-form")
        assert form is not None
        assert form.form_id == "login-form"

    def test_get_form_by_id_missing(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        ext.extract_all_forms()
        assert ext.get_form_by_id("nonexistent") is None

    def test_get_forms_by_action(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        ext.extract_all_forms()
        forms = ext.get_forms_by_action("login")
        assert len(forms) == 1

    def test_csrf_detection(self):
        html = """<form action="/submit" method="POST">
            <input type="hidden" name="csrf_token" value="xyz">
            <input type="text" name="data">
            <input type="submit" value="Go">
        </form>"""
        ext = FormExtractor(html)
        forms = ext.extract_all_forms()
        assert forms[0].has_csrf_token is True

    def test_captcha_detection(self):
        html = """<form action="/submit" method="POST">
            <input type="text" name="data">
            <div class="g-recaptcha" data-sitekey="abc"></div>
            <input type="submit" value="Go">
        </form>"""
        ext = FormExtractor(html)
        forms = ext.extract_all_forms()
        assert forms[0].has_captcha is True

    def test_label_association(self):
        html = """<form action="/test" method="POST">
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email">
            <input type="submit" value="Go">
        </form>"""
        ext = FormExtractor(html)
        forms = ext.extract_all_forms()
        email_field = [f for f in forms[0].fields if f.name == "email"][0]
        assert email_field.label == "Email Address"

    def test_select_field(self):
        html = """<form action="/test" method="POST">
            <select name="country">
                <option value="us">United States</option>
                <option value="uk" selected>United Kingdom</option>
            </select>
            <input type="submit" value="Go">
        </form>"""
        ext = FormExtractor(html)
        forms = ext.extract_all_forms()
        sel = [f for f in forms[0].fields if f.field_type == "select"][0]
        assert sel.name == "country"
        assert "us" in sel.options
        assert sel.value == "uk"

    def test_textarea_field(self):
        html = """<form action="/test" method="POST">
            <textarea name="comment" placeholder="Your comment" required></textarea>
            <input type="submit" value="Go">
        </form>"""
        ext = FormExtractor(html)
        forms = ext.extract_all_forms()
        ta = [f for f in forms[0].fields if f.field_type == "textarea"][0]
        assert ta.name == "comment"
        assert ta.required is True
        assert ta.placeholder == "Your comment"

    def test_to_dict(self, form_html):
        ext = FormExtractor(form_html, "https://example.com")
        ext.extract_all_forms()
        dicts = ext.to_dict()
        assert len(dicts) == 3
        assert "action" in dicts[0]
        assert "fields" in dicts[0]
        assert "field_count" in dicts[0]

    def test_convenience_function(self, form_html):
        forms = extract_forms(form_html, "https://example.com")
        assert len(forms) == 3

    def test_no_forms(self):
        forms = extract_forms("<html><body><p>No forms</p></body></html>")
        assert forms == []


# -----------------------------------------------------------------------
# Content Extractor
# -----------------------------------------------------------------------

class TestContentExtractor:
    def test_basic_extraction(self, simple_html):
        ext = ContentExtractor()
        result = ext.extract_content(simple_html, "https://example.com/test")
        assert result["title"] == "Test Page Title"
        assert result["meta_description"] == "Test page description"
        kw = result["meta_keywords"]
        kw_str = " ".join(kw) if isinstance(kw, list) else str(kw)
        assert "test" in kw_str.lower()
        assert result["canonical_url"] == "https://example.com/test"
        assert result["language"] == "en"

    def test_headings_extraction(self, simple_html):
        ext = ContentExtractor()
        result = ext.extract_content(simple_html, "https://example.com")
        headings = result["headings"]
        assert isinstance(headings, list)
        h1_items = [h for h in headings if h.get("level") == 1]
        assert len(h1_items) > 0
        assert any("Main Heading" in h.get("text", "") for h in h1_items)

    def test_images_with_context(self, simple_html):
        ext = ContentExtractor()
        result = ext.extract_content(simple_html, "https://example.com")
        assert len(result.get("images_with_context", [])) > 0

    @pytest.mark.parametrize("url,expected_type", [
        ("https://example.com/", "home"),
        ("https://example.com/about", "about"),
        ("https://example.com/blog/post-1", "blog"),
        ("https://example.com/products/item", "product"),
        ("https://example.com/contact", "contact"),
    ])
    def test_page_type_detection(self, url, expected_type):
        ext = ContentExtractor()
        result = ext.extract_content("<html><head><title>T</title></head><body></body></html>", url)
        assert result["page_type"] == expected_type

    @pytest.mark.asyncio
    async def test_async_extraction(self, simple_html):
        ext = ContentExtractor()
        result = await ext.extract_content_async(simple_html, "https://example.com/test")
        assert result["title"] == "Test Page Title"

    def test_empty_html(self):
        ext = ContentExtractor()
        result = ext.extract_content("", "https://example.com")
        assert result["title"] is None or result["title"] == ""


# -----------------------------------------------------------------------
# Structured Data Extractor
# -----------------------------------------------------------------------

class TestStructuredDataExtractor:
    def test_json_ld(self, structured_data_html):
        from crawlit.extractors.structured_data import StructuredDataExtractor
        ext = StructuredDataExtractor(structured_data_html, "https://example.com")
        ext.extract_all()
        data = ext.data
        assert len(data.json_ld) > 0
        assert data.json_ld[0]["@type"] == "Article"

    def test_open_graph(self, structured_data_html):
        from crawlit.extractors.structured_data import StructuredDataExtractor
        ext = StructuredDataExtractor(structured_data_html, "https://example.com")
        ext.extract_all()
        assert ext.data.open_graph.get("title") == "OG Title"

    def test_twitter_cards(self, structured_data_html):
        from crawlit.extractors.structured_data import StructuredDataExtractor
        ext = StructuredDataExtractor(structured_data_html, "https://example.com")
        ext.extract_all()
        assert ext.data.twitter_cards.get("card") == "summary"

    def test_as_dict(self, structured_data_html):
        from dataclasses import asdict
        from crawlit.extractors.structured_data import StructuredDataExtractor
        ext = StructuredDataExtractor(structured_data_html, "https://example.com")
        ext.extract_all()
        d = asdict(ext.data)
        assert "json_ld" in d
        assert "open_graph" in d

    def test_empty_html(self):
        from crawlit.extractors.structured_data import StructuredDataExtractor
        ext = StructuredDataExtractor("<html></html>", "https://example.com")
        ext.extract_all()
        assert ext.data.json_ld == []

    def test_convenience_function(self, structured_data_html):
        from crawlit.extractors.structured_data import extract_structured_data
        data = extract_structured_data(structured_data_html, "https://example.com")
        assert data is not None


# -----------------------------------------------------------------------
# Language Detector
# -----------------------------------------------------------------------

class TestLanguageDetector:
    def test_english_from_lang_attr(self):
        from crawlit.extractors.language import LanguageDetector
        html = '<html lang="en"><head><title>English</title></head><body></body></html>'
        det = LanguageDetector(html, "https://example.com")
        result = det.detect()
        assert result.primary_language == "en"

    def test_french_from_lang_attr(self):
        from crawlit.extractors.language import LanguageDetector
        html = '<html lang="fr"><body></body></html>'
        det = LanguageDetector(html, "https://example.com/fr/page")
        result = det.detect()
        assert result.primary_language == "fr"

    def test_convenience_function(self):
        from crawlit.extractors.language import detect_language
        html = '<html lang="de"><body></body></html>'
        result = detect_language(html, "https://example.de")
        assert result is not None

    def test_empty_html(self):
        from crawlit.extractors.language import LanguageDetector
        det = LanguageDetector("", "https://example.com")
        result = det.detect()
        assert result is not None


# -----------------------------------------------------------------------
# JS Embedded Data Extractor
# -----------------------------------------------------------------------

class TestJSEmbeddedDataExtractor:
    def test_next_data_extraction(self, js_embedded_html):
        from crawlit.extractors.js_embedded_data import extract_js_embedded_data
        data = extract_js_embedded_data(js_embedded_html)
        assert "__NEXT_DATA__" in data
        assert data["__NEXT_DATA__"]["props"]["pageProps"]["data"] == "test"

    def test_application_json_script(self, js_embedded_html):
        from crawlit.extractors.js_embedded_data import extract_js_embedded_data
        data = extract_js_embedded_data(js_embedded_html)
        found_json = False
        for key, value in data.items():
            if isinstance(value, dict) and value.get("key") == "value":
                found_json = True
                break
        assert found_json or len(data) > 1

    def test_empty_html(self):
        from crawlit.extractors.js_embedded_data import extract_js_embedded_data
        data = extract_js_embedded_data("")
        assert isinstance(data, dict)

    def test_no_embedded_data(self):
        from crawlit.extractors.js_embedded_data import extract_js_embedded_data
        data = extract_js_embedded_data("<html><body><p>No scripts</p></body></html>")
        assert isinstance(data, dict)

    def test_extractor_plugin_interface(self):
        from crawlit.extractors.js_embedded_data import JSEmbeddedDataExtractor
        from crawlit.models.page_artifact import PageArtifact
        ext = JSEmbeddedDataExtractor()
        assert ext.name == "js_embedded_data"
        result = ext.extract("<html></html>", PageArtifact())
        assert isinstance(result, dict)


# -----------------------------------------------------------------------
# PDF Extractor
# -----------------------------------------------------------------------

class TestPDFExtractor:
    def test_is_pdf_by_content_type(self):
        from crawlit.extractors.pdf_extractor import PDFExtractor
        ext = PDFExtractor()
        assert ext.is_pdf(content_type="application/pdf") is True
        assert ext.is_pdf(content_type="text/html") is False

    def test_is_pdf_by_content_magic_bytes(self):
        from crawlit.extractors.pdf_extractor import PDFExtractor
        ext = PDFExtractor()
        assert ext.is_pdf(content=b"%PDF-1.4 fake content") is True
        assert ext.is_pdf(content=b"<html>Not a PDF</html>") is False

    def test_is_pdf_available(self):
        from crawlit.extractors.pdf_extractor import is_pdf_available
        result = is_pdf_available()
        assert isinstance(result, bool)
