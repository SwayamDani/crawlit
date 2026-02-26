#!/usr/bin/env python3
"""
robots.py - Robots.txt parser and rule checker
"""

import logging
import time
import urllib.parse
import urllib.request
import urllib.error
from collections import OrderedDict
from urllib.robotparser import RobotFileParser
from typing import Optional
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class RobotsHandler:
    """Handler for robots.txt parsing and rule checking"""

    # Maximum number of domains to keep in the in-memory cache (LRU eviction)
    _MAX_CACHE_SIZE = 256

    def __init__(self, robots_timeout: int = 10):
        """
        Initialize robots parser cache.

        Args:
            robots_timeout: HTTP timeout (seconds) for fetching robots.txt files.
        """
        self.robots_timeout = robots_timeout
        # Ordered dicts give us O(1) LRU eviction: move-to-end on hit,
        # popitem(last=False) on miss-and-full.
        self.parsers: OrderedDict = OrderedDict()
        self.robots_txt_content: OrderedDict = OrderedDict()
        self._fetch_times: dict = {}      # domain -> float (epoch seconds)
        self.cache_expiry: int = 3600     # TTL: 1 hour
        self.skipped_paths = []  # Track paths skipped due to robots.txt rules
        self._MAX_SKIPPED = 10_000  # Cap memory used by skipped-path tracking

    def _cache_set(self, domain: str, parser: RobotFileParser, robots_text: Optional[str] = None) -> None:
        """Insert/update a domain in the LRU cache, evicting the oldest entry if full."""
        # Remove existing entry (will be re-inserted at end = most-recent)
        self.parsers.pop(domain, None)
        if len(self.parsers) >= self._MAX_CACHE_SIZE:
            self.parsers.popitem(last=False)  # Evict LRU
        self.parsers[domain] = parser
        self._fetch_times[domain] = time.time()

        if robots_text is not None:
            self.robots_txt_content.pop(domain, None)
            if len(self.robots_txt_content) >= self._MAX_CACHE_SIZE:
                self.robots_txt_content.popitem(last=False)
            self.robots_txt_content[domain] = robots_text

    def _is_cache_expired(self, domain: str) -> bool:
        """Return True if the cached robots.txt for domain has expired or is absent."""
        fetch_time = self._fetch_times.get(domain)
        if fetch_time is None:
            return True
        return (time.time() - fetch_time) > self.cache_expiry

    def get_robots_parser(self, base_url):
        """
        Get or create a parser for the domain's robots.txt.

        Results are cached with LRU eviction (max 256 domains) and a 1-hour TTL.

        Args:
            base_url: The base URL of the site

        Returns:
            RobotFileParser: A parser for the domain's robots.txt
        """
        parsed_url = urllib.parse.urlparse(base_url)
        domain = parsed_url.netloc

        # Return cached parser if still fresh
        if domain in self.parsers and not self._is_cache_expired(domain):
            # Move to end to mark as recently used (LRU)
            self.parsers.move_to_end(domain)
            return self.parsers[domain]

        robots_url = f"{parsed_url.scheme}://{domain}/robots.txt"

        try:
            logger.info(f"Fetching robots.txt from {robots_url}")

            try:
                from requests import get
                response = get(
                    robots_url,
                    timeout=self.robots_timeout,
                    allow_redirects=True,
                    headers={'User-Agent': 'crawlit/1.0'}
                )

                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'text/plain' in content_type or 'html' not in content_type:
                        parser = RobotFileParser()
                        parser.parse(response.text.splitlines())
                        self._cache_set(domain, parser, response.text)
                        return parser
                    else:
                        logger.warning(f"Invalid robots.txt at {robots_url} (content-type: {content_type})")
                        empty_parser = RobotFileParser()
                        empty_parser.parse([])
                        self._cache_set(domain, empty_parser)
                        return empty_parser
                else:
                    logger.warning(f"No robots.txt found at {robots_url} (HTTP status: {response.status_code})")
                    empty_parser = RobotFileParser()
                    empty_parser.parse([])
                    self._cache_set(domain, empty_parser)
                    return empty_parser

            except Exception as http_err:
                logger.warning(f"Error fetching robots.txt from {robots_url}: {http_err}")
                empty_parser = RobotFileParser()
                empty_parser.parse([])
                self._cache_set(domain, empty_parser)
                return empty_parser

        except Exception as e:
            logger.warning(f"Error fetching robots.txt from {robots_url}: {e}")
            empty_parser = RobotFileParser()
            empty_parser.parse([])
            self._cache_set(domain, empty_parser)
            return empty_parser

    def can_fetch(self, url, user_agent):
        """
        Check if a URL can be fetched according to robots.txt rules
        
        Args:
            url: The URL to check
            user_agent: The user agent to check rules for
            
        Returns:
            bool: True if URL can be fetched, False otherwise
        """
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
        base_url = f"{parsed_url.scheme}://{domain}"
        path = parsed_url.path or "/"
        
        # If path has query parameters, include them
        if parsed_url.query:
            path = f"{path}?{parsed_url.query}"
        
        # Get the parser for this domain and use the standard parser
        parser = self.get_robots_parser(base_url)
        is_allowed = parser.can_fetch(user_agent, path)
        
        if not is_allowed:
            # Only log and track URLs that are explicitly disallowed by robots.txt
            if len(self.skipped_paths) < self._MAX_SKIPPED:
                self.skipped_paths.append(url)
            logger.info(f"Skipping {url} (disallowed by robots.txt)")

        return is_allowed
        
    def get_skipped_paths(self):
        """Get list of URLs skipped due to robots.txt rules"""
        return self.skipped_paths

    def get_crawl_delay(self, url: str, user_agent: str = "*") -> Optional[float]:
        """
        Extract Crawl-delay from robots.txt for a URL and user agent.

        Args:
            url: The URL to check
            user_agent: The user agent to check rules for (default: "*")

        Returns:
            Crawl-delay in seconds, or None if not specified
        """
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc

        if domain not in self.robots_txt_content:
            return None

        lines = self.robots_txt_content[domain].splitlines()
        current_agent = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.lower().startswith('user-agent:'):
                current_agent = line.split(':', 1)[1].strip()
            elif line.lower().startswith('crawl-delay:'):
                if current_agent in (user_agent, '*'):
                    try:
                        return float(line.split(':', 1)[1].strip())
                    except ValueError:
                        pass
        return None


