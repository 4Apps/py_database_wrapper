# Changelog

One line per change, newest release first. **Breaking:** marks anything a downstream project
must act on. All six packages (`database_wrapper` and its `_pgsql`, `_mysql`, `_mssql`,
`_sqlite`, `_redis` adapters) are released together under one version, so one changelog covers
them; an entry names its adapter. Versions missing between entries were never published;
releases before v0.2.31 are only in the git history.

## Unreleased

- Versioning: the patch counts releases within a minor (0.4.0, 0.4.1, ...) instead of all commits
- Dependencies: SQLite requires `aiosqlite >= 0.17.0`

## v0.3.147 - 2026-10-14

- SQLite: async support on aiosqlite - `SqliteAsync`, `SqliteWithPoolingAsync`, `DBWrapperSqliteAsync`

## v0.3.146 - 2026-08-07

- **Breaking:** license changed from GPL-3.0 to MIT for all six packages; each wheel ships its `LICENSE`
- Repository moved to `github.com/4Apps/py_database_wrapper`

## v0.2.38 - 2026-07-21

- `RawSQL` marks a filter or order-by key as a trusted SQL expression, skipping identifier validation
- PostgreSQL: the pool checks connections on checkout and refills broken ones instead of wedging
- PostgreSQL, Redis: nested `with` / `async with` on one instance each get and release their own connection

## v0.2.36 - 2026-07-02

- **Breaking:** identifiers in filters, order-by and insert/update columns must be plain names; anything else raises `ValueError`
- **Breaking:** introspector-generated models use `schema_name`/`table_name` instead of `schemaName`/`tableName`
- **Breaking:** `json_encoder` writes dates and datetimes with `isoformat()`, keeping offset and microseconds
- **Breaking:** MySQL defaults to `utf8mb4` / `utf8mb4_general_ci` instead of `utf8` / `utf8_general_ci`
- **Breaking:** SQLite defaults to `isolation_level=""`, so `commit()`/`rollback()` take effect instead of autocommit
- **Breaking:** Redis requires `redis >= 8.0`
- An id of `0` is valid in `get_one`, `get_filtered`, `update` and `delete`
- `insert()` returns the id on MySQL and SQLite (`lastrowid`) and on MSSQL (`OUTPUT INSERTED`)
- Empty `$in` / `$not_in` lists no longer produce invalid SQL; MSSQL paging without an order works
- `None` serializes to SQL NULL; naive datetimes get the configured `timezone` on deserialize
- PostgreSQL: pooled `open()` raises `ConnectionError` instead of continuing without a connection
- PostgreSQL, Redis: async retries no longer block the event loop; Redis gets `close()` and honours `instant_retries`
- The core package no longer needs `psycopg` installed

## v0.2.33 - 2026-04-10

- MSSQL: the descriptor snapshot behind the leak fix ignores descriptors closed while listing

## v0.2.32 - 2026-04-10

- MSSQL: connection state is checked correctly before reuse

## v0.2.31 - 2026-04-08

- MSSQL: `close()` force-closes file descriptors pymssql/FreeTDS leaks on a dead connection
