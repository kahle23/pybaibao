"""
SQL 数据库模块。

提供 SQL 数据库客户端管理和常用操作接口。
"""

from ._sql import (
    get_driver,
    get_client,
    set_client,
    remove_client,
    get_connection,
    close,
    clear,
    execute,
    query,
)
from .db_client import DbCfg, DbClient


__all__ = [
    'get_driver',
    'get_client',
    'set_client',
    'remove_client',
    'get_connection',
    'close',
    'clear',
    'execute',
    'query',
    'DbCfg',
    'DbClient',
]
