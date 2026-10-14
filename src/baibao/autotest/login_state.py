"""
login_state — 登录配置与登录态缓存。

把"登录流程"数据驱动化，把"登录态缓存"通用化：

  - :class:`LoginCfg` — 登录配置数据类（URL 后缀 + 各字段选择器 + 验证码开关）。
    默认值匹配若依/RuoYi 风格 hash 路由后台（``/#/login``、用户名/密码占位符、验证码）。
    非 RuoYi 站点改字段选择器即可，无需改源码。
  - :func:`do_login` — 按 :class:`LoginCfg` 执行登录 + 等待跳转。
  - :func:`auth_state_path` / :func:`is_auth_valid` / :func:`save_storage_state` — 登录态缓存。
    （storage_state 文件 + TTL，首次登录后复用，默认 12 小时）

依赖：playwright（运行时由调用方传入 Page/Browser）。
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .envutil import normalize_base_url

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page


@dataclass
class LoginCfg:
    """
    登录流程配置（数据驱动，适配不同后台）。

    默认值匹配若依/RuoYi 风格 hash 路由后台。非 RuoYi 站点改字段选择器即可。

    Attributes:
        login_url_suffix: 拼接到 ``base_url`` 后的登录页路径（hash 路由用 ``/#/login``）。
        username_selector: 用户名输入框选择器。
        password_selector: 密码输入框选择器。
        login_button_selector: 登录按钮选择器。
        captcha_selectors: 验证码输入框候选选择器（按顺序回退）。
            为空列表表示无验证码。
        success_url_not_contains: 登录成功后 URL 不再包含的片段（如 ``/login``，用于判断跳转完成）。
            token 型 SPA 可改用 ``success_token_key``（URL 跳转判定会被跳过）。
        viewport: 浏览器视口尺寸。
        login_button_text / login_button_scope / login_button_pick_last:
            按文字找登录钮（优先于 ``login_button_selector``）——表单内同文案多钮、
            主按钮无特征类名时用（scope 如 ``form:visible``，多钮取最后）。
        success_token_key: token 型成功信号——轮询 localStorage 出现该 key 即成功。
        success_timeout_ms: token 轮询上限（毫秒）。
        post_login_path: 登录成功后 goto 的路由（如 ``/#/``）。
        tolerant_waits: networkidle/加载等待失败不抛错改静置（hash 单页场景）。
    """

    login_url_suffix: str = "/#/login"
    username_selector: str = 'input[placeholder="用户名"]'
    password_selector: str = 'input[type="password"]'
    login_button_selector: str = "button.el-button--primary"
    captcha_selectors: list[str] = field(
        default_factory=lambda: [
            'input[placeholder="验证码"]',
            'input[placeholder*="验证码"]',
            'input[name="captcha"]',
            'input[name="code"]',
        ],
    )
    success_url_not_contains: str = "/login"
    viewport: dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    # ---- 以下为扩展配方（2026-10-14 自 12-SDI e2e 手写 _pre_login_state 收编）----
    # 按文字找登录钮（优先于 login_button_selector；login_button_scope 缩小范围，
    # 如 "form:visible"；同文案多钮时 login_button_pick_last=True 取最后一个）
    login_button_text: str = ""
    login_button_scope: str = ""
    login_button_pick_last: bool = False
    # 成功信号改为"轮询 localStorage 出现该 key"（token 型 SPA，URL 可能不跳转）；
    # 置空沿用 URL 跳转判定。轮询上限 success_timeout_ms。
    success_token_key: str = ""
    success_timeout_ms: int = 20000
    # 登录成功后 goto 的路由（如 "/#/"——主布局依赖首跳初始化的系统）；
    # post_login_settle_ms 为落地后的静置等待。
    post_login_path: str = ""
    post_login_settle_ms: int = 2000
    # networkidle/首屏等待失败不抛错（hash 单页长轮询场景），改静置等待
    tolerant_waits: bool = False


def do_login(
    page: "Page",
    cfg: LoginCfg,
    base_url: str,
    username: str,
    password: str,
    captcha: str = "",
) -> None:
    """
    按 :class:`LoginCfg` 执行登录并等待成功信号。

    成功判定二选一（由 ``cfg.success_token_key`` 决定）：

      - token 型：轮询 localStorage 出现该 key（``success_timeout_ms`` 上限）；
      - URL 型（默认）：URL 不再包含 ``success_url_not_contains`` + networkidle。

    ``cfg.post_login_path`` 非空时登录成功后再 goto 该路由（主布局初始化）。
    ``cfg.tolerant_waits`` 为 True 时 networkidle/加载等待失败不抛错改静置
    （hash 单页长轮询场景，脚本实证配方）。

    Args:
        page: Playwright ``Page`` 实例。
        cfg: 登录配置。
        base_url: 被测系统基础地址（末尾斜杠会被去除）。
        username: 用户名。
        password: 密码。
        captcha: 验证码（无验证码时留空；测试系统常仅校验非空）。
    """
    base = normalize_base_url(base_url)
    page.goto(f"{base}{cfg.login_url_suffix}")
    _settle_load(page, cfg)

    page.locator(cfg.username_selector).fill(username)
    page.locator(cfg.password_selector).fill(password)
    _fill_captcha(page, cfg, captcha)
    _click_login_button(page, cfg)

    if cfg.success_token_key:
        tok = ""
        for _ in range(int(cfg.success_timeout_ms / 1000)):
            page.wait_for_timeout(1000)
            tok = page.evaluate(
                "() => localStorage.getItem(%r) || ''" % cfg.success_token_key) or ""
            if tok:
                break
        if not tok:
            raise RuntimeError(
                f"login: localStorage[{cfg.success_token_key!r}] 未出现（登录链失败）")
    else:
        page.wait_for_url(
            lambda url: cfg.success_url_not_contains not in url, timeout=15000,
        )
        _settle_load(page, cfg)

    if cfg.post_login_path:
        page.goto(f"{base}{cfg.post_login_path}")
        _settle_load(page, cfg)
        page.wait_for_timeout(cfg.post_login_settle_ms)


def _settle_load(page: "Page", cfg: LoginCfg) -> None:
    """登录页/落地页的加载等待（tolerant_waits 时失败不抛，改固定静置）。"""
    if cfg.tolerant_waits:
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(1200)
    else:
        page.wait_for_load_state("networkidle")


def _click_login_button(page: "Page", cfg: LoginCfg) -> None:
    """点登录钮：login_button_text 优先（文字 + 可选范围），否则 login_button_selector。"""
    if cfg.login_button_text:
        loc = page.locator(cfg.login_button_scope or "button", has_text=cfg.login_button_text)
        (loc.last if cfg.login_button_pick_last else loc.first).click()
    else:
        page.locator(cfg.login_button_selector).click()


def _fill_captcha(page: "Page", cfg: LoginCfg, captcha: str) -> None:
    """
    填写验证码（多候选选择器回退）。无候选或都不可见则跳过。
    """
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


def auth_state_path(auth_dir: Path, account: str) -> Path:
    """
    登录态缓存文件路径：``<auth_dir>/<account>.json``。

    ``account`` 是**登录态槽位**（一个命名槽同一时刻绑定一个账号身份），
    不是系统权限角色——多账号并存用不同 account 名（如 ``admin``/``a``/``b``）。
    """
    return auth_dir / f"{account}.json"


def _read_auth_meta(path: Path) -> dict[str, Any] | None:
    """
    读登录态旁写元数据（``<account>.meta.json``）。不存在/损坏返回 None。
    """
    try:
        return cast("dict[str, Any] | None", json.loads(
            path.with_suffix(".meta.json").read_text(encoding="utf-8"),
        ))
    except (OSError, json.JSONDecodeError):
        return None


def is_auth_valid(
    path: Path,
    max_age_hours: int = 12,
    username: str | None = None,
    base_url: str | None = None,
) -> bool:
    """
    登录态缓存是否有效（文件存在、未超 TTL、且身份匹配）。

    身份校验：:func:`save_storage_state` 保存登录态时会旁写 ``<account>.meta.json``（username/base_url）。
    调用方传入 ``username``/``base_url`` 时与 meta 比对，不一致（或 meta 缺失、无法证明同一身份）判无效——否则同一 account 槽位会跨账号串用。
    （典型坑：probe 换 ADMIN_USERNAME 后仍拿旧账号登录态，探出错误视角的页面结论，2026-08-28 IMP 实坑）不传时保持旧行为（仅年龄判断，兼容旧调用方）。

    Args:
        path: 缓存文件路径。
        max_age_hours: 最大有效时长（小时），默认 12。
        username: 期望的登录用户名；传了才做身份比对。
        base_url: 期望的被测系统地址；传了才做比对。
    """
    if not path.exists():
        return False
    if username is not None or base_url is not None:
        meta = _read_auth_meta(path)
        if not meta:
            return False
        if username is not None and meta.get("username") != username:
            return False
        if base_url is not None and meta.get("base_url") != normalize_base_url(base_url):
            return False
    age = time.time() - path.stat().st_mtime
    return age < max_age_hours * 3600


def save_storage_state(
    browser: "Browser",
    cfg: LoginCfg,
    auth_dir: Path,
    account: str,
    base_url: str,
    username: str,
    password: str,
    captcha: str = "",
) -> str:
    """
    登录并保存 storage_state 到缓存文件。

    组合流程：建临时 context → :func:`do_login` → ``storage_state(path=...)`` → 关 context。缓存失效后由调用方重新触发。

    Args:
        browser: Playwright ``Browser`` 实例。
        cfg: 登录配置。
        auth_dir: 缓存目录（不存在则创建）。
        account: 账号名——**登录态槽位**（用于文件命名，如 ``admin``/``a``/``b``），
            非系统权限角色；一个槽位同一时刻绑定一个账号身份，换账号由身份校验触发重登覆盖。
        base_url: 被测系统基础地址。
        username: 登录用户名。
        password: 登录密码。
        captcha: 验证码。

    Returns:
        缓存文件路径字符串（传给 ``browser.new_context(storage_state=...)``）。
    """
    auth_dir.mkdir(parents=True, exist_ok=True)
    state_file = auth_state_path(auth_dir, account)

    context = browser.new_context(viewport=cfg.viewport)  # type: ignore[arg-type]
    page = context.new_page()
    try:
        do_login(page, cfg, base_url, username, password, captcha)
        context.storage_state(path=str(state_file))
    finally:
        context.close()

    # 旁写身份元数据：is_auth_valid 传 username/base_url 时用于跨账号串用防护
    state_file.with_suffix(".meta.json").write_text(
        json.dumps({
            "username": username,
            "base_url": normalize_base_url(base_url),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    return str(state_file)


def login_context(
    browser: "Browser",
    cfg: LoginCfg,
    auth_dir: Path,
    account: str,
    base_url: str,
    username: str,
    password: str,
    captcha: str = "",
) -> tuple[Any, "Page"]:
    """
    一站式登录入口：缓存有效直接复用，失效现场登录落盘，返回带登录态的 (context, page)。

    12-SDI e2e 十三份模板的 ``login_page(browser, role)`` 即此函数的IMP 参数化版本。

    Args:
        browser: Playwright ``Browser`` 实例。
        cfg: 登录配置。
        auth_dir: 登录态缓存目录。
        account: 登录态槽位名（缓存文件名，非权限角色）。
        base_url: 被测系统基础地址。
        username: 登录用户名（同时用于缓存身份校验）。
        password: 登录密码。
        captcha: 验证码。

    Returns:
        ``(context, page)``——context 已带 storage_state 与 cfg.viewport。
    """
    state_path = auth_state_path(auth_dir, account)
    if not is_auth_valid(state_path, username=username, base_url=base_url or None):
        state_path = Path(save_storage_state(
            browser, cfg, auth_dir, account, base_url, username, password, captcha,
        ))
    ctx = browser.new_context(storage_state=str(state_path), viewport=cfg.viewport)  # type: ignore[arg-type]
    return ctx, ctx.new_page()
