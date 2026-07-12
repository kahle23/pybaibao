"""
清理命令 - 删除构建缓存和临时文件
"""

import os
import shutil
from typing import Any, List

from baibao.base import log, Command
from baibao.base.file import remove_target_dirs, remove_suffix_dirs


class PyCleanCommand(Command):
    """清理项目构建缓存"""

    @property
    def name(self) -> str:
        return "py_clean"

    @property
    def description(self) -> str:
        return "清理 build、dist、__pycache__ 等构建缓存"

    @property
    def usage(self) -> str:
        return "python -m baibao py_clean [目录路径]（默认当前目录）"

    def execute(self, args: List[str]) -> Any:
        base_dir = args[0] if args else os.getcwd()

        if not os.path.isdir(base_dir):
            log.error(f"目录不存在: {base_dir}")
            return False

        log.info(f"清理目录: {base_dir}")

        removed = 0
        # 删除 build 和 dist（仅顶层）
        removed += remove_target_dirs(base_dir, "build")
        removed += remove_target_dirs(base_dir, "dist")
        # 删除 *.egg-info
        removed += remove_suffix_dirs(base_dir, ".egg-info")
        # 递归删除 __pycache__
        removed += remove_target_dirs(base_dir, "__pycache__", recursive=True)

        if removed > 0:
            log.info(f"✓ 清理完成，共删除 {removed} 个目录")
        else:
            log.info("没有需要清理的目录")

        return True

