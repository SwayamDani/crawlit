# Crawlit Extractors Documentation

## Overview

Crawlit's extractor system provides a powerful and extensible framework for extracting structured data from web pages. Each extractor is a specialized plugin that analyzes HTML content and extracts specific types of information, storing the results in the `PageArtifact.extracted` dictionary under a unique key.

### Architecture

Extractors implement the `Extractor` interface with two key methods:
- `name` property: Returns a unique identifier used as the storage key
- `extract()` method: Processes HTML content and returns structured data

Both synchronous (`Extractor`) and asynchronous (`AsyncExtractor`) variants are supported.

```python
from crawlit.interfaces import Extractor
from crawlit.models import PageArtifact

class CustomExtractor(Extractor):
    @property
    def name(self) -> str:
        return "my_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        # Your extraction logic here
        return {"extracted_data": "value"}
```

## Built-in Extractors

### 1. Content Extractor

**Module**: `crawlit.extractors.ContentExtractor`

The ContentExtractor provides comprehensive content analysis and metadata extraction from HTML pages.

#### Features
- Page metadata (title, description, keywords)
- Language detection
- Heading hierarchy extraction
- Image context analysis
- Page type classification
- Last modified date detection
- HTTP status and headers integration

#### Configuration
```python
from crawlit.extractors import ContentExtractor

extractor = ContentExtractor()
```

#### Usage
```python
from crawlit import Crawler
from crawlit.extractors import ContentExtractor

crawler = Crawler(
    "https://example.com",
    extractors=[ContentExtractor()]
)
```

#### Output Structure
```python
{
    'title': 'Page Title',
    'meta_description': 'Page description from meta tag',
    'meta_keywords': ['keyword1', 'keyword2'],
    'canonical_url': 'https://example.com/canonical',
    'language': 'en',
    'page_type': 'blog',  # home, about, contact, product, etc.
    'last_modified': '2024-01-01T12:00:00Z',
    'headings': [
        {'level': 1, 'text': 'Main Heading'},
        {'level': 2, 'text': 'Subheading'}
    ],
    'images_with_context': [
        {
            'src': '/image.jpg',
            'alt': 'Image description',
            'position': {'index': 1, 'total_images': 5},
            'context': {
                'caption': 'Figure 1: Example',
                'surrounding_text': '...',
                'parent_tag': 'figure'
            }
        }
    ],
    'http_status': 200,
    'http_headers': {'content-type': 'text/html'},
    'error': None  # Present if extraction failed
}
```

#### Page Type Classification
The extractor automatically classifies pages based on URL patterns:
- `home`: Root paths, index pages
- `about`: About us, company info pages  
- `contact`: Contact, reach us pages
- `product`: Product, item, shop pages
- `blog`: Blog, news, article pages
- `login`: Login, signin, account pages
- `faq`: FAQ, help, support pages
- `search`: Search, find pages
- `category`: Category, department pages

### 2. Table Extractor

**Module**: `crawlit.extractors.tables`

Extracts HTML tables with robust parsing and multiple output formats.

#### Features
- Handles nested tables (extracts only top-level)
- Processes rowspan/colspan attributes correctly
- Filters tables by minimum size requirements
- Multiple export formats (CSV, JSON, dictionary)
- Cleans cell content (removes HTML tags, references)
- Handles malformed tables gracefully

#### Functions
```python
from crawlit.extractors.tables import extract_tables, tables_to_csv, tables_to_dict, tables_to_json

# Extract all tables
tables = extract_tables(html_content, min_rows=2, min_columns=2)

# Export to different formats
csv_files = tables_to_csv(tables, "output", "/path/to/dir")
json_data = tables_to_json(tables)
dict_data = tables_to_dict(tables, include_headers=True)
```

#### Output Structure
```python
# Raw table extraction
[
    [  # Table 1
        ['Header 1', 'Header 2', 'Header 3'],  # Row 1
        ['Cell 1', 'Cell 2', 'Cell 3'],       # Row 2
        ['Cell 4', 'Cell 5', 'Cell 6']        # Row 3
    ],
    [  # Table 2
        # ... more rows
    ]
]

# Dictionary format with headers
{
    'tables': [
        {
            'headers': ['Name', 'Age', 'City'],
            'rows': [
                ['John', '25', 'New York'],
                ['Jane', '30', 'Los Angeles']
            ]
        }
    ]
}
```

