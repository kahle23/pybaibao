"""数据库连接工具模块。

提供统一的数据库操作接口，支持多种数据库类型（关系型数据库、Redis、向量数据库等）。
通过数据库配置名获取对应的客户端实例进行操作。

主要组件：
  - BaseCfg：数据库配置抽象基类
  - BaseClient：数据库客户端抽象基类
  - 模块级函数：统一管理客户端实例
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Any

from baibao.base import util



class BaseCfg(ABC):
    """
    数据库配置抽象基类

    所有数据库配置类都应继承此类，按需添加字段并覆盖 validate 方法。
    子类需定义 db_type 属性标识数据库类型（如 mysql、postgresql、redis、milvus 等）。
    """

    db_type: str

    def validate(self) -> bool:
        """
        验证配置是否有效（可选覆盖）

        基类提供默认实现，校验 db_type 不为空。子类可覆盖添加额外验证逻辑。

        Returns:
            配置有效返回 True

        Raises:
            ValueError: 配置无效时抛出
        """
        if not self.db_type or not self.db_type.strip():
            raise ValueError("数据库类型不能为空! ")
        return True

    @staticmethod
    def load_from_json_file(config_path: Union[str, Path], cfg_class=None):
        """
        从 JSON 文件加载配置

        Args:
            config_path: JSON 配置文件路径
            cfg_class: 配置类，默认为调用者的类

        Returns:
            配置实例
        """
        if cfg_class is None:
            cfg_class = BaseCfg
        return util.load_dataclass_from_json_file(config_path, cfg_class)


class BaseClient(ABC):
    """
    数据库客户端抽象基类

    所有数据库客户端（如 DbClient、RedisClient、VectorDbClient）都应继承此类。
    """

    @abstractmethod
    def get_connection(self) -> Any:
        """
        获取可用的数据库操作句柄

        不同实现返回不同的句柄类型：
        - 连接池客户端（如 DbClient）：返回一个独立的数据库连接，使用后需 close 归还
        - 自管理客户端（如 Redis、向量数据库）：返回客户端实例本身，连接由内部维护

        Returns:
            数据库操作句柄
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        关闭连接或客户端
        """
        pass

    @abstractmethod
    def ping(self) -> bool:
        """
        测试连接是否有效

        Returns:
            连接有效返回 True
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

