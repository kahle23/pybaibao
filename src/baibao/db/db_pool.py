#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接池模块

提供数据库连接池管理和数据库连接包装功能，支持多种数据库类型（MySQL、PostgreSQL）。
自动处理依赖包的安装，支持连接池模式和直连模式两种连接方式。
"""

from baibao.base import Util
from .db_cfg import DbCfg


class DbPool:
    """
    数据库连接池

    支持两种连接模式：
    1. 连接池模式（默认）：基于 DBUtils.PooledDB 实现，适合高并发场景
    2. 单连接模式：直接使用单个数据库连接，适合低并发或资源受限场景

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

        根据 use_pool 参数决定初始化连接池还是单连接。
        对于单连接模式，会确保连接已创建且处于打开状态。
        """
        from .db_util import DbUtil
        driver = DbUtil.get_driver(self.cfg.db_type.lower())

        if self.use_pool:
            # 连接池模式：使用 DBUtils.PooledDB
            try:
                # PooledDB = Util.import_module('DBUtils.PooledDB', 'dbutils').PooledDB
                PooledDB = Util.import_module('dbutils.pooled_db', 'dbutils').PooledDB
            except ImportError:
                # from dbutils.pooled_db import PooledDB
                PooledDB = Util.import_module('DBUtils.PooledDB').PooledDB
            # 初始化连接池
            self._pool = PooledDB(
                creator=driver,
                host=self.cfg.host,
                port=self.cfg.port,
                user=self.cfg.username,
                password=self.cfg.password,
                database=self.cfg.database,
                charset=self.cfg.charset,
                mincached=self.mincached,
                maxcached=self.maxcached,
                maxconnections=self.maxconnections,
                cursorclass=driver.cursors.DictCursor if hasattr(driver, 'cursors') else None,
            )
        else:
            # 单连接模式：创建或验证连接
            if self._connection is None or not self._connection.open:
                self._connection = driver.connect(
                    host=self.cfg.host,
                    port=self.cfg.port,
                    user=self.cfg.username,
                    password=self.cfg.password,
                    database=self.cfg.database,
                    charset=self.cfg.charset,
                )

    def get_connection(self):
        """
        获取数据库连接

        连接池模式：从连接池获取一个连接
        单连接模式：返回已建立的单个连接

        Returns:
            数据库连接对象，由底层数据库驱动提供
        """
        if self.use_pool:
            if self._pool is None:
                self._init_pool()
            return self._pool.connection()
        else:
            # 单连接模式：确保连接存在且有效
            if self._connection is None or not self._connection.open:
                self._init_pool()
            return self._connection

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
        创建连接池

        提供便捷的方式创建 DbPool 实例。

        Args:
            cfg: 数据库配置对象
            use_pool: 是否使用连接池模式，True 为连接池模式（默认），False 为单连接模式
            mincached: 最小空闲连接数，连接池维护的最小空闲连接数量，默认为 1
            maxcached: 最大空闲连接数，连接池允许的最大空闲连接数量，默认为 10
            maxconnections: 最大连接数，连接池允许的最大总连接数，默认为 20

        Returns:
            DbPool: 连接池实例
        """
        return DbPool(cfg, use_pool, mincached, maxcached, maxconnections)