#### Performance Considerations
- Uses BeautifulSoup for robust HTML parsing
- Efficiently handles large tables with complex spanning
- Memory usage scales with table size and complexity
- Consider filtering small tables to reduce noise

### 3. Image Extractor

**Module**: `crawlit.extractors.ImageTagParser`

Extracts comprehensive image metadata and context from HTML pages.

#### Features
- All image attributes (src, alt, title, dimensions, etc.)
- Decorative image detection
- Parent element context
- Frame filtering (excludes iframe images)
- Class and ID attribute handling
- Loading attribute analysis (lazy, eager)

#### Configuration
```python
from crawlit.extractors import ImageTagParser

parser = ImageTagParser()
images = parser.extract_images(html_content)
```

#### Output Structure
```python
[
    {
        'src': '/path/to/image.jpg',
        'alt': 'Image description',
        'title': 'Image title',
        'width': 300,  # Converted to int if possible
        'height': 200,
        'loading': 'lazy',
        'srcset': 'image-small.jpg 300w, image-large.jpg 600w',
        'sizes': '(max-width: 300px) 100vw, 300px',
        'class': 'featured-image thumbnail',
        'id': 'hero-image',
        'decorative': False,  # True if no alt text
        'parent_tag': 'figure',
        # ... all other attributes from the img tag
    }
]
```

#### Best Practices
- Filter decorative images for content analysis
- Use srcset information for responsive image handling
- Check parent_tag for semantic context (figure, picture, etc.)

### 4. Keyword Extractor

**Module**: `crawlit.extractors.KeywordExtractor`

Analyzes webpage content to extract and rank relevant keywords and keyphrases.

#### Features
- Intelligent text extraction from HTML
- Stop word filtering
- Weighted keyword analysis (titles and headings have higher weight)
- Configurable minimum word length and keyword count
- Multi-language support

#### Configuration
```python
from crawlit.extractors import KeywordExtractor

extractor = KeywordExtractor(
    min_word_length=3,    # Minimum characters per keyword
    max_keywords=20       # Maximum keywords to return
)
```

#### Usage
```python
keywords = extractor.extract_keywords(html_content)
text_only = extractor.extract_text_from_html(html_content)
```

#### Output Structure
```python
[
    ('machine learning', 15.5),  # (keyword, score)
    ('artificial intelligence', 12.0),
    ('neural networks', 8.7),
    ('data science', 6.2),
    # ... more keywords ranked by relevance
]
```

#### Algorithm Details
- Extracts text with priority weighting:
  - Title text: 3x weight
  - H1 headings: 2x weight  
  - H2-H3 headings: 1x weight
  - Paragraph text: 1x weight
- Removes scripts, styles, navigation, and footer content
- Applies comprehensive stop word filtering
- Scores keywords by frequency and position importance

### 5. Form Extractor

**Module**: `crawlit.extractors.FormExtractor`

Comprehensive form analysis and field extraction with security feature detection.

#### Features
- Complete form structure analysis
- Field type detection and validation attributes
- Label association
- CSRF token detection
- CAPTCHA detection
- File upload identification
- Submit button text extraction

#### Configuration
```python
from crawlit.extractors import FormExtractor, extract_forms

extractor = FormExtractor(html_content, base_url="https://example.com")
forms = extractor.extract_all_forms()

# Or use convenience function
forms = extract_forms(html_content, base_url="https://example.com")
```

#### Output Structure
```python
[
    {
        'action': '/submit',
        'method': 'POST',
        'enctype': 'multipart/form-data',
        'form_id': 'contact-form',
        'form_class': 'form-horizontal',
        'name': 'contactForm',
        'has_file_upload': True,
        'has_captcha': True,
        'has_csrf_token': True,
        'submit_button_text': 'Send Message',
        'fieldsets': ['Personal Information', 'Message'],
        'fields': [
            {
                'name': 'email',
                'field_type': 'email',
                'label': 'Email Address',
                'placeholder': 'Enter your email',
                'required': True,
                'readonly': False,
                'disabled': False,
                'maxlength': 255,
                'pattern': r'[^@]+@[^@]+\.[^@]+',
                'options': [],  # For select/radio/checkbox
                'attributes': {'autocomplete': 'email'}
            }
        ]
    }
]
```

#### Security Features
- **CSRF Detection**: Identifies common CSRF token patterns
- **CAPTCHA Detection**: Recognizes various CAPTCHA implementations
- **File Upload Detection**: Identifies forms that accept file uploads
- **Input Validation**: Extracts client-side validation rules

