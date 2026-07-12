"""
百宝 — 方便好用的 Python 常用功能库。

把日常开发中反复用到的能力封装成简洁的 API，开箱即用。
涵盖日志、包管理、数据库、消息发送、文字识别等常用场景。
"""

from baibao.base import env, file, log, pip, time, util, validate
from baibao.base import Command, HelpCommand, CommandNotFoundError, CommandService
from baibao.data import currency
from baibao.db import sql, DbCfg, DbClient
from baibao.message import email
from baibao.message.email import EmailCfg, EmailClient, EmailSendResult


# 不捕获 PackageNotFoundError：能执行到此处说明包已加载，版本缺失应报错而非静默回退
__version__ = env.get_package_version(env.get_current_module_name())


__all__ = [
    'env', 'file', "log", "pip", "time", "util", "validate",
    "Command", "HelpCommand", "CommandNotFoundError", "CommandService",
    "currency",
    "sql",
    "DbCfg",
    "DbClient",
    "email",
    "EmailCfg",
    "EmailClient",
    "EmailSendResult",
]
