import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, NotRequired, TypedDict, cast
from urllib.parse import quote

from psycopg import AsyncConnection as PgConnectionAsync  # Async
from psycopg import AsyncCursor as PgCursorAsync
from psycopg import AsyncTransaction, Transaction
from psycopg import Connection as PgConnection  # Sync
from psycopg import Cursor as PgCursor
from psycopg.rows import DictRow as PgDictRow
from psycopg.rows import dict_row as PgDictRowFactory
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from database_wrapper import DatabaseBackend

PgConnectionType = PgConnection[PgDictRow]
PgCursorType = PgCursor[PgDictRow]

PgConnectionTypeAsync = PgConnectionAsync[PgDictRow]
PgCursorTypeAsync = PgCursorAsync[PgDictRow]


class PgsqlConfig(TypedDict):
    hostname: str
    port: NotRequired[int]
    username: str
    password: str
    database: str
    ssl: NotRequired[str]
    kwargs: NotRequired[dict[str, Any]]

    # Connection Pooling
    maxconnections: int
    pool_kwargs: NotRequired[dict[str, Any]]


class Pgsql(DatabaseBackend):
    """
    PostgreSQL database implementation.

    Instance is created without actually connecting to the database.
    When you are ready to connect, call open() method.

    Close is called automatically when class is destroyed.

    :param config: Configuration for PostgreSQL
    :type config: PgsqlConfig

    Defaults:
        port = 5432
        ssl = prefer

    """

    config: PgsqlConfig

    connection: PgConnectionType
    cursor: PgCursorType

    ##################
    ### Connection ###
    ##################

    def open(self) -> None:
        # Free resources
        if hasattr(self, "connection") and self.connection:
            self.close()

        # Set defaults
        if "port" not in self.config or not self.config["port"]:
            self.config["port"] = 5432

        if "ssl" not in self.config or not self.config["ssl"]:
            self.config["ssl"] = "prefer"

        if "kwargs" not in self.config or not self.config["kwargs"]:
            self.config["kwargs"] = {}

        if "autocommit" not in self.config["kwargs"]:
            self.config["kwargs"]["autocommit"] = True

        self.logger.debug("Connecting to DB")
        self.connection = cast(
            PgConnectionType,
            PgConnection.connect(
                host=self.config["hostname"],
                port=self.config["port"],
                sslmode=self.config["ssl"],
                user=self.config["username"],
                password=self.config["password"],
                dbname=self.config["database"],
                connect_timeout=self.connection_timeout,
                row_factory=PgDictRowFactory,
                **self.config["kwargs"],
            ),
        )
        self.cursor = self.connection.cursor(row_factory=PgDictRowFactory)

        # Lets do some socket magic
        self.fix_socket_timeouts(self.connection.fileno())

    def ping(self) -> bool:
        try:
            self.cursor.execute("SELECT 1")
            self.cursor.fetchone()
        except Exception as e:
            self.logger.debug(f"Error while pinging the database: {e}")
            return False

        return True

    ####################
    ### Transactions ###
    ####################

    @contextmanager
    def transaction(
        self,
        db_conn: PgConnectionType | None = None,
    ) -> Iterator[Transaction]:
        """Transaction context manager"""
        if db_conn:
            with db_conn.transaction() as trans:
                yield trans
                return

        assert self.connection, "Connection is not initialized"
        with self.connection.transaction() as trans:
            yield trans

    ############
    ### Data ###
    ############

    def affected_rows(self) -> int:
        assert self.cursor, "Cursor is not initialized"

        return self.cursor.rowcount

    def commit(self) -> None:
        """Commit DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Commit DB queries")
        self.connection.commit()

    def rollback(self) -> None:
        """Rollback DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Rollback DB queries")
        self.connection.rollback()


