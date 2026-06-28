"""百宝，方便好用的Python常用功能库。"""

from baibao.base import pip, log, util
from baibao import db
from baibao.db import DbCfg, DbPool
from baibao.message import email
from baibao.message.email import EmailCfg, EmailClient, EmailSendResult

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

