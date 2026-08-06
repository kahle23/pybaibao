"""
PostgreSQL 备份/恢复服务 - 使用 pg_dump / psql 工具。

继承 :class:`~pykunlun.db.RdbBackupService`，通过命令行 pg_dump 导出 SQL，
密码经 ``PGPASSWORD`` 环境变量传递（避免出现在命令行参数中）；恢复用 psql
客户端从标准输入读入 SQL 执行。
"""

import os

from pykunlun.db import RdbBackupService, RdbCfg


class PostgresqlBackupService(RdbBackupService):
    """PostgreSQL pg_dump 备份/恢复服务。"""

    db_type = 'postgresql'
    tool_name = 'pg_dump'
    install_hint = '请安装 PostgreSQL 客户端工具: https://www.postgresql.org/download/'

    def _get_env(self, cfg: RdbCfg) -> dict[str, str] | None:
        assert cfg.password
        env = os.environ.copy()
        env['PGPASSWORD'] = cfg.password
        return env

    def _build_dump_command(self, cfg: RdbCfg, tables: list[str] | None = None,
                       schema_only: bool = False) -> list[str]:
        # pg_dump 需完整连接配置；断言兼顾类型窄化与防御
        assert cfg.host and cfg.port and cfg.username and cfg.database
        cmd = [
            'pg_dump',
            f'--host={cfg.host}',
            f'--port={cfg.port}',
            f'--username={cfg.username}',
            f'--dbname={cfg.database}',
            '--no-password',
            '--format=plain',
        ]

        if schema_only:
            cmd.append('--schema-only')

        if tables:
            for table in tables:
                cmd.extend(['--table', table])

        return cmd

    def _build_restore_command(self, cfg: RdbCfg) -> list[str]:
        # 恢复用 psql 客户端从 stdin 读入 SQL；断言兼顾类型窄化与防御
        assert cfg.host and cfg.port and cfg.username and cfg.database
        return [
            'psql',
            f'--host={cfg.host}',
            f'--port={cfg.port}',
            f'--username={cfg.username}',
            f'--dbname={cfg.database}',
            '--no-password',
            '--quiet',
        ]
