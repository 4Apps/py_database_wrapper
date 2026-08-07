"""
database_wrapper_mysql package - MySQL database wrapper

Part of the database_wrapper package
"""

# Copyright 2024 Gints Murāns

import logging

from .connector import Mysql, MysqlConfig, MysqlConnection, MysqlDictCursor, MysqlTypedDictCursor
from .db_wrapper_mysql import DBWrapperMysql

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("database_wrapper_mysql")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)


__all__ = [
    # Wrappers
    DBWrapperMysql,
    # Connectors
    Mysql,
    # Connection and Cursor types
    MysqlConnection,
    MysqlDictCursor,
    MysqlTypedDictCursor,
    # Helpers
    MysqlConfig,
]
