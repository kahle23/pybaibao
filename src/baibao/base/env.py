"""
环境检测模块，提供运行时环境信息获取功能。

支持获取 Python 解释器路径、当前模块包名、调用者模块名等运行时信息，
常用于日志标记、包管理和环境适配场景。
"""

import inspect
import os
import platform
import subprocess
import sys
from importlib.metadata import version

from baibao.base import log
from typing import Optional


def get_python_executable() -> str:
    """
    获取当前 Python 解释器的可执行文件路径。
    """
    return sys.executable


def get_current_module_name() -> str:
    """
    获取当前模块的顶级包名。
    """
    # 获取当前模块的顶级包名
    # 如果当前模块没有顶级包名，返回空字符串
    return (__package__ or "").split('.')[0]


def get_caller_module_name() -> str:
    """
    获取调用者的顶级包名（跳过baibao内部调用）。
    """
    # 获取当前模块的顶级包名
    current_module = get_current_module_name()
    # 遍历调用栈，找到第一个不是baibao内部调用的模块
    for frame_info in inspect.stack():
        # 获取当前帧的模块名
        module = frame_info.frame.f_globals.get('__package__')
        # 检查是否是baibao内部调用
        if module and not module.startswith(current_module):
            return str(module.split('.')[0])
    # 如果没有找到不是baibao内部调用的模块，返回当前模块的顶级包名
    return current_module


def get_package_version(package_name: str) -> str:
    """
    获取指定包的版本号。

    包未安装时直接抛出 PackageNotFoundError，不做静默回退。
    如果包代码能被执行（如 __init__.py），说明包已加载，
    若 metadata 仍找不到则说明安装有问题，报错有助于定位。

    Args:
        package_name: 包名

    Returns:
        包的版本号

    Raises:
        PackageNotFoundError: 包未安装时抛出
    """
    return version(package_name)


def get_python_home() -> str:
    """
    获取 Python 安装目录。

    Returns:
        Python 安装目录路径。
    """
    return os.path.dirname(sys.executable)


def get_python_bin_dir() -> str:
    """
    获取 Python 可执行文件目录（Scripts/bin 目录）。

    Windows 下为 Scripts 目录，Linux/macOS 下为 bin 目录。

    Returns:
        Python 可执行文件目录路径。
    """
    python_home = get_python_home()
    system = platform.system().lower()
    if system == "windows":
        return os.path.join(python_home, "Scripts")
    else:
        return os.path.join(python_home, "bin")


def get_environment_variable(name: str) -> Optional[str]:
    """
    获取环境变量。

    Args:
        name: 环境变量名称。

    Returns:
        环境变量值，不存在时返回 None。
    """
    return os.environ.get(name)


def set_environment_variable(name: str, value: str) -> bool:
    """
    设置环境变量（永久生效）。

    Windows 下使用 setx 命令，Linux/macOS 下修改 shell 配置文件。

    Args:
        name: 环境变量名称。
        value: 环境变量值。

    Returns:
        设置成功返回 True，失败返回 False。
    """
    system = platform.system().lower()
    if system == "windows":
        return _set_windows_env_var(name, value)
    else:
        return _set_unix_env_var(name, value)


