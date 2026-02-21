#!/usr/bin/env python3
"""
proxy_manager.py - Proxy management and rotation

Provides proxy configuration, rotation, and pool management for crawlit.
Supports HTTP, HTTPS, and SOCKS5 proxies.
"""

import logging
import random
import time
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ProxyType(Enum):
    """Supported proxy types"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
    SOCKS5H = "socks5h"  # SOCKS5 with DNS resolution through proxy


@dataclass
class Proxy:
    """
    Represents a single proxy configuration.
    
    Attributes:
        host: Proxy host (IP or domain)
        port: Proxy port
        proxy_type: Type of proxy (HTTP, HTTPS, SOCKS5)
        username: Optional username for authentication
        password: Optional password for authentication
        protocol: Optional protocol override (defaults to proxy_type)
    """
    host: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: Optional[str] = None
    
    # Statistics
    _requests: int = 0
    _failures: int = 0
    _last_used: float = 0.0
    _is_working: bool = True
    
    def __post_init__(self):
        """Initialize statistics"""
        if isinstance(self.proxy_type, str):
            self.proxy_type = ProxyType(self.proxy_type.lower())
        self._requests = 0
        self._failures = 0
        self._last_used = 0.0
        self._is_working = True
    
    def get_url(self) -> str:
        """
        Get the proxy URL for use with requests/aiohttp.
        
        Returns:
            Formatted proxy URL string
        """
        protocol = self.protocol or self.proxy_type.value
        
        if self.username and self.password:
            return f"{protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{protocol}://{self.host}:{self.port}"
    
    def get_dict(self) -> Dict[str, str]:
        """
        Get proxy configuration as a dictionary for requests library.
        
        Returns:
            Dictionary with 'http' and 'https' keys
        """
        proxy_url = self.get_url()
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def mark_used(self):
        """Mark proxy as used and update statistics"""
        self._requests += 1
        self._last_used = time.time()
    
    def mark_failed(self):
        """Mark proxy as failed"""
        self._failures += 1
        logger.warning(f"Proxy {self.host}:{self.port} failed (total failures: {self._failures})")
    
    def mark_working(self):
        """Mark proxy as working"""
        self._is_working = True
    
    def mark_not_working(self):
        """Mark proxy as not working"""
        self._is_working = False
        logger.warning(f"Proxy {self.host}:{self.port} marked as not working")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        return {
            'host': self.host,
            'port': self.port,
            'type': self.proxy_type.value,
            'requests': self._requests,
            'failures': self._failures,
            'success_rate': self.get_success_rate(),
            'is_working': self._is_working,
            'last_used': self._last_used
        }
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self._requests == 0:
            return 100.0
        return ((self._requests - self._failures) / self._requests) * 100
    
    def __str__(self) -> str:
        return f"{self.proxy_type.value}://{self.host}:{self.port}"


class ProxyRotationStrategy(Enum):
    """Proxy rotation strategies"""
    ROUND_ROBIN = "round_robin"  # Cycle through proxies in order
    RANDOM = "random"  # Pick random proxy
    LEAST_USED = "least_used"  # Use proxy with fewest requests
    BEST_PERFORMANCE = "best_performance"  # Use proxy with best success rate


class ProxyManager:
    """
    Manages a pool of proxies with rotation and health checking.
    
    Features:
    - Multiple rotation strategies
    - Automatic proxy health tracking
    - Failed proxy removal
    - Thread-safe operations
    - Statistics tracking
    """
    
    def __init__(
        self,
        proxies: Optional[List[Union[Proxy, str, Dict[str, Any]]]] = None,
        rotation_strategy: Union[ProxyRotationStrategy, str] = ProxyRotationStrategy.ROUND_ROBIN,
        max_failures: int = 5,
        remove_failed: bool = True,
        retry_failed_after: Optional[int] = 300  # Retry failed proxies after 5 minutes
    ):
        """
        Initialize proxy manager.
        
        Args:
            proxies: List of proxy configurations (Proxy objects, strings, or dicts)
            rotation_strategy: Strategy for selecting next proxy
            max_failures: Maximum failures before marking proxy as not working
            remove_failed: Whether to remove failed proxies from rotation
            retry_failed_after: Seconds to wait before retrying failed proxy (None = never retry)
        """
        self.proxies: List[Proxy] = []
        self.rotation_strategy = (
            ProxyRotationStrategy(rotation_strategy) 
            if isinstance(rotation_strategy, str) 
            else rotation_strategy
        )
        self.max_failures = max_failures
        self.remove_failed = remove_failed
        self.retry_failed_after = retry_failed_after
        
        # State management
        self._current_index = 0
        self._lock = threading.Lock()
        
        # Add initial proxies
        if proxies:
            for proxy in proxies:
                self.add_proxy(proxy)
        
        logger.info(f"ProxyManager initialized with {len(self.proxies)} proxies")
        logger.info(f"Rotation strategy: {self.rotation_strategy.value}")
    
    def add_proxy(self, proxy: Union[Proxy, str, Dict[str, Any]]) -> None:
        """
        Add a proxy to the pool.
        
        Args:
            proxy: Proxy object, URL string, or configuration dict
        """
        if isinstance(proxy, Proxy):
            self.proxies.append(proxy)
        elif isinstance(proxy, str):
            self.proxies.append(self._parse_proxy_string(proxy))
        elif isinstance(proxy, dict):
            self.proxies.append(self._parse_proxy_dict(proxy))
        else:
            raise ValueError(f"Invalid proxy type: {type(proxy)}")
    
    def _parse_proxy_string(self, proxy_str: str) -> Proxy:
        """
        Parse proxy from string format.
        
        Formats supported:
        - http://host:port
        - http://user:pass@host:port
        - socks5://host:port
        - host:port (assumes HTTP)
        """
        import re
        
        # Pattern: [protocol://][user:pass@]host:port
        pattern = r'(?:(\w+)://)?(?:([^:]+):([^@]+)@)?([^:]+):(\d+)'
        match = re.match(pattern, proxy_str)
        
        if not match:
            raise ValueError(f"Invalid proxy string format: {proxy_str}")
        
        protocol, username, password, host, port = match.groups()
        
        # Default to HTTP if no protocol specified
        proxy_type = ProxyType(protocol.lower()) if protocol else ProxyType.HTTP
        
        return Proxy(
            host=host,
            port=int(port),
            proxy_type=proxy_type,
            username=username,
            password=password
        )
    
    def _parse_proxy_dict(self, proxy_dict: Dict[str, Any]) -> Proxy:
        """Parse proxy from dictionary format"""
        return Proxy(
            host=proxy_dict['host'],
            port=proxy_dict['port'],
            proxy_type=ProxyType(proxy_dict.get('type', 'http').lower()),
            username=proxy_dict.get('username'),
            password=proxy_dict.get('password'),
            protocol=proxy_dict.get('protocol')
        )
    
    def get_next_proxy(self) -> Optional[Proxy]:
        """
        Get the next proxy based on rotation strategy.
        
        Returns:
            Proxy object or None if no proxies available
        """
        with self._lock:
            if not self.proxies:
                return None
            
            # Filter working proxies
            working_proxies = self._get_working_proxies()
            
            if not working_proxies:
                logger.warning("No working proxies available")
                return None
            
            # Select based on strategy
            if self.rotation_strategy == ProxyRotationStrategy.ROUND_ROBIN:
                proxy = self._round_robin_select(working_proxies)
            elif self.rotation_strategy == ProxyRotationStrategy.RANDOM:
                proxy = self._random_select(working_proxies)
            elif self.rotation_strategy == ProxyRotationStrategy.LEAST_USED:
                proxy = self._least_used_select(working_proxies)
            elif self.rotation_strategy == ProxyRotationStrategy.BEST_PERFORMANCE:
                proxy = self._best_performance_select(working_proxies)
            else:
                proxy = working_proxies[0]
            
            proxy.mark_used()
            return proxy
    
    def _get_working_proxies(self) -> List[Proxy]:
        """Get list of working proxies, potentially retrying failed ones"""
        working = []
        current_time = time.time()
        
        for proxy in self.proxies:
            if proxy._is_working:
                working.append(proxy)
            elif self.retry_failed_after and proxy._last_used:
                # Check if enough time has passed to retry
                time_since_failure = current_time - proxy._last_used
                if time_since_failure >= self.retry_failed_after:
                    logger.info(f"Retrying previously failed proxy: {proxy}")
                    proxy.mark_working()
                    proxy._failures = 0  # Reset failure count
                    working.append(proxy)
        
        return working
    
    def _round_robin_select(self, proxies: List[Proxy]) -> Proxy:
        """Round-robin selection"""
        proxy = proxies[self._current_index % len(proxies)]
        self._current_index += 1
        return proxy
    
    def _random_select(self, proxies: List[Proxy]) -> Proxy:
        """Random selection"""
        return random.choice(proxies)
    
    def _least_used_select(self, proxies: List[Proxy]) -> Proxy:
        """Select proxy with fewest requests"""
        return min(proxies, key=lambda p: p._requests)
    
    def _best_performance_select(self, proxies: List[Proxy]) -> Proxy:
        """Select proxy with best success rate"""
        return max(proxies, key=lambda p: p.get_success_rate())
    
    def report_success(self, proxy: Proxy) -> None:
        """Report successful proxy usage"""
        with self._lock:
            proxy.mark_working()
    
    def report_failure(self, proxy: Proxy) -> None:
        """Report proxy failure and potentially remove it"""
        with self._lock:
            proxy.mark_failed()
            
            if proxy._failures >= self.max_failures:
                proxy.mark_not_working()
                
                if self.remove_failed:
                    logger.warning(f"Removing failed proxy from pool: {proxy}")
                    if proxy in self.proxies:
                        self.proxies.remove(proxy)
    
    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Get next proxy as dictionary for requests library"""
        proxy = self.get_next_proxy()
        return proxy.get_dict() if proxy else None
    
    def get_proxy_url(self) -> Optional[str]:
        """Get next proxy as URL string"""
        proxy = self.get_next_proxy()
        return proxy.get_url() if proxy else None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all proxies"""
        with self._lock:
            return {
                'total_proxies': len(self.proxies),
                'working_proxies': sum(1 for p in self.proxies if p._is_working),
                'rotation_strategy': self.rotation_strategy.value,
                'proxies': [p.get_stats() for p in self.proxies]
            }
    
    def get_working_count(self) -> int:
        """Get count of working proxies"""
        with self._lock:
            return sum(1 for p in self.proxies if p._is_working)
    
    def reset_stats(self) -> None:
        """Reset statistics for all proxies"""
        with self._lock:
            for proxy in self.proxies:
                proxy._requests = 0
                proxy._failures = 0
                proxy._is_working = True
            logger.info("Proxy statistics reset")
    
    def __len__(self) -> int:
        return len(self.proxies)
    
    def __bool__(self) -> bool:
        return len(self.proxies) > 0


def load_proxies_from_file(file_path: str) -> List[Proxy]:
    """
    Load proxies from a text file.
    
    Format: One proxy per line
    - http://host:port
    - http://user:pass@host:port
    - host:port
    
    Args:
        file_path: Path to proxy list file
        
    Returns:
        List of Proxy objects
    """
    proxies = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                try:
                    manager = ProxyManager()
                    proxy = manager._parse_proxy_string(line)
                    proxies.append(proxy)
                except ValueError as e:
                    logger.warning(f"Invalid proxy on line {line_num}: {line} - {e}")
        
        logger.info(f"Loaded {len(proxies)} proxies from {file_path}")
        return proxies
        
    except FileNotFoundError:
        logger.error(f"Proxy file not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading proxies from file: {e}")
        return []



