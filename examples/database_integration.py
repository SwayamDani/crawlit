#!/usr/bin/env python3
"""
Database Integration Examples

This script demonstrates how to use crawlit with database backends:
- SQLite (built-in, no extra dependencies)
- PostgreSQL (requires psycopg2-binary)
- MongoDB (requires pymongo)
"""

from crawlit.crawler import Crawler
from crawlit.utils.database import get_database_backend, SQLiteBackend
import os


def example_1_sqlite_basic():
    """
    Example 1: Basic SQLite database integration
    
    SQLite is perfect for:
    - Local development and testing
    - Single-user applications
    - Embedded databases
    - No extra dependencies needed!
    """
    print("=" * 60)
    print("Example 1: Basic SQLite Integration")
    print("=" * 60)
    
    # Initialize SQLite database
    db = SQLiteBackend(database_path="crawl_results.db")
    
    # Crawl a website
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=2,
        internal_only=True,
        user_agent="crawlit/2.0 (Database Example)"
    )
    
    results = crawler.crawl()
    
    # Save results to database
    metadata = {
        'start_url': crawler.start_url,
        'max_depth': crawler.max_depth,
        'user_agent': crawler.user_agent,
        'internal_only': crawler.internal_only
    }
    
    crawl_id = db.save_results(results, metadata)
    print(f"\n✓ Saved {len(results)} pages to SQLite database")
    print(f"  Crawl ID: {crawl_id}")
    
    # Retrieve and display results
    print("\nStored crawls:")
    crawls = db.get_crawls(limit=5)
    for crawl in crawls:
        print(f"  [{crawl['id']}] {crawl['start_url']} - "
              f"{crawl['successful_urls']}/{crawl['total_urls']} successful")
    
    db.disconnect()
    print("\n✓ Example completed successfully!")


def example_2_sqlite_querying():
    """
    Example 2: Advanced SQLite querying
    
    Demonstrates filtering and querying stored results
    """
    print("\n" + "=" * 60)
    print("Example 2: Advanced SQLite Querying")
    print("=" * 60)
    
    db = SQLiteBackend(database_path="crawl_results.db")
    
    # First, let's crawl a site
    crawler = Crawler(
        start_url="https://python.org",
        max_depth=1,
        internal_only=True
    )
    
    results = crawler.crawl()
    crawl_id = db.save_results(results, {'start_url': 'https://python.org'})
    
    print(f"\n✓ Crawled and saved {len(results)} pages")
    
    # Query 1: Get all successful pages
    print("\n1. Successful pages (status 200):")
    successful = db.get_results({'crawl_id': crawl_id, 'status_code': 200})
    for page in successful[:5]:  # Show first 5
        print(f"   • {page['url'][:60]}...")
    print(f"   ... {len(successful)} total successful pages")
    
    # Query 2: Get failed pages
    print("\n2. Failed pages:")
    failed = db.get_results({'crawl_id': crawl_id, 'success': False})
    if failed:
        for page in failed[:3]:
            print(f"   • {page['url'][:60]}... (status: {page['status_code']})")
    else:
        print("   No failed pages!")
    
    # Query 3: Search by URL pattern
    print("\n3. Pages matching '/download':")
    download_pages = db.get_results({'crawl_id': crawl_id, 'url': '/download'})
    for page in download_pages[:3]:
        print(f"   • {page['url'][:60]}...")
    
    db.disconnect()
    print("\n✓ Querying example completed!")


def example_3_sqlite_cleanup():
    """
    Example 3: Database cleanup and management
    """
    print("\n" + "=" * 60)
    print("Example 3: Database Cleanup")
    print("=" * 60)
    
    db = SQLiteBackend(database_path="crawl_results.db")
    
    # Show all crawls
    crawls = db.get_crawls(limit=100)
    print(f"\nTotal crawls in database: {len(crawls)}")
    
    if len(crawls) > 0:
        # Delete oldest crawl
        oldest_crawl = crawls[-1]
        print(f"\nDeleting oldest crawl:")
        print(f"  ID: {oldest_crawl['id']}")
        print(f"  URL: {oldest_crawl['start_url']}")
        print(f"  Date: {oldest_crawl['timestamp']}")
        
        db.clear_results({'crawl_id': oldest_crawl['id']})
        print("  ✓ Deleted")
        
        # Show updated count
        crawls = db.get_crawls()
        print(f"\nRemaining crawls: {len(crawls)}")
    
    # Optional: Clear all results
    # Uncomment to clear everything:
    # db.clear_results()
    # print("\n✓ All results cleared")
    
    db.disconnect()


def example_4_postgresql():
    """
    Example 4: PostgreSQL database integration
    
    PostgreSQL is ideal for:
    - Production environments
    - Multi-user applications
    - Advanced querying needs
    - ACID compliance requirements
    
    Requirements:
    - pip install psycopg2-binary
    - Running PostgreSQL server
    """
    print("\n" + "=" * 60)
    print("Example 4: PostgreSQL Integration")
    print("=" * 60)
    
    try:
        # Initialize PostgreSQL backend
        db = get_database_backend(
            'postgresql',
            host='localhost',
            port=5432,
            database='crawlit',
            user='postgres',
            password='your_password'  # Change this!
        )
        
        # Crawl and save
        crawler = Crawler(
            start_url="https://example.com",
            max_depth=1,
            internal_only=True
        )
        
        results = crawler.crawl()
        crawl_id = db.save_results(results, {'start_url': 'https://example.com'})
        
        print(f"✓ Saved {len(results)} pages to PostgreSQL")
        print(f"  Crawl ID: {crawl_id}")
        
        # Query results
        all_results = db.get_results({'crawl_id': crawl_id})
        print(f"✓ Retrieved {len(all_results)} results from PostgreSQL")
        
        db.disconnect()
        
    except ImportError:
        print("⚠ PostgreSQL support requires: pip install psycopg2-binary")
    except Exception as e:
        print(f"⚠ PostgreSQL error: {e}")
        print("  Make sure PostgreSQL is running and credentials are correct")


