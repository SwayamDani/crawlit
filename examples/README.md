# Crawlit Examples

This directory contains examples demonstrating various features of the Crawlit web crawler.

## Basic Usage

- `programmatic_usage.py`: Shows how to use Crawlit as a library in your Python code

## Data Extraction (v0.2.0+)

### Table Extraction

- `table_extraction.py`: Basic table extraction example
- `enhanced_table_extraction.py`: Advanced table extraction with rowspan/colspan support
- `rowspan_colspan_example.py`: Specific example dealing with complex table structures
- `advanced_table_extraction_all_depths.py`: Table extraction from multiple crawl depths

### Image Extraction

- `image_extraction.py`: Extract and analyze images from websites

### Keyword Extraction

- `keyword_extraction.py`: Extract keywords and key phrases from web pages

## Running the Examples

To run these examples:

1. Make sure you've installed Crawlit:
   ```bash
   pip install -e ..
   ```

2. Run an example:
   ```bash
   python programmatic_usage.py
   ```

## Using Both API and CLI

Crawlit offers both a programmatic API and a command-line interface for all features. Choose the approach that best fits your workflow:

### API Example (in Python code)

```python
from crawlit import Crawler
from crawlit.extractors.tables import extract_tables

crawler = Crawler(start_url="https://example.com")
crawler.crawl()
results = crawler.get_results()
```

### CLI Example (from terminal)

```bash
crawlit --url https://example.com --extract-tables --user-agent "crawlit/2.0"
```

For more details about CLI usage, see the `cli_usage.md` document in the docs directory.