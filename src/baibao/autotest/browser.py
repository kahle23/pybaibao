"""
browser.py — 本地 Chrome 路径探测与浏览器启动辅助。

提供跨平台的 Google Chrome 路径自动探测，以及基于 Playwright 的浏览器启动封装。
供 :mod:`baibao.autotest.fixtures` 与用户自定义 conftest 复用。

探测优先级：``CHROME_PATH`` 环境变量 → PATH 中的 chrome → OS 默认安装路径。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

__all__ = ["detect_chrome_path", "launch_browser"]


_CHROME_CANDIDATES_WIN = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]

_CHROME_CANDIDATES_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def detect_chrome_path(chrome_path_env: str | None = None) -> str | None:
    """自动探测本地 Chrome 路径。

    优先级：

      1. 显式传入的 ``chrome_path_env``（通常来自 ``CHROME_PATH`` 环境变量）
      2. PATH 中的 ``chrome`` / ``google-chrome``
      3. 操作系统默认安装路径

    Args:
        chrome_path_env: 显式指定的 Chrome 路径，为空则跳过。
    Returns:
        Chrome 可执行文件路径，未找到返回 ``None``。
    """
    if chrome_path_env and Path(chrome_path_env).exists():
        return chrome_path_env
    chrome_in_path = shutil.which("chrome") or shutil.which("google-chrome")
    if chrome_in_path:
        return chrome_in_path
    candidates = (
        _CHROME_CANDIDATES_WIN if sys.platform.startswith("win")
        else _CHROME_CANDIDATES_MAC
    )
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def launch_browser(
    playwright,
    *,
    headless: bool = False,
    slow_mo: int = 0,
    use_builtin_chromium: bool = False,
    chrome_path: str | None = None,
):
    """启动 Chromium 浏览器（自管理 Playwright 模式）。

    刻意**不**使用 pytest-playwright 的 ``context``/``page`` fixture，
    以避免 Element Plus el-select 在弹窗内的事件兼容问题
    （pytest-playwright 托管的 context 无法可靠触发 Vue pointerdown）。

    Args:
        playwright: ``sync_playwright().start()`` 返回的 Playwright 实例。
        headless: 是否无头模式。
        slow_mo: 慢放延迟（毫秒），调试用。
        use_builtin_chromium: True 走 Playwright 内置 Chromium
            （事件兼容性最好，需先 ``playwright install chromium``）；
            False 走本地已安装的 Google Chrome（默认）。
        chrome_path: 本地 Chrome 路径；为 ``None`` 时自动探测
            （通常传入 :func:`detect_chrome_path` 的结果）。
    Returns:
        Playwright ``Browser`` 实例，调用方负责 ``browser.close()``。
    """
    launch_kwargs: dict = {"headless": headless}
    if slow_mo > 0:
        launch_kwargs["slow_mo"] = slow_mo

    if use_builtin_chromium:
        # 不传 executable_path / channel，让 Playwright 自动找内置 Chromium
        pass
    elif chrome_path:
        launch_kwargs["executable_path"] = chrome_path
    else:
        launch_kwargs["channel"] = "chrome"

    return playwright.chromium.launch(**launch_kwargs)
