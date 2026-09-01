"""
envutil — 环境变量与配置的小工具。

  - :func:`load_dotenv_if_present` — 可选加载当前目录 ``.env``。fixtures 与 CLI 共用（此前两处各复制了一份相同逻辑）。
  - :func:`normalize_base_url` — 去除 ``base_url`` 末尾斜杠（此前在 api/login_state/fixtures/probe/CLI 共 5 处各自 ``rstrip("/")``）。
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["load_dotenv_if_present", "normalize_base_url"]


def load_dotenv_if_present() -> None:
    """
    可选加载当前目录 ``.env`` 到进程环境。

    python-dotenv 未安装时静默跳过（直接读 os.environ）。
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file)


def normalize_base_url(base_url: str) -> str:
    """
    去除 ``base_url`` 末尾斜杠（拼接路由/登录地址前的统一规范化）。
    """
    return base_url.rstrip("/")
