"""
数据库连接工具模块。

提供统一的数据库操作接口。
"""

from . import rdb
from .rdb import RdbCfg, rdb_mgr

__all__ = [
    'RdbCfg',
    'rdb',
    'rdb_mgr',
]
