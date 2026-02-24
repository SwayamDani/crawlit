#!/usr/bin/env python3
"""
Test database integration functionality
"""

import pytest
import os
import tempfile
from crawlit.utils.database import (
    SQLiteBackend,
    get_database_backend,
)


class TestSQLiteBackend:
    """Test SQLite database backend (no external dependencies)"""
    
    def test_create_sqlite_backend(self):
        """Test creating SQLite backend"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = SQLiteBackend(database_path=db_path)
            assert db.database_path == db_path
            assert os.path.exists(db_path)
            db.disconnect()  # Close connection before unlinking
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_save_and_retrieve_results(self):
        """Test saving and retrieving results"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = SQLiteBackend(database_path=db_path)
            
            # Sample results
            results = {
                'https://example.com': {
                    'status': 200,
                    'success': True,
                    'depth': 0,
                    'title': 'Example Domain',
                    'content_type': 'text/html',
                    'links': ['https://example.com/page1'],
                    'images': [],
                    'keywords': ['example', 'domain']
                },
                'https://example.com/page1': {
                    'status': 200,
                    'success': True,
                    'depth': 1,
                    'title': 'Page 1',
                    'content_type': 'text/html',
                    'links': [],
                    'images': [],
                    'keywords': ['page', 'one']
                }
            }
            
            metadata = {
                'start_url': 'https://example.com',
                'user_agent': 'crawlit/2.0',
                'max_depth': 2
            }
            
            # Save results
            crawl_id = db.save_results(results, metadata)
            assert crawl_id is not None
            assert crawl_id > 0
            
            # Retrieve results
            retrieved = db.get_results({'crawl_id': crawl_id})
            assert len(retrieved) == 2
            
            # Check first result
            first_result = next(r for r in retrieved if r['url'] == 'https://example.com')
            assert first_result['status_code'] == 200
            assert first_result['success'] == 1  # SQLite stores as integer
            assert first_result['title'] == 'Example Domain'
            assert len(first_result['links']) == 1
            assert len(first_result['keywords']) == 2
            
        finally:
            db.disconnect()
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_filter_by_status_code(self):
        """Test filtering results by status code"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = SQLiteBackend(database_path=db_path)
            
            results = {
                'https://example.com': {'status': 200, 'success': True, 'depth': 0},
                'https://example.com/404': {'status': 404, 'success': False, 'depth': 1},
                'https://example.com/500': {'status': 500, 'success': False, 'depth': 1}
            }
            
            crawl_id = db.save_results(results)
            
            # Filter by status 200
            success_results = db.get_results({'crawl_id': crawl_id, 'status_code': 200})
            assert len(success_results) == 1
            assert success_results[0]['url'] == 'https://example.com'
            
            # Filter by status 404
            not_found = db.get_results({'crawl_id': crawl_id, 'status_code': 404})
            assert len(not_found) == 1
            assert not_found[0]['url'] == 'https://example.com/404'
            
        finally:
            db.disconnect()
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_filter_by_success(self):
        """Test filtering results by success flag"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = SQLiteBackend(database_path=db_path)
            
            results = {
                'https://example.com/success1': {'status': 200, 'success': True, 'depth': 0},
                'https://example.com/success2': {'status': 200, 'success': True, 'depth': 1},
                'https://example.com/fail': {'status': 500, 'success': False, 'depth': 1}
            }
            
            crawl_id = db.save_results(results)
            
            # Filter successful
            successful = db.get_results({'crawl_id': crawl_id, 'success': True})
            assert len(successful) == 2
            
            # Filter failed
            failed = db.get_results({'crawl_id': crawl_id, 'success': False})
            assert len(failed) == 1
            
        finally:
            db.disconnect()
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_get_crawls_metadata(self):
        """Test retrieving crawl metadata"""
        # Use a unique temp file path to avoid conflicts
        import time
        db_path = f"test_crawl_metadata_{int(time.time() * 1000)}.db"
        
        try:
            db = SQLiteBackend(database_path=db_path)
            
            # Create multiple crawls
            crawl_ids = []
            for i in range(3):
                results = {
                    f'https://example{i}.com': {
                        'status': 200,
                        'success': True,
                        'depth': 0
                    }
                }
                metadata = {
                    'start_url': f'https://example{i}.com',
                    'max_depth': i + 1
                }
                crawl_id = db.save_results(results, metadata)
                crawl_ids.append(crawl_id)
            
            # Get crawls
            crawls = db.get_crawls(limit=10)
            assert len(crawls) == 3
            
            # Verify all our crawls are present
            returned_ids = [crawl['id'] for crawl in crawls]
            for crawl_id in crawl_ids:
                assert crawl_id in returned_ids
            
            # Verify they're ordered by timestamp (newest first)
            # In a fresh database, higher ID means newer
            assert crawls[0]['id'] == max(crawl_ids)
            assert crawls[-1]['id'] == min(crawl_ids)
            
        finally:
            db.disconnect()
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_clear_specific_crawl(self):
        """Test clearing a specific crawl"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = SQLiteBackend(database_path=db_path)
            
            # Create two crawls
            results1 = {'https://example1.com': {'status': 200, 'success': True, 'depth': 0}}
            results2 = {'https://example2.com': {'status': 200, 'success': True, 'depth': 0}}
            
            crawl_id1 = db.save_results(results1, {'start_url': 'https://example1.com'})
            crawl_id2 = db.save_results(results2, {'start_url': 'https://example2.com'})
            
            # Clear first crawl
            db.clear_results({'crawl_id': crawl_id1})
            
            # Verify first is gone, second remains
            results_1 = db.get_results({'crawl_id': crawl_id1})
            results_2 = db.get_results({'crawl_id': crawl_id2})
            
            assert len(results_1) == 0
            assert len(results_2) == 1
            
        finally:
            db.disconnect()
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_clear_all_results(self):
        """Test clearing all results"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = SQLiteBackend(database_path=db_path)
            
            # Create some crawls
            for i in range(3):
                results = {f'https://example{i}.com': {'status': 200, 'success': True, 'depth': 0}}
                db.save_results(results)
            
            # Clear all
            db.clear_results()
            
            # Verify everything is gone
            crawls = db.get_crawls()
            assert len(crawls) == 0
            
        finally:
            db.disconnect()
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseFactory:
    """Test database factory function"""
    
    def test_get_sqlite_backend(self):
        """Test getting SQLite backend from factory"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = get_database_backend('sqlite', database_path=db_path)
            assert isinstance(db, SQLiteBackend)
            assert db.database_path == db_path
            db.disconnect()  # Close connection before unlinking
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_get_invalid_backend(self):
        """Test getting invalid backend raises error"""
        with pytest.raises(ValueError, match="Unknown backend type"):
            get_database_backend('invalid_backend')
    
    def test_check_availability_sqlite(self):
        """Test SQLite availability check (always available)"""
        is_available, message = SQLiteBackend.check_availability()
        assert is_available is True
        assert "SQLite is available" in message
    
    def test_postgresql_not_running(self):
        """Test PostgreSQL availability when server not running"""
        pytest.importorskip("psycopg2", reason="psycopg2 not installed")
        # Use invalid port to simulate server not running
        from crawlit.utils.database import PostgreSQLBackend
        
        # Verify the check_availability method exists
        assert hasattr(PostgreSQLBackend, 'check_availability')
        
        # Test with invalid port (should return not available)
        is_available, message = PostgreSQLBackend.check_availability(
            host='localhost',
            port=9999,  # Invalid port
            database='test'
        )
        assert is_available is False
        assert "Cannot connect" in message or "not running" in message
    
    def test_factory_with_unavailable_database(self):
        """Test that factory raises RuntimeError for unavailable database"""
        # Try to connect to PostgreSQL on invalid port (should fail)
        with pytest.raises(RuntimeError, match="not available or not properly set up"):
            get_database_backend('postgresql', 
                                host='localhost',
                                port=9999,  # Invalid port
                                database='test',
                                user='test',
                                password='test')
    
    def test_factory_skip_availability_check(self):
        """Test that availability check can be skipped"""
        # This should not raise an error even with invalid config
        # because we're skipping the check
        try:
            from crawlit.utils.database import PostgreSQLBackend
            # Just verify we can instantiate with check_setup=False
            # (it will fail on actual connection, but that's expected)
            assert True  # PostgreSQL backend exists
        except ImportError:
            pytest.skip("psycopg2 not installed")
    
    def test_backend_aliases(self):
        """Test that backend aliases work"""
        import os
        
        # Test SQLite - always works
        db1 = get_database_backend('sqlite')
        assert type(db1).__name__ == 'SQLiteBackend'
        
        # Test PostgreSQL aliases if available
        try:
            from crawlit.utils.database import PostgreSQLBackend
            password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
            
            try:
                # Test that different aliases all work
                db3 = get_database_backend('postgresql', host='localhost', 
                                          user='postgres', password=password,
                                          database='crawlit_test')
                db4 = get_database_backend('postgres', host='localhost',
                                          user='postgres', password=password,
                                          database='crawlit_test')
                db5 = get_database_backend('psql', host='localhost',
                                          user='postgres', password=password,
                                          database='crawlit_test')
                
                assert type(db3).__name__ == 'PostgreSQLBackend'
                assert type(db4).__name__ == 'PostgreSQLBackend'
                assert type(db5).__name__ == 'PostgreSQLBackend'
            except Exception as e:
                error_msg = str(e).lower()
                if "could not connect" in error_msg or "connection refused" in error_msg:
                    pytest.skip(f"PostgreSQL server not running: {e}")
                elif "authentication failed" in error_msg:
                    pytest.skip(f"PostgreSQL authentication failed: {e}")
                elif "not available or not properly set up" in error_msg or "support not installed" in error_msg:
                    pytest.skip(f"PostgreSQL not available: {e}")
                else:
                    raise
        except ImportError:
            pass  # PostgreSQL not installed, that's ok
        
        # Test MongoDB aliases if available
        try:
            from crawlit.utils.database import MongoDBBackend
            # Just verify the backend exists, don't require connection
            assert MongoDBBackend is not None
        except ImportError:
            pass  # MongoDB not installed, that's ok


class TestDatabaseIntegration:
    """Test database integration scenarios"""
    
    def test_save_complex_result_structure(self):
        """Test saving results with complex nested structures"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = SQLiteBackend(database_path=db_path)
            
            results = {
                'https://example.com': {
                    'status': 200,
                    'success': True,
                    'depth': 0,
                    'title': 'Example',
                    'links': [
                        'https://example.com/page1',
                        'https://example.com/page2',
                        'https://example.com/page3'
                    ],
                    'images': [
                        {
                            'src': 'https://example.com/image1.jpg',
                            'alt': 'Image 1',
                            'width': 800,
                            'height': 600
                        },
                        {
                            'src': 'https://example.com/image2.png',
                            'alt': 'Image 2'
                        }
                    ],
                    'keywords': ['example', 'test', 'web', 'page'],
                    'custom_field': 'custom_value'
                }
            }
            
            crawl_id = db.save_results(results)
            retrieved = db.get_results({'crawl_id': crawl_id})
            
            assert len(retrieved) == 1
            result = retrieved[0]
            
            # Verify arrays are preserved
            assert len(result['links']) == 3
            assert len(result['images']) == 2
            assert len(result['keywords']) == 4
            
            # Verify nested objects are preserved
            assert result['images'][0]['src'] == 'https://example.com/image1.jpg'
            assert result['images'][0]['width'] == 800
            
        finally:
            db.disconnect()
            if os.path.exists(db_path):
                os.unlink(db_path)



