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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the crawler components
from crawlit.crawler.engine import Crawler
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
    parser.add_argument("--user-agent", "-a", default="crawlit/1.0", help="Custom User-Agent string")
    parser.add_argument("--allow-external", "-e", action="store_true", default=False, 
                        help="Allow crawling URLs outside the initial domain")
    parser.add_argument("--summary", "-s", action="store_true", default=False,
                        help="Show a summary of crawl results at the end")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
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
    
    return parser.parse_args()

def main():
    """Main entry point for the crawler"""
    args = parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    # Check if trying to use table extraction with crawlit/1.0
    if args.extract_tables and args.user_agent != "crawlit/2.0":
        logger.warning("Table extraction (--extract-tables) requires --user-agent crawlit/2.0")
        logger.warning("To extract tables, please use: --user-agent crawlit/2.0")
        logger.warning("Continuing with standard crawl (no table extraction)")
    
    # Check if trying to use image extraction with crawlit/1.0
    if args.extract_images and args.user_agent != "crawlit/2.0":
        logger.warning("Image extraction (--extract-images) requires --user-agent crawlit/2.0")
        logger.warning("To extract images, please use: --user-agent crawlit/2.0")
        logger.warning("Continuing with standard crawl (no image extraction)")
    
    # Check if using other v2.0 features with old user agent
    if args.user_agent != "crawlit/2.0" and (
        args.min_rows != 1 or 
        args.min_columns != 2 or 
        args.max_table_depth is not None or
        args.tables_format != "csv" or
        args.extract_keywords
    ):
        logger.warning("Advanced features (table parameters, keyword extraction) require --user-agent crawlit/2.0")
        logger.warning("These parameters will be ignored with the current user agent.")
        
    # Check specifically for keyword extraction with wrong user agent
    if args.extract_keywords and args.user_agent != "crawlit/2.0":
        logger.warning("Keyword extraction (--extract-keywords) requires --user-agent crawlit/2.0")
        logger.warning("To extract keywords, please use: --user-agent crawlit/2.0")
        logger.warning("Continuing with standard crawl (no keyword extraction)")
    
    try:
        # Record start time for duration calculation
        start_time = datetime.datetime.now()
        
        # Initialize the crawler
        crawler = Crawler(
            start_url=args.url,
            max_depth=args.depth,
            internal_only=not args.allow_external,  # Invert the allow-external flag
            user_agent=args.user_agent,
            delay=args.delay,
            respect_robots=not args.ignore_robots  # Invert the ignore-robots flag
        )
        
        # Start crawling
        logger.info(f"Starting crawl from: {args.url}")
        logger.info(f"Domain restriction is {'disabled' if args.allow_external else 'enabled'}")
        crawler.crawl()
        
        # Get results
        results = crawler.get_results()
        logger.info(f"Crawl complete. Visited {len(results)} URLs.")
        
        # Handle table extraction if enabled
        if args.extract_tables:
            import os
            
            # Check if user is using crawlit/2.0 user agent for table extraction
            is_v2_user_agent = args.user_agent == "crawlit/2.0"
            
            if not is_v2_user_agent:
                # Table extraction is only available with crawlit/2.0
                logger.warning("Table extraction is only available with --user-agent crawlit/2.0")
                logger.warning("To extract tables, please use: --user-agent crawlit/2.0")
                logger.warning("Continuing with standard crawl (no table extraction)")
            else:
                # Table extraction feature - only available in crawlit/2.0
                logger.info(f"Using table extraction feature (crawlit/2.0)...")
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
                    logger.info(f"[crawlit/2.0] Extracted {stats['total_tables_found']} tables from {stats['total_pages_with_tables']} pages, saved to {stats['total_files_saved']} files in {args.tables_output}/")
                    
                    # Log tables by depth
                    for depth, count in sorted(stats["tables_by_depth"].items()):
                        logger.debug(f"[crawlit/2.0] Depth {depth}: {count} tables found")
                else:
                    logger.info("[crawlit/2.0] No tables found on any crawled pages.")
        
        # Handle image extraction if enabled
        if args.extract_images:
            # os and json already imported at the top level
            pass
            
            # Check if user is using crawlit/2.0 user agent for image extraction
            is_v2_user_agent = args.user_agent == "crawlit/2.0"
            
            if not is_v2_user_agent:
                # Image extraction is only available with crawlit/2.0
                logger.warning("Image extraction is only available with --user-agent crawlit/2.0")
                logger.warning("To extract images, please use: --user-agent crawlit/2.0")
                logger.warning("Continuing with standard crawl (no image extraction)")
            else:
                # Image extraction feature - only available in crawlit/2.0
                logger.info(f"[crawlit/2.0] Processing images from crawled pages...")
                
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
                    logger.info(f"[crawlit/2.0] Extracted {total_images} images from {pages_with_images} pages")
                    logger.info(f"[crawlit/2.0] Image data saved to {args.images_output}/ directory")
                    
                    # Log images by depth
                    for depth, count in sorted(images_by_depth.items()):
                        logger.debug(f"[crawlit/2.0] Depth {depth}: {count} images found")
                        
                    # Log some example URLs with images
                    for url in urls_with_images[:3]:  # Show first 3 examples
                        logger.debug(f"[crawlit/2.0] Images found on: {url}")
                    if len(urls_with_images) > 3:
                        logger.debug(f"[crawlit/2.0] ... and {len(urls_with_images) - 3} more pages with images")
                else:
                    logger.info("[crawlit/2.0] No images found on any crawled pages.")
        
        # Report skipped external URLs if domain restriction is enabled
        if not args.allow_external and hasattr(crawler, 'get_skipped_external_urls'):
            skipped = crawler.get_skipped_external_urls()
            if skipped:
                logger.info(f"Skipped {len(skipped)} external URLs (use --allow-external to crawl them)")
        
        # Save results to file in the specified format
        output_path = save_results(results, args.output_format, args.output, args.pretty_json)
        logger.info(f"Results saved to {output_path}")
        
        # Handle keyword extraction if enabled
        if args.extract_keywords and args.user_agent == "crawlit/2.0":
            logger.info(f"[crawlit/2.0] Processing keywords from crawled pages...")
            
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