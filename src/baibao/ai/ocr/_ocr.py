"""
OCR 核心抽象与管理模块。

提供 :class:`OcrResult` 数据类、:class:`OcrService` 抽象基类，
以及模块级的 OCR 服务注册、切换和便捷调用函数。

设计上采用策略模式结合模板方法：基类统一负责图片加载、纯文本拼接与结果绘制，
子类只需实现核心识别方法 :meth:`OcrService._recognize_array`，
最大程度复用代码并保证各引擎行为一致。
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    # numpy 是 OCR 场景下不可避免的依赖，而非额外负担：
    #   - OpenCV 的 imread 返回 ndarray，polylines / putText 也只接收 ndarray；
    #   - EasyOCR / PaddleOCR 同样基于 ndarray 处理图像；
    #   - 因此 numpy 是 opencv-python / easyocr / paddleocr 的传递依赖，运行时必然已安装。
    # 此处仅做类型提示导入（运行时零成本），运行期的实际导入下沉到 _load_image、recognize_and_draw 内部。
    import numpy as np


# region ======== 数据对象 ========

@dataclass
class OcrResult:
    """
    OCR 识别结果。

    Attributes:
        text: 识别出的文字内容。
        bbox: 四边形边界框坐标，格式 ``[(x1, y1), (x2, y2), (x3, y3), (x4, y4)]``。
        confidence: 识别置信度，取值范围 0~1。
    """

    text: str
    bbox: List[Tuple[int, int]]
    confidence: float


# endregion


# region ======== 策略抽象基类 ========

class OcrService(ABC):
    """
    OCR 策略抽象基类，定义统一的识别接口。

    采用模板方法模式：图片加载、文本清洗、结果绘制等通用流程由基类统一实现，
    子类只需实现 :meth:`_recognize_array`，专注于具体引擎的识别逻辑。
    这样既消除了各实现间的重复代码，又保证了不同引擎对外行为完全一致。

    Note:
        传入的 numpy 图像数组不会被修改——基类在加载阶段会创建副本，
        因此 :meth:`recognize_and_draw` 的绘制操作不会影响调用方持有的原图。
    """

    @abstractmethod
    def _recognize_array(self, image: 'np.ndarray') -> List[OcrResult]:
        """
        对已加载的图像数组执行 OCR 识别（子类唯一需实现的核心方法）。

        输入保证为经过 :meth:`_load_image` 校验的 OpenCV 图像数组（BGR），
        子类无需重复加载或校验文件，也不必关心空白文本的过滤——
        后者由基类在 :meth:`_filter_results` 中统一处理。

        Args:
            image: OpenCV 图像数组（BGR 格式）。

        Returns:
            :class:`OcrResult` 对象列表，文本字段可为原始值（基类会统一清洗）。

        Raises:
            RuntimeError: 底层引擎识别失败时抛出。
        """

    @staticmethod
    def _load_image(image: Union[str, 'np.ndarray']) -> 'np.ndarray':
        """
        将输入统一加载为 OpenCV 图像数组。

        - 字符串路径：读取文件，校验存在性与可读性。
        - numpy 数组：返回副本，避免后续绘制修改调用方的原始图像。

        Args:
            image: 图片路径或 OpenCV 图像数组。

        Returns:
            OpenCV 图像数组（BGR 格式）。

        Raises:
            FileNotFoundError: 图片路径不存在。
            ValueError: 无法读取图片文件（损坏或格式不支持）。
            TypeError: image 既不是字符串也不是 numpy 数组。
        """
        import cv2
        import numpy as np

        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"图片文件不存在: {image}")
            img = cv2.imread(image)
            if img is None:
                raise ValueError(
                    f"无法读取图片文件，请检查文件是否损坏或格式是否支持: {image}"
                )
            return img

        if isinstance(image, np.ndarray):
            return image.copy()

        raise TypeError(
            f"image 必须是图片路径(str)或 numpy 数组，实际类型: {type(image)}"
        )

    @staticmethod
    def _filter_results(results: List[OcrResult]) -> List[OcrResult]:
        """
        清洗识别结果：去除首尾空白，过滤空文本。

        将文本清洗策略集中在基类，子类只需返回引擎原始结果，
        无需关心空白处理，进一步降低耦合。

        Args:
            results: 引擎返回的原始识别结果列表。

        Returns:
            清洗后的 :class:`OcrResult` 列表，文本均为去除首尾空白的非空字符串。
        """
        cleaned: List[OcrResult] = []
        for r in results:
            text = r.text.strip() if r.text else ""
            if text:
                cleaned.append(
                    OcrResult(text=text, bbox=r.bbox, confidence=r.confidence)
                )
        return cleaned

    def recognize(self, image: Union[str, 'np.ndarray']) -> str:
        """
        识别图片中的文字，返回纯文本结果。

        Args:
            image: 图片路径或 OpenCV 图像数组。

        Returns:
            识别出的文本内容，多行文本以换行符 ``\\n`` 分隔，空白文本被过滤。

        Raises:
            FileNotFoundError: 图片路径不存在。
            ValueError: 无法读取图片文件。
            TypeError: image 类型不支持。
        """
        img = self._load_image(image)
        results = self._filter_results(self._recognize_array(img))
        return '\n'.join(r.text for r in results)

    def recognize_with_details(
        self, image: Union[str, 'np.ndarray']
    ) -> List[OcrResult]:
        """
        识别图片中的文字，返回包含位置与置信度的详细结果。

        Args:
            image: 图片路径或 OpenCV 图像数组。

        Returns:
            :class:`OcrResult` 对象列表，空白文本已被过滤。

        Raises:
            FileNotFoundError: 图片路径不存在。
            ValueError: 无法读取图片文件。
            TypeError: image 类型不支持。
        """
        img = self._load_image(image)
        return self._filter_results(self._recognize_array(img))

    def recognize_and_draw(
        self,
        image: Union[str, 'np.ndarray'],
        output_path: Optional[str] = None,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> 'np.ndarray':
        """
        识别图片中的文字，并在图片上绘制边界框与文本标签。

        Args:
            image: 图片路径或 OpenCV 图像数组。传入数组时会创建副本，不修改原图。
            output_path: 结果保存路径；为 ``None`` 时仅返回图像数组不保存。
            color: 边界框与文本颜色，BGR 格式，默认绿色 ``(0, 255, 0)``。
            thickness: 边界框线条粗细，默认 2 像素。

        Returns:
            绘制了边界框与文本标签的图像数组（BGR 格式）。

        Raises:
            FileNotFoundError: 图片路径不存在。
            ValueError: 无法读取图片文件。
            TypeError: image 类型不支持。
        """
        import cv2
        import numpy as np

        img = self._load_image(image)
        for item in self._filter_results(self._recognize_array(img)):
            pts = np.array(item.bbox, np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)

            x, y = int(item.bbox[0][0]), int(item.bbox[0][1]) - 10
            cv2.putText(
                img,
                item.text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        if output_path:
            cv2.imwrite(output_path, img)

        return img


# endregion


# region ======== 模块级 OCR 管理 ========

# 存储不同配置名对应的 OcrService 实例
_ocrServices: Dict[str, OcrService] = {}
# 保护 _ocrServices 字典并发访问的锁
_ocrServices_lock = Lock()
# 默认配置名
DEFAULT_OCR_NAME = "default"


def get_ocr_service(ocr_name: Optional[str] = None) -> OcrService:
    """
    获取指定配置名对应的 OcrService 实例。

    对于默认配置名，如果尚未设置，会自动创建 EasyOcr 实例。

    Args:
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        OcrService 实例。

    Raises:
        KeyError: 指定的配置名对应的 OcrService 不存在时抛出。
    """
    if not ocr_name:
        ocr_name = DEFAULT_OCR_NAME

    with _ocrServices_lock:
        if ocr_name not in _ocrServices:
            if ocr_name == DEFAULT_OCR_NAME:
                # 延迟导入，避免与子类形成循环依赖
                from .easy_ocr import EasyOcr

                _ocrServices[ocr_name] = EasyOcr()
            else:
                raise KeyError(
                    f"未找到配置名 '{ocr_name}' 对应的 OcrService，"
                    f"请先调用 set_ocr_service() 设置"
                )
        return _ocrServices[ocr_name]


def set_ocr_service(ocr_name: str, service: OcrService) -> None:
    """
    设置指定配置名对应的 OcrService 实例。

    Args:
        ocr_name: OCR 配置名。
        service: OcrService 实例。

    Raises:
        TypeError: service 不是 OcrService 类型时抛出。
    """
    if not isinstance(service, OcrService):
        raise TypeError(f"service 必须是 OcrService 类型，实际类型: {type(service)}")
    if not ocr_name:
        ocr_name = DEFAULT_OCR_NAME
    with _ocrServices_lock:
        _ocrServices[ocr_name] = service


def remove_ocr_service(ocr_name: Optional[str] = None) -> None:
    """
    移除指定配置名对应的 OcrService 实例。

    Args:
        ocr_name: OCR 配置名，如果不传则移除默认配置名。
    """
    if not ocr_name:
        ocr_name = DEFAULT_OCR_NAME
    with _ocrServices_lock:
        _ocrServices.pop(ocr_name, None)


def recognize(image: Union[str, 'np.ndarray'], ocr_name: Optional[str] = None) -> str:
    """
    识别图片中的文字，返回纯文本结果。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        识别出的文本内容，多行文本以换行符分隔。
    """
    return get_ocr_service(ocr_name).recognize(image)


def recognize_with_details(
    image: Union[str, 'np.ndarray'], ocr_name: Optional[str] = None
) -> List[OcrResult]:
    """
    识别图片中的文字，返回包含位置与置信度的详细结果。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        :class:`OcrResult` 对象列表。
    """
    return get_ocr_service(ocr_name).recognize_with_details(image)


def recognize_and_draw(
    image: Union[str, 'np.ndarray'],
    output_path: Optional[str] = None,
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    ocr_name: Optional[str] = None,
) -> 'np.ndarray':
    """
    识别图片中的文字，并在图片上绘制边界框与文本标签。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        output_path: 结果保存路径；为 ``None`` 时不保存。
        color: 边界框颜色，BGR 格式，默认绿色 ``(0, 255, 0)``。
        thickness: 边界框线条粗细，默认 2。
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        绘制了边界框的图像数组。
    """
    return get_ocr_service(ocr_name).recognize_and_draw(
        image, output_path=output_path, color=color, thickness=thickness
    )


# endregion
