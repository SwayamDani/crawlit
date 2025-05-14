#!/usr/bin/env python3
"""
crawlit - Modular, Ethical Python Web Crawler

A flexible web crawler library that can be used programmatically or via CLI.
"""

__version__ = '0.1.0'

# Export core functionality
from crawlit.crawler.engine import Crawler
from crawlit.output.formatters import save_results, generate_summary_report

# CLI functionality (but not executed on import)
def cli_main():
    """Entry point for the CLI interface when installed with [cli] option"""
    from crawlit.crawlit import main
    return main()

__all__ = [
    'Crawler',           # Main crawler engine
    'save_results',      # Output formatters 
    'generate_summary_report',
    'cli_main'           # CLI entry point
]