#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db.py 的测试类
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from baibao.db.db_cfg import DbCfg


class TestDbInit:
    """Db 类初始化测试"""

    def test_db_init_with_default_pool_params(self):
        """测试默认连接池参数初始化"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        with patch('baibao.db.db.DbPool') as mock_pool:
            db = Db(cfg)
            mock_pool.assert_called_once()
            call_kwargs = mock_pool.call_args[1]
            assert call_kwargs['use_pool'] is True
            assert call_kwargs['mincached'] == 1
            assert call_kwargs['maxcached'] == 10
            assert call_kwargs['maxconnections'] == 20

    def test_db_init_with_custom_pool_params(self):
        """测试自定义连接池参数初始化"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        with patch('baibao.db.db.DbPool') as mock_pool:
            db = Db(cfg, use_pool=False, mincached=2, maxcached=5, maxconnections=10)
            call_kwargs = mock_pool.call_args[1]
            assert call_kwargs['use_pool'] is False
            assert call_kwargs['mincached'] == 2
            assert call_kwargs['maxcached'] == 5
            assert call_kwargs['maxconnections'] == 10


class TestDbConnect:
    """Db 连接相关方法测试"""

    def test_connect_creates_connection(self):
        """测试 connect 方法创建连接"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = MagicMock()

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            result = db.connect()
            assert result is db
            mock_pool.get_connection.assert_called_once()
            assert db._connection is not None

    def test_connect_returns_existing_connection(self):
        """测试 connect 方法复用已有连接"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            db.connect()
            db.connect()  # 再次调用，不应再获取新连接
            mock_pool.get_connection.assert_called_once()


class TestDbCursor:
    """Db 游标相关方法测试"""

    def test_cursor_creates_connection_if_needed(self):
        """测试 cursor 方法在未连接时自动建立连接"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            cursor = db.cursor()
            assert cursor is mock_cursor
            mock_pool.get_connection.assert_called_once()


class TestDbClose:
    """Db 关闭连接测试"""

    def test_close_closes_connection(self):
        """测试 close 方法关闭连接"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            db.connect()
            assert db._connection is not None
            db.close()
            mock_connection.close.assert_called_once()
            assert db._connection is None

    def test_close_when_no_connection(self):
        """测试 close 方法在无连接时的行为"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        with patch('baibao.db.db.DbPool'):
            db = Db(cfg)
            db.close()  # 不应抛出异常


class TestDbContextManager:
    """Db 上下文管理器测试"""

    def test_context_manager_enters_and_connects(self):
        """测试上下文管理器进入时建立连接"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            with Db(cfg) as db:
                assert db._connection is mock_connection

    def test_context_manager_exits_and_closes(self):
        """测试上下文管理器退出时关闭连接"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            with Db(cfg) as db:
                pass
            mock_connection.close.assert_called_once()


class TestDbExecute:
    """Db execute 方法测试"""

    def test_execute_commits_on_success(self):
        """测试 execute 方法成功时提交事务"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            cursor = db.execute("INSERT INTO test VALUES (%s)", ("value",))
            mock_cursor.execute.assert_called_once_with("INSERT INTO test VALUES (%s)", ("value",))
            mock_connection.commit.assert_called_once()
            assert cursor is mock_cursor

    def test_execute_rollbacks_on_error(self):
        """测试 execute 方法出错时回滚事务"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("SQL error")
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            with pytest.raises(Exception, match="SQL error"):
                db.execute("INSERT INTO test VALUES (%s)", ("value",))
            mock_connection.rollback.assert_called_once()


class TestDbQuery:
    """Db query 方法测试"""

    def test_query_returns_fetchall_results(self):
        """测试 query 方法返回查询结果"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            result = db.query("SELECT * FROM test WHERE id = %s", (1,))
            mock_cursor.execute.assert_called_once_with("SELECT * FROM test WHERE id = %s", (1,))
            mock_cursor.fetchall.assert_called_once()
            assert result == [{"id": 1, "name": "test"}]

    def test_query_without_params(self):
        """测试 query 方法不带参数调用"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            result = db.query("SELECT * FROM test")
            mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)


class TestDbFactory:
    """Db 工厂方法测试"""

    def test_of_factory_method(self):
        """测试 of 工厂方法"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        with patch('baibao.db.db.DbPool') as mock_pool:
            db = Db.of(cfg, use_pool=False)
            assert db.cfg is cfg
            call_kwargs = mock_pool.call_args[1]
            assert call_kwargs['use_pool'] is False


class TestDbGetDriver:
    """Db.get_driver 静态方法测试"""

    def test_get_driver_mysql(self):
        """测试获取 MySQL 驱动"""
        from baibao.db.db import Db
        with patch('baibao.base.Util.import_module') as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            result = Db.get_driver('mysql')
            mock_import.assert_called_once_with('pymysql', 'pymysql')
            assert result is mock_module

    def test_get_driver_postgresql(self):
        """测试获取 PostgreSQL 驱动"""
        from baibao.db.db import Db
        with patch('baibao.base.Util.import_module') as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            result = Db.get_driver('postgresql')
            mock_import.assert_called_once_with('psycopg2', 'psycopg2')
            assert result is mock_module

    def test_get_driver_unsupported_type(self):
        """测试获取不支持的数据库类型"""
        from baibao.db.db import Db
        with pytest.raises(ValueError, match="不支持的数据库类型"):
            Db.get_driver('sqlite')


class TestDbDestructor:
    """Db 析构函数测试"""

    def test_del_closes_connection(self):
        """测试 __del__ 方法关闭连接"""
        from baibao.db.db import Db
        cfg = DbCfg(
            host="localhost",
            port=3306,
            username="root",
            password="password",
            database="test_db"
        )
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_pool.get_connection.return_value = mock_connection

        with patch('baibao.db.db.DbPool', return_value=mock_pool):
            db = Db(cfg)
            db.connect()
            del db  # 不应抛出异常
