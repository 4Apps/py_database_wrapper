"""
database_wrapper_sqlite package - Sqlite database wrapper

Part of the database_wrapper package
"""

# Copyright 2024 Gints Murāns

import logging

# from .db_wrapper_sqlite import DBWrapperSqlite
from .connector import Sqlite, SqliteConfig, SqliteTypedDictCursor
from .db_wrapper_sqlite import DBWrapperSqlite

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("database_wrapper_sqlite")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)


__all__ = [
    # Wrappers
    DBWrapperSqlite,
    # Connectors
    Sqlite,
    # Connection and Cursor types
    SqliteTypedDictCursor,
    # Helpers
    SqliteConfig,
]
