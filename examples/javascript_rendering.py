#!/usr/bin/env python3
"""
javascript_rendering.py - Examples of using JavaScript rendering with crawlit

This script demonstrates how to crawl Single Page Applications (SPAs) and
JavaScript-heavy websites using Playwright integration.

Requirements:
    pip install playwright
    python -m playwright install chromium
"""

import asyncio
import logging
from crawlit import Crawler, AsyncCrawler
from crawlit.output.formatters import save_results

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def example_1_basic_js_rendering():
    """Example 1: Basic JavaScript rendering with synchronous crawler"""
    logger.info("=" * 80)
    logger.info("Example 1: Basic JavaScript Rendering (Synchronous)")
    logger.info("=" * 80)
    
    # Create crawler with JavaScript rendering enabled
    crawler = Crawler(
        start_url="https://react.dev",  # React documentation site
        max_depth=1,
        use_js_rendering=True,
        js_browser_type="chromium",
        internal_only=True,
        delay=1.0  # Be polite
    )
    
    # Crawl the site
    crawler.crawl()
    
    # Get results
    results = crawler.get_results()
    logger.info(f"Crawled {len(results)} pages from React documentation")
    
    # Save results
    save_results(results, "json", "react_crawl_results.json", pretty=True)
    logger.info("Results saved to react_crawl_results.json")
    
    # Show sample URLs
    logger.info("Sample crawled URLs:")
    for url in list(results.keys())[:5]:
        logger.info(f"  - {url}")
    
    return results


def example_2_wait_for_selector():
    """Example 2: Wait for specific element before extracting content"""
    logger.info("\n" + "=" * 80)
    logger.info("Example 2: Wait for Specific Selector")
    logger.info("=" * 80)
    
    # Create crawler that waits for specific element
    crawler = Crawler(
        start_url="https://vuejs.org",  # Vue.js documentation
        max_depth=1,
        use_js_rendering=True,
        js_browser_type="chromium",
        js_wait_for_selector="#app",  # Wait for Vue app to mount
        internal_only=True,
        delay=1.0
    )
    
    crawler.crawl()
    results = crawler.get_results()
    
    logger.info(f"Crawled {len(results)} pages from Vue.js documentation")
    logger.info("Waited for #app selector on each page")
    
    return results


def example_3_wait_with_timeout():
    """Example 3: Additional timeout for animations and dynamic content"""
    logger.info("\n" + "=" * 80)
    logger.info("Example 3: Additional Wait Timeout for Animations")
    logger.info("=" * 80)
    
    # Create crawler with additional wait time
    crawler = Crawler(
        start_url="https://angular.io",  # Angular documentation
        max_depth=1,
        use_js_rendering=True,
        js_browser_type="chromium",
        js_wait_for_timeout=2000,  # Wait 2 seconds for animations
        internal_only=True,
        delay=1.0
    )
    
    crawler.crawl()
    results = crawler.get_results()
    
    logger.info(f"Crawled {len(results)} pages from Angular documentation")
    logger.info("Added 2-second wait for animations on each page")
    
    return results


def example_4_different_browsers():
    """Example 4: Testing with different browser engines"""
    logger.info("\n" + "=" * 80)
    logger.info("Example 4: Testing Different Browser Engines")
    logger.info("=" * 80)
    
    test_url = "https://svelte.dev"
    browsers = ["chromium", "firefox", "webkit"]
    
    results_by_browser = {}
    
    for browser in browsers:
        logger.info(f"\nTesting with {browser}...")
        
        crawler = Crawler(
            start_url=test_url,
            max_depth=1,
            use_js_rendering=True,
            js_browser_type=browser,
            internal_only=True,
            delay=1.0
        )
        
        crawler.crawl()
        results = crawler.get_results()
        results_by_browser[browser] = results
        
        logger.info(f"  {browser}: Crawled {len(results)} pages")
    
    return results_by_browser


async def example_5_async_js_rendering():
    """Example 5: Asynchronous crawling with JavaScript rendering"""
    logger.info("\n" + "=" * 80)
    logger.info("Example 5: Async Crawler with JavaScript Rendering")
    logger.info("=" * 80)
    
    # Create async crawler with JavaScript rendering
    crawler = AsyncCrawler(
        start_url="https://nextjs.org",  # Next.js documentation
        max_depth=2,
        use_js_rendering=True,
        js_browser_type="chromium",
        js_wait_for_selector="main",
        max_concurrent_requests=3,  # Limited concurrency with JS rendering
        internal_only=True,
        delay=1.0
    )
    
    # Crawl asynchronously
    await crawler.crawl()
    
    # Get results
    results = crawler.get_results()
    logger.info(f"Async crawled {len(results)} pages from Next.js documentation")
    
    # Save results
    save_results(results, "json", "nextjs_async_results.json", pretty=True)
    logger.info("Results saved to nextjs_async_results.json")
    
    return results


