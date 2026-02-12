#!/usr/bin/env python3
"""
structured_data.py - Structured data extraction

Extracts structured data from web pages including:
- JSON-LD
- Microdata
- RDFa
- Open Graph
- Twitter Cards
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class StructuredData:
    """Container for all structured data found on a page"""
    json_ld: List[Dict[str, Any]] = field(default_factory=list)
    microdata: List[Dict[str, Any]] = field(default_factory=list)
    rdfa: List[Dict[str, Any]] = field(default_factory=list)
    open_graph: Dict[str, Any] = field(default_factory=dict)
    twitter_cards: Dict[str, Any] = field(default_factory=dict)
    meta_tags: Dict[str, str] = field(default_factory=dict)


class StructuredDataExtractor:
    """
    Extracts structured data from HTML pages.
    
    Supports:
    - JSON-LD (Schema.org)
    - Microdata (Schema.org)
    - RDFa (Resource Description Framework in Attributes)
    - Open Graph Protocol
    - Twitter Cards
    - Standard meta tags
    """
    
    def __init__(self, html_content: str, url: str = ""):
        """
        Initialize structured data extractor.
        
        Args:
            html_content: HTML content to extract from
            url: URL of the page (for context)
        """
        self.html_content = html_content
        self.url = url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.data = StructuredData()
    
    def extract_all(self) -> StructuredData:
        """
        Extract all structured data from the page.
        
        Returns:
            StructuredData object with all extracted data
        """
        self.data.json_ld = self.extract_json_ld()
        self.data.microdata = self.extract_microdata()
        self.data.rdfa = self.extract_rdfa()
        self.data.open_graph = self.extract_open_graph()
        self.data.twitter_cards = self.extract_twitter_cards()
        self.data.meta_tags = self.extract_meta_tags()
        
        total_items = (len(self.data.json_ld) + len(self.data.microdata) + 
                      len(self.data.rdfa) + bool(self.data.open_graph) + 
                      bool(self.data.twitter_cards))
        
        if total_items > 0:
            logger.info(f"Extracted {total_items} structured data item(s) from {self.url}")
        
        return self.data
    
    def extract_json_ld(self) -> List[Dict[str, Any]]:
        """
        Extract JSON-LD structured data.
        
        JSON-LD is the recommended format by Google for structured data.
        Commonly used for Schema.org markup.
        
        Returns:
            List of JSON-LD objects
        """
        json_ld_data = []
        
        # Find all script tags with type="application/ld+json"
        scripts = self.soup.find_all('script', {'type': 'application/ld+json'})
        
        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    
                    # Handle @graph arrays (multiple items in one script)
                    if isinstance(data, dict) and '@graph' in data:
                        json_ld_data.extend(data['@graph'])
                    # Handle arrays of JSON-LD objects
                    elif isinstance(data, list):
                        json_ld_data.extend(data)
                    # Single JSON-LD object
                    else:
                        json_ld_data.append(data)
                    
                    logger.debug(f"Extracted JSON-LD: {data.get('@type', 'Unknown')}")
                
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON-LD: {e}")
                except Exception as e:
                    logger.warning(f"Error extracting JSON-LD: {e}")
        
        return json_ld_data
    
    def extract_microdata(self) -> List[Dict[str, Any]]:
        """
        Extract Microdata structured data.
        
        Microdata uses HTML attributes (itemscope, itemtype, itemprop) 
        to embed structured data.
        
        Returns:
            List of microdata objects
        """
        microdata_items = []
        
        # Find all top-level items (itemscope without itemprop - not nested)
        items = self.soup.find_all(attrs={'itemscope': True})
        
        # Filter to top-level items (not nested inside other items)
        top_level_items = []
        for item in items:
            # Check if this item is nested inside another item
            parent_item = item.find_parent(attrs={'itemscope': True})
            if not parent_item or parent_item == item:
                top_level_items.append(item)
        
        for item in top_level_items:
            item_data = self._extract_microdata_item(item)
            if item_data:
                microdata_items.append(item_data)
        
        return microdata_items
    
    def _extract_microdata_item(self, item_element) -> Dict[str, Any]:
        """Extract a single microdata item"""
        item_data = {}
        
        # Get item type
        item_type = item_element.get('itemtype', '')
        if item_type:
            item_data['@type'] = item_type.split('/')[-1]  # Get last part of URL
            item_data['@context'] = '/'.join(item_type.split('/')[:-1])
        
        # Extract properties
        properties = item_element.find_all(attrs={'itemprop': True})
        
        for prop in properties:
            prop_name = prop.get('itemprop')
            
            # Skip if this property belongs to a nested item
            parent_scope = prop.find_parent(attrs={'itemscope': True})
            if parent_scope and parent_scope != item_element:
                continue
            
            # Get property value
            if prop.has_attr('itemscope'):
                # Nested item
                prop_value = self._extract_microdata_item(prop)
            elif prop.name == 'meta':
                prop_value = prop.get('content', '')
            elif prop.name == 'link':
                prop_value = prop.get('href', '')
            elif prop.name in ['img', 'audio', 'video', 'source']:
                prop_value = prop.get('src', '')
            elif prop.name == 'a':
                prop_value = prop.get('href', '')
            elif prop.name == 'time':
                prop_value = prop.get('datetime', prop.get_text(strip=True))
            else:
                prop_value = prop.get_text(strip=True)
            
            # Handle multiple properties with same name
            if prop_name in item_data:
                if not isinstance(item_data[prop_name], list):
                    item_data[prop_name] = [item_data[prop_name]]
                item_data[prop_name].append(prop_value)
            else:
                item_data[prop_name] = prop_value
        
        return item_data
    
    def extract_rdfa(self) -> List[Dict[str, Any]]:
        """
        Extract RDFa (Resource Description Framework in Attributes) data.
        
        RDFa uses attributes like vocab, typeof, property, resource, etc.
        
        Returns:
            List of RDFa objects
        """
        rdfa_items = []
        
        # Find elements with 'typeof' attribute (indicates RDFa type)
        items = self.soup.find_all(attrs={'typeof': True})
        
        # Filter to top-level items
        top_level_items = []
        for item in items:
            parent_item = item.find_parent(attrs={'typeof': True})
            if not parent_item or parent_item == item:
                top_level_items.append(item)
        
        for item in top_level_items:
            item_data = self._extract_rdfa_item(item)
            if item_data:
                rdfa_items.append(item_data)
        
        return rdfa_items
    
    def _extract_rdfa_item(self, item_element) -> Dict[str, Any]:
        """Extract a single RDFa item"""
        item_data = {}
        
        # Get type
        typeof = item_element.get('typeof', '')
        if typeof:
            item_data['@type'] = typeof
        
        # Get vocabulary
        vocab = item_element.get('vocab', '')
        if vocab:
            item_data['@context'] = vocab
        else:
            # Check parents for vocab
            parent_with_vocab = item_element.find_parent(attrs={'vocab': True})
            if parent_with_vocab:
                item_data['@context'] = parent_with_vocab.get('vocab')
        
        # Extract properties
        properties = item_element.find_all(attrs={'property': True})
        
        for prop in properties:
            # Skip if belongs to nested item
            parent_type = prop.find_parent(attrs={'typeof': True})
            if parent_type and parent_type != item_element:
                continue
            
            prop_name = prop.get('property')
            
            # Get value
            if prop.has_attr('content'):
                prop_value = prop.get('content')
            elif prop.has_attr('resource'):
                prop_value = prop.get('resource')
            elif prop.has_attr('href'):
                prop_value = prop.get('href')
            elif prop.has_attr('src'):
                prop_value = prop.get('src')
            else:
                prop_value = prop.get_text(strip=True)
            
            # Handle nested items
            if prop.has_attr('typeof'):
                prop_value = self._extract_rdfa_item(prop)
            
            # Handle multiple properties
            if prop_name in item_data:
                if not isinstance(item_data[prop_name], list):
                    item_data[prop_name] = [item_data[prop_name]]
                item_data[prop_name].append(prop_value)
            else:
                item_data[prop_name] = prop_value
        
        return item_data
    
    def extract_open_graph(self) -> Dict[str, Any]:
        """
        Extract Open Graph Protocol data.
        
        Used by Facebook and other social platforms for rich link previews.
        
        Returns:
            Dictionary of Open Graph properties
        """
        og_data = {}
        
        # Find all meta tags with property starting with 'og:'
        og_tags = self.soup.find_all('meta', attrs={'property': re.compile(r'^og:', re.I)})
        
        for tag in og_tags:
            property_name = tag.get('property', '').lower()
            content = tag.get('content', '')
            
            if property_name and content:
                # Remove 'og:' prefix
                key = property_name.replace('og:', '')
                og_data[key] = content
        
        return og_data
    
    def extract_twitter_cards(self) -> Dict[str, Any]:
        """
        Extract Twitter Card data.
        
        Used by Twitter for rich link previews.
        
        Returns:
            Dictionary of Twitter Card properties
        """
        twitter_data = {}
        
        # Find all meta tags with name starting with 'twitter:'
        twitter_tags = self.soup.find_all('meta', attrs={'name': re.compile(r'^twitter:', re.I)})
        
        for tag in twitter_tags:
            name = tag.get('name', '').lower()
            content = tag.get('content', '')
            
            if name and content:
                # Remove 'twitter:' prefix
                key = name.replace('twitter:', '')
                twitter_data[key] = content
        
        return twitter_data
    
    def extract_meta_tags(self) -> Dict[str, str]:
        """
        Extract standard meta tags.
        
        Returns:
            Dictionary of meta tag names to content
        """
        meta_data = {}
        
        # Find all meta tags with name attribute
        meta_tags = self.soup.find_all('meta', attrs={'name': True})
        
        for tag in meta_tags:
            name = tag.get('name', '').lower()
            content = tag.get('content', '')
            
            # Skip Open Graph and Twitter Cards (already extracted)
            if name.startswith(('og:', 'twitter:')):
                continue
            
            if name and content:
                meta_data[name] = content
        
        return meta_data
    
    def get_schema_types(self) -> List[str]:
        """
        Get all Schema.org types found in the page.
        
        Returns:
            List of unique Schema.org types
        """
        if not self.data.json_ld and not self.data.microdata:
            self.extract_all()
        
        types = set()
        
        # From JSON-LD
        for item in self.data.json_ld:
            if '@type' in item:
                type_val = item['@type']
                if isinstance(type_val, list):
                    types.update(type_val)
                else:
                    types.add(type_val)
        
        # From Microdata
        for item in self.data.microdata:
            if '@type' in item:
                types.add(item['@type'])
        
        return sorted(list(types))
    
    def has_schema_type(self, schema_type: str) -> bool:
        """
        Check if page has a specific Schema.org type.
        
        Args:
            schema_type: Schema.org type to check for (e.g., 'Article', 'Product')
            
        Returns:
            True if type is present
        """
        return schema_type in self.get_schema_types()
    
    def get_by_type(self, schema_type: str) -> List[Dict[str, Any]]:
        """
        Get all structured data items of a specific type.
        
        Args:
            schema_type: Schema.org type to filter by
            
        Returns:
            List of matching items
        """
        if not self.data.json_ld and not self.data.microdata:
            self.extract_all()
        
        results = []
        
        # Search JSON-LD
        for item in self.data.json_ld:
            if '@type' in item:
                type_val = item['@type']
                if (isinstance(type_val, str) and type_val == schema_type) or \
                   (isinstance(type_val, list) and schema_type in type_val):
                    results.append(item)
        
        # Search Microdata
        for item in self.data.microdata:
            if item.get('@type') == schema_type:
                results.append(item)
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert all structured data to a dictionary.
        
        Returns:
            Dictionary with all structured data
        """
        if not any([self.data.json_ld, self.data.microdata, self.data.rdfa,
                   self.data.open_graph, self.data.twitter_cards]):
            self.extract_all()
        
        return {
            'json_ld': self.data.json_ld,
            'microdata': self.data.microdata,
            'rdfa': self.data.rdfa,
            'open_graph': self.data.open_graph,
            'twitter_cards': self.data.twitter_cards,
            'meta_tags': self.data.meta_tags,
            'schema_types': self.get_schema_types()
        }


def extract_structured_data(html_content: str, url: str = "") -> StructuredData:
    """
    Convenience function to extract all structured data.
    
    Args:
        html_content: HTML content
        url: URL of the page
        
    Returns:
        StructuredData object
    """
    extractor = StructuredDataExtractor(html_content, url)
    return extractor.extract_all()

