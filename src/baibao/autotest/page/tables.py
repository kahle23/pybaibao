"""
tables — el-table 按表头读列 + 分页游走的自由函数族。

BasePage 的 ``get_row_cell``/``click_row_action`` 按"行 keyword"定位；
本模块补齐另一套高频口径：**按列头文本定列**（列序会变、固定列拷贝行干扰、
跨页找行）——独立脚本式 E2E 直接调函数，BasePage 的对应方法是薄委托。

来源：12-SDI e2e 03~08 六份模板内嵌的 ``column_cells_by_header`` 族
（约各 150 行，口径：260828/261012 轮实证）。

约定：``container`` 为 page 或表格所在 locator（弹窗内表格传弹窗 locator）；
``page`` 仅用于 ``wait_for_timeout``（协议消息等待）。
"""

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def wait_row(
    page: "Page", text: str, timeout_ms: int = 12000, scope: "Locator | None" = None,
) -> "Locator":
    """
    轮询等含 ``text`` 的行出现（超时返回最后一次探测的 locator，可能为空）。
    """
    root = scope or page
    for _ in range(int(timeout_ms / 400)):
        row = root.locator(f"tr:has-text('{text}')")
        if row.count() >= 1:
            return row
        page.wait_for_timeout(400)
    return root.locator(f"tr:has-text('{text}')")


def wait_row_count(
    page: "Page", n: int, timeout_ms: int = 12000, scope: "Locator | None" = None,
) -> bool:
    """
    轮询等 body 行数等于 ``n``（列表刷新/清空判定）。
    """
    root = scope or page
    for _ in range(int(timeout_ms / 400)):
        if root.locator(".el-table__body-wrapper tr").count() == n:
            return True
        page.wait_for_timeout(400)
    return root.locator(".el-table__body-wrapper tr").count() == n


def header_texts(container: "Locator | Page") -> list[str]:
    """
    表头文本列表（含固定列；用于口径探测/列存在性判定）。
    """
    headers = container.locator(".el-table__header-wrapper th")
    out = []
    for i in range(headers.count()):
        try:
            out.append((headers.nth(i).inner_text() or "").strip())
        except Exception:
            out.append("")
    return out


def _header_index(container: "Locator | Page", header: str) -> int:
    """
    按列头文本（包含匹配）找列序；找不到返回 -1。
    """
    headers = container.locator(".el-table__header-wrapper th")
    for i in range(headers.count()):
        try:
            if header in (headers.nth(i).inner_text() or ""):
                return i
        except Exception:
            continue
    return -1


def column_cells_by_header(container: "Locator | Page", header: str) -> "Locator | None":
    """
    按列头文本定位列序 → 该列 body cell 集合（找不到列返回 None）。
    """
    idx = _header_index(container, header)
    if idx < 0:
        return None
    return container.locator(f".el-table__body-wrapper tr td:nth-child({idx + 1})")


def row_cell_by_header(
    container: "Locator | Page", row: "Locator", header: str,
) -> "Locator | None":
    """
    行内按列头文本取 cell（找不到列返回 None）。
    """
    idx = _header_index(container, header)
    if idx < 0:
        return None
    return row.locator(f"td:nth-child({idx + 1})").first


def cells_texts(cells: "Locator") -> list[str]:
    """
    cell 集合逐个取文本（异常项跳过）。
    """
    out = []
    for i in range(cells.count()):
        try:
            out.append((cells.nth(i).inner_text() or "").strip())
        except Exception:
            continue
    return out


def read_row(
    container: "Locator | Page", row: "Locator", headers: list[str],
) -> dict[str, str | None]:
    """
    按表头清单读整行 → ``{header: text}``（取不到的列记 None）。
    """
    m: dict[str, str | None] = {}
    for h in headers:
        c = row_cell_by_header(container, row, h)
        try:
            m[h] = (c.inner_text() or "").strip() if c else None
        except Exception:
            m[h] = None
    return m


def page_next(container: "Locator | Page", page: "Page", timeout_ms: int = 1500) -> bool:
    """
    翻到下一页（EP 分页 btn-next；disabled/不存在返回 False）。
    """
    btn = container.locator(".el-pagination .btn-next").first
    if not btn.count():
        return False
    try:
        if btn.is_disabled():
            return False
    except Exception:
        pass
    btn.click()
    page.wait_for_timeout(timeout_ms)
    return True


def page_prev_to_first(container: "Locator | Page", page: "Page", max_steps: int = 6) -> None:
    """
    连续回退到第一页（disabled/不存在即止）。
    """
    for _ in range(max_steps):
        btn = container.locator(".el-pagination .btn-prev").first
        if not btn.count():
            return
        try:
            if btn.is_disabled():
                return
        except Exception:
            return
        btn.click()
        page.wait_for_timeout(1200)


def find_row_across_pages(
    page: "Page", row_locator: Callable[["Page"], "Locator"], max_pages: int = 10,
    container: "Locator | Page | None" = None,
) -> "Locator":
    """
    逐页扫描定位目标行（结束回第一页）。

    Args:
        page: Playwright ``Page``。
        row_locator: 当前页找行——返回 locator（空 locator = 本页没有）。
        max_pages: 最多翻几页。
        container: 分页控件所在范围（默认 page；弹窗内表格传弹窗 locator）。
    """
    cont = container or page
    row = row_locator(page)
    if row.count():
        return row
    for _ in range(max_pages):
        if not page_next(cont, page):
            break
        row = row_locator(page)
        if row.count():
            return row
    page_prev_to_first(cont, page)
    return row


def iter_rows(
    container: "Locator | Page", page: "Page", headers: list[str], max_pages: int = 4,
) -> list[dict[str, str | None]]:
    """
    跨页遍历行 → ``{header: text}`` 列表（结束后回第一页）。

    过滤固定列拷贝的残缺行（首列取不到文本即跳过——fixed 列在 EP 表格里
    会复制一份 DOM，非固定列 cell 为空）。
    """
    out: list[dict[str, str | None]] = []
    for _ in range(max_pages):
        trs = container.locator(".el-table__body-wrapper tr")
        for i in range(trs.count()):
            m = read_row(container, trs.nth(i), headers)
            if not m.get(headers[0]):
                continue
            out.append(m)
        if not page_next(container, page):
            break
    page_prev_to_first(container, page)
    return out


def pick_page_size(page: "Page", size_label: str, rounds: int = 3) -> bool:
    """
    页容量选择：点 sizes 下拉 → 轮询等选项 → 点选；未现重开重试。

    Args:
        page: Playwright ``Page``。
        size_label: 选项文案，如 ``"50条/page"`` 或 ``"50"``。
        rounds: 重开下拉的重试轮数。

    Returns:
        是否点选成功（分页器不存在/选项始终未现返回 False）。
    """
    for _ in range(rounds):
        sizes_sel = page.locator(".el-pagination .el-pagination__sizes .el-select").first
        if not sizes_sel.count():
            return False
        sizes_sel.click()
        opt = None
        for _ in range(10):
            dd = page.locator(".el-select-dropdown:visible").last
            cand = dd.locator(".el-select-dropdown__item", has_text=size_label).first
            if cand.count():
                opt = cand
                break
            page.wait_for_timeout(500)
        if opt:
            opt.click()
            page.wait_for_timeout(1000)
            return True
        page.wait_for_timeout(600)
    return False