class PgsqlAsync(DatabaseBackend):
    """
    PostgreSQL database async implementation.

    Instance is created without actually connecting to the database.
    When you are ready to connect, call await open() method.

    ! Note: Close is not called automatically when class is destroyed.
    ! You need to call it manually in async environment.

    :param config: Configuration for PostgreSQL
    :type config: PgsqlConfig

    Defaults:
        port = 5432
        ssl = prefer

    """

    config: PgsqlConfig

    connection: PgConnectionTypeAsync
    cursor: PgCursorTypeAsync

    def __del__(self) -> None:
        """Destructor"""

        # Just to be sure as async does not have __del__
        if hasattr(self, "cursor"):
            del self.cursor

        if hasattr(self, "connection"):
            del self.connection

    async def open(self) -> None:
        # Free resources
        if hasattr(self, "connection") and self.connection:
            await self.close()

        # Set defaults
        if "port" not in self.config or not self.config["port"]:
            self.config["port"] = 5432

        if "ssl" not in self.config or not self.config["ssl"]:
            self.config["ssl"] = "prefer"

        if "kwargs" not in self.config or not self.config["kwargs"]:
            self.config["kwargs"] = {}

        if "autocommit" not in self.config["kwargs"]:
            self.config["kwargs"]["autocommit"] = True

        self.logger.debug("Connecting to DB")
        self.connection = await PgConnectionAsync.connect(
            host=self.config["hostname"],
            port=self.config["port"],
            sslmode=self.config["ssl"],
            user=self.config["username"],
            password=self.config["password"],
            dbname=self.config["database"],
            connect_timeout=self.connection_timeout,
            row_factory=PgDictRowFactory,
            **self.config["kwargs"],
        )
        self.cursor = self.connection.cursor(row_factory=PgDictRowFactory)

        # Lets do some socket magic
        self.fix_socket_timeouts(self.connection.fileno())

    async def close(self) -> Any:
        """Close connections"""
        try:
            if hasattr(self, "cursor") and self.cursor:
                self.logger.debug("Closing cursor")
                await self.cursor.close()
        except Exception as e:
            self.logger.debug(f"Error while closing cursor: {e}")
        finally:
            self.cursor = None

        try:
            if hasattr(self, "connection") and self.connection:
                self.logger.debug("Closing connection")
                await self.connection.close()
        except Exception as e:
            self.logger.debug(f"Error while closing connection: {e}")
        finally:
            self.connection = None

    async def ping(self) -> bool:
        try:
            await self.cursor.execute("SELECT 1")
            await self.cursor.fetchone()
        except Exception as e:
            self.logger.debug(f"Error while pinging the database: {e}")
            return False

        return True

    ####################
    ### Transactions ###
    ####################

    @asynccontextmanager
    async def transaction(
        self,
        db_conn: PgConnectionTypeAsync | None = None,
    ) -> AsyncIterator[AsyncTransaction]:
        """Transaction context manager"""
        if db_conn:
            async with db_conn.transaction() as trans:
                yield trans
                return

        assert self.connection, "Connection is not initialized"
        async with self.connection.transaction() as trans:
            yield trans

    ############
    ### Data ###
    ############

    def affected_rows(self) -> int:
        assert self.cursor, "Cursor is not initialized"

        return self.cursor.rowcount

    async def commit(self) -> None:
        """Commit DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Commit DB queries")
        await self.connection.commit()

    async def rollback(self) -> None:
        """Rollback DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Rollback DB queries")
        await self.connection.rollback()


