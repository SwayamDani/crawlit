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
- **Detailed Logging**: Comprehensive logging of all crawler activities
- **Command Line Interface**: Simple, powerful CLI for easy usage

## 📋 Requirements

- Python 3.8+
- Dependencies (will be listed in requirements.txt)

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/SwayamDani/crawlit.git
cd crawlit

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 📘 Usage

### Basic Usage`

```bash
python crawlit.py --url https://example.com
```

### Advanced Options

```bash
python crawlit.py --url https://example.com \
                 --depth 3 \
                 --output-format json \
                 --output-file results.json \
                 --respect-robots \
                 --delay 0.5 \
                 --user-agent "crawlit/1.0" \
                 --internal-only
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--url`, `-u` | Target website URL | Required |
| `--depth`, `-d` | Maximum crawl depth | 3 |
| `--output-format`, `-f` | Output format (json, csv, txt) | json |
| `--output-file`, `-o` | File to save results | crawl_results.json |
| `--respect-robots`, `-r` | Respect robots.txt rules | False |
| `--delay` | Delay between requests (seconds) | 0.1 |
| `--user-agent` | Custom User-Agent string | crawlit/1.0 |
| `--internal-only`, `-i` | Only crawl URLs within the same domain | True |
| `--verbose`, `-v` | Verbose output | False |
| `--help`, `-h` | Show help message | - |

## 🏗️ Project Structure

```
crawlit/
├── crawlit.py           # Main entry point
├── requirements.txt     # Project dependencies
├── crawler/             # Core crawler modules
│   ├── __init__.py
│   ├── engine.py        # Core crawler logic
│   ├── fetcher.py       # HTTP request handling
│   ├── parser.py        # HTML parsing and link extraction
│   ├── robots.py        # Robots.txt parser
│   └── utils.py         # Utility functions
├── output/              # Output formatters
│   ├── __init__.py
│   ├── json_formatter.py
│   ├── csv_formatter.py
│   └── text_formatter.py
└── tests/               # Unit and integration tests
    ├── __init__.py
    ├── test_crawler.py
    ├── test_parser.py
    └── test_robots.py
```

## 📅 Project Timeline

- **May 2025**: Initial structure and CLI setup
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