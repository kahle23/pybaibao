"""OCR 核心抽象与管理模块。

提供 :class:`OcrResult` 数据类、:class:`OcrService` 抽象基类，
以及模块级的 OCR 服务注册、切换和便捷调用函数。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, List, Tuple, Union

if TYPE_CHECKING:
    import numpy as np


@dataclass
class OcrResult:
    """OCR 识别结果。

    Attributes:
        text: 识别出的文字内容。
        bbox: 四边形边界框坐标，格式 ``[(x1, y1), (x2, y2), (x3, y3), (x4, y4)]``。
        confidence: 识别置信度，取值范围 0~1。
    """

    text: str
    bbox: List[Tuple[int, int]]
    confidence: float


class OcrService(ABC):
    """OCR 策略抽象基类，定义统一的识别接口。

    所有具体实现（如 EasyOcr、PaddleOcr）需继承此类并实现三个核心方法，
    以保证接口的一致性和可替换性。
    """

    @abstractmethod
    def recognize(self, image: Union[str, np.ndarray]) -> str:
        """识别图片中的文字，返回纯文本结果。

        Args:
            image: 图片路径或 OpenCV 图像数组。

        Returns:
            识别出的文本内容，多行文本用换行符 ``\\n`` 分隔。

        Raises:
            FileNotFoundError: 图片路径不存在。
            ValueError: 无法读取图片文件。
        """
        pass

    @abstractmethod
    def recognize_with_details(
        self, image: Union[str, np.ndarray]
    ) -> List[OcrResult]:
        """识别图片中的文字，返回包含位置与置信度的详细结果。

        Args:
            image: 图片路径或 OpenCV 图像数组。

        Returns:
            :class:`OcrResult` 对象列表，包含 text、bbox、confidence 字段。

        Raises:
            FileNotFoundError: 图片路径不存在。
            ValueError: 无法读取图片文件。
        """
        pass

    @abstractmethod
    def recognize_and_draw(
        self,
        image: Union[str, np.ndarray],
        output_path: Optional[str] = None,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """识别图片中的文字，并在图片上绘制边界框与文本标签。

        Args:
            image: 图片路径或 OpenCV 图像数组。
            output_path: 结果保存路径；为 ``None`` 时不保存，仅返回图像数组。
            color: 边界框与文本颜色，BGR 格式，默认绿色 ``(0, 255, 0)``。
            thickness: 边界框线条粗细，默认 2 像素。

        Returns:
            绘制了边界框与文本标签的图像数组。

        Raises:
            FileNotFoundError: 图片路径不存在。
            ValueError: 无法读取图片文件。
        """
        pass


# 子类导入必须在 OcrService 定义之后，避免循环导入
from .easy_ocr import EasyOcr  # noqa: E402


# ---------------------------------------------------------------------------
# 模块级 OCR 管理 —— 统一管理并支持运行时切换 OCR 实现
# ---------------------------------------------------------------------------

# 存储不同配置名对应的 OcrService 实例
_ocrServices: Dict[str, OcrService] = {}

# 默认配置名
DEFAULT_OCR_NAME = "default"


def get_ocr_service(ocr_name: Optional[str] = None) -> OcrService:
    """获取指定配置名对应的 OcrService 实例。

    对于默认配置名，如果尚未设置，会自动创建 EasyOcr 实例。

    Args:
        ocr_name: OCR 配置名，如果不传则使用默认配置名

    Returns:
        OcrService 实例

    Raises:
        KeyError: 指定的配置名对应的 OcrService 不存在时抛出
    """
    # 如果未指定配置名，使用默认配置名
    if not ocr_name:
        ocr_name = DEFAULT_OCR_NAME
    # 如果配置名不存在，并且是默认配置名，设置为 EasyOcr 实例
    if ocr_name not in _ocrServices:
        if ocr_name == DEFAULT_OCR_NAME:
            _ocrServices[ocr_name] = EasyOcr()
        else:
            raise KeyError(f"未找到配置名 '{ocr_name}' 对应的 OcrService，请先调用 set_ocr_service() 设置")
    # 返回对应的 OcrService 实例
    return _ocrServices[ocr_name]


def set_ocr_service(ocr_name: str, service: OcrService) -> None:
    """设置指定配置名对应的 OcrService 实例。

    Args:
        ocr_name: OCR 配置名
        service: OcrService 实例
    """
    # 检查 service 是否为 OcrService 类型
    if not isinstance(service, OcrService):
        raise TypeError(f"service 必须是 OcrService 类型，实际类型: {type(service)}")
    # 如果未指定配置名，使用默认配置名
    if not ocr_name:
        ocr_name = DEFAULT_OCR_NAME
    # 设置对应的 OcrService 实例
    _ocrServices[ocr_name] = service


def remove_ocr_service(ocr_name: Optional[str] = None) -> None:
    """移除指定配置名对应的 OcrService 实例。

    Args:
        ocr_name: OCR 配置名，如果不传则移除默认配置名
    """
    # 如果未指定配置名，使用默认配置名
    if not ocr_name:
        ocr_name = DEFAULT_OCR_NAME
    # 如果配置名存在，移除对应的 OcrService 实例
    if ocr_name in _ocrServices:
        del _ocrServices[ocr_name]


def recognize(image: Union[str, np.ndarray], ocr_name: Optional[str] = None) -> str:
    """识别图片中的文字，返回纯文本结果。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        ocr_name: OCR 配置名，如果不传则使用默认配置名

    Returns:
        识别出的文本内容，多行文本以换行符分隔。
    """
    return get_ocr_service(ocr_name).recognize(image)


def recognize_with_details(
    image: Union[str, np.ndarray], ocr_name: Optional[str] = None
) -> List[OcrResult]:
    """识别图片中的文字，返回包含位置与置信度的详细结果。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        ocr_name: OCR 配置名，如果不传则使用默认配置名

    Returns:
        :class:`OcrResult` 对象列表，包含 text、bbox、confidence 字段。
    """
    return get_ocr_service(ocr_name).recognize_with_details(image)


def recognize_and_draw(
    image: Union[str, np.ndarray],
    output_path: Optional[str] = None,
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    ocr_name: Optional[str] = None,
) -> np.ndarray:
    """识别图片中的文字，并在图片上绘制边界框与文本标签。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        output_path: 结果保存路径；为 ``None`` 时不保存。
        color: 边界框颜色，BGR 格式，默认绿色 ``(0, 255, 0)``。
        thickness: 边界框线条粗细，默认 2。
        ocr_name: OCR 配置名，如果不传则使用默认配置名

    Returns:
        绘制了边界框的图像数组。
    """
    return get_ocr_service(ocr_name).recognize_and_draw(image, output_path, color, thickness)