class PgsqlWithPooling(DatabaseBackend):
    """
    PostgreSQL database implementation with connection pooling.

    Instance is created without actually connecting to the database.
    When you are ready to connect, call open_pool() method.

    Then you can use new_connection() to get connection from the pool and
    return_connection() to return it back.
    Or use context manager to get connection and return it back automatically,
    for example:

        pool = PgsqlWithPooling(config)
        pool.open_pool()
        with pool as (connection, cursor):
            cursor.execute("SELECT 1")

    :param config: Configuration for PostgreSQL
    :type config: PgsqlConfig
    :param connection_timeout: Connection timeout
    :type connection_timeout: int
    :param instance_name: Name of the instance
    :type instance_name: str

    Defaults:
        port = 5432
        ssl = prefer
        maxconnections = 5
    """

    config: PgsqlConfig
    """ Configuration """

    pool: ConnectionPool[PgConnectionType]
    """ Connection pool """

    connection: PgConnectionType | None
    """ Connection to database """

    cursor: PgCursorType | None
    """ Cursor to database """

    context_connection: ContextVar[tuple[PgConnectionType, PgCursorType] | None]
    """ Connection used in context manager """

    ########################
    ### Class Life Cycle ###
    ########################

    def __init__(
        self,
        db_config: PgsqlConfig,
        connection_timeout: int = 5,
        instance_name: str = "postgresql_pool",
    ) -> None:
        """
        Main concept here is that in init we do not connect to database,
        so that class instances can be safely made regardless of connection statuss.

        Remember to call open_pool() after creating instance to actually open the pool to the database
        and also close_pool() to close the pool.
        """

        super().__init__(db_config, connection_timeout, instance_name)

        # Set defaults
        if "port" not in self.config or not self.config["port"]:
            self.config["port"] = 5432

        if "ssl" not in self.config or not self.config["ssl"]:
            self.config["ssl"] = "prefer"

        if "kwargs" not in self.config or not self.config["kwargs"]:
            self.config["kwargs"] = {}

        if "autocommit" not in self.config["kwargs"]:
            self.config["kwargs"]["autocommit"] = True

        # Connection pooling defaults
        if "maxconnections" not in self.config or not self.config["maxconnections"]:
            self.config["maxconnections"] = 5

        if "pool_kwargs" not in self.config or not self.config["pool_kwargs"]:
            self.config["pool_kwargs"] = {}

        conn_str = (
            f"postgresql://{quote(self.config['username'])}:{quote(self.config['password'])}"
            f"@{self.config['hostname']}:{self.config['port']}"
            f"/{quote(self.config['database'])}?connect_timeout={self.connection_timeout}"
            f"&application_name={quote(self.name)}"
            f"&sslmode={self.config['ssl']}"
        )
        self.pool = ConnectionPool(
            conn_str,
            open=False,
            min_size=2,
            max_size=self.config["maxconnections"],
            max_lifetime=20 * 60,
            max_idle=400,
            timeout=self.connection_timeout,
            reconnect_timeout=0,
            num_workers=4,
            connection_class=PgConnectionType,
            kwargs=self.config["kwargs"],
            **self.config["pool_kwargs"],
        )

    ##################
    ### Connection ###
    ##################

    def open_pool(self) -> None:
        self.pool.open(wait=True, timeout=self.connection_timeout)

    def close_pool(self) -> None:
        """Close Pool"""

        if self.shutdown_requested.is_set():
            return
        self.shutdown_requested.set()

        # Close pool
        self.logger.debug("Closing connection pool")
        self.close()
        if hasattr(self, "pool") and self.pool.closed is False:
            self.pool.close()

    def open(self) -> None:
        """Get connection from the pool and keep it in the class"""
        if self.connection:
            self.close()

        # Create new connection
        res = self.new_connection()
        if not res:
            raise ConnectionError("Failed to get a connection from the pool")

        (self.connection, self.cursor) = res

    def close(self) -> None:
        """Close connection by returning it to the pool"""
        try:
            if self.cursor:
                self.logger.debug("Closing cursor")
                self.cursor.close()
        except Exception as e:
            self.logger.debug(f"Error while closing cursor: {e}")
        finally:
            self.cursor = None

        if self.connection:
            connection = self.connection
            self.connection = None
            try:
                self.return_connection(connection)
            except Exception as e:
                self.logger.debug(f"Error while returning connection to the pool: {e}")

    def new_connection(
        self,
    ) -> tuple[PgConnectionType, PgCursorType] | None:
        assert self.pool, "Pool is not initialized"

        # Log
        self.logger.debug("Getting connection from the pool")

        # Get connection from the pool
        tries = 0
        while not self.shutdown_requested.is_set():
            connection = None
            try:
                connection = self.pool.getconn(timeout=self.connection_timeout)
                cursor = connection.cursor(row_factory=PgDictRowFactory)

                # Lets do some socket magic
                self.fix_socket_timeouts(connection.fileno())

                with connection.transaction():
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

                return (connection, cursor)

            except Exception as e:
                if connection:
                    connection.close()
                    self.pool.putconn(connection)

                self.logger.error(f"Error while getting connection from the pool: {e}")
                self.shutdown_requested.wait(self.slow_down_timeout)
                tries += 1
                if tries >= 3:
                    break
                continue

        return None

    def return_connection(self, connection: PgConnectionType) -> None:
        """Return connection to the pool"""
        assert self.pool, "Pool is not initialized"

        # Log
        self.logger.debug("Putting connection back to the pool")

        # Put connection back to the pool
        self.pool.putconn(connection)

        # Debug
        self.logger.debug(self.pool.get_stats())

    ###############
    ### Context ###
    ###############

    def __enter__(
        self,
    ) -> tuple[PgConnectionType | None, PgCursorType | None]:
        """Context manager"""

        # Lets set the context var so that it is set even if we fail to get connection
        self.context_connection.set(None)

        res = self.new_connection()
        if res:
            self.context_connection.set(res)
            return res

        return (
            None,
            None,
        )

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Context manager"""

        test_data = self.context_connection.get()
        if test_data:
            self.return_connection(test_data[0])

        # Reset context
        self.context_connection.set(None)

    ####################
    ### Transactions ###
    ####################

    @contextmanager
    def transaction(
        self,
        db_conn: PgConnectionType | None = None,
    ) -> Iterator[Transaction]:
        """Transaction context manager"""
        if db_conn:
            with db_conn.transaction() as trans:
                yield trans
                return

        assert self.connection, "Connection is not initialized"
        with self.connection.transaction() as trans:
            yield trans

    ############
    ### Data ###
    ############

    def affected_rows(self) -> int:
        assert self.cursor, "Cursor is not initialized"

        return self.cursor.rowcount

    def commit(self) -> None:
        """Commit DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Commit DB queries")
        self.connection.commit()

    def rollback(self) -> None:
        """Rollback DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Rollback DB queries")
        self.connection.rollback()


class PgsqlWithPoolingAsync(DatabaseBackend):
    """
    PostgreSQL database implementation with async connection pooling.

    Instance is created without actually connecting to the database.
    When you are ready to connect, call await open_pool() method.

    Then you can use new_connection() to get connection from the pool and
    return_connection() to return it back.

    Or use context manager to get connection and return it back automatically,
    for example:

        pool = PgsqlWithPoolingAsync(config)
        await pool.open_pool()
        async with pool as (connection, cursor):
            await cursor.execute("SELECT 1")


    ! Note: Close is not called automatically when class is destroyed.
    ! You need to call `await close_pool()` manually in async environment.

    :param config: Configuration for PostgreSQL
    :type config: PgsqlConfig
    :param connection_timeout: Connection timeout
    :type connection_timeout: int
    :param instance_name: Name of the instance
    :type instance_name: str

    Defaults:
        port = 5432
        ssl = prefer
        maxconnections = 5
    """

    config: PgsqlConfig
    """ Configuration """

    pool_async: AsyncConnectionPool[PgConnectionTypeAsync]
    """ Connection pool """

    connection: PgConnectionTypeAsync | None
    """ Connection to database """

    cursor: PgCursorTypeAsync | None
    """ Cursor to database """

    context_connection_async: ContextVar[tuple[PgConnectionTypeAsync, PgCursorTypeAsync] | None]
    """ Connection used in async context manager """

    ########################
    ### Class Life Cycle ###
    ########################

    def __init__(
        self,
        db_config: PgsqlConfig,
        connection_timeout: int = 5,
        instance_name: str = "async_postgresql",
    ) -> None:
        """
        Main concept here is that in init we do not connect to database,
        so that class instances can be safely made regardless of connection statuss.

        Remember to call await open_pool() after creating instance to actually open the pool to the database
        and also await close_pool() to close the pool.
        """

        super().__init__(db_config, connection_timeout, instance_name)

        # Set defaults
        if "port" not in self.config or not self.config["port"]:
            self.config["port"] = 5432

        if "ssl" not in self.config or not self.config["ssl"]:
            self.config["ssl"] = "prefer"

        if "kwargs" not in self.config or not self.config["kwargs"]:
            self.config["kwargs"] = {}

        if "autocommit" not in self.config["kwargs"]:
            self.config["kwargs"]["autocommit"] = True

        # Connection pooling defaults
        if "maxconnections" not in self.config or not self.config["maxconnections"]:
            self.config["maxconnections"] = 5

        if "pool_kwargs" not in self.config or not self.config["pool_kwargs"]:
            self.config["pool_kwargs"] = {}

        conn_str = (
            f"postgresql://{quote(self.config['username'])}:{quote(self.config['password'])}"
            f"@{self.config['hostname']}:{self.config['port']}"
            f"/{quote(self.config['database'])}?connect_timeout={self.connection_timeout}"
            f"&application_name={quote(self.name)}"
            f"&sslmode={self.config['ssl']}"
        )
        self.pool_async = AsyncConnectionPool(
            conn_str,
            open=False,
            min_size=2,
            max_size=self.config["maxconnections"],
            max_lifetime=20 * 60,
            max_idle=400,
            timeout=self.connection_timeout,
            reconnect_timeout=0,
            num_workers=4,
            connection_class=PgConnectionTypeAsync,
            kwargs=self.config["kwargs"],
            **self.config["pool_kwargs"],
        )

    def __del__(self) -> None:
        """Destructor"""
        if hasattr(self, "cursor"):
            del self.cursor

        if hasattr(self, "connection"):
            del self.connection

        if hasattr(self, "pool_async"):
            del self.pool_async

    ##################
    ### Connection ###
    ##################

    async def open_pool(self) -> None:
        await self.pool_async.open(wait=True, timeout=self.connection_timeout)

    async def close_pool(self) -> None:
        """Close Pool"""

        if self.shutdown_requested.is_set():
            return
        self.shutdown_requested.set()

        # Close async pool
        self.logger.debug("Closing connection pool")
        await self.close()
        if hasattr(self, "pool_async") and self.pool_async.closed is False:
            await self.pool_async.close()

    async def open(self) -> None:
        """Get connection from the pool and keep it in the class"""
        if self.connection:
            await self.close()

        # Create new connection
        res = await self.new_connection()
        if not res:
            raise ConnectionError("Failed to get a connection from the pool")

        (self.connection, self.cursor) = res

    async def close(self) -> None:
        """Close connection by returning it to the pool"""
        try:
            if self.cursor:
                self.logger.debug("Closing cursor")
                await self.cursor.close()
        except Exception as e:
            self.logger.debug(f"Error while closing cursor: {e}")
        finally:
            self.cursor = None

        if self.connection:
            connection = self.connection
            self.connection = None
            try:
                await self.return_connection(connection)
            except Exception as e:
                self.logger.debug(f"Error while returning connection to the pool: {e}")

    async def new_connection(
        self,
    ) -> tuple[PgConnectionTypeAsync, PgCursorTypeAsync] | None:
        assert self.pool_async, "Async pool is not initialized"

        # Log
        self.logger.debug("Getting connection from the pool")

        # Get connection from the pool
        tries = 0
        while not self.shutdown_requested.is_set():
            connection = None
            try:
                connection = await self.pool_async.getconn(timeout=self.connection_timeout)
                cursor = connection.cursor(row_factory=PgDictRowFactory)

                # Lets do some socket magic
                self.fix_socket_timeouts(connection.fileno())

                async with connection.transaction():
                    await cursor.execute("SELECT 1")
                    await cursor.fetchone()

                return (connection, cursor)

            except Exception as e:
                if connection:
                    await connection.close()
                    await self.pool_async.putconn(connection)

                self.logger.error(f"Error while getting connection from the pool: {e}")
                # Event.wait() would block the whole event loop; the loop condition
                # re-checks shutdown_requested after the sleep
                await asyncio.sleep(self.slow_down_timeout)
                tries += 1
                if tries >= 3:
                    break
                continue

        return None

    async def return_connection(self, connection: PgConnectionTypeAsync) -> None:
        """Return connection to the pool"""
        assert self.pool_async, "Async pool is not initialized"

        # Log
        self.logger.debug("Putting connection back to the pool")

        # Put connection back to the pool
        await self.pool_async.putconn(connection)

        # Debug
        self.logger.debug(self.pool_async.get_stats())

    ###############
    ### Context ###
    ###############

    async def __aenter__(
        self,
    ) -> tuple[PgConnectionTypeAsync | None, PgCursorTypeAsync | None]:
        """Context manager"""

        # Lets set the context var so that it is set even if we fail to get connection
        self.context_connection_async.set(None)

        res = await self.new_connection()
        if res:
            self.context_connection_async.set(res)
            return res

        return (
            None,
            None,
        )

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Context manager"""

        test_data = self.context_connection_async.get()
        if test_data:
            await self.return_connection(test_data[0])

        # Reset context
        self.context_connection_async.set(None)

    ####################
    ### Transactions ###
    ####################

    @asynccontextmanager
    async def transaction(
        self,
        db_conn: PgConnectionTypeAsync | None = None,
    ) -> AsyncIterator[AsyncTransaction]:
        """Transaction context manager"""
        if db_conn:
            async with db_conn.transaction() as trans:
                yield trans
                return

        assert self.connection, "Connection is not initialized"
        async with self.connection.transaction() as trans:
            yield trans

    ############
    ### Data ###
    ############

    def affected_rows(self) -> int:
        assert self.cursor, "Cursor is not initialized"

        return self.cursor.rowcount

    async def commit(self) -> None:
        """Commit DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Commit DB queries")
        await self.connection.commit()

    async def rollback(self) -> None:
        """Rollback DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Rollback DB queries")
        await self.connection.rollback()
