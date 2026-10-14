import logging
from typing import Any

from database_wrapper import DBWrapperAsync

from .connector import SqliteTypedDictCursorAsync


class DBWrapperSqliteAsync(DBWrapperAsync):
    """
    Async database wrapper for SQLite

    This is meant to be used in async environments.
    """

    db_cursor: SqliteTypedDictCursorAsync | None
    """ Async SQLite cursor object """

    placeholder = "?"
    """ sqlite3 uses qmark paramstyle """

    insert_returning = False
    """ The id comes back from lastrowid """

    #######################
    ### Class lifecycle ###
    #######################

    # Meta methods
    # We are overriding the __init__ method for the type hinting
    def __init__(
        self,
        db_cursor: SqliteTypedDictCursorAsync | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initializes a new instance of the DBWrapper class.

        Args:
            db_cursor (SqliteTypedDictCursorAsync): The async SQLite cursor object.
            logger (logging.Logger, optional): The logger object. Defaults to None.
        """
        super().__init__(db_cursor, logger)

    ###############
    ### Setters ###
    ###############

    def set_db_cursor(self, db_cursor: SqliteTypedDictCursorAsync | None) -> None:
        """
        Updates the database cursor object.

        Args:
            db_cursor (SqliteTypedDictCursorAsync): The new database cursor object.
        """
        super().set_db_cursor(db_cursor)

    ######################
    ### Helper methods ###
    ######################

    def log_query(
        self,
        cursor: SqliteTypedDictCursorAsync,
        query: Any,
        params: tuple[Any, ...],
    ) -> None:
        """
        Logs the given query and parameters.

        Args:
            cursor (SqliteTypedDictCursorAsync): The cursor used to execute the query.
            query (Any): The query to log.
            params (tuple[Any, ...]): The parameters to log.
        """
        # sqlite3 does not support mogrify, so we just log query and params
        logging.getLogger().debug(f"Query: {query} with params: {params}")
