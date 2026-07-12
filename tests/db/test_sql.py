import unittest
from unittest.mock import MagicMock
from baibao.db import sql
from baibao.db.sql.db_client import DbClient


class TestExecute(unittest.TestCase):
    """测试 execute 方法 - 执行 SQL 语句（INSERT、UPDATE、DELETE）"""

    def setUp(self):
        sql.clear()

    def test_execute_success(self):
        """测试执行成功并返回影响行数"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor

        mock_client = MagicMock(spec=DbClient)
        mock_client.get_connection.return_value = mock_conn
        sql.set_client('', mock_client)

        result = sql.execute("INSERT INTO test VALUES(1)")

        self.assertEqual(result, 1)
        mock_cursor.execute.assert_called_once_with("INSERT INTO test VALUES(1)", None)
        mock_conn.commit.assert_called_once()

    def test_execute_rollback_on_error(self):
        """测试出错时回滚"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB Error")
        mock_conn.cursor.return_value = mock_cursor

        mock_client = MagicMock(spec=DbClient)
        mock_client.get_connection.return_value = mock_conn
        sql.set_client('', mock_client)

        with self.assertRaises(Exception):
            sql.execute("FAILING QUERY")

        mock_conn.rollback.assert_called_once()


class TestQuery(unittest.TestCase):
    """测试 query 方法 - 执行查询语句"""

    def setUp(self):
        sql.clear()

    def test_query_success(self):
        """测试查询成功并返回结果"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]
        mock_conn.cursor.return_value = mock_cursor

        mock_client = MagicMock(spec=DbClient)
        mock_client.get_connection.return_value = mock_conn
        sql.set_client('', mock_client)

        result = sql.query("SELECT * FROM users")

        self.assertEqual(result, [{'id': 1, 'name': 'test'}])
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users", None)

    def test_query_with_params(self):
        """测试带参数的查询"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_client = MagicMock(spec=DbClient)
        mock_client.get_connection.return_value = mock_conn
        sql.set_client('', mock_client)

        sql.query("SELECT * FROM users WHERE id = %s", (1,))

        mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (1,))

