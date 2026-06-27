"""
工具模块

提供通用的工具方法和类。
"""

import importlib

from baibao.base import pip
from baibao.base import log


class Util:
    """模块导入工具类"""

    @staticmethod
    def import_module(module_name: str, install_name: str = None):
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
        if install_name is None:
            install_name = module_name

        try:
            log.info(f"正在导入模块 {module_name}")
            return importlib.import_module(module_name)
        except ImportError:
            log.warn(f"模块 {module_name} 未安装，开始安装 {install_name}")
            success, msg = pip.install(install_name)
            if not success:
                raise ImportError(f"安装 {install_name} 失败: {msg}")
            log.info(f"{install_name} 安装成功，重新导入 {module_name}")
            return importlib.import_module(module_name)
