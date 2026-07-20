"""
SQL 数据库操作模块。

提供统一的数据库操作接口。
通过数据库配置名获取对应的 DbClient 实例进行操作。
"""

from typing import Dict, Optional, Tuple, Any, List, Union
from decimal import Decimal
import threading

from baibao.base import log
from baibao.base import mod
from .db_client import DbCfg, DbClient


# 存储不同配置名对应的 DbClient 实例
_clients: Dict[str, DbClient] = {}
_clients_lock = threading.RLock()

# 默认配置名
DEFAULT_CFG_NAME = "default"

# 数据库驱动映射表：db_type -> (模块名, pip 包名)
_DRIVER_MAP = {
    'mysql': ('pymysql', 'pymysql'),
    'postgresql': ('psycopg2', 'psycopg2'),
}


def get_driver(db_type: str):
    """
    获取数据库驱动模块

    根据数据库类型动态导入对应的数据库驱动模块，如未安装则自动安装。

    Args:
        db_type: 数据库类型（mysql、postgresql）

    Returns:
        数据库驱动模块

    Raises:
        ValueError: 不支持的数据库类型
        ImportError: 驱动模块安装失败
    """
    # 从映射表中获取驱动模块信息
    driver_tuple = _DRIVER_MAP.get(db_type.lower())
    # 如果映射表中没有对应的驱动模块信息，抛出异常
    if not driver_tuple:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    # 导入驱动模块 
    module_name, install_name = driver_tuple
    return mod.import_module(module_name, install_name)


def get_client(cfg_name: Optional[str] = None):
    """
    获取指定配置名对应的 DbClient 实例

    对于默认配置名，如果尚未设置，会自动从 ./db.config 文件加载配置并初始化客户端。

    Args:
        cfg_name: 数据库配置名，如果不传则使用默认配置名

    Returns:
        DbClient 实例

    Raises:
        KeyError: 指定的配置名对应的 DbClient 不存在时抛出
    """
    # 如果未指定配置名，使用默认配置名
    if not cfg_name:
        cfg_name = DEFAULT_CFG_NAME
    # 使用锁保护全局字典的访问
    with _clients_lock:
        # 如果配置名不存在，并且是默认配置名，尝试从 ./db.config 加载配置
        if cfg_name not in _clients:
            if cfg_name == DEFAULT_CFG_NAME:
                try:
                    cfg = DbCfg.load_from_json_cfg("./db.config")
                    set_client(cfg_name, cfg)
                except FileNotFoundError as e:
                    raise KeyError("自动加载默认配置失败: 找不到配置文件 './db.config'") from e
                except ValueError as e:
                    raise KeyError(f"自动加载默认配置失败: 配置格式错误 - {e}") from e
                except Exception as e:
                    raise KeyError(f"自动加载默认配置失败: {e}") from e
            else:
                raise KeyError(f"未找到配置名 '{cfg_name}' 对应的 DbClient，请先调用 set_client() 设置")
        # 返回对应的 DbClient 实例
        return _clients[cfg_name]


def set_client(cfg_name: str, db_client: Union[DbClient, DbCfg]) -> None:
    """
    设置指定配置名对应的 DbClient 或 DbCfg

    如果传入 DbCfg，会自动创建 DbClient 实例。

    Args:
        cfg_name: 数据库配置名
        db_client: DbClient 实例或 DbCfg 配置对象
    """
    # 如果未指定配置名，使用默认配置名
    if not cfg_name:
        cfg_name = DEFAULT_CFG_NAME
    # 使用锁保护全局字典的访问
    with _clients_lock:
        # 设置对应的 DbClient 实例
        if isinstance(db_client, DbClient):
            _clients[cfg_name] = db_client
        elif isinstance(db_client, DbCfg):
            _clients[cfg_name] = DbClient(db_client)
        else:
            raise TypeError(f"db_client 必须是 DbClient 或 DbCfg 类型，实际类型: {type(db_client)}")


