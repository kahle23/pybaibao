# data 模块使用指南

> 本文档详细记录 `baibao.data` 包中各子模块的使用方法。

## 目录

- [currency - 货币模块](#1-currency---货币模块)
- [template - 模板引擎模块](#2-template---模板引擎模块)

---

## 1. currency - 货币模块

提供币种数据对象 `Currency` 及相关查询、管理工具。内置人民币、美元、欧元、英镑、俄罗斯卢布、港币、新加坡元等常用货币。

### 1.1 数据结构

```python
from baibao.data import currency

# Currency 是 frozen dataclass，包含三个字段
# symbol: 符号，如 ￥、$
# code:   编码，如 CNY、USD
# name:   名字，如 人民币、美元
```

### 1.2 查询货币

```python
from baibao.data import currency

# 根据符号查询
c = currency.get_by_symbol("￥")
print(c)  # Currency(symbol='￥', code='CNY', name='人民币')

# 根据编码查询（忽略大小写）
c = currency.get_by_code("usd")
print(c)  # Currency(symbol='$', code='USD', name='美元')

# 根据名字查询
c = currency.get_by_name("欧元")
print(c)  # Currency(symbol='€', code='EUR', name='欧元')

# 智能搜索：依次匹配符号、编码、名字，返回第一个匹配项
c = currency.search_first("HK$")
c = currency.search_first("GBP")
c = currency.search_first("新加坡")
```

### 1.3 获取符号快捷方法

```python
from baibao.data import currency

# 根据编码获取符号
symbol = currency.get_symbol_by_code("CNY")       # "￥"
symbol = currency.get_symbol_by_code("USD")       # "$"
symbol = currency.get_symbol_by_code("UNKNOWN")   # ""（未找到返回默认值）
symbol = currency.get_symbol_by_code("UNKNOWN", default="N/A")  # "N/A"
symbol = currency.get_symbol_by_code("")          # ""（空输入直接返回默认值）
```

### 1.4 新增币种

```python
from baibao.data import currency

# 新增成功返回 True
ok = currency.add(symbol="₩", code="KRW", name="韩元")
print(ok)  # True

# 编码重复时返回 False
ok = currency.add(symbol="¥", code="CNY", name="人民币")
print(ok)  # False

# 参数为空时返回 False
ok = currency.add(symbol="", code="XXX", name="测试")
print(ok)  # False
```

### 1.5 删除币种

```python
from baibao.data import currency

# 删除成功返回 True
ok = currency.remove("KRW")
print(ok)  # True

# 编码不存在时返回 False
ok = currency.remove("UNKNOWN")
print(ok)  # False
```

---

## 2. template - 模板引擎模块 (待完善)

提供基于策略模式的模板引擎抽象，内置 Jinja2 实现。支持模板字符串和文件渲染、自定义过滤器、全局变量、运行时切换引擎等特性。

jinja2 库会在首次使用时自动安装。

### 2.1 快速上手

```python
from baibao.data.template import render_string

# 渲染模板字符串
result = render_string("Hello, {{ name }}!", name="World")
print(result)  # Hello, World!
```

### 2.2 渲染模板字符串

```python
from baibao.data.template import render_string

# 变量替换
result = render_string("{{ name | upper }}", name="hello")
print(result)  # HELLO

# 条件语句
template = """
{% if user %}
欢迎, {{ user }}!
{% else %}
请登录。
{% endif %}
"""
result = render_string(template, user="张三")
print(result.strip())  # 欢迎, 张三!

# 循环
template = """
物品列表:
{% for item in items %}
- {{ item }}
{% endfor %}
"""
result = render_string(template, items=["苹果", "香蕉", "橙子"])
print(result.strip())
```

### 2.3 渲染模板文件

```python
from baibao.data.template import render_file

# 渲染 HTML 模板文件
result = render_file(
    "templates/report.html",
    title="月度报告",
    author="张三",
    items=["项目A", "项目B"]
)
print(result)
```

模板文件示例 `templates/report.html`：

```html
<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body>
    <h1>{{ title }}</h1>
    <p>作者: {{ author }}</p>
    <ul>
    {% for item in items %}
        <li>{{ item }}</li>
    {% endfor %}
    </ul>
</body>
</html>
```

### 2.4 获取详细渲染结果

```python
from baibao.data.template import render_string_with_details

details = render_string_with_details(
    "Hello, {{ name }}! Today is {{ day }}.",
    name="World",
    day="Monday"
)

print(f"内容: {details.content}")          # Hello, World! Today is Monday.
print(f"模板名称: {details.template_name}") # None（字符串渲染无文件名）
print(f"使用的变量: {details.variables}")    # {'name': 'World', 'day': 'Monday'}
```

### 2.5 自定义 Jinja2Engine

```python
from baibao.data.template import Jinja2Engine

# 创建引擎实例，可配置模板目录、自动转义、未定义变量处理等
engine = Jinja2Engine(
    template_dir="templates",   # 模板文件目录
    autoescape=False,           # 禁用 HTML 自动转义
    undefined="undefined",      # 未定义变量返回空字符串（而非报错）
)

# 添加自定义过滤器
engine.add_filter("reverse", lambda s: s[::-1])
result = engine.render_string("{{ name | reverse }}", name="Hello")
print(result)  # olleH

# 添加全局变量（所有模板可访问）
engine.add_global("site_name", "我的网站")
engine.add_global("version", "1.0.0")
result = engine.render_string("欢迎访问 {{ site_name }} v{{ version }}")
print(result)  # 欢迎访问 我的网站 v1.0.0
```

### 2.6 运行时切换引擎

```python
from baibao.data.template import render_string, set_template_engine, get_template_engine

# 注册自定义引擎
custom_engine = Jinja2Engine(autoescape=False, undefined="undefined")
set_template_engine("custom", custom_engine)

# 使用指定引擎渲染
result = render_string("Hello, {{ name }}!", engine_name="custom", name="World")

# 获取引擎实例进行操作
engine = get_template_engine("custom")
result = engine.render_string("{{ name | upper }}", name="hello")
```

### 2.7 错误处理

```python
from baibao.data.template import render_string, render_file

# 模板语法错误 → ValueError
try:
    render_string("{{ unclosed")
except ValueError as e:
    print(f"语法错误: {e}")

# 未定义变量（strict 模式）→ UndefinedError
try:
    render_string("{{ undefined_var }}")
except Exception as e:
    print(f"未定义变量: {e}")

# 文件不存在 → FileNotFoundError
try:
    render_file("nonexistent.html")
except FileNotFoundError as e:
    print(f"文件不存在: {e}")
```

### 2.8 Jinja2Engine 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template_dir` | `str \| None` | `None` | 模板文件目录，为 None 时只能渲染字符串 |
| `autoescape` | `bool` | `True` | 是否启用 HTML 自动转义 |
| `cache_size` | `int` | `400` | 模板缓存大小，0 禁用缓存 |
| `undefined` | `str` | `"strict"` | 未定义变量处理：`strict` 报错 / `undefined` 返回空 / `debug` 返回调试信息 |
| `filters` | `dict` | `{}` | 自定义过滤器字典 |
| `globals` | `dict` | `{}` | 全局变量字典 |

---

## 综合示例

### 示例 1：货币格式化

```python
from baibao.data import currency

def format_price(amount: float, code: str) -> str:
    """格式化价格，自动添加货币符号。"""
    symbol = currency.get_symbol_by_code(code, default=code)
    return f"{symbol}{amount:,.2f}"

print(format_price(1234.5, "CNY"))   # ￥1,234.50
print(format_price(99.99, "USD"))    # $99.99
print(format_price(500, "EUR"))      # €500.00
print(format_price(100, "UNKNOWN"))  # UNKNOWN100.00
```

### 示例 2：模板渲染生成报告

```python
from baibao.data.template import render_string

template = """
{{ title }}
{{ "=" * title | length }}

日期: {{ date }}
作者: {{ author }}

项目清单:
{% for item in items %}
  {{ loop.index }}. {{ item.name }} - {{ item.status }}
{% endfor %}

合计: {{ items | length }} 个项目
"""

result = render_string(
    template,
    title="周工作报告",
    date="2024-01-15",
    author="张三",
    items=[
        {"name": "需求分析", "status": "已完成"},
        {"name": "接口开发", "status": "进行中"},
        {"name": "单元测试", "status": "待开始"},
    ]
)
print(result)
```
