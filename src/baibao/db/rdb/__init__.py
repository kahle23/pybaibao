"""
SQL 数据库模块。

基于 kunlun 的 RdbClient / RdbManager 抽象层，
提供驱动客户端实现，以及模块级默认管理器实例
:data:`rdb`，用户直接拿这些实例按名称/类型注册和管理实例。

sqlite 驱动复用 kunlun 内置的 :class:`~kunlun.db.SqliteClient`（connect-per-call）；

典型用法::

    from baibao.db.rdb import rdb, MysqlRdbClient, RdbCfg

    # 驱动：为不同环境注册同类型的 MySQL 实例（实现类相同、连接配置不同）
    rdb.register("dev",  MysqlRdbClient(RdbCfg(db_type='mysql', host='dev-host', ...)))
    rdb.register("test", MysqlRdbClient(RdbCfg(db_type='mysql', host='test-host', ...)))

    # 按别名选择实例执行（省略 name 时用默认名 "default"）
    rdb.execute("INSERT INTO t VALUES (1)", name="dev")
    rows = rdb.query("SELECT * FROM t", name="test")

"""

from kunlun.db import (
    RdbCfg,
    RdbManager,
    SqliteClient,
)

from .mysql_client import MysqlRdbClient
from .pooled_client import PooledRdbClient
from .postgresql_client import PostgresqlRdbClient

#: 模块级默认驱动管理器实例，按名称（别名）管理各数据库客户端实例
rdb: RdbManager = RdbManager()

__all__ = [
    'MysqlRdbClient',
    'PooledRdbClient',
    'PostgresqlRdbClient',
    'RdbCfg',
    'SqliteClient',
    'rdb',
]
