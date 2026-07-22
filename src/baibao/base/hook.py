"""
钩子管理模块

提供钩子（Hook）的注册、取消注册、获取、遍历和执行能力。
每个钩子由 group + name + order 唯一标识，类型为无入参、无返回值的可调用对象。
group 用于数据隔离，默认值为 "default"。

典型用法：
    from baibao.base.hook import hook, ON_STARTUP, ON_SHUTDOWN

    # 方式一：手动注册
    from baibao.base import hook as hook_mod
    hook_mod.register(ON_STARTUP, my_init_func, group="default", order=100)

    # 方式二：装饰器注册（推荐）
    @hook(name=ON_STARTUP, group="default", order=100)
    def my_init_func():
        ...

    # 执行钩子
    from baibao.base import hook as hook_mod
    hook_mod.execute(ON_STARTUP)                    # 执行所有启动钩子（按 order 升序）
    hook_mod.execute(ON_SHUTDOWN, order=100)        # 仅执行 order=100 的结束钩子
"""

import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


# region ======== 类型 & 常量 ========
# 内置钩子名称常量
ON_STARTUP = "on_startup"
ON_SHUTDOWN = "on_shutdown"

# 钩子类型：无入参、无返回值（内部类型别名，调用者无需导入，传入可调用对象即可）
Hook = Callable[[], None]

# endregion


# region ======== 数据结构 ========
@dataclass(frozen=True)
class HookInfo:
    """钩子信息，包含分组、名称、顺序和回调函数"""
    group: str
    name: str
    order: int
    hook: Hook

# endregion


# region ======== 钩子管理 ========
# {group: {name: {order: hook}}}
_hooks: Dict[str, Dict[str, Dict[int, Hook]]] = {}
_lock = threading.RLock()

# 默认分组名
DEFAULT_GROUP = "default"
# 默认顺序
DEFAULT_ORDER = 0


def register(name: str, hook_fn: Hook, group: Optional[str] = None, order: Optional[int] = None) -> None:
    """
    注册钩子

    Args:
        name: 钩子名称
        hook_fn: 无入参、无返回值的可调用对象
        group: 分组名称（可选，默认为 DEFAULT_GROUP）
        order: 执行顺序（可选，默认为 0，数字越小越先执行）

    Raises:
        TypeError: hook_fn 不可调用时抛出
        ValueError: 当 group+name+order 已存在时抛出
    """
    if group is None or group == '':
        group = DEFAULT_GROUP
    if order is None or order == '':
        order = DEFAULT_ORDER
    if not callable(hook_fn):
        raise TypeError(f"hook 必须是可调用对象，实际类型: {type(hook_fn)}")
    with _lock:
        group_hooks = _hooks.setdefault(group, {})
        name_hooks = group_hooks.setdefault(name, {})
        if order in name_hooks:
            raise ValueError(f"钩子已存在: group='{group}', name='{name}', order={order}")
        name_hooks[order] = hook_fn


def unregister(name: str, group: Optional[str] = None, order: Optional[int] = None) -> bool:
    """
    取消注册钩子

    Args:
        name: 钩子名称
        group: 分组名称（可选，默认为 DEFAULT_GROUP）
        order: 执行顺序（可选，默认为 0）

    Returns:
        是否成功取消（不存在时返回 False）
    """
    if group is None or group == '':
        group = DEFAULT_GROUP
    if order is None or order == '':
        order = DEFAULT_ORDER
    with _lock:
        group_hooks = _hooks.get(group)
        if group_hooks is None:
            return False
        name_hooks = group_hooks.get(name)
        if name_hooks is None or order not in name_hooks:
            return False
        del name_hooks[order]
        # 逐层清理空条目
        if not name_hooks:
            del group_hooks[name]
        if not group_hooks:
            del _hooks[group]
        return True


def get_hook(name: str, group: Optional[str] = None, order: Optional[int] = None) -> Optional[HookInfo]:
    """
    获取指定钩子

    Args:
        name: 钩子名称
        group: 分组名称（可选，默认为 DEFAULT_GROUP）
        order: 执行顺序（可选，默认为 0）

    Returns:
        HookInfo 或 None
    """
    if group is None or group == '':
        group = DEFAULT_GROUP
    if order is None or order == '':
        order = DEFAULT_ORDER
    with _lock:
        group_hooks = _hooks.get(group)
        if group_hooks is None:
            return None
        name_hooks = group_hooks.get(name)
        if name_hooks is None:
            return None
        hook_fn = name_hooks.get(order)
        if hook_fn is None:
            return None
        return HookInfo(group=group, name=name, order=order, hook=hook_fn)


