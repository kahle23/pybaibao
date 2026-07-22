from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List, Tuple, Union
import os

if TYPE_CHECKING:
    import numpy as np

from ._ocr import OcrService, OcrResult


class PaddleOcr(OcrService):
    """基于 PaddleOCR 的本地 OCR 策略实现。

    PaddleOCR 是百度飞桨推出的开源 OCR 工具库，具有高精度、高性能的特点。
    本实现提供完整的本地文字识别能力，无需联网即可运行。

    特性:
        - 支持中英文等多种语言识别
        - 内置角度分类器，支持倾斜文本识别
        - 基于 PaddlePaddle 深度学习框架
        - 提供详细的识别结果（位置、置信度）

    依赖:
        - paddleocr: 核心 OCR 引擎（含 PaddlePaddle）
        - opencv-python: 图像处理
    """

    def __init__(
        self,
        use_angle_cls: bool = True,
        lang: str = 'ch',
    ) -> None:
        """初始化 PaddleOCR 策略。

        Args:
            use_angle_cls: 是否启用角度分类器，用于识别旋转文本（如倒置、倾斜的文字）。
                          启用后可提高倾斜文本的识别准确率，但会增加少量计算开销。
            lang: 识别语言，默认为 'ch'（中英文混合）。
                  支持的语言代码包括: 'ch'（中英）、'en'（英文）、'ja'（日文）等。

        Raises:
            ImportError: 当 paddleocr 库未安装时抛出。

        Note:
            首次使用时会自动下载预训练模型，约 100MB-500MB，取决于语言配置。
        """
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise ImportError(
                "paddleocr 库未安装，请运行: pip install paddleocr"
            )

        self._lang: str = lang
        self._ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=lang,
        )

    def _preprocess_image(self, image: Union[str, np.ndarray]) -> Union[str, np.ndarray]:
        """预处理图片，验证输入有效性并返回可直接传给 PaddleOCR 的格式。

        PaddleOCR 的 ocr 方法同时支持图片路径和 numpy 数组作为输入，
        因此无需将数组转为临时文件，避免不必要的 IO 开销。

        Args:
            image: 图片路径（字符串）或 OpenCV 图像数组（numpy.ndarray）。

        Returns:
            验证后的图片路径或 numpy 数组。

        Raises:
            FileNotFoundError: 当传入的图片路径不存在时抛出。
        """
        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"图片文件不存在: {image}")
        return image

    def recognize(self, image: Union[str, np.ndarray]) -> str:
        """识别图片中的文字，返回纯文本结果。

        Args:
            image: 图片路径（字符串）或 OpenCV 图像数组（numpy.ndarray）。

        Returns:
            识别出的文本内容，多行文本用换行符 `\n` 分隔，空白文本被过滤。

        Note:
            PaddleOCR 返回的结果结构为: [[[bbox, [text, confidence]], ...], ...]
            外层列表表示页面，内层列表表示识别到的文本行。
        """
        img_path = self._preprocess_image(image)
        result = self._ocr.ocr(img_path, cls=True)

        lines: List[str] = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
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
        img_path = self._preprocess_image(image)
        result = self._ocr.ocr(img_path, cls=True)

        details: List[OcrResult] = []
        if result and result[0]:
            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]
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

        Note:
            对于 numpy 数组输入，会创建副本进行绘制，避免修改原始图像。
        """
        import cv2
        import numpy as np

        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"图片文件不存在: {image}")
            img = cv2.imread(image)
        else:
            # 创建副本，避免修改原始图像
            img = image.copy()

        result = self._ocr.ocr(img, cls=True)

        if result and result[0]:
            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                if not text.strip():
                    continue

                # 绘制四边形边界框
                pts = np.array(bbox, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)

                # 在边界框上方绘制文本标签
                x, y = int(bbox[0][0]), int(bbox[0][1]) - 10
                cv2.putText(
                    img,
                    text,
                    (x, y),
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
    def lang(self) -> str:
        """获取当前配置的语言代码。

        Returns:
            str: 语言代码，如 'ch'（中英）、'en'（英文）。
        """
        return self._lang
