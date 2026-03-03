"""Tests for crawlit.utils.session_manager module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from crawlit.utils.session_manager import SessionManager


class TestSessionManager:
    def test_default_init(self):
        sm = SessionManager()
        assert sm is not None

    def test_custom_user_agent(self):
        sm = SessionManager(user_agent="custom-bot/1.0")
        session = sm.get_sync_session()
        assert session.headers.get("User-Agent") == "custom-bot/1.0"

    def test_get_sync_session(self):
        sm = SessionManager()
        session = sm.get_sync_session()
        assert session is not None
        session2 = sm.get_sync_session()
        assert session is session2

    def test_add_cookie(self):
        sm = SessionManager()
        sm.add_cookie("test_cookie", "test_value", domain="example.com")
        cookies = sm.get_cookies()
        assert "test_cookie" in cookies

    def test_add_header(self):
        sm = SessionManager()
        sm.add_header("X-Custom", "value")
        session = sm.get_sync_session()
        assert session.headers.get("X-Custom") == "value"

    def test_set_oauth_token(self):
        sm = SessionManager()
        sm.set_oauth_token("my-token")
        session = sm.get_sync_session()
        assert session.headers.get("Authorization") == "Bearer my-token"

    def test_set_api_key(self):
        sm = SessionManager()
        sm.set_api_key("key123", "X-API-Key")
        session = sm.get_sync_session()
        assert session.headers.get("X-API-Key") == "key123"

    def test_close_sync_session(self):
        sm = SessionManager()
        sm.get_sync_session()
        sm.close_sync_session()

    def test_context_manager(self):
        with SessionManager() as sm:
            session = sm.get_sync_session()
            assert session is not None

    def test_save_and_load_cookies_json(self, tmp_path):
        sm = SessionManager()
        sm.add_cookie("test", "value", domain="example.com")
        filepath = str(tmp_path / "cookies.json")
        sm.save_cookies(filepath, format="json")

        sm2 = SessionManager()
        sm2.load_cookies(filepath, format="json")
        cookies = sm2.get_cookies()
        assert "test" in cookies

    def test_get_cookies_empty(self):
        sm = SessionManager()
        cookies = sm.get_cookies()
        assert isinstance(cookies, dict)
