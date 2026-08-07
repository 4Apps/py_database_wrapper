# AGENTS.md

## Project Overview

Multi-database Python wrapper library (`database-wrapper`) supporting PostgreSQL, MySQL, MSSQL, SQLite, and Redis. Published to PyPI as separate packages with a shared core. Zero runtime dependencies for the core module.

## Commands

### Tests

```bash
# Run all tests (unit only, no DB connections needed)
python3 -m unittest discover -v src/tests

# Run integration tests (requires running database services)
TEST_CONNECTIONS=1 python3 -m unittest discover -v src/tests

# Run a single test file
python3 -m unittest -v src/tests/test_sqlite.py

# Run a single test
python3 -m unittest -v src.tests.test_sqlite.TestSqlite.test_init
```

SQLite tests always run (in-memory DB). Other integration tests require `TEST_CONNECTIONS=1` and running services via `docker-compose up`.

### Linting & Type Checking

```bash
# Format and lint
ruff format src/
ruff check src/ --fix

# Type check
mypy src/

# Spell check
codespell src/
```

### Building

```bash
# Build all packages (from project root)
pip install -e ".[dev]"

# Build specific adapter
pip install -e src/database_wrapper_pgsql/
```

### Versioning

`major.minor` is manual and lives in `.version`; the patch part is the git commit count,
stamped by CI at build time. All six packages share the one number — they are released in
lockstep and pin each other exactly.

```bash
scripts/version.bash              # what the current commit would publish as, e.g. 0.3.145
scripts/version.bash --dev        # the develop-channel form, 0.3.145.dev0
scripts/bump_version.bash minor   # bump and stage .version (and major; never patch)
scripts/set_version.bash [VER]    # stamp a version into the workspace, ready to build
scripts/release_tag.bash          # create v<version> for the current commit
```

- `.version` — the only place the version is declared. The six `pyproject.toml` files and
  `config.py` carry the bare `major.minor` so a local editable install of all six resolves
  against itself; `set_version.bash` writes the full number in at build time and verifies
  every version line and cross-package pin actually changed. That rewrite is workspace-only
  and is never committed.
- The release workflow runs it after checking the tag matches the derived version, then
  asserts the six wheel filenames before uploading. Checkout needs `fetch-depth: 0` or the
  count is wrong, and `version.bash` refuses a shallow clone rather than reporting `.1`.
- Nothing bumps the patch by hand, and the pre-commit hook no longer touches the version —
  it only records the commit hash and date in `config.py`.

The commit count only grows on a branch that is added to, but a rebase, a squash or a reset
can shorten history and hand back a version below one already published — and **a version on
PyPI can never be replaced, and a deleted one can never be re-uploaded**. `release_tag.bash`
refuses to cut a tag that sorts below the newest existing one; the remedy is to bump the
minor.

Releasing: commit, `scripts/release_tag.bash`, `git push origin v<version>`, then create the
GitHub release from that tag — that last step is what publishes all six packages.

## Architecture

### Module Layout

Each database adapter is a separate installable package under `src/`:

- `database_wrapper/` — Core: base classes, protocols, serialization, filter system
- `database_wrapper_pgsql/` — PostgreSQL (psycopg3, supports async + connection pooling)
- `database_wrapper_mysql/` — MySQL (mysqlclient)
- `database_wrapper_mssql/` — MSSQL (pymssql)
- `database_wrapper_sqlite/` — SQLite (stdlib)
- `database_wrapper_redis/` — Redis (redis-py)

### Class Hierarchy

```
DatabaseBackend          — Abstract base for DB connections (open/close/ping/commit)
├── Mysql, Mssql, Sqlite, PgsqlWithPooling, Redis

DBWrapperMixin           — Shared query building and filter logic
├── DBWrapper            — Sync: get_one/get_all/insert/update/delete (returns Generators)
└── DBWrapperAsync       — Async: same interface with async generators

DBDataModel (@dataclass) — Base model with id, serialization, dict/JSON conversion
└── DBDefaultsDataModel  — Adds created_at, updated_at, disabled_at, deleted_at

DBIntrospector           — Base schema introspection, auto-generates dataclasses from DB schema
```

### Key Patterns

- **Dataclass metadata system**: Field behavior controlled via `metadata` dict on dataclass fields — keys: `db_field`, `store`, `update`, `exclude`, `serialize`/`deserialize`, `enum_class`, `timezone`
- **MongoDB-like filter operators**: `$contains`, `$starts_with`, `$ends_with`, `$min/$max`, `$in/$not_in`, `$gt/$gte/$lt/$lte`, `$is_null/$is_not_null`, `$not`
- **Generator results**: `get_all()` and `get_filtered()` return generators/async generators for memory efficiency
- **NoParam sentinel**: Used in filters for operators that take no value (e.g., `$is_null`)

### Adding a New Adapter

Follow the pattern in any existing adapter (e.g., `database_wrapper_sqlite`):
1. Create `src/database_wrapper_<db>/` with its own `pyproject.toml`
2. Implement `connector.py` extending `DatabaseBackend`
3. Implement `db_wrapper_<db>.py` extending `DBWrapper` and/or `DBWrapperAsync`
4. Implement `<db>_introspector.py` extending `DBIntrospector`

## Code Style

- Line length: 120 chars (ruff)
- Double quotes
- Full type annotations on all public methods (`str | None` style, not `Optional`)
- Python 3.8+ compatibility for published packages
- Always use braces for if blocks, even single-line bodies
