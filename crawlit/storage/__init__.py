#!/usr/bin/env python3
"""
Storage module for crawlit.
Provides database backend compatibility aliases.
"""

from crawlit.utils.database import PostgreSQLBackend, MongoDBBackend, SQLiteBackend


# Compatibility aliases for test imports
class PostgresStorage(PostgreSQLBackend):
    """Alias for PostgreSQLBackend for backward compatibility."""
    pass


class MongoStorage(MongoDBBackend):
    """Alias for MongoDBBackend for backward compatibility."""
    pass


__all__ = [
    'PostgresStorage',
    'MongoStorage',
    'PostgreSQLBackend',
    'MongoDBBackend',
    'SQLiteBackend',
]
