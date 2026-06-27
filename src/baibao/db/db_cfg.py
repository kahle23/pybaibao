#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置模块

提供数据库连接所需的配置类定义和配置文件加载功能。
支持从 JSON 配置文件中读取数据库连接参数，并进行必填字段校验。
"""
from dataclasses import dataclass, fields, MISSING
from pathlib import Path
from typing import Any, Union
from baibao.base import log


@dataclass
class DbCfg:
    """
    数据库连接配置类

    封装数据库连接所需的所有参数，支持多种数据库类型。

    Attributes:
        host: 数据库服务器地址
        port: 数据库服务端口
        username: 数据库用户名
        password: 数据库密码
        database: 数据库名称
        db_type: 数据库类型，支持 mysql、postgresql、sqlite，默认为 mysql
        charset: 数据库字符集，默认 utf8mb4（支持完整 Unicode）
    """
    host: str
    port: int
    username: str
    password: str
    database: str
    db_type: str = 'mysql'
    charset: str = 'utf8mb4'

    @staticmethod
    def load_json_config(config_path: Union[str, Path]) -> 'DbCfg':
        """
        从 JSON 文件加载数据库配置

        读取指定路径的 JSON 配置文件，解析并校验必填字段后返回 DbCfg 对象。

        Args:
            config_path: 配置文件路径，可以是字符串或 Path 对象

        Returns:
            DbCfg: 解析后的数据库配置对象

        Raises:
            FileNotFoundError: 配置文件不存在时抛出
            ValueError: 配置文件缺少必填字段时抛出
            json.JSONDecodeError: JSON 格式解析失败时抛出
        """
        # 确保配置文件路径是 Path 对象
        log.info(f"加载数据库配置文件: {config_path}")
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        # 读取 JSON 文件
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg: dict[str, Any] = json.load(f)
        # 利用 dataclass 的 fields 自动校验必填字段
        required = {f.name for f in fields(DbCfg) if f.default is MISSING}
        missing = required - cfg.keys()
        if missing:
            raise ValueError(f"DbCfg 缺少字段: {', '.join(sorted(missing))}")
        # 返回解析后的配置对象
        return DbCfg(**cfg)
