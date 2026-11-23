import os
import unittest
from unittest import IsolatedAsyncioTestCase

from database_wrapper_pgsql import (
    DBWrapperPgsqlAsync,
    PgsqlConfig,
    PgsqlWithPoolingAsync,
)

# Mock config
POSTGRES_CONFIG: PgsqlConfig = {
    "hostname": "localhost",
    "port": 5432,
    "username": "postgres",
    "password": "password",
    "database": "postgres",
    "maxconnections": 10,
}


class TestPgsqlAsync(IsolatedAsyncioTestCase):
    def test_init(self):
        """Test basic initialization"""
        pool = PgsqlWithPoolingAsync(POSTGRES_CONFIG)
        self.assertIsInstance(pool, PgsqlWithPoolingAsync)
        self.assertEqual(pool.config["hostname"], "localhost")

    @unittest.skipUnless(
        os.environ.get("TEST_CONNECTIONS", "").lower() in ("1", "true", "yes"),
        "Skipping connection test. Set TEST_CONNECTIONS=1 to run.",
    )
    async def test_connection_and_query(self):
        """Test actual connection and query execution"""
        try:
            pool = PgsqlWithPoolingAsync(POSTGRES_CONFIG)
            await pool.open_pool()

            async with pool as (conn, cursor):
                self.assertIsNotNone(conn)
                self.assertIsNotNone(cursor)

                await cursor.execute("SELECT 1 as val")
                row = await cursor.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["val"], 1)

                wrapper = DBWrapperPgsqlAsync(db_cursor=cursor)
                self.assertIsInstance(wrapper, DBWrapperPgsqlAsync)

            await pool.close_pool()
        except Exception as e:
            self.fail(f"PGSQL test failed with error: {e}")

    @unittest.skipUnless(
        os.environ.get("TEST_CONNECTIONS", "").lower() in ("1", "true", "yes"),
        "Skipping connection test. Set TEST_CONNECTIONS=1 to run.",
    )
    async def test_password_callable_per_connection(self):
        """A callable password is called for every connection the pool opens"""
        calls = 0

        async def password() -> str:
            nonlocal calls
            calls += 1
            return POSTGRES_CONFIG["password"]

        pool = PgsqlWithPoolingAsync({**POSTGRES_CONFIG, "password": password})
        await pool.open_pool()
        try:
            # One more connection than the pool opens up front, so it has to grow
            async with pool as (_, cursor_1), pool as (_, cursor_2), pool as (_, cursor_3):
                self.assertIsNotNone(cursor_1)
                self.assertIsNotNone(cursor_2)
                self.assertIsNotNone(cursor_3)

            self.assertGreaterEqual(calls, 3)
            self.assertEqual(calls, pool.pool_async.get_stats()["connections_num"])
        finally:
            await pool.close_pool()
