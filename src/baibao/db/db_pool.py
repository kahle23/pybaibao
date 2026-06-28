#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接池模块

提供数据库连接池管理功能，支持 MySQL 和 PostgreSQL 两种数据库类型。
数据库驱动和 DBUtils 等依赖包在首次使用时会自动安装。

支持两种连接模式：
  - 连接池模式：基于 DBUtils.PooledDB 实现，适合高并发场景
  - 单连接模式：直接使用单个数据库连接，适合低并发或资源受限场景

主要组件：
  - DbPool：数据库连接池，管理连接的创建和生命周期
  - DbCfg：数据库连接配置，支持从 JSON 文件加载
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from baibao.base import util
from baibao.base import log


@dataclass
class DbCfg:
    """
    数据库连接配置

    封装数据库连接所需的所有参数，支持多种数据库类型。

    Attributes:
        host: 服务器地址
        port: 服务端口
        username: 用户名
        password: 密码
        database: 数据库名称
        db_type: 数据库类型，支持 mysql、postgresql，默认为 mysql
        charset: 数据库字符集，默认 utf8mb4（MySQL 默认值；PostgreSQL 建议使用 utf8）
    """
    host: str
    port: int
    username: str
    password: str
    database: str
    db_type: str = 'mysql'
    charset: str = 'utf8mb4'

    @staticmethod
    def load_from_json_cfg(config_path: Union[str, Path]) -> 'DbCfg':
        """
        从 JSON 文件加载数据库配置

        读取指定路径的 JSON 文件，自动校验必填字段后返回 DbCfg 实例。

        Args:
            config_path: JSON 配置文件路径，支持字符串或 Path 对象

        Returns:
            DbCfg 实例对象

        Raises:
            FileNotFoundError: 文件不存在时抛出
            ValueError: 文件缺少必填字段时抛出
            json.JSONDecodeError: JSON 格式解析失败时抛出
        """
        return util.load_dataclass_from_json_file(config_path, DbCfg)


