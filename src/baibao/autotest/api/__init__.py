"""
api — 后端接口调用骨架。

  - :class:`ApiBase` — Playwright ``APIRequestContext`` 版（复用浏览器 cookie）。
  - :class:`TokenSession` — 纯 requests 版（captcha 登录 + token 头 +
    401 自动重登重放；与浏览器登录态缓存 ``.auth/`` 互通）。

包接管原 ``baibao.autotest.api`` 模块名，旧导入路径不变。
"""

from .base import ApiBase
from .token_session import TokenSession, TokenSessionCfg

__all__ = ["ApiBase", "TokenSession", "TokenSessionCfg"]
