#!/usr/bin/env python3
"""
crawlit.py - Modular, Ethical Python Web Crawler
"""

import argparse
import sys
import logging
import datetime
import json
import os
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the crawler components
from crawlit.crawler.engine import Crawler
from crawlit.crawler.async_engine import AsyncCrawler
from crawlit.output.formatters import save_results, generate_summary_report

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="crawlit - Modular, Ethical Python Web Crawler",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--url", "-u", required=True, help="Target website URL")
    parser.add_argument("--depth", "-d", type=int, default=3, help="Maximum crawl depth")
    parser.add_argument("--output-format", "-f", default="json", choices=["json", "csv", "txt", "html"], 
                        help="Output format (json, csv, txt, html)")
    parser.add_argument("--output", "-O", default="crawl_results.json", help="File to save results")
    parser.add_argument("--pretty-json", "-p", action="store_true", default=False,
                        help="Enable pretty-print JSON with indentation")
    parser.add_argument("--ignore-robots", "-i", action="store_true", default=False, 
                       help="Ignore robots.txt rules when crawling")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    parser.add_argument("--user-agent", "-a", default="crawlit/2.0", help="Custom User-Agent string")
    parser.add_argument("--allow-external", "-e", action="store_true", default=False, 
                        help="Allow crawling URLs outside the initial domain")
    parser.add_argument("--summary", "-s", action="store_true", default=False,
                        help="Show a summary of crawl results at the end")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--async", action="store_true", default=False,
                        help="Enable asynchronous crawling for faster performance")
    parser.add_argument("--concurrency", type=int, default=15, 
                        help="Maximum number of concurrent requests for async crawling")
    
    # Table extraction options
    parser.add_argument("--extract-tables", "-t", action="store_true", default=False,
                        help="Extract HTML tables from crawled pages")
    parser.add_argument("--tables-output", default="table_output", 
                        help="Directory to save extracted tables")
    parser.add_argument("--tables-format", default="csv", choices=["csv", "json"],
                        help="Format to save extracted tables (csv or json)")
    parser.add_argument("--min-rows", type=int, default=1,
                        help="Minimum number of rows for a table to be extracted")
    parser.add_argument("--min-columns", type=int, default=2,
                        help="Minimum number of columns for a table to be extracted")
    parser.add_argument("--max-table-depth", type=int, default=None,
                        help="Maximum depth to extract tables from (default: same as max crawl depth)")
    
    # Image extraction options
    parser.add_argument("--extract-images", "-img", action="store_true", default=False,
                        help="Extract images from crawled pages")
    parser.add_argument("--images-output", default="image_output", 
                        help="Directory to save image information")
    
    # Keyword extraction options
    parser.add_argument("--extract-keywords", "-k", action="store_true", default=False,
                        help="Extract keywords from crawled pages")
    parser.add_argument("--keywords-output", default="keywords.json", 
                        help="File to save extracted keywords")
    parser.add_argument("--max-keywords", type=int, default=20,
                        help="Maximum number of keywords to extract per page")
    parser.add_argument("--min-word-length", type=int, default=3,
                        help="Minimum length of words to consider as keywords")
    
    # Content extraction coverage options
    parser.add_argument("--extract-content", "-c", action="store_true", default=False,
                        help="Enable comprehensive content extraction (metadata, headings, etc.)")
    parser.add_argument("--content-output", default="content_extraction.json",
                        help="File to save extracted content data")
    parser.add_argument("--extract-headings", action="store_true", default=False,
                        help="Extract heading tags (h1-h6) in hierarchical order")
    parser.add_argument("--extract-metadata", action="store_true", default=False,
                        help="Extract meta tags like title, description, keywords")
    parser.add_argument("--extract-images-context", action="store_true", default=False,
                        help="Extract surrounding text context for images")
    parser.add_argument("--detect-page-type", action="store_true", default=False,
                        help="Auto-detect page type based on URL patterns")
    
    # JavaScript rendering options
    parser.add_argument("--use-js", "--javascript", action="store_true", default=False,
                        help="Enable JavaScript rendering for SPAs and JS-heavy websites (requires Playwright)")
    parser.add_argument("--js-browser", default="chromium", choices=["chromium", "firefox", "webkit"],
                        help="Browser type for JavaScript rendering")
    parser.add_argument("--js-wait-selector", default=None,
                        help="CSS selector to wait for when using JS rendering")
    parser.add_argument("--js-wait-timeout", type=int, default=None,
                        help="Additional timeout (ms) to wait after page load when using JS rendering")
    
    # Proxy support options
    parser.add_argument("--proxy", default=None,
                        help="Single proxy to use (format: http://host:port or socks5://host:port)")
    parser.add_argument("--proxy-file", default=None,
                        help="File containing list of proxies (one per line)")
    parser.add_argument("--proxy-rotation", default="round-robin", 
                        choices=["round-robin", "random", "least-used", "best-performance"],
                        help="Proxy rotation strategy when using proxy file")
    
    # Database integration options
    parser.add_argument("--database", "--db", default=None, choices=["sqlite", "postgresql", "mongodb"],
                        help="Database backend to store crawl results")
    parser.add_argument("--db-path", default="crawl_results.db",
                        help="Database file path (for SQLite)")
    parser.add_argument("--db-host", default="localhost",
                        help="Database host (for PostgreSQL/MongoDB)")
    parser.add_argument("--db-port", type=int, default=None,
                        help="Database port (default: 5432 for PostgreSQL, 27017 for MongoDB)")
    parser.add_argument("--db-name", default="crawlit",
                        help="Database name (for PostgreSQL/MongoDB)")
    parser.add_argument("--db-user", default="postgres",
                        help="Database username (for PostgreSQL)")
    parser.add_argument("--db-password", default="",
                        help="Database password (for PostgreSQL/MongoDB)")
    parser.add_argument("--db-collection", default="results",
                        help="Collection name (for MongoDB)")
    
    return parser.parse_args()
    

