"""pip 工具，支持多镜像站点自动切换。

按优先级依次尝试多个 PyPI 镜像站点安装 Python 包，
当首选镜像不可用时自动切换到下一个镜像，
提高在国内网络环境下安装包的可靠性和速度。
"""

from typing import Optional, List, Tuple, Union
import subprocess


# 默认镜像站点列表，按优先级从高到低
DEFAULT_MIRRORS: List[str] = [
    'https://pypi.tuna.tsinghua.edu.cn/simple/',     # 清华大学
    'https://mirrors.aliyun.com/pypi/simple/',       # 阿里云
    'https://mirrors.ustc.edu.cn/pypi/web/simple/',  # 中科大
    'https://pypi.org/simple/',                      # 官方
]

# Python 命令，可修改为其他路径，如 'python3' 或 'D:\\Python39\\python.exe'
_PYTHON_COMMAND: str = 'python'


def get_python_command() -> str:
    """获取当前 Python 命令。"""
    return _PYTHON_COMMAND


def set_python_command(command: str) -> None:
    """设置 Python 命令。

    Args:
        command: Python 命令，如 'python3' 或 'D:\\Python39\\python.exe'。
    """
    global _PYTHON_COMMAND
    _PYTHON_COMMAND = command


def _install_single(
    package: str,
    timeout: int = 120,
    mirrors: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """安装单个包，按优先级依次尝试多个镜像站点。

    内部方法，通过 subprocess 执行 pip install 命令。遇到异常时记录错误并尝试下一个镜像。

    Args:
        package: 包名，可包含版本号，如 'requests' 或 'requests==2.31.0'。
        timeout: 每个镜像站点的超时时间（秒），默认 120 秒。
        mirrors: 镜像站点列表，若为 None 则使用默认列表。

    Returns:
        元组 (成功标志, 结果信息)。成功时包含所使用的镜像地址；失败时包含所有镜像站点的错误摘要。
    """
    mirrors = mirrors if mirrors else DEFAULT_MIRRORS
    errors: List[str] = []
    # 按优先级依次尝试每个镜像站点
    for mirror in mirrors:
        try:
            host = mirror.split('//')[1].split('/')[0]
            command = [
                _PYTHON_COMMAND, '-m', 'pip', 'install', package,
                '-i', mirror,
                '--trusted-host', host,
            ]
            # 执行安装命令
            subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
            return (True, f"成功使用镜像 [{mirror}] 安装 {package}")
        except subprocess.CalledProcessError as e:
            errors.append(f"镜像 [{mirror}] 安装失败: {e.stderr.strip()}")
        except subprocess.TimeoutExpired as e:
            errors.append(f"镜像 [{mirror}] 安装超时: {e}")
        except Exception as e:
            errors.append(f"镜像 [{mirror}] 发生异常: {e}")
    # 所有镜像站点都失败
    return (False, "所有镜像站点安装失败:\n" + "\n".join(errors))


def install(
    packages: Union[str, List[str]],
    timeout: int = 120,
    mirrors: Optional[List[str]] = None,
) -> Union[Tuple[bool, str], Tuple[List[str], List[str]]]:
    """安装包，支持单个安装和批量安装，自动尝试多个镜像站点。

    Args:
        packages: 包名（可含版本号）或包名列表。
        timeout: 每个镜像站点的超时时间（秒），默认 120 秒。
        mirrors: 镜像站点列表，若为 None 则使用默认列表。

    Returns:
        - 单个包：元组 (成功标志, 结果信息)
        - 批量包：元组 (成功列表, 失败列表)，失败列表中每项格式为 "包名: 错误信息"
    """
    if isinstance(packages, str):
        return _install_single(packages, timeout, mirrors)
    # 批量安装
    success_list: List[str] = []
    fail_list: List[str] = []
    mirrors = mirrors if mirrors else DEFAULT_MIRRORS
    # 按优先级依次尝试每个镜像站点
    for package in packages:
        success, msg = _install_single(package, timeout, mirrors)
        if success:
            success_list.append(package)
        else:
            fail_list.append(f"{package}: {msg}")
    # 所有包安装完成
    return (success_list, fail_list)

