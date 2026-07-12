# BaiBao (百宝)

方便好用的 Python 常用功能库。把日常开发中反复用到的能力（日志、包管理、数据库、邮件、OCR）封装成简洁的 API，开箱即用。

## 优势

- **统一抽象，随时替换** — LLM、OCR、模板引擎均采用策略模式设计，共享同一抽象接口，运行时自由切换后端实现
- **零配置依赖管理** — `import_module()` 首次导入时自动检测并安装缺失的包；pip 操作内置清华、阿里云等多镜像自动 fallback
- **数据库双模支持** — 连接池模式（高并发/线程安全）与单连接模式（轻量级）自由切换，MySQL / PostgreSQL 驱动自动安装
- **可扩展 CLI 框架** — 基于注册机制的命令行系统，支持命令缩写、帮助命令、线程安全，轻松添加自定义命令
- **配置即代码** — 所有配置类均为 `dataclass`，支持从 JSON 一键加载，自动校验必填字段，拒绝运行时 TypeError
- **邮件收发一体** — 支持纯文本、HTML 和附件，自动判断 SSL / STARTTLS 加密方式，抄送/密送/群发一应俱全


## 模块概览

| 分类 | 模块 | 功能 |
|------|------|------|
| **AI** | `baibao.ai` | LLM 对话（OpenAI 兼容）、OCR 文字识别（EasyOCR/PaddleOCR） |
| **基础** | `baibao.base` | 日志、包管理、动态导入、配置加载 |
| **数据处理** | `baibao.data` | 货币查询、模板引擎（Jinja2） |
| **数据** | `baibao.db` | MySQL/PostgreSQL 连接池与查询 |
| **消息** | `baibao.message` | 邮件发送（文本/HTML/附件） |
| **工具** | `baibao.util` | CLI 命令行工具（包管理、项目清理） |


## 快速上手

```bash
# 安装 baibao（使用清华镜像源加速）
pip install baibao -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

```python
from baibao.base import util, log

# 自动下载并导入模块（未安装时自动安装）
numpy = util.import_module("numpy")

# 日志输出
log.info("Hello BaiBao")
```

更多用法请查看 [使用示例](#使用示例)。


## 开发指南

### 本地安装

```bash
# 开发模式（修改源码立刻生效，无需重新安装）
python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 基础安装
python -m pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 开发依赖

```bash
# 安装开发依赖（代码检查、测试等）
python -m pip install ".[dev]"

# 安装全部依赖
python -m pip install ".[all]"
```

### 代码质量

```bash
# 代码风格检查
python -m ruff check src/

# 类型检查
python -m mypy src/

# 运行测试
python -m pytest tests/
```

### 工具命令

```bash
# 清理 __pycache__ 缓存
python -m baibao py_clean .
```

## 许可证

GPL-3.0-or-later



## 使用示例

### ai - AI 模块

#### ai.llm - LLM 大语言模型

支持 OpenAI 兼容 API（OpenAI、DeepSeek、Moonshot、智谱、本地 Ollama 等），提供单轮/多轮对话和流式输出。

```python
from baibao.ai.llm import chat, set_llm_service, stream_chat
from baibao.ai.llm.openai_llm import OpenAiLlm

# 1. 设置 LLM 服务（支持环境变量 OPENAI_API_KEY）
set_llm_service("default", OpenAiLlm(
    api_key="sk-xxx",
    base_url="https://api.openai.com/v1",
    model="gpt-4o-mini",
))

# 2. 单轮对话
response = chat("你好，请介绍一下自己")
print(response.content)

# 3. 流式输出
for chunk in stream_chat("讲一个故事"):
    print(chunk, end="", flush=True)
```

