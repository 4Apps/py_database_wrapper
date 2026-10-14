import os
import tempfile
import unittest
from dataclasses import dataclass, field

from database_wrapper import DBDataModel, MetadataDict
from database_wrapper_sqlite import (
    DBWrapperSqlite,
    DBWrapperSqliteAsync,
    Sqlite,
    SqliteAsync,
    SqliteConfig,
    SqliteWithPoolingAsync,
)


@dataclass
class NoteModel(DBDataModel):
    @property
    def table_name(self) -> str:
        return "notes"

    body: str = field(default="", metadata=MetadataDict(db_field=("body", "text"), store=True, update=True))


class TestSqlite(unittest.TestCase):
    def test_connection_and_query(self):
        # SQLite should always work as it can be in-memory
        config: SqliteConfig = {"database": ":memory:", "timeout": 5.0}

        db = Sqlite(config)
        db.open()

        self.assertIsNotNone(db.connection)
        self.assertIsNotNone(db.cursor)

        # Test 1: Basic Select
        db.cursor.execute("SELECT 1 as val")
        row = db.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["val"], 1)

        # Test 2: Wrapper Init
        wrapper = DBWrapperSqlite(db_cursor=db.cursor)
        self.assertIsInstance(wrapper, DBWrapperSqlite)

        # Test 3: Create Table and Insert
        db.cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        db.cursor.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        db.commit()

        last_id = db.last_insert_id()
        self.assertEqual(last_id, 1)

        # Test 4: Select with Dict check
        db.cursor.execute("SELECT * FROM users WHERE id = ?", (1,))
        user = db.cursor.fetchone()
        self.assertIsInstance(user, dict)
        self.assertEqual(user["name"], "Alice")

        db.close()


class TestSqliteAsync(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config: SqliteConfig = {"database": os.path.join(directory.name, "test.sqlite3")}

    async def test_connection_enforces_foreign_keys_in_wal_mode(self):
        db = SqliteAsync(self.config)
        await db.open()
        try:
            assert db.connection
            cur = await db.connection.execute("PRAGMA foreign_keys")
            self.assertEqual(await cur.fetchone(), {"foreign_keys": 1})
            cur = await db.connection.execute("PRAGMA journal_mode")
            self.assertEqual(await cur.fetchone(), {"journal_mode": "wal"})
        finally:
            await db.close()

    async def test_transaction_commits_rolls_back_and_nests_as_savepoints(self):
        db = SqliteAsync(self.config)
        await db.open()
        try:
            assert db.connection
            conn = db.connection
            await conn.execute("CREATE TABLE t (x int)")

            async with db.transaction():
                await conn.execute("INSERT INTO t VALUES (1)")
                with self.assertRaises(RuntimeError):
                    async with conn.transaction():
                        await conn.execute("INSERT INTO t VALUES (2)")
                        raise RuntimeError("inner")

            with self.assertRaises(RuntimeError):
                async with db.transaction():
                    await conn.execute("INSERT INTO t VALUES (3)")
                    raise RuntimeError("outer")

            cur = await conn.execute("SELECT group_concat(x) AS xs FROM t")
            self.assertEqual(await cur.fetchone(), {"xs": "1"})
            self.assertFalse(conn.in_transaction)
        finally:
            await db.close()

    async def test_pool_contexts_run_the_async_wrapper(self):
        pool = SqliteWithPoolingAsync(self.config)
        await pool.open_pool()

        async with pool as (conn, cur):
            await conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
            wrapper = DBWrapperSqliteAsync(cur)
            new_id, affected = await wrapper.insert(NoteModel(body="hello"))

            # A nested context is its own connection, and sees the committed row.
            async with pool as (_other_conn, other_cur):
                found = await DBWrapperSqliteAsync(other_cur).get_by_key(NoteModel(), "id", new_id)

        await pool.close_pool()

        self.assertEqual((new_id, affected), (1, 1))
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.body, "hello")


if __name__ == "__main__":
    unittest.main()
