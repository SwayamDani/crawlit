from html.parser import HTMLParser
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ImageTagParser(HTMLParser):
    """Custom HTML parser for extracting image tags and their attributes."""
    
    def __init__(self):
        super().__init__()
        self.images = []
        self.current_tag = None
        self.parent_tags = []
    
    def handle_starttag(self, tag, attrs):
        # Keep track of parent tags for context
        if tag != 'img':
            self.parent_tags.append(tag)
            return
        
        # Process image tag
        attrs_dict = dict(attrs)
        
        # Skip images without src attribute or with empty src
        if 'src' not in attrs_dict or not attrs_dict['src'].strip():
            return
            
        # Create image data dictionary
        image_data = attrs_dict.copy()
        
        # Convert numeric attributes if possible
        for attr in ['width', 'height']:
            if attr in image_data:
                try:
                    image_data[attr] = int(image_data[attr])
                except (ValueError, TypeError):
                    pass
        
        # Check if image is likely decorative (no alt text)
        image_data['decorative'] = 'alt' not in image_data or not image_data['alt']
        
        # Add parent context if available
        if self.parent_tags:
            image_data['parent_tag'] = self.parent_tags[-1]
            
        self.images.append(image_data)
    
    def handle_endtag(self, tag):
        # Update parent tags stack
        if tag != 'img' and self.parent_tags and self.parent_tags[-1] == tag:
            self.parent_tags.pop()


class ImageExtractor:
    """Extract images and their attributes from HTML content."""
    
    def __init__(self):
        self.supported_attrs = ["src", "alt", "title", "width", "height", "loading", "class"]
    
    def extract_images(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract all images from the HTML content.
        
        Args:
            html_content: HTML content as string
            
        Returns:
            List of dictionaries containing image details
        """
        if not html_content:
            logger.warning("Empty HTML content provided for image extraction")
            return []
        
        # Create and configure parser
        parser = ImageTagParser()
        
        try:
            parser.feed(html_content)
            images = parser.images
            logger.debug(f"Extracted {len(images)} images from content")
            return images
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return []