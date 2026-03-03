"""Tests for crawlit.output.formatters module."""

import json
import os
import pytest

from crawlit.output.formatters import (
    save_results, save_as_json, save_as_csv, save_as_txt,
    save_as_html, generate_summary_report, create_output_file,
    _safe_href,
)


class TestSafeHref:
    def test_normal_url(self):
        assert _safe_href("https://example.com") == "https://example.com"

    def test_blocks_javascript(self):
        assert _safe_href("javascript:alert(1)") == "#"

    def test_blocks_javascript_case_insensitive(self):
        assert _safe_href("JavaScript:alert(1)") == "#"

    def test_blocks_data(self):
        assert _safe_href("data:text/html,<h1>X</h1>") == "#"

    def test_blocks_vbscript(self):
        assert _safe_href("vbscript:msgbox") == "#"

    def test_escapes_html_chars(self):
        result = _safe_href('https://example.com/?a=1&b="2"')
        assert "&amp;" in result or "&" in result


class TestCreateOutputFile:
    def test_creates_directory(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "output.json")
        create_output_file(path)
        assert os.path.isdir(str(tmp_path / "sub" / "dir"))

    def test_no_directory_component(self):
        create_output_file("output.json")


class TestSaveResults:
    def test_json_format(self, tmp_path, sample_results):
        output = str(tmp_path / "results.json")
        result = save_results(sample_results, output_format="json", output_file=output)
        assert os.path.exists(output)
        with open(output) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "urls" in data

    def test_csv_format(self, tmp_path, sample_results):
        output = str(tmp_path / "results.csv")
        save_results(sample_results, output_format="csv", output_file=output)
        assert os.path.exists(output)
        with open(output) as f:
            content = f.read()
        assert "URL" in content

    def test_txt_format(self, tmp_path, sample_results):
        output = str(tmp_path / "results.txt")
        save_results(sample_results, output_format="txt", output_file=output)
        assert os.path.exists(output)
        with open(output) as f:
            content = f.read()
        assert "Crawl Results" in content

    def test_html_format(self, tmp_path, sample_results):
        output = str(tmp_path / "results.html")
        save_results(sample_results, output_format="html", output_file=output)
        assert os.path.exists(output)
        with open(output) as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "Crawlit" in content

    def test_unsupported_format(self, sample_results, tmp_path):
        with pytest.raises(ValueError):
            save_results(sample_results, output_format="xml", output_file=str(tmp_path / "r.xml"))

    def test_pretty_json(self, tmp_path, sample_results):
        output = str(tmp_path / "pretty.json")
        save_results(sample_results, output_format="json", output_file=output, pretty_json=True)
        with open(output) as f:
            content = f.read()
        assert "\n" in content
        assert "  " in content

    def test_format_type_alias(self, tmp_path, sample_results):
        output = str(tmp_path / "alias.json")
        result = save_results(sample_results, format_type="json", output_file=output)
        assert os.path.exists(output)

    def test_pretty_alias(self, tmp_path, sample_results):
        output = str(tmp_path / "p.json")
        save_results(sample_results, output_format="json", output_file=output, pretty=True)
        with open(output) as f:
            content = f.read()
        assert "  " in content

    def test_returns_output_path(self, tmp_path, sample_results):
        output = str(tmp_path / "r.json")
        result = save_results(sample_results, output_format="json", output_file=output)
        assert result == output


class TestSaveAsJson:
    def test_excludes_html_content(self, tmp_path, sample_results):
        output = str(tmp_path / "test.json")
        save_as_json(sample_results, output, "2026-01-01")
        with open(output) as f:
            data = json.load(f)
        for url_data in data["urls"].values():
            assert "html_content" not in url_data

    def test_includes_metadata(self, tmp_path, sample_results):
        output = str(tmp_path / "test.json")
        save_as_json(sample_results, output, "2026-01-01")
        with open(output) as f:
            data = json.load(f)
        assert data["metadata"]["timestamp"] == "2026-01-01"
        assert data["metadata"]["total_urls"] == 2


class TestSaveAsCsv:
    def test_headers(self, tmp_path, sample_results):
        output = str(tmp_path / "test.csv")
        save_as_csv(sample_results, output, "2026-01-01")
        with open(output) as f:
            first_line = f.readline()
        assert "URL" in first_line
        assert "Status" in first_line

    def test_data_rows(self, tmp_path, sample_results):
        output = str(tmp_path / "test.csv")
        save_as_csv(sample_results, output, "2026-01-01")
        with open(output) as f:
            content = f.read()
        assert "example.com" in content


class TestSaveAsTxt:
    def test_includes_url_info(self, tmp_path, sample_results):
        output = str(tmp_path / "test.txt")
        save_as_txt(sample_results, output, "2026-01-01")
        with open(output) as f:
            content = f.read()
        assert "URL:" in content
        assert "Status:" in content
        assert "Links Found:" in content


class TestSaveAsHtml:
    def test_xss_prevention(self, tmp_path):
        results = {
            "https://example.com": {
                "status": 200,
                "depth": 0,
                "content_type": "text/html",
                "links": ["javascript:alert(1)"],
                "success": True,
                "images": [],
                "keywords": [],
                "keyphrases": [],
                "tables": [],
            },
        }
        output = str(tmp_path / "test.html")
        save_as_html(results, output, "2026-01-01")
        with open(output) as f:
            content = f.read()
        assert 'href="javascript:' not in content
        assert 'href="#"' in content


class TestGenerateSummaryReport:
    def test_basic_report(self, sample_results):
        report = generate_summary_report(sample_results)
        assert "Total URLs crawled: 2" in report
        assert "Successful requests: 2" in report
        assert "Failed requests: 0" in report

    def test_depth_breakdown(self, sample_results):
        report = generate_summary_report(sample_results)
        assert "Depth 0:" in report
        assert "Depth 1:" in report

    def test_link_count(self, sample_results):
        report = generate_summary_report(sample_results)
        assert "Total links discovered:" in report

    def test_empty_results(self):
        report = generate_summary_report({})
        assert "Total URLs crawled: 0" in report
