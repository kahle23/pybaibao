# autotest — Playwright E2E 测试基础设施

把日常 Web 自动化测试中反复用到的能力封装成简洁 API：页面对象基类、浏览器启动、
登录态缓存、接口基类、可选启用的 pytest fixture。

源自实战项目，解决 Vue 3 + Element Plus 后台的 E2E 自动化测试硬骨头。

<br />

## 安装

```bash
# 安装 baibao 与 autotest 可选依赖（playwright / python-dotenv / faker 等）
python -m pip install "baibao[autotest]" -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 安装 Playwright 浏览器内核（首次必装）
python -m playwright install chromium
```

> `faker` 在国内默认 PyPI 源可能装不上，务必用清华源。

<br />

## 模块概览

| 模块 | 关键符号 | 用途 |
|------|----------|------|
| `baibao.autotest.page` | `BasePage` | 页面对象基类：Element Plus 组件操作 + CDP 真实点击 + 对话框作用域 + 表格行列助手 |
| `baibao.autotest.browser` | `detect_chrome_path` / `launch_browser` | 本地 Chrome 路径探测与浏览器启动 |
| `baibao.autotest.login_state` | `LoginCfg` / `do_login` / `save_storage_state` / `is_auth_valid` | 数据驱动登录流程 + 登录态缓存（TTL） |
| `baibao.autotest.api` | `ApiBase` | 后端接口基类：复用浏览器登录态 cookie + 防御式 JSON 解析 |
| `baibao.autotest.fixtures` | `browser` / `base_url` / `faker` 等 | opt-in pytest fixture（`pytest_plugins` 启用） |
| `baibao.autotest.conftest_template` | — | 角色级 fixture 参考样板（复制改造） |

<br />

## 快速上手

### 1. 写页面对象（继承 BasePage）

```python
from baibao.autotest.page import BasePage

class AssetListPage(BasePage):
    """资产列表页。"""

    def click_add_button(self):
        self.click("button:has-text('新增')")

    def search(self, keyword: str):
        self.fill("input[placeholder='请输入编号']", keyword)
        self.click("button:has-text('搜索')")
        self.wait_ready()
```

### 2. 写接口客户端（继承 ApiBase，复用登录态）

```python
from baibao.autotest.api import ApiBase

class AssetApi(ApiBase):
    def add_asset(self, **payload) -> dict:
        return self._parse_json(self._post("/oa/asset/record/add", payload))

    def delete_asset(self, *ids: int) -> dict:
        return self._parse_json(self._post("/oa/asset/record/delete", {"ids": list(ids)}))
```

### 3. 启用基础 fixture（项目根 conftest.py）

```python
# conftest.py
pytest_plugins = ["baibao.autotest.fixtures"]
```

启用后即可用 `browser` / `base_url` / `faker` / `today_str` / `unique_id` 等 fixture。
角色级 fixture（`storage_state` / `page` / `api_context`）请参考
`baibao.autotest.conftest_template`，复制改造到项目 conftest。

### 4. 配置环境变量（.env）

```ini
BASE_URL=http://your-host
ADMIN_USERNAME=admin
ADMIN_PASSWORD=xxx
CAPTCHA_VALUE=1234
HEADLESS=false
SLOW_MO=0
USE_BUILTIN_CHROMIUM=false      # true 走内置 Chromium，false 走本地 Chrome
CHROME_PATH=                    # 可选，显式指定 Chrome 路径
```

<br />

## LoginCfg 字段

`LoginCfg` 把登录流程数据驱动化，默认值匹配若依/RuoYi 风格 hash 路由后台。
非 RuoYi 站点改字段选择器即可，无需改源码。

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `login_url_suffix` | `"/#/login"` | 拼接到 base_url 后的登录页路径 |
| `username_selector` | `'input[placeholder="用户名"]'` | 用户名输入框选择器 |
| `password_selector` | `'input[type="password"]'` | 密码输入框选择器 |
| `login_button_selector` | `'button.el-button--primary'` | 登录按钮选择器 |
| `captcha_selectors` | `[...]` | 验证码候选选择器（顺序回退；空列表表示无验证码） |
| `success_url_not_contains` | `"/login"` | 登录成功后 URL 不再包含的片段 |
| `viewport` | `{"width":1920,"height":1080}` | 视口尺寸 |

<br />

## 关键设计：为什么自管理 Playwright

本模块**刻意不使用** `pytest-playwright` 提供的 `context` / `page` fixture，
而是自己管理 Playwright 生命周期（`fixtures.browser` + 角色级 `admin_page`）。

**原因**：Element Plus 的 `el-select` 放在 `el-dialog` 内时，pytest-playwright 托管 context
下 Playwright 的合成 `click()` 事件无法触发 Vue 的 `pointerdown` 处理链，下拉面板展不开。
自管理 context + CDP 真实点击才能解决。

<br />

## 排坑要点

### 1. el-select 在弹窗内点不开

**现象**：`el-select` 在 `el-dialog` 内，`locator.click()` / `force=True` / `page.mouse.click()`
都无法展开下拉，或展开了但选不中。

**根因**：Playwright 合成事件不触发 Vue 的 `pointerdown`；overlay 遮挡导致点击落空；
全局选择器命中了搜索栏的同名 wrapper（页面上有 9 个 `.el-select__wrapper`）。

**解法**（已内置在 `BasePage.el_select`）：
- 用 `_scope_form_item` 把选择器限定到 `.el-dialog` 内部
- 用 `_cdp_click`（CDP `Input.dispatchMouseEvent`）发送浏览器底层真实鼠标事件，
  完整触发 `mouseMoved → mousePressed → mouseReleased` 链

### 2. pytest-playwright 的 page fixture 不要用

装了 `pytest-playwright` 后它自动注册 `page` / `context` fixture。**不要用它们**，
否则会触发上述事件兼容问题。本模块的 `fixtures.browser` + 角色级 `admin_page` 已自管理。

### 3. 登录态缓存失效

`.auth/<role>.json` 默认 12 小时 TTL，过期自动重新登录。可调 `is_auth_valid(path, max_age_hours=...)`。
缓存文件含 cookie，**勿提交到 git**，加入 `.gitignore`。

<br />

## 运行测试

```bash
# 全量
pytest

# 仅冒烟（P0）
pytest -m smoke

# 调试：可见浏览器 + 慢放
pytest --headed --slowmo 200

# 失败时截图/录屏（pytest-playwright 提供的 CLI 选项）
pytest --screenshot=only-on-failure --video=retain-on-failure --tracing=retain-on-failure

# 调试器
PWDEBUG=1 pytest tests/it_asset/test_asset_crud.py
```
