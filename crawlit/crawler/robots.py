#!/usr/bin/env python3
"""
robots.py - Robots.txt parser and rule checker
"""

import logging
import urllib.parse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

class RobotsHandler:
    """Handler for robots.txt parsing and rule checking"""
    
    def __init__(self):
        """Initialize robots parser cache"""
        self.parsers = {}  # Cache for robot parsers by domain
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
            import urllib.request
            import urllib.error
            
            logger.info(f"Fetching robots.txt from {robots_url}")
            
            # First manually check if robots.txt exists and is valid
            req = urllib.request.Request(
                robots_url,
                headers={'User-Agent': 'crawlit/2.0'}
            )
            
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    # Check if it's a text response and not HTML
                    content_type = response.headers.get('Content-Type', '').lower()
                    if response.status == 200 and ('text/plain' in content_type or not 'html' in content_type):
                        # Valid robots.txt file found, use the standard parser
                        parser.set_url(robots_url)
                        parser.read()
                        self.parsers[domain] = parser
                        return parser
                    else:
                        # If it returns HTML or other non-text content, it's not a valid robots.txt
                        logger.warning(f"Invalid robots.txt at {robots_url} (content-type: {content_type})")
                        empty_parser = RobotFileParser()
                        self.parsers[domain] = empty_parser
                        return empty_parser
            except urllib.error.HTTPError as http_err:
                # 404 or other HTTP errors mean no robots.txt file exists
                logger.warning(f"No robots.txt found at {robots_url} (HTTP error: {http_err.code})")
                empty_parser = RobotFileParser()
                self.parsers[domain] = empty_parser
                return empty_parser
                
        except Exception as e:
            logger.warning(f"Error fetching robots.txt from {robots_url}: {e}")
            # Return a permissive parser if robots.txt couldn't be fetched
            empty_parser = RobotFileParser()
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
        
        parser = self.get_robots_parser(base_url)
        path = parsed_url.path or "/"
        
        # If path has query parameters, include them
        if parsed_url.query:
            path = f"{path}?{parsed_url.query}"
            
        can_fetch = parser.can_fetch(user_agent, path)
        
        if not can_fetch:
            self.skipped_paths.append(url)
            logger.info(f"Skipping {url} (disallowed by robots.txt)")
            
        return can_fetch
        
    def get_skipped_paths(self):
        """Get list of URLs skipped due to robots.txt rules"""
        return self.skipped_paths

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