def example_6_js_with_content_extraction():
    """Example 6: Combine JavaScript rendering with content extraction"""
    logger.info("\n" + "=" * 80)
    logger.info("Example 6: JavaScript Rendering + Content Extraction")
    logger.info("=" * 80)
    
    # Create crawler with JS rendering and content extraction
    crawler = Crawler(
        start_url="https://react.dev",
        max_depth=1,
        use_js_rendering=True,
        js_browser_type="chromium",
        enable_content_extraction=True,
        enable_keyword_extraction=True,
        enable_image_extraction=True,
        internal_only=True,
        delay=1.0
    )
    
    crawler.crawl()
    results = crawler.get_results()
    
    logger.info(f"Crawled {len(results)} pages with full content extraction")
    
    # Show extracted data from first page
    if results:
        first_url = list(results.keys())[0]
        first_result = results[first_url]
        
        logger.info(f"\nExtracted data from {first_url}:")
        if 'title' in first_result:
            logger.info(f"  Title: {first_result['title']}")
        if 'keywords' in first_result:
            logger.info(f"  Keywords: {first_result['keywords'][:5]}")
        if 'images' in first_result:
            logger.info(f"  Images found: {len(first_result['images'])}")
    
    return results


def example_7_spa_comparison():
    """Example 7: Compare static HTML fetching vs JavaScript rendering"""
    logger.info("\n" + "=" * 80)
    logger.info("Example 7: Static vs JavaScript Rendering Comparison")
    logger.info("=" * 80)
    
    test_url = "https://react.dev"
    
    # First, try without JavaScript rendering
    logger.info("\n1. Crawling WITHOUT JavaScript rendering...")
    crawler_static = Crawler(
        start_url=test_url,
        max_depth=1,
        use_js_rendering=False,
        internal_only=True,
        delay=1.0
    )
    crawler_static.crawl()
    results_static = crawler_static.get_results()
    
    # Then, with JavaScript rendering
    logger.info("\n2. Crawling WITH JavaScript rendering...")
    crawler_js = Crawler(
        start_url=test_url,
        max_depth=1,
        use_js_rendering=True,
        js_browser_type="chromium",
        internal_only=True,
        delay=1.0
    )
    crawler_js.crawl()
    results_js = crawler_js.get_results()
    
    # Compare results
    logger.info("\n=== Comparison Results ===")
    logger.info(f"Static HTML:         {len(results_static)} URLs found")
    logger.info(f"JavaScript Rendered: {len(results_js)} URLs found")
    
    # Check content length difference
    if test_url in results_static and test_url in results_js:
        static_content = results_static[test_url].get('html_content', '')
        js_content = results_js[test_url].get('html_content', '')
        
        if static_content and js_content:
            logger.info(f"\nContent size difference for {test_url}:")
            logger.info(f"  Static HTML:         {len(static_content):,} bytes")
            logger.info(f"  JavaScript Rendered: {len(js_content):,} bytes")
            logger.info(f"  Difference:          {len(js_content) - len(static_content):+,} bytes")
    
    return {
        "static": results_static,
        "javascript": results_js
    }


def main():
    """Run all JavaScript rendering examples"""
    logger.info("Starting JavaScript Rendering Examples")
    logger.info("=" * 80)
    logger.info("\nThese examples demonstrate crawling SPAs and JS-heavy websites.")
    logger.info("Make sure Playwright is installed:")
    logger.info("  pip install playwright")
    logger.info("  python -m playwright install chromium")
    logger.info("")
    
    # Check if Playwright is available
    try:
        from crawlit.crawler.js_renderer import is_playwright_available
        if not is_playwright_available():
            logger.error("\n❌ Playwright not installed!")
            logger.error("Install it with: pip install playwright")
            logger.error("Then run: python -m playwright install chromium")
            return
        logger.info("✅ Playwright is installed and ready\n")
    except ImportError:
        logger.error("\n❌ Could not import JavaScript renderer!")
        logger.error("Make sure crawlit is properly installed with JS support")
        return
    
    try:
        # Run examples
        # Note: These examples use real websites. Be respectful and add appropriate delays.
        
        # Example 1: Basic usage
        example_1_basic_js_rendering()
        
        # Example 2: Wait for selector
        example_2_wait_for_selector()
        
        # Example 3: Wait with timeout
        example_3_wait_with_timeout()
        
        # Example 4: Different browsers
        example_4_different_browsers()
        
        # Example 5: Async crawler
        logger.info("\nRunning async example...")
        asyncio.run(example_5_async_js_rendering())
        
        # Example 6: With content extraction
        example_6_js_with_content_extraction()
        
        # Example 7: Comparison
        example_7_spa_comparison()
        
        logger.info("\n" + "=" * 80)
        logger.info("All examples completed successfully!")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.info("\n\nExamples interrupted by user")
    except Exception as e:
        logger.exception(f"\n\nError running examples: {e}")


if __name__ == "__main__":
    main()



