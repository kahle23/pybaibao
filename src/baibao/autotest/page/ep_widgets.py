"""
ep_widgets — Element Plus 弹层清场自由函数族。

把"ESC/取消链关闭 message-box、取消钮链关闭 dialog、headerbtn 链关闭 drawer、
返回链关闭全页 overlay、toast 捕捉/读取"的重复模式收成**自由函数**（收 ``page``，
不建页对象）——与 :class:`baibao.autotest.page.BasePage` 的实例方法版互补：
独立脚本式 E2E 直接调函数；BasePage 的同名方法是本模块的薄委托（实现单点）。

来源：12-SDI e2e 模板每份内嵌约 250~300 行的"弹层清场链"（26092419 校准口径）。
清场顺序约定（:func:`close_any_dialog`）：message-box → dialog → drawer → overlay。

IMP 页面特化点已参数化为带默认值的参数（overlay 类名、返回钮选择器、
遮挡检测的按钮范围），非 IMP 项目按页面改参即可。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def ensure_no_dialog(page: "Page", rounds: int = 4) -> None:
    """
    清残留 el-message-box：优先点「取消」，无则 ESC；最多 ``rounds`` 轮。
    """
    for _ in range(rounds):
        if page.locator(".el-message-box:visible").count() == 0:
            return
        try:
            box = page.locator(".el-message-box:visible").first
            cancel = box.locator("button:has-text('取消')")
            if cancel.count():
                cancel.first.click()
            else:
                page.keyboard.press("Escape")
        except Exception:
            page.keyboard.press("Escape")
        page.wait_for_timeout(500)


def confirm_box_cancel(page: "Page", expect_frag: str | None = None) -> tuple[str, bool]:
    """
    断言文案片段后**只点取消**（负向/防误触用例）。

    Returns:
        ``(文案, 已关)``——文案不符也清场，此时已关为 False。
    """
    mb = page.locator(".el-message-box:visible")
    txt = (mb.first.inner_text() or "").strip() if mb.count() else ""
    if expect_frag and expect_frag not in txt:
        ensure_no_dialog(page)
        return txt, False
    cancelled = False
    if mb.count():
        cancel_btn = mb.first.locator("button:has-text('取消')")
        if cancel_btn.count():
            cancel_btn.first.click()
        for _ in range(6):
            page.wait_for_timeout(500)
            if page.locator(".el-message-box:visible").count() == 0:
                cancelled = True
                break
    ensure_no_dialog(page)
    return txt, cancelled


def confirm_box_accept(page: "Page", expect_frag: str | None = None) -> str:
    """
    受控写用：断言文案后点「确定」并等关闭。

    Returns:
        文案全文；文案不符时末尾追加 ``[文案不符]`` 标记。
    """
    mb = page.locator(".el-message-box:visible")
    if not mb.count():
        return ""
    txt = (mb.first.inner_text() or "").strip()
    ok_frag = (not expect_frag) or (expect_frag in txt)
    btn = mb.first.locator("button:has-text('确定')")
    if btn.count():
        btn.first.click()
    for _ in range(6):
        page.wait_for_timeout(500)
        if page.locator(".el-message-box:visible").count() == 0:
            break
    ensure_no_dialog(page)
    return txt if ok_frag else (txt + "[文案不符]")


def close_dialog(page: "Page", rounds: int = 6) -> None:
    """
    链式关闭全部可见 el-dialog：footer「取消」→ headerbtn → ESC，最多 ``rounds`` 轮。
    """
    for _ in range(rounds):
        dlg = page.locator(".el-dialog:visible")
        if not dlg.count():
            return
        try:
            d = dlg.last
            cancel = d.locator(".el-dialog__footer button:has-text('取消')")
            if cancel.count():
                cancel.first.click(timeout=3000)
            else:
                hdr = d.locator(".el-dialog__headerbtn")
                if hdr.count():
                    hdr.first.click(timeout=3000)
                else:
                    page.keyboard.press("Escape")
            page.wait_for_timeout(700)
        except Exception:
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
    if page.locator(".el-dialog:visible").count():
        print("  [close_dialog] 仍有 .el-dialog:visible 残留（已放弃重试）", flush=True)


def close_drawer(page: "Page", rounds: int = 6) -> None:
    """
    链式关闭全部 el-drawer：headerbtn/关闭钮 → ESC，最多 ``rounds`` 轮。
    """
    for _ in range(rounds):
        dr = page.locator(".el-drawer.open")
        if not dr.count():
            return
        try:
            btn = dr.last.locator(".el-drawer__headerbtn, .el-drawer__close-btn")
            if btn.count():
                btn.first.click(timeout=4000)
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(700)
        except Exception:
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
    if page.locator(".el-drawer.open").count():
        print("  [close_drawer] 仍有 .el-drawer.open 残留（已放弃重试）", flush=True)


def overlay_visible(page: "Page", selector: str = ".page-overlay") -> bool:
    """
    全页 overlay 是否可见（按宽度 > 0 判定；evaluate 异常按不可见）。
    """
    try:
        return bool(page.evaluate(
            "(s) => [...document.querySelectorAll(s)]"
            ".some(e => e.getBoundingClientRect().width > 0)", selector))
    except Exception:
        return False


def close_overlay(
    page: "Page",
    back_selectors: tuple[str, ...] = (".head-card .back-btn:visible",
                                       ".el-page-header__back:visible"),
    selector: str = ".page-overlay",
) -> None:
    """
    关闭全页 overlay：依次尝试返回钮候选，兜底 ESC，最多 6 轮。
    """
    for _ in range(6):
        if not overlay_visible(page, selector):
            return
        clicked = False
        for sel in back_selectors:
            try:
                loc = page.locator(sel)
                if loc.count():
                    loc.first.click(timeout=3000)
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
        page.wait_for_timeout(700)


def close_any_dialog(
    page: "Page",
    back_selectors: tuple[str, ...] = (".head-card .back-btn:visible",
                                       ".el-page-header__back:visible"),
    overlay_selector: str = ".page-overlay",
) -> None:
    """
    全量清场链：message-box → dialog → drawer → overlay。
    """
    ensure_no_dialog(page)
    close_dialog(page)
    close_drawer(page)
    close_overlay(page, back_selectors, overlay_selector)


def click_blocked(
    page: "Page",
    buttons_selector: str = ".query-panel .qp-actions button, .chips button",
) -> bool:
    """
    可见按钮是否被透明遮罩挡住（elementFromPoint 命中他者；异常按"被挡"返回）。
    """
    try:
        return bool(page.evaluate(
            """(s) => {
                 const els = [...document.querySelectorAll(s)]
                   .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
                 for (const b of els.slice(0, 3)) {
                   const r = b.getBoundingClientRect();
                   const el = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
                   if (el && !b.contains(el) && !el.contains(b)) return true;
                 }
                 return false;
             }""", buttons_selector))
    except Exception:
        return True


def hard_reset(
    page: "Page",
    reset_url: str = "",
    base_url: str = "",
    buttons_selector: str = ".query-panel .qp-actions button, .chips button",
) -> None:
    """
    硬复位：清场后仍有弹层残留/按钮被挡时，goto + reload 真刷新（keep-alive 修法）。

    Args:
        page: Playwright ``Page``。
        reset_url: 复位目标路由（如 ``/prod/plan-demand``；空串只清场不刷新）。
        base_url: 拼 ``reset_url`` 用的基础地址（空串视为 ``reset_url`` 是完整 URL）。
        buttons_selector: 遮挡检测的按钮范围。
    """
    close_any_dialog(page)
    try:
        residual = (page.locator(".el-dialog:visible").count()
                    or page.locator(".el-drawer.open").count()
                    or page.locator(".el-message-box:visible").count()
                    or overlay_visible(page))
        if (residual or click_blocked(page, buttons_selector)) and reset_url:
            target = f"{base_url.rstrip('/')}{reset_url}" if base_url else reset_url
            if page.url != target:
                page.goto(target)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(500)
    except Exception:
        pass


_DLG_TITLE_JS = """(t) => { for (const d of document.querySelectorAll('.el-dialog')) {
         const r = d.getBoundingClientRect(); if (r.width > 0) {
         const tt = d.querySelector('.el-dialog__title');
         if (tt && (tt.textContent || '').includes(t)) return true; } } return false; }"""


def wait_dialog(page: "Page", title: str, timeout_ms: int = 10000) -> bool:
    """
    轮询等待标题含 ``title`` 的可见 el-dialog。
    """
    for _ in range(int(timeout_ms / 400)):
        try:
            if page.evaluate(_DLG_TITLE_JS, title):
                return True
        except Exception:
            pass
        page.wait_for_timeout(400)
    return False


def dialog_by_title(page: "Page", title: str) -> "Locator":
    """
    按标题定位 dialog locator（找不到时返回最后一个可见 dialog 兜底）。
    """
    dlg = page.locator(".el-dialog:visible").filter(
        has=page.locator(f".el-dialog__title:has-text('{title}')"))
    if dlg.count():
        return dlg.first
    return page.locator(".el-dialog:visible").last


def dialog_gone(page: "Page", title: str, timeout_ms: int = 6000) -> bool:
    """
    轮询等待标题含 ``title`` 的 dialog 消失。
    """
    for _ in range(int(timeout_ms / 400)):
        try:
            if not page.evaluate(_DLG_TITLE_JS, title):
                return True
        except Exception:
            return True
        page.wait_for_timeout(400)
    return False


def wait_drawer(page: "Page", title: str, timeout_ms: int = 10000) -> bool:
    """
    轮询等待 header 含 ``title`` 的打开 el-drawer。
    """
    for _ in range(int(timeout_ms / 500)):
        drs = page.locator(".el-drawer.open")
        for i in range(drs.count()):
            if title in (drs.nth(i).locator(".el-drawer__header").inner_text() or ""):
                return True
        page.wait_for_timeout(500)
    return False


def drawer_by_title(page: "Page", title: str) -> "Locator":
    """
    按标题定位 drawer locator（找不到时返回最后一个打开 drawer 兜底）。
    """
    dr = page.locator(".el-drawer.open").filter(
        has=page.locator(f".el-drawer__header:has-text('{title}')"))
    if dr.count():
        return dr.first
    return page.locator(".el-drawer.open").last


def wait_overlay(
    page: "Page", title: str, timeout_ms: int = 10000,
    title_selector: str = ".page-overlay-title",
) -> bool:
    """
    轮询等待标题含 ``title`` 的全页 overlay。
    """
    for _ in range(int(timeout_ms / 500)):
        t = page.locator(title_selector)
        for i in range(t.count()):
            if title in (t.nth(i).inner_text() or ""):
                return True
        page.wait_for_timeout(500)
    return False


def poll_toast(
    page: "Page", cls: str, keyword: str | None = None,
    rounds: int = 8, gap_ms: int = 400,
) -> str | None:
    """
    toast 捕捉（辅助证据）：轮询遍历全部可见条目（EP toast 可叠加），含 keyword 即返回。

    Args:
        page: Playwright ``Page``。
        cls: toast 容器选择器，如 ``.el-message--success`` / ``.el-message--error``。
        keyword: 命中关键词（None = 任一条即返回）。
        rounds: 轮询轮数；gap_ms: 轮询间隔。

    Returns:
        命中的 toast 文本；超时未命中返回 None。
    """
    for _ in range(rounds):
        try:
            msg = page.locator(f"{cls}:visible")
            n = msg.count()
        except Exception:
            pass  # locator/count 异常按本轮无 toast 处理（仍走轮间隔等待）
        else:
            for i in range(n):
                try:
                    txt = (msg.nth(i).inner_text() or "").strip()
                except Exception:
                    continue
                if keyword is None or keyword in txt:
                    return txt
        page.wait_for_timeout(gap_ms)
    return None


def toast_text(page: "Page", cls: str = ".el-message", wait_ms: int = 2500) -> str:
    """
    读当前全部 toast 文本（先静置 600ms 等渲染；多条拼接分号，异常即止）。
    """
    page.wait_for_timeout(600)
    out = ""
    msgs = page.locator(cls)
    for i in range(msgs.count()):
        try:
            out += msgs.nth(i).inner_text(timeout=1200)[:120] + ";"
        except Exception:
            break
    return out
