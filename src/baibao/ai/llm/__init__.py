"""
LLM 模块，提供多种大语言模型策略实现。

采用策略模式设计，支持 OpenAI、DeepSeek 等多种 LLM 服务商的无缝切换，
提供统一的对话接口（单轮、多轮、流式输出）和模块级服务管理。
"""

from ._llm import (
    LlmCfg,
    ChatMessage,
    ChatResponse,
    LlmService,
    get_llm_service,
    set_llm_service,
    remove_llm_service,
    chat,
    stream_chat,
)
from .openai_llm import OpenAiLlm


__all__ = [
    'LlmCfg',
    'ChatMessage',
    'ChatResponse',
    'LlmService',
    'get_llm_service',
    'set_llm_service',
    'remove_llm_service',
    'chat',
    'stream_chat',
    'OpenAiLlm',
]
