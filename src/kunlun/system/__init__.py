"""
系统级底层能力模块。

提供与操作系统相关的通用抽象（策略接口与注册表），具体平台实现由上层包提供并注册。
"""

from . import env_var
from .env_var import (
    SCOPE_SYSTEM,
    SCOPE_USER,
    EnvVarManager,
    EnvVarService,
)

__all__ = [
    'SCOPE_SYSTEM',
    'SCOPE_USER',
    'EnvVarManager',
    'EnvVarService',
    'env_var',
]
