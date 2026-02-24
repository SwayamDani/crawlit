#!/usr/bin/env python3
"""
Database Availability Check Examples

This script demonstrates how to check database availability before using it.
"""

from crawlit.utils.database import (
    SQLiteBackend,
    PostgreSQLBackend,
    MongoDBBackend,
    get_database_backend
)


def example_1_check_before_use():
    """
    Example 1: Manually check database availability before creating backend
    """
    print("=" * 60)
    print("Example 1: Manual Availability Check")
    print("=" * 60)
    
    # Check SQLite (always available)
    is_available, message = SQLiteBackend.check_availability()
    print(f"\nSQLite: {message}")
    
    # Check PostgreSQL
    print("\n" + "-" * 60)
    is_available, message = PostgreSQLBackend.check_availability(
        host='localhost',
        database='crawlit',
        user='postgres',
        password=''
    )
    print(f"PostgreSQL: {message}")
    
    # Check MongoDB
    print("\n" + "-" * 60)
    is_available, message = MongoDBBackend.check_availability(
        host='localhost',
        port=27017
    )
    print(f"MongoDB: {message}")


def example_2_automatic_check():
    """
    Example 2: Automatic availability check via factory (default behavior)
    """
    print("\n" + "=" * 60)
    print("Example 2: Automatic Availability Check")
    print("=" * 60)
    
    # Try SQLite (will succeed)
    print("\nTrying SQLite...")
    try:
        db = get_database_backend('sqlite', database_path='test.db')
        print("[OK] SQLite backend created successfully!")
        db.disconnect()
    except RuntimeError as e:
        print(f"[ERROR] Failed: {e}")
    
    # Try PostgreSQL (may fail if not set up)
    print("\nTrying PostgreSQL...")
    try:
        db = get_database_backend(
            'postgresql',
            host='localhost',
            database='crawlit',
            user='postgres',
            password=''
        )
        print("[OK] PostgreSQL backend created successfully!")
        db.disconnect()
    except RuntimeError as e:
        print("[ERROR] PostgreSQL not available:")
        print(str(e))
    
    # Try MongoDB (may fail if not set up)
    print("\nTrying MongoDB...")
    try:
        db = get_database_backend(
            'mongodb',
            host='localhost',
            port=27017
        )
        print("[OK] MongoDB backend created successfully!")
        db.disconnect()
    except RuntimeError as e:
        print("[ERROR] MongoDB not available:")
        print(str(e))


