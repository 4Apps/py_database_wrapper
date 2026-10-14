"""
database_wrapper_sqlite package - Sqlite database wrapper

Part of the database_wrapper package
"""

# Copyright 2024 Gints Murāns

import logging

# from .db_wrapper_sqlite import DBWrapperSqlite
from .connector import (
    Sqlite,
    SqliteAsync,
    SqliteConfig,
    SqliteConnectionAsync,
    SqliteTypedDictCursor,
    SqliteTypedDictCursorAsync,
    SqliteWithPoolingAsync,
)
from .db_wrapper_sqlite import DBWrapperSqlite
from .db_wrapper_sqlite_async import DBWrapperSqliteAsync

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("database_wrapper_sqlite")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)


__all__ = [
    # Wrappers
    DBWrapperSqlite,
    DBWrapperSqliteAsync,
    # Connectors
    Sqlite,
    SqliteAsync,
    SqliteWithPoolingAsync,
    # Connection and Cursor types
    SqliteConnectionAsync,
    SqliteTypedDictCursor,
    SqliteTypedDictCursorAsync,
    # Helpers
    SqliteConfig,
]
