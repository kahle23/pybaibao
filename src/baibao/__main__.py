"""
baibao 命令行入口。

使用方式：
    python -m baibao                    查看帮助
    python -m baibao install requests   安装包
"""

import sys
from baibao.base import env, CommandNotFoundError
from baibao.util.commands import command_service


def main():
    # 解析命令行参数
    args = sys.argv[1:]
    # 解析命令
    command_name = args[0].lower() if args else ""
    command_args = args[1:] if args else []
    # 无命令时显示帮助
    if not command_name:
        command_name = command_service.get_help_command().name
    # 执行命令
    try:
        command_service.execute_command(command_name, command_args)
    except CommandNotFoundError as e:
        print(str(e))
        print(f"使用 'python -m {env.get_caller_module_name()} {command_service.get_help_command().name}' 查看可用命令")
        sys.exit(1)


if __name__ == "__main__":
    main()
