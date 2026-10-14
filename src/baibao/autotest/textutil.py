"""
textutil — E2E 断言常用的数值/文本小件。

来源：12-SDI e2e 十三份模板顶部各自内嵌的 ``num_in``/``_i``/``_f``/``num_eq``/
``exact_rx``/``fmt_qty`` 族（各取所需、命名不一，此处统一为无下划线公开名）。
"""

import re

_NUM_RX = re.compile(r"-?\d+(?:\.\d+)?")      # num_in/nums_in 共用（模块级预编译）


def num_in(text: object) -> float | None:
    """
    抽文本里第一个数字（去千分位逗号；无数字返回 None）。
    """
    m = _NUM_RX.search(str(text).replace(",", ""))
    return float(m.group()) if m else None


def nums_in(text: object) -> list[float]:
    """
    抽文本里全部数字（如 ``"3/7 黑"`` → ``[3.0, 7.0]``）。
    """
    return [float(m) for m in _NUM_RX.findall(str(text).replace(",", ""))]


def to_int(x: object) -> int | None:
    """
    宽容转 int（``"12"`` / ``12.0`` / ``12.5`` → ``12``；失败返回 None）。
    """
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def to_float(x: object, default: float | None = None) -> float | None:
    """
    宽容转 float（剥千分位逗号；失败返回 default）。
    """
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def num_eq(x: object, y: object, tol: float = 0.01) -> bool:
    """数值近似相等（剥千分位逗号；任一侧转不成数字返回 False）。"""
    fx, fy = to_float(x), to_float(y)
    if fx is None or fy is None:
        return False
    return abs(fx - fy) <= tol


def fmt_qty(q: object) -> str:
    """
    整数千分位（``1234567`` → ``"1,234,567"``）；转不成数字原样返回。
    """
    try:
        return f"{int(float(q)):,}"
    except (TypeError, ValueError):
        return str(q)


def js_num(v: object) -> str:
    """
    数值转 JS 字面量形态（``12.0`` → ``"12"``、``12.5`` → ``"12.5"``、None → ``""``）。

    页面 ``evaluate`` 传参后与界面渲染值比对时用（JS 数字无千分位、整型无小数点）。
    """
    if v is None:
        return ""
    f = float(v)
    return str(int(f)) if f == int(f) else repr(f)


def exact_rx(text: object) -> re.Pattern[str]:
    """
    整串精确匹配的正则（转义 + 首尾锚定 + 容忍首尾空白）。

    供 ``has_text`` 场景做精确比对（EP 文案常带前后空白与拼接词）。
    """
    return re.compile(rf"^\s*{re.escape(str(text))}\s*$")
