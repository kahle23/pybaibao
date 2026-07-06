"""
验证模块

提供通用的数据验证方法，适用于 dataclass 等数据结构。
"""

from dataclasses import fields, MISSING
from typing import TypeVar, Type, Any, Sequence


# 定义类型变量 T，用于表示 dataclass 配置类的实例类型
T = TypeVar('T')


def check_dataclass_required_fields(data: dict[str, Any], data_class: Type[T], 
    required_fields: list[str] | None = None
) -> None:
    """
    检查数据字典是否包含构造 dataclass 所需的必填字段

    防止 data_class(**data) 因缺少必填字段而抛出 TypeError。

    支持两种模式：
    1. 传入 required_fields：检查指定的字段列表
    2. required_fields 为 None：自动从 data_class 获取没有默认值的字段

    Args:
        data: 待校验的数据字典
        data_class: dataclass 类类型
        required_fields: 指定的必填字段列表，为 None 时自动获取

    Raises:
        ValueError: 当数据字典缺少必填字段时抛出
    """
    # 确定必填字段集合
    if required_fields is not None:
        required = set(required_fields)
    else:
        required = {f.name for f in fields(data_class) if f.default is MISSING} # type: ignore[arg-type]
    # 检查字段是否存在
    missing = required - data.keys()
    if missing:
        raise ValueError(f"{data_class.__name__} 缺少字段: {', '.join(sorted(missing))}")


def check_required_fields_not_empty(obj: Any, required_fields: Sequence[str], 
    context: str | None = None
) -> None:
    """
    检查对象的必填字段是否有值（非 None、非空字符串）

    通用的对象字段非空校验方法，适用于 dataclass 实例等具有属性的对象。

    Args:
        obj: 待校验的对象实例
        required_fields: 必填字段名列表
        context: 上下文描述，用于错误提示，默认为对象的类名

    Raises:
        ValueError: 当必填字段为空时抛出
    """
    context = context or type(obj).__name__
    for field in required_fields:
        value = getattr(obj, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{context} 字段 '{field}' 不能为空")

