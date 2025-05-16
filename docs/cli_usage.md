# Command Line Usage

The `crawlit` package provides a powerful command-line interface for crawling websites and extracting structured data. This document details the usage patterns and features available through the CLI.

## Basic Usage

```bash
# Basic usage - crawl a website and save results in JSON format
crawlit --url https://example.com
```

## Standard Crawling Options

Control how the crawler operates:

```bash
crawlit --url https://example.com \
        --depth 3 \                     # Maximum depth to crawl
        --delay 0.5 \                   # Delay between requests
        --user-agent "MyBot/1.0" \      # Custom user agent
        --allow-external \              # Allow crawling external domains
        --ignore-robots                 # Ignore robots.txt rules
```

## Output Options

Control how results are saved:

```bash
crawlit --url https://example.com \
        --output-format json \          # Output format (json, csv, txt, html)
        --output results.json \         # Output file name
        --pretty-json                   # Pretty-print JSON output
```

## Data Extraction (v0.2.0+)

Crawlit v0.2.0 introduces powerful data extraction features. These features require setting the user agent to "crawlit/2.0".

### Table Extraction

Extract HTML tables from crawled pages:

```bash
crawlit --url https://example.com \
        --user-agent "crawlit/2.0" \    # Required for extraction features
        --extract-tables \              # Enable table extraction
        --tables-output "./tables" \    # Directory for table output
        --tables-format csv \           # Output format (csv, json)
        --min-rows 2 \                  # Minimum rows for table extraction
        --min-columns 2 \               # Minimum columns for table extraction
        --max-table-depth 2             # Maximum depth to extract tables from
```

### Image Extraction

Extract images and related metadata from crawled pages:

```bash
crawlit --url https://example.com \
        --user-agent "crawlit/2.0" \    # Required for extraction features
        --extract-images \              # Enable image extraction
        --images-output "./images"      # Directory for image metadata
```

### Keyword Extraction

Extract keywords and key phrases from crawled pages:

```bash
crawlit --url https://example.com \
        --user-agent "crawlit/2.0" \    # Required for extraction features
        --extract-keywords \            # Enable keyword extraction
        --keywords-output keywords.json \ # Output file for keywords
        --max-keywords 30 \             # Maximum keywords per page
        --min-word-length 4             # Minimum word length
```

## Combined Features

You can combine multiple extraction features in a single crawl:

```bash
crawlit --url https://example.com \
        --user-agent "crawlit/2.0" \
        --depth 2 \
        --extract-tables \
        --extract-images \
        --extract-keywords \
        --summary                       # Show summary at the end
```

## Output Examples

### Table Extraction Output

For each extracted table, files are created in the specified output directory:
- CSV format: `domain_com_depth1_1.csv`, `domain_com_depth1_2.csv`, etc.
- JSON format: `domain_com_depth1_1.json`, `domain_com_depth1_2.json`, etc.

### Image Extraction Output

For each page with images, a JSON file is created in the specified output directory:
- `https_domain_com.json`

Example content:
```json
{
  "url": "https://example.com",
  "images_count": 3,
  "images": [
    {
      "src": "logo.png",
      "alt": "Example Logo",
      "width": 200,
      "height": 100,
      "decorative": false
    },
    ...
  ]
}
```

### Keyword Extraction Output

A single JSON file with keywords and phrases:
```json
{
  "per_page": {
    "https://example.com": {
      "keywords": ["example", "website", ...],
      "keyphrases": ["example website", ...],
      "scores": {"example": 0.8, "website": 0.6, ...}
    },
    ...
  },
  "overall": {
    "keywords": {"example": 5, "website": 3, ...},
    "keyphrases": ["example website", ...]
  }
}
```
