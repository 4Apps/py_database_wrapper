import sqlite3
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any, NotRequired, TypedDict, cast

import aiosqlite

from database_wrapper import DatabaseBackend


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    fields = [col[0] for col in cursor.description]
    return dict(zip(fields, row, strict=False))


class SqliteConfig(TypedDict):
    database: str
    timeout: NotRequired[float]
    isolation_level: NotRequired[str | None]
    kwargs: NotRequired[dict[str, Any]]


class SqliteTypedDictCursor(sqlite3.Cursor):
    """
    Type hint wrapper only. At runtime, this is just a sqlite3.Cursor
    that happens to produce dicts because of the row_factory.
    """

    def fetchone(self) -> dict[str, Any] | None:
        return super().fetchone()  # type: ignore

    def fetchall(self) -> list[dict[str, Any]]:
        return super().fetchall()  # type: ignore

    def __iter__(self) -> "SqliteTypedDictCursor":
        return self

    def __next__(self) -> dict[str, Any]:
        return super().__next__()  # type: ignore


class Sqlite(DatabaseBackend):
    """
    SQLite database backend

    :param config: Configuration for SQLite
    :type config: SqliteConfig
    """

    config: SqliteConfig
    connection: sqlite3.Connection
    cursor: SqliteTypedDictCursor

    ##################
    ### Connection ###
    ##################

    def open(self) -> None:
        # Free resources
        if hasattr(self, "connection") and self.connection:
            self.close()

        self.logger.debug("Connecting to DB")

        if "kwargs" not in self.config:
            self.config["kwargs"] = {}

        # Default timeout to 5.0 seconds if not specified
        timeout = self.config.get("timeout", 5.0)

        # sqlite3's standard default is "" (deferred transactions); None would mean
        # autocommit, silently turning commit()/rollback() into no-ops
        isolation_level = self.config.get("isolation_level", "")

        self.connection = sqlite3.connect(
            self.config["database"],
            timeout=timeout,
            isolation_level=isolation_level,
            **self.config["kwargs"],
        )

        # Set row factory to return dicts
        self.connection.row_factory = dict_factory

        # Create cursor
        self.cursor = cast(SqliteTypedDictCursor, self.connection.cursor())

    def ping(self) -> bool:
        try:
            self.cursor.execute("SELECT 1")
            self.cursor.fetchone()
        except Exception as e:
            self.logger.debug(f"Error while pinging the database: {e}")
            return False

        return True

    ############
    ### Data ###
    ############

    def last_insert_id(self) -> int:
        assert self.cursor, "Cursor is not initialized"
        return self.cursor.lastrowid or 0

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


class SqliteTypedDictCursorAsync(aiosqlite.Cursor):
    """
    Type hint wrapper only. At runtime, this is just an aiosqlite.Cursor
    that happens to produce dicts because of the row_factory.
    """

    async def fetchone(self) -> dict[str, Any] | None:  # type: ignore[override]
        return await super().fetchone()  # type: ignore

    async def fetchall(self) -> list[dict[str, Any]]:  # type: ignore[override]
        return await super().fetchall()  # type: ignore


class SqliteConnectionAsync:
    """
    An aiosqlite connection in autocommit mode with psycopg's `transaction()`.
    Outside a transaction every statement commits on its own, as on a pooled
    PostgreSQL connection.
    """

    raw: aiosqlite.Connection
    """ The underlying aiosqlite connection """

    database: str
    """ Database path, as configured """

    def __init__(self, raw: aiosqlite.Connection, database: str) -> None:
        self.raw = raw
        self.database = database
        self._depth = 0

    @property
    def in_transaction(self) -> bool:
        return self.raw.in_transaction

    async def cursor(self) -> SqliteTypedDictCursorAsync:
        return cast(SqliteTypedDictCursorAsync, await self.raw.cursor())

    async def execute(self, statement: str, parameters: Iterable[Any] | None = None) -> SqliteTypedDictCursorAsync:
        return cast(SqliteTypedDictCursorAsync, await self.raw.execute(statement, parameters))

    async def close(self) -> None:
        await self.raw.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """
        BEGIN IMMEDIATE takes the write lock up front: a deferred transaction that reads
        first gets SQLITE_BUSY at its first write, without waiting out the timeout.
        Nested calls are savepoints.
        """
        depth = self._depth
        savepoint = f"sp_{depth}"
        await self.raw.execute("BEGIN IMMEDIATE" if depth == 0 else f"SAVEPOINT {savepoint}")
        self._depth = depth + 1
        try:
            yield
        except BaseException:
            # Some errors make SQLite roll back by itself; a second ROLLBACK would then
            # raise and hide the error that caused it.
            if self.raw.in_transaction:
                if depth == 0:
                    await self.raw.execute("ROLLBACK")
                else:
                    await self.raw.execute(f"ROLLBACK TO {savepoint}")
                    await self.raw.execute(f"RELEASE {savepoint}")
            raise
        else:
            await self.raw.execute("COMMIT" if depth == 0 else f"RELEASE {savepoint}")
        finally:
            self._depth = depth


