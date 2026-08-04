"""
SQL 数据库模块。

基于 pykunlun 的 RdbClient / RdbManager 抽象层，
提供驱动客户端，以及默认管理器实例
:data:`rdb_mgr`，用户直接拿该实例按名称/类型注册和管理实例。

sqlite 驱动复用 pykunlun 内置的 :class:`~pykunlun.db.SqliteClient`（connect-per-call）；

典型用法::

    from baibao.db.rdb import rdb_mgr, MysqlClient, RdbCfg

    # 驱动：为不同环境注册同类型的 MySQL 实例（实现类相同、连接配置不同）
    rdb_mgr.register("dev",  MysqlClient(RdbCfg(db_type='mysql', host='dev-host', ...)))
    rdb_mgr.register("test", MysqlClient(RdbCfg(db_type='mysql', host='test-host', ...)))

    # 按别名选择实例执行（省略 name 时用默认名 "default"）
    rdb_mgr.execute("INSERT INTO t VALUES (1)", name="dev")
    rows = rdb_mgr.query("SELECT * FROM t", name="test")
"""

import json
import logging

from pykunlun.db import (
    RdbCfg,
    RdbManager,
    SqliteClient,
)
from pykunlun.util import ResolveType, fileutil

from .mysql_client import MysqlClient
from .pooled_client import PooledDBClient
from .postgresql_client import PostgresqlClient

log = logging.getLogger(__name__)

# region ======== 配置加载 ========

_config_loaded = False


def _config_loader(manager: RdbManager, name: str) -> None:
    """配置加载器，注册客户端类并从 .baibao/rdb.config 加载配置，只执行一次。"""
    global _config_loaded
    if _config_loaded:
        return
    _config_loaded = True

    # 注册客户端类
    manager.register_client_class(MysqlClient)
    manager.register_client_class(PostgresqlClient)
    manager.register_client_class(SqliteClient)

    # 从配置文件加载实例
    try:
        content = fileutil.read_text(".baibao/rdb.config",
                           search_dirs=[ResolveType.CURRENT, ResolveType.USER])
        config: dict[str, dict] = json.loads(content)
        for n, cfg_data in config.items():
            cfg = RdbCfg(**cfg_data)
            manager.register(n, cfg)
    except Exception as e:
        log.warning("Failed to load rdb config: %s", e)


# endregion


# region ======== 模块级管理器实例 ========

#: 模块级默认驱动管理器实例，按名称（别名）管理各数据库客户端实例
rdb_mgr: RdbManager = RdbManager(config_loader=_config_loader)

# endregion
__all__ = [
    'MysqlClient',
    'PooledDBClient',
    'RdbCfg',
    'SqliteClient',
    'rdb_mgr',
]
