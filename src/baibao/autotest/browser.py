"""
browser — 浏览器启动辅助（内置 Chromium 优先 + 本地浏览器兜底）。

提供跨平台的 Google Chrome 路径自动探测，以及基于 Playwright 的浏览器启动封装：
:func:`launch_browser`（普通启动，返回 Browser）与 :func:`launch_browser_persistent`
（持久化上下文，返回绑定 user_data_dir 的 BrowserContext，风控敏感站点"低调运行"姿势）。
供 :mod:`baibao.autotest.fixtures` 与用户自定义 conftest 复用。

浏览器选择链（默认自动模式）：Playwright 内置 Chromium（自动化事件兼容性最好，缺失自动下载）→ 本地 Chrome → Edge。
只启动 Chromium 系（Firefox/WebKit 内核的 Page 亦可使用本包其余设施，真实输入由 :mod:`.devtools` 按内核分流）。
"""

import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Playwright

T = TypeVar("T")


# 自动安装内置内核时的默认下载镜像（尊重用户已设置的 PLAYWRIGHT_DOWNLOAD_HOST）
_PW_MIRROR_DEFAULT = "https://cdn.npmmirror.com/binaries/playwright"


_CHROME_CANDIDATES_WIN = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]

_CHROME_CANDIDATES_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def detect_chrome_path(chrome_path_env: str | None = None) -> str | None:
    """
    自动探测本地 Chrome 路径。

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


def _install_builtin_kernel(headless: bool) -> bool:
    """
    兜底自动安装 Playwright 内置浏览器内核（本地 Chrome/Edge 都缺失时）。

    - 无头场景优先只装 ``chromium-headless-shell``（轻量，约完整内核三分之一）；
      playwright < 1.49 不识别 ``--only-shell`` 时降级装完整内核。
    - 下载源依次尝试：npmmirror 镜像（快，但存在版本同步空洞，如缺 v1208）→ 官方源（``cdn.playwright.dev``，实测多数网络可达）。
      ``PLAYWRIGHT_DOWNLOAD_HOST`` 已被显式设置时尊重用户配置，只试该源。
    - 任何失败都返回 False（调用方继续走原始报错），不影响主流程。
    """
    import subprocess

    if os.environ.get("PLAYWRIGHT_DOWNLOAD_HOST"):
        env_list = [dict(os.environ)]
    else:
        env_list = [
            dict(os.environ, PLAYWRIGHT_DOWNLOAD_HOST=_PW_MIRROR_DEFAULT),
            dict(os.environ),
        ]
    cmd_base = [sys.executable, "-m", "playwright", "install", "chromium"]
    # 无头优先轻量 shell；--only-shell 不兼容（旧版）时再试完整内核
    cmd_variants = [cmd_base + ["--only-shell"], cmd_base] if headless else [cmd_base]
    try:
        for cmd in cmd_variants:
            for env in env_list:
                done = subprocess.run(
                    cmd, env=env, capture_output=True, timeout=900, check=False,
                ).returncode == 0
                if done:
                    return True
    except Exception:
        return False
    return False


def _run_chromium_chain(
    launch: Callable[[dict[str, Any]], T],
    *,
    headless: bool,
    use_builtin_chromium: bool | None,
    chrome_path: str | None,
) -> T:
    """
    按浏览器选择链执行 ``launch`` 回调，返回 Browser / BrowserContext。

    ``launch`` 接收本链附加的启动参数（``executable_path`` / ``channel``），
    负责并入完整调用——:func:`launch_browser` 与 :func:`launch_browser_persistent`
    共用同一条链，保证两者浏览器选择行为一致。

    链序（默认 ``use_builtin_chromium=None`` 自动模式）：

      1. 内置 Chromium（缺失自动下载，``BAIBAO_BROWSER_AUTO_INSTALL=false`` 关闭）
      2. 下载失败 → 显式 ``chrome_path`` → 本地 Chrome → Edge（仅 Chromium 系）
      3. 都失败 → 最后一次不带捕获，抛出带 channel 信息的原始错误
    """
    if use_builtin_chromium is None or use_builtin_chromium is True:
        try:
            return launch({})
        except Exception:
            auto_installed = (
                os.getenv("BAIBAO_BROWSER_AUTO_INSTALL", "").lower() != "false"
                and _install_builtin_kernel(headless)
            )
            if auto_installed:
                return launch({})
            if use_builtin_chromium is True:
                # 显式要求内置但装不上：如实抛错，不静默换浏览器
                raise
            # 自动模式：下载失败 → 继续本地浏览器链兜底

    if chrome_path:
        return launch({"executable_path": chrome_path})

    for channel in ("chrome", "msedge"):
        try:
            return launch({"channel": channel})
        except Exception:
            continue
    # 都失败：再按 chrome 试一次，不带捕获，抛出带 channel 信息的原始错误
    return launch({"channel": "chrome"})


def launch_browser(
    playwright: "Playwright",
    *,
    headless: bool = False,
    slow_mo: int = 0,
    use_builtin_chromium: bool | None = None,
    chrome_path: str | None = None,
    args: list[str] | None = None,
    window_size: str | None = None,
) -> "Browser":
    """
    启动浏览器（自管理 Playwright 模式）。

    刻意**不**使用 pytest-playwright 的 ``context``/``page`` fixture。
    原因：Element Plus el-select 在弹窗内的事件兼容问题（pytest-playwright 托管的 context 无法可靠触发 Vue pointerdown）。

    浏览器选择链（默认 ``use_builtin_chromium=None`` 自动模式）：

      1. **Playwright 内置 Chromium 优先**（自动化事件兼容性最好）；
         未安装则自动下载（镜像优先、官方回退，``BAIBAO_BROWSER_AUTO_INSTALL=false`` 关闭）
      2. 下载失败 → 本地浏览器兜底：显式 ``chrome_path`` → Chrome → Edge（只考虑 Chromium 系，CDP 点击仅 Chromium 支持）
      3. 都失败 → 抛出带 channel 信息的原始错误

    Args:
        playwright: ``sync_playwright().start()`` 返回的 Playwright 实例。
        headless: 是否无头模式，默认 **False（有头）**——用户不强调一律有头。
        slow_mo: 慢放延迟（毫秒），调试用。
        use_builtin_chromium: ``None``（默认）自动模式（内置优先 → 自动下载 → 本地兜底）；``True`` 强制内置（缺失自动下载，失败抛错）；
            ``False`` 跳过内置，直接走本地浏览器链（不触发自动下载）。
        chrome_path: 本地 Chrome 路径（仅本地链使用）；为 ``None`` 时按 channel 自动探测。

    Returns:
        Playwright ``Browser`` 实例，调用方负责 ``browser.close()``。

    窗口尺寸（``window_size``）——**默认 auto 铺满，框架默认 1280×720 只是兜底**：

      - 默认 ``None`` / ``"auto"``：启动前按 OS 当前会话实测主屏分辨率，转成与显式
        ``"宽x高"`` 完全相同的铺满参数（无头时自动跳过）；
      - ``"宽x高"``（如 ``"1920x1080"``）：显式注入 ``--window-position=0,0``
        + ``--window-size=宽,高`` + ``--force-device-scale-factor=1``；
      - ``"default"``：不注入任何窗口参数，回到框架默认 1280×720（低配/特殊场景兜底）。

      背景（为什么 WxH 必须带 force-scale-factor）：Windows 显示缩放 ≠100% 时
      Chromium 按**逻辑坐标**解释 ``--window-size``——150% 缩放下逻辑全屏只有
      1280×720，传 1920,1080 会被钳回 1280×720（RDP 会话同理不可靠）；
      ``--force-device-scale-factor=1`` 让逻辑=物理，WxH 才是真实尺寸。
      需求尺寸不能超过物理屏幕（系统级钳制，代码绕不过）。

      auto 为什么在 OS 层实测、而不是启动后页面里读 ``screen.width``：
      Playwright context 默认带 viewport 仿真，服务端会同时下发
      ``Emulation.setDeviceMetricsOverride`` 与 ``Page.setScreenSizeOverride``，
      把 ``window.screen`` 一并仿真成 viewport 尺寸——非持久 context 即使传
      ``viewport=None``，服务端也会补回默认 1280×720，页面实测永远 720p；
      且启动后用 CDP 改临时窗口大小传导不到后续 context 的新窗口。
      只有启动参数能一次铺满所有后续窗口；OS 实测失败（无显示器/探测异常）
      才回退 "default"——框架 1280×720 是最后兜底。

      AI 观察阶梯：用户没提窗口 → 默认（auto 铺满）；用户说"窗口太小" → 显式
      ``"宽x高"``（一般 ``"1920x1080"``）；用户仍说小 → 停下问用户实际环境
      （分辨率/远程桌面/缩放比例），不要盲目加大。
    """

    # 窗口尺寸：默认 auto 铺满；"default"=框架默认 1280×720（兜底逃生门）。
    # 无头无窗口概念，auto 无意义（显式 WxH 仍照传）。
    if headless and (window_size is None or window_size.strip().lower() == "auto"):
        ws = "default"
    else:
        ws = (window_size or "auto").strip().lower()
    # auto → 启动前 OS 实测主屏，复用显式 WxH 的铺满参数链
    if ws == "auto":
        detected = _detect_screen_size()
        ws = f"{detected[0]}x{detected[1]}" if detected else "default"

    def launch(extra: dict[str, Any]) -> "Browser":
        launch_kwargs: dict[str, Any] = {"headless": headless, **extra}
        if slow_mo > 0:
            launch_kwargs["slow_mo"] = slow_mo
        merged_args = list(args) if args else []
        # 调用方显式传过 --window-size 时不覆盖（调用方优先）
        if ws and ws not in ("default", "none", "auto") and not any(a.startswith("--window-size") for a in merged_args):
            w, sep, h = ws.partition("x")
            if not (sep and w.isdigit() and h.isdigit()):
                raise ValueError(
                    "window_size 仅支持 'auto' / 'default' / '宽x高'（如 '1920x1080'），"
                    f"收到: {window_size!r}"
                )
            merged_args = [
                "--window-position=0,0",
                f"--window-size={w},{h}",
                "--force-device-scale-factor=1",
                *merged_args,
            ]
        if merged_args:
            launch_kwargs["args"] = merged_args
        return playwright.chromium.launch(**launch_kwargs)

    browser = _run_chromium_chain(
        launch,
        headless=headless,
        use_builtin_chromium=use_builtin_chromium,
        chrome_path=chrome_path,
    )
    return browser


def _detect_screen_size() -> tuple[int, int] | None:
    """OS 级探测当前会话主屏分辨率（物理像素，尽力而为，失败返回 None）。

    天然跟随当前会话：RDP 断开重连、分辨率切换后重跑即得新值。
    不能改成页面里读 ``screen.width`` 实测——Playwright 会把 ``window.screen``
    仿真成 context viewport（默认 1280×720），实测永远拿到仿真值（详见
    :func:`launch_browser` 的窗口尺寸说明）。
    """
    try:
        if sys.platform.startswith("win"):
            import ctypes

            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            # DPI 虚拟化：DPI-unaware 进程拿到的是逻辑像素，乘系统缩放比还原物理；
            # 进程本身 DPI-aware 时拿到的已是物理值，放大后由系统钳回屏幕，结果同为铺满。
            try:
                scale = ctypes.windll.shcore.GetScaleFactorForDevice(0)
                width = round(width * scale / 100)
                height = round(height * scale / 100)
            except Exception:
                pass
            if width > 0 and height > 0:
                return width, height
        else:
            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            width, height = root.winfo_screenwidth(), root.winfo_screenheight()
            root.destroy()
            if width > 0 and height > 0:
                return width, height
    except Exception:
        return None
    return None


def launch_browser_persistent(
    playwright: "Playwright",
    *,
    user_data_dir: str | Path,
    headless: bool = False,
    slow_mo: int = 0,
    locale: str = "zh-CN",
    viewport: dict[str, int] | None = None,
    args: list[str] | None = None,
    use_builtin_chromium: bool | None = None,
    chrome_path: str | None = None,
) -> "BrowserContext":
    """
    启动**持久化上下文**浏览器（风控敏感站点的"低调运行"默认姿势）。

    与 :func:`launch_browser` 的区别：直接返回绑定 ``user_data_dir`` 的 BrowserContext，
    整个用户数据目录（cookies / localStorage / IndexedDB / 设备指纹）跨进程保留——
    同一目录反复使用即"会话连续"，像一个真人浏览器在多次访问，而不是每次新开
    一个无历史的干净实例（后者正是风控眼里的典型异常）。

    低调默认值：有头（``headless=False``）、不模拟 viewport（页面跟随真实窗口）、
    自动追加 ``--disable-blink-features=AutomationControlled``。
    这些只是让行为更像真人、降低风控触发**概率**，不是破解风控——
    验证码/滑块仍应由用户手动通过。

    浏览器选择链与 :func:`launch_browser` 一致（内置 Chromium → 自动下载 → 本地 Chrome → Edge）。

    Args:
        playwright: ``sync_playwright().start()`` 返回的 Playwright 实例。
        user_data_dir: 用户数据目录（登录态与指纹的持久化根），建议放入 .gitignore。
        headless: 是否无头，默认 **False（有头）**——风控敏感站默认有头。
        slow_mo: 慢放延迟（毫秒），调试用。
        locale: 区域设置，默认 ``zh-CN``。
        viewport: 视口模拟；``None``（默认）= 不模拟，跟随真实窗口尺寸（更像真人）。
        args: 额外 Chromium 启动参数；默认追加 ``--disable-blink-features=AutomationControlled``（调用方已含则不重复）。
        use_builtin_chromium: 同 :func:`launch_browser`。
        chrome_path: 同 :func:`launch_browser`。

    Returns:
        Playwright ``BrowserContext``（调用方负责 ``ctx.close()``；持久化数据随 close 落盘）。
    """
    if args is None:
        args = []
    if "--disable-blink-features=AutomationControlled" not in args:
        args = [*args, "--disable-blink-features=AutomationControlled"]
    user_data_dir = os.fspath(user_data_dir)

    def launch(extra: dict[str, Any]) -> "BrowserContext":
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": user_data_dir,
            "headless": headless,
            "locale": locale,
            "args": args,
            **extra,
        }
        if slow_mo > 0:
            launch_kwargs["slow_mo"] = slow_mo
        if viewport is not None:
            launch_kwargs["viewport"] = viewport
        return playwright.chromium.launch_persistent_context(**launch_kwargs)

    return _run_chromium_chain(
        launch,
        headless=headless,
        use_builtin_chromium=use_builtin_chromium,
        chrome_path=chrome_path,
    )
