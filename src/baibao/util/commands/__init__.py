"""
命令模块 - 实现命令模式架构

每个命令都是一个独立的模块，继承自 Command 基类。
通过 CommandService 注册和管理所有命令。
"""

from baibao.base import CommandService, HelpCommand

__all__ = ['command_service']


class BaibaoHelpCommand(HelpCommand):
    """Baibao 帮助命令，复写 full_help_text 方法"""

    def full_help_text(self, commands: dict) -> str:
        """生成所有命令的帮助文本，在头部增加 baibao 描述，在尾部增加常用示例

        Args:
            commands: 已注册的命令字典，键为命令名称，值为命令实例

        Returns:
            str: 生成的帮助文本
        """
        # 构建命令列表
        command_lines = []
        for cmd in commands.values():
            command_lines.append(f"    {cmd.name:<12} {cmd.description}")
        # 拼接命令列表
        commands_text = "\n".join(command_lines)
        # 构建帮助文本（头部增加 baibao 描述，尾部增加常用示例）
        return (
            f"BaiBao - 百宝，方便好用的 Python 常用功能库\n\n"
            f"可用命令:\n"
            f"{commands_text}\n\n"
            f"使用 {self.usage} 查看具体命令的详细用法\n\n"
            f"常用示例:\n"
            f"    python -m baibao help install     查看 install 命令的详细用法\n"
            f"    python -m baibao install <包名>   安装指定的 Python 包\n"
            f"    python -m baibao upgrade <包名>   升级指定的 Python 包\n"
        )


# 创建全局命令服务实例
command_service = CommandService()

# 注册自定义帮助命令
command_service.set_help_command(BaibaoHelpCommand(command_service))

# 导入所有命令模块，触发注册
from baibao.util.commands.pip_command import PipInstallCommand, PipUpgradeCommand  # noqa: E402
from baibao.util.commands.pypr_command import PyCleanCommand  # noqa: E402

# 执行注册（HelpCommand 已在 CommandService 初始化时自动注册）
command_service.register(PipInstallCommand())
command_service.register(PipUpgradeCommand())
command_service.register(PyCleanCommand())

