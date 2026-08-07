"""
database_wrapper_redis package - Redis database wrapper

Part of the database_wrapper package
"""

# Copyright 2024 Gints Murāns

import logging

from .connector import (
    # Connection and Cursor types
    RedisClient,
    RedisClientAsync,
    # Basics
    RedisConfig,
    RedisConnection,
    RedisConnectionAsync,
    # Connectors
    RedisDb,
    RedisDbAsync,
    RedisDbWithPool,
    RedisDbWithPoolAsync,
    RedisDefaultConfig,
)

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("database_wrapper_redis")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)


__all__ = [
    # Connectors
    RedisDb,
    RedisDbAsync,
    RedisDbWithPool,
    RedisDbWithPoolAsync,
    # Connection and Cursor types
    RedisClient,
    RedisClientAsync,
    RedisConnection,
    RedisConnectionAsync,
    # Helpers
    RedisConfig,
    RedisDefaultConfig,
]
