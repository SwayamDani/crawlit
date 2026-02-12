#!/usr/bin/env python3
"""
Proxy Usage Examples for crawlit

Demonstrates comprehensive proxy support including:
- Single proxy usage
- Proxy Manager with rotation
- Loading proxies from file
- Different rotation strategies
- Health tracking and statistics
- SOCKS5 proxies
"""

import time
from crawlit import Crawler, AsyncCrawler, ProxyManager


def example_single_proxy():
    """Example: Using a Single Proxy"""
    print("\n=== Single Proxy Usage ===")
    
    # HTTP proxy
    crawler = Crawler(
        'https://httpbin.org/ip',
        max_depth=1,
        proxy='http://proxy.example.com:8080'
    )
    
    print("[OK] Crawler configured with single HTTP proxy")
    print(f"  Proxy: http://proxy.example.com:8080")
    
    # With authentication
    crawler_auth = Crawler(
        'https://httpbin.org/ip',
        max_depth=1,
        proxy='http://username:password@proxy.example.com:8080'
    )
    
    print("[OK] Crawler configured with authenticated proxy")
    print(f"  Proxy: http://username:****@proxy.example.com:8080")


def example_socks5_proxy():
    """Example: Using SOCKS5 Proxy"""
    print("\n=== SOCKS5 Proxy Usage ===")
    
    crawler = Crawler(
        'https://httpbin.org/ip',
        max_depth=1,
        proxy='socks5://proxy.example.com:1080'
    )
    
    print("[OK] Crawler configured with SOCKS5 proxy")
    print(f"  Proxy: socks5://proxy.example.com:1080")


def example_proxy_manager_basic():
    """Example: Basic Proxy Manager Usage"""
    print("\n=== Proxy Manager - Basic Usage ===")
    
    # Create proxy manager with round-robin strategy
    proxy_manager = ProxyManager(rotation_strategy='round_robin')
    
    # Add proxies
    proxy_manager.add_proxy('http://proxy1.example.com:8080')
    proxy_manager.add_proxy('http://proxy2.example.com:8080')
    proxy_manager.add_proxy('http://proxy3.example.com:8080')
    
    print(f"[OK] Created ProxyManager with {len(proxy_manager)} proxies")
    print(f"  Strategy: round-robin")
    
    # Get statistics
    stats = proxy_manager.get_stats()
    print(f"\nProxy Statistics:")
    print(f"  Total proxies: {stats['total_proxies']}")
    print(f"  Working proxies: {stats['working_proxies']}")
    print(f"  Rotation strategy: {stats['rotation_strategy']}")
    
    # Use with crawler
    crawler = Crawler(
        'https://httpbin.org/ip',
        max_depth=1,
        proxy_manager=proxy_manager
    )
    
    print(f"\n[OK] Crawler configured with ProxyManager")


def example_rotation_strategies():
    """Example: Different Rotation Strategies"""
    print("\n=== Rotation Strategies ===")
    
    strategies = ['round_robin', 'random', 'least_used', 'best_performance']
    
    for strategy in strategies:
        proxy_manager = ProxyManager(rotation_strategy=strategy)
        
        # Add some proxies
        proxy_manager.add_proxy('http://proxy1.example.com:8080')
        proxy_manager.add_proxy('http://proxy2.example.com:8080')
        proxy_manager.add_proxy('http://proxy3.example.com:8080')
        
        print(f"\n[OK] {strategy.upper()} Strategy:")
        
        # Get 5 proxies to demonstrate rotation
        for i in range(5):
            proxy = proxy_manager.get_next_proxy()
            if proxy:
                print(f"  Request {i+1}: {proxy.host}:{proxy.port}")


