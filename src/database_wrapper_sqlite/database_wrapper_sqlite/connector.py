import sqlite3
from typing import Any, NotRequired, TypedDict, cast

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
