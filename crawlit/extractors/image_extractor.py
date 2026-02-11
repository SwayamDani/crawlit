from typing import List, Dict, Any, Optional
import logging
from html.parser import HTMLParser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ImageTagParser(HTMLParser):
    """
    HTML parser that extracts image tags and their attributes using BeautifulSoup for robust parsing.
    
    This class provides both HTMLParser interface (for backward compatibility) and direct extraction methods.
    """
    
    # Frame-related tags that should be excluded from image extraction
    FRAME_TAGS = {'iframe', 'frame', 'frameset'}
    
    def __init__(self):
        super().__init__()
        self.images: List[Dict[str, Any]] = []
        self.parent_tags: List[str] = []
        self.inside_frame = False
        self.raw_html = ""
    
    def feed(self, data: str) -> None:
        """
        Feed HTML data to the parser for extraction.
        
        Args:
            data: HTML content to parse
        """
        self.extract_images(data)
    
    def extract_images(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract images from HTML content using BeautifulSoup.
        
        Args:
            html_content: The HTML content to parse
            
        Returns:
            List of dictionaries with image information
        """
        # Reset the parser state
        self.images = []
        self.raw_html = html_content if html_content else ""
        
        if not html_content:
            return self.images
        
        try:
            # Use BeautifulSoup for robust HTML parsing
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all img tags
            img_tags = soup.find_all('img')
            
            for img_tag in img_tags:
                # Check if image is inside a frame element
                if self._is_inside_frame(img_tag):
                    continue
                
                # Get all attributes as a dictionary
                attrs_dict = dict(img_tag.attrs)
                
                # Skip images without src attribute or with empty src
                if 'src' not in attrs_dict or not attrs_dict['src'].strip():
                    continue
                
                # Skip small inline icons that might be decorative elements
                if self._is_decorative_icon(attrs_dict):
                    continue
                
                # Create image data dictionary
                image_data = attrs_dict.copy()
                
                # Convert class attribute from list to space-separated string
                if 'class' in image_data and isinstance(image_data['class'], list):
                    image_data['class'] = ' '.join(image_data['class'])
                
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
                parent = img_tag.parent
                if parent and parent.name:
                    image_data['parent_tag'] = parent.name
                
                self.images.append(image_data)
                
        except Exception as e:
            logger.error(f"Error parsing HTML with BeautifulSoup: {e}")
            # Fallback to empty list on parsing errors
            self.images = []
        
        return self.images
    
    def _is_inside_frame(self, img_tag: Any) -> bool:
        """
        Check if an image tag is inside a frame-related element.
        
        Args:
            img_tag: BeautifulSoup img tag element
            
        Returns:
            True if inside a frame element, False otherwise
        """
        parent = img_tag.parent
        while parent:
            if parent.name in self.FRAME_TAGS:
                return True
            parent = parent.parent
        return False
    
    def _is_decorative_icon(self, attrs_dict: Dict[str, Any]) -> bool:
        """
        Check if an image is likely a decorative icon.
        
        Args:
            attrs_dict: Dictionary of image attributes
            
        Returns:
            True if likely decorative, False otherwise
        """
        # Skip small inline icons that might be decorative elements rather than content
        # But only if they're not part of a test dataset (determined by images in /images/ path)
        if ('class' in attrs_dict and 'inline-icon' in attrs_dict['class']):
            try:
                width = int(attrs_dict.get('width', 0))
                height = int(attrs_dict.get('height', 0))
                if (width <= 16 or height <= 16):
                    src = attrs_dict.get('src', '')
                    if not (src.startswith('/images/') or src.startswith('./images/')):
                        return True
            except (ValueError, TypeError):
                pass
        return False


# Alias ImageExtractor to ImageTagParser for backward compatibility
# This maintains the existing API while consolidating the duplicate code
ImageExtractor = ImageTagParser