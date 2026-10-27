# py_database_wrapper

A Different Approach to Database Wrappers in Python

This project aims to create an alternative to the commonly used ORMs in Python, focusing on raw queries, models that represent returned results, and a straightforward base to make simple queries genuinely simple.

## Installation

```bash
pip install database_wrapper[pgsql] # for postgres
pip install database_wrapper[mysql] # for mysql
pip install database_wrapper[mssql] # for mssql
pip install database_wrapper[sqlite] # TODO: for sqlite
pip install database_wrapper[redis] # for redis
```

All six packages share one version; what changed in each release is in [CHANGELOG.md](CHANGELOG.md).

## Usage

General usage is the same for all databases. The only difference is the import statement and the class name.

#### Random notes:

* For now all databases are sync, except for PostgreSQL which can use both sync and async.
    * PgSQL connector for sync
    * PgSQLWithPoolingAsync for async
* We are assuming that there is no point of using tuple cursors, so behind the scenes all databases are using dict cursors.
* Wrapper methods that return multiple results are async generators.
* Wrapper methods that return a single result are still async methods, but returns without generator.


#### Specific database wrappers:

* [database_wrapper_pgsql](src/database_wrapper_pgsql)
* [database_wrapper_mysql](src/database_wrapper_mysql)
* [database_wrapper_mssql](src/database_wrapper_mssql)
* [database_wrapper_sqlite](src/database_wrapper_sqlite)
* [database_wrapper_redis](src/database_wrapper_redis)

## Data Models

The project uses `dataclasses` to define data models. The base class for all models is `DBDataModel`.

### DBDataModel

`DBDataModel` provides the foundation for database-backed objects, including methods for:
* Serialization/Deserialization to and from dictionaries and JSON.
* Handling database fields via metadata.
* `store_data()` and `update_data()` methods to filter fields for INSERT and UPDATE queries.

### Default Field Models

To simplify common patterns, two classes with predefined fields are available:

#### DBDefaultsDataModel

Includes standard fields for tracking state and history:
* `created_at`: Timestamp (readonly).
* `updated_at`: Timestamp (automatically updated on `update_data()`).
* `disabled_at`: Timestamp (stored and updated by default).
* `deleted_at`: Timestamp (stored and updated by default).
* `enabled`: Boolean status (deprecated).
* `deleted`: Boolean status (deprecated).

> [!NOTE]
> It is recommended to use the `disabled_at` and `deleted_at` timestamps to determine state instead of the deprecated `enabled` and `deleted` boolean flags.

##### Selective Columns

Subclasses of `DBDefaultsDataModel` can specify which of the 4 default columns should be present using the `_defaults_config` attribute:

```python
@dataclass
class MyModel(DBDefaultsDataModel):
    table_name: str = "my_table"
    # Only include created_at and deleted_at
    _defaults_config = ["created_at", "deleted_at"]
```

Supported column names: `created_at`, `updated_at`, `disabled_at`, `deleted_at`.


## Development

For develompent we are using docker. To start the development environment run the following command:

```bash
docker compose build develop && docker compose up -d --remove-orphans develop
```

Now when inside the container (how to do that is beyond the scope of this README) you should be able to install packages in editable mode:

```bash
pip install -e ./src/database_wrapper --config-settings editable_mode=strict
pip install -e ./src/database_wrapper_pgsql --config-settings editable_mode=strict
pip install -e ./src/database_wrapper_mysql --config-settings editable_mode=strict
pip install -e ./src/database_wrapper_mssql --config-settings editable_mode=strict
pip install -e ./src/database_wrapper_sqlite --config-settings editable_mode=strict
pip install -e ./src/database_wrapper_redis --config-settings editable_mode=strict
```

We are adding `--config-settings editable_mode=strict` for vscode to be able to use the packages in the development environment. See [#3473](https://github.com/microsoft/pylance-release/issues/3473)

## Implementation

| Database | Sync | Async | Sync Pooling | Async Pooling | Introspection |
| :------- | :--: | :---: | :----------: | :-----------: | :-----------: |
| pgsql    |  Y   |   Y   |       Y      |      Y        |       B       |
| mysql    |  Y   |   N   |       N      |      N        |       N       |
| mssql    |  Y   |   N   |       N      |      N        |       N       |
| sqlite   |  Y   |   N   |       -      |      -        |       N       |
| redis    |  Y   |   Y   |       Y      |      Y        |       N       |

## Testing

Tests are located in `src/tests/` and can be run using Python's standard `unittest` framework.

```bash
# Run all tests using the runner script (handles paths automatically)
# This will run basic initialization tests for all supported databases.
python3 -m unittest discover -v src/tests
```

### Integration Tests

To run integration tests that connect to actual database instances (MySQL, PostgreSQL, MSSQL, Redis), set the `TEST_CONNECTIONS` environment variable:

```bash
TEST_CONNECTIONS=1 python3 -m unittest discover -v src/tests
```

*   **Basic Tests:** Validate class initialization and configuration (always run).
*   **Integration Tests:** Validate actual database connections and queries (skipped by default unless `TEST_CONNECTIONS=1`).
*   **SQLite Tests:** Always run as they use an in-memory database.

## TODO

- [x] Rename methods, properties and variables to pep-8
    - [x] Solved in v0.2.2
- [x] Figure out uniform naming for sync/async classes
- [x] Add sqlite support
- [x] Add more tests
    - [ ] Even more tests are welcome, but at for now we at least have some basic tests for all databases.
- [ ] Add more usage examples
- [ ] Create a better documentation
- [ ] Add async support for Mysql and Mssql - need to look into libraries that support this
- [ ] Do we need more database support? If so, which ones?
