"""
带连接池的 RdbClient 基类。

基于 kunlun 的 :class:`~kunlun.db.RdbClient`，覆盖 :meth:`get_connection`
走连接池（DBUtils.PooledDB）或单连接，使继承的 query / execute 自动获得
连接复用能力。子类需实现 :meth:`~kunlun.db.RdbClient.get_driver` 与
:meth:`~kunlun.db.RdbClient.build_connect_kwargs`。
"""

from typing import Any, Dict

from kunlun import logutil, modutil
from kunlun.db import RdbClient

log = logutil.getLogger(__name__)


class _SingleConnectionProxy:
    """
    单连接模式代理包装器。

    包装单连接模式下的数据库连接，使调用方的 ``close()`` 不会真正关闭底层连接，
    而是交由 :class:`PooledRdbClient` 统一管理连接的生命周期。
    其他属性与方法调用均透传给底层连接。
    """

    def __init__(self, connection) -> None:
        object.__setattr__(self, '_connection', connection)

    def close(self) -> None:
        """空操作，不关闭底层连接。"""

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __setattr__(self, name, value):
        setattr(self._connection, name, value)


class PooledRdbClient(RdbClient):
    """
    带连接池的 :class:`~kunlun.db.RdbClient` 基类。

    覆盖 :meth:`get_connection` 走连接池（或单连接），使继承自基类的
    :meth:`~kunlun.db.RdbClient.query` / :meth:`~kunlun.db.RdbClient.execute`
    自动获得连接复用能力，无需重复实现。

    子类仍需实现 :meth:`~kunlun.db.RdbClient.get_driver` 与
    :meth:`~kunlun.db.RdbClient.build_connect_kwargs`。

    支持两种模式：
      - 连接池模式（默认）：基于 DBUtils.PooledDB，线程安全；
      - 单连接模式：直接复用单个连接，**非线程安全，仅限单线程**。
    """

    def __init__(self, cfg, use_pool: bool = True, mincached: int = 1,
                 maxcached: int = 10, maxconnections: int = 20) -> None:
        """
        Args:
            cfg: 数据库配置对象。
            use_pool: 是否使用连接池模式，默认 True。
            mincached: 连接池最小空闲连接数，默认 1。
            maxcached: 连接池最大空闲连接数，默认 10。
            maxconnections: 连接池最大总连接数，默认 20。
        """
        # 先暂存池参数，再调用 super().__init__（其会触发 _validate_cfg），
        # 避免 _init_connection_source 在属性就绪前被调用。
        self.use_pool = use_pool
        self.mincached = mincached
        self.maxcached = maxcached
        self.maxconnections = maxconnections
        self._pool = None
        self._connection = None
        super().__init__(cfg)
        log.info("数据库连接初始化（use_pool:%s），地址：%s://%s:%s/%s",
                 use_pool, cfg.db_type, cfg.host, cfg.port, cfg.database)
        self._init_connection_source()

    def _init_connection_source(self) -> None:
        """初始化连接池或单连接。"""
        if self.use_pool:
            try:
                PooledDB = modutil.import_module('dbutils.pooled_db', 'dbutils').PooledDB
            except ImportError:
                PooledDB = modutil.import_module('DBUtils.PooledDB').PooledDB
            pool_kwargs: Dict[str, Any] = {
                'creator': self.get_driver(),
                'mincached': self.mincached,
                'maxcached': self.maxcached,
                'maxconnections': self.maxconnections,
            }
            pool_kwargs.update(self.build_connect_kwargs())
            self._pool = PooledDB(**pool_kwargs)
        else:
            # 单连接模式：先关闭旧连接再创建新连接，避免资源泄漏
            if self._connection is not None and self.is_connection_open(self._connection):
                try:
                    self._connection.close()
                except Exception:
                    pass
            self._connection = self.get_driver().connect(**self.build_connect_kwargs())

    def get_connection(self):
        """
        获取数据库连接。

        连接池模式：从池中获取一个连接，使用后调用其 ``close()`` 归还到池中。
        单连接模式：返回 :class:`_SingleConnectionProxy` 代理，其 ``close()`` 为空操作，
        防止调用方误关共享连接。
        """
        if self.use_pool:
            if self._pool is None:
                self._init_connection_source()
            return self._pool.connection()
        if self._connection is None or not self.is_connection_open(self._connection):
            self._init_connection_source()
        return _SingleConnectionProxy(self._connection)

    def close(self) -> None:
        """关闭连接池（或单连接），释放资源。"""
        if self.use_pool:
            if self._pool is not None:
                self._pool.close()
                self._pool = None
        else:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
