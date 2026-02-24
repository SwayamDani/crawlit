#!/usr/bin/env python3
"""
pool.py - Connection pooling for improved performance

Provides connection pooling for databases and HTTP requests.
"""

import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Callable
from queue import Queue, Empty, Full
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ConnectionPool(ABC):
    """Abstract base class for connection pools"""
    
    def __init__(self, min_connections: int = 1, max_connections: int = 10,
                 max_idle_time: float = 300.0, connection_timeout: float = 30.0):
        """
        Initialize connection pool.
        
        Args:
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            max_idle_time: Maximum time a connection can be idle (seconds)
            connection_timeout: Timeout for acquiring a connection (seconds)
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.connection_timeout = connection_timeout
        
        self._pool: Queue = Queue(maxsize=max_connections)
        self._active_connections = 0
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'created': 0,
            'reused': 0,
            'closed': 0,
            'timeouts': 0,
            'errors': 0
        }
        
        # Initialize minimum connections
        self._initialize_pool()
    
    @abstractmethod
    def _create_connection(self) -> Any:
        """Create a new connection"""
        pass
    
    @abstractmethod
    def _close_connection(self, conn: Any):
        """Close a connection"""
        pass
    
    @abstractmethod
    def _is_connection_valid(self, conn: Any) -> bool:
        """Check if a connection is still valid"""
        pass
    
    def _initialize_pool(self):
        """Initialize pool with minimum connections"""
        for _ in range(self.min_connections):
            try:
                conn = self._create_connection()
                self._pool.put((conn, time.time()))
                with self._lock:
                    self._active_connections += 1
                    self.stats['created'] += 1
            except Exception as e:
                logger.error(f"Error creating initial connection: {e}")
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).
        
        Usage:
            with pool.get_connection() as conn:
                # Use connection
                pass
        """
        conn = None
        try:
            conn = self.acquire()
            yield conn
        finally:
            if conn is not None:
                self.release(conn)
    
    def acquire(self) -> Any:
        """
        Acquire a connection from the pool.
        
        Returns:
            Connection object
            
        Raises:
            TimeoutError: If connection cannot be acquired within timeout
        """
        start_time = time.time()
        
        while True:
            # Try to get from pool
            try:
                conn, last_used = self._pool.get(timeout=0.1)
                
                # Check if connection is still valid
                if self._is_connection_valid(conn):
                    # Check idle time
                    idle_time = time.time() - last_used
                    if idle_time < self.max_idle_time:
                        with self._lock:
                            self.stats['reused'] += 1
                        logger.debug(f"Reused connection (idle: {idle_time:.1f}s)")
                        return conn
                    else:
                        logger.debug(f"Connection idle too long ({idle_time:.1f}s), creating new one")
                        self._close_connection(conn)
                        with self._lock:
                            self._active_connections -= 1
                            self.stats['closed'] += 1
                else:
                    logger.debug("Connection invalid, creating new one")
                    self._close_connection(conn)
                    with self._lock:
                        self._active_connections -= 1
                        self.stats['closed'] += 1
                
            except Empty:
                pass
            
            # Check if we can create a new connection
            with self._lock:
                if self._active_connections < self.max_connections:
                    try:
                        conn = self._create_connection()
                        self._active_connections += 1
                        self.stats['created'] += 1
                        logger.debug(f"Created new connection (total: {self._active_connections})")
                        return conn
                    except Exception as e:
                        self.stats['errors'] += 1
                        logger.error(f"Error creating connection: {e}")
                        raise
            
            # Check timeout
            if (time.time() - start_time) > self.connection_timeout:
                with self._lock:
                    self.stats['timeouts'] += 1
                raise TimeoutError(
                    f"Could not acquire connection within {self.connection_timeout}s "
                    f"(active: {self._active_connections}/{self.max_connections})"
                )
            
            # Wait a bit before retrying
            time.sleep(0.1)
    
    def release(self, conn: Any):
        """
        Release a connection back to the pool.
        
        Args:
            conn: Connection to release
        """
        if conn is None:
            return
        
        try:
            # Check if connection is still valid
            if self._is_connection_valid(conn):
                # Try to put back in pool
                try:
                    self._pool.put((conn, time.time()), block=False)
                    logger.debug("Connection returned to pool")
                except Full:
                    # Pool is full, close connection
                    self._close_connection(conn)
                    with self._lock:
                        self._active_connections -= 1
                        self.stats['closed'] += 1
                    logger.debug("Pool full, connection closed")
            else:
                # Connection invalid, close it
                self._close_connection(conn)
                with self._lock:
                    self._active_connections -= 1
                    self.stats['closed'] += 1
                logger.debug("Invalid connection closed")
        except Exception as e:
            logger.error(f"Error releasing connection: {e}")
            self.stats['errors'] += 1
    
    def close_all(self):
        """Close all connections in the pool"""
        logger.info("Closing all connections in pool...")
        
        while True:
            try:
                conn, _ = self._pool.get(block=False)
                self._close_connection(conn)
                with self._lock:
                    self._active_connections -= 1
                    self.stats['closed'] += 1
            except Empty:
                break
        
        logger.info(f"All connections closed. Stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                **self.stats,
                'active_connections': self._active_connections,
                'pool_size': self._pool.qsize(),
                'max_connections': self.max_connections
            }


