"""
dom_summary.py — DOM 摘要探针。

把一个**已登录**页面压缩成 KB 级 markdown 结构摘要（表单项/表格/按钮/弹窗/
消息/下拉实际选项），供 AI 在不读整页 HTML 的前提下了解页面结构：

  - :func:`run_probe` — 完整流程入口（登录态缓存 + 浏览器 + 打开页面 + 提取），
    CLI 与脚本两用。
  - :func:`extract_summary` — 在已打开的 ``Page`` 上注入 JS 提取并格式化摘要。
  - :func:`format_summary` — 把 JS 提取的结构化 dict 渲染成 markdown（含截断）。

选择器知识沿用 :mod:`baibao.autotest.page`（BasePage）的 Element Plus 约定；
点击交互复用 CDP 真实事件（el-select 展开的唯一可靠方式）。

依赖：playwright（重依赖，按需懒加载，不在模块顶层导入）。
安装：``pip install "baibao[autotest]"``。
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .browser import launch_browser
from .login_state import LoginCfg, auth_state_path, is_auth_valid, save_storage_state

if TYPE_CHECKING:
    from playwright.sync_api import FloatRect, Page

__all__ = ["build_target_url", "extract_summary", "format_summary", "run_probe"]

# 摘要硬上限（字符）。超限截断并标注，保证单页输出对 AI 上下文友好。
MAX_OUTPUT_CHARS = 6000

# 注入页面的提取脚本：返回结构化 dict（元素全部经过可见性过滤与截断）。
EXTRACT_JS = """() => {
  const visible = el => !!(el && el.getClientRects().length > 0);
  const txt = el => { if (!el) return ''; return (el.textContent || '').replace(/\\s+/g, ' ').trim(); };
  const clip = (s, n) => { s = s || ''; return s.length > n ? s.slice(0, n) + '…' : s; };
  const scopeOf = el => {
    const d = el.closest('.el-dialog');
    if (d && visible(d)) return '弹窗「' + (clip(txt(d.querySelector('.el-dialog__title')), 20) || '无标题') + '」';
    const w = el.closest('.el-drawer');
    if (w && visible(w)) return '抽屉「' + (clip(txt(w.querySelector('.el-drawer__header, .el-drawer__title')), 20) || '无标题') + '」';
    return '';
  };

  const forms = [];
  document.querySelectorAll('.el-form-item').forEach(item => {
    if (!visible(item) || forms.length >= 40) return;
    const label = txt(item.querySelector('.el-form-item__label'));
    const q = s => item.querySelector(s);
    let type = '未知', value = '', options = null;
    if (q('.el-select__wrapper') || q('.el-select')) {
      type = 'select';
      const box = q('.el-select__wrapper') || q('.el-select');
      const tags = Array.from(box.querySelectorAll('.el-tag')).map(e => clip(txt(e), 12));
      if (tags.length) { value = tags.join('、'); }
      else {
        value = txt(box.querySelector('.el-select__selected-item'))
          || (box.querySelector('input') ? box.querySelector('input').value : '');
      }
    } else if (q('.el-cascader')) { type = '级联'; }
    else if (q('.el-range-editor')) {
      type = '日期范围';
      value = Array.from(item.querySelectorAll('.el-range-editor input')).map(i => i.value).filter(Boolean).join(' ~ ');
    } else if (q('.el-date-editor')) {
      type = '日期';
      const i = q('.el-date-editor input'); value = i ? i.value : '';
    } else if (q('.el-input-number')) {
      type = '数字';
      const i = q('input'); value = i ? i.value : '';
    } else if (q('.el-radio-group')) {
      type = '单选';
      options = Array.from(item.querySelectorAll('.el-radio__label')).map(e => txt(e)).slice(0, 8);
    } else if (q('.el-checkbox-group')) {
      type = '多选';
      options = Array.from(item.querySelectorAll('.el-checkbox__label')).map(e => txt(e)).slice(0, 8);
    } else if (q('.el-switch')) {
      type = '开关';
      value = q('.el-switch').classList.contains('is-checked') ? '开' : '关';
    } else if (q('textarea')) {
      type = '多行文本';
      value = q('textarea').value;
    } else if (q('input[type=file]')) { type = '文件'; }
    else if (q('input')) { type = '文本'; value = q('input').value; }
    const input = q('input, textarea');
    const ph = (input && input.placeholder)
      || txt(item.querySelector('.el-select__placeholder'));
    // 搜索栏等无 label 表单项：placeholder 即字段语义，提升为标签
    forms.push({
      label: clip(label || ph, 20),
      required: item.classList.contains('is-required'),
      type: type, value: clip(value, 30),
      placeholder: clip(ph || '', 20),
      options: options, scope: scopeOf(item),
    });
  });

  const tables = [];
  document.querySelectorAll('.el-table').forEach(t => {
    if (!visible(t) || tables.length >= 3) return;
    const cols = Array.from(t.querySelectorAll('.el-table__header th .cell'))
      .map(c => txt(c)).filter(Boolean).slice(0, 15);
    const rows = Array.from(t.querySelectorAll('.el-table__row')).filter(visible);
    const firstRow = rows.length
      ? Array.from(rows[0].querySelectorAll('.cell')).map(c => clip(txt(c), 20)).slice(0, 15)
      : [];
    tables.push({ cols: cols, rowCount: rows.length, firstRow: firstRow });
  });

  const pagination = Array.from(document.querySelectorAll('.el-pagination__total'))
    .filter(visible).map(e => txt(e));

  const buttons = [];
  document.querySelectorAll('button').forEach(b => {
    if (!visible(b) || buttons.length >= 20) return;
    const t = txt(b);
    if (t && !buttons.includes(t)) buttons.push(clip(t, 12));
  });

  const overlays = [];
  document.querySelectorAll('.el-dialog').forEach(d => {
    if (visible(d)) overlays.push('弹窗「' + (clip(txt(d.querySelector('.el-dialog__title')), 20) || '无标题') + '」');
  });
  document.querySelectorAll('.el-drawer').forEach(d => {
    if (visible(d)) overlays.push('抽屉「' + (clip(txt(d.querySelector('.el-drawer__header, .el-drawer__title')), 20) || '无标题') + '」');
  });

  const messages = Array.from(document.querySelectorAll('.el-message')).filter(visible).map(m => {
    const cls = m.className || '';
    const kind = cls.indexOf('--error') >= 0 ? 'error' : (cls.indexOf('--success') >= 0 ? 'success' : 'info');
    return kind + ': ' + clip(txt(m), 50);
  });

  const errors = Array.from(document.querySelectorAll('.el-form-item__error'))
    .filter(visible).map(e => clip(txt(e), 40)).slice(0, 10);

  const tabs = Array.from(document.querySelectorAll('.el-tabs__item'))
    .filter(visible).map(t => clip(txt(t), 12)).slice(0, 15);

  const dropdowns = [];
  document.querySelectorAll('.el-select-dropdown').forEach(dd => {
    if (!visible(dd)) return;
    const items = Array.from(dd.querySelectorAll('.el-select-dropdown__item')).filter(visible);
    const emptyEl = dd.querySelector('.el-select-dropdown__empty, .el-select__empty, .el-select-dropdown__loading');
    dropdowns.push({
      count: items.length,
      emptyText: visible(emptyEl) ? clip(txt(emptyEl), 20) : '',
      selected: items.filter(i => i.classList.contains('selected')).map(i => clip(txt(i), 20)).slice(0, 3),
      texts: items.map(i => clip(txt(i), 20)).filter(Boolean).slice(0, 30),
    });
  });

  return {
    title: clip(document.title, 40),
    url: location.href,
    forms: forms, tables: tables, pagination: pagination, buttons: buttons,
    overlays: overlays, messages: messages, errors: errors, tabs: tabs,
    dropdowns: dropdowns,
  };
}"""


def format_summary(data: dict, *, brief: bool = False) -> str:
    """把 :data:`EXTRACT_JS` 提取的结构化 dict 渲染成紧凑 markdown。

    空段落自动省略；整体超过 :data:`MAX_OUTPUT_CHARS` 时硬截断并标注。

    Args:
        data: :data:`EXTRACT_JS` 提取的结构化 dict。
        brief: 超简略模式——只留骨架：表单项的 label/类型/必填/静态选项、
            表格列头与行数、按钮/弹窗/页签等；去掉当前值、首行样本、
            分页数据（展开中的下拉选项保留，因为点击是有意为之）。
    """
    if brief:
        data = {
            **data,
            "forms": [
                {k: f.get(k) for k in ("label", "required", "type", "options", "scope")}
                for f in data.get("forms") or []
            ],
            "tables": [
                {k: t.get(k) for k in ("cols", "rowCount")}
                for t in data.get("tables") or []
            ],
            "pagination": [],
        }
    lines: list[str] = []
    lines.append(f"# 页面摘要：{data.get('title') or '无标题'}")
    lines.append(f"- URL：{data.get('url') or ''}")

    overlays = data.get("overlays") or []
    if overlays:
        lines.append(f"\n## 打开中的弹窗/抽屉：{'、'.join(overlays)}")

    forms = data.get("forms") or []
    if forms:
        lines.append(f"\n## 表单项（{len(forms)}）")
        for f in forms:
            req = "[必填] " if f.get("required") else ""
            label = f.get("label") or "无标签"
            parts = [f"- {req}{label}：{f.get('type') or '未知'}"]
            if f.get("value"):
                parts.append(f"当前“{f['value']}”")
            if (
                f.get("placeholder") and not f.get("value")
                and f["placeholder"] != f.get("label")
            ):
                parts.append(f"提示“{f['placeholder']}”")
            if f.get("options"):
                parts.append("选项：" + "、".join(f["options"]))
            if f.get("scope"):
                parts.append(f"@{f['scope']}")
            lines.append(" ".join(parts))

    tables = data.get("tables") or []
    for idx, t in enumerate(tables, 1):
        lines.append(f"\n## 表格{idx}（数据行 {t.get('rowCount', 0)}）")
        cols = t.get("cols") or []
        if cols:
            lines.append(f"- 列头：{' | '.join(cols)}")
        first_row = t.get("firstRow") or []
        if first_row:
            lines.append(f"- 首行：{' | '.join(first_row)}")

    pagination = data.get("pagination") or []
    if pagination:
        lines.append(f"- 分页：{'；'.join(pagination)}")

    tabs = data.get("tabs") or []
    if tabs:
        lines.append(f"\n## 页签：{'、'.join(tabs)}")

    buttons = data.get("buttons") or []
    if buttons:
        lines.append(f"\n## 按钮：{' / '.join(buttons)}")

    messages = data.get("messages") or []
    if messages:
        lines.append(f"\n## 消息：{'；'.join(messages)}")

    errors = data.get("errors") or []
    if errors:
        lines.append(f"\n## 校验错误：{'；'.join(errors)}")

    dropdowns = data.get("dropdowns") or []
    for idx, d in enumerate(dropdowns, 1):
        selected = d.get("selected") or []
        texts = d.get("texts") or []
        empty = d.get("emptyText") or ""
        seg = f"\n## 展开中的下拉{idx}（共 {d.get('count', 0)} 项"
        if selected:
            seg += f"，已选：{'、'.join(selected)}"
        seg += "）"
        lines.append(seg)
        if texts:
            lines.append(f"- 选项：{'、'.join(texts)}")
        if empty:
            lines.append(f"- 状态：{empty}")

    md = "\n".join(lines)
    if not forms and not tables and not buttons and not overlays:
        md += "\n\n（页面无可见 Element Plus 结构：可能是登录页、白屏或路由未命中）"
    if len(md) > MAX_OUTPUT_CHARS:
        md = md[:MAX_OUTPUT_CHARS] + "\n…（超出上限已截断）"
    return md


def extract_summary(page: Page, *, brief: bool = False) -> str:
    """在已打开的 ``Page`` 上注入 :data:`EXTRACT_JS` 并返回 markdown 摘要。"""
    data = cast("dict", page.evaluate(EXTRACT_JS))
    return format_summary(data, brief=brief)


def _format_custom(result: object) -> str:
    """把自定义 JS 的返回值渲染成紧凑 JSON（不可序列化时降级 str，超限截断）。"""
    try:
        text = json.dumps(result, ensure_ascii=False)
    except TypeError:
        text = str(result)
    if len(text) > MAX_OUTPUT_CHARS:
        text = text[:MAX_OUTPUT_CHARS] + "…（超出上限已截断）"
    return text


def _cdp_click(page: Page, box: FloatRect) -> None:
    """用 CDP ``Input.dispatchMouseEvent`` 发送真实鼠标点击（同 BasePage 的做法）。

    el-select wrapper 只有真实输入事件才能展开（Playwright 合成事件被 overlay 拦截）。
    """
    cdp = page.context.new_cdp_session(page)
    try:
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        time.sleep(0.05)
        cdp.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1,
        })
        time.sleep(0.03)
        cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1,
        })
    finally:
        cdp.detach()


def _click_label(page: Page, label: str) -> None:
    """按标签文本点击表单控件（优先 el-select wrapper 的 CDP 点击，用于展开下拉）。

    找不到 el-select 时退化为按文本点击可见按钮（触发弹窗/页签等交互后提取）。
    """
    dialog = page.locator(".el-dialog").first
    base = dialog if dialog.is_visible() else page
    wrapper = (
        base.locator(".el-form-item", has_text=label).first
        .locator(".el-select__wrapper").first
    )
    if wrapper.count() and wrapper.is_visible():
        box = wrapper.bounding_box()
        if box:
            _cdp_click(page, box)
            page.wait_for_timeout(400)
            return
    btn = page.get_by_role("button", name=label).first
    if btn.count() and btn.is_visible():
        try:
            btn.click(timeout=3000)
        except Exception:
            btn.evaluate("el => el.click()")
        page.wait_for_timeout(400)
        return
    raise RuntimeError(f"找不到可点击的表单项/按钮：{label}")


# Git Bash (MSYS) 会把以 / 开头的参数转换成 Windows 路径：
# "#/it-asset" → "#C:/Program Files/Git/it-asset"。检测到被污染的形式直接报错并给解法。
_MSYS_POLLUTED = re.compile(r"^#?[A-Za-z]:[\\/]")


def build_target_url(target: str, base_url: str) -> str:
    """把 ``target`` 规范成完整 URL。

    支持三种写法：

      - 完整 URL（``http``/``https`` 开头）原样返回；
      - hash 路由（``#/it-asset``）拼到 ``base_url`` 后；
      - 纯路由（``it-asset`` 或 ``/it-asset``）自动补 ``#``——**Git Bash 下推荐**，
        天然免疫 MSYS 参数路径转换。

    Raises:
        RuntimeError: ``target`` 是被 Git Bash MSYS 路径转换污染的形式
            （如 ``#C:/Program Files/Git/it-asset``）。
    """
    if _MSYS_POLLUTED.match(target):
        raise RuntimeError(
            f"目标路由疑似被 Git Bash 路径转换污染：{target!r}。"
            "请改用纯路由（如 it-asset，不带开头 # 或 /），"
            "或加 MSYS_NO_PATHCONV=1 前缀，或传完整 URL",
        )
    if target.startswith("http"):
        return target
    if not target.startswith("#"):
        target = "#" + (target if target.startswith("/") else f"/{target}")
    return f"{base_url.rstrip('/')}/{target}"


def run_probe(
    target: str,
    *,
    base_url: str,
    role: str = "admin",
    auth_dir: Path | str = ".auth",
    username: str = "",
    password: str = "",
    captcha: str = "",
    login_cfg: LoginCfg | None = None,
    click_labels: Sequence[str] = (),
    headless: bool = False,
    use_builtin_chromium: bool | None = None,
    chrome_path: str | None = None,
    slow_mo: int = 0,
    settle_ms: int = 600,
    brief: bool = False,
    extract_js: str | None = None,
) -> str:
    """打开已登录页面并返回 DOM 摘要（markdown）。

    完整流程：登录态缓存（失效且给了账号密码则自动重登）→ 打开页面 →
    依次点击 ``click_labels`` → 注入 JS 提取 → 返回摘要字符串。

    Args:
        target: hash 路由（如 ``#/oa/asset``）或完整 URL。
        base_url: 被测系统基础地址（``target`` 非 http 时拼接）。
        role: 角色名（登录态缓存文件名 ``<auth_dir>/<role>.json``）。
        auth_dir: 登录态缓存目录。
        username / password / captcha: 登录凭据（缓存有效时不使用；
            缓存失效且缺凭据时报错）。
        login_cfg: 登录流程配置，默认 :class:`LoginCfg`（若依/RuoYi 风格）。
        click_labels: 提取前依次点击的表单项标签（展开下拉拿实际选项）。
        headless: 是否无头模式，默认 **False（有头）**——用户不强调一律有头。
        use_builtin_chromium: ``None``（默认）自动模式（内置 Chromium 优先，
            缺失自动下载，失败回退本地 Chrome → Edge）；``True`` 强制内置；
            ``False`` 跳过内置走本地链。``USE_BUILTIN_CHROMIUM`` 环境变量
            （true/false）可覆盖默认。
        chrome_path: 本地 Chrome 路径；为 ``None`` 时按 ``CHROME_PATH`` 环境变量探测。
        slow_mo: 慢放延迟毫秒（调试用）。
        settle_ms: 页面就绪后的额外稳定等待毫秒。
        brief: 超简略模式（只留页面骨架，见 :func:`format_summary`）。
        extract_js: 自定义提取 JS（表达式或箭头函数均可）——在页面上执行并
            返回其结果的紧凑 JSON，**替代**内置摘要。配合 ``click_labels``
            可先交互再取任意局部数据（如整列值、聚合统计）。
    Returns:
        markdown 摘要字符串（``extract_js`` 时为紧凑 JSON 字符串）。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - 环境相关
        raise RuntimeError(
            '探针依赖 playwright，请先安装：pip install "baibao[autotest]"',
        ) from exc

    cfg = login_cfg or LoginCfg()
    auth_dir_path = Path(auth_dir)

    # 内置/本地选择三态：参数显式值 > USE_BUILTIN_CHROMIUM 环境变量 > 自动模式
    if use_builtin_chromium is None:
        env_val = os.getenv("USE_BUILTIN_CHROMIUM", "").lower()
        use_builtin_chromium = (
            True if env_val == "true" else (False if env_val == "false" else None)
        )
    # chrome_path 仅显式传入/环境变量时用；本地链的自动探测交给 launch_browser
    detected = (
        chrome_path if chrome_path is not None
        else (os.getenv("CHROME_PATH") or None)
    )

    with sync_playwright() as p:
        browser = launch_browser(
            p, headless=headless, slow_mo=slow_mo,
            use_builtin_chromium=use_builtin_chromium, chrome_path=detected,
        )
        try:
            state_file = auth_state_path(auth_dir_path, role)
            # 身份绑定校验：缓存属另一账号/站点时强制重登（防跨账号串用得出错误视角结论）
            if not is_auth_valid(
                state_file, username=username or None, base_url=base_url or None,
            ):
                if not (username and password):
                    raise RuntimeError(
                        f"登录态缓存无效（{state_file}）且未提供账号密码"
                        f"（role={role}）：请传 username/password 或配置"
                        " ADMIN_USERNAME/ADMIN_PASSWORD 环境变量",
                    )
                state_file = Path(save_storage_state(
                    browser, cfg, auth_dir_path, role,
                    base_url, username, password, captcha,
                ))

            context = browser.new_context(
                storage_state=str(state_file), viewport=cfg.viewport,
            )
            try:
                page = context.new_page()
                page.set_default_timeout(15000)
                page.set_default_navigation_timeout(30000)

                url = build_target_url(target, base_url)
                # 直接深链（与测试套件同款走法）。动态路由 SPA（如若依）在菜单
                # 未注册完时会跳 404：检测到 404 则等待后重试导航
                page.goto(url)
                for _ in range(3):
                    page.wait_for_load_state("domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass  # 长轮询页面到不了 networkidle，接受现状
                    if "/404" not in page.url:
                        break
                    page.wait_for_timeout(800)
                    page.goto(url)
                page.wait_for_timeout(settle_ms)

                for label in click_labels:
                    _click_label(page, label)

                if extract_js is not None:
                    return _format_custom(page.evaluate(extract_js))
                return extract_summary(page, brief=brief)
            finally:
                context.close()
        finally:
            browser.close()
