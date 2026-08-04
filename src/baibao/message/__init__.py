"""
消息发送工具模块。

提供统一的消息发送接口，支持多种消息渠道。
"""

from . import email
from .email import EmailCfg, EmailClient, EmailSendResult

__all__ = [
    'EmailCfg',
    'EmailClient',
    'EmailSendResult',
    'email',
]