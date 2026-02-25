#!/usr/bin/env python3
"""
robots.py - Robots.txt parser and rule checker
"""

import logging
import urllib.parse
import urllib.request
import urllib.error
from urllib.robotparser import RobotFileParser
from typing import Optional
import aiohttp
import asyncio
import time

logger = logging.getLogger(__name__)

class RobotsHandler:
    """Handler for robots.txt parsing and rule checking"""
    
    def __init__(self):
        """Initialize robots parser cache"""
        self.parsers = {}  # Cache for robot parsers by domain
        self.robots_txt_content = {}  # Cache robots.txt content for crawl-delay extraction
        self.skipped_paths = []  # Track paths skipped due to robots.txt rules

    def get_robots_parser(self, base_url):
        """
        Get or create a parser for the domain's robots.txt
        
        Args:
            base_url: The base URL of the site
        
        Returns:
            RobotFileParser: A parser for the domain's robots.txt
        """
        parsed_url = urllib.parse.urlparse(base_url)
        domain = parsed_url.netloc
        
        # Return cached parser if available
        if domain in self.parsers:
            return self.parsers[domain]
            
        # Create a new parser
        parser = RobotFileParser()
        robots_url = f"{parsed_url.scheme}://{domain}/robots.txt"
        
        try:
            logger.info(f"Fetching robots.txt from {robots_url}")
            
            # Use requests instead of urllib to handle redirects properly
            try:
                from requests import get
                response = get(robots_url, timeout=10, allow_redirects=True, headers={'User-Agent': 'crawlit/1.0'})
                
                # Check if the request was successful
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'text/plain' in content_type or not 'html' in content_type:
                        # Store robots.txt content for crawl-delay extraction
                        self.robots_txt_content[domain] = response.text
                        # Create a parser and feed the robots.txt content directly
                        parser = RobotFileParser()
                        parser.parse(response.text.splitlines())
                        self.parsers[domain] = parser
                        return parser
                    else:
                        # If it returns HTML or other non-text content, it's not a valid robots.txt
                        logger.warning(f"Invalid robots.txt at {robots_url} (content-type: {content_type})")
                        empty_parser = RobotFileParser()
                        # Set the url to indicate an empty robots.txt
                        empty_parser.set_url(robots_url)
                        # Read it to mark it as having been loaded
                        empty_parser.read()
                        self.parsers[domain] = empty_parser
                        return empty_parser
                else:
                    # 404 or other HTTP errors mean no robots.txt file exists
                    logger.warning(f"No robots.txt found at {robots_url} (HTTP status: {response.status_code})")
                    empty_parser = RobotFileParser()
                    # Set the url to indicate an empty robots.txt
                    empty_parser.set_url(robots_url)
                    # Read it to mark it as having been loaded
                    empty_parser.read()
                    self.parsers[domain] = empty_parser
                    return empty_parser
                    
            except Exception as http_err:
                # Any exception means we couldn't fetch robots.txt
                logger.warning(f"Error fetching robots.txt from {robots_url}: {http_err}")
                empty_parser = RobotFileParser()
                # Set the url to indicate an empty robots.txt
                empty_parser.set_url(robots_url)
                # Read it to mark it as having been loaded
                empty_parser.read()
                self.parsers[domain] = empty_parser
                return empty_parser
                
        except Exception as e:
            logger.warning(f"Error fetching robots.txt from {robots_url}: {e}")
            # Return a permissive parser if robots.txt couldn't be fetched
            empty_parser = RobotFileParser()
            # Set the url to indicate an empty robots.txt
            empty_parser.set_url(robots_url)
            # Read it to mark it as having been loaded
            empty_parser.read()
            self.parsers[domain] = empty_parser
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
    
    def __init__(self):
        """Initialize the AsyncRobotsHandler."""
        self.parsers = {}  # Dictionary to cache robots.txt parsers by domain
        self.robots_txt_content = {}  # Cache robots.txt content for crawl-delay extraction
        self.last_fetch_time = {}  # Track when we last fetched a robots.txt file
        self.cache_expiry = 3600  # Cache robots.txt for 1 hour by default
        self.skipped_paths = []  # Track paths skipped due to robots.txt rules
    
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
            
            # If we have a parser for this domain, check if we can fetch the URL
            if domain in self.parsers:
                parser = self.parsers[domain]
                can_fetch = parser.can_fetch(user_agent, url)
                if not can_fetch:
                    # Add URL to skipped paths if disallowed by robots.txt
                    logger.info(f"Skipping {url} (disallowed by robots.txt)")
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
        
        try:
            headers = {"User-Agent": user_agent}
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        robots_txt = await response.text()
                        
                        # Store robots.txt content for crawl-delay extraction
                        self.robots_txt_content[domain] = robots_txt
                        
                        # Create a parser and feed it the robots.txt content
                        parser = RobotFileParser()
                        parser.set_url(robots_url)
                        parser.parse(robots_txt.splitlines())
                        
                        # Cache the parser
                        self.parsers[domain] = parser
                        self.last_fetch_time[domain] = time.time()
                        
                    elif response.status == 404:
                        # No robots.txt found, create an "allow all" parser
                        parser = RobotFileParser()
                        parser.set_url(robots_url)
                        parser.parse(["User-agent: *", "Allow: /"])
                        
                        # Cache the parser
                        self.parsers[domain] = parser
                        self.last_fetch_time[domain] = time.time()
                        
                    else:
                        logger.warning(f"Failed to fetch robots.txt from {robots_url} (HTTP {response.status})")
                        # For other errors, we'll create a permissive parser
                        parser = RobotFileParser()
                        parser.set_url(robots_url)
                        parser.parse(["User-agent: *", "Allow: /"])
                        self.parsers[domain] = parser
                        self.last_fetch_time[domain] = time.time()
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching robots.txt from {robots_url}")
            # Create a permissive parser on timeout
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(["User-agent: *", "Allow: /"])
            self.parsers[domain] = parser
            self.last_fetch_time[domain] = time.time()
            
        except Exception as e:
            logger.error(f"Error fetching robots.txt from {robots_url}: {str(e)}")
            # Create a permissive parser on error
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(["User-agent: *", "Allow: /"])
            self.parsers[domain] = parser
            self.last_fetch_time[domain] = time.time()
    
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
        """Get sitemaps from robots.txt"""
        # Since we're using urllib.robotparser, we can access the sitemap URLs
        # directly from the parser
        return self.parser.sitemap_urls