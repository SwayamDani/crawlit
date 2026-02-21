#!/usr/bin/env python3
"""
PostgreSQL storage backend - compatibility module.
Re-exports PostgreSQLBackend as PostgresStorage.
"""

from crawlit.utils.database import PostgreSQLBackend as PostgresStorage

__all__ = ['PostgresStorage']
