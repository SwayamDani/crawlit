---
title: Content Extraction
description: How to extract detailed content from web pages using the ContentExtractor
---

# Content Extractor

The `ContentExtractor` is a powerful utility for extracting structured data from HTML pages. It works with both synchronous and asynchronous code.

## Basic Usage

```python
from crawlit.extractors import ContentExtractor

# Create an extractor instance
extractor = ContentExtractor()

# Synchronous extraction
result = extractor.extract_content(html_content, url)

# Asynchronous extraction
result = await extractor.extract_content_async(html_content, url)
```

## Extracted Content

The `ContentExtractor` extracts a variety of structured information:

- Basic metadata (title, description, keywords, canonical URL)
- Page language
- All headings with hierarchical levels (h1-h6)
- Images with comprehensive context
- Page type detection based on URL patterns
- Last modified date

## Image Context Extraction

A key feature of the `ContentExtractor` is its ability to extract rich context for images. For each image, it extracts:

- Basic attributes (src, alt, title, dimensions, etc.)
- Surrounding context (text near the image)
- Captions (from figcaption elements)
- Related links
- Nearby headings
- Position in document
- Relevance score

Images are sorted by relevance, with the most contextually important images appearing first.

## Example Response

```json
{
  "title": "Page Title",
  "meta_description": "Page description",
  "meta_keywords": ["keyword1", "keyword2"],
  "canonical_url": "https://example.com/canonical",
  "language": "en",
  "headings": [
    {"level": 1, "text": "Main Heading"},
    {"level": 2, "text": "Subheading"}
  ],
  "images_with_context": [
    {
      "src": "/images/example.jpg",
      "alt": "Example image",
      "title": "Example title",
      "width": "800",
      "height": "600",
      "context": "Surrounding text from the page",
      "caption": "Image caption if available",
      "nearby_headings": [
        {"level": 2, "text": "Relevant heading"}
      ],
      "related_links": [
        {"href": "/related", "text": "Related link", "relationship": "parent"}
      ],
      "position": {
        "index": 1,
        "total_images": 5,
        "relative_position": "1/5"
      },
      "relevance_score": 8
    }
  ],
  "page_type": "blog",
  "last_modified": "Wed, 21 Oct 2025 07:28:00 GMT"
}
```
