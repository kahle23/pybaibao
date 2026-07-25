"""
OCR 模块，提供多种 OCR 策略实现。

采用策略模式（结合模板方法）设计：基类 :class:`OcrService` 统一负责图片
加载、文本清洗与结果绘制，子类只需实现核心识别方法，专注于引擎适配。
支持 EasyOCR、PaddleOCR 等多种实现的运行时切换，并提供模块级服务管理。
"""

from ._ocr import (
    OcrResult,
    OcrService,
    get_ocr_service,
    recognize,
    recognize_and_draw,
    recognize_with_details,
    remove_ocr_service,
    set_ocr_service,
)
from .easy_ocr import EasyOcr
from .paddle_ocr import PaddleOcr

__all__ = [
    'EasyOcr',
    'OcrResult',
    'OcrService',
    'PaddleOcr',
    'get_ocr_service',
    'recognize',
    'recognize_and_draw',
    'recognize_with_details',
    'remove_ocr_service',
    'set_ocr_service',
]
