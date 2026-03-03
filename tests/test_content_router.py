"""Tests for crawlit.content_router module."""

import pytest

from crawlit.content_router import ContentRouter


class TestContentRouter:
    def test_register_and_route(self):
        router = ContentRouter()
        handler = lambda x: f"handled {x}"
        router.register("text/html", handler)
        result = router.route("text/html", "test")
        assert result == "handled test"

    def test_case_insensitive(self):
        router = ContentRouter()
        router.register("text/html", lambda: "html")
        assert router.route("TEXT/HTML") == "html"
        assert router.route("Text/Html") == "html"

    def test_parameter_stripping(self):
        router = ContentRouter()
        router.register("text/html", lambda: "html")
        assert router.route("text/html; charset=utf-8") == "html"
        assert router.route("text/html; charset=utf-8; boundary=something") == "html"

    def test_default_handler(self):
        router = ContentRouter()
        router.set_default(lambda ct: f"default: {ct}")
        result = router.route("application/unknown", "application/unknown")
        assert result == "default: application/unknown"

    def test_no_handler_returns_none(self):
        router = ContentRouter()
        result = router.route("text/html", "data")
        assert result is None

    def test_specific_overrides_default(self):
        router = ContentRouter()
        router.set_default(lambda: "default")
        router.register("text/html", lambda: "html")
        assert router.route("text/html") == "html"
        assert router.route("application/json") == "default"

    def test_chaining(self):
        router = ContentRouter()
        result = router.register("text/html", lambda: "h").register("application/json", lambda: "j")
        assert result is router
        result2 = router.set_default(lambda: "d")
        assert result2 is router

    def test_unregister_existing(self):
        router = ContentRouter()
        router.register("text/html", lambda: "html")
        assert router.unregister("text/html") is True
        assert router.route("text/html") is None

    def test_unregister_nonexistent(self):
        router = ContentRouter()
        assert router.unregister("text/html") is False

    def test_has_handler_specific(self):
        router = ContentRouter()
        router.register("text/html", lambda: None)
        assert router.has_handler("text/html") is True
        assert router.has_handler("application/json") is False

    def test_has_handler_with_default(self):
        router = ContentRouter()
        router.set_default(lambda: None)
        assert router.has_handler("anything/here") is True

    def test_get_handler(self):
        router = ContentRouter()
        h = lambda: "html"
        router.register("text/html", h)
        assert router.get_handler("text/html") is h
        assert router.get_handler("text/plain") is None

    def test_get_handler_falls_back_to_default(self):
        router = ContentRouter()
        d = lambda: "default"
        router.set_default(d)
        assert router.get_handler("text/plain") is d

    def test_registered_types(self):
        router = ContentRouter()
        router.register("text/html", lambda: None)
        router.register("application/json", lambda: None)
        types = router.registered_types()
        assert set(types) == {"text/html", "application/json"}

    def test_registered_types_empty(self):
        router = ContentRouter()
        assert router.registered_types() == []

    def test_overwrite_handler(self):
        router = ContentRouter()
        router.register("text/html", lambda: "old")
        router.register("text/html", lambda: "new")
        assert router.route("text/html") == "new"

    def test_repr(self):
        router = ContentRouter()
        assert "ContentRouter" in repr(router)
        assert "none" in repr(router)
        router.register("text/html", lambda: None)
        assert "text/html" in repr(router)

    def test_repr_with_default(self):
        router = ContentRouter()
        router.set_default(lambda: None)
        assert "set" in repr(router)

    def test_normalise_static(self):
        assert ContentRouter._normalise("Text/HTML; charset=UTF-8") == "text/html"
        assert ContentRouter._normalise("APPLICATION/JSON") == "application/json"
        assert ContentRouter._normalise("  text/plain  ") == "text/plain"

    def test_route_with_kwargs(self):
        router = ContentRouter()
        router.register("text/html", lambda url, depth=0: f"{url}:{depth}")
        result = router.route("text/html", "https://example.com", depth=3)
        assert result == "https://example.com:3"
