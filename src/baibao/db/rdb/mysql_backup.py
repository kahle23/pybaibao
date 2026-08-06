"""
MySQL 备份/恢复服务 - 使用 mysqldump / mysql 工具。

继承 :class:`~pykunlun.db.RdbBackupService`，通过命令行 mysqldump 导出 SQL、
mysql 客户端从标准输入读入 SQL 执行恢复。
"""


from pykunlun.db import RdbBackupService, RdbCfg


class MysqlBackupService(RdbBackupService):
    """MySQL mysqldump 备份/恢复服务。"""

    db_type = 'mysql'
    tool_name = 'mysqldump'
    install_hint = '请安装 MySQL 客户端工具: https://dev.mysql.com/downloads/'

    def _build_dump_command(self, cfg: RdbCfg, tables: list[str] | None = None,
                       schema_only: bool = False) -> list[str]:
        # mysqldump 需完整连接配置；断言兼顾类型窄化与防御
        assert cfg.host and cfg.port and cfg.username and cfg.password and cfg.database
        cmd = [
            'mysqldump',
            f'--host={cfg.host}',
            f'--port={cfg.port}',
            f'--user={cfg.username}',
            f'--password={cfg.password}',
            '--single-transaction',
            '--routines',
            '--triggers',
        ]

        if schema_only:
            cmd.append('--no-data')

        cmd.append(cfg.database)

        if tables:
            cmd.extend(tables)

        return cmd

    def _build_restore_command(self, cfg: RdbCfg) -> list[str]:
        # 恢复用 mysql 客户端从 stdin 读入 SQL；断言兼顾类型窄化与防御
        assert cfg.host and cfg.port and cfg.username and cfg.password and cfg.database
        return [
            'mysql',
            f'--host={cfg.host}',
            f'--port={cfg.port}',
            f'--user={cfg.username}',
            f'--password={cfg.password}',
            cfg.database,
        ]
