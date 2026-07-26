"""
SQL 数据库模块。

提供 SQL 数据库客户端管理和常用操作接口。
"""

from ._sql import (
    clear,
    close,
    execute,
    get_client,
    get_connection,
    get_driver,
    query,
    remove_client,
    set_client,
)
from .db_client import DbCfg, DbClient

__all__ = [
    'DbCfg',
    'DbClient',
    'clear',
    'close',
    'execute',
    'get_client',
    'get_connection',
    'get_driver',
    'query',
    'remove_client',
    'set_client',
]
