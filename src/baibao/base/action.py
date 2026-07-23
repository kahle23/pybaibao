"""
动作管理模块

提供动作（Action）的注册、取消注册、获取和执行能力。
每个动作由 name 唯一标识，支持 name 通配符匹配批量执行。

动作为任意可调用对象（Callable[..., Any]），由调用方自行约定入参与返回值。

典型用法：
    from baibao.base import action
    from baibao.base.action import APP_ON_STARTUP, APP_ON_SHUTDOWN

    # 注册
    action.register(APP_ON_STARTUP, my_init_func)
    action.register(APP_ON_SHUTDOWN, my_cleanup_func)

    # 执行单个
    result = action.execute("validate", data)

    # 批量执行（通配符匹配，按名称排序，异常隔离）
    action.execute_all("app_on_*", config, print_result=True)
"""

import fnmatch
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional

from baibao.base import log


# region ======== 常量 ========
# 内置动作名称常量（app_ 前缀表示应用生命周期事件，因为 CLI 也是一种 app）
APP_ON_STARTUP = "app_on_startup"
APP_ON_SHUTDOWN = "app_on_shutdown"
# endregion


# region ======== 动作管理 ========
# 动作类型：任意可调用对象
ActionType = Callable[..., Any]

_actions: Dict[str, ActionType] = {}
_lock = threading.RLock()


def register(name: str, action_obj: ActionType) -> None:
    """
    注册动作

    Args:
        name: 动作名称（唯一）
        action_obj: 可调用对象

    Raises:
        TypeError: action_obj 不可调用时抛出
        ValueError: name 已存在时抛出
    """
    if not callable(action_obj):
        raise TypeError(f"action 必须是可调用对象，实际类型: {type(action_obj)}")
    with _lock:
        if name in _actions:
            raise ValueError(f"动作已存在: name='{name}'")
        _actions[name] = action_obj


def unregister(name: str) -> bool:
    """
    取消注册动作

    Returns:
        是否成功取消（不存在时返回 False）
    """
    with _lock:
        return _actions.pop(name, None) is not None


def get_action(name: str) -> Optional[ActionType]:
    """获取指定动作"""
    with _lock:
        return _actions.get(name)


def get_names(name_pattern: Optional[str] = None) -> List[str]:
    """
    获取匹配的动作名称列表

    Args:
        name_pattern: 名称匹配模式（支持通配符 * ?）。若为 None，返回全部。

    Returns:
        匹配的动作名称列表（按名称排序）
    """
    with _lock:
        if name_pattern is None:
            return sorted(_actions.keys())
        return sorted(fnmatch.filter(_actions.keys(), name_pattern))


def clear(name_pattern: Optional[str] = None) -> None:
    """
    清空动作

    Args:
        name_pattern: 名称匹配模式。若为 None，清空全部。
    """
    with _lock:
        if name_pattern is None:
            _actions.clear()
        else:
            for name in get_names(name_pattern):
                _actions.pop(name, None)


def execute(name: str, *args: Any, **kwargs: Any) -> Any:
    """
    执行单个动作

    Args:
        name: 动作名称
        *args: 透传给动作的位置参数
        **kwargs: 透传给动作的关键字参数

    Returns:
        执行结果；动作不存在时返回 None
    """
    with _lock:
        action_obj = _actions.get(name)
    if action_obj is None:
        return None
    return action_obj(*args, **kwargs)


def execute_all(name_pattern: str, *args: Any, print_result: bool = False, **kwargs: Any) -> None:
    """
    批量执行匹配的所有动作（按名称排序）

    对单个动作做异常隔离：某个动作抛异常不会中断后续动作，
    失败信息（含堆栈）通过 log.error 记录。

    Args:
        name_pattern: 名称匹配模式（支持通配符 * ?）
        *args: 透传给动作的位置参数
        print_result: 是否打印非空返回值
        **kwargs: 透传给动作的关键字参数
    """
    with _lock:
        snapshot = [(n, _actions[n]) for n in get_names(name_pattern)]
    for name, action_obj in snapshot:
        try:
            result = action_obj(*args, **kwargs)
            if print_result and result is not None:
                print(result)
        except Exception:
            log.error(f"执行动作失败: name={name}\n{traceback.format_exc()}")

# endregion
