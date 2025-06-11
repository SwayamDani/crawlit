#!/usr/bin/env python3
"""
content_extractor.py - Extract detailed content from HTML pages
Supports both synchronous and asynchronous operations
"""

import logging
import re
import asyncio
from typing import Dict, Any, Optional, Union
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ContentExtractor:
    """
    Extract detailed content from HTML pages including metadata, headings, and more
    Supports both synchronous and asynchronous operations
    """
    
    def __init__(self):
        """Initialize the content extractor"""
        self.page_type_patterns = {
            'home': [r'^/$', r'^/index\.html$', r'^/home$'],
            'about': [r'/about', r'/company', r'/who-we-are'],
            'contact': [r'/contact', r'/reach-us', r'/get-in-touch'],
            'product': [r'/product', r'/item', r'/shop'],
            'blog': [r'/blog', r'/news', r'/articles'],
            'login': [r'/login', r'/signin', r'/account'],
            'faq': [r'/faq', r'/help', r'/support'],
            'search': [r'/search', r'/find'],
            'category': [r'/category', r'/cat', r'/department']
        }
    
    def extract_content(self, html_content, url, response=None):
        """
        Extract detailed content from an HTML page (synchronous version)
        
        Args:
            html_content: The HTML content to parse
            url: The URL of the page
            response: Optional requests.Response object to get headers
            
        Returns:
            dict: Dictionary containing extracted content
        """
        return self._process_content(html_content, url, response)
        
    async def extract_content_async(self, html_content, url, response=None):
        """
        Extract detailed content from an HTML page (asynchronous version)
        
        Args:
            html_content: The HTML content to parse
            url: The URL of the page
            response: Optional aiohttp.ClientResponse object to get headers
            
        Returns:
            dict: Dictionary containing extracted content
        """
        # Since HTML parsing is CPU-bound, we can run it in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._process_content, html_content, url, response)
    
    def _process_content(self, html_content, url, response=None):
        """
        Internal method that handles the actual content extraction logic
        Used by both sync and async methods
        
        Args:
            html_content: The HTML content to parse
            url: The URL of the page
            response: Optional response object to get headers
            
        Returns:
            dict: Dictionary containing extracted content
        """
        # Initialize result dictionary
        result = {}
        
        # Convert to string if bytes
        if isinstance(html_content, bytes):
            try:
                html_content = html_content.decode('utf-8')
            except UnicodeDecodeError:
                html_content = html_content.decode('latin-1')
        
        # Parse HTML with BeautifulSoup
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                result['title'] = title_tag.get_text().strip()
            else:
                result['title'] = None
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.has_attr('content'):
                result['meta_description'] = meta_desc['content'].strip()
            else:
                result['meta_description'] = None
            
            # Extract meta keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.has_attr('content'):
                result['meta_keywords'] = [k.strip() for k in meta_keywords['content'].split(',')]
            else:
                result['meta_keywords'] = []
            
            # Extract canonical URL
            canonical_link = soup.find('link', attrs={'rel': 'canonical'})
            if canonical_link and canonical_link.has_attr('href'):
                result['canonical_url'] = canonical_link['href'].strip()
            else:
                result['canonical_url'] = None
            
            # Extract HTML lang attribute
            html_tag = soup.find('html')
            if html_tag and html_tag.has_attr('lang'):
                result['language'] = html_tag['lang'].strip()
            else:
                result['language'] = None
            
            # Extract all headings in hierarchical order
            result['headings'] = self._extract_headings(soup)
            
            # Extract images with surrounding text
            result['images_with_context'] = self._extract_images_with_context(soup)
            
            # Determine page type based on URL
            result['page_type'] = self._determine_page_type(url)
            
            # Extract last-modified date
            result['last_modified'] = self._extract_last_modified(soup, response)
            
            # Include HTTP status code and headers if response is provided
            if response:
                if hasattr(response, 'status_code'):  # requests Response
                    result['http_status'] = response.status_code
                    result['http_headers'] = dict(response.headers)
                elif hasattr(response, 'status'):     # aiohttp Response
                    result['http_status'] = response.status
                    result['http_headers'] = dict(response.headers)
            
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            result['error'] = str(e)
        
        return result
    
    def _extract_headings(self, soup):
        """Extract all heading tags (h1-h6) maintaining hierarchy"""
        headings = []
        for i in range(1, 7):  # For h1 through h6
            for heading in soup.find_all(f'h{i}'):
                headings.append({
                    'level': i,
                    'text': heading.get_text().strip()
                })
        return headings
    
    def _extract_images_with_context(self, soup):
        """
        Extract images with comprehensive context including captions, surrounding text,
        alt text, and structural information to provide rich image context
        """
        images_with_context = []
        
        # Track image positions to provide document flow context
        total_images = len(soup.find_all('img'))
        img_position = 0
        
        for img in soup.find_all('img'):
            img_position += 1
            
            # Extract all possible image attributes
            img_data = {
                # Basic attributes
                'src': img.get('src'),
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', ''),
                'loading': img.get('loading', ''),  # lazy, eager, auto
                'srcset': img.get('srcset', ''),
                'sizes': img.get('sizes', ''),
                'class': img.get('class', []),
                'id': img.get('id', ''),
                
                # Positional information
                'position': {
                    'index': img_position,
                    'total_images': total_images,
                    'relative_position': f"{img_position}/{total_images}"
                },
                
                # Context fields to be populated
                'context': '',
                'caption': '',
                'nearby_headings': [],
                'related_links': [],
                'relevance_score': 0
            }
            
            # 1. Look for dedicated caption (figcaption)
            figure_parent = self._find_parent_by_tag(img, 'figure')
            if figure_parent:
                figcaption = figure_parent.find('figcaption')
                if figcaption:
                    img_data['caption'] = figcaption.get_text().strip()
                    # If we found a proper caption, increase relevance score
                    img_data['relevance_score'] += 4
            
            # 2. Extract nearby headings for context
            img_data['nearby_headings'] = self._find_nearby_headings(img, soup)
            if img_data['nearby_headings']:
                img_data['relevance_score'] += len(img_data['nearby_headings'])
            
            # 3. Find closest link if the image is inside or near an anchor
            img_data['related_links'] = self._extract_related_links(img)
            
            # 4. Find surrounding context (nearby text elements)
            context_elements = []
            
            # 4.1. Look for previous siblings that might provide context
            prev_elements = self._get_previous_content_elements(img, max_elements=2)
            context_elements.extend(prev_elements)
            
            # 4.2. Look for parent's text if it's relevant
            parent_context = self._extract_parent_context(img)
            if parent_context:
                context_elements.append(parent_context)
                img_data['relevance_score'] += 2  # Direct parent context is valuable
            
            # 4.3. Look for next siblings that might provide context
            next_elements = self._get_next_content_elements(img, max_elements=2)
            context_elements.extend(next_elements)
            
            # 5. If no context was found but we have alt text, that becomes the primary context
            if not context_elements and img_data['alt']:
                context_elements.append(f"Image described as: {img_data['alt']}")
                img_data['relevance_score'] += 1
            
            # 6. Look for aria-label as potential context
            aria_label = img.get('aria-label', '')
            if aria_label:
                context_elements.append(f"Image labeled as: {aria_label}")
                img_data['relevance_score'] += 1
            
            # 7. Check for structured data about the image
            if img.get('itemprop') or img.parent.get('itemprop'):
                itemprop = img.get('itemprop') or img.parent.get('itemprop')
                img_data['structured_data'] = {'itemprop': itemprop}
                img_data['relevance_score'] += 2
            
            # 8. Calculate a relevance score based on image attributes
            if img_data['alt']:
                img_data['relevance_score'] += 2
            if img_data['title']:
                img_data['relevance_score'] += 1
            if img.get('id'):
                img_data['relevance_score'] += 2  # Images with IDs are often important
            
            # Combine all context elements into a cohesive context string
            img_data['context'] = ' '.join([elem for elem in context_elements if elem])
            
            # Add to our list
            images_with_context.append(img_data)
        
        # Sort by relevance score if we have multiple images
        if images_with_context:
            images_with_context.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return images_with_context
        
    def _find_parent_by_tag(self, element, tag_name):
        """Find the closest parent element with the given tag name"""
        parent = element.parent
        while parent:
            if parent.name == tag_name:
                return parent
            parent = parent.parent
        return None
        
    def _find_nearby_headings(self, img, soup):
        """Find headings that might be related to the image"""
        headings = []
        
        # Look for headings that precede the image (up to 2)
        current = img
        distance = 0
        max_heading_distance = 3  # Max number of elements to look back
        
        while current and distance < max_heading_distance:
            current = current.previous_element
            if current and current.name and current.name.startswith('h') and len(current.name) == 2:
                # It's a heading element (h1-h6)
                try:
                    level = int(current.name[1])
                    if 1 <= level <= 6:  # Valid heading level
                        headings.append({
                            'level': level, 
                            'text': current.get_text().strip()
                        })
                        if len(headings) >= 2:  # Maximum 2 previous headings
                            break
                except ValueError:
                    pass  # Not a valid heading level
            distance += 1
            
        return headings
        
    def _extract_related_links(self, img):
        """Extract links related to the image"""
        related_links = []
        
        # Check if image itself is inside an anchor
        parent_anchor = self._find_parent_by_tag(img, 'a')
        if parent_anchor and parent_anchor.has_attr('href'):
            related_links.append({
                'href': parent_anchor['href'],
                'text': parent_anchor.get_text().strip(),
                'relationship': 'parent'
            })
        
        # Look for adjacent links (siblings)
        next_element = img.next_sibling
        prev_element = img.previous_sibling
        
        # Check next sibling for link
        if next_element and next_element.name == 'a' and next_element.has_attr('href'):
            related_links.append({
                'href': next_element['href'],
                'text': next_element.get_text().strip(),
                'relationship': 'next_sibling'
            })
            
        # Check previous sibling for link
        if prev_element and prev_element.name == 'a' and prev_element.has_attr('href'):
            related_links.append({
                'href': prev_element['href'],
                'text': prev_element.get_text().strip(),
                'relationship': 'previous_sibling'
            })
            
        return related_links
        
    def _get_previous_content_elements(self, element, max_elements=2):
        """Get meaningful text from previous elements"""
        content_elements = []
        prev_element = element.previous_sibling
        
        while prev_element and len(content_elements) < max_elements:
            if prev_element.name in ['p', 'div', 'span', 'section', 'article']:
                text = prev_element.get_text().strip()
                if text:
                    content_elements.insert(0, text)  # Insert at beginning to maintain order
            prev_element = prev_element.previous_sibling
            
        return content_elements
        
    def _get_next_content_elements(self, element, max_elements=2):
        """Get meaningful text from next elements"""
        content_elements = []
        next_element = element.next_sibling
        
        while next_element and len(content_elements) < max_elements:
            if next_element.name in ['p', 'div', 'span', 'section', 'article']:
                text = next_element.get_text().strip()
                if text:
                    content_elements.append(text)
            next_element = next_element.next_sibling
            
        return content_elements
        
    def _extract_parent_context(self, img):
        """Extract context from the parent element if relevant"""
        if not img.parent or img.parent.name in ['a', 'body', 'html']:
            return None
            
        # Get all text from parent except the image itself
        parent_elements = [elem for elem in img.parent.contents if elem != img]
        parent_text = ''.join(str(elem) for elem in parent_elements)
        
        # Clean the text using BeautifulSoup
        if parent_text.strip():
            soup_parent = BeautifulSoup(parent_text, 'html.parser')
            clean_parent_text = soup_parent.get_text().strip()
            return clean_parent_text
            
        return None
    
    def _determine_page_type(self, url):
        """Determine page type based on URL pattern matching"""
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        for page_type, patterns in self.page_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, path):
                    return page_type
        
        # Default to 'other' if no match is found
        return 'other'
    
    def _extract_last_modified(self, soup, response=None):
        """Extract last-modified date from HTTP headers or meta tags"""
        # First check HTTP headers if response is provided
        if response and 'Last-Modified' in response.headers:
            return response.headers['Last-Modified']
        
        # Then check meta tags
        meta_modified = soup.find('meta', attrs={'http-equiv': 'last-modified'})
        if meta_modified and meta_modified.has_attr('content'):
            return meta_modified['content']
        
        # Finally check schema.org metadata
        time_tag = soup.find('time', attrs={'itemprop': 'dateModified'})
        if time_tag and time_tag.has_attr('datetime'):
            return time_tag['datetime']
        
        # Return None if no last-modified date is found
        return None
