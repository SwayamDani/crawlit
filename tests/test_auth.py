"""Tests for crawlit.utils.auth module."""

import pytest
from crawlit.utils.auth import (
    AuthConfig,
    AuthManager,
    create_basic_auth,
    create_bearer_auth,
    create_api_key_auth,
    create_custom_auth,
    create_digest_auth,
    get_auth_tuple,
)


class TestAuthConfig:
    def test_none_type(self):
        config = AuthConfig(auth_type="none")
        assert config.auth_type == "none"
        assert config.username is None
        assert config.password is None
        assert config.token is None

    def test_basic_auth_config(self):
        config = AuthConfig(auth_type="basic", username="user", password="pass")
        assert config.auth_type == "basic"
        assert config.username == "user"
        assert config.password == "pass"

    def test_bearer_auth_config(self):
        config = AuthConfig(auth_type="bearer", token="my-token")
        assert config.token == "my-token"

    def test_api_key_config(self):
        config = AuthConfig(
            auth_type="api_key",
            api_key="key123",
            api_key_name="X-Custom-Key",
        )
        assert config.api_key == "key123"
        assert config.api_key_name == "X-Custom-Key"

    def test_invalid_auth_type_raises(self):
        with pytest.raises(ValueError, match="Invalid auth_type"):
            AuthConfig(auth_type="invalid")

    def test_basic_without_password_raises(self):
        with pytest.raises(ValueError, match="requires username and password"):
            AuthConfig(auth_type="basic", username="user")


class TestAuthManager:
    def test_no_config(self):
        mgr = AuthManager()
        assert mgr.get_auth_for_requests() is None

    def test_basic_auth_headers(self):
        config = AuthConfig(auth_type="basic", username="user", password="pass")
        mgr = AuthManager(config)
        headers = mgr.add_auth_to_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_bearer_auth_headers(self):
        config = AuthConfig(auth_type="bearer", token="tok123")
        mgr = AuthManager(config)
        headers = mgr.add_auth_to_headers()
        assert headers["Authorization"] == "Bearer tok123"

    def test_api_key_headers(self):
        config = AuthConfig(auth_type="api_key", api_key="mykey", api_key_name="X-API-Key")
        mgr = AuthManager(config)
        headers = mgr.add_auth_to_headers()
        assert headers["X-API-Key"] == "mykey"

    def test_api_key_in_params(self):
        config = AuthConfig(
            auth_type="api_key",
            api_key="mykey",
            api_key_name="api_key",
            api_key_location="query",
        )
        mgr = AuthManager(config)
        params = mgr.add_auth_to_params()
        assert params.get("api_key") == "mykey"

    def test_custom_headers(self):
        config = AuthConfig(
            auth_type="custom",
            custom_headers={"X-Custom": "val"},
        )
        mgr = AuthManager(config)
        headers = mgr.add_auth_to_headers()
        assert headers["X-Custom"] == "val"

    def test_update_config(self):
        mgr = AuthManager(AuthConfig(auth_type="basic", username="u", password="p"))
        mgr.update_config(username="new_user")
        assert mgr.config.username == "new_user"

    def test_get_auth_for_requests(self):
        config = AuthConfig(auth_type="basic", username="u", password="p")
        mgr = AuthManager(config)
        result = mgr.get_auth_for_requests()
        assert result == ("u", "p")


class TestConvenienceFactories:
    def test_create_basic_auth(self):
        mgr = create_basic_auth("user", "pass")
        assert isinstance(mgr, AuthManager)
        headers = mgr.add_auth_to_headers()
        assert "Authorization" in headers

    def test_create_bearer_auth(self):
        mgr = create_bearer_auth("tok")
        assert isinstance(mgr, AuthManager)
        headers = mgr.add_auth_to_headers()
        assert headers["Authorization"] == "Bearer tok"

    def test_create_api_key_auth(self):
        mgr = create_api_key_auth("key123")
        assert isinstance(mgr, AuthManager)

    def test_create_api_key_auth_query(self):
        mgr = create_api_key_auth("key123", location="query")
        assert isinstance(mgr, AuthManager)

    def test_create_custom_auth(self):
        mgr = create_custom_auth({"X-Custom": "val"})
        assert isinstance(mgr, AuthManager)

    def test_create_digest_auth(self):
        mgr = create_digest_auth("user", "pass")
        assert isinstance(mgr, AuthManager)

    def test_get_auth_tuple(self):
        result = get_auth_tuple("user", "pass")
        assert result == ("user", "pass")
