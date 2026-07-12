"""
环境相关工具函数。
"""

import inspect
import sys
from importlib.metadata import version


def get_python_executable() -> str:
    """
    获取当前 Python 解释器的可执行文件路径。
    """
    return sys.executable


def get_current_module_name() -> str:
    """
    获取当前模块的顶级包名。
    """
    # 获取当前模块的顶级包名
    # 如果当前模块没有顶级包名，返回空字符串
    return (__package__ or "").split('.')[0]


def get_caller_module_name() -> str:
    """
    获取调用者的顶级包名（跳过baibao内部调用）。
    """
    # 获取当前模块的顶级包名
    current_module = get_current_module_name()
    # 遍历调用栈，找到第一个不是baibao内部调用的模块
    for frame_info in inspect.stack():
        # 获取当前帧的模块名
        module = frame_info.frame.f_globals.get('__package__')
        # 检查是否是baibao内部调用
        if module and not module.startswith(current_module):
            return module.split('.')[0]
    # 如果没有找到不是baibao内部调用的模块，返回当前模块的顶级包名
    return current_module


def get_package_version(package_name: str) -> str:
    """
    获取指定包的版本号。

    包未安装时直接抛出 PackageNotFoundError，不做静默回退。
    如果包代码能被执行（如 __init__.py），说明包已加载，
    若 metadata 仍找不到则说明安装有问题，报错有助于定位。

    Args:
        package_name: 包名

    Returns:
        包的版本号

    Raises:
        PackageNotFoundError: 包未安装时抛出
    """
    return version(package_name)

