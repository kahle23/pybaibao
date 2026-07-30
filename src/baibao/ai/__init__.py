"""
AI 能力模块。

提供人工智能相关能力，按子模块组织：

  - llm: 大语言模型对话（OpenAI 兼容）
  - ocr: 光学字符识别（EasyOCR / PaddleOCR）
"""

from baibao.ai import llm, ocr
from baibao.ai.llm import ChatMessage, ChatResponse, LlmCfg, LlmService, OpenAiLlm
from baibao.ai.ocr import EasyOcr, OcrResult, OcrService, PaddleOcr

__all__ = [
    'ChatMessage',
    'ChatResponse',
    'EasyOcr',
    'LlmCfg',
    'LlmService',
    'OcrResult',
    'OcrService',
    'OpenAiLlm',
    'PaddleOcr',
    'llm',
    'ocr',
]
