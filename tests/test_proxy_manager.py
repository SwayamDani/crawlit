"""Tests for crawlit.utils.proxy_manager module."""

import pytest
from crawlit.utils.proxy_manager import (
    Proxy, ProxyType, ProxyManager, ProxyRotationStrategy,
)


class TestProxy:
    def test_basic_proxy(self):
        p = Proxy(host="proxy.example.com", port=8080)
        assert p.host == "proxy.example.com"
        assert p.port == 8080
        assert p.proxy_type == ProxyType.HTTP

    def test_proxy_with_auth(self):
        p = Proxy(host="proxy.example.com", port=8080, username="user", password="pass")
        url = p.get_url()
        assert "user:pass" in url
        assert "proxy.example.com" in url

    def test_get_url_no_auth(self):
        p = Proxy(host="proxy.example.com", port=8080)
        url = p.get_url()
        assert url == "http://proxy.example.com:8080"

    def test_get_url_socks5(self):
        p = Proxy(host="proxy.example.com", port=1080, proxy_type=ProxyType.SOCKS5)
        url = p.get_url()
        assert "socks5" in url

    def test_get_dict(self):
        p = Proxy(host="proxy.example.com", port=8080)
        d = p.get_dict()
        assert "http" in d
        assert "https" in d

    def test_mark_used(self):
        p = Proxy(host="proxy.example.com", port=8080)
        p.mark_used()
        assert p._requests == 1

    def test_mark_failed(self):
        p = Proxy(host="proxy.example.com", port=8080)
        p.mark_failed()
        assert p._failures == 1

    def test_mark_working(self):
        p = Proxy(host="proxy.example.com", port=8080)
        p.mark_working()
        assert p._is_working is True

    def test_mark_not_working(self):
        p = Proxy(host="proxy.example.com", port=8080)
        p.mark_not_working()
        assert p._is_working is False

    def test_get_stats(self):
        p = Proxy(host="proxy.example.com", port=8080)
        p.mark_used()
        p.mark_used()
        p.mark_failed()
        stats = p.get_stats()
        assert stats["requests"] == 2
        assert stats["failures"] == 1

    def test_success_rate(self):
        p = Proxy(host="proxy.example.com", port=8080)
        p._requests = 10
        p._failures = 3
        rate = p.get_success_rate()
        assert rate == pytest.approx(70.0, abs=1.0)

    def test_success_rate_no_requests(self):
        p = Proxy(host="proxy.example.com", port=8080)
        assert p.get_success_rate() == 100.0

    def test_str(self):
        p = Proxy(host="proxy.example.com", port=8080)
        assert "proxy.example.com" in str(p)


class TestProxyManager:
    def test_add_proxy_object(self):
        pm = ProxyManager()
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        assert len(pm) == 1

    def test_add_proxy_string(self):
        pm = ProxyManager()
        pm.add_proxy("http://proxy1.com:8080")
        assert len(pm) == 1

    def test_add_proxy_dict(self):
        pm = ProxyManager()
        pm.add_proxy({"host": "proxy1.com", "port": 8080})
        assert len(pm) == 1

    def test_get_next_proxy_round_robin(self):
        pm = ProxyManager(rotation_strategy=ProxyRotationStrategy.ROUND_ROBIN)
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        pm.add_proxy(Proxy(host="proxy2.com", port=8080))
        p1 = pm.get_next_proxy()
        p2 = pm.get_next_proxy()
        assert p1 is not None
        assert p2 is not None

    def test_get_next_proxy_random(self):
        pm = ProxyManager(rotation_strategy=ProxyRotationStrategy.RANDOM)
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        p = pm.get_next_proxy()
        assert p is not None

    def test_get_next_proxy_empty(self):
        pm = ProxyManager()
        assert pm.get_next_proxy() is None

    def test_report_success(self):
        pm = ProxyManager()
        p = Proxy(host="proxy1.com", port=8080)
        pm.add_proxy(p)
        pm.report_success(p)
        assert p._is_working is True

    def test_report_failure(self):
        pm = ProxyManager()
        p = Proxy(host="proxy1.com", port=8080)
        pm.add_proxy(p)
        pm.report_failure(p)
        assert p._failures >= 1

    def test_get_proxy_dict(self):
        pm = ProxyManager()
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        d = pm.get_proxy_dict()
        assert d is not None
        assert "http" in d

    def test_get_proxy_url(self):
        pm = ProxyManager()
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        url = pm.get_proxy_url()
        assert url is not None
        assert "proxy1.com" in url

    def test_get_stats(self):
        pm = ProxyManager()
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        stats = pm.get_stats()
        assert isinstance(stats, dict)
        assert stats["total_proxies"] == 1

    def test_get_working_count(self):
        pm = ProxyManager()
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        assert pm.get_working_count() == 1

    def test_reset_stats(self):
        pm = ProxyManager()
        p = Proxy(host="proxy1.com", port=8080)
        pm.add_proxy(p)
        p.mark_used()
        p.mark_failed()
        pm.reset_stats()
        assert p._requests == 0
        assert p._failures == 0

    def test_bool_empty(self):
        pm = ProxyManager()
        assert bool(pm) is False

    def test_bool_with_proxies(self):
        pm = ProxyManager()
        pm.add_proxy(Proxy(host="proxy1.com", port=8080))
        assert bool(pm) is True


class TestProxyType:
    def test_types(self):
        assert ProxyType.HTTP is not None
        assert ProxyType.HTTPS is not None
        assert ProxyType.SOCKS5 is not None