#### Field Types Supported
- Text inputs (text, email, password, url, tel, etc.)
- Select dropdowns and option groups
- Textareas
- Checkboxes and radio buttons  
- Hidden fields
- File uploads
- Custom input types

### 6. Structured Data Extractor

**Module**: `crawlit.extractors.StructuredDataExtractor`

Extracts all forms of structured data embedded in web pages.

#### Features
- JSON-LD extraction (Schema.org)
- Microdata parsing
- RDFa (Resource Description Framework) extraction
- Open Graph protocol data
- Twitter Cards metadata
- Standard meta tags

#### Configuration
```python
from crawlit.extractors import StructuredDataExtractor, extract_structured_data

extractor = StructuredDataExtractor(html_content, url="https://example.com")
data = extractor.extract_all()

# Or use convenience function  
data = extract_structured_data(html_content, url="https://example.com")
```

#### Output Structure
```python
{
    'json_ld': [
        {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Article Title',
            'author': {'@type': 'Person', 'name': 'John Doe'},
            'datePublished': '2024-01-01'
        }
    ],
    'microdata': [
        {
            'type': 'http://schema.org/Product',
            'properties': {
                'name': 'Product Name',
                'price': '$99.99',
                'availability': 'in stock'
            }
        }
    ],
    'rdfa': [
        {
            'subject': 'https://example.com/article',
            'predicates': {
                'dc:title': 'Article Title',
                'dc:creator': 'Author Name'
            }
        }
    ],
    'open_graph': {
        'og:title': 'Page Title',
        'og:description': 'Page description',
        'og:image': 'https://example.com/image.jpg',
        'og:url': 'https://example.com/page'
    },
    'twitter_cards': {
        'twitter:card': 'summary_large_image',
        'twitter:title': 'Tweet Title',
        'twitter:description': 'Tweet description'
    },
    'meta_tags': {
        'description': 'Page meta description',
        'keywords': 'keyword1, keyword2',
        'author': 'Site Author'
    }
}
```

#### Schema.org Support
Comprehensive support for Schema.org vocabularies:
- Article, BlogPosting, NewsArticle
- Product, Offer, Review
- Person, Organization
- Event, Place
- Recipe, HowTo
- And many more...

### 7. Language Detector

**Module**: `crawlit.extractors.LanguageDetector`

Advanced language detection using multiple analysis methods.

#### Features
- HTML lang attribute detection
- Meta tag language extraction
- Content-based language analysis
- Character frequency patterns
- Common word detection
- URL-based language hints
- Confidence scoring

#### Configuration
```python
from crawlit.extractors import LanguageDetector, detect_language

detector = LanguageDetector(html_content, url="https://example.com")
result = detector.detect_language()

# Or use convenience function
result = detect_language(html_content, url="https://example.com")
```

#### Output Structure
```python
{
    'primary_language': 'en',  # ISO 639-1 code
    'confidence': 0.85,        # 0.0 to 1.0
    'detected_languages': [    # All detected languages with confidence
        ('en', 0.85),
        ('es', 0.12),
        ('fr', 0.03)
    ],
    'detection_methods': {     # Results from each method
        'html_lang': 'en',
        'meta_lang': 'en',
        'content_analysis': 'en',
        'common_words': 'en',
        'url_pattern': 'en'
    },
    'html_lang': 'en-US',      # Original HTML lang attribute
    'meta_lang': 'en',         # Meta Content-Language
    'content_lang': 'en'       # Content-based detection
}
```

#### Supported Languages
- **Latin script**: English, Spanish, French, German, Italian, Portuguese, Dutch, Polish, Turkish, Swedish
- **Non-Latin scripts**: Russian (Cyrillic), Japanese (Hiragana/Katakana/Kanji), Korean (Hangul), Chinese (Simplified/Traditional), Arabic, Hebrew, Thai, Greek

#### Detection Methods
1. **HTML Analysis**: Extracts lang attributes and meta tags
2. **Character Patterns**: Identifies script-specific characters
3. **Word Frequency**: Matches common words against language dictionaries
4. **URL Patterns**: Analyzes URL structure for language indicators

### 8. PDF Extractor

**Module**: `crawlit.extractors.PDFExtractor`

Extracts text and metadata from PDF files with optional OCR support.