def example_proxy_file_loading():
    """Example: Loading Proxies from File"""
    print("\n=== Loading Proxies from File ===")
    
    # Create a sample proxy file
    proxy_content = """# Proxy list
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:8080
socks5://proxy3.example.com:1080
http://proxy4.example.com:3128
https://proxy5.example.com:443
"""
    
    # In a real scenario, you would save this to a file
    # For demo purposes, we'll manually add them
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(proxy_content)
        proxy_file = f.name
    
    try:
        # Load proxies from file
        proxy_manager = ProxyManager(rotation_strategy='least_used')
        
        # Manually parse and add proxies (load_from_file may not be implemented)
        with open(proxy_file, 'r') as f:
            count = 0
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy_manager.add_proxy(line)
                    count += 1
        
        print(f"[OK] Loaded {count} proxies from file")
        
        # Show loaded proxies
        stats = proxy_manager.get_stats()
        print(f"\nLoaded Proxies:")
        for i, proxy_info in enumerate(stats['proxies'], 1):
            proxy_type = proxy_info.get('type', 'http')
            host = proxy_info.get('host', 'unknown')
            port = proxy_info.get('port', 0)
            print(f"  {i}. {proxy_type}://{host}:{port}")
    finally:
        import os
        os.unlink(proxy_file)


def example_proxy_with_authentication():
    """Example: Proxies with Authentication"""
    print("\n=== Proxies with Authentication ===")
    
    proxy_manager = ProxyManager()
    
    # Add proxy with authentication (embedded in URL)
    proxy_manager.add_proxy('http://myusername:mypassword@proxy.example.com:8080')
    
    print("[OK] Added proxy with authentication")
    print(f"  URL: http://myusername:****@proxy.example.com:8080")
    print(f"  Authentication is embedded in the proxy URL")


def example_proxy_health_tracking():
    """Example: Proxy Health Tracking"""
    print("\n=== Proxy Health Tracking ===")
    
    proxy_manager = ProxyManager(rotation_strategy='best_performance')
    
    # Add proxies
    proxy_manager.add_proxy('http://proxy1.example.com:8080')
    proxy_manager.add_proxy('http://proxy2.example.com:8080')
    proxy_manager.add_proxy('http://proxy3.example.com:8080')
    
    print("[OK] Created ProxyManager with health tracking")
    
    # Simulate some requests and track success/failure
    print("\nSimulating requests with different proxies:")
    
    for i in range(10):
        proxy = proxy_manager.get_next_proxy()
        
        if proxy:
            # Simulate request success or failure
            import random
            success = random.random() > 0.3  # 70% success rate
            
            if success:
                proxy_manager.report_success(proxy)
                status = "[OK] Success"
            else:
                proxy_manager.report_failure(proxy)
                status = "[X] Failed"
            
            print(f"  Request {i+1} via {proxy.host}:{proxy.port}: {status}")
    
    # Show statistics after simulation
    print("\nProxy Statistics After Simulation:")
    stats = proxy_manager.get_stats()
    
    for proxy_info in stats['proxies']:
        host = proxy_info.get('host', 'unknown')
        port = proxy_info.get('port', 0)
        requests = proxy_info.get('requests', 0)
        failures = proxy_info.get('failures', 0)
        success_rate = proxy_info.get('success_rate', 0)
        is_working = proxy_info.get('is_working', True)
        
        status = "[OK] Working" if is_working else "[X] Not Working"
        print(f"  {host}:{port}")
        print(f"    Requests: {requests}, Failures: {failures}")
        print(f"    Success Rate: {success_rate:.1f}%")
        print(f"    Status: {status}")
        print()


def example_async_crawler_with_proxy():
    """Example: Using Proxies with Async Crawler"""
    print("\n=== Async Crawler with Proxy ===")
    
    # Create proxy manager
    proxy_manager = ProxyManager(rotation_strategy='round_robin')
    proxy_manager.add_proxy('http://proxy1.example.com:8080')
    proxy_manager.add_proxy('http://proxy2.example.com:8080')
    
    # Create async crawler with proxy manager
    crawler = AsyncCrawler(
        'https://httpbin.org/ip',
        max_depth=1,
        max_concurrent_requests=5,
        proxy_manager=proxy_manager
    )
    
    print(f"[OK] AsyncCrawler configured with ProxyManager")
    print(f"  Total proxies: {len(proxy_manager)}")
    print(f"  Max concurrent requests: 5")
    print(f"  Each request will use a different proxy (round-robin)")


