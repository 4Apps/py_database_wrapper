"""
database_wrapper_mssql package - Mssql database wrapper

Part of the database_wrapper package
"""

# Copyright 2024 Gints Murāns

import logging

from .connector import Mssql, MssqlConfig, MssqlConnection, MssqlCursor, MssqlTypedDictCursor
from .db_wrapper_mssql import DBWrapperMssql
from .mssql_introspector import MssqlIntrospector

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("database_wrapper_mssql")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)


__all__ = [
    # Wrappers
    DBWrapperMssql,
    # Connectors
    Mssql,
    # Connection and Cursor types
    MssqlConnection,
    MssqlCursor,
    MssqlTypedDictCursor,
    # Helpers
    MssqlConfig,
    MssqlIntrospector,
]
