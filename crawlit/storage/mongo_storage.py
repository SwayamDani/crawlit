#!/usr/bin/env python3
"""
MongoDB storage backend - compatibility module.
Re-exports MongoDBBackend as MongoStorage.
"""

from crawlit.utils.database import MongoDBBackend as MongoStorage

__all__ = ['MongoStorage']