def example_proxy_reset_stats():
    """Example: Resetting Proxy Statistics"""
    print("\n=== Resetting Proxy Statistics ===")
    
    proxy_manager = ProxyManager()
    
    # Add proxies and simulate usage
    proxy_manager.add_proxy('http://proxy1.example.com:8080')
    proxy = proxy_manager.get_next_proxy()
    
    if proxy:
        # Simulate some requests
        proxy.mark_used()
        proxy.mark_used()
        proxy.mark_failed()
        
        print(f"Proxy stats before reset:")
        stats = proxy.get_stats()
        print(f"  Requests: {stats['requests']}")
        print(f"  Failures: {stats['failures']}")
        
        # Reset stats
        proxy_manager.reset_stats()
        
        print(f"\n[OK] Statistics reset")
        print(f"Proxy stats after reset:")
        stats = proxy.get_stats()
        print(f"  Requests: {stats['requests']}")
        print(f"  Failures: {stats['failures']}")


def example_cli_usage():
    """Example: CLI Usage with Proxies"""
    print("\n=== CLI Usage Examples ===")
    
    print("Single proxy:")
    print("  crawlit --url https://example.com \\")
    print("          --proxy http://proxy.example.com:8080")
    
    print("\nProxy file with rotation:")
    print("  crawlit --url https://example.com \\")
    print("          --proxy-file proxies.txt \\")
    print("          --proxy-rotation round-robin")
    
    print("\nAvailable rotation strategies:")
    print("  - round-robin: Rotate proxies in order")
    print("  - random: Select random proxy for each request")
    print("  - least-used: Use the proxy with fewest requests")
    print("  - best-performance: Use the proxy with best success rate")


def example_real_world_scenario():
    """Example: Real-world Proxy Usage Scenario"""
    print("\n=== Real-world Scenario: Web Scraping with Proxy Rotation ===")
    
    print("\nScenario: Scraping a website that rate-limits by IP")
    print("Solution: Use proxy rotation to distribute requests across multiple IPs")
    
    # Setup proxy pool
    proxy_manager = ProxyManager(rotation_strategy='least_used')
    
    # Add multiple proxies (in reality, these would be real proxy servers)
    proxies = [
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080',
        'http://proxy3.example.com:8080',
        'http://proxy4.example.com:8080',
        'http://proxy5.example.com:8080',
    ]
    
    for proxy_url in proxies:
        proxy_manager.add_proxy(proxy_url)
    
    print(f"\n[OK] Configured proxy pool with {len(proxy_manager)} proxies")
    
    # Configure crawler
    crawler = Crawler(
        'https://example.com',
        max_depth=3,
        delay=0.5,  # Delay between requests
        proxy_manager=proxy_manager
    )
    
    print(f"[OK] Crawler configured:")
    print(f"  - Proxy rotation: least-used")
    print(f"  - Request delay: 0.5s")
    print(f"  - Max depth: 3")
    
    print(f"\nBenefits:")
    print(f"  [OK] Distribute load across {len(proxy_manager)} IPs")
    print(f"  [OK] Reduce chance of IP-based rate limiting")
    print(f"  [OK] Automatic failover if proxy fails")
    print(f"  [OK] Health tracking for proxy reliability")


if __name__ == '__main__':
    print("=" * 70)
    print("Proxy Usage Examples for crawlit")
    print("=" * 70)
    
    example_single_proxy()
    example_socks5_proxy()
    example_proxy_manager_basic()
    example_rotation_strategies()
    example_proxy_file_loading()
    example_proxy_with_authentication()
    example_proxy_health_tracking()
    example_async_crawler_with_proxy()
    example_proxy_reset_stats()
    example_cli_usage()
    example_real_world_scenario()
    
    print("\n" + "=" * 70)
    print("Examples complete!")
    print("\nNote: These examples use placeholder proxy addresses.")
    print("Replace with real proxy servers for actual usage.")
    print("=" * 70)

