import unittest
from unittest.mock import MagicMock, patch
from baibao.db.db_util import DbUtil
from baibao.db.db_pool import DbPool
from baibao.db.db_cfg import DbCfg


class TestDbUtilGetPool(unittest.TestCase):
    """测试 DbUtil.get_pool 方法"""

    def setUp(self):
        # 清理之前的池实例
        DbUtil._pools.clear()

    def test_get_pool_with_default_name(self):
        """测试使用默认配置名获取池（跳过：需要真实配置文件）"""
        # 此测试需要 ./db.config 文件存在，这里跳过实际调用
        # 如果配置文件不存在，会抛出 KeyError
        try:
            DbUtil.get_pool()
            self.fail("Expected KeyError due to missing config file")
        except KeyError as e:
            self.assertIn("自动加载默认配置失败", str(e))

    @patch('baibao.db.db_util.DbCfg')
    def test_get_pool_with_custom_name(self, mock_cfg):
        """测试使用自定义配置名获取池（需先设置）"""
        mock_cfg_instance = MagicMock()
        mock_cfg.load_json_config.return_value = mock_cfg_instance

        # 先设置一个池
        test_pool = MagicMock(spec=DbPool)
        DbUtil.set_pool('test_cfg', test_pool)

        pool = DbUtil.get_pool('test_cfg')

        self.assertEqual(pool, test_pool)

    def test_get_pool_unknown_name_raises(self):
        """测试获取不存在的配置名时抛出 KeyError"""
        with self.assertRaises(KeyError) as context:
            DbUtil.get_pool('nonexistent')

        self.assertIn("未找到配置名", str(context.exception))


class TestDbUtilSetPool(unittest.TestCase):
    """测试 DbUtil.set_pool 方法"""

    def setUp(self):
        DbUtil._pools.clear()

    def test_set_pool_with_dbpool_instance(self):
        """测试设置 DbPool 实例"""
        test_pool = MagicMock(spec=DbPool)
        DbUtil.set_pool('test', test_pool)

        self.assertEqual(DbUtil._pools['test'], test_pool)

    def test_set_pool_with_dbcfg_object(self):
        """测试设置 DbCfg 对象（使用 mock 避免真实数据库连接）"""
        from unittest.mock import patch

        # Mock DbPool.__init__ 以避免真实数据库连接
        with patch('baibao.db.db_pool.DbPool.__init__', return_value=None):
            test_cfg = DbCfg(host='localhost', port=3306, username='user', password='pass', database='db')
            DbUtil.set_pool('test', test_cfg)

        self.assertIsInstance(DbUtil._pools['test'], DbPool)

    def test_set_pool_invalid_type_raises(self):
        """测试设置无效类型时抛出 TypeError"""
        with self.assertRaises(TypeError) as context:
            DbUtil.set_pool('test', "invalid")

        self.assertIn("必须是 DbPool 或 DbCfg 类型", str(context.exception))


class TestDbUtilRemovePool(unittest.TestCase):
    """测试 DbUtil.remove_pool 方法"""

    def setUp(self):
        DbUtil._pools.clear()

    def test_remove_default_pool(self):
        """测试移除默认配置的池"""
        test_pool = MagicMock(spec=DbPool)
        DbUtil.set_pool('', test_pool)

        DbUtil.remove_pool()

        self.assertNotIn('', DbUtil._pools)

    def test_remove_custom_pool(self):
        """测试移除自定义配置的池"""
        test_pool = MagicMock(spec=DbPool)
        DbUtil.set_pool('my_cfg', test_pool)

        DbUtil.remove_pool('my_cfg')

        self.assertNotIn('my_cfg', DbUtil._pools)

    def test_remove_nonexistent_pool(self):
        """测试移除不存在的池不会报错"""
        DbUtil.remove_pool('nonexistent')  # 不应抛出异常


