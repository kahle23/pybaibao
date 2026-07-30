"""
BaiBao 命令行入口。

使用方式：
    python -m baibao                       查看帮助
    python -m baibao pip_install requests  安装 Python 包
"""

from baibao.cli import command_manager


def _on_startup(args):
    """
    启动钩子：在命令解析与执行之前调用。

    预留的扩展点，默认空实现。需要时可在此完成初始化、参数预处理等；
    若需中断流程，可直接抛出异常。

    Args:
        args: 原始命令行参数列表（sys.argv[1:]）。
    """


def _on_shutdown(args):
    """
    关闭钩子：命令执行完毕后调用（无论成功或失败，在 finally 中执行）。

    预留的扩展点，默认空实现。适合做资源回收、统计输出等收尾工作。
    注意：回调内部不能抛出异常。

    Args:
        args: 原始命令行参数列表（sys.argv[1:]）。
    """


if __name__ == "__main__":
    """
    启动命令管理器，并注入生命周期钩子
    （on_startup 在命令执行前调用，on_shutdown 在执行后调用）
    """
    command_manager.main_cli(on_startup=_on_startup, on_shutdown=_on_shutdown)
