"""BasePage 新增可复用方法的冒烟测试（接口存在性 + 最小调用，不启浏览器）。

filter_row / fill_row_by_cells / select_table_select 依赖 Playwright Page 与真实 UI，
完整功能验证走 browser-e2e-runner 技能实跑（2026-08-31 报价管理 E2E 已用同款实现验证）。
此处用 stub Page 校验：方法存在、可调用、对最小 happy-path 不抛 AttributeError。
"""

import inspect
import unittest

from baibao.autotest.page import BasePage


class _Chain:
    """链式 stub：任何定位方法都返回自身，fill/click/inner_text 各归其位。"""

    def count(self) -> int:
        return 1

    @property
    def first(self):
        return self

    @property
    def last(self):
        return self

    def nth(self, _i):
        return self

    def filter(self, **kw):
        return self

    def locator(self, _sel):
        return self

    def get_by_role(self, _role, name=None):
        return self

    def fill(self, _v):
        return None

    def click(self, **kw):
        return None

    def inner_text(self):
        return "stub-text"

    def is_visible(self):
        return True

    def press(self, _k):
        return None


class _StubPage:
    """覆盖 BasePage 三个新方法用到的 Page 行为。"""

    def __init__(self):
        self._c = _Chain()
        self._kb = type("K", (), {"press": lambda self, k: None})()

    def locator(self, _sel):
        return self._c

    def wait_for_timeout(self, _ms):
        return None

    def wait_for_load_state(self, _s):
        return None

    def goto(self, _u):
        return None

    def evaluate(self, *_a, **_k):
        return None

    @property
    def keyboard(self):
        return self._kb


class TestBasePageNewMethods(unittest.TestCase):
    """新增方法冒烟测试。"""

    def setUp(self):
        self.bp = BasePage(_StubPage())  # type: ignore[arg-type]

    def test_methods_exist(self):
        for name in ("filter_row", "fill_row_by_cells", "select_table_select"):
            self.assertTrue(hasattr(self.bp, name), f"缺少方法 {name}")

    def test_filter_row_signature(self):
        sig = inspect.signature(BasePage.filter_row)
        self.assertIn("keyword", sig.parameters)

    def test_filter_row_callable(self):
        row = self.bp.filter_row("SERIES-A")
        self.assertEqual(row.count(), 1)

    def test_fill_row_by_cells_callable(self):
        # 不抛异常即通过；真实填值需 browser-e2e-runner 实跑
        self.bp.fill_row_by_cells(_Chain(), {2: "品名", 4: "款号", 6: "100"})

    def test_select_table_select_callable(self):
        text = self.bp.select_table_select(_Chain())
        self.assertIn("stub", text)


if __name__ == "__main__":
    unittest.main()
