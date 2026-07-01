"""
货币模块

提供币种数据对象及相关工具方法。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    """
    货币数据对象

    存储货币的基本信息：符号、编码、名称
    """
    symbol: str  # 符号，如 ￥、$
    code: str    # 编码，如 CNY、USD
    name: str    # 名字，如 人民币、美元


# 常用货币列表
_currencies = [
    Currency(symbol='￥', code='CNY', name='人民币'),
    Currency(symbol='$', code='USD', name='美元'),
    Currency(symbol='€', code='EUR', name='欧元'),
    Currency(symbol='￡', code='GBP', name='英镑'),
    Currency(symbol='₽', code='RUB', name='俄罗斯卢布'),
    Currency(symbol='HK$', code='HKD', name='港币'),
    Currency(symbol='S$', code='SGD', name='新加坡元'),
]

# 按符号、编码、名字建立索引
_symbol_map = {c.symbol: c for c in _currencies}
_code_map = {c.code.upper(): c for c in _currencies}
_name_map = {c.name: c for c in _currencies}


def add(symbol: str, code: str, name: str) -> bool:
    """
    新增币种

    Args:
        symbol: 货币符号，如 '￥'
        code: 货币编码，如 'CNY'（不能重复）
        name: 货币名字，如 '人民币'

    Returns:
        添加成功返回 True，如果 code 已存在或参数无效则返回 False
    """
    # 验证输入参数
    if not symbol or not symbol.strip():
        return False
    if not code or not code.strip():
        return False
    if not name or not name.strip():
        return False
    # 检查编码是否已存在
    code_upper = code.upper()
    if code_upper in _code_map:
        return False
    # 创建新的货币对象
    currency = Currency(symbol=symbol, code=code, name=name)
    # 添加到常用货币列表
    _currencies.append(currency)
    _symbol_map[symbol] = currency
    _code_map[code_upper] = currency
    _name_map[name] = currency
    return True


def remove(code: str) -> bool:
    """
    删除币种

    Args:
        code: 货币编码，如 'CNY'

    Returns:
        删除成功返回 True，如果 code 不存在则返回 False
    """
    # 查询货币是否存在
    code_upper = code.upper()
    currency = _code_map.get(code_upper)
    if not currency:
        return False
    # 从常用货币列表中删除
    try:
        _currencies.remove(currency)
    except ValueError:
        pass
    del _symbol_map[currency.symbol]
    del _code_map[code_upper]
    del _name_map[currency.name]
    return True


def get_by_symbol(symbol: str) -> Currency | None:
    """
    根据符号获取货币信息

    Args:
        symbol: 货币符号，如 '￥'、'$'

    Returns:
        对应的 Currency 对象，如果未找到则返回 None
    """
    return _symbol_map.get(symbol)


def get_by_code(code: str) -> Currency | None:
    """
    根据编码获取货币信息

    Args:
        code: 货币编码，如 'CNY'、'USD'

    Returns:
        对应的 Currency 对象，如果未找到则返回 None
    """
    return _code_map.get(code.upper())


def get_by_name(name: str) -> Currency | None:
    """
    根据名字获取货币信息

    Args:
        name: 货币名字，如 '人民币'、'美元'

    Returns:
        对应的 Currency 对象，如果未找到则返回 None
    """
    return _name_map.get(name)


def search_first(text: str) -> Currency | None:
    """
    根据传入的字符串搜索货币信息，支持精确匹配符号、编码或名字，返回第一个匹配项

    Args:
        text: 币种符号、编码或名字，如 '￥'、'CNY'、'人民币'

    Returns:
        对应的 Currency 对象，如果未找到则返回 None
    """
    # 先按符号匹配
    currency = _symbol_map.get(text)
    if currency:
        return currency
    # 再按编码匹配（忽略大小写）
    currency = _code_map.get(text.upper())
    if currency:
        return currency
    # 最后按名字模糊匹配
    for name, currency in _name_map.items():
        if text in name:
            return currency
    # 如果所有匹配都失败，返回 None
    return None


def get_symbol_by_code(code: str, default: str = '') -> str:
    """
    根据编码获取货币符号

    Args:
        code: 货币编码，如 'CNY'、'USD'，为空时直接返回 default
        default: 如果未找到对应的货币符号，则返回此默认值，默认为空字符串

    Returns:
        对应的货币符号，如果未找到或 code 为空则返回传入的 default 参数值
    """
    # 验证输入参数
    if not code or not code.strip():
        return default
    # 按编码匹配（忽略大小写）
    currency = _code_map.get(code.upper())
    return currency.symbol if currency else default