def remove_client(cfg_name: Optional[str] = None):
    """
    移除指定配置名对应的 DbClient

    Args:
        cfg_name: 数据库配置名，如果不传则移除默认配置名
    """
    # 如果未指定配置名，使用默认配置名
    if not cfg_name:
        cfg_name = DEFAULT_CFG_NAME
    # 使用锁保护全局字典的访问
    with _clients_lock:
        # 如果配置名存在，先关闭客户端再移除
        if cfg_name in _clients:
            try:
                _clients[cfg_name].close()
            except Exception:
                pass
            del _clients[cfg_name]


def get_connection(cfg_name: Optional[str] = None):
    """
    获取数据库连接

    通过指定的数据库配置名获取对应的 DbClient，并返回连接。
    注意：此连接在使用后必须手动关闭并归还到连接池。

    Args:
        cfg_name: 数据库配置名，如果不传则使用默认配置名

    Returns:
        数据库连接实例
    """
    client = get_client(cfg_name)
    return client.get_connection()


def close(cfg_name: Optional[str] = None):
    """
    关闭数据库客户端

    通过指定的数据库配置名获取对应的 DbClient，并关闭整个客户端。
    注意：这会关闭整个连接池，后续获取连接会重新初始化。

    Args:
        cfg_name: 数据库配置名，如果不传则使用默认配置名
    """
    client = get_client(cfg_name)
    client.close()


def clear():
    """
    清空所有数据库客户端。
    调用后需重新通过 set_client() 初始化客户端。
    """
    with _clients_lock:
        for client in _clients.values():
            try:
                client.close()
            except Exception:
                pass
        _clients.clear()


def execute(sql: str, params: Optional[Tuple[Any, ...]] = None, cfg_name: Optional[str] = None) -> int:
    """
    执行 SQL 语句（自动管理连接生命周期）

    自动提交事务，适用于 INSERT、UPDATE、DELETE 等写操作。
    使用后会自动关闭连接并归还到连接池。

    Args:
        sql: SQL 语句字符串
        params: SQL 参数，用于参数化查询，防止 SQL 注入
        cfg_name: 数据库配置名，如果不传则使用默认配置名

    Returns:
        int: 受影响的行数
    """
    connection = get_connection(cfg_name)
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        connection.commit()
        return int(cursor.rowcount)
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        connection.close()


def query(
    sql: str,
    params: Optional[Tuple[Any, ...]] = None,
    cfg_name: Optional[str] = None,
    to_float: bool = False,
) -> List[Dict]:
    """
    执行查询并返回结果（自动管理连接生命周期）

    适用于 SELECT 等读操作，返回查询结果列表。
    使用后会自动关闭连接并归还到连接池。

    Args:
        sql: SQL 查询语句字符串
        params: SQL 参数，用于参数化查询，防止 SQL 注入
        cfg_name: 数据库配置名，如果不传则使用默认配置名
        to_float: 是否将 Decimal 类型转换为 float，默认为 False

    Returns:
        list[dict]: 查询结果列表，每个元素是一个字典，键为列名
    """
    connection = None
    cursor = None
    try:
        connection = get_connection(cfg_name)
        cursor = connection.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        # 处理空结果集
        if not rows:
            return []
        # 处理字典格式结果
        if isinstance(rows[0], dict):
            result = [
                {
                    k: float(v) if (to_float and isinstance(v, Decimal)) else v
                    for k, v in row.items()
                }
                for row in rows
            ]
            return result
        # 从 cursor.description 获取列名（适用于 psycopg2 等返回元组的驱动）
        cols = [desc[0] for desc in cursor.description] if cursor.description else None
        # 无法获取列名描述
        if cols is None:
            log.warn("无法获取列名描述，将使用位置索引 field_0, field_1...")
        # 处理结果集
        result = []
        for row in rows:
            if cols:
                d = dict(zip(cols, row))
            else:
                d = {f'field_{i}': v for i, v in enumerate(row)}
            result.append(
                {
                    k: float(v) if (to_float and isinstance(v, Decimal)) else v
                    for k, v in d.items()
                }
            )
        return result
    except Exception as e:
        log.error(f"Database query failed: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

