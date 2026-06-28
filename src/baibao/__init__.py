"""
百宝 — 方便好用的 Python 常用功能库。

把日常开发中反复用到的能力封装成简洁的 API，开箱即用。
涵盖日志、包管理、数据库、消息发送、文字识别等常用场景。
"""

from importlib.metadata import version, PackageNotFoundError

from baibao.base import pip, log, util
from baibao import db
from baibao.db import DbCfg, DbPool
from baibao.message import email
from baibao.message.email import EmailCfg, EmailClient, EmailSendResult


try:
    __version__ = version("baibao")
except PackageNotFoundError:
    __version__ = "0.0.1"


__all__ = [
    "pip",
    "log",
    "util",
    "db",
    "DbCfg",
    "DbPool",
    "email",
    "EmailCfg",
    "EmailClient",
    "EmailSendResult",
]

