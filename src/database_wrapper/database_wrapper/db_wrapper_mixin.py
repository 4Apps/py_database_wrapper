import logging
from typing import Any, cast

from .common import DataModelType, NoParam, OrderByItem


class DBWrapperMixin:
    """
    Mixin class for the DBWrapper class to provide methods that can be
    used by both sync and async versions of the DBWrapper class.

    :property db_cursor: Database cursor object.
    :property logger: Logger object
    """

    ###########################
    ### Instance properties ###
    ###########################

    db_cursor: Any
    """
    Database cursor object.
    """

    # logger
    logger: Any
    """Logger object"""

    #######################
    ### Class lifecycle ###
    #######################

    # Meta methods
    def __init__(
        self,
        db_cursor: Any = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initializes a new instance of the DBWrapper class.

        Args:
            db (DatabaseBackend): The DatabaseBackend object.
            logger (logging.Logger, optional): The logger object. Defaults to None.
        """
        self.db_cursor = db_cursor

        if logger is None:
            logger_name = f"{__name__}.{self.__class__.__name__}"
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logger

    def __del__(self) -> None:
        """
        Deallocates the instance of the DBWrapper class.
        """
        self.logger.debug("Dealloc")

        # Force remove instances so that there are no circular references
        if hasattr(self, "db_cursor") and self.db_cursor:
            del self.db_cursor

    ###############
    ### Setters ###
    ###############

    def set_db_cursor(self, db_cursor: Any) -> None:
        """
        Updates the database cursor object.

        Args:
            db_cursor (Any): The new database cursor object.
        """

        if db_cursor is None:
            if hasattr(self, "db_cursor"):
                del self.db_cursor
            return

        self.db_cursor = db_cursor

    ######################
    ### Helper methods ###
    ######################

    def make_identifier(self, schema: str | None, name: str) -> Any:
        """
        Creates a SQL identifier object from the given name.

        Args:
            schema (str | None): The schema to create the identifier from.
            name (str): The name to create the identifier from.

        Returns:
            str: The created SQL identifier object.
        """
        if schema:
            return f"{schema}.{name}"

        return name

    def log_query(self, cursor: Any, query: Any, params: tuple[Any, ...]) -> None:
        """
        Logs the given query and parameters.

        Args:
            cursor (Any): The database cursor.
            query (Any): The query to log.
            params (tuple[Any, ...]): The parameters to log.
        """
        logging.getLogger().debug(f"Query: {query} with params: {params}")

    def turn_data_into_model(
        self,
        empty_data_class: type[DataModelType],
        db_data: dict[str, Any],
    ) -> DataModelType:
        """
        Turns the given data into a data model.
        By default we are pretty sure that there is no factory in the cursor,
        So we need to create a new instance of the data model and fill it with data

        Args:
            empty_data_class (DataModelType): The data model to use.
            db_data (dict[str, Any]): The data to turn into a model.

        Returns:
            DataModelType: The data model filled with data.
        """

        result = empty_data_class()
        result.fill_data_from_dict(db_data)
        result.raw_data = db_data

        # If the id key is not "id", we set it manually so that its filled correctly
        if result.id_key != "id":
            result.id = db_data.get(result.id_key, None)

        return result

    #####################
    ### Query methods ###
    #####################

    def filter_query(self, schema_name: str | None, table_name: str) -> Any:
        """
        Creates a SQL query to filter data from the given table.

        Args:
            schema_name (str | None): The name of the schema to filter data from.
            table_name (str): The name of the table to filter data from.

        Returns:
            Any: The created SQL query object.
        """
        full_table_name = self.make_identifier(schema_name, table_name)
        return f"SELECT * FROM {full_table_name}"

    def order_query(self, order_by: OrderByItem | None = None) -> Any | None:
        """
        Creates a SQL query to order the results by the given column.

        Args:
            order_by (OrderByItem | None, optional): The column to order the results by. Defaults to None.

        Returns:
            Any: The created SQL query object.
        """
        if order_by is None:
            return None

        order_list = [f"{item[0]} {item[1] if len(item) > 1 and item[1] is not None else 'ASC'}" for item in order_by]
        return "ORDER BY {}".format(", ".join(order_list))

    def limit_query(self, offset: int = 0, limit: int = 100) -> Any | None:
        """
        Creates a SQL query to limit the number of results returned.

        Args:
            offset (int, optional): The number of results to skip. Defaults to 0.
            limit (int, optional): The maximum number of results to return. Defaults to 100.

        Returns:
            Any: The created SQL query object.
        """
        if limit == 0:
            return None

        return f"LIMIT {limit} OFFSET {offset}"

    def format_filter(self, key: str, filter: Any) -> tuple[Any, ...]:
        if type(filter) is dict:
            if "$contains" in filter:
                return (
                    f"{key} LIKE %s",
                    f"%{filter['$contains']}%",
                )
            elif "$starts_with" in filter:
                return (f"{key} LIKE %s", f"{filter['$starts_with']}%")
            elif "$ends_with" in filter:
                return (f"{key} LIKE %s", f"%{filter['$ends_with']}")
            elif "$min" in filter and "$max" not in filter:
                return (f"{key} >= %s", filter["$min"])
            elif "$max" in filter and "$min" not in filter:
                return (f"{key} <= %s", filter["$max"])
            elif "$min" in filter and "$max" in filter:
                return (f"{key} BETWEEN %s AND %s", filter["$min"], filter["$max"])
            elif "$in" in filter:
                in_filter_1: list[Any] = cast(list[Any], filter["$in"])
                return (f"{key} IN (%s)" % ",".join(["%s"] * len(in_filter_1)),) + tuple(in_filter_1)
            elif "$not_in" in filter:
                in_filter_2: list[Any] = cast(list[Any], filter["$not_in"])
                return (f"{key} NOT IN (%s)" % ",".join(["%s"] * len(in_filter_2)),) + tuple(in_filter_2)
            elif "$not" in filter:
                return (f"{key} != %s", filter["$not"])

            elif "$gt" in filter:
                return (f"{key} > %s", filter["$gt"])
            elif "$gte" in filter:
                return (f"{key} >= %s", filter["$gte"])
            elif "$lt" in filter:
                return (f"{key} < %s", filter["$lt"])
            elif "$lte" in filter:
                return (f"{key} <= %s", filter["$lte"])
            elif "$is_null" in filter:
                return (f"{key} IS NULL",)
            elif "$is_not_null" in filter:
                return (f"{key} IS NOT NULL",)

            raise NotImplementedError("Filter type not supported")
        elif isinstance(filter, (bool, str, int, float)):
            return (f"{key} = %s", filter)
        else:
            raise NotImplementedError(f"Filter type not supported: {key} = {type(filter)}")

    def create_filter(self, filter: dict[str, Any] | None) -> tuple[Any, tuple[Any, ...]]:
        if filter is None or len(filter) == 0:
            return ("", tuple())

        raw = [self.format_filter(key, filter[key]) for key in filter]
        _query = " AND ".join([tup[0] for tup in raw])
        _query = f"WHERE {_query}"
        _params = tuple([val for tup in raw for val in tup[1:] if val is not NoParam])

        return (_query, _params)

    def _format_filter_query(
        self,
        query: Any,
        q_filter: Any,
        order: Any,
        limit: Any,
    ) -> Any:
        if q_filter is None:
            q_filter = ""
        if order is None:
            order = ""
        if limit is None:
            limit = ""
        return f"{query} {q_filter} {order} {limit}"

    def _format_insert_query(
        self,
        table_identifier: Any,
        store_data: dict[str, Any],
        return_key: Any,
    ) -> Any:
        keys = store_data.keys()
        values = list(store_data.values())

        columns = ", ".join(keys)
        values_placeholder = ", ".join(["%s"] * len(values))
        return f"INSERT INTO {table_identifier} ({columns}) VALUES ({values_placeholder}) RETURNING {return_key}"

    def _format_update_query(
        self,
        table_identifier: Any,
        update_key: Any,
        update_data: dict[str, Any],
    ) -> Any:
        keys = update_data.keys()
        set_clause = ", ".join(f"{key} = %s" for key in keys)
        return f"UPDATE {table_identifier} SET {set_clause} WHERE {update_key} = %s"

    def _format_delete_query(
        self,
        table_identifier: Any,
        delete_key: Any,
    ) -> Any:
        return f"DELETE FROM {table_identifier} WHERE {delete_key} = %s"
