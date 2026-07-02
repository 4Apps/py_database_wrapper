import logging
from typing import Any

from database_wrapper import DBWrapper

from .connector import MysqlTypedDictCursor


class DBWrapperMysql(DBWrapper):
    """Wrapper for MySQL database"""

    db_cursor: MysqlTypedDictCursor | None
    """ MySQL cursor object """

    insert_returning = False
    """ MySQL has no INSERT ... RETURNING (MariaDB only); use lastrowid instead """

    #######################
    ### Class lifecycle ###
    #######################

    # Meta methods
    # We are overriding the __init__ method for the type hinting
    def __init__(
        self,
        db_cursor: MysqlTypedDictCursor | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initializes a new instance of the DBWrapper class.

        Args:
            db_cursor (MysqlTypedDictCursor): The MySQL database cursor object.
            logger (logging.Logger, optional): The logger object. Defaults to None.
        """
        super().__init__(db_cursor, logger)

    ###############
    ### Setters ###
    ###############

    def set_db_cursor(self, db_cursor: MysqlTypedDictCursor | None) -> None:
        """
        Updates the database cursor object.

        Args:
            db_cursor (MysqlTypedDictCursor): The new database cursor object.
        """
        super().set_db_cursor(db_cursor)

    ######################
    ### Helper methods ###
    ######################

    def log_query(
        self,
        cursor: MysqlTypedDictCursor,
        query: Any,
        params: tuple[Any, ...],
    ) -> None:
        """
        Logs the given query and parameters.

        Args:
            cursor (MysqlTypedDictCursor): The cursor used to execute the query.
            query (Any): The query to log.
            params (tuple[Any, ...]): The parameters to log.
        """
        query_string = cursor.mogrify(query, params)
        logging.getLogger().debug(f"Query: {query_string}")

    #####################
    ### Query methods ###
    #####################

    def limit_query(self, offset: int = 0, limit: int = 100) -> str | None:
        if limit == 0:
            return None
        return f"LIMIT {int(offset)},{int(limit)}"
