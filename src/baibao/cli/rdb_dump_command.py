"""
数据库备份命令 - 支持 MySQL、PostgreSQL、SQLite 等数据库转储。
"""

import argparse
import os
from typing import Any

from pykunlun.cli import CliContext, Command
from pykunlun.util import fileutil, logutil

from baibao.db.rdb import RdbCfg, rdb_mgr

log = logutil.getLogger(__name__)


class RdbDumpCommand(Command):
    """
    数据库备份（转储）命令。

    通过适配器工厂获取对应数据库类型的备份适配器执行备份。
    """

    @property
    def name(self) -> str:
        return "rdb_dump"

    @property
    def abbr(self) -> str:
        return "rd"

    @property
    def description(self) -> str:
        return "数据库备份（转储）"

    @property
    def usage(self) -> str:
        supported = ', '.join(rdb_mgr.get_registered_backup_types())
        return (
            f"python -m baibao rdb_dump [选项]  （支持: {supported}）\n"
            "\n"
            "选项:\n"
            "  -c, --config NAME       数据库配置名（默认: default）\n"
            "  -f, --config-file PATH  数据库配置文件路径（默认: ./db.config）\n"
            "  -o, --output DIR        备份输出目录（默认: ./backups）\n"
            "  --tables TABLES         只备份指定的表（逗号分隔）\n"
            "  --schema-only           只备份结构，不备份数据\n"
            "  --no-compress           不压缩备份文件\n"
            "  --verbose               显示详细输出\n"
            "  -h, --help              显示帮助信息"
        )

    def _parse_args(self, args: list[str]) -> argparse.Namespace:
        """解析命令行参数。"""
        parser = argparse.ArgumentParser(
            prog=f'python -m baibao {self.name}',
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            '-c', '--config',
            default='default',
            help='数据库配置名（默认: default）',
        )

        parser.add_argument(
            '-f', '--config-file',
            default='./db.config',
            help='数据库配置文件路径（默认: ./db.config）',
        )

        parser.add_argument(
            '-o', '--output',
            default='./backups',
            help='备份输出目录（默认: ./backups）',
        )

        parser.add_argument(
            '--tables',
            help='只备份指定的表（逗号分隔）',
        )

        parser.add_argument(
            '--schema-only',
            action='store_true',
            help='只备份结构，不备份数据',
        )

        parser.add_argument(
            '--no-compress',
            action='store_true',
            help='不压缩备份文件',
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细输出',
        )

        return parser.parse_args(args)

    def _load_config(self, config_name: str, config_file: str) -> 'RdbCfg | None':
        """加载数据库配置。"""
        import json

        # 从配置文件加载（优先，因为备份通常从配置文件读取）
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # SQLite 仅需 database，其余字段省略即可：各实现的
                # _validate_and_prepare_cfg 会按需校验，无需在此填占位值。
                cfg = RdbCfg(**data)
                # RdbCfg 为纯数据容器不做校验；db_type 推导与必填字段校验/默认值补全
                # 均在构造驱动客户端时由 RdbClient.__init__ / _validate_and_prepare_cfg 触发。
                return cfg
            except Exception as e:
                log.error(f"加载配置文件失败: {e}")
                return None

        # 从已注册的配置中获取
        from baibao.db.rdb import rdb_mgr
        try:
            name = config_name if config_name != 'default' else None
            return rdb_mgr.get_client(name).cfg
        except ValueError:
            pass

        log.error(f"找不到数据库配置: 配置名='{config_name}', 配置文件='{config_file}'")
        return None

    def execute(self, ctx: CliContext) -> Any:
        """执行数据库备份命令。"""
        args = ctx.current_args
        # 解析参数
        try:
            ns = self._parse_args(args)
        except SystemExit:
            return False

        # 加载配置
        cfg = self._load_config(ns.config, ns.config_file)
        if not cfg:
            return False

        if not cfg.db_type or not cfg.database:
            log.error("配置缺少必填项 db_type / database，无法备份")
            return False

        # 创建输出目录
        output_dir = os.path.abspath(ns.output)
        os.makedirs(output_dir, exist_ok=True)

        # 生成备份文件路径
        compress = not ns.no_compress
        ext = 'sql.gz' if compress else 'sql'
        filename = fileutil.timestamped_filename([cfg.db_type, cfg.database], ext)
        output_path = os.path.join(output_dir, filename)

        # 解析表列表
        tables = None
        if ns.tables:
            tables = [t.strip() for t in ns.tables.split(',') if t.strip()]

        # 执行备份
        log.info(f"开始备份数据库: {cfg.db_type}://{cfg.host}:{cfg.port}/{cfg.database}")
        if tables:
            log.info(f"备份表: {', '.join(tables)}")

        try:
            result = rdb_mgr.dump(
                cfg,
                output_path=output_path,
                tables=tables,
                schema_only=ns.schema_only,
                compress=compress,
                verbose=ns.verbose,
            )
        except ValueError as e:
            log.error(str(e))
            return False

        if result.success:
            log.info(f"[OK] {result}")
            return True
        else:
            log.error(f"[FAIL] {result}")
            return False