#### Features
- Multiple backend support (pdfplumber preferred, PyPDF2 fallback)
- Text extraction from native PDFs
- Optional OCR for scanned PDFs
- Metadata extraction (title, author, creation date, etc.)
- Page count and document properties
- Error handling for corrupted PDFs

#### Configuration
```python
from crawlit.extractors import PDFExtractor, extract_pdf_text, is_pdf_available

# Check if PDF extraction is available
if is_pdf_available():
    extractor = PDFExtractor(
        backend='auto',        # 'auto', 'pdfplumber', 'pypdf2'
        enable_ocr=True,      # Enable OCR for scanned PDFs
        ocr_language='eng'    # Tesseract language code
    )
```

#### Usage
```python
# From bytes (common when fetching PDFs)
pdf_data = extractor.extract_from_bytes(pdf_bytes)

# From file path
pdf_data = extractor.extract_from_file("/path/to/document.pdf")

# Convenience function
text = extract_pdf_text(pdf_bytes)
```

#### Output Structure
```python
{
    'text': 'Extracted text content from PDF...',
    'num_pages': 10,
    'metadata': {
        'title': 'Document Title',
        'author': 'Author Name', 
        'subject': 'Document Subject',
        'creator': 'PDF Creator Application',
        'producer': 'PDF Producer',
        'creation_date': '2024-01-01T12:00:00Z',
        'modification_date': '2024-01-02T14:30:00Z'
    },
    'success': True,
    'error': None,  # Error message if extraction failed
    'backend_used': 'pdfplumber',
    'ocr_used': False
}
```

#### Dependencies
- **Required**: `pdfplumber` (preferred) or `PyPDF2` (fallback)
- **Optional OCR**: `PIL` (Pillow) and `pytesseract`

#### Performance Notes
- pdfplumber is more accurate but slower than PyPDF2
- OCR processing significantly increases extraction time
- Consider timeout settings for large documents

### 9. JavaScript Embedded Data Extractor

**Module**: `crawlit.extractors.JSEmbeddedDataExtractor`

Extracts JSON data embedded in JavaScript for modern web applications.

#### Features
- Next.js `__NEXT_DATA__` extraction
- Apollo GraphQL `__APOLLO_STATE__` extraction  
- Redux `__REDUX_STATE__` extraction
- Generic `__INITIAL_STATE__` and `__DATA__` patterns
- Nuxt.js `__NUXT__` extraction
- Application/json script blocks
- Safe JSON parsing with size limits

#### Configuration
```python
from crawlit.extractors import JSEmbeddedDataExtractor, extract_js_embedded_data

extractor = JSEmbeddedDataExtractor()
data = extractor.extract(html_content, artifact)

# Or use convenience function
data = extract_js_embedded_data(html_content)
```

#### Output Structure
```python
{
    '__NEXT_DATA__': {
        'props': {'pageProps': {...}},
        'page': '/products/123',
        'query': {'id': '123'},
        'buildId': 'abc123'
    },
    '__APOLLO_STATE__': {
        'ROOT_QUERY': {...},
        'Product:123': {...}
    },
    '__REDUX_STATE__': {
        'user': {'id': 1, 'name': 'John'},
        'cart': {'items': []}
    },
    'script_json_blocks': [
        {'id': 'config-data', 'content': {...}},
        {'class': 'app-config', 'content': {...}}
    ]
}
```

#### Supported Patterns
- `window.__NEXT_DATA__ = {...};` (Next.js)
- `window.__APOLLO_STATE__ = {...};` (Apollo GraphQL)
- `window.__REDUX_STATE__ = {...};` (Redux)
- `window.__INITIAL_STATE__ = {...};` (Generic)
- `window.__DATA__ = {...};` (Generic)
- `__NUXT__ = {...};` (Nuxt.js)
- `<script type="application/json">` blocks

#### Safety Features
- HTML content size limit (2MB)
- Script block size limit (500KB)
- Safe JSON parsing with error handling
- Prevents pathological regex performance

## Configuration Options

### Global Extractor Configuration

Most extractors support configuration through their constructor parameters:

```python
from crawlit.extractors import *

# Configure individual extractors
content_extractor = ContentExtractor()

table_extractor = extract_tables  # Function-based, no configuration needed

image_extractor = ImageTagParser()

keyword_extractor = KeywordExtractor(
    min_word_length=4,
    max_keywords=15
)

form_extractor = None  # Created per-page with base_url

structured_data_extractor = None  # Created per-page with URL

language_detector = None  # Created per-page with URL

pdf_extractor = PDFExtractor(
    backend='pdfplumber',
    enable_ocr=False,
    ocr_language='eng'
)
```

