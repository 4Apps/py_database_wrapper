# database_wrapper_sqlite

_Part of the `database_wrapper` package._

This python package is a database wrapper for [sqlite](https://www.sqlite.org/) database.

## Installation

```bash
pip install database_wrapper[sqlite]
```

## Usage

```python
from database_wrapper_sqlite import Sqlite, DBWrapperSqlite

db = Sqlite({"database": "my_database.db"})
db.open()
db_wrapper = DBWrapperSqlite(db_cursor=db.cursor)

res = db_wrapper.get_by_key(MyModel(), "id", 3005)
if res:
    print(f"get_by_key: {res.to_dict()}")

db.close()
```

### Async

`SqliteWithPoolingAsync` has the shape of `PgsqlWithPoolingAsync`: `async with pool as
(connection, cursor)`, so code written against one runs on the other as long as its SQL does.
It opens a fresh aiosqlite connection per context rather than reusing them.

```python
from database_wrapper_sqlite import SqliteWithPoolingAsync, DBWrapperSqliteAsync

pool = SqliteWithPoolingAsync({"database": "/srv/app/data/app.sqlite3"})
await pool.open_pool()

async with pool as (connection, cursor):
    db_wrapper = DBWrapperSqliteAsync(cursor)

    async with connection.transaction():
        await db_wrapper.insert(MyModel(name="x"))

    res = db_wrapper.get_all(MyModel(), custom_query="SELECT * FROM my_table WHERE active = 1")
    async for record in res:
        print(record.to_dict())
```

Async connections differ from the sync `Sqlite` on purpose:

- Autocommit: every statement commits on its own outside `connection.transaction()`, as on a
  pooled PostgreSQL connection. `isolation_level` is ignored.
- `transaction()` starts with `BEGIN IMMEDIATE`, taking the write lock up front, so a
  transaction that reads before it writes cannot fail with `SQLITE_BUSY` at the write.
  Nested calls are savepoints.
- `PRAGMA foreign_keys = ON` on every connection, and WAL for a file database.
- Rows are dicts; `DBWrapperSqliteAsync` uses `?` placeholders and reads inserted ids from
  `lastrowid`.

`SqliteAsync` is the single-connection form, like `PgsqlAsync`.
