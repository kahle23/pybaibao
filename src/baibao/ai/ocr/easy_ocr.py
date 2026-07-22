from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List, Tuple, Union
import os

if TYPE_CHECKING:
    import numpy as np

from ._ocr import OcrService, OcrResult
from baibao.base import pip


class EasyOcr(OcrService):
    """基于 EasyOCR 库的本地 OCR 策略实现。

    EasyOCR 是一个基于 PyTorch 的开源 OCR 库，支持 80+ 种语言的文字识别。
    本实现提供完整的本地文字识别能力，无需联网即可运行。

    特性:
        - 支持多语言识别，默认支持简体中文和英文
        - 支持 GPU 加速（需 CUDA 环境）
        - 自动下载和管理模型文件（首次使用约 1GB）
        - 提供详细的识别结果（位置、置信度）

    依赖:
        - easyocr: 核心 OCR 引擎
        - opencv-python: 图像处理
        - torch: 深度学习框架（easyocr 依赖）
    """

    def __init__(
        self,
        langs: Optional[List[str]] = None,
        gpu: bool = False,
        model_storage_directory: Optional[str] = None,
    ) -> None:
        """初始化 EasyOCR 策略。

        Args:
            langs: 识别语言列表，默认为 ['ch_sim', 'en']（简体中文和英文）。
                   支持的语言代码参考 easyocr 官方文档，如 'ja'（日语）、'ko'（韩语）等。
            gpu: 是否启用 GPU 加速，需要安装 CUDA 和 cuDNN 环境。
                 启用 GPU 可显著提升识别速度，但需要 NVIDIA 显卡支持。
            model_storage_directory: 模型文件存储目录，默认在用户主目录下的 .EasyOCR 文件夹。
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

        self._langs: List[str] = langs if langs else ['ch_sim', 'en']
        self._gpu: bool = gpu
        self._reader: easyocr.Reader = easyocr.Reader(
            lang_list=self._langs,
            gpu=self._gpu,
            model_storage_directory=model_storage_directory,
        )

    def _preprocess_image(self, image: Union[str, np.ndarray]) -> np.ndarray:
        """预处理图片，统一格式并验证有效性。

        将输入转换为 OpenCV 图像数组格式，确保后续识别流程的一致性。

        Args:
            image: 图片路径（字符串）或 OpenCV 图像数组（numpy.ndarray）。

        Returns:
            预处理后的 OpenCV 图像数组（BGR 格式）。

        Raises:
            FileNotFoundError: 当传入的图片路径不存在时抛出。
            ValueError: 当无法读取图片文件（文件损坏或格式不支持）时抛出。
        """
        import cv2

        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"图片文件不存在: {image}")
            img = cv2.imread(image)
        else:
            img = image

        if img is None:
            raise ValueError("无法读取图片文件，请检查文件是否损坏或格式是否支持")

        return img

    def recognize(self, image: Union[str, np.ndarray]) -> str:
        """识别图片中的文字，返回纯文本结果。

        Args:
            image: 图片路径（字符串）或 OpenCV 图像数组（numpy.ndarray）。

        Returns:
            识别出的文本内容，多行文本用换行符 `\n` 分隔，空白文本被过滤。
        """
        img = self._preprocess_image(image)
        result = self._reader.readtext(img)

        lines: List[str] = []
        for detection in result:
            text = detection[1]
            if text.strip():
                lines.append(text.strip())

        return '\n'.join(lines)

    def recognize_with_details(
        self, image: Union[str, np.ndarray]
    ) -> List[OcrResult]:
        """识别图片中的文字，返回包含位置和置信度的详细结果。

        Args:
            image: 图片路径（字符串）或 OpenCV 图像数组（numpy.ndarray）。

        Returns:
            :class:`OcrResult` 对象列表，空白文本会被过滤。
        """
        img = self._preprocess_image(image)
        result = self._reader.readtext(img)

        details: List[OcrResult] = []
        for detection in result:
            bbox, text, confidence = detection
            if text.strip():
                details.append(OcrResult(
                    text=text.strip(),
                    bbox=bbox,
                    confidence=confidence,
                ))

        return details

    def recognize_and_draw(
        self,
        image: Union[str, np.ndarray],
        output_path: Optional[str] = None,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """识别图片中的文字，并在图片上绘制边界框和文本标签。

        在原图上绘制识别结果：用多边形框标出文字位置，并在框上方显示识别出的文本。

        Args:
            image: 图片路径（字符串）或 OpenCV 图像数组（numpy.ndarray）。
            output_path: 输出图片保存路径，为 None 时仅返回图像数组不保存。
            color: 边界框和文本颜色，BGR 格式，默认为绿色 (0, 255, 0)。
            thickness: 边界框线条粗细，默认为 2 像素。

        Returns:
            绘制了边界框和文本标签的图像数组（BGR 格式）。
        """
        import cv2
        import numpy as np

        img = self._preprocess_image(image)
        result = self._reader.readtext(img)

        for detection in result:
            bbox = detection[0]
            text = detection[1]
            if not text.strip():
                continue

            # 绘制四边形边界框
            pts = np.array(bbox, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)

            # 在边界框上方绘制文本标签
            x, y = bbox[0][0], bbox[0][1] - 10
            cv2.putText(
                img,
                text,
                (int(x), int(y)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        # 保存结果图片（如果指定了路径）
        if output_path:
            cv2.imwrite(output_path, img)

        return img

    @property
    def langs(self) -> List[str]:
        """获取当前配置的语言列表。

        Returns:
            List[str]: 语言代码列表，如 ['ch_sim', 'en']。
        """
        return self._langs

    @property
    def gpu_enabled(self) -> bool:
        """获取是否启用 GPU 加速。

        Returns:
            bool: True 表示启用 GPU，False 表示使用 CPU。
        """
        return self._gpu
