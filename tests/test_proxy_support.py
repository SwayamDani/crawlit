#!/usr/bin/env python3
"""
Test proxy support functionality
"""

import pytest
from crawlit.utils.proxy_manager import (
    Proxy,
    ProxyType,
    ProxyManager,
    ProxyRotationStrategy,
    load_proxies_from_file,
)


class TestProxyCreation:
    """Test proxy object creation and configuration"""
    
    def test_create_basic_proxy(self):
        """Test creating a basic proxy"""
        proxy = Proxy(host="127.0.0.1", port=8080, proxy_type=ProxyType.HTTP)
        
        assert proxy.host == "127.0.0.1"
        assert proxy.port == 8080
        assert proxy.proxy_type == ProxyType.HTTP
    
    def test_create_authenticated_proxy(self):
        """Test creating a proxy with authentication"""
        proxy = Proxy(
            host="proxy.example.com",
            port=3128,
            proxy_type=ProxyType.HTTPS,
            username="user",
            password="pass"
        )
        
        assert proxy.username == "user"
        assert proxy.password == "pass"
    
    def test_proxy_url_generation(self):
        """Test proxy URL generation"""
        proxy = Proxy(host="127.0.0.1", port=8080, proxy_type=ProxyType.HTTP)
        url = proxy.get_url()
        
        assert "127.0.0.1:8080" in url
        assert url.startswith("http://")
    
    def test_proxy_url_with_auth(self):
        """Test proxy URL generation with authentication"""
        proxy = Proxy(
            host="proxy.example.com",
            port=3128,
            proxy_type=ProxyType.HTTPS,
            username="user",
            password="pass"
        )
        url = proxy.get_url()
        
        assert "user:pass@proxy.example.com:3128" in url
    
    def test_proxy_dict_generation(self):
        """Test proxy dictionary generation for requests library"""
        proxy = Proxy(host="127.0.0.1", port=8080, proxy_type=ProxyType.HTTP)
        proxy_dict = proxy.get_dict()
        
        assert 'http' in proxy_dict
        assert 'https' in proxy_dict
        assert "127.0.0.1:8080" in proxy_dict['http']


class TestProxyStatistics:
    """Test proxy statistics and tracking"""
    
    def test_proxy_usage_tracking(self):
        """Test that proxy tracks usage"""
        proxy = Proxy(host="127.0.0.1", port=8080)
        
        initial_requests = proxy._requests
        proxy.mark_used()
        
        assert proxy._requests == initial_requests + 1
    
    def test_proxy_failure_tracking(self):
        """Test that proxy tracks failures"""
        proxy = Proxy(host="127.0.0.1", port=8080)
        
        initial_failures = proxy._failures
        proxy.mark_failed()
        
        assert proxy._failures == initial_failures + 1
    
    def test_proxy_success_rate(self):
        """Test proxy success rate calculation"""
        proxy = Proxy(host="127.0.0.1", port=8080)
        
        # Initially should be 100%
        assert proxy.get_success_rate() == 100.0
        
        # Mark some usage
        proxy.mark_used()
        proxy.mark_used()
        proxy.mark_failed()
        
        # Should be 50% (1 failure out of 2 requests)
        assert proxy.get_success_rate() == 50.0


class TestProxyManager:
    """Test proxy manager functionality"""
    
    def test_create_proxy_manager(self):
        """Test creating a proxy manager"""
        manager = ProxyManager()
        
        assert len(manager) == 0
        assert manager.rotation_strategy == ProxyRotationStrategy.ROUND_ROBIN
    
    def test_add_proxy_from_string(self):
        """Test adding proxy from string"""
        manager = ProxyManager()
        manager.add_proxy("http://proxy1.example.com:8080")
        
        assert len(manager) == 1
    
    def test_add_proxy_from_dict(self):
        """Test adding proxy from dictionary"""
        manager = ProxyManager()
        manager.add_proxy({
            "host": "proxy1.example.com",
            "port": 8080,
            "type": "http"
        })
        
        assert len(manager) == 1
    
    def test_add_proxy_object(self):
        """Test adding Proxy object"""
        manager = ProxyManager()
        proxy = Proxy(host="proxy1.example.com", port=8080)
        manager.add_proxy(proxy)
        
        assert len(manager) == 1
    
    def test_initialize_with_proxies(self):
        """Test initializing manager with proxy list"""
        manager = ProxyManager(proxies=[
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:3128",
            {"host": "proxy3.example.com", "port": 8888, "type": "http"}
        ])
        
        assert len(manager) == 3


class TestProxyRotation:
    """Test proxy rotation strategies"""
    
    def test_round_robin_rotation(self):
        """Test round-robin rotation strategy"""
        manager = ProxyManager(
            proxies=[
                "http://proxy1.example.com:8080",
                "http://proxy2.example.com:8080",
                "http://proxy3.example.com:8080"
            ],
            rotation_strategy=ProxyRotationStrategy.ROUND_ROBIN
        )
        
        proxy1 = manager.get_next_proxy()
        proxy2 = manager.get_next_proxy()
        proxy3 = manager.get_next_proxy()
        proxy4 = manager.get_next_proxy()
        
        assert proxy1 is not None
        assert proxy2 is not None
        assert proxy3 is not None
        assert proxy4 is not None
        
        # Should cycle back to first proxy
        assert proxy1.host == proxy4.host
    
    def test_random_rotation(self):
        """Test random rotation strategy"""
        manager = ProxyManager(
            proxies=[
                "http://proxy1.example.com:8080",
                "http://proxy2.example.com:8080"
            ],
            rotation_strategy=ProxyRotationStrategy.RANDOM
        )
        
        proxy = manager.get_next_proxy()
        assert proxy is not None
    
    def test_least_used_rotation(self):
        """Test least-used rotation strategy"""
        manager = ProxyManager(
            proxies=[
                "http://proxy1.example.com:8080",
                "http://proxy2.example.com:8080"
            ],
            rotation_strategy=ProxyRotationStrategy.LEAST_USED
        )
        
        # First call should return first proxy
        proxy1 = manager.get_next_proxy()
        
        # Second call should return second proxy (least used)
        proxy2 = manager.get_next_proxy()
        
        assert proxy1.host != proxy2.host


