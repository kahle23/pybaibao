"""LLM 模块，提供多种大语言模型策略实现。"""

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