def main():
    """Main entry point for the crawler"""
    args = parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Record start time for duration calculation
        start_time = datetime.datetime.now()
        
        # Log common setup info
        logger.info(f"Starting crawl from: {args.url}")
        logger.info(f"Domain restriction is {'disabled' if args.allow_external else 'enabled'}")
        
        # Setup proxy if provided
        proxy_manager = None
        proxy = args.proxy if hasattr(args, 'proxy') else None
        
        if hasattr(args, 'proxy_file') and args.proxy_file:
            # Load proxies from file
            logger.info(f"Loading proxies from file: {args.proxy_file}")
            from crawlit.utils.proxy_manager import ProxyManager
            proxy_manager = ProxyManager(rotation_strategy=args.proxy_rotation)
            try:
                count = proxy_manager.load_from_file(args.proxy_file)
                logger.info(f"Loaded {count} proxies with {args.proxy_rotation} rotation")
            except Exception as e:
                logger.error(f"Failed to load proxies: {e}")
                return
        elif proxy:
            logger.info(f"Using single proxy: {proxy}")
        
        # Determine whether to use async crawling
        if getattr(args, 'async', False):
            logger.info("Using asynchronous crawling mode")
            
            # Create a new event loop and set it as the current loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Initialize the async crawler with feature flags
                crawler = AsyncCrawler(
                    start_url=args.url,
                    max_depth=args.depth,
                    internal_only=not args.allow_external,  # Invert the allow-external flag
                    user_agent=args.user_agent,
                    delay=args.delay,
                    respect_robots=not args.ignore_robots,  # Invert the ignore-robots flag
                    enable_image_extraction=args.extract_images,
                    enable_keyword_extraction=args.extract_keywords,
                    enable_table_extraction=args.extract_tables,
                    max_concurrent_requests=args.concurrency,
                    use_js_rendering=args.use_js,
                    js_browser_type=args.js_browser,
                    js_wait_for_selector=args.js_wait_selector,
                    js_wait_for_timeout=args.js_wait_timeout,
                    proxy=proxy,
                    proxy_manager=proxy_manager
                )
                
                # Run the crawler in the current event loop
                loop.run_until_complete(crawler.crawl())
            finally:
                # Close the event loop
                loop.close()
        else:
            logger.info("Using synchronous crawling mode")
            
            # Initialize the crawler with feature flags
            crawler = Crawler(
                start_url=args.url,
                max_depth=args.depth,
                internal_only=not args.allow_external,  # Invert the allow-external flag
                user_agent=args.user_agent,
                delay=args.delay,
                respect_robots=not args.ignore_robots,  # Invert the ignore-robots flag
                enable_image_extraction=args.extract_images,
                enable_keyword_extraction=args.extract_keywords,
                enable_table_extraction=args.extract_tables,
                use_js_rendering=args.use_js,
                js_browser_type=args.js_browser,
                js_wait_for_selector=args.js_wait_selector,
                js_wait_for_timeout=args.js_wait_timeout,
                proxy=proxy,
                proxy_manager=proxy_manager
            )
            
            # Start crawling
            crawler.crawl()
            
        # Get results
        results = crawler.get_results()
        logger.info(f"Crawl complete. Visited {len(results)} URLs.")
        
        # Handle table extraction if enabled
        if args.extract_tables:
            # Table extraction feature
            logger.info(f"Using table extraction feature...")
            from crawlit.extractors.tables import extract_and_save_tables_from_crawl
            
            # Process all results and extract tables
            stats = extract_and_save_tables_from_crawl(
                results=results,
                output_dir=args.tables_output,
                output_format=args.tables_format,
                min_rows=args.min_rows,
                min_columns=args.min_columns,
                max_depth=args.max_table_depth if args.max_table_depth is not None else args.depth
            )
            
            # Log the results
            if stats["total_tables_found"] > 0:
                logger.info(f"Extracted {stats['total_tables_found']} tables from {stats['total_pages_with_tables']} pages, saved to {stats['total_files_saved']} files in {args.tables_output}/")
                
                # Log tables by depth
                for depth, count in sorted(stats["tables_by_depth"].items()):
                    logger.debug(f"Depth {depth}: {count} tables found")
            else:
                logger.info("No tables found on any crawled pages.")
        
        # Handle image extraction if enabled
        if args.extract_images:
            # Process images from crawled pages
            logger.info(f"Processing images from crawled pages...")
            
            # Create output directory if it doesn't exist
            os.makedirs(args.images_output, exist_ok=True)
            # Process results and extract images
            total_images = 0
            pages_with_images = 0
            images_by_depth = {}
            urls_with_images = []
            
            for url, page_data in results.items():
                if not page_data.get('success', False) or 'images' not in page_data:
                    continue
                    
                images = page_data.get('images', [])
                if not images:
                    continue
                
                # Count this page's images
                num_images = len(images)
                total_images += num_images
                pages_with_images += 1
                urls_with_images.append(url)
                
                # Track images by depth
                depth = page_data.get('depth', 0)
                images_by_depth[depth] = images_by_depth.get(depth, 0) + num_images
                
                # Save images data for this page
                url_filename = url.replace('://', '_').replace('/', '_').replace(':', '_')
                if len(url_filename) > 100:
                    url_filename = url_filename[:100]  # Truncate very long URLs
                    
                output_file = os.path.join(args.images_output, f"{url_filename}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'url': url,
                        'images_count': num_images,
                        'images': images
                    }, f, indent=2)
            
            # Report results
            if total_images > 0:
                logger.info(f"Extracted {total_images} images from {pages_with_images} pages")
                logger.info(f"Image data saved to {args.images_output}/ directory")
                
                # Log images by depth
                for depth, count in sorted(images_by_depth.items()):
                    logger.debug(f"Depth {depth}: {count} images found")
                    
                # Log some example URLs with images
                for url in urls_with_images[:3]:  # Show first 3 examples
                    logger.debug(f"Images found on: {url}")
                if len(urls_with_images) > 3:
                    logger.debug(f"... and {len(urls_with_images) - 3} more pages with images")
            else:
                logger.info("No images found on any crawled pages.")
        
        # Report skipped external URLs if domain restriction is enabled
        if not args.allow_external and hasattr(crawler, 'get_skipped_external_urls'):
            skipped = crawler.get_skipped_external_urls()
            if skipped:
                logger.info(f"Skipped {len(skipped)} external URLs (use --allow-external to crawl them)")
        
        # Save results to database if specified
        if args.database:
            logger.info(f"Checking {args.database} database availability...")
            from crawlit.utils.database import get_database_backend
            
            # Build database configuration
            db_config = {}
            if args.database == 'sqlite':
                db_config['database_path'] = args.db_path
            elif args.database == 'postgresql':
                db_config['host'] = args.db_host
                db_config['port'] = args.db_port if args.db_port else 5432
                db_config['database'] = args.db_name
                db_config['user'] = args.db_user
                db_config['password'] = args.db_password
            elif args.database == 'mongodb':
                db_config['host'] = args.db_host
                db_config['port'] = args.db_port if args.db_port else 27017
                db_config['database'] = args.db_name
                db_config['collection'] = args.db_collection
                if args.db_user:
                    db_config['username'] = args.db_user
                if args.db_password:
                    db_config['password'] = args.db_password
            
            try:
                # check_setup=True by default, will raise RuntimeError if not available
                db = get_database_backend(args.database, **db_config)
                
                logger.info(f"Saving results to {args.database} database...")
                
                # Prepare metadata
                metadata = {
                    'start_url': args.url,
                    'max_depth': args.depth,
                    'user_agent': args.user_agent,
                    'internal_only': not args.allow_external,
                    'respect_robots': not args.ignore_robots,
                    'js_rendering': args.use_js,
                }
                
                crawl_id = db.save_results(results, metadata)
                logger.info(f"✓ Saved {len(results)} pages to {args.database} database (crawl_id: {crawl_id})")
                db.disconnect()
                
            except RuntimeError as e:
                # Database not available or not properly set up
                logger.error("\n" + "="*60)
                logger.error("DATABASE SETUP REQUIRED")
                logger.error("="*60)
                # The error message already contains setup instructions
                logger.error(str(e))
                logger.error("="*60 + "\n")
                logger.warning("Continuing with file output only...")
                
            except ImportError as e:
                logger.error(f"\nDatabase backend not available: {e}")
                logger.error(f"Install with: pip install crawlit[{args.database}]\n")
                logger.warning("Continuing with file output only...")
                
            except Exception as e:
                logger.error(f"\nFailed to save to database: {e}")
                logger.warning("Continuing with file output only...")
        
        # Save results to file in the specified format
        output_path = save_results(results, args.output_format, args.output, args.pretty_json)
        logger.info(f"Results saved to {output_path}")
        
        # Handle comprehensive content extraction if enabled
        if args.extract_content or args.extract_headings or args.extract_metadata or \
           args.extract_images_context or args.detect_page_type:
            logger.info(f"Processing comprehensive content extraction...")
            
            # Determine which features to extract
            extract_all = args.extract_content
            extract_headings = extract_all or args.extract_headings
            extract_metadata = extract_all or args.extract_metadata
            extract_images_context = extract_all or args.extract_images_context
            detect_page_type = extract_all or args.detect_page_type
            
            # Prepare the content extraction data structure
            content_data = {
                "per_page": {},
                "overall": {
                    "page_types": {},
                    "languages": {},
                    "headings": {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
                    "meta_tags": {"has_description": 0, "has_keywords": 0, "has_canonical": 0}
                },
                "metadata": {
                    "total_pages": len(results),
                    "extraction_time": datetime.datetime.now().isoformat(),
                    "extraction_config": {
                        "headings": extract_headings,
                        "metadata": extract_metadata,
                        "images_context": extract_images_context,
                        "page_type": detect_page_type
                    }
                }
            }
            
            # Process each page for content extraction
            for url, page_data in results.items():
                if not page_data.get('success', False) or 'html_content' not in page_data:
                    continue
                
                # Initialize the page entry
                content_data["per_page"][url] = {}
                
                # Extract metadata if enabled
                if extract_metadata:
                    # Title
                    if 'title' in page_data:
                        content_data["per_page"][url]['title'] = page_data['title']
                    
                    # Meta description
                    if 'meta_description' in page_data:
                        content_data["per_page"][url]['meta_description'] = page_data['meta_description']
                        if page_data['meta_description']:
                            content_data["overall"]["meta_tags"]["has_description"] += 1
                    
                    # Meta keywords
                    if 'meta_keywords' in page_data:
                        content_data["per_page"][url]['meta_keywords'] = page_data['meta_keywords']
                        if page_data['meta_keywords']:
                            content_data["overall"]["meta_tags"]["has_keywords"] += 1
                    
                    # Canonical URL
                    if 'canonical_url' in page_data:
                        content_data["per_page"][url]['canonical_url'] = page_data['canonical_url']
                        if page_data['canonical_url']:
                            content_data["overall"]["meta_tags"]["has_canonical"] += 1
                    
                    # Language
                    if 'language' in page_data:
                        content_data["per_page"][url]['language'] = page_data['language']
                        if page_data['language']:
                            lang = page_data['language']
                            if lang not in content_data["overall"]["languages"]:
                                content_data["overall"]["languages"][lang] = 0
                            content_data["overall"]["languages"][lang] += 1
                
                # Extract headings if enabled
                if extract_headings and 'headings' in page_data:
                    content_data["per_page"][url]['headings'] = page_data['headings']
                    
                    # Update overall heading counts
                    for heading in page_data['headings']:
                        level = heading.get('level', 0)
                        if 1 <= level <= 6:
                            content_data["overall"]["headings"][f"h{level}"] += 1
                
                # Extract image context if enabled
                if extract_images_context and 'images_with_context' in page_data:
                    content_data["per_page"][url]['images_with_context'] = page_data['images_with_context']
                
                # Extract page type if enabled
                if detect_page_type and 'page_type' in page_data:
                    page_type = page_data['page_type']
                    content_data["per_page"][url]['page_type'] = page_type
                    
                    # Update overall page type counts
                    if page_type not in content_data["overall"]["page_types"]:
                        content_data["overall"]["page_types"][page_type] = 0
                    content_data["overall"]["page_types"][page_type] += 1
            
            # Save content extraction data to file
            with open(args.content_output, 'w', encoding='utf-8') as f:
                json.dump(content_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Content extraction complete. Results saved to {args.content_output}")
        
        # Handle keyword extraction if enabled
        if args.extract_keywords:
            logger.info(f"Processing keywords from crawled pages...")
            
            # Extract keywords from each page and compile them
            keywords_data = {
                "per_page": {},
                "overall": {"keywords": {}, "keyphrases": []},
                "metadata": {
                    "total_pages": len(results),
                    "extraction_time": datetime.datetime.now().isoformat(),
                    "config": {
                        "max_keywords": args.max_keywords,
                        "min_word_length": args.min_word_length
                    }
                }
            }
            
            # Process each page to extract keywords
            for url, page_data in results.items():
                if page_data.get('keywords') and 'text/html' in page_data.get('content_type', ''):
                    page_keywords = page_data.get('keywords', [])
                    page_keyphrases = page_data.get('keyphrases', [])
                    keywords_data["per_page"][url] = {
                        "keywords": page_keywords,
                        "keyphrases": page_keyphrases,
                        "scores": page_data.get('keyword_scores', {})
                    }
                    
                    # Aggregate overall keyword frequencies
                    for keyword in page_keywords:
                        if keyword not in keywords_data["overall"]["keywords"]:
                            keywords_data["overall"]["keywords"][keyword] = 0
                        keywords_data["overall"]["keywords"][keyword] += 1
                    
                    # Aggregate keyphrases
                    keywords_data["overall"]["keyphrases"].extend(page_keyphrases)
            
            # Sort overall keywords by frequency
            keywords_data["overall"]["keywords"] = {k: v for k, v in sorted(
                keywords_data["overall"]["keywords"].items(), 
                key=lambda item: item[1], 
                reverse=True
            )}
            
            # Remove duplicate keyphrases and sort by length (longer first)
            # First count occurrences in the original list
            keyphrase_counts = {}
            for phrase in keywords_data["overall"]["keyphrases"]:
                if phrase not in keyphrase_counts:
                    keyphrase_counts[phrase] = 0
                keyphrase_counts[phrase] += 1
            
            # Then remove duplicates and sort by length and frequency
            keyphrases_set = set(keywords_data["overall"]["keyphrases"])
            keywords_data["overall"]["keyphrases"] = sorted(
                list(keyphrases_set), 
                key=lambda x: (len(x.split()), keyphrase_counts.get(x, 0)), 
                reverse=True
            )[:args.max_keywords]
            
            # Save keywords data to file
            with open(args.keywords_output, 'w', encoding='utf-8') as f:
                json.dump(keywords_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Keyword extraction complete. Results saved to {args.keywords_output}")
        
        # Calculate and display crawl duration
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logger.info(f"Total crawl time: {duration}")
        
        # Show summary if requested
        if args.summary:
            print("\n" + generate_summary_report(results))
        
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())