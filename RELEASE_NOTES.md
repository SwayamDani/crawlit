# Crawlit Release Notes

## Version 0.2.0 (May 23, 2025)

We are excited to announce version 0.2.0 of Crawlit with several powerful new features!

### New Features

- **Image Extraction**: Extract and analyze images including metadata, dimensions, and accessibility information
  - New `image_extractor.py` module with `ImageTagParser` class
  - Support for image metadata (src, alt, width, height, etc.)
  - Decorative image identification for accessibility checking
  - Parent element context for better image understanding

- **Table Extraction**: Enhanced capabilities for extracting complex HTML tables
  - Support for complex table structures with rowspan and colspan
  - Multiple output formats (CSV, JSON, dictionaries)
  - Configurable minimum rows and columns

- **Keyword Extraction**: Extract and rank important terms from page content
  - Stop word filtering and customizable word length
  - Smart content weighting based on HTML structure
  - Keyphrase extraction for multi-word terms
  - Relevance scoring

### Improvements

- Updated documentation with examples for all new features
- New examples demonstrating each feature
- Extended CLI with options for new extraction capabilities

### Documentation

- Added documentation for the extractors module
- Updated API reference
- Added example usage for all new features

# Crawlit 0.1.0 - Release Notes

We are pleased to announce the first public release of Crawlit - a modular, ethical Python web crawler.

## Features

- **Modular Architecture**: Easily extend with custom modules and parsers
- **Ethical Crawling**: Configurable robots.txt compliance and rate limiting
- **Depth Control**: Set maximum crawl depth to prevent excessive resource usage
- **Domain Filtering**: Restrict crawling to specific domains or subdomains
- **Robust Error Handling**: Gracefully manage connection issues and malformed pages
- **Multiple Output Formats**: Export results as JSON, CSV, or plain text
- **Detailed Logging**: Comprehensive logging of all crawler activities
- **Command Line Interface**: Simple, powerful CLI for easy usage
- **Programmatic API**: Use as a library in your own Python code

## Installation

```bash
# Install the core library
pip install crawlit

# Install with CLI tool support
pip install crawlit[cli]
```

## Documentation

Comprehensive API documentation is now available in the `docs` directory. To build and view the documentation:

```bash
# Install Sphinx and required packages
pip install sphinx sphinx_rtd_theme sphinxcontrib-napoleon

# Build the documentation
cd docs
make html  # On Windows: make.bat html

# View the documentation
# Open docs/_build/html/index.html in your browser
```

## Known Issues

- Limited support for JavaScript-rendered content
- No advanced request throttling based on domain

## Acknowledgments

Thanks to all the early testers and contributors who helped make this release possible.
