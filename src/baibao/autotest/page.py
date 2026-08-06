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
        """定位 el-select 的 .el-select__wrapper（弹窗内优先）。"""
        dialog = self.page.locator(".el-dialog").first
        base = dialog if dialog.is_visible() else self.page
        return base.locator(".el-form-item", has_text=form_item_label).first \
            .locator(".el-select__wrapper").first

    def el_select(self, form_item_label: str, option_text: str) -> None:
        """操作 Element Plus 的 el-select 下拉选择。

        使用 CDP ``Input.dispatchMouseEvent`` 发送真实鼠标事件。
        这是唯一能可靠触发 Vue/Element Plus 在弹窗内 el-select 交互的方式：

          - Playwright ``locator.click()`` 的合成事件被 overlay 拦截
          - JS ``dispatchEvent`` 能展开但无法选中
          - CDP Input 事件是浏览器底层真实输入，完整触发事件链

        Args:
            form_item_label: 表单项标签文本，如「资产类型」「状态」
            option_text: 选项文本，如「IT设备」「在库」
        """
        wrapper = self._select_wrapper(form_item_label)

        # CDP 点击 wrapper 展开下拉
        wrapper_box = wrapper.bounding_box()
        if not wrapper_box:
            raise RuntimeError(f"找不到 {form_item_label} 的 el-select wrapper")
        self._cdp_click(
            wrapper_box["x"] + wrapper_box["width"] / 2,
            wrapper_box["y"] + wrapper_box["height"] / 2,
        )
        self.page.wait_for_timeout(400)

        # 在可见的下拉面板中找到目标选项，CDP 点击（下拉面板 teleport 到 body）
        opt_center = self.page.evaluate(
            f"""() => {{
                const dropdowns = Array.from(document.querySelectorAll('.el-select-dropdown'))
                    .filter(d => d.offsetParent !== null);
                if (!dropdowns.length) return null;
                const dd = dropdowns[0];
                const item = Array.from(dd.querySelectorAll('.el-select-dropdown__item'))
                    .find(i => i.textContent.trim() === {option_text!r});
                if (!item) return null;
                const r = item.getBoundingClientRect();
                return {{x: r.x + r.width/2, y: r.y + r.height/2}};
            }}"""
        )
        if not opt_center:
            raise RuntimeError(f"下拉面板中找不到选项「{option_text}」")
        self._cdp_click(opt_center["x"], opt_center["y"])
        self.page.wait_for_timeout(300)

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
        self._cdp_click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.page.wait_for_timeout(400)

        # 在展开的搜索框中输入关键词
        combobox = wrapper.locator('input[role="combobox"]').first
        combobox.fill(keyword)
        self.page.wait_for_timeout(800)  # 等待远程数据加载

        # CDP 点击匹配选项
        opt_center = self.page.evaluate(
            f"""() => {{
                const dropdowns = Array.from(document.querySelectorAll('.el-select-dropdown'))
                    .filter(d => d.offsetParent !== null);
                if (!dropdowns.length) return null;
                const dd = dropdowns[0];
                const item = Array.from(dd.querySelectorAll('.el-select-dropdown__item'))
                    .find(i => i.textContent.trim().includes({option_text!r}));
                if (!item) return null;
                const r = item.getBoundingClientRect();
                return {{x: r.x + r.width/2, y: r.y + r.height/2}};
            }}"""
        )
        if not opt_center:
            raise RuntimeError(f"远程下拉中找不到选项「{option_text}」")
        self._cdp_click(opt_center["x"], opt_center["y"])
        self.page.wait_for_timeout(300)

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
