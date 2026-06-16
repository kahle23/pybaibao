from typing import Optional

from baibao.base import Util
from .db_cfg import DbCfg
from .db_pool import DbPool


class Db:
    """
    数据库连接包装类

    提供统一的数据库连接接口。
    实现上下文管理器协议，支持 `with` 语句自动管理连接生命周期。
    """

    def __init__(self, cfg: DbCfg, use_pool: bool = True, mincached: int = 1, maxcached: int = 10, maxconnections: int = 20):
        """
        初始化数据库连接包装器

        Args:
            cfg: 数据库配置对象，包含连接所需的主机、端口、用户名、密码等信息
            use_pool: 是否使用连接池，默认为 True（推荐使用连接池）
            mincached: 最小空闲连接数，默认为 1
            maxcached: 最大空闲连接数，默认为 10
            maxconnections: 最大连接数，默认为 20
        """

        self.cfg = cfg
        self._pool = DbPool(cfg, use_pool=use_pool, mincached=mincached, maxcached=maxcached, maxconnections=maxconnections)
        self._connection = None

    def connect(self):
        """
        建立数据库连接

        从连接池获取连接。如果连接已存在，则复用现有连接。

        Returns:
            Db: 返回自身实例，支持链式调用
        """
        if self._connection is not None:
            return self

        self._connection = self._pool.get_connection()
        return self

    def cursor(self):
        """
        获取数据库游标

        如果连接尚未建立，会先自动建立连接。

        Returns:
            游标对象，默认返回 DictCursor（以字典形式返回查询结果）
        """
        if self._connection is None:
            self.connect()
        return self._connection.cursor()

    def close(self):
        """
        关闭数据库连接

        释放底层数据库连接资源。如果使用连接池，连接会被归还到池中；
        如果是直连模式，连接会被直接关闭。
        """
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False

    def execute(self, sql: str, params: tuple = None):
        """
        执行 SQL 语句

        自动提交事务，适用于 INSERT、UPDATE、DELETE 等写操作。

        Args:
            sql: SQL 语句字符串
            params: SQL 参数，用于参数化查询，防止 SQL 注入

        Returns:
            游标对象，可通过游标获取执行结果（如受影响行数）
        """
        if self._connection is None:
            self.connect()
        
        cursor = self._connection.cursor()
        try:
            cursor.execute(sql, params)
            self._connection.commit()
            return cursor
        except Exception:
            self._connection.rollback()
            raise

    def query(self, sql: str, params: tuple = None):
        """
        执行查询并返回结果

        适用于 SELECT 等读操作，返回查询结果列表。

        Args:
            sql: SQL 查询语句字符串
            params: SQL 参数，用于参数化查询，防止 SQL 注入

        Returns:
            list[dict]: 查询结果列表，每个元素是一个字典，键为列名
        """
        if self._connection is None:
            self.connect()
        
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    def __del__(self):
        """析构函数"""
        self.close()

    @staticmethod
    def of(cfg: DbCfg, **pool_kwargs) -> 'Db':
        """
        获取数据库连接包装器（工厂方法）

        Args:
            cfg: 数据库配置对象
            pool_kwargs: 连接池参数（use_pool, mincached, maxcached, maxconnections）

        Returns:
            Db: 数据库连接包装器实例
        """
        return Db(cfg, **pool_kwargs)

    DRIVER_MAP = {
        'mysql': ('pymysql', 'pymysql'),
        'postgresql': ('psycopg2', 'psycopg2'),
    }

    @staticmethod
    def get_driver(db_type: str):
        """
        获取数据库驱动模块

        根据数据库类型动态导入对应的数据库驱动模块，如未安装则自动安装。

        Args:
            db_type: 数据库类型（如 'mysql'、'postgresql'）

        Returns:
            数据库驱动模块

        Raises:
            ValueError: 不支持的数据库类型
            ImportError: 驱动模块安装失败
        """
        driver_tuple = Db.DRIVER_MAP.get(db_type.lower())
        if not driver_tuple:
            raise ValueError(f"不支持的数据库类型: {db_type}")

        module_name, install_name = driver_tuple
        return Util.import_module(module_name, install_name)