def is_memory_database(database: str) -> bool:
    return database in ("", ":memory:")


async def connect_async(config: SqliteConfig) -> SqliteConnectionAsync:
    """
    Opens an autocommit connection with dict rows, foreign keys on and WAL.
    `isolation_level` is ignored: transactions come from `transaction()`.
    """
    database = str(config["database"])
    raw = await aiosqlite.connect(
        database,
        isolation_level=None,
        timeout=config.get("timeout", 5.0),
        **config.get("kwargs", {}),
    )
    try:
        raw.row_factory = dict_factory  # type: ignore[assignment]
        # foreign_keys is per connection and off by default. WAL is stored in the file,
        # so after the first connection this is a no-op.
        await raw.execute("PRAGMA foreign_keys = ON")
        if not is_memory_database(database):
            await raw.execute("PRAGMA journal_mode = WAL")
    except BaseException:
        await raw.close()
        raise

    return SqliteConnectionAsync(raw, database)


class SqliteAsync(DatabaseBackend):
    """
    SQLite database async implementation, on aiosqlite.

    Instance is created without actually connecting to the database.
    When you are ready to connect, call await open() method.

    ! Note: Close is not called automatically when class is destroyed.
    ! You need to call it manually in async environment.

    :param config: Configuration for SQLite
    :type config: SqliteConfig
    """

    config: SqliteConfig

    connection: SqliteConnectionAsync | None
    cursor: SqliteTypedDictCursorAsync | None

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

        self.logger.debug("Connecting to DB")
        self.connection = await connect_async(self.config)
        self.cursor = await self.connection.cursor()

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
            assert self.cursor, "Cursor is not initialized"
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
    async def transaction(self, db_conn: SqliteConnectionAsync | None = None) -> AsyncIterator[None]:
        """Transaction context manager"""
        connection = db_conn or self.connection
        assert connection, "Connection is not initialized"
        async with connection.transaction():
            yield

    ############
    ### Data ###
    ############

    def last_insert_id(self) -> int:
        assert self.cursor, "Cursor is not initialized"
        return self.cursor.lastrowid or 0

    def affected_rows(self) -> int:
        assert self.cursor, "Cursor is not initialized"
        return self.cursor.rowcount


class SqliteWithPoolingAsync(DatabaseBackend):
    """
    `async with pool as (connection, cursor)` over SQLite, the same shape as
    PgsqlWithPoolingAsync, so code written against one runs on the other.

    Connections are not reused: opening one is cheap, and a fresh one per context
    means a transaction left open by one user cannot reach the next.

        pool = SqliteWithPoolingAsync(config)
        await pool.open_pool()
        async with pool as (connection, cursor):
            await cursor.execute("SELECT 1")

    :param config: Configuration for SQLite
    :type config: SqliteConfig
    """

    config: SqliteConfig

    def __del__(self) -> None:
        """Nothing to release: connections live only inside their contexts"""

    async def open_pool(self) -> None:
        """Connects once, so a wrong path or an unwritable directory fails here"""
        connection = await connect_async(self.config)
        await connection.close()

    async def close_pool(self) -> None:
        """Nothing is pooled, so nothing to close"""
        self.shutdown_requested.set()

    async def new_connection(self) -> tuple[SqliteConnectionAsync, SqliteTypedDictCursorAsync]:
        self.logger.debug("Opening connection")
        connection = await connect_async(self.config)
        try:
            cursor = await connection.cursor()
        except BaseException:
            await connection.close()
            raise

        return (connection, cursor)

    async def return_connection(self, connection: SqliteConnectionAsync) -> None:
        self.logger.debug("Closing connection")
        await connection.close()

    ###############
    ### Context ###
    ###############

    async def __aenter__(self) -> tuple[SqliteConnectionAsync, SqliteTypedDictCursorAsync]:
        """Context manager"""
        # Kept per context, so concurrent tasks sharing this instance each close their own.
        res = await self.new_connection()
        stack = self.context_connection_async.get() or ()
        self.context_connection_async.set(stack + (res,))
        return res

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Context manager"""
        stack = self.context_connection_async.get() or ()
        if not stack:
            return

        (connection, cursor) = stack[-1]
        self.context_connection_async.set(stack[:-1])
        try:
            await cursor.close()
        finally:
            await self.return_connection(connection)
