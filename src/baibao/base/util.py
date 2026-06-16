"""
工具模块

提供通用的工具函数和类。
"""

import importlib

from .pip_util import PipUtil


class Util:

    @staticmethod
    def import_module(module_name: str, install_name: str):
        """
        动态导入模块，模块未安装时自动安装

        Args:
            module_name: 要导入的模块名
            install_name: 安装包名称

        Returns:
            模块对象

        Raises:
            ImportError: 模块安装失败
        """
        try:
            return importlib.import_module(module_name)
        except ImportError:
            success, msg = PipUtil.install(install_name)
            if not success:
                raise ImportError(f"安装 {install_name} 失败: {msg}")
            return importlib.import_module(module_name)

