"""
Unix-like 平台（Linux、macOS、BSD 等）的环境变量管理实现。

通过向用户 shell 配置文件（如 ``~/.bashrc``、``~/.zshrc``、``~/.profile``）
追加 ``export`` 行实现永久生效的环境变量管理。
"""

import os
from typing import Optional

from baibao.base import env as _env_info
from baibao.base import log
from kunlun.system import SCOPE_SYSTEM, EnvVarService


class UnixEnvService(EnvVarService):
    """
    Unix-like 系统环境变量管理实现。

    依据 ``SHELL`` 环境变量推断当前 shell 配置文件，
    通过追加/过滤 ``export`` 行实现永久生效。

    仅支持用户级（``SCOPE_USER``）环境变量：Unix 下系统级配置需 root 写入
    ``/etc/environment`` 等文件，本实现不涉及；传入 ``scope=SCOPE_SYSTEM (1)`` 将抛出
    ``ValueError``。
    """

    def __init__(self, platform: str = "unix") -> None:
        super().__init__(platform)

    # region ======== 策略接口实现 ========

    def set_var(self, name: str, value: str, scope: Optional[int] = None) -> bool:
        if scope == SCOPE_SYSTEM:
            raise ValueError("Unix 暂不支持系统级环境变量（需 root 写入 /etc/environment）")
        profile_path = _env_info.get_shell_profile_path()
        if not profile_path:
            return False
        # 构建 export 行
        export_line = f'export {name}="{value}"'
        try:
            # 已存在相同配置则跳过写入，仅同步到当前进程
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    if export_line in f.read():
                        os.environ[name] = value
                        return True
            with open(profile_path, "a", encoding="utf-8") as f:
                f.write(f"\n{export_line}\n")
            os.environ[name] = value
            return True
        except (PermissionError, OSError):
            return False

    def append_to_path(self, value: str) -> bool:
        config_file = _env_info.get_shell_profile_path()
        if not config_file:
            return False

        path_line = f'export PATH="$PATH:{value}"'

        # 检查是否已存在
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if value in content and "PATH" in content:
                        log.info("PATH 中已包含 %s", value)
                        return True
            except OSError as e:
                log.error("读取配置文件失败: %s", e)
                return False

        # 追加到配置文件
        try:
            with open(config_file, "a", encoding="utf-8") as f:
                f.write(f"\n# Add to PATH\n{path_line}\n")

            # 同步到当前进程
            os.environ["PATH"] = f"{os.environ.get('PATH', '')}:{value}"

            return True
        except OSError as e:
            log.error("添加到 Unix PATH 时出错: %s", e)
            return False

    def remove_from_path(self, value: str) -> bool:
        config_file = _env_info.get_shell_profile_path()
        if not config_file:
            return False

        # 读取配置文件
        if not os.path.exists(config_file):
            log.info("配置文件不存在: %s", config_file)
            return True

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 过滤掉包含该值的 PATH 相关行
            new_lines = [line for line in lines if not (value in line and "PATH" in line)]

            # 写回配置文件
            with open(config_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            # 同步到当前进程
            path_list = [p for p in os.environ.get("PATH", "").split(":") if p and p != value]
            os.environ["PATH"] = ":".join(path_list)

            return True
        except OSError as e:
            log.error("从 Unix PATH 移除时出错: %s", e)
            return False

    # endregion
