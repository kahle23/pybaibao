# cli - 命令行工具模块

提供基于命令模式的 CLI 工具，支持包管理和项目清理等功能。

## 命令列表

| 命令 | 功能 | 用法 |
|------|------|------|
| `pip_install` | 安装 Python 包（自动切换镜像） | `python -m baibao pip_install <包名> [包名2 ...]` |
| `pip_upgrade` | 升级 Python 包 | `python -m baibao pip_upgrade <包名> [包名2 ...]` |
| `py_clean` | 清理构建缓存 | `python -m baibao py_clean [目录路径]` |
| `kbase_init` | 生成知识库目录骨架 / 新增项目目录（必须 -t 指定模板） | `python -m baibao kbase_init -t <模板> [目录]` |
| `ocr` | 识别图片中的文字（OCR，支持 easy/paddle 引擎） | `python -m baibao ocr <图片路径> [--engine paddle]` |
| `help` | 显示帮助信息 | `python -m baibao help [命令名]` |

## 使用示例

### 安装包

```bash
# 安装单个包
python -m baibao pip_install requests

# 安装多个包
python -m baibao pip_install numpy pandas matplotlib
```

### 升级包

```bash
# 升级单个包
python -m baibao pip_upgrade requests

# 升级多个包
python -m baibao pip_upgrade numpy pandas
```

### 清理缓存

```bash
# 清理当前目录的构建缓存
python -m baibao py_clean

# 清理指定目录的构建缓存
python -m baibao py_clean /path/to/project
```

清理操作会删除以下内容：
- `build/` 目录
- `dist/` 目录
- `*.egg-info` 目录
- `__pycache__/` 目录（递归删除）

### 初始化知识库

通过「模板」定义一种知识库长什么样，用 `-t/--template` 指定模板（必须）。
内置「公司」模板：公司资料、项目资产、运营支持、团队流程、知识沉淀、资源工具、归档等顶层职能域，
并预置「自研项目」「三方系统」两套可复制样板。

```bash
# 生成完整骨架（必须指定模板，默认当前目录）
python -m baibao kbase_init -t 公司

# 指定目录 + 指定模板
python -m baibao kbase_init /path/to/knowledge-base -t 公司

# 列出所有可用模板
python -m baibao kbase_init list
```

新增一个具体项目（自动递增编号，平铺到 `02-项目资产/` 下；项目类型由模板定义）：

```bash
# 新增自研项目（必须指定模板，编号自动取下一个，如 01-xxx）
python -m baibao kbase_init new -t 公司 自研 我的系统

# 新增三方系统（指定目录 + 指定模板）
python -m baibao kbase_init new 三方 采购系统 /path/to/knowledge-base -t 公司
```

设计原则：顶层按稳定的职能域划分，文件用命名规范承载维度（日期/项目/类型/标题/版本），不靠多层文件夹表达维度；样板项目（以"模板"开头）固定使用 99 编号。

#### 新增知识库模板（扩展性）

模板是 `KbaseTemplate` 的实例，注册后立即可用，命令侧无需改动：

```python
from baibao.cli.kbase_command import KbaseTemplate, register_template

register_template(KbaseTemplate(
    name="个人",                  # 用作 -t 参数
    description="个人知识库",
    top_levels={"00-首页": "...", "01-笔记": "..."},
    second_levels={"00-首页": [], "01-笔记": ["技术", "生活"]},
    project_templates={"个人项目": {"00-概览": [], "01-笔记": []}},
    seed_projects=[("个人项目", "模板个人项目")],
))
```

注册后即可 `python -m baibao kbase_init -t 个人`。同分类多版本只需注册多个不同 `name`（如「公司」「公司v2」）。

### 图片文字识别（OCR）

识别图片中的文字，结果输出到 stdout。默认 EasyOCR，可切 PaddleOCR（按已装版本自动选 V2/V3）。