### Using Extractors with Crawler

```python
from crawlit import Crawler
from crawlit.extractors import *

# Custom extractor class for using functions
class TableExtractor:
    @property
    def name(self):
        return "tables"
    
    def extract(self, html_content, artifact):
        return extract_tables(html_content, min_rows=2, min_columns=2)

# Configure crawler with extractors
crawler = Crawler(
    start_urls=["https://example.com"],
    extractors=[
        ContentExtractor(),
        TableExtractor(),
        ImageTagParser(),
        KeywordExtractor(max_keywords=10),
        JSEmbeddedDataExtractor()
    ]
)

# Process pages
for artifact in crawler.crawl():
    print(f"Extracted data keys: {artifact.extracted.keys()}")
```

## Performance Considerations

### Memory Usage
- **Table Extractor**: Memory usage increases with table size and complexity
- **Content Extractor**: Moderate memory usage for image context analysis
- **PDF Extractor**: High memory usage for large PDF files, especially with OCR
- **Structured Data**: Minimal memory impact for most pages

### Processing Speed
- **Fastest**: Image, Keyword, Form extractors
- **Medium**: Content, Structured Data, Language detectorsLanguage, JS Data extractors  
- **Slowest**: PDF (especially with OCR), large table extraction

### Optimization Tips
1. **Filter unnecessary data**: Use minimum size thresholds for tables
2. **Disable unused features**: Turn off OCR if not needed for PDFs  
3. **Process in parallel**: Use AsyncCrawler for concurrent extraction
4. **Cache results**: Store extracted data to avoid re-processing
5. **Set timeouts**: Configure reasonable timeouts for PDF processing

### Scaling Considerations
```python
# For high-volume crawling
crawler = AsyncCrawler(
    start_urls=urls,
    extractors=[
        ContentExtractor(),
        # Only include extractors you actually need
        
    ],
    max_concurrent=10,  # Limit concurrency based on resources
    delay_ms=200       # Add delay to be respectful
)
```

## Custom Extractor Development

### Basic Extractor Template

```python
from crawlit.interfaces import Extractor
from crawlit.models import PageArtifact
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class CustomExtractor(Extractor):
    """Example custom extractor for extracting specific data types."""
    
    def __init__(self, custom_option: str = "default"):
        self.custom_option = custom_option
    
    @property
    def name(self) -> str:
        """Unique name for storing extracted data."""
        return "custom_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        """Extract custom data from HTML content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Your extraction logic here
            extracted_data = {
                'custom_field': self._extract_custom_field(soup),
                'url': artifact.url,
                'timestamp': artifact.timestamp
            }
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Custom extraction failed for {artifact.url}: {e}")
            return {'error': str(e)}
    
    def _extract_custom_field(self, soup):
        """Helper method for specific extraction logic."""
        # Implement your specific extraction logic
        elements = soup.find_all('div', class_='custom-class')
        return [elem.get_text().strip() for elem in elements]
```

### Async Extractor Template

```python
from crawlit.interfaces import AsyncExtractor
from crawlit.models import PageArtifact
import asyncio
import aiohttp

class AsyncCustomExtractor(AsyncExtractor):
    """Async extractor that can make external API calls."""
    
    @property
    def name(self) -> str:
        return "async_custom_data"
    
    async def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        """Extract data asynchronously."""
        # CPU-bound parsing in thread pool
        loop = asyncio.get_event_loop()
        parsed_data = await loop.run_in_executor(
            None, self._parse_html, html_content
        )
        
        # I/O-bound API call
        enriched_data = await self._enrich_with_api(parsed_data)
        
        return enriched_data
    
    def _parse_html(self, html_content: str) -> dict:
        """CPU-intensive parsing in thread pool."""
        # Your parsing logic here
        return {"parsed": True}
    
    async def _enrich_with_api(self, data: dict) -> dict:
        """Enrich data with external API call."""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.example.com/enrich") as response:
                api_data = await response.json()
                data.update(api_data)
        return data
```

### Advanced Features