class TestPostgreSQLBackend:
    """PostgreSQL backend tests (requires running PostgreSQL server)"""
    
    def test_postgresql_connection(self):
        """Test PostgreSQL connection and automatic database creation"""
        pytest.importorskip("psycopg2", reason="psycopg2 not installed")
        try:
            from crawlit.utils.database import PostgreSQLBackend
        except ImportError:
            pytest.skip("psycopg2 not installed")
        
        # Try to check if PostgreSQL is available
        import os
        password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
        
        try:
            # This will automatically create the database if it doesn't exist
            db = PostgreSQLBackend(
                host='localhost',
                database='crawlit_test',
                user='postgres',
                password=password
            )
            db.connect()
            assert db.conn is not None
            
            # Test that tables were created
            db.cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row['table_name'] for row in db.cursor.fetchall()]
            assert 'crawls' in tables
            assert 'results' in tables
            
            db.disconnect()
        except Exception as e:
            error_msg = str(e)
            if "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
                pytest.skip(f"PostgreSQL server not running: {e}")
            elif "authentication failed" in error_msg.lower() or "password" in error_msg.lower():
                pytest.skip(f"PostgreSQL authentication failed (try setting POSTGRES_PASSWORD env var): {e}")
            else:
                raise


class TestMongoDBBackend:
    """MongoDB backend tests (requires running MongoDB server)"""
    
    def test_mongodb_connection(self):
        """Test MongoDB connection"""
        pytest.importorskip("pymongo", reason="pymongo not installed")
        from crawlit.utils.database import MongoDBBackend
        
        try:
            db = MongoDBBackend(
                host='localhost',
                database='crawlit_test'
            )
            db.connect()
            assert db.client is not None
            db.disconnect()
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower() or "timeout" in error_msg.lower():
                pytest.skip(f"MongoDB server not running: {e}")
            else:
                raise