> 完整文档请参考 [AI 模块使用指南](https://github.com/kahle23/pybaibao/blob/master/docs/ai.md)

---

#### ai.ocr - 文字识别

支持 EasyOCR 和 PaddleOCR 两种引擎，运行时自由切换。

```python
from baibao.ai.ocr import recognize, recognize_with_details

# 识别图片文字（默认 EasyOCR）
text = recognize("invoice.png")
print(text)

# 获取详细结果（含位置和置信度）
for item in recognize_with_details("image.png"):
    print(f"{item.text} ({item.confidence:.1%})")
```

> 完整文档请参考 [AI 模块使用指南](docs/ai.md)

---

### base - 基础工具包

提供动态导入、日志、包管理、时间处理和数据验证等基础工具。

```python
from baibao.base import util, log, pip, time, validate

# 动态导入模块（未安装时自动安装）
numpy = util.import_module("numpy")

# 日志输出
log.info("Hello BaiBao")

# 安装包
pip.install("requests")

# 解析时间字符串
dt = time.parse("2024-01-15 14:30:00")
```

> 完整文档请参考 [base 模块使用指南](https://github.com/kahle23/pybaibao/blob/master/docs/base.md)

---

### db - 数据库

支持 MySQL 和 PostgreSQL，数据库驱动（pymysql / psycopg2）在首次使用时自动安装。
连接池模式线程安全，单连接模式仅限单线程使用。

> 完整文档请参考 [数据库模块](https://github.com/kahle23/pybaibao/blob/master/docs/db.md)

```python
from baibao import sql, DbCfg, DbClient
# 或者通过子模块导入
# from baibao.db import sql, DbCfg, DbClient

# 1. 配置并注册数据源
cfg = DbCfg(host="localhost", port=3306, username="root",
            password="123456", database="test_db")
sql.set_client("default", cfg)

# 2. 执行写操作
sql.exec("INSERT INTO users (name, email) VALUES (%s, %s)",
         params=("张三", "zhangsan@example.com"))

# 3. 执行查询
users = sql.query("SELECT * FROM users WHERE name = %s", params=("张三",))
```

---

### message - 消息发送

#### message.email - 邮件发送

支持纯文本、HTML 和带附件的邮件发送，支持抄送、密送和群发。自动判断 SSL / STARTTLS 加密方式。

> 完整文档请参考 [消息发送模块](https://github.com/kahle23/pybaibao/blob/master/docs/message.md)

```python
from baibao.message.email import EmailClient, EmailCfg

config = EmailCfg(
    send_server="smtp.qq.com",
    send_port=465,
    username="your_email@qq.com",
    password="your_auth_code"
)

client = EmailClient(config)
client.send(to="recipient@example.com", subject="测试", content="Hello")
```

---

### data - 数据处理

#### data.currency - 货币查询

提供币种数据对象及查询工具，内置人民币、美元、欧元等常用货币，支持按符号、编码、名字查询。

```python
from baibao.data import currency

# 查询货币信息
c = currency.get_by_code("CNY")   # Currency(symbol='￥', code='CNY', name='人民币')
c = currency.get_by_symbol("$")   # Currency(symbol='$', code='USD', name='美元')

# 智能搜索（自动匹配符号/编码/名字）
c = currency.search_first("欧元")  # Currency(symbol='€', code='EUR', name='欧元')

# 快捷获取符号
symbol = currency.get_symbol_by_code("USD")  # "$"
```

---

#### data.template - 模板引擎 (待完善)

基于 Jinja2 的模板引擎，支持字符串/文件渲染、自定义过滤器、全局变量、运行时切换引擎。jinja2 库首次使用时自动安装。

```python
from baibao.data.template import render_string

# 渲染模板字符串
result = render_string("Hello, {{ name }}!", name="World")

# 使用过滤器和循环
template = "物品: {% for item in items %}{{ item }} {% endfor %}"
result = render_string(template, items=["苹果", "香蕉", "橙子"])
```

> 完整文档请参考 [data 模块使用指南](https://github.com/kahle23/pybaibao/blob/master/docs/data.md)

---

### util - 命令行工具

提供基于命令模式的 CLI 工具，支持包管理和项目清理。内置多镜像源自动切换。

```bash
# 安装包（自动切换镜像源）
python -m baibao pip_install requests

# 安装多个包
python -m baibao pip_install numpy pandas matplotlib

# 升级包
python -m baibao pip_upgrade requests

# 清理构建缓存（build/dist/__pycache__）
python -m baibao py_clean .

# 查看所有命令
python -m baibao help
```

> 完整文档请参考 [util 命令行工具模块](https://github.com/kahle23/pybaibao/blob/master/docs/util.md)


