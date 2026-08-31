"""
page.py — 页面对象基类。

封装所有页面共享的通用操作：导航、点击、填充、断言辅助、Element Plus 组件操作。
所有具体页面对象继承 :class:`BasePage`，按业务页面补充专属方法。

核心特性：

  - **Element Plus 组件操作**：el-select / el-date-picker / 远程搜索下拉 / 消息提示 / 表单校验 / 表格行列
  - **CDP 真实点击**：用 ``Input.dispatchMouseEvent`` 解决 el-select 在 el-dialog 内
    Playwright 合成事件无法触发展开/选中的硬骨头（Vue 3 + Element Plus 已知兼容问题）
  - **对话框作用域**：弹窗打开时自动把选择器限定到 ``.el-dialog`` 内部，
    避免误命中搜索栏等同名表单项

依赖：playwright（重依赖，按需懒加载，不在模块顶层导入）。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class BasePage:
    """页面基类，提供通用操作封装。

    Args:
        page: Playwright ``Page`` 实例。
        screenshot_dir: ``take_screenshot`` 的输出目录，默认 ``screenshots``。
    """

    def __init__(self, page: Page, screenshot_dir: str = "screenshots") -> None:
        self.page = page
        self.screenshot_dir = screenshot_dir

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------

    def goto(self, url: str, wait_networkidle: bool = True) -> None:
        """跳转到指定 URL 并等待加载。"""
        self.page.goto(url)
        if wait_networkidle:
            self.page.wait_for_load_state("networkidle")

    def wait_ready(self) -> None:
        """等待页面就绪（domcontentloaded + networkidle）。"""
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_load_state("networkidle")

    # ------------------------------------------------------------------
    # 通用点击/填充（带自动等待）
    # ------------------------------------------------------------------

    def click(self, selector: str, timeout: int = 10000) -> None:
        """点击元素（自动等待可见且稳定）。"""
        self.page.locator(selector).first.click(timeout=timeout)

    def fill(self, selector: str, value: str, timeout: int = 10000) -> None:
        """清空并填充输入框。"""
        locator = self.page.locator(selector).first
        locator.fill(value, timeout=timeout)

    def get_text(self, selector: str, timeout: int = 5000) -> str:
        """获取元素文本。"""
        return self.page.locator(selector).first.inner_text(timeout=timeout)

    # ------------------------------------------------------------------
    # Element Plus 组件操作（下拉选择、日期选择、对话框）
    # ------------------------------------------------------------------

    def _scope_form_item(self, form_item_label: str) -> Locator:
        """定位 .el-form-item，自动限定作用域。

        若有可见的 .el-dialog（弹窗），优先在弹窗内部查找，
        避免匹配到页面搜索栏的同名表单项。
        """
        dialog = self.page.locator(".el-dialog").first
        if dialog.is_visible():
            return dialog.locator(".el-form-item", has_text=form_item_label).first
        return self.page.locator(".el-form-item", has_text=form_item_label).first

    def _cdp_click(self, x: float, y: float) -> None:
        """用 CDP ``Input.dispatchMouseEvent`` 发送真实鼠标点击。

        解决 Element Plus el-select 在弹窗内时，Playwright ``locator.click()``
        合成事件无法触发展开/选中的问题。CDP 方式发送的是浏览器底层输入事件，
        能正确触发 Vue 的 pointerdown/mousedown 处理链。

        完整事件序列：mouseMoved → mousePressed → mouseReleased。
        """
        context = self.page.context
        cdp = context.new_cdp_session(self.page)
        try:
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": x, "y": y,
            })
            time.sleep(0.05)
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": x, "y": y,
                "button": "left", "clickCount": 1,
            })
            time.sleep(0.03)
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": x, "y": y,
                "button": "left", "clickCount": 1,
            })
        finally:
            cdp.detach()

    def _get_element_center(self, selector: str) -> dict:
        """获取元素中心坐标。"""
        return cast("dict", self.page.eval_on_selector(selector, """el => {
            const r = el.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }"""))

    def _select_wrapper(self, form_item_label: str) -> Locator:
        """定位 el-select 的 .el-select__wrapper（弹窗内优先，label 精确匹配优先）。

        匹配顺序：弹窗内精确 → 全页精确 → 弹窗内 contains → 全页 contains。
        contains 必须排在精确之后：搜索栏表单项没有 label，但它的 placeholder
        文本会出现在 form-item 的 has_text 里（如 label「资产类型」contains 命中
        「请选择资产类型」），错选后还会静默返回成功（目标字段没填、提交被必填
        校验拦截，页面上毫无报错线索）。
        """
        exact_sel = (
            f'.el-form-item:has(.el-form-item__label:text-is("{form_item_label}")) '
            f'.el-select__wrapper'
        )
        in_dialog = self.page.locator(f".el-dialog:visible {exact_sel}")
        if in_dialog.count():
            return in_dialog.first
        exact_any = self.page.locator(exact_sel)
        if exact_any.count():
            return exact_any.first
        fuzzy_sel = (
            f'.el-form-item:has-text("{form_item_label}") .el-select__wrapper'
        )
        in_dialog_fuzzy = self.page.locator(f".el-dialog:visible {fuzzy_sel}")
        if in_dialog_fuzzy.count():
            return in_dialog_fuzzy.first
        fuzzy_any = self.page.locator(fuzzy_sel)
        if fuzzy_any.count():
            return fuzzy_any.first
        raise RuntimeError(f"找不到「{form_item_label}」的 el-select wrapper")

    def _visible_dropdown_option_center(self, option_text: str, exact: bool = True) -> dict | None:
        """在【所有】可见下拉面板中找选项中心坐标。

        下拉面板 teleport 到 body 且可能同时存在多个（上一个 select 的面板
        尚未收起时再展开下一个），只查第一个面板会漏掉真正目标面板里的选项。
        """
        return cast("dict | None", self.page.evaluate(
            """([opt, exact]) => {
                const dds = Array.from(document.querySelectorAll('.el-select-dropdown'))
                    .filter(d => d.offsetParent !== null);
                for (const dd of dds) {
                    const items = Array.from(dd.querySelectorAll('.el-select-dropdown__item'));
                    const item = exact
                        ? items.find(i => i.textContent.trim() === opt)
                        : items.find(i => i.textContent.trim().includes(opt));
                    if (item) {
                        const r = item.getBoundingClientRect();
                        return {x: r.x + r.width/2, y: r.y + r.height/2};
                    }
                }
                return null;
            }""", [option_text, exact]))

    def collapse_dropdowns(self) -> None:
        """收起所有残留下拉面板（CDP 点击视口左上角空白）。

        残留面板会遮挡后续点击目标、并把下一个 select 的选项藏进第二层面板。
        不要用 Escape 收：焦点不在下拉上时 Esc 会冒泡关闭 el-dialog
        （close-on-press-escape 默认开启），弹窗会莫名消失。
        """
        try:
            self._cdp_click(2, 2)
        except Exception:
            pass
        self.page.wait_for_timeout(200)

    def el_select(
        self, form_item_label: str, option_text: str, *,
        expand_retries: int = 3, poll_times: int = 5, poll_interval_ms: int = 400,
    ) -> None:
        """操作 Element Plus 的 el-select 下拉选择。

        使用 CDP ``Input.dispatchMouseEvent`` 发送真实鼠标事件。
        这是唯一能可靠触发 Vue/Element Plus 在弹窗内 el-select 交互的方式：

          - Playwright ``locator.click()`` 的合成事件被 overlay 拦截
          - JS ``dispatchEvent`` 能展开但无法选中
          - CDP Input 事件是浏览器底层真实输入，完整触发事件链

        Args:
            form_item_label: 表单项标签文本，如「资产类型」「状态」
            option_text: 选项文本，如「IT设备」「在库」
            expand_retries: 选项未找到时重新展开重试的轮数。字典/选项异步
                渲染慢（弹窗刚开、远程字典）时单轮轮询可能不够——2026-08-28
                IMP 实坑：弹窗内字典下拉首展开未渲染完即报「找不到选项」。
            poll_times: 每轮展开后轮询选项渲染的次数。
            poll_interval_ms: 轮询间隔毫秒。
        """
        wrapper = self._select_wrapper(form_item_label)
        last_err: RuntimeError | None = None
        try:
            for _attempt in range(expand_retries):
                # CDP 点击 wrapper 展开下拉（每轮重取位置，弹窗动画中坐标会漂移）
                wrapper_box = wrapper.bounding_box()
                if not wrapper_box:
                    raise RuntimeError(f"找不到 {form_item_label} 的 el-select wrapper")
                self._cdp_click(
                    wrapper_box["x"] + wrapper_box["width"] / 2,
                    wrapper_box["y"] + wrapper_box["height"] / 2,
                )
                self.page.wait_for_timeout(400)

                # 在可见的下拉面板中找到目标选项，CDP 点击（下拉面板 teleport 到
                # body；字典/选项可能是异步渲染，轮询而非直接判死）
                opt_center = None
                for _ in range(poll_times):
                    opt_center = self._visible_dropdown_option_center(option_text, exact=True)
                    if opt_center:
                        break
                    self.page.wait_for_timeout(poll_interval_ms)
                if opt_center:
                    self._cdp_click(opt_center["x"], opt_center["y"])
                    self.page.wait_for_timeout(300)
                    return

                last_err = RuntimeError(f"下拉面板中找不到选项「{option_text}」")
                self.collapse_dropdowns()
                self.page.wait_for_timeout(400)
            raise last_err  # type: ignore[misc]
        finally:
            self.collapse_dropdowns()

    def el_dict_select(self, form_item_label: str, option_text: str) -> None:
        """操作字典下拉选择（ma-dict-select，本质也是 el-select 变体）。

        与 :meth:`el_select` 相同实现，若定位失败可在子类覆写。
        """
        self.el_select(form_item_label, option_text)

    def el_remote_select(
        self, form_item_label: str, keyword: str, option_text: str | None = None,
    ) -> None:
        """操作远程搜索下拉（remote-select，需输入关键词搜索后选）。

        Args:
            form_item_label: 表单项标签
            keyword: 搜索关键词
            option_text: 选项文本（默认用 keyword）
        """
        option_text = option_text or keyword
        wrapper = self._select_wrapper(form_item_label)

        # CDP 点击展开
        box = wrapper.bounding_box()
        if not box:
            raise RuntimeError(f"找不到 {form_item_label} 的 el-select wrapper")
        try:
            self._cdp_click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            self.page.wait_for_timeout(400)

            # 在展开的搜索框中输入关键词
            combobox = wrapper.locator('input[role="combobox"]').first
            combobox.fill(keyword)

            # 远程数据加载耗时不确定，轮询等选项出现（上限 ~4s）再点击
            opt_center = None
            for _ in range(8):
                self.page.wait_for_timeout(500)
                opt_center = self._visible_dropdown_option_center(option_text, exact=False)
                if opt_center:
                    break
            if not opt_center:
                raise RuntimeError(f"远程下拉中找不到选项「{option_text}」")
            self._cdp_click(opt_center["x"], opt_center["y"])
            self.page.wait_for_timeout(300)
        finally:
            self.collapse_dropdowns()

    def el_date_picker(self, form_item_label: str, date_str: str) -> None:
        """操作 Element Plus 日期选择器。

        Args:
            form_item_label: 表单项标签，如「采购日期」
            date_str: 日期字符串，格式 ``YYYY-MM-DD``
        """
        form_item = self._scope_form_item(form_item_label)
        date_input = form_item.locator("input").first
        date_input.click()
        date_input.fill(date_str)
        date_input.press("Enter")
        self.page.wait_for_timeout(200)

    def expect_row_cell(
        self, row_keyword: str, column_header: str, expected: str, timeout: int = 8000,
    ) -> None:
        """轮询断言某行某列格刷新到期望值。

        提交成功后列表 refresh 是异步请求，提交返回后立即读列格存在竞态
        （读到旧值），必须轮询等待。
        """
        deadline = time.time() + timeout / 1000
        last = ""
        while time.time() < deadline:
            last = self.get_row_cell(row_keyword, column_header)
            if last == expected:
                return
            self.page.wait_for_timeout(400)
        raise AssertionError(
            f"行[{row_keyword}]列[{column_header}]未刷新为 {expected!r}，最后值={last!r}")

    def expect_input_value(self, selector: str, expected: str, timeout: int = 8000) -> None:
        """轮询断言输入框值到达期望（表单异步回显的等待）。"""
        deadline = time.time() + timeout / 1000
        loc = self.page.locator(selector).first
        while time.time() < deadline:
            if loc.count() and loc.input_value() == expected:
                return
            self.page.wait_for_timeout(400)
        actual = loc.input_value() if loc.count() else "<元素不存在>"
        raise AssertionError(f"{selector} 值未到达 {expected!r}，当前={actual!r}")

    def wait_no_loading_mask(self, timeout: int = 5000) -> None:
        """等待 Element Plus v-loading 遮罩全部消失。

        遮罩消失可能略晚于数据回显：遮罩还盖着时 CDP 点击会打在遮罩上
        （无展开/点击效果），回显后要操作弹窗表单前必须等它消失。
        """
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            if self.page.locator(".el-loading-mask:visible").count() == 0:
                return
            self.page.wait_for_timeout(300)
        raise AssertionError("loading 遮罩等待超时未消失")

    def overlay(self) -> Locator:
        """当前打开的弹窗或抽屉（优先弹窗，多层弹窗取最后打开的）。

        ⚠️ 不要用 ``.el-drawer:visible`` 定位抽屉：页面常驻隐藏抽屉（如 IMP
        的「布局设置」，rtl 方向被 transform 移出视口）时 Playwright 仍判其
        visible，会定位到错误容器导致元素找不到（2026-08-28 IMP 实坑）。
        Element Plus 打开中的抽屉带 ``open`` 类，用它判定。
        """
        dlg = self.page.locator(".el-dialog:visible")
        if dlg.count():
            return dlg.last
        return self.page.locator(".el-drawer.open").first

    def close_all_dialogs(self) -> None:
        """关闭所有残留弹窗与确认框。

        残留弹窗的遮罩会挡住行操作按钮，导致后续用例连锁点击超时；
        ElMessageBox（二次确认框）不是 .el-dialog，需一并处理。
        """
        for _ in range(4):
            has_dialog = self.page.locator(".el-dialog:visible").count()
            has_box = self.page.locator(".el-message-box:visible").count()
            if not has_dialog and not has_box:
                return
            self.page.keyboard.press("Escape")  # MessageBox 默认 Esc=取消；下拉面板优先收起
            self.page.wait_for_timeout(400)
            if self.page.locator(".el-dialog:visible").count():
                try:
                    self.close_dialog()
                except Exception:
                    pass
                self.page.wait_for_timeout(400)

    def read_select_options(self, form_item_label: str) -> list[str]:
        """展开指定表单项的下拉，读取全部选项文本后收起（用于可选集断言）。"""
        wrapper = self._select_wrapper(form_item_label)
        box = wrapper.bounding_box()
        if not box:
            raise RuntimeError(f"找不到 {form_item_label} 的 el-select wrapper")
        try:
            self._cdp_click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            self.page.wait_for_timeout(600)
            texts: list[str] = []
            for _ in range(3):  # 字典异步渲染时选项可能未就绪，轮询
                items = self.page.locator(
                    ".el-select-dropdown:visible .el-select-dropdown__item")
                texts = [items.nth(i).inner_text().strip() for i in range(items.count())]
                if texts:
                    break
                self.page.wait_for_timeout(400)
            return texts
        finally:
            self.collapse_dropdowns()

    def upload_file(self, file, nth: int = 0, scope: "Locator | None" = None):
        """向弹窗内第 nth 个 el-upload 上传位传文件（同名文件防 change 丢失）。

        2026-08-28 WMS E2E 12 轮实跑实证的坑：``set_input_files`` 对**同名文件二次
        设置不触发 change**（input.value 不变，浏览器安全模型下值是 fakepath 文件名）。
        弹窗/组件复用场景（如 KeepAlive 缓存页再次打开建单弹窗）图片会**静默丢失**——
        提交被"请上传 xx 图"必填校验拦截，页面上无任何报错线索，且首次打开能成功，
        极难排查。本方法每次调用把文件复制为带自增序号的新文件名再传，保证 value 必变。

        上传 input（``.el-upload__input``）是 hidden 元素，Playwright 常规 click 会
        超时——这里用 ``state="attached"`` 后直接 ``set_input_files``。

        Args:
            file: 源文件路径（str/Path）。
            nth: 上传位序号（同一弹窗有多个上传位时：0=第一个，如全景图；1=第二个）。
            scope: 上传区的定位容器；默认当前打开的弹窗/抽屉（``overlay()``）。

        Returns:
            Path: 实际上传的临时文件路径（与源同目录、带序号后缀，供调用方清理）。
        """
        import shutil
        from pathlib import Path as _P

        src = _P(file)
        if not src.is_file():
            raise FileNotFoundError(f"上传源文件不存在: {src}")
        area = scope if scope is not None else self.overlay()
        BasePage._upload_seq = getattr(BasePage, "_upload_seq", 0) + 1
        dst = src.with_name(f"{src.stem}-{BasePage._upload_seq}{src.suffix}")
        shutil.copyfile(src, dst)
        loc = area.locator(".el-upload__input").nth(nth)
        loc.wait_for(state="attached", timeout=8000)
        loc.set_input_files(str(dst))
        return dst

    # ------------------------------------------------------------------
    # 对话框/消息提示
    # ------------------------------------------------------------------

    def expect_toast(self, text: str, timeout: int = 5000) -> None:
        """断言出现包含指定文本的消息提示（el-message，浮层位于 body 下）。"""
        from playwright.sync_api import expect

        expect(
            self.page.locator(".el-message", has_text=text).first,
        ).to_be_visible(timeout=timeout)

    def expect_toast_success(self, text: str = "成功", timeout: int = 8000) -> None:
        """断言成功消息。兼容多种 Element Plus 消息样式。"""
        from playwright.sync_api import expect

        try:
            expect(
                self.page.locator(".el-message--success", has_text=text).first,
            ).to_be_visible(timeout=timeout)
        except Exception:
            # 降级：匹配任意类型的 el-message
            expect(
                self.page.locator(".el-message", has_text=text).first,
            ).to_be_visible(timeout=3000)

    def expect_form_error(self, text: str, timeout: int = 5000) -> None:
        """断言表单校验错误消息（.el-form-item__error）。

        Args:
            text: 校验错误文案，如「请选择资产类型」
        """
        from playwright.sync_api import expect

        expect(
            self.page.locator(".el-form-item__error", has_text=text).first,
        ).to_be_visible(timeout=timeout)

    def click_dialog_button(self, text: str = "确定") -> None:
        """点击对话框底部按钮（确定/取消）。兼容 overlay 拦截。"""
        btn = self.page.locator(".el-dialog__footer").last.get_by_role("button", name=text)
        try:
            btn.click(timeout=5000)
        except Exception:
            # 降级：用 JS click 绕过 overlay 拦截
            btn.evaluate("el => el.click()")

    def close_dialog(self) -> None:
        """关闭当前对话框。"""
        self.page.locator(".el-dialog__headerbtn:visible").last.click()

    # ------------------------------------------------------------------
    # 表格操作
    # ------------------------------------------------------------------

    def get_table_row(self, keyword: str) -> Locator:
        """获取表格中包含指定文本的行。

        Args:
            keyword: 行内任意单元格的文本（如资产编号 TH0000001）
        Returns:
            该行 tr Locator
        """
        return self.page.locator(".el-table__row", has_text=keyword).first

    def click_row_action(self, row_keyword: str, button_text: str) -> None:
        """点击某行操作列的按钮。

        Args:
            row_keyword: 用于定位行的文本（如资产编号）
            button_text: 按钮文本，如「编辑」「查看」
        """
        row = self.get_table_row(row_keyword)
        row.get_by_role("button", name=button_text).first.click()

    def get_row_cell(self, row_keyword: str, column_header: str) -> str:
        """获取某行指定列的单元格文本。

        通过列头文本定位列索引，再取该行的单元格。

        Args:
            row_keyword: 行定位文本
            column_header: 列头文本，如「状态」「领用人」
        Returns:
            单元格文本
        """
        headers = self.page.locator(".el-table__header th .cell").all_inner_texts()
        col_index = headers.index(column_header)
        row = self.get_table_row(row_keyword)
        cells = row.locator(".cell").all_inner_texts()
        if col_index < len(cells):
            return cells[col_index].strip()
        return ""

    def expect_row_exists(self, keyword: str, timeout: int = 5000) -> None:
        """断言表格中存在包含关键词的行。"""
        from playwright.sync_api import expect

        expect(self.get_table_row(keyword)).to_be_visible(timeout=timeout)

    def expect_row_not_exists(self, keyword: str, timeout: int = 5000) -> None:
        """断言表格中不存在包含关键词的行。"""
        from playwright.sync_api import expect

        expect(self.get_table_row(keyword)).to_have_count(0, timeout=timeout)

    def filter_row(
        self, keyword: str, *, filter_selector: str | None = None, query_button: str = "查询",
        wait_after_query_ms: int = 1500, timeout: int = 12000,
    ) -> Locator:
        """列表先按关键词筛选再定位目标行（防『早建单被推下第一页』）。

        列表通常按创建时间倒序，先建的数据会被后建数据推下第一页，裸 ``get_table_row``
        只查当前页会永远找不到 → 行内按钮点击超时（2026-08-31 报价管理 E2E 连锁根因）。
        正解：刷新到列表 → 填筛选框圈定 → 点查询 → 再等目标行。

        Args:
            keyword: 行定位关键词（业务键，如系列名/单号，既作筛选值也作行定位）。
            filter_selector: 筛选输入框定位（CSS）。默认取页面第一个 ``input``
                （列表页第一个文本输入通常是主筛选框）；定位不到时尝试按
                ``placeholder`` 含关键词所在列名的兜底由调用方传入。
            query_button: 查询按钮文本，默认「查询」。
            wait_after_query_ms: 点查询后固定等待毫秒（列表异步加载）。
            timeout: 等目标行出现的总超时毫秒。

        Returns:
            目标行 ``tr`` Locator（含 keyword 的表格行）。
        """
        page = self.page
        if filter_selector:
            inp = page.locator(filter_selector).first
        else:
            inp = page.locator("input").first
        try:
            inp.fill(keyword)
        except Exception:
            # placeholder 定位兜底（如搜索栏无 label 时）
            page.locator("input[placeholder*='系列名称'], input[placeholder*='名称'], input[placeholder*='单号']").first.fill(keyword)
        page.wait_for_timeout(300)
        page.locator(f"button:has-text('{query_button}')").first.click()
        page.wait_for_timeout(wait_after_query_ms)
        # 轮询等目标行（列表接口异步）
        deadline = time.time() + timeout / 1000
        row = page.locator(f"tr:has-text('{keyword}')").first
        while time.time() < deadline:
            if row.count():
                return row
            page.wait_for_timeout(400)
        return row

    def fill_row_by_cells(self, row: Locator, col_map: dict[int, str]) -> None:
        """按列序号填充可编辑表格行（新增/编辑行的单元格输入框）。

        ⚠️ 可编辑行的首个 ``input`` 往往是 enabled 复选框/开关（value='on'），
        不是首个数据字段——若用 ``row.locator('input').nth(n)`` 会把第 0 项填到
        开关上、后续字段全错位（保存后 DB 查不到）。须按单元格定位。

        Args:
            row: 可编辑行的 ``tr`` Locator。
            col_map: ``{列序号: 值}``，如 ``{2: '品名', 4: '款号', 6: '100'}``
                （列序号需先用探针确认，见 browser-e2e-runner 技能）。
        """
        for col_idx, value in sorted(col_map.items()):
            cell_input = row.locator("td").nth(col_idx).locator("input").first
            if cell_input.count():
                cell_input.fill(str(value))

    def select_table_select(
        self, container: "Locator", *, nth: int = 0, row_idx: int = 0,
        collapse: bool = True,
    ) -> str:
        """操作 ma-element-table-select（表格型多选下拉）选中一项。

        该组件展开后是**表格**（非简单选项列表），且选中后 popper 不自动收起——
        若不收起，popper 会遮挡弹窗 footer 的「确定」按钮导致点击超时
        （2026-08-31 报价管理匹配款式库 E2E 实证）。

        Args:
            container: 所在弹窗/抽屉 Locator（如 ``overlay()``）。
            nth: 下拉序号（同一容器有多个 ma-element-table-select 时）。
            row_idx: 目标行在展开表格中的序号（默认第一行）。
            collapse: 选中后是否收起 popper（True 才可点 footer 确定）。

        Returns:
            选中行的文本片段（供断言）。
        """
        page = self.page
        sel = container.locator(".ma-element-table-select, .el-select").nth(nth)
        sel.click()
        page.wait_for_timeout(1200)
        popper = page.locator(".el-popper:visible").last
        row0 = popper.locator(".el-table__row").nth(row_idx)
        if not row0.count():
            raise RuntimeError("ma-element-table-select 下拉无可用行")
        text = row0.inner_text().strip()[:40]
        row0.locator(".el-checkbox").first.click()
        page.wait_for_timeout(600)
        if collapse:
            try:
                container.locator(".el-dialog__title, .el-drawer__header").first.click(force=True)
            except Exception:
                page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        return text

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def wait(self, ms: int) -> None:
        """固定等待（仅在必要时使用，优先用 expect/等待状态）。"""
        self.page.wait_for_timeout(ms)

    def take_screenshot(self, name: str) -> None:
        """截图到 ``screenshot_dir/<name>.png``（全页面）。"""
        import os

        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.page.screenshot(
            path=f"{self.screenshot_dir}/{name}.png", full_page=True,
        )
