"""OCR 模块，提供多种 OCR 策略实现。

示例::

    from baibao.ai.ocr import recognize, set_ocr_service
    from baibao.ai.ocr.paddle_ocr import PaddleOcr

    # 1. 直接使用默认提供者（EasyOcr）
    text = recognize("image.png")
    print(text)

    # 2. 动态切换为 PaddleOcr
    set_ocr_service("paddle", PaddleOcr())

    # 3. 使用指定的 OCR 服务
    from baibao.ai.ocr import get_ocr_service
    ocr = get_ocr_service("paddle")
    text = ocr.recognize("image.png")

    # 4. 获取详细结果（含位置、置信度）
    from baibao.ai.ocr import recognize_with_details
    for item in recognize_with_details("image.png"):
        print(f"文本: {item['text']}, 置信度: {item['confidence']:.2f}")

    # 5. 绘制边界框并保存结果图
    from baibao.ai.ocr import recognize_and_draw
    img = recognize_and_draw("image.png", output_path="result.png")
"""

from ._ocr import (  # noqa: F401
    OcrResult,
    OcrService,
    get_ocr_service,
    set_ocr_service,
    remove_ocr_service,
    recognize,
    recognize_with_details,
    recognize_and_draw,
)
from .easy_ocr import EasyOcr  # noqa: F401
from .paddle_ocr import PaddleOcr  # noqa: F401


__all__ = [
    'OcrResult',
    'OcrService',
    'EasyOcr',
    'PaddleOcr',
    'get_ocr_service',
    'set_ocr_service',
    'remove_ocr_service',
    'recognize',
    'recognize_with_details',
    'recognize_and_draw',
]
