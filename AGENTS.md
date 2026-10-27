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

SQLite tests always run (in-memory or temp-file DB). Other integration tests require `TEST_CONNECTIONS=1` and running services via `docker-compose up`.

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

### Dependencies

Adapter `pyproject.toml` files hold floors for driver dependencies, each clear of published
security advisories (a cap only for a known breaking major - an upper bound there binds every
downstream project), plus the exact `database_wrapper` pin. Dev tools are minor-pinned.

### Changelog

Every user-visible change adds one line under `## Unreleased` in `CHANGELOG.md`, in the same
change. One line each - no paragraphs, no file lists, no rationale; that belongs in the commit
message. Prefix `**Breaking:**` when a downstream project must act. Refactors and tests get none.
One changelog covers all six packages; name the adapter when an entry is about one.

### Versioning

`major.minor` is manual and lives in `.version`. The patch counts releases within that minor
(`0.4.0`, `0.4.1`, ...) and is read off the `v<major.minor>.<patch>` tags - never stored, never
bumped by hand. All six packages share the one number — they are released in lockstep and pin
each other exactly.

```bash
scripts/version.bash              # what the current commit would publish as, e.g. 0.4.1
scripts/version.bash --dev        # next patch + commits since the newest tag, 0.4.1.dev3
scripts/bump_version.bash minor   # bump and stage .version and the bare pins (or major)
scripts/set_version.bash [VER]    # stamp a version into the workspace, ready to build
scripts/changelog.bash prepare    # rename "## Unreleased" to the next version, dated
scripts/changelog.bash notes TAG  # print that section, the GitHub release body
scripts/release_tag.bash          # create v<version> for the current commit
```

- `version.bash` — a commit carrying a release tag of the current minor prints that version,
  any other commit the next patch. Needs tags and full history (`fetch-depth: 0`); refuses a
  shallow clone.
- `.version` — the only place the version is declared. The six `pyproject.toml` files and
  `config.py` carry the bare `major.minor` so a local editable install of all six resolves
  against itself; `set_version.bash` writes the full number in at build time and verifies
  every version line and cross-package pin actually changed. That rewrite is workspace-only
  and is never committed.
- The release workflow checks the tag matches the derived version, stamps it, then asserts the
  six wheel filenames before uploading.
- The pre-commit hook does not touch the version — it only records the commit hash and date in
  `config.py`.
- `release_tag.bash` refuses a commit that is already released, a version without a changelog
  section, and a tag sorting below the newest existing one (remedy: bump the minor).

**A version on PyPI can never be replaced, and a deleted one can never be re-uploaded.**
Release numbers come from tags, so a rebase, squash or merge commit cannot shift them.

Releasing — the last step is what publishes all six packages:

```bash
scripts/changelog.bash prepare    # Unreleased -> v0.4.0; commit CHANGELOG.md
scripts/release_tag.bash          # creates v0.4.0 locally
git push origin v0.4.0            # publishes nothing
scripts/changelog.bash notes v0.4.0 | gh release create v0.4.0 --title v0.4.0 --notes-file -
```

## Architecture

### Module Layout

Each database adapter is a separate installable package under `src/`:

- `database_wrapper/` — Core: base classes, protocols, serialization, filter system
- `database_wrapper_pgsql/` — PostgreSQL (psycopg3, supports async + connection pooling)
- `database_wrapper_mysql/` — MySQL (mysqlclient)
- `database_wrapper_mssql/` — MSSQL (pymssql)
- `database_wrapper_sqlite/` — SQLite (stdlib `sqlite3`; async + `async with` pool on aiosqlite, autocommit with `BEGIN IMMEDIATE` transactions)
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
