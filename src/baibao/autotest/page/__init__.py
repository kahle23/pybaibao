"""
page — 页面操作层。

  - :class:`BasePage` — 页面对象基类（Element Plus 组件操作 + 真实输入 +
    对话框作用域）。
  - :mod:`ep_widgets` — EP 弹层清场/toast 自由函数族（收 ``page``，不建页对象）。
  - :mod:`tables` — el-table 按表头读列 + 分页游走自由函数族。

包接管原 ``baibao.autotest.page`` 模块名，旧导入路径不变。
"""

from . import ep_widgets, tables
from .base import BasePage

__all__ = ["BasePage", "ep_widgets", "tables"]
