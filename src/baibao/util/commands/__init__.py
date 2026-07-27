"""
命令模块，实现命令模式架构。

每个命令都是一个独立的模块，继承自 Command 基类，
通过 CommandService 注册和管理所有命令。
"""

from baibao.base import CommandService
from baibao.util.commands.help_command import BaibaoHelpCommand
from baibao.util.commands.kbase_command import KbaseInitCommand
from baibao.util.commands.path_command import PythonPathSetupCommand
from baibao.util.commands.pip_command import PipInstallCommand, PipUpgradeCommand
from baibao.util.commands.pypr_command import PyCleanCommand

__all__ = ['command_service']

# 创建全局命令服务实例
command_service = CommandService()

# 注册自定义帮助命令
command_service.set_help_command(BaibaoHelpCommand(command_service))

# 执行注册（HelpCommand 已在 CommandService 初始化时自动注册）
command_service.register(PipInstallCommand())
command_service.register(PipUpgradeCommand())
command_service.register(PyCleanCommand())
command_service.register(KbaseInitCommand())
command_service.register(PythonPathSetupCommand())
