"""
work_item 命令 - 工作事项管理（事项 = 待办 + 阶段链 + append-only 留痕）。

基于 :class:`baibao.work.MySqlWorkItemService`。数据库是唯一真相源，AI 会话、
纯脚本、人工 CLI 都是可互换的客户端——新会话接手只需 ``open <item_id>``，
背景/当前阶段/近期留痕一个包带回（"给个 id，自带 prompt 和背景"）。

子命令概览（标准循环：init 首次 → create → open → 干活 → log / stage move → status）：
  - init            幂等建 work_* 三张表
  - create          建事项（按类型模板展开阶段链，--stages-file 可自定义）
  - list            看板查询（按状态/负责人/参与者/类型/关键词过滤）
  - status          事项详情（头 + 阶段链 + 留痕计数 + 外部索引）
  - open            接链包（背景 + 阶段链 + 当前阶段 + 近期留痕，给接手的人/AI）
  - update          白名单字段更新（title/summary/background/status/priority/
                    due_date/owner/participants/keywords/refs）
  - stage add       加阶段（追加链尾或 --after-seq 插入，后方自动顺延重排）
  - stage move      阶段状态流转（事项状态自动联动 + 留痕）
  - stage update    改阶段名/指令/负责人
  - log             记链留痕（append-only；讨论轮/拍板/产物/交接）
  - event list      留痕查询（复盘时间线）
  - ref add         挂外部索引（file/url/pt_task/zentao/memory/...）
  - delete          硬删（仅限误建清理，--yes 守卫；正常收尾用 update --status）

身份与配置（与 plan_task 同款机制）：
  - 配置文件 ``.baibao/work_item.config``（当前目录优先，再用户目录，utf-8-sig 容错），
    只放环境事实键：``rdb_name`` / ``owner``；
  - 环境变量 ``WORK_ITEM_DB`` / ``WORK_ITEM_OWNER`` 覆盖配置文件；
  - ``--operator`` 标志 > ``WORK_ITEM_OWNER`` > 配置 ``owner``，作为 creator/operator
    落痕（标签，不鉴权）；未配置只告警不阻断。

长文本（background/instruction/content）一律提供 ``--xxx-file`` 且支持 "-" 读
stdin——绕开 Windows shell argv 引号剥离与中文编码问题。默认输出省 token：
长字段折叠为 300 字预览，``--full`` 输出全文。
"""

import argparse
import csv
import io
import json
import os
import sys
from datetime import date, datetime
from typing import Any

from pykunlun.cli import CliContext, Command
from pykunlun.util import logutil

from baibao.work import (
    DEFAULT_TEMPLATES,
    EVENT_LEVELS,
    EVENT_TYPES,
    ITEM_STATUSES,
    REF_KINDS,
    STAGE_STATUSES,
    MySqlWorkItemService,
    template_stages,
)

log = logutil.getLogger(__name__)

#: 身份配置文件名
_CONFIG_FILENAMES = ('work_item.config',)

#: 配置缓存（一次进程内复用）
_config_cache: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    """搜索并加载配置文件，返回字典（无则为空 dict）。当前目录 → 用户目录。"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    dirs = [os.getcwd(), os.path.expanduser('~')]
    paths = [os.path.join(d, '.baibao', fn) for d in dirs for fn in _CONFIG_FILENAMES]
    for p in paths:
        try:
            if os.path.isfile(p):
                with open(p, encoding='utf-8-sig') as f:
                    data: dict[str, Any] = json.load(f)
                if isinstance(data, dict):
                    log.debug("加载工作事项配置: %s", p)
                    _config_cache = data
                    return data
        except Exception:
            log.warning("读取工作事项配置失败: %s", p, exc_info=True)
    _config_cache = {}
    return _config_cache


def _read_text_source(path: str | None) -> str | None:
    """从文件或 stdin 读取长文本，绕开命令行 shell 引号转义问题。"""
    if not path:
        return None
    if path == '-':
        return sys.stdin.read()
    with open(path, encoding='utf-8-sig') as f:
        return f.read()


def _parse_csv_list(text: str | None) -> list[str] | None:
    """逗号分隔字符串 → 去空白列表；None/空 → None。"""
    if text is None:
        return None
    items = [x.strip() for x in text.split(',') if x.strip()]
    return items or None


def _parse_date(text: str | None) -> date | None:
    """YYYY-MM-DD → date；None 直通；非法格式抛 ValueError。"""
    if text is None:
        return None
    return datetime.strptime(text, '%Y-%m-%d').date()


class _CustomEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理日期时间类型。"""

    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)