class AsyncRobotsHandler:
    """Asynchronous handler for robots.txt files.

    This class is responsible for fetching, parsing and checking robots.txt
    rules using async/await patterns.
    """

    # Maximum number of domains to keep in the in-memory cache (LRU eviction)
    _MAX_CACHE_SIZE = 256

    def __init__(self, robots_timeout: int = 10):
        """
        Initialize the AsyncRobotsHandler.

        Args:
            robots_timeout: HTTP timeout (seconds) for fetching robots.txt files.
        """
        self.robots_timeout = robots_timeout
        self.parsers: OrderedDict = OrderedDict()  # LRU cache: domain -> RobotFileParser
        self.robots_txt_content: OrderedDict = OrderedDict()  # LRU cache: domain -> text
        self.last_fetch_time: dict = {}  # domain -> float
        self.cache_expiry: int = 3600  # Cache robots.txt for 1 hour by default
        self.skipped_paths = []  # Track paths skipped due to robots.txt rules
        self._MAX_SKIPPED = 10_000  # Cap memory used by skipped-path tracking

    def _lru_set(self, domain: str, parser: RobotFileParser, robots_text: Optional[str] = None) -> None:
        """Insert/update a domain in the LRU parser cache."""
        self.parsers.pop(domain, None)
        if len(self.parsers) >= self._MAX_CACHE_SIZE:
            self.parsers.popitem(last=False)
        self.parsers[domain] = parser
        self.last_fetch_time[domain] = time.time()

        if robots_text is not None:
            self.robots_txt_content.pop(domain, None)
            if len(self.robots_txt_content) >= self._MAX_CACHE_SIZE:
                self.robots_txt_content.popitem(last=False)
            self.robots_txt_content[domain] = robots_text
    
    async def can_fetch(self, url: str, user_agent: str) -> bool:
        """
        Check if a URL can be fetched according to robots.txt rules.
        
        Args:
            url: URL to check
            user_agent: User agent string to use for checking permissions
            
        Returns:
            bool: True if URL can be fetched, False otherwise
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            path = parsed_url.path
            if not path:
                path = '/'
                
            # Add query parameters if present
            if parsed_url.query:
                path = f"{path}?{parsed_url.query}"
            
            # Check if we need to fetch/update the robots.txt
            if domain not in self.parsers or self._is_cache_expired(domain):
                await self._fetch_robots_txt(domain, user_agent)
            else:
                # Mark as recently used for LRU tracking
                self.parsers.move_to_end(domain)

            # If we have a parser for this domain, check if we can fetch the URL
            if domain in self.parsers:
                parser = self.parsers[domain]
                can_fetch = parser.can_fetch(user_agent, url)
                if not can_fetch:
                    # Add URL to skipped paths if disallowed by robots.txt
                    logger.info(f"Skipping {url} (disallowed by robots.txt)")
                    if len(self.skipped_paths) < self._MAX_SKIPPED:
                        self.skipped_paths.append(url)
                return can_fetch
            
            # If we couldn't get a parser, we assume it's allowed
            return True
            
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {str(e)}")
            # On error, we default to allowing the URL
            return True
    
    async def _fetch_robots_txt(self, domain: str, user_agent: str) -> None:
        """
        Fetch and parse the robots.txt file for a domain.

        Args:
            domain: Base domain URL (e.g., "https://example.com")
            user_agent: User agent string to use when fetching
        """
        robots_url = f"{domain}/robots.txt"
        logger.debug(f"Fetching robots.txt from {robots_url}")

        _permissive = ["User-agent: *", "Allow: /"]

        def _make_permissive_parser() -> RobotFileParser:
            p = RobotFileParser()
            p.set_url(robots_url)
            p.parse(_permissive)
            return p

        try:
            headers = {"User-Agent": user_agent}
            timeout_obj = aiohttp.ClientTimeout(total=self.robots_timeout)
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, headers=headers, timeout=timeout_obj) as response:
                    if response.status == 200:
                        robots_txt = await response.text()
                        parser = RobotFileParser()
                        parser.set_url(robots_url)
                        parser.parse(robots_txt.splitlines())
                        self._lru_set(domain, parser, robots_txt)

                    elif response.status == 404:
                        self._lru_set(domain, _make_permissive_parser())

                    else:
                        logger.warning(f"Failed to fetch robots.txt from {robots_url} (HTTP {response.status})")
                        self._lru_set(domain, _make_permissive_parser())

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching robots.txt from {robots_url}")
            self._lru_set(domain, _make_permissive_parser())

        except Exception as e:
            logger.error(f"Error fetching robots.txt from {robots_url}: {str(e)}")
            self._lru_set(domain, _make_permissive_parser())
    
    def _is_cache_expired(self, domain: str) -> bool:
        """
        Check if the cached robots.txt for a domain has expired.
        
        Args:
            domain: Domain to check
            
        Returns:
            bool: True if cache has expired or doesn't exist, False otherwise
        """
        if domain not in self.last_fetch_time:
            return True
        
        elapsed = time.time() - self.last_fetch_time[domain]
        return elapsed > self.cache_expiry
    
    def clear_cache(self) -> None:
        """Clear the robots.txt parser cache."""
        self.parsers.clear()
        self.last_fetch_time.clear()
    
    async def get_skipped_paths(self) -> list:
        """
        Get list of URLs skipped due to robots.txt rules.
        
        Returns:
            list: URLs that were skipped due to robots.txt disallow rules
        """
        return self.skipped_paths
    
    async def get_crawl_delay(self, url: str, user_agent: str = "*") -> Optional[float]:
        """
        Extract crawl-delay from robots.txt for a specific URL and user agent (async version).
        
        Args:
            url: The URL to check crawl-delay for
            user_agent: The user agent to check rules for (default: "*")
            
        Returns:
            Crawl-delay in seconds, or None if not specified
        """
        parsed_url = urllib.parse.urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Check if we need to fetch/update the robots.txt
        if domain not in self.robots_txt_content or self._is_cache_expired(domain):
            await self._fetch_robots_txt(domain, user_agent)
        
        # Check if we have robots.txt content for this domain
        if domain not in self.robots_txt_content:
            return None
        
        robots_content = self.robots_txt_content[domain]
        lines = robots_content.splitlines()
        
        # Parse robots.txt to find crawl-delay for the user agent
        current_user_agent = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Check for User-agent directive
            if line.lower().startswith('user-agent:'):
                current_user_agent = line.split(':', 1)[1].strip()
                continue
            
            # Check for Crawl-delay directive
            if line.lower().startswith('crawl-delay:'):
                if current_user_agent == user_agent or current_user_agent == '*':
                    try:
                        delay = float(line.split(':', 1)[1].strip())
                        logger.debug(f"Found crawl-delay {delay}s for {domain} (user-agent: {current_user_agent})")
                        return delay
                    except ValueError:
                        logger.warning(f"Invalid crawl-delay value in robots.txt for {domain}: {line}")
        
        return None

# Add RobotsTxt class for backward compatibility with tests
class RobotsTxt:
    """
    Compatibility class for tests that expect a RobotsTxt class
    This wraps the RobotsHandler class functionality
    """
    
    def __init__(self, url, user_agent="crawlit/1.0"):
        """
        Initialize RobotsTxt with a URL and user agent
        
        Args:
            url: Base URL for robots.txt
            user_agent: User agent to check rules against
        """
        self.handler = RobotsHandler()
        self.url = url
        self.user_agent = user_agent
        self.parser = self.handler.get_robots_parser(url)
    
    def can_fetch(self, path):
        """Check if a path can be fetched"""
        full_url = urllib.parse.urljoin(self.url, path)
        return self.handler.can_fetch(full_url, self.user_agent)
    
    def get_sitemaps(self):
        """Get sitemap URLs declared in robots.txt via 'Sitemap:' directives.

        Returns:
            list: List of sitemap URL strings found in robots.txt.
        """
        parsed = urllib.parse.urlparse(self.url)
        domain = parsed.netloc
        robots_text = self.handler.robots_txt_content.get(domain)
        if not robots_text:
            return []
        sitemaps = []
        for line in robots_text.splitlines():
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                if sitemap_url:
                    sitemaps.append(sitemap_url)
        return sitemaps