"""
baibao 命令行入口。

使用方式：
    python -m baibao                    查看帮助
    python -m baibao install requests   安装包
"""

from baibao.base import hook
from baibao.util.commands import command_service


def _on_startup():
    print("执行启动钩子")
    print("初始化完成")


def _on_shutdown():
    print("执行关闭钩子")
    print("清理完成")


hook.register(hook.ON_STARTUP, _on_startup)
hook.register(hook.ON_SHUTDOWN, _on_shutdown)



if __name__ == "__main__":
    command_service.main_cli()