class DatabaseConnectionPool(ConnectionPool):
    """
    Connection pool for database connections.
    
    Supports any database backend with a connect/close interface.
    """
    
    def __init__(self, db_backend: str, db_config: Dict[str, Any],
                 min_connections: int = 1, max_connections: int = 10,
                 **kwargs):
        """
        Initialize database connection pool.
        
        Args:
            db_backend: Database backend type ('sqlite', 'postgresql', 'mongodb')
            db_config: Database configuration
            min_connections: Minimum connections
            max_connections: Maximum connections
            **kwargs: Additional pool parameters
        """
        from ..utils.database import get_database_backend
        
        self.db_backend = db_backend
        self.db_config = db_config
        self._get_db_backend = get_database_backend
        
        super().__init__(min_connections, max_connections, **kwargs)
        
        logger.info(f"Database connection pool initialized ({db_backend})")
    
    def _create_connection(self) -> Any:
        """Create a new database connection"""
        # Don't check setup for pooled connections (already checked once)
        return self._get_db_backend(self.db_backend, check_setup=False, **self.db_config)
    
    def _close_connection(self, conn: Any):
        """Close a database connection"""
        try:
            conn.disconnect()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    def _is_connection_valid(self, conn: Any) -> bool:
        """Check if database connection is still valid"""
        try:
            # Different backends have different ways to check validity
            if hasattr(conn, 'conn'):
                # SQLite/PostgreSQL
                if conn.conn is None:
                    return False
                # Try a simple operation
                if hasattr(conn, 'cursor') and conn.cursor:
                    return True
            elif hasattr(conn, 'client'):
                # MongoDB
                if conn.client is None:
                    return False
                # Try to ping
                conn.client.admin.command('ping')
            return True
        except Exception:
            return False


