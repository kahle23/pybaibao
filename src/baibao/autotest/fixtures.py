"""
fixtures.py — 可选启用的 pytest fixture（自管理 Playwright 模式）。

启用方式：在项目根 ``conftest.py`` 加一行::

    pytest_plugins = ["baibao.autotest.fixtures"]

提供的 fixture：

  - ``base_url`` / ``is_headless`` / ``slow_mo`` (session) — 环境变量驱动
  - ``playwright`` / ``browser`` (session) — 自管理 Playwright 生命周期
  - ``today_str`` / ``faker`` / ``unique_id`` (function) — 通用测试数据

**不**提供角色级 fixture（``storage_state`` / ``page`` / ``api_context``），
它们与具体角色和登录流程相关，请在项目 conftest 中基于
:mod:`baibao.autotest.login_state` 自行实例化，参考
:mod:`baibao.autotest.conftest_template`。

刻意**不**使用 pytest-playwright 的 ``context`` / ``page`` fixture，
以避免 Element Plus el-select 在弹窗内的事件兼容问题
（pytest-playwright 托管的 context 无法可靠触发 Vue pointerdown）。

依赖：需安装 ``baibao[autotest]``（playwright / python-dotenv / faker）。
"""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pytest

# 可选加载项目根 .env（python-dotenv 未安装则跳过，直接读 os.environ）
try:
    from dotenv import load_dotenv
    _env_file = Path.cwd() / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass


def _cfg(key: str, default: str = "") -> str:
    """读取环境变量配置。"""
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# 基础配置 fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url() -> str:
    """被测系统基础地址（环境变量 ``BASE_URL``）。"""
    return _cfg("BASE_URL", "http://localhost:8080").rstrip("/")


@pytest.fixture(scope="session")
def is_headless() -> bool:
    """是否无头模式（环境变量 ``HEADLESS``，默认 false）。"""
    return _cfg("HEADLESS", "false").lower() == "true"


@pytest.fixture(scope="session")
def slow_mo() -> int:
    """慢放延迟毫秒（环境变量 ``SLOW_MO``，默认 0）。"""
    try:
        return int(_cfg("SLOW_MO", "0"))
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Playwright 生命周期（session 级，自管理）
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def playwright():
    """session 级启动 Playwright。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright, is_headless, slow_mo):
    """session 级启动浏览器。

    通过环境变量 ``USE_BUILTIN_CHROMIUM`` 切换：

      - ``true``  → 走 Playwright 内置 Chromium（需先 ``playwright install chromium``）
      - ``false`` → 走本地已安装的 Google Chrome（默认，自动探测路径）
    """
    from baibao.autotest.browser import detect_chrome_path, launch_browser

    use_builtin = _cfg("USE_BUILTIN_CHROMIUM", "false").lower() == "true"
    chrome_path = None if use_builtin else detect_chrome_path(
        _cfg("CHROME_PATH") or None,
    )
    browser = launch_browser(
        playwright,
        headless=is_headless,
        slow_mo=slow_mo,
        use_builtin_chromium=use_builtin,
        chrome_path=chrome_path,
    )
    yield browser
    browser.close()


# ---------------------------------------------------------------------------
# 测试数据辅助 fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def today_str() -> str:
    """今天的 ISO 日期字符串（``YYYY-MM-DD``）。"""
    return date.today().isoformat()


@pytest.fixture()
def unique_id() -> str:
    """唯一 ID：``TEST-<时间戳>``。需自定义前缀请在项目 conftest 自建 fixture。"""
    return f"TEST-{int(time.time())}"


@pytest.fixture()
def faker():
    """``Faker("zh_CN")`` 实例（中文假数据生成）。

    依赖 ``faker`` 包（已含在 ``baibao[autotest]`` extra）。
    pip 装 faker 在国内默认镜像可能失败，建议用清华源：
    ``pip install faker -i https://pypi.tuna.tsinghua.edu.cn/simple/``
    """
    from faker import Faker

    return Faker("zh_CN")
