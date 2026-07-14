# BaiBao (百宝)

方便好用的 Python 常用功能库。把日常开发中反复用到的能力（日志、包管理、数据库、邮件、OCR）封装成简洁的 API，开箱即用。<br />

[![PyPI](https://img.shields.io/pypi/v/baibao.svg)](https://pypi.org/project/baibao/)

<br />

## 优势

- **统一抽象，随时替换** — LLM、OCR、模板引擎均采用策略模式设计，共享同一抽象接口，运行时自由切换后端实现
- **零配置依赖管理** — `import_module()` 首次导入时自动检测并安装缺失的包；pip 操作内置清华、阿里云等多镜像自动 fallback
- **数据库双模支持** — 连接池模式（高并发/线程安全）与单连接模式（轻量级）自由切换，MySQL / PostgreSQL 驱动自动安装
- **可扩展 CLI 框架** — 基于注册机制的命令行系统，支持命令缩写、帮助命令、线程安全，轻松添加自定义命令
- **配置即代码** — 所有配置类均为 `dataclass`，支持从 JSON 一键加载，自动校验必填字段，拒绝运行时 TypeError
- **邮件收发一体** — 支持纯文本、HTML 和附件，自动判断 SSL / STARTTLS 加密方式，抄送/密送/群发一应俱全

<br />

## 开始使用

### 安装

```bash
# 安装 baibao（使用清华镜像源加速）
pip install baibao -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

<br />

### 模块概览

| 分类 | 模块 | 功能 | 文档 |
|------|------|------|------|
| **AI** | `baibao.ai` | LLM 对话（OpenAI 兼容）、OCR 文字识别（EasyOCR/PaddleOCR） | [文档](https://github.com/kahle23/pybaibao/blob/master/docs/ai.md) |
| **基础** | `baibao.base` | 日志、包管理、动态导入、配置加载 | [文档](https://github.com/kahle23/pybaibao/blob/master/docs/base.md) |
| **数据处理** | `baibao.data` | 货币查询、模板引擎（Jinja2） | [文档](https://github.com/kahle23/pybaibao/blob/master/docs/data.md) |
| **数据** | `baibao.db` | MySQL/PostgreSQL 连接池与查询 | [文档](https://github.com/kahle23/pybaibao/blob/master/docs/db.md) |
| **消息** | `baibao.message` | 邮件发送（文本/HTML/附件） | [文档](https://github.com/kahle23/pybaibao/blob/master/docs/message.md) |
| **工具** | `baibao.util` | CLI 命令行工具（包管理、项目清理） | [文档](https://github.com/kahle23/pybaibao/blob/master/docs/util.md) |

<br />

## 开发指南

### 本地安装

```bash
# 开发模式（修改源码立刻生效，无需重新安装）
python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 基础安装
python -m pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

<br />

### 开发依赖

```bash
# 安装开发依赖（代码检查、测试等）
python -m pip install ".[dev]"

# 安装全部依赖
python -m pip install ".[all]"
```

<br />

### 代码质量

```bash
# 代码风格检查
python -m ruff check src/

# 类型检查
python -m mypy src/

# 运行测试
python -m pytest tests/
```

<br />

### 工具命令

```bash
# 清理 __pycache__ 缓存
python -m baibao py_clean .
```

<br />

## 许可证

GPL-3.0-or-later

<br />