def get_hooks(group: Optional[str] = None, name: Optional[str] = None) -> List[HookInfo]:
    """
    获取钩子列表

    Args:
        group: 分组名称（可选）。若指定，仅返回该分组的钩子；若为 None，返回全部分组。
        name: 钩子名称（可选）。若指定，返回该名称下的所有钩子；若为 None，返回全部钩子。

    Returns:
        HookInfo 列表（按 group → name → order 排序）
    """
    if group is not None and group == '':
        group = DEFAULT_GROUP
    if name is not None and name == '':
        name = None
    with _lock:
        result: List[HookInfo] = []
        groups = [group] if group is not None else sorted(_hooks.keys())
        for g in groups:
            group_hooks = _hooks.get(g, {})
            names = [name] if name is not None else sorted(group_hooks.keys())
            for n in names:
                name_hooks = group_hooks.get(n, {})
                for order in sorted(name_hooks.keys()):
                    result.append(HookInfo(group=g, name=n, order=order, hook=name_hooks[order]))
        return result


def has_hook(name: str, group: Optional[str] = None, order: Optional[int] = None) -> bool:
    """
    检查钩子是否存在

    Args:
        name: 钩子名称
        group: 分组名称（可选，默认为 DEFAULT_GROUP）
        order: 执行顺序（可选）。若指定，检查 name+order 是否存在；若为 None，检查该名称下是否有任何钩子。

    Returns:
        是否存在
    """
    if group is None or group == '':
        group = DEFAULT_GROUP
    if order is not None and order == '':
        order = DEFAULT_ORDER
    with _lock:
        group_hooks = _hooks.get(group)
        if group_hooks is None:
            return False
        name_hooks = group_hooks.get(name)
        if name_hooks is None:
            return False
        if order is not None:
            return order in name_hooks
        return len(name_hooks) > 0


def count(group: Optional[str] = None, name: Optional[str] = None) -> int:
    """
    统计钩子数量

    Args:
        group: 分组名称（可选）。若指定，仅统计该分组；若为 None，统计全部。
        name: 钩子名称（可选）。若指定，仅统计该名称下的钩子；若为 None，统计全部。

    Returns:
        钩子总数
    """
    if group is not None and group == '':
        group = DEFAULT_GROUP
    with _lock:
        if group is not None:
            group_hooks = _hooks.get(group, {})
            if name is not None:
                name_hooks = group_hooks.get(name, {})
                return len(name_hooks)
            return sum(len(v) for v in group_hooks.values())
        if name is not None:
            return sum(len(group_hooks.get(name, {})) for group_hooks in _hooks.values())
        return sum(sum(len(v) for v in g.values()) for g in _hooks.values())


def clear(group: Optional[str] = None, name: Optional[str] = None) -> None:
    """
    清空钩子

    Args:
        group: 分组名称。若为 None，清空全部分组。
        name: 钩子名称。若为 None，清空该分组下所有钩子。
              仅当 group 也指定时才生效。
    """
    with _lock:
        if group is None:
            _hooks.clear()
        elif name is None:
            _hooks.pop(group, None)
        else:
            group_hooks = _hooks.get(group)
            if group_hooks is not None:
                group_hooks.pop(name, None)
                if not group_hooks:
                    del _hooks[group]


def execute(name: str, group: Optional[str] = None, order: Optional[int] = None) -> None:
    """
    执行钩子

    Args:
        name: 钩子名称
        group: 分组名称（可选，默认为 DEFAULT_GROUP）
        order: 执行顺序（可选）。若指定，仅执行该钩子；若为 None，执行该名称下所有钩子（按 order 升序）。
    """
    if group is None or group == '':
        group = DEFAULT_GROUP
    if order is not None and order == '':
        order = DEFAULT_ORDER
    if order is not None:
        info = get_hook(name, order, group)
        if info is None:
            return
        info.hook()
    else:
        hooks = get_hooks(group, name)
        if not hooks:
            return
        for info in hooks:
            info.hook()

# endregion


# region ======== 装饰器 ========
# def hook(name: str, order: Optional[int] = None, group: Optional[str] = None) -> Callable[[Hook], Hook]:
#     """
#     装饰器：将函数注册为钩子

#     装饰时立即注册，函数本身原样返回、不影响直接调用。

#     Args:
#         name: 钩子名称
#         order: 执行顺序（可选，默认为 0，数字越小越先执行）
#         group: 分组名称（可选，默认为 DEFAULT_GROUP）

#     Example:
#         @hook(name=ON_STARTUP, order=100)
#         def init_db():
#             ...
#     """
#     def decorator(func: Hook) -> Hook:
#         register(name, func, order, group)
#         return func
#     return decorator

# endregion

