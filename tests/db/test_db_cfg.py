#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_cfg.py 的测试类
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from baibao import DbCfg


class TestDbCfg:
    """DbCfg 数据类测试"""

    def test_db_config_default_values(self):
        config = DbCfg(
            host="localhost",
            port=3306,
            database="test_db",
            username="root",
            password="password"
        )
        assert config.db_type == 'mysql'
        assert config.charset == 'utf8mb4'

    def test_db_config_custom_values(self):
        config = DbCfg(
            db_type="postgresql",
            charset="utf8",
            host="192.168.1.1",
            port=5432,
            username="user",
            password="pass",
            database="mydb"
        )
        assert config.db_type == "postgresql"
        assert config.charset == "utf8"
        assert config.host == "192.168.1.1"
        assert config.port == 5432
        assert config.username == "user"
        assert config.password == "pass"
        assert config.database == "mydb"


class TestLoadDbCfg:
    """load_json_config 方法测试"""

    def test_load_json_config_success(self, tmp_path):
        config_data = {
            "db_type": "mysql",
            "charset": "utf8",
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test_db"
        }
        config_path = tmp_path / "db_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)

        config = DbCfg.load_from_json_cfg(config_path)

        assert config.db_type == "mysql"
        assert config.charset == "utf8"
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.username == "root"
        assert config.password == "password"
        assert config.database == "test_db"

    def test_load_json_config_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            DbCfg.load_from_json_cfg("/nonexistent/path/config.json")

    def test_load_json_config_missing_required_fields(self, tmp_path):
        config_data = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "database": "test_db"
        }
        config_path = tmp_path / "db_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)

        with pytest.raises(ValueError, match="缺少字段"):
            DbCfg.load_from_json_cfg(config_path)
