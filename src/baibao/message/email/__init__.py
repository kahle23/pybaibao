"""
邮件模块，支持多配置管理。

提供邮件服务器配置管理和邮件发送功能，适用于需要管理多个邮件服务器配置的场景。
通过 ``set_client`` 注册不同邮件服务器配置，再通过 ``send_text``、``send_html`` 等方法快速发送邮件。

主要功能：
- 支持多个邮件服务器配置管理
- 支持纯文本和HTML格式邮件发送
- 支持附件发送
- 支持字典和配置对象两种配置方式
"""

from ._email import (
    get_client,
    set_client,
    remove_client,
    clear,
    send,
    send_text,
    send_html,
)
from .email_client import EmailCfg, EmailSendResult, EmailClient

__all__ = [
    "get_client",
    "set_client",
    "remove_client",
    "clear",
    "send",
    "send_text",
    "send_html",
    "EmailCfg",
    "EmailSendResult",
    "EmailClient",
]
