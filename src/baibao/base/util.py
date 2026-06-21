"""
工具模块

提供通用的工具方法和类。
"""

import importlib
from datetime import datetime

from .pip_util import PipUtil


class Log:
    """日志工具类"""

    LOG_COLORS = {
        "INFO ": "\033[92m",  # 绿色
        "WARN ": "\033[93m",  # 黄色
        "ERROR": "\033[91m",  # 红色
        "USAGE": "\033[94m",  # 蓝色
        "RESET": "\033[0m",   # 重置颜色
    }

    @staticmethod
    def _log(level, msg, show_log=True):
        """一个简单的、带级别和时间的基于 print 的日志输出"""
        if show_log:
            color = Log.LOG_COLORS.get(level, Log.LOG_COLORS["RESET"])
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{color}[{level}]{Log.LOG_COLORS['RESET']} {timestamp} - {msg}"
            )

    @staticmethod
    def info(msg, show_log=True):
        Log._log("INFO ", msg, show_log)

    @staticmethod
    def warn(msg, show_log=True):
        Log._log("WARN ", msg, show_log)

    @staticmethod
    def error(msg, show_log=True):
        Log._log("ERROR", msg, show_log)

    @staticmethod
    def usage(msg, show_log=True):
        Log._log("USAGE", msg, show_log)


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
            Log.info(f"正在导入模块 {module_name}")
            return importlib.import_module(module_name)
        except ImportError:
            Log.warn(f"模块 {module_name} 未安装，开始安装 {install_name}")
            success, msg = PipUtil.install(install_name)
            if not success:
                raise ImportError(f"安装 {install_name} 失败: {msg}")
            Log.info(f"{install_name} 安装成功，重新导入 {module_name}")
            return importlib.import_module(module_name)
