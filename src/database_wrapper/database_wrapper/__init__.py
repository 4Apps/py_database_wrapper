"""
database_wrapper package - Base for database wrappers
"""

# Copyright 2024 Gints Murans

import logging

from . import utils
from .abc import ConnectionABC, ConnectionAsyncABC, CursorABC, CursorAsyncABC
from .common import DataModelType, NoParam, OrderByItem, RawSQL
from .db_backend import DatabaseBackend
from .db_data_model import DBDataModel, DBDefaultsDataModel, MetadataDict
from .db_introspector import ColumnMetaIntrospector, DBIntrospector
from .db_wrapper import DBWrapper
from .db_wrapper_async import DBWrapperAsync
from .serialization import SerializeType
from .utils.dataclass_addons import ignore_unknown_kwargs

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("database_wrapper")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)


# Expose the classes
__all__ = [
    # Database backend
    "DatabaseBackend",
    # Data models
    "DBDataModel",
    "DBDefaultsDataModel",
    # Wrappers
    "DBWrapper",
    "DBWrapperAsync",
    # Helpers
    "MetadataDict",
    "DataModelType",
    "OrderByItem",
    "NoParam",
    "RawSQL",
    "utils",
    "SerializeType",
    "ignore_unknown_kwargs",
    "ColumnMetaIntrospector",
    "DBIntrospector",
    # Abstract classes
    "ConnectionABC",
    "CursorABC",
    "CursorAsyncABC",
    "ConnectionAsyncABC",
]
