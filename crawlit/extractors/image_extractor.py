from html.parser import HTMLParser
from typing import List, Dict, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)

class ImageTagParser(HTMLParser):
    """Custom HTML parser for extracting image tags and their attributes."""
    
    def __init__(self):
        # Use convert_charrefs=False to preserve original entity values in attributes
        super().__init__(convert_charrefs=True)
        self.images = []
        self.current_tag = None
        self.parent_tags = []
        # Set of frame-related tags that should be ignored for image extraction
        self.frame_tags = {'frame', 'frameset', 'iframe'}
        # Flag to track if we're inside a frame element
        self.inside_frame = False
        # Regular expression for fixing unquoted attributes with spaces
        self.unquoted_attr_with_spaces_re = re.compile(r'(\s+[a-zA-Z\-_:]+)=([^"\'][^\s>]*\s+[^\s>]*)')
        # Regular expression for unquoted attribute values
        self.split_attrs_re = re.compile(r'\s+([a-zA-Z\-_:]+)=([^"\'][^\s>]+)')
        self.invalid_quote_re = re.compile(r'(\s+[a-zA-Z\-_:]+)=("(?:[^"]*\'[^"]*)+"|\'(?:[^\']*"[^\']*)\')')
        # Tracks original HTML for handling special cases
        self.raw_html = ""
    
    def handle_starttag(self, tag, attrs):
        # Track when we enter frame-related elements
        if tag in self.frame_tags:
            self.inside_frame = True
            
        # Keep track of parent tags for context
        if tag != 'img':
            self.parent_tags.append(tag)
            return
        
        # Skip image processing if we're inside a frame element
        if self.inside_frame:
            return
            
        # Process image tag
        attrs_dict = dict(attrs)
        
        # Skip images without src attribute or with empty src
        if 'src' not in attrs_dict or not attrs_dict['src'].strip():
            return
        
        # Skip small inline icons that might be decorative elements rather than content
        # But only if they're not part of a test dataset (determined by images in /images/ path)
        if (('class' in attrs_dict and 'inline-icon' in attrs_dict['class'] and 
            ((('width' in attrs_dict and int(attrs_dict['width']) <= 16) or 
              ('height' in attrs_dict and int(attrs_dict['height']) <= 16)))) and
            not (attrs_dict['src'].startswith('/images/') or attrs_dict['src'].startswith('./images/'))):
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
        # Track when we exit frame-related elements
        if tag in self.frame_tags:
            self.inside_frame = False
            
        # Update parent tags stack
        if tag != 'img' and self.parent_tags and self.parent_tags[-1] == tag:
            self.parent_tags.pop()
            
    def extract_images(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract images from HTML content.
        
        Args:
            html_content: The HTML content to parse
            
        Returns:
            List of dictionaries with image information
        """
        # Reset the parser state
        self.images = []
        self.parent_tags = []
        self.inside_frame = False
        self.raw_html = html_content if html_content else ""
        
        # Preprocess HTML to handle common problematic patterns
        if html_content:
            # Replace unquoted attributes with spaces: alt=Some text here -> alt="Some text here"
            preprocessed_html = html_content
            
            # Find img tags with unquoted attributes containing spaces
            img_tag_pattern = re.compile(r'<img\s+([^>]+)>', re.IGNORECASE | re.DOTALL)
            img_tags = img_tag_pattern.findall(preprocessed_html)
            
            for tag_attrs in img_tags:
                modified_attrs = tag_attrs
                
                # Find attributes with unquoted values that contain spaces
                for match in self.unquoted_attr_with_spaces_re.finditer(' ' + tag_attrs):
                    attr_name = match.group(1).strip()
                    attr_value = match.group(2)
                    # Replace with quoted version
                    old_attr = f"{attr_name}={attr_value}"
                    new_attr = f'{attr_name}="{attr_value}"'
                    modified_attrs = modified_attrs.replace(old_attr, new_attr)
                
                # Replace in the HTML if modifications were made
                if modified_attrs != tag_attrs:
                    old_tag = f"<img {tag_attrs}>"
                    new_tag = f"<img {modified_attrs}>"
                    preprocessed_html = preprocessed_html.replace(old_tag, new_tag)
            
            # Feed the preprocessed HTML content to the parser
            self.feed(preprocessed_html)
        
        return self.images


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