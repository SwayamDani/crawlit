"""Tests for crawlit.crawler.fetcher module."""

import pytest
from unittest.mock import patch, MagicMock
import requests
import requests.exceptions

from crawlit.crawler.fetcher import fetch_page, fetch_url


class TestFetchPage:
    URL = "https://example.com"

    def _mock_response(self, status=200, text="<html></html>", headers=None):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status
        resp.text = text
        resp.content = text.encode("utf-8")
        resp.headers = headers or {"Content-Type": "text/html"}
        resp.url = self.URL
        resp.ok = 200 <= status < 300
        return resp

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = self._mock_response()
        success, response, status = fetch_page(self.URL)
        assert success is True
        assert status == 200

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_404_no_retry(self, mock_get):
        mock_get.return_value = self._mock_response(status=404)
        success, error_msg, status = fetch_page(self.URL, max_retries=3)
        assert success is False
        assert status == 404
        assert mock_get.call_count == 1

    @patch("crawlit.crawler.fetcher.time.sleep")
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_500_retries(self, mock_get, mock_sleep):
        mock_get.return_value = self._mock_response(status=500)
        success, error_msg, status = fetch_page(self.URL, max_retries=2)
        assert success is False
        assert status == 500
        assert mock_get.call_count == 3  # initial + 2 retries

    @patch("crawlit.crawler.fetcher.time.sleep")
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_429_respects_retry_after(self, mock_get, mock_sleep):
        resp_429 = self._mock_response(status=429, headers={"Content-Type": "text/html", "Retry-After": "5"})
        resp_ok = self._mock_response(status=200)
        mock_get.side_effect = [resp_429, resp_ok]
        success, response, status = fetch_page(self.URL, max_retries=3)
        assert success is True
        assert status == 200
        mock_sleep.assert_called_once_with(5.0)

    @patch("crawlit.crawler.fetcher.time.sleep")
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_429_exponential_backoff_without_retry_after(self, mock_get, mock_sleep):
        resp_429 = self._mock_response(status=429)
        resp_ok = self._mock_response(status=200)
        mock_get.side_effect = [resp_429, resp_ok]
        success, response, status = fetch_page(self.URL, max_retries=3)
        assert success is True
        assert mock_sleep.called

    @patch("crawlit.crawler.fetcher.time.sleep")
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_timeout_retries(self, mock_get, mock_sleep):
        mock_get.side_effect = requests.exceptions.Timeout("Timed out")
        success, error_msg, status = fetch_page(self.URL, max_retries=1)
        assert success is False
        assert "Timeout" in error_msg or "timeout" in error_msg.lower()

    @patch("crawlit.crawler.fetcher.time.sleep")
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_connection_error_retries(self, mock_get, mock_sleep):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        success, error_msg, status = fetch_page(self.URL, max_retries=1)
        assert success is False

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_too_many_redirects_no_retry(self, mock_get):
        mock_get.side_effect = requests.exceptions.TooManyRedirects("Too many redirects")
        success, error_msg, status = fetch_page(self.URL, max_retries=3)
        assert success is False
        assert mock_get.call_count == 1

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_custom_user_agent(self, mock_get):
        mock_get.return_value = self._mock_response()
        fetch_page(self.URL, user_agent="TestBot/1.0")
        call_kwargs = mock_get.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert headers.get("User-Agent") == "TestBot/1.0"

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_custom_timeout(self, mock_get):
        mock_get.return_value = self._mock_response()
        fetch_page(self.URL, timeout=30)
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs.get("timeout") == 30 or call_kwargs[1].get("timeout") == 30

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_proxy_string(self, mock_get):
        mock_get.return_value = self._mock_response()
        fetch_page(self.URL, proxy="http://proxy:8080")
        call_kwargs = mock_get.call_args
        proxies = call_kwargs.kwargs.get("proxies") or call_kwargs[1].get("proxies")
        assert proxies == {"http": "http://proxy:8080", "https": "http://proxy:8080"}

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_max_response_bytes_exceeded(self, mock_get):
        resp = self._mock_response(headers={"Content-Type": "text/html", "Content-Length": "999999"})
        mock_get.return_value = resp
        success, error_msg, status = fetch_page(self.URL, max_response_bytes=1000)
        assert success is False
        assert "too large" in error_msg.lower() or "size" in error_msg.lower()

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_session_usage(self, mock_get):
        session = MagicMock(spec=requests.Session)
        session.get.return_value = self._mock_response()
        success, response, status = fetch_page(self.URL, session=session)
        assert success is True
        session.get.assert_called_once()
        mock_get.assert_not_called()

    @patch("crawlit.crawler.fetcher.time.sleep")
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_on_retry_callback(self, mock_get, mock_sleep):
        mock_get.return_value = self._mock_response(status=500)
        callback = MagicMock()
        fetch_page(self.URL, max_retries=1, on_retry=callback)
        assert callback.called

    @patch("crawlit.crawler.fetcher.time.sleep")
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_proxy_manager_rotation(self, mock_get, mock_sleep):
        proxy_obj = MagicMock()
        proxy_obj.get_dict.return_value = {"http": "http://p1:80", "https": "http://p1:80"}
        proxy_mgr = MagicMock()
        proxy_mgr.get_next_proxy.return_value = proxy_obj

        mock_get.return_value = self._mock_response()
        success, _, _ = fetch_page(self.URL, proxy_manager=proxy_mgr)
        assert success is True
        proxy_mgr.report_success.assert_called_once_with(proxy_obj)


class TestFetchUrl:
    @patch("crawlit.crawler.fetcher.requests.get")
    def test_success_returns_response(self, mock_get):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.text = "<html></html>"
        resp.headers = {"Content-Type": "text/html"}
        mock_get.return_value = resp
        result = fetch_url("https://example.com")
        assert result.status_code == 200

    @patch("crawlit.crawler.fetcher.requests.get")
    def test_error_raises(self, mock_get):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 404
        resp.text = "Not Found"
        resp.headers = {"Content-Type": "text/html"}
        mock_get.return_value = resp
        with pytest.raises(requests.exceptions.RequestException):
            fetch_url("https://example.com")