def _set_windows_env_var(name: str, value: str) -> bool:
    """
    设置 Windows 用户环境变量。

    Args:
        name: 环境变量名称。
        value: 环境变量值。

    Returns:
        设置成功返回 True，失败返回 False。
    """
    try:
        result = subprocess.run(
            ["setx", name, value],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            os.environ[name] = value
            return True
        return False
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def _set_unix_env_var(name: str, value: str) -> bool:
    """
    设置 Unix 系统（Linux/macOS）的环境变量。

    Args:
        name: 环境变量名称。
        value: 环境变量值。

    Returns:
        设置成功返回 True，失败返回 False。
    """
    config_file = get_shell_config_file()
    if not config_file:
        return False

    export_line = f'export {name}="{value}"'

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if export_line in f.read():
                    os.environ[name] = value
                    return True
        except OSError:
            return False

    try:
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(f'\n# Python Path\n{export_line}\n')
        os.environ[name] = value
        return True
    except (PermissionError, OSError):
        return False


def get_shell_config_file() -> Optional[str]:
    """
    获取当前用户的 shell 配置文件路径。

    Returns:
        配置文件路径，失败时返回 None。
    """
    try:
        home_dir = os.path.expanduser("~")
        system = platform.system().lower()

        if system == "darwin":
            shell = os.environ.get("SHELL", "/bin/zsh")
            if "zsh" in shell:
                return os.path.join(home_dir, ".zshrc")
            else:
                return os.path.join(home_dir, ".bash_profile")
        else:
            shell = os.environ.get("SHELL", "/bin/bash")
            if "zsh" in shell:
                return os.path.join(home_dir, ".zshrc")
            elif "fish" in shell:
                fish_config_dir = os.path.join(home_dir, ".config", "fish")
                return os.path.join(fish_config_dir, "config.fish")
            else:
                return os.path.join(home_dir, ".bashrc")
    except OSError:
        return None


def add_to_path(var_name: str) -> bool:
    """
    将环境变量引用添加到 PATH（永久生效）。

    Windows 下使用 setx 命令，Linux/macOS 下修改 shell 配置文件。

    Args:
        var_name: 环境变量名称。

    Returns:
        添加成功返回 True，失败返回 False。
    """
    system = platform.system().lower()
    if system == "windows":
        return _add_to_windows_path(var_name)
    else:
        return _add_to_unix_path(var_name)


def _add_to_windows_path(var_name: str) -> bool:
    """
    将环境变量引用添加到 Windows PATH。

    Args:
        var_name: 环境变量名称。

    Returns:
        添加成功返回 True，失败返回 False。
    """
    try:
        result = subprocess.run(
            ["reg", "query", r"HKCU\Environment", "/v", "Path"],
            capture_output=True,
            text=True,
            check=False
        )

        current_path = ""
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Path" in line and "REG_" in line:
                    parts = line.split("    ")
                    if len(parts) >= 3:
                        current_path = parts[2].strip()

        var_ref = f"%{var_name}%"

        if var_ref in current_path:
            log.info("PATH 中已包含 %s", var_ref)
            return True

        if current_path:
            new_path = f"{current_path};{var_ref}"
        else:
            new_path = var_ref

        result = subprocess.run(
            ["setx", "Path", new_path],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            os.environ["PATH"] = f"{os.environ.get('PATH', '')};{var_ref}"
            return True
        else:
            log.error("设置 PATH 失败: %s", result.stderr)
            return False
    except FileNotFoundError:
        log.error("setx 或 reg 命令不可用，请确保在 Windows 系统上运行")
        return False
    except subprocess.SubprocessError as e:
        log.error("添加到 Windows PATH 时出错: %s", e)
        return False


def _add_to_unix_path(var_name: str) -> bool:
    """
    将环境变量引用添加到 Unix PATH。

    Args:
        var_name: 环境变量名称。

    Returns:
        添加成功返回 True，失败返回 False。
    """
    config_file = get_shell_config_file()
    if not config_file:
        return False

    var_ref = f"${{{var_name}}}"
    path_line = f'export PATH="$PATH:{var_ref}"'

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if var_ref in content and "PATH" in content:
                    log.info("PATH 中已包含 %s", var_ref)
                    return True
        except OSError as e:
            log.error("读取配置文件失败: %s", e)
            return False

    try:
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(f'\n# Add {var_name} to PATH\n{path_line}\n')

        var_value = get_environment_variable(var_name)
        if var_value:
            os.environ["PATH"] = f"{os.environ.get('PATH', '')}:{var_value}"

        return True
    except OSError as e:
        log.error("添加到 Unix PATH 时出错: %s", e)
        return False

