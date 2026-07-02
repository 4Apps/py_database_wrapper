import logging
import socket
from collections.abc import Coroutine
from contextvars import ContextVar
from threading import Event
from typing import Any


class DatabaseBackend:
    config: Any
    """ Database configuration """

    connection_timeout: int
    """ Connection timeout """

    name: str
    """ Instance name """

    # TODO: This should be made to increase exponentially
    slow_down_timeout: int
    """ How long to wait before trying to reconnect """

    pool: Any
    """ Connection pool """

    pool_async: Any
    """ Async connection pool """

    connection: Any
    """ Connection to database """

    cursor: Any
    """ Cursor to database """

    context_connection: ContextVar[Any | None]
    """ Connection used in context manager """

    context_connection_async: ContextVar[Any | None]
    """ Connection used in async context manager """

    logger_name: str
    """ Logger name """

    logger: logging.Logger
    """ Logger """

    shutdown_requested: Event
    """
    Event to signal shutdown
    Used to stop database pool from creating new connections
    """

    ########################
    ### Class Life Cycle ###
    ########################

    def __init__(
        self,
        db_config: Any,
        connection_timeout: int = 5,
        instance_name: str = "database_backend",
        slow_down_timeout: int = 5,
    ) -> None:
        """
        Main concept here is that in init we do not connect to database,
        so that class instances can be safely made regardless of connection statuss.

        Remember to call open() or open_pool() before using this class.
        Close will be called automatically when class is destroyed.

        Contexts are not implemented here, but in child classes should be used
        by using connection pooling.

        Async classes should be called manually and should override __del__ method,
        if not upon destroying the class, an error will be raised that method was not awaited.
        """

        self.config = db_config
        self.connection_timeout = connection_timeout
        self.name = instance_name
        self.slow_down_timeout = slow_down_timeout

        self.logger_name = f"{__name__}.{self.__class__.__name__}.{self.name}"
        self.logger = logging.getLogger(self.logger_name)

        self.pool = None
        self.pool_async = None

        self.connection = None
        self.cursor = None
        self.shutdown_requested = Event()
        self.context_connection = ContextVar(f"db_connection_{self.name}", default=None)
        self.context_connection_async = ContextVar(
            f"db_connection_{self.name}_async",
            default=None,
        )

    def __del__(self) -> None:
        """What to do when class is destroyed"""
        self.logger.debug("Dealloc")

        # Clean up connections
        self.close()
        self.close_pool()

        # Clean just in case
        if hasattr(self, "connection"):
            del self.connection

        if hasattr(self, "cursor"):
            del self.cursor

        if hasattr(self, "pool"):
            del self.pool

        if hasattr(self, "pool_async"):
            del self.pool_async

    ###############
    ### Context ###
    ###############

    def __enter__(self) -> tuple[Any, Any]:
        """Context manager"""
        raise Exception("Not implemented")

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Context manager"""
        raise Exception("Not implemented")

    async def __aenter__(self) -> tuple[Any, Any]:
        """Context manager"""
        raise Exception("Not implemented")

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Context manager"""
        raise Exception("Not implemented")

    ##################
    ### Connection ###
    ##################

    def open_pool(self) -> Any:
        """Open connection pool"""
        ...

    def close_pool(self) -> Any:
        """Close connection pool"""
        ...

    def open(self) -> Any:
        """Connect to database"""
        ...

    def close(self) -> Any:
        """Close connections"""
        try:
            if self.cursor:
                self.logger.debug("Closing cursor")
                self.cursor.close()
        except Exception as e:
            self.logger.debug(f"Error while closing cursor: {e}")
        finally:
            self.cursor = None

        try:
            if self.connection:
                self.logger.debug("Closing connection")
                self.connection.close()
        except Exception as e:
            self.logger.debug(f"Error while closing connection: {e}")
        finally:
            self.connection = None

    def new_connection(self) -> Any:
        """
        Create new connection

        Used for async context manager and async connection creation

        Returns:
            tuple[Any, Any] | None: Connection and cursor
        """
        raise Exception("Not implemented")

    def return_connection(self, connection: Any) -> Any:
        """
        Return connection to pool

        Used for async context manager and async connections return.
        For example to return connection to a pool.

        Args:
            connection (Any): Connection to return to pool
        """
        raise Exception("Not implemented")

    def ping(self) -> bool | Coroutine[Any, Any, bool]:
        """
        Check if connection is alive.
        This should be done in try except block and bool should be returned.

        Returns:
            bool: Connection status
        """
        raise Exception("Not implemented")

    def has_connection(self) -> bool:
        """
        Check if connection is alive/set.

        Returns:
            bool: Connection status
        """
        return self.connection is not None

    def has_cursor(self) -> bool:
        """
        Check if cursor is alive/set.

        Returns:
            bool: Cursor status
        """
        return self.cursor is not None

    ###############
    ### Helpers ###
    ###############

    def fix_socket_timeouts(self, fd: Any) -> None:
        # Lets do some socket magic
        s = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        # Enable sending of keep-alive messages
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Time the connection needs to remain idle before start sending
        # keepalive probes
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, self.connection_timeout)
        # Time between individual keepalive probes
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
        # The maximum number of keepalive probes should send before dropping
        # the connection
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        # To set timeout for an RTO you must set TCP_USER_TIMEOUT timeout
        # (in milliseconds) for socket.
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_USER_TIMEOUT, self.connection_timeout * 1000)

    ####################
    ### Transactions ###
    ####################

    def begin_transaction(self) -> Any:
        """Start transaction"""
        raise Exception("Not implemented")

    def commit_transaction(self) -> Any:
        """Commit transaction"""
        raise Exception("Not implemented")

    def rollback_transaction(self) -> Any:
        """Rollback transaction"""
        raise Exception("Not implemented")

    # @contextmanager
    def transaction(self, db_conn: Any = None) -> Any:
        """
        Transaction context manager

        ! When overriding this method, remember to use context manager.
        ! Its not defined here, so that it can be used in both sync and async methods.
        """
        raise Exception("Not implemented")

    ############
    ### Data ###
    ############

    def last_insert_id(self) -> int:
        """Get last inserted row id generated by auto increment"""
        raise Exception("Not implemented")

    def affected_rows(self) -> int:
        """Get affected rows count"""
        raise Exception("Not implemented")

    def commit(self) -> Any:
        """Commit DB queries"""
        raise Exception("Not implemented")

    def rollback(self) -> Any:
        """Rollback DB queries"""
        raise Exception("Not implemented")
