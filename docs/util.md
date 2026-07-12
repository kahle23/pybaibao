# util - 命令行工具模块

提供基于命令模式的 CLI 工具，支持包管理和项目清理等功能。

## 命令列表

| 命令 | 功能 | 用法 |
|------|------|------|
| `pip_install` | 安装 Python 包（自动切换镜像） | `python -m baibao pip_install <包名> [包名2 ...]` |
| `pip_upgrade` | 升级 Python 包 | `python -m baibao pip_upgrade <包名> [包名2 ...]` |
| `py_clean` | 清理构建缓存 | `python -m baibao py_clean [目录路径]` |
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
- `CommandService`：管理命令注册和执行
- 具体命令类：实现具体的命令逻辑

### 扩展命令

要添加自定义命令，只需：

1. 创建继承 `Command` 的类
2. 实现必要的属性和方法
3. 在 `commands/__init__.py` 中注册命令

```python
from baibao.base import Command

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
