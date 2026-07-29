"""
命令模块，实现命令模式架构。

每个命令都是一个独立的模块，继承自 Command 基类，
通过 CommandManager 注册和管理所有命令。
"""

from kunlun import CommandManager

from baibao.util.commands.help_command import BaibaoHelpCommand
from baibao.util.commands.kbase_command import KbaseInitCommand
from baibao.util.commands.path_command import PythonPathSetupCommand
from baibao.util.commands.pip_command import PipInstallCommand, PipUpgradeCommand
from baibao.util.commands.pypr_command import PyCleanCommand

__all__ = ['command_manager']

# 创建全局命令管理器实例
command_manager = CommandManager()

# 注册自定义帮助命令
command_manager.set_help_command(BaibaoHelpCommand(command_manager))

# 执行注册（HelpCommand 已在 CommandManager 初始化时自动注册）
command_manager.register(PipInstallCommand())
command_manager.register(PipUpgradeCommand())
command_manager.register(PyCleanCommand())
command_manager.register(KbaseInitCommand())
command_manager.register(PythonPathSetupCommand())