class TestProxyFailureHandling:
    """Test proxy failure handling"""
    
    def test_report_failure(self):
        """Test reporting proxy failure"""
        manager = ProxyManager(proxies=["http://proxy1.example.com:8080"])
        
        proxy = manager.get_next_proxy()
        initial_failures = proxy._failures
        
        manager.report_failure(proxy)
        
        assert proxy._failures == initial_failures + 1
    
    def test_remove_failed_proxy(self):
        """Test removing failed proxy from pool"""
        manager = ProxyManager(
            proxies=[
                "http://proxy1.example.com:8080",
                "http://proxy2.example.com:8080"
            ],
            max_failures=2,
            remove_failed=True
        )
        
        initial_count = len(manager.proxies)
        proxy = manager.get_next_proxy()
        
        # Exceed max failures
        for _ in range(3):
            manager.report_failure(proxy)
        
        # Should have one less proxy
        assert len(manager.proxies) < initial_count
    
    def test_mark_not_working(self):
        """Test marking proxy as not working"""
        manager = ProxyManager(
            proxies=["http://proxy1.example.com:8080"],
            max_failures=1
        )
        
        proxy = manager.get_next_proxy()
        assert proxy._is_working == True
        
        # Exceed failures
        manager.report_failure(proxy)
        manager.report_failure(proxy)
        
        assert proxy._is_working == False
    
    def test_working_proxy_count(self):
        """Test getting working proxy count"""
        manager = ProxyManager(
            proxies=[
                "http://proxy1.example.com:8080",
                "http://proxy2.example.com:8080"
            ],
            max_failures=1,
            remove_failed=False
        )
        
        assert manager.get_working_count() == 2
        
        # Fail one proxy
        proxy = manager.get_next_proxy()
        manager.report_failure(proxy)
        manager.report_failure(proxy)
        
        assert manager.get_working_count() == 1


class TestProxyStatistics:
    """Test proxy manager statistics"""
    
    def test_get_stats(self):
        """Test getting proxy manager statistics"""
        manager = ProxyManager(
            proxies=[
                "http://proxy1.example.com:8080",
                "http://proxy2.example.com:8080"
            ]
        )
        
        stats = manager.get_stats()
        
        assert 'total_proxies' in stats
        assert 'working_proxies' in stats
        assert 'rotation_strategy' in stats
        assert 'proxies' in stats
        
        assert stats['total_proxies'] == 2
        assert stats['working_proxies'] == 2
    
    def test_reset_stats(self):
        """Test resetting proxy statistics"""
        manager = ProxyManager(proxies=["http://proxy1.example.com:8080"])
        
        proxy = manager.get_next_proxy()
        manager.report_failure(proxy)
        
        assert proxy._failures > 0
        
        manager.reset_stats()
        
        assert proxy._failures == 0
        assert proxy._is_working == True


class TestFetcherProxyIntegration:
    """Test fetcher integration with proxy support"""
    
    def test_sync_fetcher_has_proxy_parameters(self):
        """Test that sync fetcher accepts proxy parameters"""
        from crawlit.crawler.fetcher import fetch_page
        import inspect
        
        sig = inspect.signature(fetch_page)
        params = sig.parameters
        
        assert 'proxy' in params
        assert 'proxy_manager' in params
    
    def test_async_fetcher_has_proxy_parameters(self):
        """Test that async fetcher accepts proxy parameters"""
        from crawlit.crawler.async_fetcher import fetch_page_async
        import inspect
        
        sig = inspect.signature(fetch_page_async)
        params = sig.parameters
        
        assert 'proxy' in params
        assert 'proxy_manager' in params


class TestProxyParsing:
    """Test proxy string parsing"""
    
    def test_parse_simple_proxy(self):
        """Test parsing simple proxy string"""
        manager = ProxyManager()
        proxy = manager._parse_proxy_string("http://proxy.example.com:8080")
        
        assert proxy.host == "proxy.example.com"
        assert proxy.port == 8080
        assert proxy.proxy_type == ProxyType.HTTP
    
    def test_parse_authenticated_proxy(self):
        """Test parsing authenticated proxy string"""
        manager = ProxyManager()
        proxy = manager._parse_proxy_string("http://user:pass@proxy.example.com:8080")
        
        assert proxy.host == "proxy.example.com"
        assert proxy.port == 8080
        assert proxy.username == "user"
        assert proxy.password == "pass"
    
    def test_parse_socks5_proxy(self):
        """Test parsing SOCKS5 proxy string"""
        manager = ProxyManager()
        proxy = manager._parse_proxy_string("socks5://proxy.example.com:1080")
        
        assert proxy.host == "proxy.example.com"
        assert proxy.port == 1080
        assert proxy.proxy_type == ProxyType.SOCKS5
    
    def test_parse_proxy_without_protocol(self):
        """Test parsing proxy without protocol (defaults to HTTP)"""
        manager = ProxyManager()
        proxy = manager._parse_proxy_string("proxy.example.com:8080")
        
        assert proxy.host == "proxy.example.com"
        assert proxy.port == 8080
        assert proxy.proxy_type == ProxyType.HTTP



