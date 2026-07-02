from typing import Any

from psycopg import sql

from database_wrapper import NoParam, OrderByItem


class DBWrapperPgsqlMixin:
    """
    Mixin for providing methods that can be used by both sync and async versions of the DBWrapperPgsql class.
    """

    ######################
    ### Helper methods ###
    ######################

    def make_identifier(self, schema: str | None, name: str) -> sql.Identifier | str:
        """
        Creates a SQL identifier object from the given name.

        Args:
            name (str): The name to create the identifier from.

        Returns:
            sql.Identifier: The created SQL identifier object.
        """
        if schema:
            return sql.Identifier(schema, name)

        return sql.Identifier(name)

    #####################
    ### Query methods ###
    #####################

    def filter_query(
        self,
        schema_name: str | None,
        table_name: str,
    ) -> sql.SQL | sql.Composed | str:
        """
        Creates a SQL query to filter data from the given table.

        Args:
            schema_name (str): The name of the schema to filter data from.
            table_name (str): The name of the table to filter data from.

        Returns:
            sql.SQL | sql.Composed: The created SQL query object.
        """
        return sql.SQL("SELECT * FROM {table}").format(
            table=self.make_identifier(schema_name, table_name),
        )

    def order_query(
        self,
        order_by: OrderByItem | None = None,
    ) -> sql.SQL | sql.Composed | None:
        """
        Creates a SQL query to order the results by the given column.

        Args:
            order_by (OrderByItem | None, optional): The column to order the results by. Defaults to None.

        Returns:
            Any: The created SQL query object.

        TODO: Fix return type
        """
        if order_by is None:
            return None

        order_list = [
            sql.SQL("{} {}").format(
                sql.Identifier(item[0]),
                # order_direction (from DBWrapperMixin via MRO) validates against ASC/DESC
                sql.SQL(self.order_direction(item)),  # type: ignore[attr-defined]
            )
            for item in order_by
        ]
        return sql.SQL("ORDER BY ") + sql.SQL(", ").join(order_list)

    def limit_query(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> sql.Composed | sql.SQL | None:
        if limit == 0:
            return None

        return sql.SQL("LIMIT {} OFFSET {}").format(limit, offset)

    def format_filter(self, key: str, filter: Any) -> tuple[Any, ...]:
        # TODO: For now we assume that we have that method from DBWrapperMixin
        # TODO: Its 5am and I am tired, I will fix this later
        return super().format_filter(key, filter)

    def create_filter(self, filter: dict[str, Any] | None) -> tuple[sql.Composed | None, tuple[Any, ...]]:
        if filter is None or len(filter) == 0:
            return (None, tuple())

        raw = [self.format_filter(key, filter[key]) for key in filter]

        _query_items = sql.SQL(" AND ").join([sql.SQL(tup[0]) for tup in raw])
        _query = sql.SQL("WHERE {query_items}").format(query_items=_query_items)
        _params = tuple([val for tup in raw for val in tup[1:] if val is not NoParam])

        return (_query, _params)

    def _format_filter_query(
        self,
        query: sql.SQL | sql.Composed | str,
        q_filter: sql.SQL | sql.Composed | None,
        order: sql.SQL | sql.Composed | None,
        limit: sql.SQL | sql.Composed | None,
    ) -> sql.Composed:
        if isinstance(query, str):
            query = sql.SQL(query)

        query_parts: list[sql.Composable] = [query]
        if q_filter is not None:
            # if isinstance(q_filter, str):
            #     q_filter = sql.SQL(q_filter)
            query_parts.append(q_filter)
        if order is not None:
            query_parts.append(order)
        if limit is not None:
            query_parts.append(limit)

        return sql.SQL(" ").join(query_parts)

    def _format_insert_query(
        self,
        table_identifier: sql.Identifier | str,
        store_data: dict[str, Any],
        return_key: sql.Identifier | str,
    ) -> sql.Composed:
        keys = store_data.keys()
        values = list(store_data.values())

        return sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values}) RETURNING {id_key}").format(
            table=table_identifier,
            columns=sql.SQL(", ").join(map(sql.Identifier, keys)),
            values=sql.SQL(", ").join(sql.Placeholder() * len(values)),
            id_key=return_key,
        )

    def _format_update_query(
        self,
        table_identifier: sql.Identifier | str,
        update_key: sql.Identifier | str,
        update_data: dict[str, Any],
    ) -> sql.Composed:
        keys = update_data.keys()
        set_clause = sql.SQL(", ").join(sql.Identifier(key) + sql.SQL(" = %s") for key in keys)
        return sql.SQL("UPDATE {table} SET {set_clause} WHERE {id_key} = %s").format(
            table=table_identifier,
            set_clause=set_clause,
            id_key=update_key,
        )

    def _format_delete_query(
        self,
        table_identifier: sql.Identifier | str,
        delete_key: sql.Identifier | str,
    ) -> sql.Composed:
        return sql.SQL("DELETE FROM {table} WHERE {id_key} = %s").format(
            table=table_identifier,
            id_key=delete_key,
        )
