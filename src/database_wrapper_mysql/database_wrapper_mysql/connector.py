from typing import Any, NotRequired, TypedDict

from MySQLdb.connections import Connection as MysqlConnection
from MySQLdb.cursors import DictCursor as MysqlDictCursor

from database_wrapper import DatabaseBackend


class MysqlConfig(TypedDict):
    hostname: str
    port: NotRequired[int]
    username: str
    password: str
    database: str
    charset: NotRequired[str]
    collation: NotRequired[str]
    kwargs: NotRequired[dict[str, Any]]


class MysqlTypedDictCursor(MysqlDictCursor):
    def fetchone(self) -> dict[str, Any] | None:
        return super().fetchone()

    def fetchall(self) -> tuple[dict[str, Any], ...]:
        return super().fetchall()


class Mysql(DatabaseBackend):
    """
    MySQL database backend

    :param config: Configuration for MySQL
    :type config: MysqlConfig

    Defaults:
        port = 0 - See comment below
        charset = utf8mb4
        collation = utf8mb4_general_ci
    """

    config: MysqlConfig

    connection: MysqlConnection
    cursor: MysqlTypedDictCursor

    ##################
    ### Connection ###
    ##################

    def open(self) -> None:
        # Free resources
        if hasattr(self, "connection") and self.connection:
            self.close()

        # Set defaults
        if "port" not in self.config or not self.config["port"]:
            self.config["port"] = 0

        # utf8 is an alias for utf8mb3, which cannot store 4-byte characters (e.g. emoji)
        if "charset" not in self.config or not self.config["charset"]:
            self.config["charset"] = "utf8mb4"

        if "collation" not in self.config or not self.config["collation"]:
            self.config["collation"] = "utf8mb4_general_ci"

        if "kwargs" not in self.config or not self.config["kwargs"]:
            self.config["kwargs"] = {}

        self.logger.debug("Connecting to DB")
        self.connection = MysqlConnection(
            host=self.config["hostname"],
            user=self.config["username"],
            passwd=self.config["password"],
            db=self.config["database"],
            # By default, when port is not specified, Python library passes 0 to
            # MySQL C API function mysql_real_connect as port number.
            #
            # At https://dev.mysql.com/doc/c-api/8.0/en/mysql-real-connect.html
            # is written "If port is not 0, the value is used as the port number
            # for the TCP/IP connection."
            #
            # We keep the same behavior not to break services that have port
            # number unspecified.
            port=self.config.get("port", 0),
            connect_timeout=self.connection_timeout,
            use_unicode=True,
            charset=self.config["charset"],
            collation=self.config["collation"],
            cursorclass=MysqlTypedDictCursor,
            **self.config["kwargs"],
        )
        # TODO: Typings issue
        self.cursor = self.connection.cursor(MysqlTypedDictCursor)

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
        return self.cursor.lastrowid

    def affected_rows(self) -> int:
        assert self.cursor, "Cursor is not initialized"
        return self.cursor.rowcount

    def commit(self) -> None:
        """Commit DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Commit DB queries..")
        # TODO: Typings issue
        self.connection.commit()

    def rollback(self) -> None:
        """Rollback DB queries"""
        assert self.connection, "Connection is not initialized"

        self.logger.debug("Rollback DB queries..")
        # TODO: Typings issue
        self.connection.rollback()
