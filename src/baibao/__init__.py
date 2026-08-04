"""
百宝 — 方便好用的 Python 常用功能库。

把日常开发中反复用到的能力封装成简洁的 API，开箱即用。
涵盖日志、包管理、数据库、消息发送、文字识别等常用场景。
"""

from pykunlun.envinfo import pkginfo

from baibao.ai import llm, ocr
from baibao.ai.llm import ChatMessage, ChatResponse, LlmCfg, LlmService, OpenAiLlm
from baibao.ai.ocr import EasyOcr, OcrResult, OcrService, PaddleOcr
from baibao.data import Field, Style, currency
from baibao.db import RdbCfg, rdb, rdb_mgr
from baibao.message import email
from baibao.message.email import EmailCfg, EmailClient, EmailSendResult
from baibao.render import Jinja2Engine, TemplateEngine, html, template

# 不捕获 PackageNotFoundError：能执行到此处说明包已加载，版本缺失应报错而非静默回退
__version__ = pkginfo.get_package_version("baibao")


__all__ = [
    "ChatMessage",
    "ChatResponse",
    "EasyOcr",
    "EmailCfg",
    "EmailClient",
    "EmailSendResult",
    "Field",
    "Jinja2Engine",
    "LlmCfg",
    "LlmService",
    "OcrResult",
    "OcrService",
    "OpenAiLlm",
    "PaddleOcr",
    "RdbCfg",
    "Style",
    "TemplateEngine",
    "currency",
    "email",
    "html",
    "llm",
    "ocr",
    "rdb",
    "rdb_mgr",
    "template",
]