class WorkItemCommand(Command):
    """工作事项命令（事项管理：待办 + 阶段链 + 留痕）。"""

    @property
    def name(self) -> str:
        return 'work_item'

    @property
    def abbr(self) -> str:
        return 'wi'

    @property
    def description(self) -> str:
        return '工作事项管理（建事项/阶段链推进/留痕复盘/接链背景包）'

    @property
    def usage(self) -> str:
        types = '/'.join(DEFAULT_TEMPLATES)
        return (
            "python -m baibao work_item <子命令> [选项]\n"
            "python -m baibao wi <子命令> [选项]        # 缩写\n"
            "\n"
            "标准循环:  init（首次）→ create → (open → 干活 → log / stage move)* → status\n"
            "AI 接力:   新会话 open <item_id> —— 背景+当前阶段+近期留痕一个包带回\n"
            "\n"
            "子命令:\n"
            "  init                                          幂等建 3 张 work_* 表\n"
            "  create  --title [--background|--background-file] [--type T]\n"
            "                [--stages-file F] [--owner --participants --priority\n"
            "                 --due-date --keywords --operator]      建事项（类型模板展开阶段链）\n"
            f"                内置类型模板: {types}\n"
            "  list    [--status --owner --participant --type --keyword --limit]  看板查询\n"
            "  status  <item_id> [--full]                    事项详情（头+阶段链+留痕计数+索引）\n"
            "  open    <item_id> [--events N --full]         接链包（item/stages/current_stage/\n"
            "                                                recent_events；AI 接手所需全部信息）\n"
            "  update  <item_id> [--title --summary --background-file --status --priority\n"
            "                --due-date --owner --participants --keywords --refs-json]\n"
            "                                                白名单字段更新（自动留痕 item_change）\n"
            "  stage add  <item_id> --name [--instruction-file --owner --after-seq N]\n"
            "                                                加阶段（默认链尾；插入后方顺延重排）\n"
            "  stage move <stage_id> --to doing|done|skipped|pending [--operator]\n"
            "                                                阶段流转（事项状态自动联动+留痕）\n"
            "  stage update <stage_id> [--name --instruction-file --owner]  改阶段指令等\n"
            "  log     <item_id> --content|--content-file [--type --stage-id --ref --operator]\n"
            "                                                记链留痕（append-only：讨论/拍板/产物/交接）\n"
            "  event list <item_id> [--limit --asc]          留痕查询（复盘时间线）\n"
            "  ref add <item_id> --kind K --ref R [--note]   挂外部索引（file/report/diff/url/\n"
            "                                                pt_task/zentao/memory/other）\n"
            "  delete  <item_id> --yes                       硬删（仅限误建清理；正常收尾用\n"
            "                                                update --status cancelled 留痕不删）\n"
            "\n"
            "配置: .baibao/work_item.config（只放环境事实键 rdb_name/owner）\n"
            "      环境变量: WORK_ITEM_DB / WORK_ITEM_OWNER\n"
            "身份: --operator 标志（creator/operator 落痕标签）> WORK_ITEM_OWNER > 配置 owner\n"
            "\n"
            "通用选项:\n"
            "  --format FMT  输出格式: json|jsonl|csv|table（默认: jsonl；open 仅 json|jsonl）\n"
            "  -h, --help    显示帮助信息"
        )

    def execute(self, ctx: CliContext) -> Any:
        args = ctx.current_args
        if not args:
            self.show_usage()
            return False

        sub = args[0]
        rest = args[1:]
        try:
            if sub == 'init':
                return self._init(ctx, rest)
            if sub == 'create':
                return self._create(ctx, rest)
            if sub == 'list':
                return self._list(ctx, rest)
            if sub == 'status':
                return self._status(ctx, rest)
            if sub == 'open':
                return self._open(ctx, rest)
            if sub == 'update':
                return self._update(ctx, rest)
            if sub == 'stage':
                return self._stage(ctx, rest)
            if sub == 'log':
                return self._log(ctx, rest)
            if sub == 'event':
                return self._event(ctx, rest)
            if sub == 'ref':
                return self._ref(ctx, rest)
            if sub == 'delete':
                return self._delete(ctx, rest)
            if sub in ('-h', '--help'):
                self.show_usage()
                return True
            log.error(f"未知子命令: {sub}")
            self.show_usage()
            return False
        except Exception as e:
            log.error(f"work_item {sub} 失败: {e}")
            return False

    # region ======== 工具：配置解析与构造 ========
    @staticmethod
    def _build_svc() -> MySqlWorkItemService:
        """构造服务（rdb 实例名走配置，调用方无需关心）。"""
        cfg = _load_config()
        db_name = (os.environ.get('WORK_ITEM_DB') or cfg.get('rdb_name'))
        return MySqlWorkItemService(db_name=db_name)

    @staticmethod
    def _resolve_operator(ns: argparse.Namespace) -> str | None:
        """解析 operator 标签：标志 > WORK_ITEM_OWNER > 配置文件；未配置仅告警。"""
        cfg = _load_config()
        operator = (getattr(ns, 'operator', None)
                    or os.environ.get('WORK_ITEM_OWNER')
                    or cfg.get('owner'))
        if operator is None:
            log.info("未配置 operator（WORK_ITEM_OWNER / work_item.config），留痕将无操作者标签；"
                     "多人共用库建议配置以便追溯")
        return operator

    def _emit(self, ctx: CliContext, rows: list[dict[str, Any]], fmt: str) -> None:
        ctx.print_delim()
        self._format_result(rows, fmt)
        ctx.print_delim()

    def _emit_one(self, ctx: CliContext, row: dict[str, Any], fmt: str) -> None:
        """输出单个对象（非列表，如接链包）为一段 JSON（jsonl 单行省 token）。"""
        ctx.print_delim()
        if fmt == 'jsonl':
            print(json.dumps(row, ensure_ascii=False, cls=_CustomEncoder))
        else:
            print(json.dumps(row, ensure_ascii=False, indent=2, cls=_CustomEncoder))
        ctx.print_delim()

    def _format_result(self, rows: list[dict[str, Any]], fmt: str) -> None:
        if not rows:
            log.info("结果为空")
            return
        if fmt == 'json':
            print(json.dumps(rows, ensure_ascii=False, indent=2, cls=_CustomEncoder))
        elif fmt == 'csv':
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            print(output.getvalue(), end='')
        elif fmt == 'table':
            self._print_table(rows)
        else:  # jsonl
            for row in rows:
                print(json.dumps(row, ensure_ascii=False, cls=_CustomEncoder))

    @staticmethod
    def _print_table(rows: list[dict[str, Any]]) -> None:
        columns = list(rows[0].keys())
        widths = {c: max(len(str(c)), max(len(str(r.get(c, ''))) for r in rows)) for c in columns}
        header = ' | '.join(str(c).ljust(widths[c]) for c in columns)
        print(header)
        print('-' * len(header))
        for r in rows:
            print(' | '.join(str(r.get(c, '')).ljust(widths[c]) for c in columns))
        print(f"\n共 {len(rows)} 条记录")

    @staticmethod
    def _apply_snippet(rows: list[dict[str, Any]], limit: int,
                       fields: tuple[str, ...]) -> list[dict[str, Any]]:
        """对 rows 的指定长字段做预览截断（省 AI 上下文）。"""
        for r in rows:
            for fld in fields:
                v = r.get(fld)
                if not isinstance(v, str):
                    continue
                full_len = len(v)
                preview = ' '.join(v[:limit].split())
                if full_len > limit:
                    preview = f'{preview}…（+{full_len - limit} 字，--full 看全文）'
                r[fld] = preview
        return rows
    # endregion

    # region ======== 子命令实现 ========
    def _init(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item init')
        parser.parse_args(args)
        tables = self._build_svc().setup()
        ctx.print_delim()
        print(f"工作事项库已就绪（{len(tables)} 张 work_* 表，service=mysql）")
        ctx.print_delim()
        return True

    def _create(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item create')
        parser.add_argument('--title', required=True, help='事项标题')
        bg_group = parser.add_mutually_exclusive_group(required=False)
        bg_group.add_argument('--background', default=None,
                              help='背景全文（markdown；与 --background-file 二选一）')
        bg_group.add_argument('--background-file', dest='background_file', default=None,
                              help='从 UTF-8 文件读取背景；"-" 读 stdin（长中文推荐走文件）')
        parser.add_argument('--type', default='general', dest='item_type',
                            help=f'事项类型（决定默认阶段模板；内置: {"/".join(DEFAULT_TEMPLATES)}；'
                                 f'未知类型回退 general，或用 --stages-file 自定义）')
        stages_group = parser.add_mutually_exclusive_group(required=False)
        stages_group.add_argument('--stages-file', dest='stages_file', default=None,
                                  help='自定义阶段 JSON 数组文件（[{"name","instruction?","owner?"}]，'
                                       '"-" 读 stdin）；覆盖类型模板')
        stages_group.add_argument('--no-stages', action='store_true', dest='no_stages',
                                  help='不建阶段（裸事项，后续 stage add 补）')
        parser.add_argument('--owner', default=None, help='负责人（人名）')
        parser.add_argument('--participants', default=None,
                            help='参与者（逗号分隔人名）')
        parser.add_argument('--priority', default='normal',
                            choices=['urgent', 'high', 'normal', 'low'],
                            help='优先级（默认 normal）')
        parser.add_argument('--due-date', default=None, dest='due_date',
                            help='截止日期 YYYY-MM-DD')
        parser.add_argument('--keywords', default=None,
                            help='记忆库 recall 关键词（逗号分隔；AI 接链时按此查背景）')
        parser.add_argument('--operator', default=None,
                            help='创建者标签（默认: WORK_ITEM_OWNER > 配置 owner）')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        background = ns.background if ns.background is not None \
            else _read_text_source(ns.background_file)
        try:
            due = _parse_date(ns.due_date)
        except ValueError:
            log.error("--due-date 须为 YYYY-MM-DD 格式")
            return False

        stages: list[dict[str, Any]] | None = None
        if ns.stages_file is not None:
            text = _read_text_source(ns.stages_file)
            try:
                raw = json.loads(text or 'null')
            except json.JSONDecodeError as e:
                log.error("stages JSON 解析失败: %s", e)
                return False
            if not isinstance(raw, list) or not raw or \
                    any(not isinstance(s, dict) or not s.get('name') for s in raw):
                log.error("stages 须为非空 JSON 数组且每个元素含 name")
                return False
            stages = raw
        elif ns.no_stages:
            stages = None
        else:
            stages = [{'name': n} for n in template_stages(ns.item_type)]
            if ns.item_type not in DEFAULT_TEMPLATES:
                log.info("未知类型 %r 无内置模板，已按 general 兜底展开（自定义请用 --stages-file）",
                         ns.item_type)

        operator = self._resolve_operator(ns)
        item_id = self._build_svc().create_item(
            title=ns.title, background=background, item_type=ns.item_type,
            priority=ns.priority, due_date=due, owner=ns.owner, creator=operator,
            participants=_parse_csv_list(ns.participants),
            recall_keywords=ns.keywords, stages=stages)
        log.info("事项已创建 id=%s (title=%s, type=%s, 阶段 %d 个, creator=%s)",
                 item_id, ns.title, ns.item_type, len(stages or []), operator)
        created = self._build_svc().get_item(item_id)
        if created is not None:
            self._emit(ctx, self._apply_snippet([created], 300, ('background',)), ns.format)
        return True

    def _list(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item list')
        parser.add_argument('--status', default=None,
                            help=f'限定事项状态（{"/".join(ITEM_STATUSES)}）')
        parser.add_argument('--owner', default=None, help='限定负责人')
        parser.add_argument('--participant', default=None, help='限定参与者（人名）')
        parser.add_argument('--type', default=None, dest='item_type', help='限定事项类型')
        parser.add_argument('--keyword', default=None, help='标题/摘要模糊匹配')
        parser.add_argument('--limit', type=int, default=50, help='最多返回条数（默认 50）')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        rows = self._build_svc().list_items(
            status=ns.status, owner=ns.owner, participant=ns.participant,
            item_type=ns.item_type, keyword=ns.keyword, limit=ns.limit)
        log.info("共 %d 个事项（status=%s, owner=%s, type=%s）", len(rows), ns.status,
                 ns.owner, ns.item_type)
        self._emit(ctx, rows, ns.format)
        return True

    def _status(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item status')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        parser.add_argument('--snippet', type=int, default=300,
                            help='长字段预览字数（默认 300）；--full 时忽略')
        parser.add_argument('--full', action='store_true', help='不截断，输出全文')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        svc = self._build_svc()
        item = svc.get_item(ns.item_id)
        if item is None:
            log.error("事项不存在: id=%s（用 list 查看现有事项）", ns.item_id)
            return False
        stages = svc.list_stages(ns.item_id)
        counts: dict[str, int] = {}
        for s in stages:
            counts[s['status']] = counts.get(s['status'], 0) + 1
        overview = dict(item)
        overview.update({
            'stage_total': len(stages),
            'stage_done': counts.get('done', 0) + counts.get('skipped', 0),
            'stage_doing': counts.get('doing', 0),
            'stage_pending': counts.get('pending', 0),
            'ref_count': len(item.get('refs') or []),
        })
        if not ns.full:
            self._apply_snippet([overview], ns.snippet, ('background',))
        self._emit(ctx, [overview], ns.format)
        if stages:
            rows = stages if ns.full else self._apply_snippet(
                [dict(s) for s in stages], ns.snippet, ('instruction',))
            self._emit(ctx, rows, ns.format)
        log.info("留痕时间线用 event list %s 查看（--asc 正序复盘）", ns.item_id)
        return True

    def _open(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item open')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        parser.add_argument('--events', type=int, default=10,
                            help='携带最近留痕条数（默认 10）')
        parser.add_argument('--snippet', type=int, default=300,
                            help='长字段预览字数（默认 300）；--full 时忽略')
        parser.add_argument('--full', action='store_true', help='不截断，输出全文')
        parser.add_argument('--format', dest='format', choices=['json', 'jsonl'],
                            default='jsonl', help='接链包输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        package = self._build_svc().open_item(ns.item_id, recent_events=ns.events)
        if package is None:
            log.error("事项不存在: id=%s（用 list 查看现有事项）", ns.item_id)
            return False
        if not ns.full:
            self._apply_snippet([package['item']], ns.snippet, ('background',))
            self._apply_snippet([dict(s) for s in package['stages']], ns.snippet,
                                ('instruction',))
            self._apply_snippet([dict(e) for e in package['recent_events']], ns.snippet,
                                ('content',))
        cur = package.get('current_stage')
        log.info("接链包就绪（事项 %s，阶段 %d 个，当前: %s，留痕 %d 条）；"
                 "接力协议：按 item.recall_keywords 查记忆库背景 → 干 current_stage 的活",
                 package['item']['id'], len(package['stages']),
                 f"{cur['seq']}. {cur['name']}" if cur else '（链已完成）',
                 len(package['recent_events']))
        self._emit_one(ctx, package, ns.format)
        return True

    def _update(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item update')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        parser.add_argument('--title', default=None, help='事项标题')
        parser.add_argument('--summary', default=None, help='一句话摘要')
        bg_group = parser.add_mutually_exclusive_group(required=False)
        bg_group.add_argument('--background', default=None, help='背景全文')
        bg_group.add_argument('--background-file', dest='background_file', default=None,
                              help='从 UTF-8 文件读取背景；"-" 读 stdin')
        parser.add_argument('--status', default=None, choices=list(ITEM_STATUSES),
                            help=f'事项状态（{" / ".join(ITEM_STATUSES)}）')
        parser.add_argument('--priority', default=None,
                            choices=['urgent', 'high', 'normal', 'low'])
        parser.add_argument('--due-date', default=None, dest='due_date',
                            help='截止日期 YYYY-MM-DD（空串清除）')
        parser.add_argument('--owner', default=None, help='负责人')
        parser.add_argument('--participants', default=None, help='参与者（逗号分隔，整体替换）')
        parser.add_argument('--keywords', default=None,
                            help='记忆库 recall 关键词（逗号分隔，整体替换）')
        parser.add_argument('--refs-json', default=None, dest='refs_json',
                            help='外部索引 JSON 数组（[{kind,ref,note}]，整体替换；追加用 ref add）')
        parser.add_argument('--operator', default=None, help='操作者标签')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        fields: dict[str, Any] = {}
        if ns.title is not None:
            fields['title'] = ns.title
        if ns.summary is not None:
            fields['summary'] = ns.summary
        background = ns.background if ns.background is not None \
            else _read_text_source(ns.background_file)
        if background is not None:
            fields['background'] = background
        if ns.status is not None:
            fields['status'] = ns.status
        if ns.priority is not None:
            fields['priority'] = ns.priority
        if ns.due_date is not None:
            try:
                fields['due_date'] = _parse_date(ns.due_date) if ns.due_date != '' else None
            except ValueError:
                log.error("--due-date 须为 YYYY-MM-DD 格式（空串清除）")
                return False
        if ns.owner is not None:
            fields['owner'] = ns.owner
        if ns.participants is not None:
            fields['participants'] = _parse_csv_list(ns.participants) or []
        if ns.keywords is not None:
            fields['recall_keywords'] = ns.keywords or None
        if ns.refs_json is not None:
            try:
                refs = json.loads(ns.refs_json)
            except json.JSONDecodeError as e:
                log.error("--refs-json 解析失败: %s", e)
                return False
            if not isinstance(refs, list):
                log.error("--refs-json 须为 JSON 数组")
                return False
            fields['refs'] = refs
        if not fields:
            log.error("未指定任何要更新的字段")
            return False

        operator = self._resolve_operator(ns)
        updated = self._build_svc().update_item(ns.item_id, fields, operator=operator)
        if updated is None:
            log.error("事项不存在: id=%s", ns.item_id)
            return False
        log.info("事项 %s 已更新（字段: %s）", ns.item_id, ', '.join(fields))
        self._emit(ctx, self._apply_snippet([updated], 300, ('background',)), ns.format)
        return True

    def _stage(self, ctx: CliContext, args: list[str]) -> bool:
        if not args:
            log.error("stage 需要二级子命令: add | move | update")
            return False
        sub, rest = args[0], args[1:]
        if sub == 'add':
            return self._stage_add(ctx, rest)
        if sub == 'move':
            return self._stage_move(ctx, rest)
        if sub == 'update':
            return self._stage_update(ctx, rest)
        log.error(f"未知二级子命令: stage {sub}")
        return False

    def _stage_add(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item stage add')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        parser.add_argument('--name', required=True, help='阶段名')
        instr_group = parser.add_mutually_exclusive_group(required=False)
        instr_group.add_argument('--instruction', default=None,
                                 help='该阶段工作指令（自包含 prompt；与 --instruction-file 二选一）')
        instr_group.add_argument('--instruction-file', dest='instruction_file', default=None,
                                 help='从 UTF-8 文件读取指令；"-" 读 stdin')
        parser.add_argument('--owner', default=None, help='该阶段负责人')
        parser.add_argument('--after-seq', type=int, default=None, dest='after_seq',
                            help='插入到该 seq 的阶段之后（缺省=追加链尾）；后方自动顺延重排')
        parser.add_argument('--operator', default=None, help='操作者标签')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        instruction = ns.instruction if ns.instruction is not None \
            else _read_text_source(ns.instruction_file)
        operator = self._resolve_operator(ns)
        try:
            stage = self._build_svc().add_stage(
                ns.item_id, ns.name, instruction=instruction, owner=ns.owner,
                after_seq=ns.after_seq, operator=operator)
        except ValueError as e:
            log.error("%s", e)
            return False
        log.info("阶段已添加 id=%s (item=%s, seq=%s, name=%s)",
                 stage['id'], ns.item_id, stage['seq'], ns.name)
        self._emit(ctx, self._apply_snippet([stage], 300, ('instruction',)), ns.format)
        return True

    def _stage_move(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item stage move')
        parser.add_argument('stage_id', type=int, help='目标阶段 id（status 查看）')
        parser.add_argument('--to', required=True, dest='to_status',
                            choices=list(STAGE_STATUSES),
                            help=f'目标状态（{" / ".join(STAGE_STATUSES)}）')
        parser.add_argument('--operator', default=None, help='操作者标签')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        operator = self._resolve_operator(ns)
        try:
            stage = self._build_svc().set_stage_status(
                ns.stage_id, ns.to_status, operator=operator)
        except ValueError as e:
            log.error("%s", e)
            return False
        log.info("阶段 %s「%s」已流转 → %s", stage['seq'], stage['name'], ns.to_status)
        self._emit(ctx, [stage], ns.format)
        return True

    def _stage_update(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item stage update')
        parser.add_argument('stage_id', type=int, help='目标阶段 id')
        parser.add_argument('--name', default=None, help='阶段名')
        instr_group = parser.add_mutually_exclusive_group(required=False)
        instr_group.add_argument('--instruction', default=None, help='阶段工作指令')
        instr_group.add_argument('--instruction-file', dest='instruction_file', default=None,
                                 help='从 UTF-8 文件读取指令；"-" 读 stdin')
        parser.add_argument('--owner', default=None, help='该阶段负责人')
        parser.add_argument('--operator', default=None, help='操作者标签')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args)

        instruction = ns.instruction if ns.instruction is not None \
            else _read_text_source(ns.instruction_file)
        operator = self._resolve_operator(ns)
        try:
            stage = self._build_svc().update_stage(
                ns.stage_id, name=ns.name, instruction=instruction, owner=ns.owner,
                operator=operator)
        except ValueError as e:
            log.error("%s", e)
            return False
        if stage is None:
            log.error("阶段不存在: id=%s", ns.stage_id)
            return False
        log.info("阶段 %s 已更新", ns.stage_id)
        self._emit(ctx, self._apply_snippet([stage], 300, ('instruction',)), ns.format)
        return True

    def _log(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item log')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        content_group = parser.add_mutually_exclusive_group(required=True)
        content_group.add_argument('--content', default=None,
                                   help='留痕正文（markdown；与 --content-file 二选一）')
        content_group.add_argument('--content-file', dest='content_file', default=None,
                                   help='从 UTF-8 文件读取正文；"-" 读 stdin（长中文推荐）')
        parser.add_argument('--type', default='note', dest='event_type',
                            choices=[t for t in EVENT_TYPES
                                     if t not in ('created', 'stage_move', 'item_change')],
                            help='留痕类型（默认 note：讨论轮用 discuss、拍板用 decision、'
                                 '产物用 artifact、交接用 handoff）')
        parser.add_argument('--stage-id', type=int, default=None, dest='stage_id',
                            help='关联阶段 id（可空=事项级留痕）')
        parser.add_argument('--ref', default=None, help='关联引用（产物路径/记忆条目/外链）')
        parser.add_argument('--operator', default=None, help='操作者标签（人名或 AI 会话标识）')
        parser.add_argument('--level', default='info', choices=list(EVENT_LEVELS),
                            help='级别（默认 info）')
        ns = parser.parse_args(args)

        content = ns.content if ns.content is not None else _read_text_source(ns.content_file)
        assert content is not None
        operator = self._resolve_operator(ns)
        event_id = self._build_svc().add_event(
            ns.item_id, ns.event_type, content, stage_id=ns.stage_id, ref=ns.ref,
            operator=operator, level=ns.level)
        log.info("留痕已追加 id=%s (item=%s, type=%s, operator=%s)——append-only，不可改写",
                 event_id, ns.item_id, ns.event_type, operator)
        return True

    def _event(self, ctx: CliContext, args: list[str]) -> bool:
        if not args or args[0] != 'list':
            log.error("event 需要二级子命令: list")
            return False
        parser = argparse.ArgumentParser(prog='python -m baibao work_item event list')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        parser.add_argument('--limit', type=int, default=100,
                            help='返回条数（默认 100）')
        parser.add_argument('--asc', action='store_true',
                            help='时间线正序（复盘从头看；默认最近在前）')
        parser.add_argument('--snippet', type=int, default=300,
                            help='content 预览字数（默认 300）')
        parser.add_argument('--full', action='store_true', help='不截断，输出全文')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args[1:])

        rows = self._build_svc().list_events(ns.item_id, limit=ns.limit, ascending=ns.asc)
        if not ns.full:
            self._apply_snippet(rows, ns.snippet, ('content',))
        log.info("共 %d 条留痕（item=%s，%s）", len(rows), ns.item_id,
                 '正序' if ns.asc else '最近在前')
        self._emit(ctx, rows, ns.format)
        return True

    def _ref(self, ctx: CliContext, args: list[str]) -> bool:
        if not args or args[0] != 'add':
            log.error("ref 需要二级子命令: add（查询用 status/open 的 refs 字段）")
            return False
        parser = argparse.ArgumentParser(prog='python -m baibao work_item ref add')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        parser.add_argument('--kind', required=True, choices=list(REF_KINDS),
                            help=f'索引类型（{" / ".join(REF_KINDS)}）')
        parser.add_argument('--ref', required=True, help='索引值（路径/URL/id 等）')
        parser.add_argument('--note', default=None, help='备注')
        parser.add_argument('--operator', default=None, help='操作者标签')
        parser.add_argument('--format', dest='format',
                            choices=['json', 'jsonl', 'csv', 'table'], default='jsonl',
                            help='输出格式（默认: jsonl）')
        ns = parser.parse_args(args[1:])

        operator = self._resolve_operator(ns)
        try:
            result = self._build_svc().add_ref(ns.item_id, ns.kind, ns.ref,
                                               note=ns.note, operator=operator)
        except ValueError as e:
            log.error("%s", e)
            return False
        if result is None:
            log.error("事项不存在: id=%s", ns.item_id)
            return False
        log.info("索引已挂载 (item=%s, [%s] %s)——共 %d 条", ns.item_id, ns.kind,
                 ns.ref, len(result['refs']))
        self._emit(ctx, [result], ns.format)
        return True

    def _delete(self, ctx: CliContext, args: list[str]) -> bool:
        parser = argparse.ArgumentParser(prog='python -m baibao work_item delete')
        parser.add_argument('item_id', type=int, help='目标事项 id')
        parser.add_argument('--yes', action='store_true', required=True,
                            help='确认硬删（事项+阶段+留痕一并删除，不可恢复；'
                                 '正常收尾请用 update --status cancelled 留痕不删）')
        ns = parser.parse_args(args)

        ok = self._build_svc().delete_item(ns.item_id)
        log.info("delete %s -> %s", ns.item_id, '已硬删（三表相关行）' if ok
                 else '未命中（事项不存在）')
        return ok
    # endregion
