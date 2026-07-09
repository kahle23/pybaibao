"""
数据库连接工具模块。

提供统一的数据库操作接口。
"""

from baibao.db import sql
from baibao.db.sql import DbCfg, DbClient

__all__ = [
    'sql',
    'DbCfg',
    'DbClient',
]
