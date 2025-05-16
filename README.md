# 🕷️ crawlit - Modular, Ethical Python Web Crawler

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful, modular, and ethical web crawler built in Python. Designed for security testing, link extraction, and website structure mapping with a focus on clean architecture and extensibility.

## 🚀 Features

- **Modular Architecture**: Easily extend with custom modules and parsers
- **Ethical Crawling**: Configurable robots.txt compliance and rate limiting
- **Depth Control**: Set maximum crawl depth to prevent excessive resource usage
- **Domain Filtering**: Restrict crawling to specific domains or subdomains
- **Robust Error Handling**: Gracefully manage connection issues and malformed pages
- **Multiple Output Formats**: Export results as JSON, CSV, or plain text
- **Advanced Table Extraction**: Extract tables with support for complex structures and cell spanning
- **Image Extraction**: Extract and analyze images including alt text and accessibility information
- **Keyword Extraction**: Identify key terms and phrases from webpage content
- **Detailed Logging**: Comprehensive logging of all crawler activities
- **Command Line Interface**: Simple, powerful CLI for easy usage
- **Programmatic API**: Use as a library in your own Python code
- **Version-dependent Features**: 
  - `v0.1.0`: Standard web crawling capabilities
  - `v0.2.0`: Enhanced features including image extraction, table extraction, and keyword extraction
  - `crawlit/1.0`: Standard web crawling capabilities (User-Agent)
  - `crawlit/2.0`: Enhanced features including multi-depth table extraction, keyword extraction, and image analysis (User-Agent)

## 📋 Requirements

- Python 3.8+
- Dependencies (will be listed in requirements.txt)

## 🛠️ Installation

### From PyPI (recommended)

```bash
# Install the core library
pip install crawlit

# Install with CLI tool support
pip install crawlit[cli]
```

### From Source

```bash
# Clone the repository
git clone https://github.com/SwayamDani/crawlit.git
cd crawlit

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## 📘 Usage

### API Documentation

Full API documentation is available in the `docs` directory, including documentation for:
- Core crawler modules
- Extraction modules (tables, images, and keywords)
- Output formatters
- Command-line interface

To build and view the documentation:

```bash
# Install Sphinx and required packages
pip install sphinx sphinx_rtd_theme sphinxcontrib-napoleon

# Build the documentation
cd docs
make html  # On Windows: make.bat html

# View the documentation
# Open docs/_build/html/index.html in your browser
```

### As a Library in Your Python Code

```python
from crawlit import Crawler, save_results, generate_summary_report

# Initialize the crawler with custom parameters
crawler = Crawler(
    start_url="https://example.com",
    max_depth=3,
    internal_only=True,
    user_agent="MyCustomBot/1.0",
    delay=0.5,
    respect_robots=True
)

# Start crawling
crawler.crawl()

# Get and process results
results = crawler.get_results()
print(f"Crawled {len(results)} URLs")

# Save results in different formats
save_results(results, "json", "crawl_results.json", pretty=True)
```

See the `examples/programmatic_usage.py` file for a complete example.

### Command Line Interface

If you installed with `pip install crawlit[cli]`, you can use the command-line interface:

```bash
# Basic usage
crawlit --url https://example.com

# Advanced options
crawlit --url https://example.com \
        --depth 3 \
        --output-format json \
        --output results.json \
        --delay 0.5 \
        --user-agent "crawlit/1.0" \
        --ignore-robots

# With new extraction features (v0.2.0+)
crawlit --url https://example.com \
        --user-agent "crawlit/2.0" \
        --extract-tables \
        --tables-output "./table_output" \
        --extract-images \
        --images-output "./image_output" \
        --extract-keywords \
        --keywords-output "keywords.json"
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--url`, `-u` | Target website URL | Required |
| `--depth`, `-d` | Maximum crawl depth | 3 |
| `--output-format`, `-f` | Output format (json, csv, txt, html) | json |
| `--output`, `-O` | File to save results | crawl_results.json |
| `--pretty-json`, `-p` | Enable pretty-print JSON with indentation | False |
| `--ignore-robots`, `-i` | Ignore robots.txt rules | False |
| `--delay` | Delay between requests (seconds) | 0.1 |
| `--user-agent`, `-a` | Custom User-Agent string | crawlit/1.0 |
| `--allow-external`, `-e` | Allow crawling URLs outside initial domain | False |
| `--summary`, `-s` | Show a summary of crawl results | False |
| `--verbose`, `-v` | Verbose output | False |
| `--extract-keywords`, `-k` | Extract keywords from crawled pages (requires crawlit/2.0) | False |
| `--keywords-output` | File to save extracted keywords | keywords.json |
| `--max-keywords` | Maximum number of keywords to extract per page | 20 |
| `--min-word-length` | Minimum length of words to consider as keywords | 3 |
| `--extract-images`, `-img` | Extract images from crawled pages (requires crawlit/2.0) | False |
| `--images-output` | Directory to save extracted images data | image_output/ |
| `--extract-tables`, `-t` | Extract tables from crawled pages (requires crawlit/2.0) | False |
| `--tables-output` | Directory to save extracted tables | table_output/ |
| `--tables-format` | Format to save extracted tables (csv or json) | csv |
| `--min-rows` | Minimum number of rows for a table to be extracted | 1 |
| `--min-columns` | Minimum number of columns for a table to be extracted | 2 |
| `--max-table-depth` | Maximum depth to extract tables from | Same as max crawl depth |
| `--help`, `-h` | Show help message | - |

## 📊 Advanced Table Extraction

Crawlit includes powerful HTML table extraction capabilities:

```python
from crawlit.extractors.tables import extract_tables