class DbPool:
    """
    数据库连接池

    支持两种连接模式：
    1. 连接池模式（默认）：基于 DBUtils.PooledDB 实现，适合高并发场景
    2. 单连接模式：直接使用单个数据库连接，适合低并发或资源受限场景
       单连接模式下返回 _SingleConnectionProxy 代理对象，防止调用方 close()
       误关闭共享连接，连接的生命周期由 DbPool 统一管理。

    支持 MySQL 和 PostgreSQL 两种数据库类型。
    """

    def __init__(self, cfg: DbCfg, use_pool: bool = True,
                 mincached: int = 1, maxcached: int = 10, maxconnections: int = 20):
        """
        初始化连接池

        Args:
            cfg: 数据库配置对象，包含连接所需的主机、端口、用户名、密码等信息
            use_pool: 是否使用连接池模式，True 为连接池模式（默认），False 为单连接模式
            mincached: 最小空闲连接数，连接池维护的最小空闲连接数量，默认为 1
            maxcached: 最大空闲连接数，连接池允许的最大空闲连接数量，默认为 10
            maxconnections: 最大连接数，连接池允许的最大总连接数，默认为 20
        """
        log.info(f"数据库连接初始化（use_pool:{use_pool}），地址：{cfg.db_type}://{cfg.host}:{cfg.port}/{cfg.database}")
        self.cfg = cfg
        self.use_pool = use_pool
        self.mincached = mincached
        self.maxcached = maxcached
        self.maxconnections = maxconnections
        self._pool = None
        self._connection = None
        self._init_pool()

    def _init_pool(self):
        """
        初始化连接池或单连接

        根据 use_pool 标志选择初始化方式：
        - 连接池模式：通过 DBUtils.PooledDB 创建连接池，支持 pymysql 和 psycopg2，
          pymysql 会额外设置 DictCursor 作为默认游标类型。
        - 单连接模式：通过驱动的 connect() 建立单一连接，仅在连接不存在或已关闭时创建。
        """
        driver = DbPool.get_driver(self.cfg.db_type.lower())

        if self.use_pool:
            # 连接池模式：使用 DBUtils.PooledDB
            try:
                PooledDB = util.import_module('dbutils.pooled_db', 'dbutils').PooledDB
            except ImportError:
                PooledDB = util.import_module('DBUtils.PooledDB').PooledDB
            # 构建连接池参数
            pool_kwargs = dict(
                creator=driver,
                mincached=self.mincached,
                maxcached=self.maxcached,
                maxconnections=self.maxconnections,
            )
            pool_kwargs.update(self._build_connect_kwargs())
            # 仅在驱动支持 cursors（如 pymysql）时设置 cursorclass
            if hasattr(driver, 'cursors'):
                pool_kwargs['cursorclass'] = driver.cursors.DictCursor
            # 初始化连接池
            self._pool = PooledDB(**pool_kwargs)
        else:
            # 单连接模式：创建或验证连接
            if self._connection is None or not self._is_connection_open(self._connection):
                self._connection = driver.connect(**self._build_connect_kwargs())

    def _is_connection_open(self, connection) -> bool:
        """判断数据库连接是否处于打开状态，兼容 pymysql 和 psycopg2。"""
        if hasattr(connection, 'open'):
            # pymysql
            return bool(connection.open)
        # psycopg2
        return not bool(connection.closed)

    def _build_connect_kwargs(self) -> dict:
        """
        构建数据库连接参数，根据数据库类型区分处理 charset。

        psycopg2 不支持 charset 参数，需通过 client_encoding 设置；
        pymysql 支持 charset 参数直接传入。
        """
        kwargs = dict(
            host=self.cfg.host,
            port=self.cfg.port,
            user=self.cfg.username,
            password=self.cfg.password,
            database=self.cfg.database,
        )
        if self.cfg.db_type.lower() == 'mysql':
            kwargs['charset'] = self.cfg.charset
        return kwargs

    def get_connection(self):
        """
        获取数据库连接

        连接池模式：从连接池获取一个连接，使用完毕后应调用连接的 close() 归还到连接池
        单连接模式：返回 _SingleConnectionProxy 代理对象，其 close() 为空操作，
                   防止调用方误关闭共享连接

        Returns:
            连接池模式下返回数据库连接对象；单连接模式下返回 _SingleConnectionProxy 代理
        """
        if self.use_pool:
            if self._pool is None:
                self._init_pool()
            return self._pool.connection()
        else:
            # 单连接模式：确保连接存在且有效，返回代理防止被意外关闭
            if self._connection is None or not self._is_connection_open(self._connection):
                self._init_pool()
            return _SingleConnectionProxy(self._connection)

    def close(self):
        """
        关闭连接或连接池

        单连接模式：关闭单个连接
        连接池模式：关闭整个连接池
        """
        if self.use_pool:
            if self._pool is not None:
                self._pool.close()
                self._pool = None
        else:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    @staticmethod
    def of(cfg: DbCfg, use_pool: bool = True,
           mincached: int = 1, maxcached: int = 10, maxconnections: int = 20) -> 'DbPool':
        """
        创建连接池（工厂方法）

        Args:
            cfg: 数据库配置对象
            use_pool: 是否使用连接池模式，默认为 True
            mincached: 最小空闲连接数，默认为 1
            maxcached: 最大空闲连接数，默认为 10
            maxconnections: 最大连接数，默认为 20

        Returns:
            DbPool 实例

        See Also:
            DbPool.__init__ : 参数详细说明
        """
        return DbPool(cfg, use_pool, mincached, maxcached, maxconnections)

    # 数据库驱动映射表：db_type -> (模块名, pip 包名)
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
            db_type: 数据库类型（mysql、postgresql）

        Returns:
            数据库驱动模块

        Raises:
            ValueError: 不支持的数据库类型
            ImportError: 驱动模块安装失败
        """
        # 从映射表获取驱动模块信息
        driver_tuple = DbPool.DRIVER_MAP.get(db_type.lower())
        if not driver_tuple:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        # 导入驱动模块
        module_name, install_name = driver_tuple
        return util.import_module(module_name, install_name)


class _SingleConnectionProxy:
    """
    单连接代理包装器

    包装单连接模式下的数据库连接，使调用方的 close() 不会真正关闭底层连接，
    而是交由 DbPool 统一管理连接的生命周期。
    所有其他属性和方法调用均透传给底层连接。
    """

    def __init__(self, connection):
        object.__setattr__(self, '_connection', connection)

    def close(self):
        """空操作，不关闭底层连接"""
        pass

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __setattr__(self, name, value):
        setattr(self._connection, name, value)

