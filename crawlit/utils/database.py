#!/usr/bin/env python3
"""
database.py - Database integration for crawlit

Provides support for storing crawl results in databases:
- SQLite (built-in, no extra dependencies)
- PostgreSQL (requires psycopg2)
- MongoDB (requires pymongo)
"""

import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DatabaseBackend(ABC):
    """Abstract base class for database backends"""
    
    @classmethod
    @abstractmethod
    def check_availability(cls, **config) -> tuple[bool, str]:
        """
        Check if database backend is available and properly configured.
        
        Returns:
            tuple: (is_available: bool, message: str)
                   If available, message contains success info.
                   If not available, message contains setup instructions.
        """
        pass
    
    @abstractmethod
    def connect(self):
        """Establish database connection"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close database connection"""
        pass
    
    @abstractmethod
    def save_results(self, results: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Save crawl results to database"""
        pass
    
    @abstractmethod
    def get_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve crawl results from database"""
        pass
    
    @abstractmethod
    def clear_results(self, filters: Optional[Dict[str, Any]] = None):
        """Clear results from database"""
        pass


class SQLiteBackend(DatabaseBackend):
    """
    SQLite database backend for crawlit results.
    
    Features:
    - No external dependencies (uses built-in sqlite3)
    - Lightweight and portable
    - Perfect for local development and testing
    """
    
    def __init__(self, database_path: str = "crawlit_results.db"):
        """
        Initialize SQLite backend.
        
        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.conn = None
        self.cursor = None
        self._create_tables()
    
    @classmethod
    def check_availability(cls, **config) -> tuple[bool, str]:
        """
        Check if SQLite is available (always true since it's built-in).
        
        Returns:
            tuple: (True, success_message) - SQLite is always available
        """
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return (True, f"[OK] SQLite is available (built-in with Python {python_version})")
    
    def connect(self):
        """Establish SQLite connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.database_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to SQLite database: {self.database_path}")
    
    def disconnect(self):
        """Close SQLite connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            logger.info("SQLite connection closed")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        self.connect()
        
        # Crawls table - metadata about each crawl session
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_url TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_agent TEXT,
                max_depth INTEGER,
                total_urls INTEGER DEFAULT 0,
                successful_urls INTEGER DEFAULT 0,
                failed_urls INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Results table - individual page results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id INTEGER,
                url TEXT NOT NULL,
                status_code INTEGER,
                success INTEGER,
                depth INTEGER,
                title TEXT,
                content_type TEXT,
                html_content TEXT,
                links TEXT,
                images TEXT,
                keywords TEXT,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (crawl_id) REFERENCES crawls(id)
            )
        """)
        
        # Create indexes for better query performance
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_url ON results(url)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_crawl_id ON results(crawl_id)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_status ON results(status_code)
        """)
        
        self.conn.commit()
        logger.debug("SQLite tables created/verified")
    
    def save_results(self, results: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """
        Save crawl results to SQLite database.
        
        Args:
            results: Dictionary of crawl results (URL -> result data)
            metadata: Optional metadata about the crawl session
        """
        self.connect()
        
        # Extract metadata
        meta = metadata or {}
        start_url = meta.get('start_url', 'unknown')
        user_agent = meta.get('user_agent', 'crawlit/1.0')
        max_depth = meta.get('max_depth', 0)
        
        # Count statistics
        total_urls = len(results)
        successful_urls = sum(1 for r in results.values() if r.get('success', False))
        failed_urls = total_urls - successful_urls
        
        # Insert crawl metadata
        self.cursor.execute("""
            INSERT INTO crawls (start_url, timestamp, user_agent, max_depth, 
                               total_urls, successful_urls, failed_urls, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            start_url,
            datetime.now().isoformat(),
            user_agent,
            max_depth,
            total_urls,
            successful_urls,
            failed_urls,
            json.dumps(meta)
        ))
        
        crawl_id = self.cursor.lastrowid
        
        # Insert individual results
        for url, result in results.items():
            links_json = json.dumps(result.get('links', []))
            images_json = json.dumps(result.get('images', []))
            keywords_json = json.dumps(result.get('keywords', []))
            result_metadata = json.dumps({
                k: v for k, v in result.items()
                if k not in ['url', 'status', 'success', 'depth', 'title', 
                           'content_type', 'html_content', 'links', 'images', 'keywords']
            })
            
            self.cursor.execute("""
                INSERT INTO results (crawl_id, url, status_code, success, depth,
                                   title, content_type, html_content, links,
                                   images, keywords, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                crawl_id,
                url,
                result.get('status', 0),
                int(result.get('success', False)),
                result.get('depth', 0),
                result.get('title', ''),
                result.get('content_type', ''),
                result.get('html_content', ''),
                links_json,
                images_json,
                keywords_json,
                result_metadata,
                datetime.now().isoformat()
            ))
        
        self.conn.commit()
        logger.info(f"Saved {total_urls} results to SQLite (crawl_id: {crawl_id})")
        return crawl_id
    
    def get_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve results from SQLite database.
        
        Args:
            filters: Optional filters (crawl_id, url, status_code, etc.)
            
        Returns:
            List of result dictionaries
        """
        self.connect()
        
        query = "SELECT * FROM results WHERE 1=1"
        params = []
        
        if filters:
            if 'crawl_id' in filters:
                query += " AND crawl_id = ?"
                params.append(filters['crawl_id'])
            if 'url' in filters:
                query += " AND url LIKE ?"
                params.append(f"%{filters['url']}%")
            if 'status_code' in filters:
                query += " AND status_code = ?"
                params.append(filters['status_code'])
            if 'success' in filters:
                query += " AND success = ?"
                params.append(int(filters['success']))
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON fields
            if result.get('links'):
                result['links'] = json.loads(result['links'])
            if result.get('images'):
                result['images'] = json.loads(result['images'])
            if result.get('keywords'):
                result['keywords'] = json.loads(result['keywords'])
            if result.get('metadata'):
                result['metadata'] = json.loads(result['metadata'])
            results.append(result)
        
        logger.info(f"Retrieved {len(results)} results from SQLite")
        return results
    
    def get_crawls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of crawl sessions"""
        self.connect()
        
        self.cursor.execute("""
            SELECT * FROM crawls ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        
        rows = self.cursor.fetchall()
        crawls = []
        for row in rows:
            crawl = dict(row)
            if crawl.get('metadata'):
                crawl['metadata'] = json.loads(crawl['metadata'])
            crawls.append(crawl)
        
        return crawls
    
    def clear_results(self, filters: Optional[Dict[str, Any]] = None):
        """Clear results from database"""
        self.connect()
        
        if filters and 'crawl_id' in filters:
            # Delete specific crawl
            crawl_id = filters['crawl_id']
            self.cursor.execute("DELETE FROM results WHERE crawl_id = ?", (crawl_id,))
            self.cursor.execute("DELETE FROM crawls WHERE id = ?", (crawl_id,))
            logger.info(f"Deleted crawl {crawl_id}")
        else:
            # Clear all results
            self.cursor.execute("DELETE FROM results")
            self.cursor.execute("DELETE FROM crawls")
            logger.info("Cleared all results from SQLite")
        
        self.conn.commit()


class PostgreSQLBackend(DatabaseBackend):
    """
    PostgreSQL database backend for crawlit results.
    
    Features:
    - Production-ready relational database
    - ACID compliance
    - Advanced querying capabilities
    
    Requires: psycopg2
    """
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "crawlit", user: str = "postgres",
                 password: str = "", **kwargs):
        """
        Initialize PostgreSQL backend.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            **kwargs: Additional psycopg2 connection parameters
        """
        try:
            import psycopg2
            import psycopg2.extras
            import psycopg2.sql
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
            self.sql = psycopg2.sql
        except ImportError:
            raise ImportError(
                "PostgreSQL support requires psycopg2. "
                "Install with: pip install psycopg2-binary"
            )
        
        self.config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password,
            **kwargs
        }
        self.conn = None
        self.cursor = None
        self._ensure_database_exists()
        self._create_tables()
    
    def _ensure_database_exists(self):
        """Create the database if it doesn't exist"""
        try:
            # First, try to connect to the target database
            conn = self.psycopg2.connect(**self.config)
            conn.close()
            logger.debug(f"Database '{self.config['database']}' exists")
        except self.psycopg2.OperationalError as e:
            error_msg = str(e)
            
            # Check if error is because database doesn't exist
            if "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                logger.info(f"Database '{self.config['database']}' does not exist, creating it...")
                
                # Connect to 'postgres' database to create the new database
                temp_config = self.config.copy()
                temp_config['database'] = 'postgres'
                
                try:
                    conn = self.psycopg2.connect(**temp_config)
                    conn.autocommit = True  # Required for CREATE DATABASE
                    cursor = conn.cursor()
                    
                    # Create the database (use Identifier to prevent SQL injection)
                    cursor.execute(
                        self.sql.SQL("CREATE DATABASE {}").format(
                            self.sql.Identifier(self.config['database'])
                        )
                    )
                    
                    cursor.close()
                    conn.close()
                    logger.info(f"Database '{self.config['database']}' created successfully")
                except Exception as create_error:
                    logger.error(f"Failed to create database: {create_error}")
                    raise
            else:
                # Re-raise if it's a different error (connection, auth, etc.)
                raise
    
    @classmethod
    def check_availability(cls, **config) -> tuple[bool, str]:
        """
        Check if PostgreSQL is available and accessible.
        
        Returns:
            tuple: (is_available, message)
        """
        # Check if psycopg2 is installed
        try:
            import psycopg2
        except ImportError:
            return (False, 
                    "[ERROR] PostgreSQL support not installed.\n\n"
                    "To use PostgreSQL, install the required dependency:\n"
                    "  pip install crawlit[postgresql]\n"
                    "  OR\n"
                    "  pip install psycopg2-binary\n")
        
        # Check if we can connect to the database
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        database = config.get('database', 'crawlit')
        user = config.get('user', 'postgres')
        password = config.get('password', '')
        
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=3
            )
            conn.close()
            return (True, f"[OK] PostgreSQL is available at {host}:{port}/{database}")
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            
            if "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
                return (False,
                        f"[ERROR] Cannot connect to PostgreSQL at {host}:{port}\n\n"
                        "PostgreSQL server is not running or not accessible.\n\n"
                        "Setup instructions:\n"
                        "1. Install PostgreSQL:\n"
                        "   Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib\n"
                        "   macOS: brew install postgresql\n"
                        "   Windows: Download from https://www.postgresql.org/download/\n\n"
                        "2. Start PostgreSQL:\n"
                        "   Linux: sudo systemctl start postgresql\n"
                        "   macOS: brew services start postgresql\n"
                        "   Windows: Start via Services app\n\n"
                        "3. Create database and user:\n"
                        "   sudo -u postgres psql\n"
                        "   CREATE DATABASE crawlit;\n"
                        "   CREATE USER crawlit_user WITH PASSWORD 'your_password';\n"
                        "   GRANT ALL PRIVILEGES ON DATABASE crawlit TO crawlit_user;\n")
            
            elif "authentication failed" in error_msg.lower() or "password" in error_msg.lower():
                return (False,
                        f"[ERROR] Authentication failed for PostgreSQL\n\n"
                        "The username or password is incorrect.\n\n"
                        "To fix:\n"
                        "1. Check your credentials\n"
                        "2. Reset password if needed:\n"
                        "   sudo -u postgres psql\n"
                        "   ALTER USER {user} WITH PASSWORD 'new_password';\n")
            
            elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                return (False,
                        f"[ERROR] Database '{database}' does not exist\n\n"
                        "To create the database:\n"
                        "  sudo -u postgres psql\n"
                        f"  CREATE DATABASE {database};\n"
                        f"  GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};\n")
            
            else:
                return (False, f"[ERROR] PostgreSQL error: {error_msg}\n")
        except Exception as e:
            return (False, f"[ERROR] Unexpected error checking PostgreSQL: {e}\n")
    
    def connect(self):
        """Establish PostgreSQL connection"""
        if self.conn is None or self.conn.closed:
            self.conn = self.psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor(cursor_factory=self.extras.RealDictCursor)
            logger.info(f"Connected to PostgreSQL: {self.config['host']}:{self.config['port']}/{self.config['database']}")
    
    def disconnect(self):
        """Close PostgreSQL connection"""
        if self.conn and not self.conn.closed:
            self.cursor.close()
            self.conn.close()
            logger.info("PostgreSQL connection closed")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        self.connect()
        
        # Crawls table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawls (
                id SERIAL PRIMARY KEY,
                start_url TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT,
                max_depth INTEGER,
                total_urls INTEGER DEFAULT 0,
                successful_urls INTEGER DEFAULT 0,
                failed_urls INTEGER DEFAULT 0,
                metadata JSONB
            )
        """)
        
        # Results table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                crawl_id INTEGER REFERENCES crawls(id) ON DELETE CASCADE,
                url TEXT NOT NULL,
                status_code INTEGER,
                success BOOLEAN,
                depth INTEGER,
                title TEXT,
                content_type TEXT,
                html_content TEXT,
                links JSONB,
                images JSONB,
                keywords JSONB,
                metadata JSONB,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_url ON results(url)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_crawl_id ON results(crawl_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_status ON results(status_code)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_metadata ON results USING GIN(metadata)")
        
        self.conn.commit()
        logger.debug("PostgreSQL tables created/verified")
    
    def save_results(self, results: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Save crawl results to PostgreSQL"""
        self.connect()
        
        # Extract metadata
        meta = metadata or {}
        start_url = meta.get('start_url', 'unknown')
        user_agent = meta.get('user_agent', 'crawlit/1.0')
        max_depth = meta.get('max_depth', 0)
        
        # Count statistics
        total_urls = len(results)
        successful_urls = sum(1 for r in results.values() if r.get('success', False))
        failed_urls = total_urls - successful_urls
        
        # Insert crawl metadata
        self.cursor.execute("""
            INSERT INTO crawls (start_url, user_agent, max_depth, 
                               total_urls, successful_urls, failed_urls, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            start_url, user_agent, max_depth,
            total_urls, successful_urls, failed_urls,
            self.extras.Json(meta)
        ))
        
        crawl_id = self.cursor.fetchone()['id']
        
        # Insert individual results
        for url, result in results.items():
            result_metadata = {
                k: v for k, v in result.items()
                if k not in ['url', 'status', 'success', 'depth', 'title',
                           'content_type', 'html_content', 'links', 'images', 'keywords']
            }
            
            self.cursor.execute("""
                INSERT INTO results (crawl_id, url, status_code, success, depth,
                                   title, content_type, html_content, links,
                                   images, keywords, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                crawl_id, url,
                result.get('status', 0),
                result.get('success', False),
                result.get('depth', 0),
                result.get('title', ''),
                result.get('content_type', ''),
                result.get('html_content', ''),
                self.extras.Json(result.get('links', [])),
                self.extras.Json(result.get('images', [])),
                self.extras.Json(result.get('keywords', [])),
                self.extras.Json(result_metadata)
            ))
        
        self.conn.commit()
        logger.info(f"Saved {total_urls} results to PostgreSQL (crawl_id: {crawl_id})")
        return crawl_id
    
    def get_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve results from PostgreSQL"""
        self.connect()
        
        query = "SELECT * FROM results WHERE 1=1"
        params = []
        
        if filters:
            if 'crawl_id' in filters:
                params.append(filters['crawl_id'])
                query += f" AND crawl_id = ${len(params)}"
            if 'url' in filters:
                params.append(f"%{filters['url']}%")
                query += f" AND url LIKE ${len(params)}"
            if 'status_code' in filters:
                params.append(filters['status_code'])
                query += f" AND status_code = ${len(params)}"
            if 'success' in filters:
                params.append(filters['success'])
                query += f" AND success = ${len(params)}"
        
        # Convert $1, $2 to %s for psycopg2
        for i in range(len(params), 0, -1):
            query = query.replace(f"${i}", "%s")
        
        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        
        logger.info(f"Retrieved {len(results)} results from PostgreSQL")
        return [dict(row) for row in results]
    
    def clear_results(self, filters: Optional[Dict[str, Any]] = None):
        """Clear results from PostgreSQL"""
        self.connect()
        
        if filters and 'crawl_id' in filters:
            self.cursor.execute("DELETE FROM crawls WHERE id = %s", (filters['crawl_id'],))
            logger.info(f"Deleted crawl {filters['crawl_id']}")
        else:
            self.cursor.execute("DELETE FROM results")
            self.cursor.execute("DELETE FROM crawls")
            logger.info("Cleared all results from PostgreSQL")
        
        self.conn.commit()


class MongoDBBackend(DatabaseBackend):
    """
    MongoDB database backend for crawlit results.
    
    Features:
    - NoSQL document storage
    - Flexible schema
    - Excellent for unstructured data
    
    Requires: pymongo
    """
    
    def __init__(self, host: str = "localhost", port: int = 27017,
                 database: str = "crawlit", collection: str = "results",
                 username: Optional[str] = None, password: Optional[str] = None,
                 **kwargs):
        """
        Initialize MongoDB backend.
        
        Args:
            host: MongoDB host
            port: MongoDB port
            database: Database name
            collection: Collection name for results
            username: Optional username
            password: Optional password
            **kwargs: Additional pymongo connection parameters
        """
        try:
            import pymongo
            self.pymongo = pymongo
        except ImportError:
            raise ImportError(
                "MongoDB support requires pymongo. "
                "Install with: pip install pymongo"
            )
        
        self.host = host
        self.port = port
        self.database_name = database
        self.collection_name = collection
        self.username = username
        self.password = password
        self.kwargs = kwargs
        
        self.client = None
        self.db = None
        self.collection = None
        self.connect()
    
    @classmethod
    def check_availability(cls, **config) -> tuple[bool, str]:
        """
        Check if MongoDB is available and accessible.
        
        Returns:
            tuple: (is_available, message)
        """
        # Check if pymongo is installed
        try:
            import pymongo
        except ImportError:
            return (False,
                    "[ERROR] MongoDB support not installed.\n\n"
                    "To use MongoDB, install the required dependency:\n"
                    "  pip install crawlit[mongodb]\n"
                    "  OR\n"
                    "  pip install pymongo\n")
        
        # Check if we can connect to MongoDB
        host = config.get('host', 'localhost')
        port = config.get('port', 27017)
        database = config.get('database', 'crawlit')
        username = config.get('username')
        password = config.get('password')
        
        try:
            # Build connection string
            if username and password:
                conn_str = f"mongodb://{username}:{password}@{host}:{port}"
            else:
                conn_str = f"mongodb://{host}:{port}"
            
            # Try to connect with short timeout
            client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=3000)
            # Trigger actual connection
            client.server_info()
            client.close()
            
            return (True, f"[OK] MongoDB is available at {host}:{port}")
        
        except pymongo.errors.ServerSelectionTimeoutError:
            return (False,
                    f"[ERROR] Cannot connect to MongoDB at {host}:{port}\n\n"
                    "MongoDB server is not running or not accessible.\n\n"
                    "Setup instructions:\n"
                    "1. Install MongoDB:\n"
                    "   Ubuntu/Debian: sudo apt-get install mongodb\n"
                    "   macOS: brew install mongodb-community\n"
                    "   Windows: Download from https://www.mongodb.com/try/download/community\n\n"
                    "2. Start MongoDB:\n"
                    "   Linux: sudo systemctl start mongodb\n"
                    "   macOS: brew services start mongodb-community\n"
                    "   Windows: Start via Services app\n\n"
                    "Alternative: Use Docker:\n"
                    "   docker run -d -p 27017:27017 --name mongodb mongo:latest\n")
        
        except pymongo.errors.OperationFailure as e:
            return (False,
                    f"[ERROR] MongoDB authentication failed\n\n"
                    "The username or password is incorrect.\n\n"
                    "To create a user:\n"
                    "  mongo\n"
                    "  use admin\n"
                    "  db.createUser({{\n"
                    "    user: 'crawlit_user',\n"
                    "    pwd: 'your_password',\n"
                    "    roles: [{{ role: 'readWrite', db: 'crawlit' }}]\n"
                    "  }})\n")
        
        except Exception as e:
            return (False, f"[ERROR] Unexpected error checking MongoDB: {e}\n")
    
    def connect(self):
        """Establish MongoDB connection"""
        if self.client is None:
            # Build connection string
            if self.username and self.password:
                conn_str = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}"
            else:
                conn_str = f"mongodb://{self.host}:{self.port}"
            
            self.client = self.pymongo.MongoClient(conn_str, **self.kwargs)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Create indexes
            self.collection.create_index("url")
            self.collection.create_index("crawl_id")
            self.collection.create_index("status_code")
            self.collection.create_index("timestamp")
            
            logger.info(f"Connected to MongoDB: {self.host}:{self.port}/{self.database_name}")
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("MongoDB connection closed")
    
    def save_results(self, results: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Save crawl results to MongoDB"""
        self.connect()
        
        # Create crawl document
        crawl_doc = {
            'start_url': metadata.get('start_url', 'unknown') if metadata else 'unknown',
            'timestamp': datetime.now(),
            'user_agent': metadata.get('user_agent', 'crawlit/1.0') if metadata else 'crawlit/1.0',
            'max_depth': metadata.get('max_depth', 0) if metadata else 0,
            'total_urls': len(results),
            'successful_urls': sum(1 for r in results.values() if r.get('success', False)),
            'failed_urls': sum(1 for r in results.values() if not r.get('success', False)),
            'metadata': metadata or {}
        }
        
        # Insert crawl metadata
        crawl_result = self.db.crawls.insert_one(crawl_doc)
        crawl_id = crawl_result.inserted_id
        
        # Prepare result documents
        documents = []
        for url, result in results.items():
            doc = {
                'crawl_id': crawl_id,
                'url': url,
                'timestamp': datetime.now(),
                **result
            }
            documents.append(doc)
        
        # Bulk insert results
        if documents:
            self.collection.insert_many(documents)
        
        logger.info(f"Saved {len(results)} results to MongoDB (crawl_id: {crawl_id})")
        return str(crawl_id)
    
    def get_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve results from MongoDB"""
        self.connect()
        
        query = filters or {}
        results = list(self.collection.find(query))
        
        # Convert ObjectId to string
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
            if 'crawl_id' in result:
                result['crawl_id'] = str(result['crawl_id'])
        
        logger.info(f"Retrieved {len(results)} results from MongoDB")
        return results
    
    def clear_results(self, filters: Optional[Dict[str, Any]] = None):
        """Clear results from MongoDB"""
        self.connect()
        
        if filters:
            result = self.collection.delete_many(filters)
            logger.info(f"Deleted {result.deleted_count} documents from MongoDB")
        else:
            self.collection.delete_many({})
            self.db.crawls.delete_many({})
            logger.info("Cleared all results from MongoDB")


def get_database_backend(backend_type: str, check_setup: bool = True, **config) -> DatabaseBackend:
    """
    Factory function to get appropriate database backend.
    
    Args:
        backend_type: Type of backend ('sqlite', 'postgresql', 'mongodb')
        check_setup: Whether to check if database is properly set up (default: True)
        **config: Configuration parameters for the backend
        
    Returns:
        DatabaseBackend instance
        
    Raises:
        ValueError: If backend type is unknown
        RuntimeError: If database is not available/properly set up (when check_setup=True)
        
    Example:
        >>> db = get_database_backend('sqlite', database_path='my_crawls.db')
        >>> db = get_database_backend('postgresql', host='localhost', database='crawlit')
        >>> db = get_database_backend('mongodb', host='localhost', database='crawlit')
    """
    backends = {
        'sqlite': SQLiteBackend,
        'postgresql': PostgreSQLBackend,
        'postgres': PostgreSQLBackend,  # Alias
        'psql': PostgreSQLBackend,  # Alias
        'mongodb': MongoDBBackend,
        'mongo': MongoDBBackend,  # Alias
    }
    
    backend_class = backends.get(backend_type.lower())
    if not backend_class:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Supported: {', '.join(set(backends.keys()))}"
        )
    
    # Check if database is available and properly set up
    if check_setup:
        is_available, message = backend_class.check_availability(**config)
        
        if not is_available:
            logger.error(message)
            raise RuntimeError(
                f"Database backend '{backend_type}' is not available or not properly set up.\n\n"
                f"{message}"
            )
        else:
            logger.info(message)
    
    return backend_class(**config)

