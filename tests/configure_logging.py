#!/usr/bin/env python3
"""
Set up DEBUG logging for testing the crawler
"""
import logging
import sys

def configure_logging():
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create console handler with a higher log level
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    # Add the handlers to the logger
    root_logger.addHandler(ch)
    
    # Set specific loggers to DEBUG level
    logging.getLogger('crawlit').setLevel(logging.DEBUG)
    logging.getLogger('crawlit.crawler').setLevel(logging.DEBUG)
    logging.getLogger('crawlit.crawler.engine').setLevel(logging.DEBUG)
    logging.getLogger('crawlit.crawler.parser').setLevel(logging.DEBUG)
    logging.getLogger('crawlit.crawler.fetcher').setLevel(logging.DEBUG)
    
    print("DEBUG logging configured.")

if __name__ == "__main__":
    configure_logging()