# Extract tables with minimum rows and columns filters
tables = extract_tables(html_content, min_rows=2, min_columns=3)

# Convert tables to CSV
from crawlit.extractors.tables import tables_to_csv
tables_to_csv(tables, base_filename="extracted_tables", output_dir="output")

# Convert to dictionaries using first row as headers
from crawlit.extractors.tables import tables_to_dict
table_dicts = tables_to_dict(tables)

# Convert to JSON
from crawlit.extractors.tables import tables_to_json
tables_to_json(tables, base_filename="extracted_tables")
```

The advanced table extraction provides:
- Smart handling of `<thead>` and `<tbody>` sections
- Full support for `rowspan` and `colspan` attributes
- Consistent column count across all rows
- Thorough cell content cleaning (HTML entities, whitespace, etc.)

For examples, see `examples/enhanced_table_extraction.py` and `examples/rowspan_colspan_example.py`.

## 🔍 Keyword Extraction

Crawlit 2.0 includes sophisticated keyword extraction capabilities:

```python
from crawlit import Crawler
from crawlit.extractors.keyword_extractor import KeywordExtractor

# Option 1: Use the crawler with crawlit/2.0 user agent for automatic keyword extraction
crawler = Crawler(
    start_url="https://example.com",
    user_agent="crawlit/2.0",  # Required for keyword extraction
    max_depth=2
)
crawler.crawl()
results = crawler.get_results()

# Access extracted keywords from results
for url, data in results.items():
    if 'keywords' in data:
        print(f"Keywords for {url}: {data['keywords']}")
    if 'keyphrases' in data:
        print(f"Key phrases: {data['keyphrases']}")

# Option 2: Use the keyword extractor directly on HTML content
extractor = KeywordExtractor(min_word_length=4, max_keywords=10)
html_content = "<html><body><h1>Keyword Extraction Example</h1><p>This demonstrates advanced keyword extraction capability.</p></body></html>"

# Get keywords with scores
keywords_data = extractor.extract_keywords(html_content, include_scores=True)
print(f"Keywords: {keywords_data['keywords']}")
print(f"Scores: {keywords_data['scores']}")

# Get multi-word phrases
keyphrases = extractor.extract_keyphrases(html_content)
print(f"Key phrases: {keyphrases}")
```

The keyword extraction offers:
- Smart weighting of content based on HTML structure (headings, titles, etc.)
- Automatic filtering of common stop words
- Multi-word phrase extraction for more context-rich keywords
- Scoring based on frequency and relevance
- Integration with crawl results

For a complete example, see `examples/keyword_extraction.py`.

## 🖼️ Image Extraction

Crawlit v0.2.0 introduces comprehensive image extraction capabilities:

```python
from crawlit import Crawler
from crawlit.extractors.image_extractor import ImageTagParser

# Option 1: Using the crawler for automatic image extraction
crawler = Crawler(
    start_url="https://example.com",
    max_depth=2
)
crawler.crawl()
results = crawler.get_results()

# Access extracted images from results
for url, data in results.items():
    if 'images' in data:
        for img in data['images']:
            print(f"Image URL: {img.get('src')}")
            print(f"Alt text: {img.get('alt', 'None')}")
            if 'width' in img and 'height' in img:
                print(f"Dimensions: {img['width']}x{img['height']}")
            print(f"Decorative: {img.get('decorative', False)}")

# Option 2: Use the image extractor directly on HTML content
from html.parser import HTMLParser
parser = ImageTagParser()
html_content = "<html><body><img src='example.jpg' alt='Example'></body></html>"
parser.feed(html_content)
images = parser.images
```

The image extraction feature provides:
- Complete metadata extraction (src, alt, width, height, etc.)
- Parent element context to understand image placement
- Accessibility analysis (identifying decorative images missing alt text)
- Integration with crawl results

For a complete example, see `examples/image_extraction.py`.

## 🏗️ Project Structure

```
crawlit/
├── crawlit.py           # CLI entry point
├── requirements.txt     # Project dependencies
├── crawler/             # Core crawler modules
│   ├── __init__.py
│   ├── engine.py        # Core crawler logic
│   ├── fetcher.py       # HTTP request handling
│   ├── parser.py        # HTML parsing and link extraction
│   └── robots.py        # Robots.txt parser
├── extractors/          # Data extraction modules
│   ├── __init__.py
│   ├── image_extractor.py  # Image extraction and analysis
│   ├── keyword_extractor.py  # Keyword and keyphrase extraction
│   └── tables.py        # Advanced table extraction
├── output/              # Output formatters
│   ├── __init__.py
│   └── formatters.py    # Output formatting functions
├── examples/            # Example usage
│   ├── programmatic_usage.py  # Example of using as a library
│   ├── image_extraction.py    # Example of image extraction
│   ├── keyword_extraction.py  # Example of keyword extraction
│   └── table_extraction.py    # Example of table extraction
└── tests/               # Unit and integration tests
    └── __init__.py
```

## 📅 Project Timeline

- **May 2025**: Initial structure and CLI setup
- **May 15, 2025**: v0.2.0 release with image extraction, table extraction, and keyword extraction features
- **June 2025**: Core functionality complete (HTTP handling, parsing, domain control)
- **June 30, 2025**: Project completion target with all core features

## 🤝 Contributing

Contributions will be welcome after the core functionality is complete. Please check back after June 30, 2025, for contribution guidelines.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

Built and maintained by Swayam Dani

---

**Note**: This project is under active development with completion targeted for June 30, 2025.