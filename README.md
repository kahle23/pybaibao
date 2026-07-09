# BaiBao (百宝)

方便好用的 Python 常用功能库。把日常开发中反复用到的能力（日志、包管理、数据库、邮件、OCR）封装成简洁的 API，开箱即用。

## 优势

- **依赖自动安装** — `import_module()` 首次导入时自动下载安装缺失的包，无需手动 pip install
- **镜像自动切换** — 内置清华、阿里云、中科大等多个 PyPI 镜像，按优先级自动 fallback，国内网络畅通无阻
- **配置即代码** — 所有配置类均为 `dataclass`，支持从 JSON 文件一键加载，自动校验必填字段
- **数据库开箱即用** — 连接池基于 DBUtils，驱动包首次连接时自动安装，支持 MySQL / PostgreSQL
- **OCR 统一接口** — EasyOCR 和 PaddleOCR 共享同一抽象基类，运行时随时切换引擎

## 模块概览

| 分类 | 模块 | 说明 |
|------|------|------|
| **基础设施** | `baibao.base.log` | 带颜色和级别的日志输出 |
| | `baibao.base.pip` | 多镜像源自动切换的包安装工具 |
| | `baibao.base.util` | 动态导入模块、加载 JSON 配置等通用工具 |
| **数据存储** | `baibao.db` | 数据库连接池（MySQL / PostgreSQL） |
| **消息通知** | `baibao.message.email` | 邮件发送（纯文本、HTML、附件） |
| **文字识别** | `baibao.ai.ocr` | OCR 文字识别（EasyOCR / PaddleOCR） |

## 安装

```bash
# 基础安装（安装后 import baibao 即可使用）
python -m pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 开发模式（修改源码立刻生效，无需重新安装）
python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 可选：安装 OCR 引擎依赖
python -m pip install ".[easyocr]"    # EasyOCR
python -m pip install ".[paddleocr]"  # PaddleOCR
python -m pip install ".[all]"        # 全部
```

## 快速上手

pip install baibao -i https://pypi.tuna.tsinghua.edu.cn/simple/


```python
from baibao.base import util

# 自动下载并导入 numpy（如果本机没装的话）
numpy = util.import_module("numpy")
```

更多用法请查看 [使用示例](docs/usage.md)。

## 开发环境

```bash
# 安装开发依赖
python -m pip install ".[dev]"

# 代码风格检查
python -m ruff check src/

# 类型检查
python -m mypy src/

# 运行测试
python -m pytest tests/
```

## 许可证

GPL-3.0-or-later



