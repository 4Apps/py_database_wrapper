import logging
from typing import Any

from database_wrapper import DBWrapper

from .connector import SqliteTypedDictCursor


class DBWrapperSqlite(DBWrapper):
    """Wrapper for SQLite database"""

    db_cursor: SqliteTypedDictCursor | None
    """ SQLite cursor object """

    placeholder = "?"
    """ sqlite3 uses qmark paramstyle """

    insert_returning = False
    """ RETURNING requires SQLite >= 3.35; use lastrowid instead """

    #######################
    ### Class lifecycle ###
    #######################

    # Meta methods
    # We are overriding the __init__ method for the type hinting
    def __init__(
        self,
        db_cursor: SqliteTypedDictCursor | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initializes a new instance of the DBWrapper class.

        Args:
            db_cursor (SqliteTypedDictCursor): The SQLite database cursor object.
            logger (logging.Logger, optional): The logger object. Defaults to None.
        """
        super().__init__(db_cursor, logger)

    ###############
    ### Setters ###
    ###############

    def set_db_cursor(self, db_cursor: SqliteTypedDictCursor | None) -> None:
        """
        Updates the database cursor object.

        Args:
            db_cursor (SqliteTypedDictCursor): The new database cursor object.
        """
        super().set_db_cursor(db_cursor)

    ######################
    ### Helper methods ###
    ######################

    def log_query(
        self,
        cursor: SqliteTypedDictCursor,
        query: Any,
        params: tuple[Any, ...],
    ) -> None:
        """
        Logs the given query and parameters.

        Args:
            cursor (SqliteTypedDictCursor): The cursor used to execute the query.
            query (Any): The query to log.
            params (tuple[Any, ...]): The parameters to log.
        """
        # sqlite3 does not support mogrify, so we just log query and params
        logging.getLogger().debug(f"Query: {query} with params: {params}")

    #####################
    ### Query methods ###
    #####################

    def limit_query(self, offset: int = 0, limit: int = 100) -> str | None:
        if limit == 0:
            return None
        return f"LIMIT {int(limit)} OFFSET {int(offset)}"