class TestDbUtilExecute(unittest.TestCase):
    """测试 DbUtil.execute 方法"""

    def setUp(self):
        DbUtil._pools.clear()

    @patch('baibao.db.db_util.DbUtil.get_connection')
    def test_execute_success(self, mock_get_conn):
        """测试执行成功"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # 创建一个模拟的 DbPool 来替代真实连接
        mock_pool = MagicMock(spec=DbPool)
        mock_pool.get_connection.return_value = mock_conn
        DbUtil.set_pool('', mock_pool)

        result = DbUtil.exec("INSERT INTO test VALUES(1)")

        self.assertEqual(result, mock_cursor)
        mock_cursor.execute.assert_called_once_with("INSERT INTO test VALUES(1)", None)
        mock_conn.commit.assert_called_once()

    @patch('baibao.db.db_util.DbUtil.get_connection')
    def test_execute_rollback_on_error(self, mock_get_conn):
        """测试出错时回滚"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB Error")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # 创建一个模拟的 DbPool 来替代真实连接
        mock_pool = MagicMock(spec=DbPool)
        mock_pool.get_connection.return_value = mock_conn
        DbUtil.set_pool('', mock_pool)

        with self.assertRaises(Exception):
            DbUtil.exec("FAILING QUERY")

        mock_conn.rollback.assert_called_once()


class TestDbUtilQuery(unittest.TestCase):
    """测试 DbUtil.query 方法"""

    def setUp(self):
        DbUtil._pools.clear()

    @patch('baibao.db.db_util.DbUtil.get_connection')
    def test_query_success(self, mock_get_conn):
        """测试查询成功"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # 创建一个模拟的 DbPool 来替代真实连接
        mock_pool = MagicMock(spec=DbPool)
        mock_pool.get_connection.return_value = mock_conn
        DbUtil.set_pool('', mock_pool)

        result = DbUtil.query("SELECT * FROM users")

        self.assertEqual(result, [{'id': 1, 'name': 'test'}])
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users", None)

    @patch('baibao.db.db_util.DbUtil.get_connection')
    def test_query_with_params(self, mock_get_conn):
        """测试带参数的查询"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # 创建一个模拟的 DbPool 来替代真实连接
        mock_pool = MagicMock(spec=DbPool)
        mock_pool.get_connection.return_value = mock_conn
        DbUtil.set_pool('', mock_pool)

        DbUtil.query("SELECT * FROM users WHERE id = %s", (1,))

        mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (1,))


class TestDbUtilClose(unittest.TestCase):
    """测试 DbUtil.close 方法"""

    def setUp(self):
        DbUtil._pools.clear()

    @patch('baibao.db.db_util.DbUtil.get_pool')
    def test_close_pool(self, mock_get_pool):
        """测试关闭连接池"""
        mock_pool = MagicMock(spec=DbPool)
        mock_get_pool.return_value = mock_pool

        DbUtil.close()

        mock_pool.close.assert_called_once()


class TestDbUtilGetDriver(unittest.TestCase):
    """测试 DbUtil.get_driver 方法"""

    def test_get_mysql_driver(self):
        """测试获取 MySQL 驱动"""
        driver = DbUtil.get_driver('mysql')
        self.assertEqual(driver.__name__, 'pymysql')

    def test_get_postgresql_driver(self):
        """测试获取 PostgreSQL 驱动"""
        driver = DbUtil.get_driver('postgresql')
        self.assertEqual(driver.__name__, 'psycopg2')

    def test_get_unsupported_type_raises(self):
        """测试不支持的数据库类型抛出 ValueError"""
        with self.assertRaises(ValueError) as context:
            DbUtil.get_driver('oracle')

        self.assertIn("不支持的数据库类型", str(context.exception))


class TestDbUtilClear(unittest.TestCase):
    """测试 DbUtil.clear 方法"""

    def setUp(self):
        DbUtil._pools.clear()

    def test_clear_removes_all_pools(self):
        """测试清空所有连接池"""
        test_pool1 = MagicMock(spec=DbPool)
        test_pool2 = MagicMock(spec=DbPool)

        DbUtil.set_pool('cfg1', test_pool1)
        DbUtil.set_pool('cfg2', test_pool2)

        DbUtil.clear()

        self.assertEqual(len(DbUtil._pools), 0)

    def test_clear_with_no_pools(self):
        """测试清空空连接池不会报错"""
        # 不应抛出异常
        DbUtil.clear()
        self.assertEqual(len(DbUtil._pools), 0)

    def test_clear_after_adding_pools(self):
        """测试清空后再添加新池"""
        DbUtil.clear()

        new_pool = MagicMock(spec=DbPool)
        DbUtil.set_pool('new_cfg', new_pool)

        self.assertIn('new_cfg', DbUtil._pools)
        self.assertEqual(DbUtil._pools['new_cfg'], new_pool)
