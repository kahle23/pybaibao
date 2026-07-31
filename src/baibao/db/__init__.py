"""
数据库连接工具模块。

提供统一的数据库操作接口。
"""

from baibao.db import rdb
from baibao.db.rdb import RdbCfg

__all__ = [
    'RdbCfg',
    'rdb',
]