```bash
# 默认 easy 引擎
python -m baibao ocr image.png

# 用 PaddleOCR（中文精度更高，自动按已装版本选 V2/V3）
python -m baibao ocr image.png --engine paddle

# 指定语言（en 英文、japan 日文、ko 韩文、ch_tra 繁中）
python -m baibao ocr image.png --engine paddle --lang en

# 多线程 CPU 推理（仅 paddle 生效，加快 CPU 识别）
python -m baibao ocr image.png --engine paddle --cpu-threads 8

# 启用 GPU（需已装 GPU 版依赖：paddle 需 paddlepaddle-gpu）
python -m baibao ocr image.png --engine paddle --gpu

# 强制指定版本
python -m baibao ocr image.png --engine paddle3   # 3.x API

# 输出含坐标与置信度的 JSON 详情
python -m baibao ocr image.png --engine paddle --details

# 用分隔符包裹结果（防日志混入 stdout，配合 2>$null 最稳）
python -m baibao ocr image.png --engine paddle --delim __OCR__ 2>$null

# 把识别框画到图上另存
python -m baibao ocr image.png --engine paddle --draw out.png
```

选项：

| 选项 | 说明 |
|------|------|
| `-e, --engine {easy,paddle,paddle2,paddle3}` | OCR 引擎，默认 `easy`；`paddle` 为自动分发（按已装版本选 V2/V3） |
| `--lang CODE` | 识别语言，默认 `ch`（中英）；如 `en`、`japan`、`ko`、`ch_tra` |
| `--gpu` | 启用 GPU（easyocr 需 CUDA 版 torch；paddle 需 `paddlepaddle-gpu`） |
| `--cpu-threads N` | CPU 推理线程数（仅 paddle 引擎生效）。建议取核数一半以上，否则识别很慢；PowerShell 可用 `([int]([int]$env:NUMBER_OF_PROCESSORS * 0.75))` 自动取 75% |
| `-d, --details` | 输出 JSON 数组，**每项一行紧凑输出**：`text` / `confidence`(0~1) / `bbox`(四点多边形 `[[x1,y1],...]`) |
| `--delim STR` | 结果分隔符：设则用其在 stdout 结果前后各占一行包裹，便于在夹杂日志时精准截取 |
| `--draw PATH` | 将识别框绘制到图片并保存到 PATH |

> 引擎间的参数差异（语言码、gpu/device、cpu_threads）由 `baibao.ai.ocr.build_ocr_engine` 统一映射，CLI 只暴露这套引擎无关的选项；进阶调参可用 Python API（`OcrCfg` + `build_ocr_engine`，或直接构造各引擎类）。

> 识别文字走 **stdout**，日志/下载进度走 **stderr**，两路分离。想要干净输出（只留文字），命令末尾加 `2>$null` 丢弃 stderr；若担心 OCR 框架偶发把日志写到 stdout，加 `--delim <STR>` 把结果包裹起来，取两个分隔符行之间的内容即可万无一失。失败时 stdout 会输出 `(OCR 失败：…)` 标记，去掉 `2>$null` 即可看 stderr 详细报错。Windows 下 stdout 已强制 UTF-8，不会因生僻字/符号（如 `☐`）打印报错。首次运行会自动下载引擎依赖与模型（一次性）。PaddleOCR 在 Python 3.13 / Windows 上的版本兼容与已知坑见 [AI 模块文档](./ai.md#paddleocr-版本与已知坑重要)。

### 查看帮助

```bash
# 查看所有命令
python -m baibao help

# 查看特定命令的详细用法
python -m baibao help pip_install
```

## 镜像源

`pip_install` 和 `pip_upgrade` 命令内置了多个镜像源，会自动尝试以下源：
- 清华大学镜像
- 阿里云镜像
- 官方 PyPI

如果某个源失败，会自动切换到下一个源，无需手动配置。

## 架构说明

该模块采用命令模式设计：

- `Command` 基类：定义命令接口（`name`、`description`、`usage`、`execute`）
- `CommandManager`：管理命令注册和执行
- 具体命令类：实现具体的命令逻辑

### 扩展命令

要添加自定义命令，只需：

1. 创建继承 `Command` 的类
2. 实现必要的属性和方法
3. 在 `cli/__init__.py` 中注册命令

```python
from kunlun.base.cli import Command

class MyCommand(Command):
    @property
    def name(self) -> str:
        return "my_command"
    
    @property
    def description(self) -> str:
        return "我的自定义命令"
    
    @property
    def usage(self) -> str:
        return "python -m baibao my_command [args]"
    
    def execute(self, args):
        # 实现命令逻辑
        pass
```