#### Error Handling and Logging
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RobustExtractor(Extractor):
    @property
    def name(self) -> str:
        return "robust_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> Optional[dict]:
        """Robust extraction with comprehensive error handling."""
        try:
            # Validate inputs
            if not html_content or not html_content.strip():
                logger.warning(f"Empty HTML content for {artifact.url}")
                return None
            
            # Size check
            if len(html_content) > 10_000_000:  # 10MB limit
                logger.warning(f"HTML content too large for {artifact.url}")
                return None
            
            # Extraction logic with detailed error reporting
            result = self._safe_extract(html_content, artifact)
            
            if result:
                logger.info(f"Successfully extracted {len(result)} items from {artifact.url}")
            else:
                logger.info(f"No data found for {artifact.url}")
            
            return result
                
        except Exception as e:
            logger.error(f"Extraction failed for {artifact.url}: {e}", exc_info=True)
            return {"error": str(e), "url": artifact.url}
    
    def _safe_extract(self, html_content: str, artifact: PageArtifact) -> Optional[dict]:
        """Protected extraction logic."""
        # Your extraction implementation
        pass
```

#### Configuration and Validation
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ExtractorConfig:
    """Configuration for advanced extractor."""
    min_items: int = 1
    max_items: Optional[int] = None
    include_metadata: bool = True
    allowed_domains: Optional[List[str]] = None
    timeout_seconds: float = 30.0

class ConfigurableExtractor(Extractor):
    def __init__(self, config: ExtractorConfig):
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """Validate extractor configuration."""
        if self.config.min_items < 0:
            raise ValueError("min_items must be non-negative")
        
        if (self.config.max_items is not None and 
            self.config.max_items < self.config.min_items):
            raise ValueError("max_items must be >= min_items")
    
    @property
    def name(self) -> str:
        return "configurable_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> Optional[dict]:
        """Extract with configuration validation."""
        # Domain filtering
        if self.config.allowed_domains:
            from urllib.parse import urlparse
            domain = urlparse(artifact.url).netloc
            if domain not in self.config.allowed_domains:
                return None
        
        # Your extraction logic using self.config
        pass
```

## Integration Patterns

### Chainable Extractors

Create extractors that build upon each other's results:

```python
class BaseDataExtractor(Extractor):
    @property
    def name(self) -> str:
        return "base_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        # Extract foundational data
        return {"items": [...], "metadata": {...}}

class EnhancedDataExtractor(Extractor):
    @property
    def name(self) -> str:
        return "enhanced_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        # Use results from BaseDataExtractor
        base_data = artifact.extracted.get("base_data", {})
        if not base_data:
            return {}
        
        # Enhance the base data
        enhanced_items = []
        for item in base_data.get("items", []):
            enhanced_item = self._enhance_item(item)
            enhanced_items.append(enhanced_item)
        
        return {"enhanced_items": enhanced_items}
```

### Conditional Extraction

Execute extractors based on page content or type:

```python
class ConditionalExtractor(Extractor):
    @property
    def name(self) -> str:
        return "conditional_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> Optional[dict]:
        """Only extract from specific page types."""
        # Check if this is a relevant page
        if not self._should_extract(html_content, artifact):
            return None
            
        # Proceed with extraction
        return self._extract_data(html_content)
    
    def _should_extract(self, html_content: str, artifact: PageArtifact) -> bool:
        """Determine if extraction should proceed."""
        # Check URL patterns
        if "/product/" not in artifact.url:
            return False
        
        # Check content indicators
        if "product-info" not in html_content:
            return False
            
        return True
```

### Pipeline Integration

Use extractors in data processing pipelines:

```python
from crawlit.interfaces import Pipeline
from crawlit.models import PageArtifact

class ExtractorPipeline(Pipeline):
    """Pipeline that applies extractors and post-processes results."""
    
    def __init__(self, extractors: List[Extractor]):
        self.extractors = extractors
    
    def process(self, artifact: PageArtifact) -> Optional[PageArtifact]:
        """Apply extractors and validate results."""
        for extractor in self.extractors:
            try:
                result = extractor.extract(artifact.content, artifact)
                if result is not None:
                    artifact.extracted[extractor.name] = result
            except Exception as e:
                logger.error(f"Extractor {extractor.name} failed: {e}")
        
        # Post-process or validate
        if not self._validate_extraction(artifact):
            return None  # Drop invalid artifacts
            
        return artifact
    
    def _validate_extraction(self, artifact: PageArtifact) -> bool:
        """Validate extracted data quality."""
        # Implement validation logic
        return True
```

