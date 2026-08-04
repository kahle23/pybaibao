"""
BaiBao 命令行入口。

使用方式：
    python -m baibao                       查看帮助
    python -m baibao pip_install requests  安装 Python 包
"""

from baibao.cli import command_manager

if __name__ == "__main__":
    # 启动命令管理器。stdout/stderr 编码由框架经 --output-charset 统一处理
    #（未传则沿用运行时默认；遇乱码可由用户自行指定编码）；
    # 如需自定义启动/收尾逻辑，可向 main_cli 传 on_startup/on_shutdown（入参为 CliContext）。
    command_manager.main_cli()
