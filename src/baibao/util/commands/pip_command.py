"""
pip 命令 - 安装和升级 Python 包
"""

from typing import Any, List
from baibao.base import log, pip, Command


class PipInstallCommand(Command):
    """安装 Python 包"""
    
    @property
    def name(self) -> str:
        return "pip_install"
    
    @property
    def description(self) -> str:
        return "安装 Python 包（自动切换镜像）"
    
    @property
    def usage(self) -> str:
        return "python -m baibao pip_install <包名> [包名2 ...]"
    
    def execute(self, args: List[str]) -> Any:
        if not args:
            log.error("请指定要安装的包名")
            self.show_usage()
            return False
        
        success_count = 0
        for pkg in args:
            log.info(f"正在安装: {pkg}")
            success, msg = pip.install(pkg)
            if success:
                log.info(f"✓ {pkg} 安装成功")
                success_count += 1
            else:
                log.error(f"✗ {pkg} 安装失败: {msg}")
        
        return success_count == len(args)


class PipUpgradeCommand(Command):
    """升级 Python 包"""
    
    @property
    def name(self) -> str:
        return "pip_upgrade"
    
    @property
    def description(self) -> str:
        return "升级 Python 包"
    
    @property
    def usage(self) -> str:
        return "python -m baibao pip_upgrade <包名> [包名2 ...]"
    
    def execute(self, args: List[str]) -> Any:
        if not args:
            log.error("请指定要升级的包名")
            self.show_usage()
            return False
        
        success_count = 0
        for pkg in args:
            log.info(f"正在升级: {pkg}")
            success, msg = pip.upgrade(pkg)
            if success:
                log.info(f"✓ {pkg} 升级成功")
                success_count += 1
            else:
                log.error(f"✗ {pkg} 升级失败: {msg}")
        
        return success_count == len(args)