### Storage Integration

Integrate with databases and storage systems:

```python
import json
from pathlib import Path

class StorageIntegratedExtractor(Extractor):
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
    
    @property
    def name(self) -> str:
        return "stored_data"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> dict:
        """Extract and immediately store results."""
        # Extract data
        data = self._extract_data(html_content)
        
        # Store to file system
        self._store_data(data, artifact.url)
        
        # Return for immediate use
        return data
    
    def _store_data(self, data: dict, url: str):
        """Store extracted data to filesystem."""
        # Create filename from URL
        filename = url.replace("://", "_").replace("/", "_") + ".json"
        filepath = self.storage_path / filename
        
        # Store as JSON
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
```

## Examples

### Complete Extraction Pipeline

```python
from crawlit import Crawler
from crawlit.extractors import *
import json

# Configure extractors
extractors = [
    ContentExtractor(),
    KeywordExtractor(max_keywords=15),
    ImageTagParser(),
    JSEmbeddedDataExtractor()
]

# Create table extractor wrapper
class TableExtractorWrapper:
    @property
    def name(self):
        return "tables"
    
    def extract(self, html_content, artifact):
        tables = extract_tables(html_content, min_rows=2, min_columns=2)
        if not tables:
            return None
        
        # Convert to more structured format
        return {
            "count": len(tables),
            "tables": [
                {
                    "rows": len(table),
                    "columns": max(len(row) for row in table) if table else 0,
                    "data": table
                }
                for table in tables
            ]
        }

# Add table extractor
extractors.append(TableExtractorWrapper())

# Configure crawler
crawler = Crawler(
    start_urls=["https://example.com"],
    extractors=extractors,
    max_pages=100
)

# Process and save results
results = []
for artifact in crawler.crawl():
    result = {
        "url": artifact.url,
        "timestamp": artifact.timestamp.isoformat(),
        "extracted": artifact.extracted
    }
    results.append(result)

# Save to file
with open("extraction_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"Processed {len(results)} pages")
```

### Specialized Extractor for E-commerce

```python
class EcommerceExtractor(Extractor):
    """Specialized extractor for e-commerce product pages."""
    
    @property
    def name(self) -> str:
        return "ecommerce"
    
    def extract(self, html_content: str, artifact: PageArtifact) -> Optional[dict]:
        """Extract product information from e-commerce pages."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check if this is a product page
        if not self._is_product_page(soup, artifact.url):
            return None
        
        product_data = {
            "name": self._extract_product_name(soup),
            "price": self._extract_price(soup),
            "description": self._extract_description(soup),
            "images": self._extract_product_images(soup),
            "availability": self._extract_availability(soup),
            "rating": self._extract_rating(soup),
            "reviews": self._extract_reviews(soup),
            "specifications": self._extract_specifications(soup)
        }
        
        # Remove None values
        return {k: v for k, v in product_data.items() if v is not None}
    
    def _is_product_page(self, soup, url: str) -> bool:
        """Determine if this is a product page."""
        indicators = [
            soup.find(class_=re.compile(r"product")),
            soup.find(id=re.compile(r"product")),
            "/product/" in url,
            soup.find(attrs={"itemtype": re.compile(r"Product")})
        ]
        return any(indicators)
    
    def _extract_product_name(self, soup) -> Optional[str]:
        """Extract product name using multiple selectors."""
        selectors = [
            "h1.product-title",
            "h1[data-testid='product-name']",
            ".product-name h1",
            "[itemprop='name']"
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        return None
    
    def _extract_price(self, soup) -> Optional[dict]:
        """Extract price information."""
        price_selectors = [
            ".price-current",
            "[data-testid='price']",
            "[itemprop='price']",
            ".product-price"
        ]
        
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                # Extract numeric value and currency
                import re
                match = re.search(r'([£$€¥]?)(\d+\.?\d*)', price_text)
                if match:
                    return {
                        "value": float(match.group(2)),
                        "currency": match.group(1) or "USD",
                        "formatted": price_text
                    }
        return None
    
    # Additional extraction methods...
    def _extract_description(self, soup) -> Optional[str]:
        """Extract product description."""
        desc_selectors = [
            ".product-description",
            "[data-testid='description']",
            "[itemprop='description']"
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        return None
```

This comprehensive documentation provides everything needed to understand and effectively use Crawlit's extractor system, from basic usage to advanced custom implementations.