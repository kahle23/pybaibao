"""
autotest — Playwright E2E 测试基础设施。

把日常 Web 自动化测试中反复用到的能力封装成简洁 API：页面对象基类、
浏览器启动、登录态缓存、接口基类、可选启用的 pytest fixture。

核心特性：

  - :class:`BasePage` — Element Plus 组件操作 + CDP 真实点击 + 对话框作用域
  - :class:`LoginCfg` + :func:`do_login` — 数据驱动的登录流程
  - :func:`save_storage_state` / :func:`is_auth_valid` — 登录态缓存（TTL）
  - :class:`ApiBase` — 复用浏览器登录态的后端接口基类
  - :func:`detect_chrome_path` / :func:`launch_browser` — 本地 Chrome 探测与启动
  - :mod:`fixtures` — opt-in pytest fixture（``pytest_plugins`` 启用）

按需从子模块导入，例如::

    from baibao.autotest.page import BasePage
    from baibao.autotest.api import ApiBase
    from baibao.autotest.login_state import LoginCfg, save_storage_state

依赖：playwright 为重依赖，按需懒加载，不在模块顶层导入。
安装：``pip install "baibao[autotest]"``。
"""

from . import api, browser, login_state, page
from .api import ApiBase
from .browser import detect_chrome_path, launch_browser
from .login_state import (
    LoginCfg,
    auth_state_path,
    do_login,
    is_auth_valid,
    save_storage_state,
)
from .page import BasePage

__all__ = [
    "ApiBase",
    "BasePage",
    "LoginCfg",
    "api",
    "auth_state_path",
    "browser",
    "detect_chrome_path",
    "do_login",
    "is_auth_valid",
    "launch_browser",
    "login_state",
    "page",
    "save_storage_state",
]
