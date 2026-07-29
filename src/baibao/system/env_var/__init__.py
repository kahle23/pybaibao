"""
环境变量管理模块。

提供基于策略模式的环境变量管理能力，支持 Windows、Unix-like
（Linux、macOS、BSD 等）平台。

抽象接口与平台注册表位于 :mod:`kunlun.system.env_var`
（:class:`~kunlun.system.env_var.EnvVarService` /
:class:`~kunlun.system.env_var.EnvVarManager`）；本模块在包导入时实例化
:class:`~kunlun.system.env_var.EnvVarManager`，注册 Windows / Unix 的具体实现，
并通过 :data:`env_var_manager` 对外暴露。调用方据此获取当前平台的服务实例。

用法示例::

    from baibao.system.env_var import env_var_manager

    svc = env_var_manager.get_service()        # 按当前系统自动选择
    svc = env_var_manager.get_service("unix")  # 显式指定平台

    svc.set_var("FOO", "bar")
    print(svc.get_var("FOO"))
    svc.append_to_path("/some/path")
"""

import kunlun.system as _kunlun

from .unix_env import UnixEnvService
from .windows_env import WindowsEnvService

# 平台服务管理器实例（注册表为实例属性）：注册 Windows / Unix 具体实现后对外提供。
# 通过模块别名引用 EnvVarManager，避免该类名泄漏到本包命名空间（彻底迁移）。
env_var_manager = _kunlun.EnvVarManager()
env_var_manager.register_service("windows", WindowsEnvService())
env_var_manager.register_service("unix", UnixEnvService())

__all__ = [
    'env_var_manager',
]
