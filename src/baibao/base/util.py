"""
工具模块

提供通用的工具方法。
"""

import importlib
from dataclasses import fields, MISSING
from pathlib import Path
from typing import TypeVar, Type, Any, Optional

from baibao.base import pip
from baibao.base import log


# 定义类型变量 T，用于表示 dataclass 配置类的实例类型
T = TypeVar('T')


def import_module(module_name: str, install_name: Optional[str] = None):
    """
    动态导入模块，模块未安装时自动安装
    Args:
        module_name: 要导入的模块名（必填）
        install_name: 安装包名称（可选）。若为 None，则使用 module_name 作为安装包名
    Returns:
        模块对象
    Raises:
        ImportError: 模块安装失败
    """
    # 如果未指定安装包名，则使用模块名
    if install_name is None:
        install_name = module_name
    # 尝试导入模块
    try:
        log.info(f"正在导入模块 {module_name}")
        return importlib.import_module(module_name)
    except ImportError:
        log.warn(f"模块 {module_name} 未安装，开始安装 {install_name}")
        # 尝试安装模块
        success, msg = pip.install(install_name)
        if not success:
            raise ImportError(f"安装 {install_name} 失败: {msg}")
        # 安装成功后，重新导入模块
        log.info(f"{install_name} 安装成功，重新导入 {module_name}")
        return importlib.import_module(module_name)


def load_dataclass_from_json_file(file_path: str | Path, data_class: Type[T]) -> T:
    """
    从 JSON 文件加载 dataclass 实例对象

    读取指定路径的 JSON 文件，自动校验 dataclass 的必填字段后返回实例对象。
    适用于所有使用 dataclass 定义的类。

    Args:
        file_path: 配置文件路径，可以是字符串或 Path 对象
        data_class: dataclass 类类型

    Returns:
        dataclass 实例对象

    Raises:
        FileNotFoundError: 文件不存在时抛出
        ValueError: 文件缺少必填字段时抛出
        json.JSONDecodeError: JSON 格式解析失败时抛出
    """
    # 导入 JSON 模块
    import json
    # 确保 file_path 是 Path 对象，检查文件是否存在
    log.info(f"加载文件: {file_path}")
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    # 读取 JSON 文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        data: dict[str, Any] = json.load(f)
    # 利用 dataclass 的 fields 自动校验必填字段
    required = {f.name for f in fields(data_class) if f.default is MISSING} # type: ignore[arg-type]
    missing = required - data.keys()
    if missing:
        raise ValueError(f"{data_class.__name__} 缺少字段: {', '.join(sorted(missing))}")
    # 返回 dataclass 实例对象
    return data_class(**data)

