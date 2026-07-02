import psycopg
from psycopg.rows import dict_row

from database_wrapper import ColumnMetaIntrospector, DBIntrospector

from .type_mapping import map_db_type


class PostgresIntrospector(DBIntrospector):
    conn: psycopg.Connection

    def map_db_type(self, db_type: str) -> str:
        return map_db_type(db_type)

    def get_table_columns(self, schema: str, table: str) -> list[ColumnMetaIntrospector]:
        """
        Returns ColumnMeta including enum labels if column type is enum.
        """
        q = """
        WITH cols AS (
          SELECT
            a.attname                             AS col_name,
            a.attnotnull                          AS not_null,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS fmt_type,
            t.typname                             AS typname,
            t.typcategory                         AS typcategory,
            a.atttypid                            AS typid,
            pg_catalog.pg_get_expr(ad.adbin, ad.adrelid) AS default_expr
          FROM pg_attribute a
          JOIN pg_class c       ON c.oid = a.attrelid
          JOIN pg_namespace n   ON n.oid = c.relnamespace
          JOIN pg_type t        ON t.oid = a.atttypid
          LEFT JOIN pg_attrdef ad
               ON ad.adrelid = a.attrelid
              AND ad.adnum   = a.attnum
          WHERE n.nspname = %s
            AND c.relname = %s
            AND a.attnum > 0
            AND NOT a.attisdropped
          ORDER BY a.attnum
        )
        SELECT
          cols.col_name,
          cols.typname,
          cols.fmt_type,
          NOT not_null AS is_nullable,
          default_expr,
          CASE WHEN typcategory = 'E' THEN (
            SELECT array_agg(e.enumlabel ORDER BY e.enumsortorder)
            FROM pg_enum e
            WHERE e.enumtypid = cols.typid
          )
          ELSE NULL
          END AS enum_labels
        FROM cols;
        """
        # Explicit row factory - the default psycopg cursor returns tuples
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(q, (schema, table))
            rows = cur.fetchall()

        out: list[ColumnMetaIntrospector] = []
        for row in rows:
            out.append(
                ColumnMetaIntrospector(
                    col_name=row["col_name"],
                    db_type=row["typname"],
                    is_nullable=bool(row["is_nullable"]),
                    has_default=(row["default_expr"] is not None),
                    default_expr=row["default_expr"],
                    enum_labels=list(row["enum_labels"]) if row["enum_labels"] else None,
                )
            )

        return out
