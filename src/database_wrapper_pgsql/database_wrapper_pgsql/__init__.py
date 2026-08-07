"""
database_wrapper_pgsql package - PostgreSQL database wrapper

Part of the database_wrapper package
"""

# Copyright 2024 Gints Murāns

import logging

from .connector import (
    # Basics
    PgConnection,
    PgConnectionType,
    PgConnectionTypeAsync,
    PgCursor,
    PgCursorType,
    PgCursorTypeAsync,
    PgDictRow,
    Pgsql,
    PgsqlAsync,
    PgsqlConfig,
    PgsqlWithPooling,
    PgsqlWithPoolingAsync,
)
from .db_wrapper_pgsql import DBWrapperPgsql
from .db_wrapper_pgsql_async import DBWrapperPgsqlAsync
from .pg_introspector import PostgresIntrospector

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("database_wrapper_pgsql")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)


__all__ = [
    # Wrappers
    DBWrapperPgsql,
    DBWrapperPgsqlAsync,
    # Connectors
    Pgsql,
    PgsqlAsync,
    PgsqlWithPooling,
    PgsqlWithPoolingAsync,
    # Connection and Cursor types
    PgConnection,
    PgConnectionType,
    PgConnectionTypeAsync,
    PgCursor,
    PgCursorType,
    PgCursorTypeAsync,
    PgDictRow,
    # Helpers
    PgsqlConfig,
    PostgresIntrospector,
]
