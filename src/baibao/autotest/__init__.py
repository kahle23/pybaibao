"""
autotest — Playwright E2E 测试基础设施。

把日常 Web 自动化测试中反复用到的能力封装成简洁 API：页面对象基类、浏览器启动、登录态缓存、接口基类、可选启用的 pytest fixture。

核心特性（按模块分层，门面只留入手点）：

  - :class:`BasePage` — Element Plus 组件操作 + 真实输入 + 对话框作用域
  - :class:`LoginCfg` + :func:`login_context` — 数据驱动的登录流程 + 登录态缓存复用
  - :class:`ApiBase` — 复用浏览器登录态 cookie 的后端接口基类（Playwright ``APIRequestContext``）
  - :class:`TokenSession` — requests 版 token 会话（captcha 登录 + 401 自动重登重放）
  - :class:`NetWatch` — context 级流量观察引擎（黑白名单判写 + 受控写捕获）
  - :class:`CaseRecorder` — 独立脚本式 E2E 的用例记录与执行骨架
  - :func:`launch_browser` — 本地 Chrome 探测与启动
  - :mod:`fixtures` — opt-in pytest fixture（``pytest_plugins`` 启用）

模块地图（**根目录散件 = 基础组件**，一眼可见核心入口；**子包 = 定制/加强组件**；
其余能力一律走子模块路径，不在门面重导出）::

    （根）     browser、login_state、netwatch、recorder、polling、envutil、
              devtools、lowprofile、textutil（数值/文本小件函数族）
    page/     BasePage + ep_widgets（EP 弹层自由函数族）+ tables（表格读列/分页游走）
    api/      ApiBase + TokenSession
    probe/    DOM 摘要探针（extract_js / url / render / runner）
    fixtures/ opt-in pytest fixture + conftest 样板

分层纪律：根模块（基础组件）不得 import 子包（定制/加强组件）；子包 import 根天经地义。

依赖：playwright 为重依赖，按需懒加载，不在模块顶层导入（requests 同）。
安装：``pip install "baibao[autotest]"``。
"""

from .api import ApiBase, TokenSession, TokenSessionCfg
from .browser import launch_browser
from .login_state import LoginCfg, login_context
from .netwatch import NetWatch, NetWatchCfg
from .page import BasePage
from .recorder import CaseRecorder, SkipCase

__all__ = [
    "ApiBase",
    "BasePage",
    "CaseRecorder",
    "LoginCfg",
    "NetWatch",
    "NetWatchCfg",
    "SkipCase",
    "TokenSession",
    "TokenSessionCfg",
    "launch_browser",
    "login_context",
]
