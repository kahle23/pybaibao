"""
百宝 — 方便好用的 Python 常用功能库。

把日常开发中反复用到的能力封装成简洁的 API，开箱即用。
涵盖日志、包管理、数据库、消息发送、文字识别等常用场景。
"""

from kunlun.base import action, attr, log, time, util, validate
from kunlun.system import env

from baibao.ai import llm, ocr
from baibao.ai.llm import ChatMessage, ChatResponse, LlmCfg, LlmService, OpenAiLlm
from baibao.ai.ocr import EasyOcr, OcrResult, OcrService, PaddleOcr
from baibao.base import (
    Command,
    CommandNotFoundError,
    CommandService,
    HelpCommand,
    cli,
    file,
)
from baibao.data import Field, Jinja2Engine, Style, TemplateEngine, currency, template
from baibao.db import DbCfg, DbClient, sql
from baibao.message import email
from baibao.message.email import EmailCfg, EmailClient, EmailSendResult

# 不捕获 PackageNotFoundError：能执行到此处说明包已加载，版本缺失应报错而非静默回退
__version__ = env.get_package_version("baibao")


__all__ = [
    "ChatMessage",
    "ChatResponse",
    "Command",
    "CommandNotFoundError",
    "CommandService",
    "DbCfg",
    "DbClient",
    "EasyOcr",
    "EmailCfg",
    "EmailClient",
    "EmailSendResult",
    "Field",
    "HelpCommand",
    "Jinja2Engine",
    "LlmCfg",
    "LlmService",
    "OcrResult",
    "OcrService",
    "OpenAiLlm",
    "PaddleOcr",
    "Style",
    "TemplateEngine",
    'action',
    'attr',
    'cli',
    "currency",
    "email",
    'file',
    "llm",
    "log",
    "ocr",
    "sql",
    "template",
    "time",
    "util",
    "validate",
]