def example_3_graceful_fallback():
    """
    Example 3: Graceful fallback to file output if database unavailable
    """
    print("\n" + "=" * 60)
    print("Example 3: Graceful Fallback")
    print("=" * 60)
    
    from crawlit import Crawler
    import json
    
    # Prefer PostgreSQL, fallback to SQLite, ultimate fallback to file
    backends_to_try = [
        ('postgresql', {
            'host': 'localhost',
            'database': 'crawlit',
            'user': 'postgres',
            'password': ''
        }),
        ('sqlite', {
            'database_path': 'crawl_backup.db'
        })
    ]
    
    db = None
    db_type = None
    
    for backend_type, config in backends_to_try:
        print(f"\nTrying {backend_type}...")
        try:
            db = get_database_backend(backend_type, **config)
            db_type = backend_type
            print(f"[OK] Connected to {backend_type}")
            break
        except RuntimeError:
            print(f"[ERROR] {backend_type} not available, trying next option...")
    
    # Crawl (simplified for example)
    print("\nCrawling website...")
    results = {
        'https://example.com': {
            'status': 200,
            'success': True,
            'depth': 0,
            'title': 'Example Domain'
        }
    }
    
    # Save results
    if db:
        print(f"\nSaving to {db_type} database...")
        crawl_id = db.save_results(results, {'start_url': 'https://example.com'})
        print(f"[OK] Saved to {db_type} (crawl_id: {crawl_id})")
        db.disconnect()
    else:
        print("\n⚠ No database available, saving to file...")
        with open('crawl_results_fallback.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("[OK] Saved to crawl_results_fallback.json")


def example_4_skip_check():
    """
    Example 4: Skip availability check (advanced use case)
    
    Warning: Only use this if you're handling connection errors yourself!
    """
    print("\n" + "=" * 60)
    print("Example 4: Skip Availability Check (Advanced)")
    print("=" * 60)
    
    print("\nSkipping availability check for SQLite...")
    try:
        # check_setup=False skips the availability check
        db = get_database_backend('sqlite', 
                                  check_setup=False,
                                  database_path='no_check.db')
        print("[OK] Backend created without availability check")
        db.disconnect()
    except Exception as e:
        print(f"[ERROR] Error: {e}")


def example_5_detailed_diagnostics():
    """
    Example 5: Detailed database diagnostics
    """
    print("\n" + "=" * 60)
    print("Example 5: Detailed Database Diagnostics")
    print("=" * 60)
    
    databases = [
        ('SQLite', SQLiteBackend, {}),
        ('PostgreSQL', PostgreSQLBackend, {
            'host': 'localhost',
            'database': 'crawlit',
            'user': 'postgres'
        }),
        ('MongoDB', MongoDBBackend, {
            'host': 'localhost',
            'port': 27017
        })
    ]
    
    print("\n" + "Database Availability Report".center(60))
    print("=" * 60)
    
    available_count = 0
    
    for name, backend_class, config in databases:
        print(f"\n{name}:")
        print("-" * 40)
        
        is_available, message = backend_class.check_availability(**config)
        print(message)
        
        if is_available:
            available_count += 1
            print(f"Status: [OK] READY")
        else:
            print(f"Status: [ERROR] NOT AVAILABLE")
    
    print("\n" + "=" * 60)
    print(f"Summary: {available_count}/{len(databases)} databases available")
    print("=" * 60)


def example_6_custom_error_handling():
    """
    Example 6: Custom error handling with specific error messages
    """
    print("\n" + "=" * 60)
    print("Example 6: Custom Error Handling")
    print("=" * 60)
    
    def try_connect_database(backend_type, **config):
        """Helper function with custom error handling"""
        try:
            db = get_database_backend(backend_type, **config)
            return db, None
        except RuntimeError as e:
            error_msg = str(e)
            
            # Parse error type
            if "not installed" in error_msg:
                return None, "DEPENDENCY_MISSING"
            elif "not running" in error_msg or "Connection refused" in error_msg:
                return None, "SERVER_NOT_RUNNING"
            elif "authentication failed" in error_msg or "password" in error_msg:
                return None, "AUTH_FAILED"
            elif "does not exist" in error_msg:
                return None, "DATABASE_NOT_EXIST"
            else:
                return None, "UNKNOWN_ERROR"
    
    # Try PostgreSQL with custom handling
    print("\nTrying PostgreSQL with custom error handling...")
    db, error = try_connect_database(
        'postgresql',
        host='localhost',
        database='crawlit',
        user='postgres',
        password=''
    )
    
    if db:
        print("[OK] Connected successfully!")
        db.disconnect()
    else:
        print(f"[ERROR] Connection failed: {error}")
        
        # Take specific action based on error type
        if error == "DEPENDENCY_MISSING":
            print("   → Install: pip install psycopg2-binary")
        elif error == "SERVER_NOT_RUNNING":
            print("   → Start PostgreSQL server")
        elif error == "AUTH_FAILED":
            print("   → Check username/password")
        elif error == "DATABASE_NOT_EXIST":
            print("   → Create database first")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("DATABASE AVAILABILITY CHECK EXAMPLES")
    print("=" * 60)
    
    example_1_check_before_use()
    example_2_automatic_check()
    example_3_graceful_fallback()
    example_4_skip_check()
    example_5_detailed_diagnostics()
    example_6_custom_error_handling()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

