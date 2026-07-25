"""
EasyOCR 策略实现模块。

基于 EasyOCR 库提供本地 OCR 能力，支持 80+ 种语言。
图片加载、文本清洗与结果绘制等通用流程由 :class:`OcrService` 基类统一处理，
本模块仅负责调用引擎并将结果映射为 :class:`OcrResult`。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

from baibao.base import pip

from ._ocr import OcrResult, OcrService


class EasyOcr(OcrService):
    """
    基于 EasyOCR 库的本地 OCR 策略实现。

    EasyOCR 是基于 PyTorch 的开源 OCR 库，支持 80+ 种语言。
    本实现提供完整的本地文字识别能力，无需联网即可运行。

    特性:
        - 支持多语言识别，默认支持简体中文和英文
        - 支持 GPU 加速（需 CUDA 环境）
        - 自动下载和管理模型文件（首次使用约 1GB）

    依赖:
        - easyocr: 核心 OCR 引擎
        - opencv-python: 图像处理
        - torch: 深度学习框架（easyocr 依赖）

    示例::

        from baibao.ai.ocr.easy_ocr import EasyOcr

        # 默认配置（中文 + 英文）
        ocr = EasyOcr()

        # 多语言 + GPU 加速
        ocr = EasyOcr(langs=['ch_sim', 'en', 'ja'], gpu=True)
    """

    def __init__(
        self,
        langs: list[str] | None = None,
        gpu: bool = False,
        model_storage_directory: str | None = None,
    ) -> None:
        """
        初始化 EasyOCR 策略。

        Args:
            langs: 识别语言列表，默认为 ``['ch_sim', 'en']``（简体中文和英文）。
                   支持的语言代码参考 EasyOCR 官方文档，如 ``'ja'``（日语）、``'ko'``（韩语）。
            gpu: 是否启用 GPU 加速，需要安装 CUDA 和 cuDNN 环境。
            model_storage_directory: 模型文件存储目录，默认在用户主目录下的 ``.EasyOCR`` 文件夹。
                                     可指定自定义路径避免重复下载。

        Raises:
            ImportError: 当 easyocr 库未安装且自动安装失败时抛出。
        """
        try:
            import easyocr
        except ImportError:
            success, msg = pip.install('easyocr')
            if not success:
                raise ImportError(
                    f"easyocr 库未安装，自动安装失败: {msg}\n"
                    "请手动运行: pip install easyocr"
                )
            import easyocr

        self._langs: list[str] = langs if langs else ['ch_sim', 'en']
        self._gpu: bool = gpu
        self._reader = easyocr.Reader(
            lang_list=self._langs,
            gpu=self._gpu,
            model_storage_directory=model_storage_directory,
        )

    @property
    def langs(self) -> list[str]:
        """获取当前配置的语言代码列表，如 ``['ch_sim', 'en']``。"""
        return self._langs

    @property
    def gpu_enabled(self) -> bool:
        """获取是否启用 GPU 加速。``True`` 表示启用，``False`` 表示使用 CPU。"""
        return self._gpu

    def _recognize_array(self, image: np.ndarray) -> list[OcrResult]:
        """
        调用 EasyOCR 识别图像数组。

        EasyOCR 的返回结构为 ``[(bbox, text, confidence), ...]``，
        这里仅做格式映射，文本清洗与空白过滤由基类统一处理。

        Args:
            image: OpenCV 图像数组（BGR 格式）。

        Returns:
            :class:`OcrResult` 对象列表。
        """
        result = self._reader.readtext(image)
        return [
            OcrResult(
                text=text,
                bbox=bbox,
                confidence=float(confidence),
            )
            for bbox, text, confidence in result
        ]
