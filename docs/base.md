# base 模块使用指南

> 本文档详细记录 `baibao.base` 包中各工具模块的使用方法。

## 目录

- [util - 工具模块](#1-util---工具模块)
- [log - 日志模块](#2-log---日志模块)
- [pip - 包管理工具](#3-pip---包管理工具)
- [time - 时间模块](#4-time---时间模块)
- [validate - 验证模块](#5-validate---验证模块)
- [env - 环境模块](#6-env---环境模块)
- [cli - 命令模块](#7-cli---命令模块)

---

## 1. util - 工具模块

提供通用的工具方法，包括动态导入和配置加载。

### 1.1 动态导入模块

自动检测并安装缺失的 Python 包，安装失败时抛出 `ImportError`。

```python
from baibao.base import util

# 导入标准库（已存在，直接返回）
json = util.import_module("json")

# 导入第三方包（未安装时自动安装）
numpy = util.import_module("numpy")

# 模块名和安装包名不同时，分别指定
cv2 = util.import_module("cv2", install_name="opencv-python")
```

### 1.2 从 JSON 文件加载 dataclass 配置

通用方法，适用于任何 `dataclass` 定义的配置类。自动校验必填字段，缺少字段时抛出 `ValueError`。

```python
from dataclasses import dataclass
from baibao.base import util

@dataclass
class AppConfig:
    app_name: str
    debug: bool
    port: int = 8080

# 从 JSON 文件加载，自动校验 app_name、debug 是否存在
config = util.load_dataclass_from_json_file("config.json", AppConfig)
print(config.app_name, config.port)

# 也支持 Path 对象
from pathlib import Path
config = util.load_dataclass_from_json_file(Path("config.json"), AppConfig)
```

对应的 `config.json`：

```json
{
    "app_name": "my-app",
    "debug": true
}
```

### 1.3 创建模块懒加载器

生成一个 `__getattr__` 函数，用于实现模块属性的延迟导入。首次访问属性时才导入对应模块，导入后缓存到全局变量中，有效提升大型项目的启动性能。

```python
from baibao.base import util

# 定义懒加载映射
_LAZY_IMPORTS = {
    "test": "baibao.test.t1",
    "test1": "baibao.test.t2",
}

# 创建懒加载函数
__getattr__ = util.create_lazy_loader(_LAZY_IMPORTS)

# 访问属性时才实际导入模块
# 例如：baibao.test 访问时才会导入 baibao.test.t1
```

---

## 2. log - 日志模块

提供带颜色和级别的日志输出，支持 DEBUG / INFO / WARN / ERROR 四个级别，以及始终输出的 USAGE 级别。

### 2.1 日志级别管理

```python
from baibao.base import log

# 查看当前日志级别（默认 "INFO"）
current_level = log.get_log_level()

# 设置日志级别
log.set_log_level("DEBUG")
log.set_log_level("WARN")
```

### 2.2 各级别日志输出

```python
from baibao.base import log

log.debug("调试信息")      # 灰色，级别低于当前设置时不输出
log.info("普通信息")       # 绿色
log.warn("警告信息")       # 黄色
log.error("错误信息")      # 红色
log.usage("用法说明")      # 蓝色，始终输出，不受 LOG_LEVEL 限制
```

### 2.3 输出格式示例

```
[INFO ] 2024-01-15 14:30:00 - 普通信息
[WARN ] 2024-01-15 14:30:00 - 警告信息
[ERROR] 2024-01-15 14:30:00 - 错误信息
```

---

## 3. pip - 包管理工具

按优先级依次尝试多个 PyPI 镜像站点安装 Python 包，国内网络环境下自动切换镜像源，提高安装成功率。

默认镜像优先级：清华 > 阿里云 > 中科大 > PyPI 官方。

### 3.1 Python 命令管理

```python
from baibao.base import pip

# 获取当前 Python 命令（默认为当前解释器）
python_cmd = pip.get_python_command()

# 修改 Python 命令路径
pip.set_python_command("python3")
pip.set_python_command("D:\\Python39\\python.exe")
```

### 3.2 安装包

```python
from baibao.base import pip

# 安装单个包
success, msg = pip.install("requests")
print(success, msg)  # True, 安装信息

# 安装指定版本
success, msg = pip.install("requests==2.31.0")

# 批量安装
results = pip.install(["numpy", "pandas", "matplotlib"])
# results: (成功列表, 失败列表)
```

### 3.3 升级包

```python
from baibao.base import pip

# 升级单个包
success, msg = pip.upgrade("requests")

# 批量升级
success_list, fail_list = pip.upgrade(["numpy", "pandas"])
```

### 3.4 卸载包

```python
from baibao.base import pip

# 卸载单个包
success, msg = pip.uninstall("requests")

# 批量卸载
success_list, fail_list = pip.uninstall(["numpy", "pandas"])
```

### 3.5 自定义镜像源

```python
from baibao.base import pip

# 使用自定义镜像源
success, msg = pip.install(
    "requests",
    mirrors=["https://pypi.tuna.tsinghua.edu.cn/simple/"],
    timeout=60
)
```

### 3.6 执行任意 pip 命令

```python
from baibao.base import pip

# 执行 pip list
success, msg = pip.execute("list")

# 执行 pip show
success, msg = pip.execute("show", ["requests"])

# 执行 pip freeze
success, msg = pip.execute("freeze")
```

---

## 4. time - 时间模块

提供日期时间相关的工具方法，支持多种格式自动识别和转换。

### 4.1 解析时间字符串

自动识别多种日期时间格式，返回 `datetime` 对象。

```python
from baibao.base import time

# 解析标准格式
dt = time.parse("2024-01-15 14:30:00")

# 解析 ISO 8601 格式
dt = time.parse("2024-01-15T14:30:00Z")

# 解析中文格式
dt = time.parse("2024年01月15日 14时30分00秒")

# 解析英文格式
dt = time.parse("January 15, 2024 14:30:00")

# 解析失败返回 None
dt = time.parse("invalid date")
```

### 4.2 解析日期和时间

```python
from baibao.base import time

# 提取日期部分
d = time.parse_date("2024-01-15 14:30:00")  # 返回 date 对象

# 提取时间部分
t = time.parse_time("2024-01-15 14:30:00")  # 返回 time 对象
```

### 4.3 格式化时间对象

```python
from baibao.base import time
from datetime import datetime, date

# 格式化 datetime 对象
dt = datetime.now()
result = time.format(dt)  # 默认格式: "%Y-%m-%d %H:%M:%S"
result = time.format(dt, fmt="%Y/%m/%d %H:%M")

# 格式化 date 对象
d = date.today()
result = time.format(d, fmt="%Y年%m月%d日")

# 格式化 None 返回 None
result = time.format(None)  # None
```

### 4.4 解析并格式化字符串

```python
from baibao.base import time

# 解析后按指定格式输出
result = time.format_str("2024-01-15 14:30:00", fmt="%Y/%m/%d")
# 输出: "2024/01/15"

result = time.format_str("January 15, 2024", fmt="%Y-%m-%d")
# 输出: "2024-01-15"
```

### 4.5 管理时间格式

```python
from baibao.base import time

# 获取所有支持的格式
formats = time.get_formats()

# 添加自定义格式
time.add_format("%Y年%m月%d日")

# 删除格式
time.remove_format("%Y年%m月%d日")

# 获取格式解析统计
stats = time.get_format_stats()

# 重置统计
time.reset_format_stats()

# 根据使用频率重新排序格式（提高解析效率）
time.reorder_formats()
```

### 4.6 支持的格式示例

| 类型 | 格式示例 |
|------|----------|
| ISO 8601 | `2024-01-15T14:30:00Z` |
| 标准格式 | `2024-01-15 14:30:00` |
| 中文格式 | `2024年01月15日 14时30分00秒` |
| 英文格式 | `January 15, 2024 14:30:00` |
| 美式格式 | `01/15/2024 02:30:00 PM` |
| 紧凑格式 | `20240115143000` |

---

## 5. validate - 验证模块

提供通用的数据验证方法，适用于 dataclass 等数据结构。

### 5.1 检查 dataclass 必填字段

检查数据字典是否包含构造 dataclass 所需的必填字段。

```python
from dataclasses import dataclass
from baibao.base import validate

@dataclass
class UserConfig:
    name: str
    email: str
    age: int = 0

# 自动检测必填字段（name, email）
data = {"name": "张三"}
try:
    validate.check_dataclass_required_fields(data, UserConfig)
except ValueError as e:
    print(e)  # "UserConfig 缺少字段: email"

# 手动指定必填字段
data = {"name": "张三", "email": "test@example.com"}
validate.check_dataclass_required_fields(data, UserConfig, required_fields=["name"])
```

### 5.2 检查字段非空

检查对象的必填字段是否有值（非 None、非空字符串）。

```python
from baibao.base import validate

class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

user = User("张三", "")

try:
    validate.check_required_fields_not_empty(user, ["name", "email"])
except ValueError as e:
    print(e)  # "User 字段 'email' 不能为空"

# 自定义错误提示上下文
try:
    validate.check_required_fields_not_empty(user, ["email"], context="用户信息")
except ValueError as e:
    print(e)  # "用户信息 字段 'email' 不能为空"
```

---

## 6. env - 环境模块

提供环境和包管理相关的工具函数。

### 6.1 获取 Python 解释器路径

```python
from baibao.base import env

# 获取当前 Python 解释器的可执行文件路径
python_exe = env.get_python_executable()
print(python_exe)  # "D:\\Python39\\python.exe"
```

### 6.2 获取模块名

```python
from baibao.base import env

# 获取当前模块的顶级包名
module_name = env.get_current_module_name()

# 获取调用者的顶级包名（跳过 baibao 内部调用）
caller_name = env.get_caller_module_name()
```

### 6.3 获取包版本号

```python
from baibao.base import env

# 获取指定包的版本号
version = env.get_package_version("requests")
print(version)  # "2.31.0"

# 包未安装时抛出 PackageNotFoundError
```

---

## 7. cli - 命令模块

提供可扩展的命令系统，支持命令注册、查找、执行和帮助信息生成。

### 7.1 核心组件

| 组件 | 说明 |
|------|------|
| `Command` | 命令抽象基类，所有命令需继承此类 |
| `HelpCommand` | 帮助命令默认实现 |
| `CommandService` | 命令注册、查找和执行服务 |
| `CommandNotFoundError` | 命令未找到异常 |

### 7.2 定义自定义命令

```python
from baibao.base import Command, CommandService

class GreetCommand(Command):
    @property
    def name(self) -> str:
        return "--greet"

    @property
    def abbr(self) -> str:
        return "-g"

    @property
    def description(self) -> str:
        return "打招呼"

    @property
    def usage(self) -> str:
        return "--greet [名字]"

    def execute(self, args: list[str]) -> str:
        name = args[0] if args else "World"
        return f"Hello, {name}!"

# 注册命令
service = CommandService()
service.register(GreetCommand())
```

### 7.3 执行命令

```python
from baibao.base import CommandService, CommandNotFoundError

service = CommandService()
# ... 注册命令 ...

# 通过名称执行
result = service.execute_command("--greet", ["Alice"])

# 通过缩写执行
result = service.execute_command("-g", ["Bob"])

# 命令不存在时抛出 CommandNotFoundError
try:
    service.execute_command("--unknown", [])
except CommandNotFoundError as e:
    print(e)  # "未知命令: --unknown"
```

### 7.4 查询命令

```python
# 获取单个命令
cmd = service.get_command("--greet")

# 获取所有命令（包括帮助命令）
all_cmds = service.get_all_commands()

# 获取帮助命令实例
help_cmd = service.get_help_command()
```

### 7.5 管理命令

```python
# 取消注册命令
service.unregister("--greet")

# 清空所有命令
service.clear()

# 设置自定义帮助命令
service.set_help_command(MyHelpCommand(service))
```

### 7.6 帮助命令

`CommandService` 自动内置 `help` / `h` 命令。

```python
# 查看所有命令
service.execute_command("help", [])

# 查看单个命令的帮助
service.execute_command("help", ["--greet"])
```

---

## 综合示例

### 示例 1：配置加载与验证

```python
from dataclasses import dataclass
from baibao.base import util, validate

@dataclass
class DatabaseConfig:
    host: str
    port: int
    username: str
    password: str
    database: str

# 从 JSON 加载配置
config = util.load_dataclass_from_json_file("db_config.json", DatabaseConfig)

# 额外验证：检查字段非空
validate.check_required_fields_not_empty(
    config,
    ["host", "username", "password", "database"],
    context="数据库配置"
)
```

### 示例 2：动态导入并处理时间

```python
from baibao.base import util, time

# 动态导入 pandas
pd = util.import_module("pandas")

# 解析时间字符串
date_str = "2024年01月15日"
dt = time.parse(date_str)

# 转换为 pandas Timestamp
timestamp = pd.Timestamp(dt)
print(timestamp)
```

### 示例 3：日志记录工具使用

```python
from baibao.base import log, pip

log.info("开始安装依赖包")

packages = ["requests", "numpy", "pandas"]
success_list, fail_list = pip.install(packages)

log.info(f"成功安装 {len(success_list)} 个包")

if fail_list:
    log.warn(f"以下包安装失败:")
    for fail in fail_list:
        log.error(f"  - {fail}")
else:
    log.info("所有包安装成功")
```

### 示例 4：构建可扩展的命令行工具

```python
from baibao.base import Command, CommandService, log

class VersionCommand(Command):
    @property
    def name(self) -> str:
        return "--version"

    @property
    def description(self) -> str:
        return "显示版本信息"

    def execute(self, args: list[str]) -> str:
        from baibao.base import env
        return f"my-tool 1.0.0 (Python {env.get_package_version('baibao')})"

service = CommandService()
service.register(VersionCommand())

# 执行命令
result = service.execute_command("--version", [])
print(result)
```
