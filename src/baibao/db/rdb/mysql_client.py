"""
MySQL 驱动客户端（pymysql，连接池）。

继承 :class:`~baibao.db.rdb.pooled_client.PooledRdbClient`，驱动模块由本类
通过 :func:`kunlun.modutil.import_module` 自行导入与按需安装。
"""

from decimal import Decimal
from typing import Any, Callable, Dict

from kunlun import modutil

from .pooled_client import PooledRdbClient


class MysqlRdbClient(PooledRdbClient):
    """MySQL 驱动客户端（pymysql，连接池）。"""

    db_type = 'mysql'

    def _validate_and_prepare_cfg(self) -> None:
        # MySQL 标准默认：端口 3306、字符集 utf8mb4；先填再交基类校验。
        if self.cfg.port is None:
            self.cfg.port = 3306
        if not self.cfg.charset:
            self.cfg.charset = 'utf8mb4'
        super()._validate_and_prepare_cfg()

    def _default_converters(self) -> Dict[type, Callable[[Any], Any]]:
        # pymysql 将 DECIMAL 列返回为 decimal.Decimal，默认转 float，
        # 以适配 JSON 序列化等不原生支持 Decimal 的场景。
        return {Decimal: float}

    def get_driver(self):
        return modutil.import_module('pymysql', 'pymysql')

    def build_connect_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            'host': self.cfg.host,
            'port': self.cfg.port,
            'user': self.cfg.username,
            'password': self.cfg.password,
            'database': self.cfg.database,
        }
        if self.cfg.charset:
            kwargs['charset'] = self.cfg.charset
        return kwargs
