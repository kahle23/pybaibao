"""
PostgreSQL 驱动客户端（psycopg2，连接池）。

继承 :class:`~baibao.db.rdb.pooled_client.PooledRdbClient`，驱动模块由本类
通过 :func:`kunlun.modutil.import_module` 自行导入与按需安装。
"""

from decimal import Decimal
from typing import Any, Callable, Dict

from kunlun import modutil

from .pooled_client import PooledRdbClient


class PostgresqlRdbClient(PooledRdbClient):
    """PostgreSQL 驱动客户端（psycopg2，连接池）。"""

    db_type = 'postgresql'

    def _validate_and_prepare_cfg(self) -> None:
        # PostgreSQL 标准默认：端口 5432、字符集 utf8；先填再交基类校验。
        if self.cfg.port is None:
            self.cfg.port = 5432
        if not self.cfg.charset:
            self.cfg.charset = 'utf8'
        super()._validate_and_prepare_cfg()

    def _default_converters(self) -> Dict[type, Callable[[Any], Any]]:
        # psycopg2 将 NUMERIC/DECIMAL 列默认映射为 decimal.Decimal，
        # 默认转 float，以适配 JSON 序列化等不原生支持 Decimal 的场景。
        return {Decimal: float}

    def get_driver(self):
        return modutil.import_module('psycopg2', 'psycopg2')

    def build_connect_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            'host': self.cfg.host,
            'port': self.cfg.port,
            'user': self.cfg.username,
            'password': self.cfg.password,
            'database': self.cfg.database,
        }
        if self.cfg.charset:
            # psycopg2 不支持 charset 参数，通过 client_encoding 设置
            kwargs['client_encoding'] = self.cfg.charset
        return kwargs
