"""
login_state.py — 登录配置与登录态缓存。

把"登录流程"数据驱动化，把"登录态缓存"通用化：

  - :class:`LoginCfg` — 登录配置数据类（URL 后缀 + 各字段选择器 + 验证码开关）。
    默认值匹配若依/RuoYi 风格 hash 路由后台（``/#/login``、用户名/密码占位符、验证码）。
    非 RuoYi 站点改字段选择器即可，无需改源码。
  - :func:`do_login` — 按 :class:`LoginCfg` 执行登录 + 等待跳转。
  - :func:`auth_state_path` / :func:`is_auth_valid` / :func:`save_storage_state` —
    登录态缓存（storage_state 文件 + TTL，首次登录后复用，默认 12 小时）。

依赖：playwright（运行时由调用方传入 Page/Browser）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page

__all__ = [
    "LoginCfg",
    "auth_state_path",
    "do_login",
    "is_auth_valid",
    "save_storage_state",
]


@dataclass
class LoginCfg:
    """登录流程配置（数据驱动，适配不同后台）。

    默认值匹配若依/RuoYi 风格 hash 路由后台。非 RuoYi 站点改字段选择器即可。

    Attributes:
        login_url_suffix: 拼接到 ``base_url`` 后的登录页路径（hash 路由用 ``/#/login``）。
        username_selector: 用户名输入框选择器。
        password_selector: 密码输入框选择器。
        login_button_selector: 登录按钮选择器。
        captcha_selectors: 验证码输入框候选选择器（按顺序回退）。
            为空列表表示无验证码。
        success_url_not_contains: 登录成功后 URL 不再包含的片段
            （如 ``/login``，用于判断跳转完成）。
        viewport: 浏览器视口尺寸。
    """

    login_url_suffix: str = "/#/login"
    username_selector: str = 'input[placeholder="用户名"]'
    password_selector: str = 'input[type="password"]'
    login_button_selector: str = 'button.el-button--primary'
    captcha_selectors: list[str] = field(
        default_factory=lambda: [
            'input[placeholder="验证码"]',
            'input[placeholder*="验证码"]',
            'input[name="captcha"]',
            'input[name="code"]',
        ],
    )
    success_url_not_contains: str = "/login"
    viewport: dict = field(default_factory=lambda: {"width": 1920, "height": 1080})


def do_login(
    page: Page,
    cfg: LoginCfg,
    base_url: str,
    username: str,
    password: str,
    captcha: str = "",
) -> None:
    """按 :class:`LoginCfg` 执行登录并等待跳转完成。

    Args:
        page: Playwright ``Page`` 实例。
        cfg: 登录配置。
        base_url: 被测系统基础地址（末尾斜杠会被去除）。
        username: 用户名。
        password: 密码。
        captcha: 验证码（无验证码时留空；测试系统常仅校验非空）。
    """
    page.goto(f"{base_url.rstrip('/')}{cfg.login_url_suffix}")
    page.wait_for_load_state("networkidle")

    page.locator(cfg.username_selector).fill(username)
    page.locator(cfg.password_selector).fill(password)
    _fill_captcha(page, cfg, captcha)
    page.locator(cfg.login_button_selector).click()

    page.wait_for_url(
        lambda url: cfg.success_url_not_contains not in url, timeout=15000,
    )
    page.wait_for_load_state("networkidle")


def _fill_captcha(page: Page, cfg: LoginCfg, captcha: str) -> None:
    """填写验证码（多候选选择器回退）。无候选或都不可见则跳过。"""
    if not cfg.captcha_selectors:
        return
    for sel in cfg.captcha_selectors:
        loc = page.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=1500)
            loc.fill(captcha)
            return
        except Exception:
            continue


def auth_state_path(auth_dir: Path, role: str) -> Path:
    """登录态缓存文件路径：``<auth_dir>/<role>.json``。"""
    return auth_dir / f"{role}.json"


def is_auth_valid(path: Path, max_age_hours: int = 12) -> bool:
    """登录态缓存是否有效（文件存在且未超 TTL）。

    Args:
        path: 缓存文件路径。
        max_age_hours: 最大有效时长（小时），默认 12。
    """
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < max_age_hours * 3600


def save_storage_state(
    browser: Browser,
    cfg: LoginCfg,
    auth_dir: Path,
    role: str,
    base_url: str,
    username: str,
    password: str,
    captcha: str = "",
) -> str:
    """登录并保存 storage_state 到缓存文件。

    组合流程：建临时 context → :func:`do_login` → ``storage_state(path=...)``
    → 关 context。缓存失效后由调用方重新触发。

    Args:
        browser: Playwright ``Browser`` 实例。
        cfg: 登录配置。
        auth_dir: 缓存目录（不存在则创建）。
        role: 角色名（用于文件命名，如 ``admin``/``employee1``）。
        base_url: 被测系统基础地址。
        username: 登录用户名。
        password: 登录密码。
        captcha: 验证码。
    Returns:
        缓存文件路径字符串（传给 ``browser.new_context(storage_state=...)``）。
    """
    auth_dir.mkdir(parents=True, exist_ok=True)
    state_file = auth_state_path(auth_dir, role)

    context = browser.new_context(viewport=cfg.viewport)  # type: ignore[arg-type]
    page = context.new_page()
    try:
        do_login(page, cfg, base_url, username, password, captcha)
        context.storage_state(path=str(state_file))
    finally:
        context.close()

    return str(state_file)
