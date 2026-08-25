"""
OCR 模块，提供多种 OCR 策略实现。

采用策略模式（结合模板方法）设计：基类 :class:`OcrEngine`（来自 :mod:`pykunlun.ai.ocr`）
统一负责图片加载、文本清洗与结果绘制，子类只需实现核心识别方法，专注于引擎适配。
支持 EasyOCR、PaddleOCR 2.x/3.x。

引擎无关配置 :class:`OcrCfg` 与抽象基类 :class:`OcrEngine` / 管理器 :class:`OcrManager`
收敛在 :mod:`pykunlun.ai.ocr`；本包提供 EasyOCR / PaddleOCR 的具体实现（带重依赖）。

两种使用风格：

1. 直接构造（推荐用于新代码）::

     from baibao.ai.ocr import EasyOcr, build_ocr_engine
     from pykunlun.ai.ocr import OcrCfg

     ocr = EasyOcr(OcrCfg())
     text = ocr.recognize("image.png")

     # 或用引擎类型工厂（引擎间参数差异由工厂内部映射）
     ocr = build_ocr_engine("paddle", OcrCfg(lang='en'))

2. 模块级具名实例（兼容旧 API，背后由一个 :class:`OcrManager` 单例托管）::

     from baibao.ai.ocr import set_ocr_engine, recognize

     set_ocr_engine("my", PaddleOcr(OcrCfg()))
     recognize("image.png", ocr_name="my")
"""

from pykunlun.ai.ocr import OcrCfg, OcrEngine, OcrManager, OcrResult

from .easy_ocr import EasyOcr, langs_from_code
from .paddle_ocr import PaddleOcr, PaddleOcrV2, PaddleOcrV3, get_paddleocr_version

# region ======== 引擎类型 → 实现类 工厂 ========

# 引擎类型与实现类的映射。引擎间的参数差异（语言码、gpu/device、cpu_threads、角度分类）
# 由各实现类在构造时按 cfg 自行解释，工厂只负责按类型取类并构造。
_ENGINE_CLASSES: dict[str, type[OcrEngine]] = {
    'easy': EasyOcr,
    'paddle': PaddleOcr,
    'paddle2': PaddleOcrV2,
    'paddle3': PaddleOcrV3,
}


def build_ocr_engine(
    engine_type: str,
    cfg: OcrCfg,
) -> OcrEngine:
    """
    按引擎类型 + 统一配置构造 :class:`OcrEngine` 实例。

    引擎间参数差异（语言码、gpu/device、cpu_threads、角度分类）由各实现类在构造时
    按 ``cfg`` 自行解释，调用方（CLI / 技能 / 业务代码）只需提供引擎无关的 :class:`OcrCfg`，
    无需关心 EasyOCR / PaddleOCR 2.x / 3.x 各自的构造参数。

    Args:
        engine_type: 引擎类型：``easy`` / ``paddle`` / ``paddle2`` / ``paddle3``。
            ``paddle`` 为自动分发器，按已装 paddleocr 版本选 V2/V3。
        cfg: 引擎无关配置（``engine_type`` 字段无需设置，由所构造的实现类推导）。

    Raises:
        ValueError: 未知引擎类型。
    """
    cls = _ENGINE_CLASSES.get(engine_type)
    if cls is None:
        raise ValueError(
            f"未知 OCR 引擎: {engine_type}（可选: {', '.join(_ENGINE_CLASSES)}）"
        )
    return cls(cfg)


# endregion


# region ======== 模块级具名实例管理（兼容旧 API，背后由 OcrManager 单例托管） ========

# 托管具名实例的默认管理器。类注册表留空（本模块直接 register_engine 实例），
# 仅用其实例注册表与 get/recognize 便捷能力。
_default_manager = OcrManager()


def get_ocr_engine(ocr_name: str | None = None) -> OcrEngine:
    """
    获取指定配置名对应的 OcrEngine 实例。

    对于默认配置名，如果尚未设置，会自动创建 EasyOcr 实例。

    Args:
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        OcrEngine 实例。

    Raises:
        ValueError: 指定的配置名对应的 OcrEngine 不存在时抛出。
    """
    name = ocr_name or OcrManager.DEFAULT_NAME
    try:
        return _default_manager.get_engine(name)
    except ValueError:
        if name == OcrManager.DEFAULT_NAME:
            engine = EasyOcr(OcrCfg())
            _default_manager.register_engine(name, engine)
            return engine
        raise


def set_ocr_engine(ocr_name: str, engine: OcrEngine) -> None:
    """
    设置指定配置名对应的 OcrEngine 实例。

    Args:
        ocr_name: OCR 配置名。
        engine: OcrEngine 实例。

    Raises:
        TypeError: engine 不是 OcrEngine 类型时抛出。
    """
    if not isinstance(engine, OcrEngine):
        raise TypeError(f"engine 必须是 OcrEngine 类型，实际类型: {type(engine)}")
    _default_manager.register_engine(ocr_name, engine)


def remove_ocr_engine(ocr_name: str | None = None) -> None:
    """
    移除指定配置名对应的 OcrEngine 实例。

    Args:
        ocr_name: OCR 配置名，如果不传则移除默认配置名。
    """
    _default_manager.unregister_engine(ocr_name)


def recognize(image, ocr_name: str | None = None) -> str:
    """
    识别图片中的文字，返回纯文本结果。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        识别出的文本内容，多行文本以换行符分隔。
    """
    return get_ocr_engine(ocr_name).recognize(image)


def recognize_with_details(image, ocr_name: str | None = None) -> list[OcrResult]:
    """
    识别图片中的文字，返回包含位置与置信度的详细结果。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        :class:`OcrResult` 对象列表。
    """
    return get_ocr_engine(ocr_name).recognize_with_details(image)


def recognize_and_draw(
    image,
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int | None = None,
    output_path: str | None = None,
    ocr_name: str | None = None,
):
    """
    识别图片中的文字，并在图片上绘制边界框与文本标签。

    Args:
        image: 图片路径或 OpenCV 图像数组。
        color: 边界框颜色，BGR 格式。
        thickness: 边界框线条粗细；为 ``None`` 时透传给 cv2、沿用其默认（1）。
        output_path: 结果保存路径；为 ``None`` 时不保存。
        ocr_name: OCR 配置名，如果不传则使用默认配置名。

    Returns:
        绘制了边界框的图像数组。
    """
    return get_ocr_engine(ocr_name).recognize_and_draw(
        image, output_path=output_path, color=color, thickness=thickness
    )


# endregion


__all__ = [
    'EasyOcr',
    'OcrCfg',
    'OcrEngine',
    'OcrManager',
    'OcrResult',
    'PaddleOcr',
    'PaddleOcrV2',
    'PaddleOcrV3',
    'build_ocr_engine',
    'get_ocr_engine',
    'get_paddleocr_version',
    'langs_from_code',
    'recognize',
    'recognize_and_draw',
    'recognize_with_details',
    'remove_ocr_engine',
    'set_ocr_engine',
]
