"""
文件操作工具函数
"""

import os
import shutil

from baibao.base import log


def remove_target_dirs(base_dir: str, target_name: str, recursive: bool = False) -> int:
    """删除指定名称的目录
    
    在指定目录中查找并删除匹配名称的目录。支持递归搜索所有子目录。
    
    Args:
        base_dir: 搜索的根目录路径
        target_name: 要删除的目录名（如 __pycache__、build、dist）
        recursive: 是否递归搜索所有子目录中的匹配目录，默认为 False
    
    Returns:
        成功删除的目录数量
    
    Raises:
        FileNotFoundError: 当 base_dir 目录不存在时
        PermissionError: 当没有权限删除目录时
    
    Examples:
        >>> # 删除顶层的 build 目录
        >>> remove_target_dirs("/path/to/project", "build")
        
        >>> # 递归删除所有 __pycache__ 目录
        >>> remove_target_dirs("/path/to/project", "__pycache__", recursive=True)
    """
    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"目录不存在: {base_dir}")
    
    removed = 0
    
    if recursive:
        # 递归遍历所有子目录
        for root, dirs, _ in os.walk(base_dir):
            if target_name in dirs:
                target_path = os.path.join(root, target_name)
                try:
                    shutil.rmtree(target_path)
                    log.info(f"已删除: {target_path}")
                    removed += 1
                except PermissionError as e:
                    log.warn(f"删除失败 (权限不足): {target_path} - {e}")
    else:
        # 只检查顶层目录
        target_path = os.path.join(base_dir, target_name)
        if os.path.isdir(target_path):
            try:
                shutil.rmtree(target_path)
                log.info(f"已删除: {target_path}")
                removed = 1
            except PermissionError as e:
                log.warn(f"删除失败 (权限不足): {target_path} - {e}")
    
    return removed


def remove_suffix_dirs(base_dir: str, suffix: str, recursive: bool = False) -> int:
    """删除匹配后缀的目录
    
    在指定目录中查找并删除以指定后缀结尾的目录。支持递归搜索所有子目录。
    
    Args:
        base_dir: 搜索的根目录路径
        suffix: 目录名后缀（如 .egg-info、.dist-info）
        recursive: 是否递归搜索所有子目录中的匹配目录，默认为 False
    
    Returns:
        成功删除的目录数量
    
    Raises:
        FileNotFoundError: 当 base_dir 目录不存在时
        PermissionError: 当没有权限删除目录时
    
    Examples:
        >>> # 删除顶层的 .egg-info 目录
        >>> remove_suffix_dirs("/path/to/project", ".egg-info")
        
        >>> # 递归删除所有 .dist-info 目录
        >>> remove_suffix_dirs("/path/to/project", ".dist-info", recursive=True)
    """
    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"目录不存在: {base_dir}")
    
    removed = 0
    
    if recursive:
        # 递归遍历所有子目录
        for root, dirs, _ in os.walk(base_dir):
            for dir_name in dirs[:]:  # 使用副本避免修改正在迭代的列表
                if dir_name.endswith(suffix):
                    target_path = os.path.join(root, dir_name)
                    try:
                        shutil.rmtree(target_path)
                        log.info(f"已删除: {target_path}")
                        removed += 1
                    except PermissionError as e:
                        log.warn(f"删除失败 (权限不足): {target_path} - {e}")
    else:
        # 只检查顶层目录
        for entry in os.listdir(base_dir):
            full_path = os.path.join(base_dir, entry)
            if os.path.isdir(full_path) and entry.endswith(suffix):
                try:
                    shutil.rmtree(full_path)
                    log.info(f"已删除: {full_path}")
                    removed += 1
                except PermissionError as e:
                    log.warn(f"删除失败 (权限不足): {full_path} - {e}")
    
    return removed