class HTTPConnectionPool(ConnectionPool):
    """
    Connection pool for HTTP requests.
    
    Reuses requests.Session objects for better performance.
    """
    
    def __init__(self, min_connections: int = 1, max_connections: int = 10,
                 session_config: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """
        Initialize HTTP connection pool.
        
        Args:
            min_connections: Minimum connections
            max_connections: Maximum connections
            session_config: Configuration for requests.Session
            **kwargs: Additional pool parameters
        """
        self.session_config = session_config or {}
        
        super().__init__(min_connections, max_connections, **kwargs)
        
        logger.info("HTTP connection pool initialized")
    
    def _create_connection(self) -> Any:
        """Create a new HTTP session"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=self.session_config.get('max_retries', 3),
            backoff_factor=self.session_config.get('backoff_factor', 1),
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.session_config.get('pool_connections', 10),
            pool_maxsize=self.session_config.get('pool_maxsize', 10)
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        if 'headers' in self.session_config:
            session.headers.update(self.session_config['headers'])
        
        # Set timeout
        if 'timeout' in self.session_config:
            session.timeout = self.session_config['timeout']
        
        return session
    
    def _close_connection(self, conn: Any):
        """Close HTTP session"""
        try:
            conn.close()
        except Exception as e:
            logger.error(f"Error closing HTTP session: {e}")
    
    def _is_connection_valid(self, conn: Any) -> bool:
        """Check if HTTP session is still valid"""
        # Sessions don't really "expire" but we can check if they exist
        return conn is not None and hasattr(conn, 'get')


class AsyncConnectionPool(ABC):
    """
    Async connection pool base class.
    
    Similar to ConnectionPool but for async operations.
    """
    
    def __init__(self, min_connections: int = 1, max_connections: int = 10,
                 max_idle_time: float = 300.0, connection_timeout: float = 30.0):
        """
        Initialize async connection pool.
        
        Args:
            min_connections: Minimum number of connections
            max_connections: Maximum number of connections
            max_idle_time: Maximum idle time (seconds)
            connection_timeout: Connection acquisition timeout (seconds)
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.connection_timeout = connection_timeout
        
        import asyncio
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self._active_connections = 0
        self._lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            'created': 0,
            'reused': 0,
            'closed': 0,
            'timeouts': 0,
            'errors': 0
        }
    
    @abstractmethod
    async def _create_connection(self) -> Any:
        """Create a new connection"""
        pass
    
    @abstractmethod
    async def _close_connection(self, conn: Any):
        """Close a connection"""
        pass
    
    @abstractmethod
    async def _is_connection_valid(self, conn: Any) -> bool:
        """Check if connection is valid"""
        pass
    
    async def initialize(self):
        """Initialize the pool with minimum connections"""
        for _ in range(self.min_connections):
            try:
                conn = await self._create_connection()
                await self._pool.put((conn, time.time()))
                async with self._lock:
                    self._active_connections += 1
                    self.stats['created'] += 1
            except Exception as e:
                logger.error(f"Error creating initial async connection: {e}")
    
    async def acquire(self) -> Any:
        """Acquire a connection from the pool"""
        import asyncio
        
        start_time = time.time()
        
        while True:
            # Try to get from pool
            try:
                conn, last_used = await asyncio.wait_for(
                    self._pool.get(),
                    timeout=0.1
                )
                
                # Check validity
                if await self._is_connection_valid(conn):
                    idle_time = time.time() - last_used
                    if idle_time < self.max_idle_time:
                        async with self._lock:
                            self.stats['reused'] += 1
                        return conn
                    else:
                        await self._close_connection(conn)
                        async with self._lock:
                            self._active_connections -= 1
                            self.stats['closed'] += 1
                else:
                    await self._close_connection(conn)
                    async with self._lock:
                        self._active_connections -= 1
                        self.stats['closed'] += 1
                        
            except asyncio.TimeoutError:
                pass
            
            # Try to create new connection
            async with self._lock:
                if self._active_connections < self.max_connections:
                    try:
                        conn = await self._create_connection()
                        self._active_connections += 1
                        self.stats['created'] += 1
                        return conn
                    except Exception as e:
                        self.stats['errors'] += 1
                        logger.error(f"Error creating async connection: {e}")
                        raise
            
            # Check timeout
            if (time.time() - start_time) > self.connection_timeout:
                async with self._lock:
                    self.stats['timeouts'] += 1
                raise TimeoutError(f"Could not acquire connection within {self.connection_timeout}s")
            
            await asyncio.sleep(0.1)
    
    async def release(self, conn: Any):
        """Release connection back to pool"""
        if conn is None:
            return
        
        try:
            if await self._is_connection_valid(conn):
                try:
                    self._pool.put_nowait((conn, time.time()))
                except:
                    await self._close_connection(conn)
                    async with self._lock:
                        self._active_connections -= 1
                        self.stats['closed'] += 1
            else:
                await self._close_connection(conn)
                async with self._lock:
                    self._active_connections -= 1
                    self.stats['closed'] += 1
        except Exception as e:
            logger.error(f"Error releasing async connection: {e}")
            self.stats['errors'] += 1
    
    async def close_all(self):
        """Close all connections"""
        logger.info("Closing all async connections...")
        
        while not self._pool.empty():
            try:
                conn, _ = self._pool.get_nowait()
                await self._close_connection(conn)
                async with self._lock:
                    self._active_connections -= 1
                    self.stats['closed'] += 1
            except:
                break
        
        logger.info(f"All async connections closed. Stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            **self.stats,
            'active_connections': self._active_connections,
            'pool_size': self._pool.qsize(),
            'max_connections': self.max_connections
        }




