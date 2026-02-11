#!/usr/bin/env python3
"""
sitemap.py - Sitemap parser for discovering URLs
"""

import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, urljoin
import requests
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

# Sitemap namespaces
SITEMAP_NS = {
    'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'
}


class SitemapParser:
    """
    Parser for XML sitemaps (both sitemap.xml and sitemap index files).
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize the sitemap parser.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.visited_sitemaps: Set[str] = set()
    
    def parse_sitemap(self, sitemap_url: str, session: Optional[requests.Session] = None) -> List[Dict[str, any]]:
        """
        Parse a sitemap XML file and extract URLs.
        
        Args:
            sitemap_url: URL of the sitemap XML file
            session: Optional requests session for HTTP requests
            
        Returns:
            List of dictionaries containing URL information:
            [
                {
                    'url': 'https://example.com/page',
                    'lastmod': '2023-01-01',
                    'changefreq': 'daily',
                    'priority': '1.0'
                },
                ...
            ]
        """
        if sitemap_url in self.visited_sitemaps:
            logger.debug(f"Skipping already visited sitemap: {sitemap_url}")
            return []
        
        self.visited_sitemaps.add(sitemap_url)
        
        try:
            # Fetch the sitemap
            if session:
                response = session.get(sitemap_url, timeout=self.timeout)
            else:
                response = requests.get(sitemap_url, timeout=self.timeout)
            
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Check if it's a sitemap index (contains <sitemap> elements)
            sitemap_elements = root.findall('.//sm:sitemap', SITEMAP_NS)
            if sitemap_elements:
                # This is a sitemap index, recursively parse each sitemap
                logger.info(f"Found sitemap index with {len(sitemap_elements)} sitemaps")
                all_urls = []
                for sitemap_elem in sitemap_elements:
                    loc_elem = sitemap_elem.find('sm:loc', SITEMAP_NS)
                    if loc_elem is not None:
                        nested_sitemap_url = loc_elem.text.strip()
                        logger.debug(f"Parsing nested sitemap: {nested_sitemap_url}")
                        nested_urls = self.parse_sitemap(nested_sitemap_url, session)
                        all_urls.extend(nested_urls)
                return all_urls
            
            # Otherwise, it's a regular sitemap with <url> elements
            url_elements = root.findall('.//sm:url', SITEMAP_NS)
            logger.info(f"Found {len(url_elements)} URLs in sitemap: {sitemap_url}")
            
            urls = []
            for url_elem in url_elements:
                loc_elem = url_elem.find('sm:loc', SITEMAP_NS)
                if loc_elem is not None:
                    url_info = {
                        'url': loc_elem.text.strip(),
                        'lastmod': None,
                        'changefreq': None,
                        'priority': None
                    }
                    
                    # Extract optional metadata
                    lastmod_elem = url_elem.find('sm:lastmod', SITEMAP_NS)
                    if lastmod_elem is not None:
                        url_info['lastmod'] = lastmod_elem.text.strip()
                    
                    changefreq_elem = url_elem.find('sm:changefreq', SITEMAP_NS)
                    if changefreq_elem is not None:
                        url_info['changefreq'] = changefreq_elem.text.strip()
                    
                    priority_elem = url_elem.find('sm:priority', SITEMAP_NS)
                    if priority_elem is not None:
                        url_info['priority'] = priority_elem.text.strip()
                    
                    urls.append(url_info)
            
            return urls
            
        except requests.RequestException as e:
            logger.error(f"Error fetching sitemap {sitemap_url}: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"Error parsing sitemap XML {sitemap_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing sitemap {sitemap_url}: {e}")
            return []
    
    async def parse_sitemap_async(
        self,
        sitemap_url: str,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[Dict[str, any]]:
        """
        Parse a sitemap XML file asynchronously and extract URLs.
        
        Args:
            sitemap_url: URL of the sitemap XML file
            session: Optional aiohttp session for HTTP requests
            
        Returns:
            List of dictionaries containing URL information
        """
        if sitemap_url in self.visited_sitemaps:
            logger.debug(f"Skipping already visited sitemap: {sitemap_url}")
            return []
        
        self.visited_sitemaps.add(sitemap_url)
        
        try:
            # Fetch the sitemap
            if session:
                async with session.get(sitemap_url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    response.raise_for_status()
                    content = await response.read()
            else:
                async with aiohttp.ClientSession() as temp_session:
                    async with temp_session.get(sitemap_url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                        response.raise_for_status()
                        content = await response.read()
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Check if it's a sitemap index (contains <sitemap> elements)
            sitemap_elements = root.findall('.//sm:sitemap', SITEMAP_NS)
            if sitemap_elements:
                # This is a sitemap index, recursively parse each sitemap
                logger.info(f"Found sitemap index with {len(sitemap_elements)} sitemaps")
                all_urls = []
                for sitemap_elem in sitemap_elements:
                    loc_elem = sitemap_elem.find('sm:loc', SITEMAP_NS)
                    if loc_elem is not None:
                        nested_sitemap_url = loc_elem.text.strip()
                        logger.debug(f"Parsing nested sitemap: {nested_sitemap_url}")
                        nested_urls = await self.parse_sitemap_async(nested_sitemap_url, session)
                        all_urls.extend(nested_urls)
                return all_urls
            
            # Otherwise, it's a regular sitemap with <url> elements
            url_elements = root.findall('.//sm:url', SITEMAP_NS)
            logger.info(f"Found {len(url_elements)} URLs in sitemap: {sitemap_url}")
            
            urls = []
            for url_elem in url_elements:
                loc_elem = url_elem.find('sm:loc', SITEMAP_NS)
                if loc_elem is not None:
                    url_info = {
                        'url': loc_elem.text.strip(),
                        'lastmod': None,
                        'changefreq': None,
                        'priority': None
                    }
                    
                    # Extract optional metadata
                    lastmod_elem = url_elem.find('sm:lastmod', SITEMAP_NS)
                    if lastmod_elem is not None:
                        url_info['lastmod'] = lastmod_elem.text.strip()
                    
                    changefreq_elem = url_elem.find('sm:changefreq', SITEMAP_NS)
                    if changefreq_elem is not None:
                        url_info['changefreq'] = changefreq_elem.text.strip()
                    
                    priority_elem = url_elem.find('sm:priority', SITEMAP_NS)
                    if priority_elem is not None:
                        url_info['priority'] = priority_elem.text.strip()
                    
                    urls.append(url_info)
            
            return urls
            
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching sitemap {sitemap_url}: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"Error parsing sitemap XML {sitemap_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing sitemap {sitemap_url}: {e}")
            return []
    
    def get_urls_from_sitemap(self, sitemap_url: str, session: Optional[requests.Session] = None) -> List[str]:
        """
        Extract just the URLs from a sitemap (convenience method).
        
        Args:
            sitemap_url: URL of the sitemap XML file
            session: Optional requests session for HTTP requests
            
        Returns:
            List of URL strings
        """
        url_info_list = self.parse_sitemap(sitemap_url, session)
        return [url_info['url'] for url_info in url_info_list]
    
    async def get_urls_from_sitemap_async(
        self,
        sitemap_url: str,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[str]:
        """
        Extract just the URLs from a sitemap asynchronously (convenience method).
        
        Args:
            sitemap_url: URL of the sitemap XML file
            session: Optional aiohttp session for HTTP requests
            
        Returns:
            List of URL strings
        """
        url_info_list = await self.parse_sitemap_async(sitemap_url, session)
        return [url_info['url'] for url_info in url_info_list]
    
    def clear_cache(self) -> None:
        """Clear the visited sitemaps cache"""
        self.visited_sitemaps.clear()


def get_sitemaps_from_robots(robots_handler, base_url: str) -> List[str]:
    """
    Extract sitemap URLs from a robots.txt handler.
    
    Args:
        robots_handler: RobotsHandler or AsyncRobotsHandler instance
        base_url: Base URL of the site
        
    Returns:
        List of sitemap URLs
    """
    try:
        # For sync RobotsHandler
        if hasattr(robots_handler, 'get_robots_parser'):
            parser = robots_handler.get_robots_parser(base_url)
            if hasattr(parser, 'sitemap_urls'):
                return list(parser.sitemap_urls) if parser.sitemap_urls else []
        
        # For RobotsTxt compatibility class
        if hasattr(robots_handler, 'get_sitemaps'):
            return robots_handler.get_sitemaps()
        
        return []
    except Exception as e:
        logger.warning(f"Error extracting sitemaps from robots.txt: {e}")
        return []


async def get_sitemaps_from_robots_async(robots_handler, base_url: str) -> List[str]:
    """
    Extract sitemap URLs from an async robots.txt handler.
    
    Args:
        robots_handler: AsyncRobotsHandler instance
        base_url: Base URL of the site
        
    Returns:
        List of sitemap URLs
    """
    try:
        # For async handler, we need to check if it has parsed robots.txt
        # and access the parser's sitemap_urls
        if hasattr(robots_handler, 'parsers'):
            parsed_url = urlparse(base_url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            if domain in robots_handler.parsers:
                parser = robots_handler.parsers[domain]
                if hasattr(parser, 'sitemap_urls'):
                    return list(parser.sitemap_urls) if parser.sitemap_urls else []
        
        return []
    except Exception as e:
        logger.warning(f"Error extracting sitemaps from robots.txt: {e}")
        return []


