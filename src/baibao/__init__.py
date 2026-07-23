"""
百宝 — 方便好用的 Python 常用功能库。

把日常开发中反复用到的能力封装成简洁的 API，开箱即用。
涵盖日志、包管理、数据库、消息发送、文字识别等常用场景。
"""

from baibao.base import action, attr, cli, env, file, log, pip, time, util, validate
from baibao.base import Command, HelpCommand, CommandNotFoundError, CommandService
from baibao.data import template, currency
from baibao.data import TemplateEngine, Jinja2Engine
from baibao.data import Style, Field
from baibao.db import sql, DbCfg, DbClient
from baibao.message import email
from baibao.message.email import EmailCfg, EmailClient, EmailSendResult
from baibao.ai import llm
from baibao.ai.llm import LlmCfg, ChatMessage, ChatResponse, LlmService
from baibao.ai import ocr
from baibao.ai.ocr import OcrService, EasyOcr, PaddleOcr


# 不捕获 PackageNotFoundError：能执行到此处说明包已加载，版本缺失应报错而非静默回退
__version__ = env.get_package_version(env.get_current_module_name())


__all__ = [
    "llm",
    "LlmCfg", "ChatMessage", "ChatResponse", "LlmService",
    'action', 'attr', 'cli', 'env', 'file', "log", "pip", "time", "util", "validate",
    "Command", "HelpCommand", "CommandNotFoundError", "CommandService",
    "template", "currency",
    "TemplateEngine", "Jinja2Engine",
    "Style", "Field",
    "sql",
    "DbCfg",
    "DbClient",
    "email",
    "EmailCfg",
    "EmailClient",
    "EmailSendResult",
    "ocr",
    "OcrService",
    "EasyOcr",
    "PaddleOcr",
]