def example_5_mongodb():
    """
    Example 5: MongoDB database integration
    
    MongoDB is perfect for:
    - Unstructured/semi-structured data
    - Flexible schemas
    - Document-oriented storage
    - High write throughput
    
    Requirements:
    - pip install pymongo
    - Running MongoDB server
    """
    print("\n" + "=" * 60)
    print("Example 5: MongoDB Integration")
    print("=" * 60)
    
    try:
        # Initialize MongoDB backend
        db = get_database_backend(
            'mongodb',
            host='localhost',
            port=27017,
            database='crawlit',
            collection='crawl_results'
        )
        
        # Crawl and save
        crawler = Crawler(
            start_url="https://example.com",
            max_depth=1,
            internal_only=True
        )
        
        results = crawler.crawl()
        crawl_id = db.save_results(results, {'start_url': 'https://example.com'})
        
        print(f"✓ Saved {len(results)} pages to MongoDB")
        print(f"  Crawl ID: {crawl_id}")
        
        # Query results
        all_results = db.get_results({'crawl_id': crawl_id})
        print(f"✓ Retrieved {len(all_results)} results from MongoDB")
        
        db.disconnect()
        
    except ImportError:
        print("⚠ MongoDB support requires: pip install pymongo")
    except Exception as e:
        print(f"⚠ MongoDB error: {e}")
        print("  Make sure MongoDB is running")


def example_6_factory_pattern():
    """
    Example 6: Using the factory pattern for flexible backend selection
    """
    print("\n" + "=" * 60)
    print("Example 6: Factory Pattern for Database Selection")
    print("=" * 60)
    
    # Configuration can come from environment, config file, etc.
    db_config = {
        'backend': 'sqlite',  # Can be 'sqlite', 'postgresql', or 'mongodb'
        'sqlite': {'database_path': 'crawl_results.db'},
        'postgresql': {
            'host': 'localhost',
            'database': 'crawlit',
            'user': 'postgres',
            'password': 'password'
        },
        'mongodb': {
            'host': 'localhost',
            'database': 'crawlit'
        }
    }
    
    # Get backend based on configuration
    backend_type = db_config['backend']
    backend_config = db_config[backend_type]
    
    print(f"Using {backend_type} backend")
    
    db = get_database_backend(backend_type, **backend_config)
    
    # Use the database
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=1
    )
    
    results = crawler.crawl()
    crawl_id = db.save_results(results, {'start_url': 'https://example.com'})
    
    print(f"✓ Saved {len(results)} pages using {backend_type}")
    
    db.disconnect()


def example_7_with_js_rendering():
    """
    Example 7: Database integration with JavaScript rendering
    
    Combines database storage with JS rendering for SPAs
    """
    print("\n" + "=" * 60)
    print("Example 7: Database + JavaScript Rendering")
    print("=" * 60)
    
    db = SQLiteBackend(database_path="spa_crawl_results.db")
    
    try:
        # Crawl a JavaScript-heavy site
        crawler = Crawler(
            start_url="https://react-example.com",  # Replace with actual SPA
            max_depth=1,
            internal_only=True,
            use_js_rendering=True,
            js_wait_for_timeout=2000,
            js_browser_type="chromium"
        )
        
        print("Crawling JavaScript-rendered site...")
        results = crawler.crawl()
        
        # Save to database
        metadata = {
            'start_url': crawler.start_url,
            'js_rendering': True,
            'browser_type': 'chromium'
        }
        
        crawl_id = db.save_results(results, metadata)
        print(f"✓ Saved {len(results)} JS-rendered pages to database")
        print(f"  Crawl ID: {crawl_id}")
        
    except ImportError:
        print("⚠ JavaScript rendering requires: playwright install")
    except Exception as e:
        print(f"⚠ Error: {e}")
    finally:
        db.disconnect()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("CRAWLIT DATABASE INTEGRATION EXAMPLES")
    print("=" * 60)
    
    # Run SQLite examples (always available)
    example_1_sqlite_basic()
    example_2_sqlite_querying()
    example_3_sqlite_cleanup()
    example_6_factory_pattern()
    
    # Optional examples (require external dependencies/servers)
    # Uncomment to run:
    # example_4_postgresql()
    # example_5_mongodb()
    # example_7_with_js_rendering()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nNote: Database files created:")
    print("  - crawl_results.db")
    print("  - spa_crawl_results.db (if JS rendering example was run)")
    print("\nTo inspect the database, you can use:")
    print("  sqlite3 crawl_results.db")
    print("  sqlite> SELECT * FROM crawls;")
    print("  sqlite> SELECT url, status_code, title FROM results LIMIT 10;")


if __name__ == "__main__":
    main()




