"""
baibao 命令行入口。

使用方式：
    python -m baibao                    查看帮助
    python -m baibao install requests   安装包
"""

from baibao.base import action
from baibao.util.commands import command_service


def _on_startup(args):
    print("执行启动动作")
    print(f"入参: {args}")
    print("初始化完成")


def _on_shutdown(args):
    print("执行关闭动作")
    print("清理完成")


action.register(action.APP_ON_STARTUP, _on_startup)
action.register(action.APP_ON_SHUTDOWN, _on_shutdown)



if __name__ == "__main__":
    command_service.main_cli()
