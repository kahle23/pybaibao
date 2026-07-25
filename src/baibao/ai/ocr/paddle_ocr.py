"""
PaddleOCR 策略实现模块。

基于 PaddleOCR 库提供本地高精度 OCR 能力。
图片加载、文本清洗与结果绘制等通用流程由 :class:`OcrService` 基类统一处理，
本模块仅负责调用引擎并将结果映射为 :class:`OcrResult`。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

from baibao.base import pip

from ._ocr import OcrResult, OcrService


class PaddleOcr(OcrService):
    """
    基于 PaddleOCR 的本地 OCR 策略实现。

    PaddleOCR 是百度飞桨推出的开源 OCR 工具库，具有高精度、高性能的特点。
    本实现提供完整的本地文字识别能力，无需联网即可运行。

    特性:
        - 支持中英文等多种语言识别
        - 内置角度分类器，支持倾斜文本识别
        - 基于 PaddlePaddle 深度学习框架

    依赖:
        - paddleocr: 核心 OCR 引擎（含 PaddlePaddle）
        - opencv-python: 图像处理

    示例::

        from baibao.ai.ocr.paddle_ocr import PaddleOcr

        # 默认配置（中英文）
        ocr = PaddleOcr()

        # 英文识别 + 禁用角度分类器（更快）
        ocr = PaddleOcr(lang='en', use_angle_cls=False)
    """

    def __init__(
        self,
        use_angle_cls: bool = True,
        lang: str = 'ch',
    ) -> None:
        """
        初始化 PaddleOCR 策略。

        Args:
            use_angle_cls: 是否启用角度分类器，用于识别旋转文本（如倒置、倾斜的文字）。
                           启用后可提高倾斜文本的识别准确率，但会增加少量计算开销。
                           该配置同时作用于模型加载与识别调用，保持行为一致。
            lang: 识别语言，默认为 ``'ch'``（中英文混合）。
                  支持的语言代码包括: ``'ch'``（中英）、``'en'``（英文）、``'ja'``（日文）等。

        Raises:
            ImportError: 当 paddleocr 库未安装且自动安装失败时抛出。

        Note:
            首次使用时会自动下载预训练模型，约 100MB-500MB，取决于语言配置。
        """
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            success, msg = pip.install('paddleocr')
            if not success:
                raise ImportError(
                    f"paddleocr 库未安装，自动安装失败: {msg}\n"
                    "请手动运行: pip install paddleocr"
                )
            from paddleocr import PaddleOCR

        self._lang: str = lang
        self._use_angle_cls: bool = use_angle_cls
        self._ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)

    @property
    def lang(self) -> str:
        """获取当前配置的语言代码，如 ``'ch'``（中英）、``'en'``（英文）。"""
        return self._lang

    @property
    def use_angle_cls(self) -> bool:
        """获取是否启用角度分类器。"""
        return self._use_angle_cls

    def _recognize_array(self, image: np.ndarray) -> list[OcrResult]:
        """
        调用 PaddleOCR 识别图像数组。

        PaddleOCR 的返回结构为 ``[[[bbox, [text, confidence]], ...]]``：
        外层列表表示页面，内层列表表示识别到的文本行。
        这里仅做格式映射，文本清洗与空白过滤由基类统一处理。

        Args:
            image: OpenCV 图像数组（BGR 格式）。

        Returns:
            :class:`OcrResult` 对象列表。
        """
        result = self._ocr.ocr(image, cls=self._use_angle_cls)
        if not result or not result[0]:
            return []

        return [
            OcrResult(
                text=line[1][0],
                bbox=line[0],
                confidence=float(line[1][1]),
            )
            for line in result[0]
        ]
