#!/usr/bin/env python3
"""
compare_crawl_performance.py - A script to compare synchronous vs asynchronous crawling performance

This script crawls a website with both sync and async methods and compares the time taken.
"""

import os
import time
import json
import asyncio
import logging
from datetime import datetime

# Import both crawler types from crawlit
from crawlit import Crawler, AsyncCrawler

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Target URL to crawl
TARGET_URL = "https://swayamdani.com"
CRAWL_DEPTH = 2
INTERNAL_ONLY = False  # Allow external URLs

def run_sync_crawler():
    """Run the synchronous crawler and time it"""
    logger.info("Starting synchronous crawl of %s (depth: %d)", TARGET_URL, CRAWL_DEPTH)
    
    start_time = time.time()
    
    # Create and run synchronous crawler
    crawler = Crawler(
        start_url=TARGET_URL,
        max_depth=CRAWL_DEPTH,
        internal_only=INTERNAL_ONLY,
        user_agent="crawlit-example/1.0",
        respect_robots=True
    )
    
    # Run the crawler
    crawler.crawl()
    
    # Calculate time taken
    end_time = time.time()
    time_taken = end_time - start_time
    
    # Get results
    results = crawler.results
    
    logger.info("Synchronous crawl completed")
    logger.info("Pages crawled: %d", len(results))
    logger.info("Time taken: %.2f seconds", time_taken)
    
    return {
        "type": "synchronous",
        "pages_crawled": len(results),
        "time_taken": time_taken,
        "results": results
    }

async def run_async_crawler():
    """Run the asynchronous crawler and time it"""
    logger.info("Starting asynchronous crawl of %s (depth: %d)", TARGET_URL, CRAWL_DEPTH)
    
    start_time = time.time()
    
    # Create and run asynchronous crawler
    crawler = AsyncCrawler(
        start_url=TARGET_URL,
        max_depth=CRAWL_DEPTH,
        internal_only=INTERNAL_ONLY,
        user_agent="crawlit-example/1.0",
        respect_robots=True,
        max_concurrency=10  # Adjust concurrency as needed
    )
    
    # Run the async crawler
    await crawler.crawl()
    
    # Calculate time taken
    end_time = time.time()
    time_taken = end_time - start_time
    
    # Get results
    results = crawler.results
    
    logger.info("Asynchronous crawl completed")
    logger.info("Pages crawled: %d", len(results))
    logger.info("Time taken: %.2f seconds", time_taken)
    
    return {
        "type": "asynchronous",
        "pages_crawled": len(results),
        "time_taken": time_taken,
        "results": results
    }

def save_results(results, filename):
    """Save crawl results to a file"""
    # Create results directory if it doesn't exist
    os.makedirs("crawl_results", exist_ok=True)
    
    # Save to file
    filepath = os.path.join("crawl_results", filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {filepath}")
    
    return filepath

async def main():
    """Main function to run both crawlers and compare results"""
    logger.info("Starting crawl comparison")
    
    # Run synchronous crawler
    sync_results = run_sync_crawler()
    
    # Add small delay between runs
    await asyncio.sleep(2)
    
    # Run asynchronous crawler
    async_results = await run_async_crawler()
    
    # Compare results
    sync_time = sync_results["time_taken"]
    async_time = async_results["time_taken"]
    
    if async_time > 0:
        speed_improvement = (sync_time / async_time - 1) * 100
    else:
        speed_improvement = 0
    
    print("\n" + "=" * 50)
    print("CRAWL PERFORMANCE COMPARISON")
    print("=" * 50)
    print(f"Target URL: {TARGET_URL}")
    print(f"Crawl Depth: {CRAWL_DEPTH}")
    print(f"Allow External URLs: {not INTERNAL_ONLY}")
    print("-" * 50)
    print(f"Synchronous Crawl:")
    print(f"  - Pages Crawled: {sync_results['pages_crawled']}")
    print(f"  - Time Taken: {sync_results['time_taken']:.2f} seconds")
    print(f"Asynchronous Crawl:")
    print(f"  - Pages Crawled: {async_results['pages_crawled']}")
    print(f"  - Time Taken: {async_results['time_taken']:.2f} seconds")
    print("-" * 50)
    print(f"Performance Improvement: {speed_improvement:.2f}%")
    print("=" * 50)
    
    # Save detailed results to files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sync_file = f"sync_crawl_{timestamp}.json"
    async_file = f"async_crawl_{timestamp}.json"
    
    save_results(sync_results, sync_file)
    save_results(async_results, async_file)
    
    # Save comparison summary
    comparison = {
        "target_url": TARGET_URL,
        "crawl_depth": CRAWL_DEPTH,
        "allow_external_urls": not INTERNAL_ONLY,
        "sync_results": {
            "pages_crawled": sync_results["pages_crawled"],
            "time_taken": sync_results["time_taken"]
        },
        "async_results": {
            "pages_crawled": async_results["pages_crawled"],
            "time_taken": async_results["time_taken"]
        },
        "performance_improvement_percent": speed_improvement,
        "timestamp": datetime.now().isoformat()
    }
    
    save_results(comparison, f"comparison_summary_{timestamp}.json")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
