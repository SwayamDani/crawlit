#!/usr/bin/env python3
"""
Example script demonstrating keyword extraction capabilities in crawlit/2.0.

This example demonstrates:
1. Using the crawler with keyword extraction enabled
2. Direct usage of the KeywordExtractor class
3. Processing and analyzing extracted keywords
"""

import sys
import logging
from pathlib import Path
import json
import os

# Add project root to path to make imports work when running this file directly
sys.path.append(str(Path(__file__).parent.parent))

# Import the required components
from crawlit.crawler.engine import Crawler
from crawlit.extractors.keyword_extractor import KeywordExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def crawl_with_keyword_extraction(url, output_file="keywords.json"):
    """Crawl a website with keyword extraction enabled."""
    logger.info(f"Starting crawl of {url} with keyword extraction enabled")
    
    # Initialize the crawler with crawlit/2.0 user agent to enable keyword extraction
    crawler = Crawler(
        start_url="https://swayamdani.com",  # Replace with your target URL
        max_depth=1,  # Keep depth small for example purposes
        internal_only=True,
        user_agent="crawlit/2.0",  # Required for keyword extraction
        delay=0.5,
        respect_robots=True
    )
    
    # Start crawling
    crawler.crawl()
    
    # Get the results
    results = crawler.get_results()
    logger.info(f"Crawling complete. Visited {len(results)} URLs")
    
    # Process and save keywords from each page
    process_keyword_results(results, output_file)
    
    return results

def process_keyword_results(results, output_file="keywords.json"):
    """Process and save keyword extraction results."""
    # Create a structure to store all keyword data
    keywords_data = {
        "per_page": {},
        "overall": {"keywords": {}, "keyphrases": []},
        "metadata": {
            "total_pages": len(results)
        }
    }
    
    # Process each page to extract and compile keywords
    for url, page_data in results.items():
        if 'keywords' in page_data:
            # Add this page's keywords to the per-page collection
            keywords_data["per_page"][url] = {
                "keywords": page_data.get('keywords', []),
                "keyphrases": page_data.get('keyphrases', []),
                "scores": page_data.get('keyword_scores', {})
            }
            
            # Aggregate overall keyword frequencies
            for keyword in page_data.get('keywords', []):
                if keyword not in keywords_data["overall"]["keywords"]:
                    keywords_data["overall"]["keywords"][keyword] = 0
                keywords_data["overall"]["keywords"][keyword] += 1
            
            # Aggregate keyphrases
            keywords_data["overall"]["keyphrases"].extend(page_data.get('keyphrases', []))
    
    # Sort overall keywords by frequency
    keywords_data["overall"]["keywords"] = {
        k: v for k, v in sorted(
            keywords_data["overall"]["keywords"].items(), 
            key=lambda item: item[1], 
            reverse=True
        )
    }
    
    # Remove duplicate keyphrases and sort by length (longer first)
    keyphrases_set = set(keywords_data["overall"]["keyphrases"])
    keywords_data["overall"]["keyphrases"] = sorted(
        list(keyphrases_set), 
        key=lambda x: len(x.split()), 
        reverse=True
    )[:20]  # Limit to top 20
    
    # Save keywords data to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(keywords_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Keyword data saved to {output_file}")
    
    # Print a summary
    top_keywords = list(keywords_data["overall"]["keywords"].items())[:10]
    logger.info("Top 10 keywords across all pages:")
    for keyword, count in top_keywords:
        logger.info(f"  - {keyword}: {count} occurrences")
    
    if keywords_data["overall"]["keyphrases"]:
        logger.info("Top key phrases:")
        for phrase in keywords_data["overall"]["keyphrases"][:5]:
            logger.info(f"  - {phrase}")

def direct_keyword_extraction_example():
    """Example of using KeywordExtractor directly on HTML content."""
    logger.info("Demonstrating direct keyword extraction")
    
    # Sample HTML content
    html_content = """
    <html>
        <head>
            <title>Keyword Extraction Demo for Crawlit</title>
        </head>
        <body>
            <h1>Advanced Keyword Extraction in Python</h1>
            <h2>Natural language processing for web content</h2>
            <p>This is a demonstration of extracting important keywords from web content.
            Keyword extraction is a natural language processing technique that automatically
            identifies the most relevant words or phrases from text. This can be used for
            search engine optimization, content categorization, and understanding document themes.</p>
            
            <h2>Applications of Keyword Extraction</h2>
            <p>Keyword extraction has many applications in content analysis, including:
                <ul>
                    <li>Search engine optimization (SEO)</li>
                    <li>Content recommendation systems</li>
                    <li>Document classification</li>
                    <li>Topic modeling and theme identification</li>
                </ul>
            </p>
            
            <p>The crawlit library provides powerful tools for extracting and analyzing
            keywords from web content, helping you understand what topics are covered
            on a website.</p>
        </body>
    </html>
    """
    
    # Create a keyword extractor instance
    extractor = KeywordExtractor(min_word_length=4, max_keywords=15)
    
    # Extract keywords with scores
    keywords_data = extractor.extract_keywords(html_content, include_scores=True)
    
    logger.info("Extracted keywords:")
    for i, keyword in enumerate(keywords_data['keywords']):
        score = keywords_data['scores'][keyword]
        logger.info(f"  {i+1}. {keyword} (score: {score:.3f})")
    
    # Extract multi-word phrases
    keyphrases = extractor.extract_keyphrases(html_content)
    
    logger.info("Extracted key phrases:")
    for i, phrase in enumerate(keyphrases):
        logger.info(f"  {i+1}. {phrase}")

def main():
    """Main entry point for the script."""
    try:
        # Example 1: Crawl a website with keyword extraction
        url = "https://example.com"  # Replace with your target URL
        logger.info(f"Example 1: Crawling {url} with keyword extraction")
        results = crawl_with_keyword_extraction(url)
        
        # Example 2: Direct usage of KeywordExtractor
        logger.info("\nExample 2: Direct keyword extraction from HTML")
        direct_keyword_extraction_example()
        
        return 0
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
