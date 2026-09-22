"""
工作事项服务的 MySQL 实现（基于 baibao 的 rdb_mgr）。

做法对标 :mod:`baibao.task.plan.mysql_service`，核心要点：

  - **仅支持 MySQL**（方言守卫同 plan_task）：占位符固定 ``%s``；
  - **幂等初始化**——:meth:`setup` 用 ``CREATE TABLE IF NOT EXISTS`` 建
    ``work_*`` 三张表（列定义见 :mod:`.schema` 单一信息源）；
  - **事务化复合操作**——create_item / add_stage / set_stage_status /
    delete_item 等经 ``rdb_mgr.get_connection()`` 裸连接 + 显式 ``commit/rollback``
    在同一事务内完成；单语句走 ``rdb_mgr.query/execute``；
  - **INSERT 回填 id**——走裸连接读 ``cursor.lastrowid``；
  - **留痕 append-only**——``work_event`` 只有 INSERT 与查询，不提供任何
    update/delete 路径；状态流转自动追加 ``stage_move``/``item_change`` 事件；
  - **JSON 文本列**（participants/refs）以 ``ensure_ascii=False`` 序列化写入，
    读取侧容错反序列化。

使用者不限于 AI：任何脚本/人均可经 CLI 或直接读本包操作（自动化测试
登记异常、流水线执行留痕、纯 CLI 人工事项管理等场景同 plan_task）。
"""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, cast

from pykunlun.util import logutil

from baibao.db.rdb import rdb_mgr

from .schema import TABLES, ddl

log = logutil.getLogger(__name__)

#: 事项状态
ITEM_STATUSES = ('todo', 'doing', 'blocked', 'done', 'cancelled')
#: 事项终态
ITEM_TERMINAL_STATUSES = ('done', 'cancelled')
#: 阶段状态
STAGE_STATUSES = ('pending', 'doing', 'done', 'skipped')
#: 阶段终态（视同完成，不阻塞链推进）
STAGE_TERMINAL_STATUSES = ('done', 'skipped')
#: 留痕事件类型（手动 log 常用 discuss/decision/note/artifact/handoff）
EVENT_TYPES = ('created', 'note', 'discuss', 'decision', 'artifact',
               'handoff', 'stage_move', 'item_change')
#: 事件级别
EVENT_LEVELS = ('info', 'warn', 'error')
#: 事项字段更新白名单（update_item 仅接受这些键）
UPDATABLE_ITEM_FIELDS = ('title', 'summary', 'background', 'status', 'priority',
                         'due_date', 'owner', 'participants', 'recall_keywords', 'refs')
#: 外部索引的 kind 合法值
REF_KINDS = ('file', 'report', 'diff', 'url', 'pt_task', 'zentao', 'memory', 'other')


def _jdump(obj: Any) -> str | None:
    """对象 → JSON 字符串（ensure_ascii=False；None 直通），供 JSON 文本列落库。"""
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False, default=str)


def _jload(text: Any) -> Any:
    """JSON 字符串 → 对象，容错：非字符串/解析失败返回 None（列值可能被人工改过）。"""
    if text is None or text == '':
        return None
    if isinstance(text, (dict, list)):
        return cast(Any, text)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        log.warning("JSON 列解析失败，按 None 处理: %.100s", text)
        return None


class MySqlWorkItemService:
    """
    基于 rdb_mgr 的工作事项服务实现（仅 MySQL）。

    通过指定 rdb 实例名（``db_name``）复用 baibao 已注册的数据库连接；省略时使用
    rdb 的默认实例。建议与 plan_task 同实例部署（如 ``ai_agent``），表名不同域互不
    干扰。

    Args:
        db_name: rdb 实例名；None 用 rdb 默认实例。
    """

    service_type = 'mysql'

    def __init__(self, db_name: str | None = None) -> None:
        self._db_name = db_name
        self._db_type: str | None = None  # 懒加载并缓存

    @property
    def db_name(self) -> str | None:
        return self._db_name

    # region ======== 方言守卫与连接 ========
    def _get_db_type(self) -> str:
        """探测并缓存目标实例的数据库类型标识。"""
        if self._db_type is None:
            self._db_type = rdb_mgr.get_client(self._db_name).db_type
        return self._db_type

    def _require_mysql(self) -> None:
        """方言守卫：本期工作事项仅支持 MySQL，其余方言直接拒绝。"""
        db_type = self._get_db_type()
        if db_type != 'mysql':
            raise NotImplementedError(f"本期工作事项仅支持 MySQL，目标实例为 {db_type}")

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """单语句读（rdb_mgr.query，参数化 %s）。"""
        self._require_mysql()
        return rdb_mgr.query(sql, tuple(params), name=self._db_name)

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """单语句写（rdb_mgr.execute，参数化 %s），返回受影响行数。"""
        self._require_mysql()
        return rdb_mgr.execute(sql, tuple(params), name=self._db_name)

    @contextmanager
    def _tx(self) -> Generator[tuple[Any, Any], None, None]:
        """
        事务：从 rdb 实例借裸连接并建游标，正常退出 commit，异常回滚后重抛。

        池化连接的 ``close()`` 是归还连接池而非真关闭，故复合操作内多次执行共享
        同一事务。yield ``(conn, cur)``。
        """
        self._require_mysql()
        conn = rdb_mgr.get_connection(self._db_name)
        cur = None
        try:
            cur = conn.cursor()
            yield conn, cur
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                log.warning("事务回滚失败", exc_info=True)
            raise
        finally:
            if cur:
                cur.close()
            conn.close()

    @staticmethod
    def _rows(cur: Any) -> list[dict[str, Any]]:
        """裸游标结果 → 行字典列表（依 ``cur.description``，驱动无关）。"""
        if cur.description is None:
            return []
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def _lastrowid(cur: Any) -> int:
        """取 INSERT 回填的主键；lastrowid 为 None 属非预期，直接抛错。"""
        if cur.lastrowid is None:
            raise RuntimeError("INSERT 未返回 lastrowid（非预期，请检查表结构）")
        return int(cur.lastrowid)

    def _event(self, cur: Any, item_id: int, event_type: str, content: str,
               stage_id: int | None = None, ref: str | None = None,
               operator: str | None = None, level: str = 'info') -> None:
        """事务内追加留痕事件（append-only）。类型/级别不合法直接抛错拦住。"""
        if event_type not in EVENT_TYPES:
            raise ValueError(f"非法的 event_type: {event_type!r}（合法值: {EVENT_TYPES}）")
        if level not in EVENT_LEVELS:
            raise ValueError(f"非法的 level: {level!r}（合法值: {EVENT_LEVELS}）")
        cur.execute(
            'INSERT INTO work_event '
            '(item_id, stage_id, event_type, level, content, ref, operator, created_at) '
            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
            (item_id, stage_id, event_type, level, content, ref, operator, datetime.now()))

    def _setup_table(self, cur: Any, table: str) -> None:
        """事务内幂等建单表。"""
        cur.execute(ddl(table))
    # endregion

    # region ======== 初始化 ========
    def setup(self) -> list[str]:
        """幂等建 ``work_*`` 三张表，返回表名列表。"""
        with self._tx() as (_conn, cur):
            for table in TABLES:
                self._setup_table(cur, table)
        return list(TABLES)
    # endregion

    # region ======== 事项 CRUD ========
    def create_item(
        self,
        title: str,
        background: str | None = None,
        item_type: str = 'general',
        status: str = 'todo',
        priority: str = 'normal',
        due_date: date | None = None,
        owner: str | None = None,
        creator: str | None = None,
        participants: list[str] | None = None,
        recall_keywords: str | None = None,
        stages: list[dict[str, Any]] | None = None,
    ) -> int:
        """
        建事项并展开阶段链（同一事务），返回事项 id。

        Args:
            stages: 阶段实例列表 ``[{name, instruction?, owner?}]``；None/空 =
                不建阶段（裸事项，后续 ``stage add`` 补）。
        """
        if status not in ITEM_STATUSES:
            raise ValueError(f"非法的 status: {status!r}（合法值: {ITEM_STATUSES}）")
        now = datetime.now()
        with self._tx() as (_conn, cur):
            cur.execute(
                'INSERT INTO work_item '
                '(title, summary, background, item_type, status, priority, due_date, '
                'owner, creator, participants, recall_keywords, refs, created_at, updated_at) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (title, None, background, item_type, status, priority, due_date,
                 owner, creator, _jdump(participants), recall_keywords, None, now, now))
            item_id = self._lastrowid(cur)
            n_stage = 0
            for seq, st in enumerate(stages or [], start=1):
                n_stage += 1
                cur.execute(
                    'INSERT INTO work_stage '
                    '(item_id, seq, name, status, owner, instruction, created_at, updated_at) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (item_id, seq, st['name'], 'pending',
                     st.get('owner'), st.get('instruction'), now, now))
            parts = f'，参与者 {len(participants)} 人' if participants else ''
            self._event(cur, item_id, 'created',
                        f'事项创建: {title}（type={item_type}, 状态={status}'
                        f'{f'，展开 {n_stage} 个阶段' if n_stage else ''}{parts}）',
                        operator=creator)
        return item_id

    def get_item(self, item_id: int) -> dict[str, Any] | None:
        """取单个事项（participants/refs 已反序列化）；不存在返回 None。"""
        rows = self._query('SELECT * FROM work_item WHERE id = %s', (item_id,))
        return self._item_row(rows[0]) if rows else None

    @staticmethod
    def _item_row(row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        row['participants'] = _jload(row.get('participants')) or []
        row['refs'] = _jload(row.get('refs')) or []
        return row

    def list_items(
        self,
        status: str | None = None,
        owner: str | None = None,
        participant: str | None = None,
        item_type: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        事项看板查询（updated_at 倒序）。

        Args:
            participant: 按参与者名过滤（JSON 文本 LIKE 包含匹配，人名含引号/百分号时可能失准）。
            keyword: 标题/摘要模糊匹配。
        """
        where: list[str] = []
        params: list[Any] = []
        if status is not None:
            where.append('status = %s')
            params.append(status)
        if owner is not None:
            where.append('owner = %s')
            params.append(owner)
        if item_type is not None:
            where.append('item_type = %s')
            params.append(item_type)
        if participant is not None:
            where.append("participants LIKE %s")
            params.append(f'%{json.dumps(participant, ensure_ascii=False)[1:-1]}%')
        if keyword is not None:
            where.append('(title LIKE %s OR summary LIKE %s)')
            params.extend((f'%{keyword}%', f'%{keyword}%'))
        clause = ('WHERE ' + ' AND '.join(where)) if where else ''
        params.append(limit)
        rows = self._query(
            f'SELECT id, title, summary, item_type, status, priority, due_date, owner, '
            f'recall_keywords, created_at, updated_at FROM work_item {clause} '
            f'ORDER BY updated_at DESC, id DESC LIMIT %s', tuple(params))
        return rows

    def update_item(self, item_id: int, fields: dict[str, Any],
                    operator: str | None = None) -> dict[str, Any] | None:
        """
        白名单字段更新；状态变更校验合法性。返回更新后的事项行。

        自动留痕：所改字段及新值记 ``item_change`` 事件（background/refs 等长值
        只记字段名不记内容）。
        """
        bad = set(fields) - set(UPDATABLE_ITEM_FIELDS)
        if bad:
            raise ValueError(f"不可更新字段: {sorted(bad)}（白名单: {UPDATABLE_ITEM_FIELDS}）")
        if 'status' in fields and fields['status'] not in ITEM_STATUSES:
            raise ValueError(f"非法的 status: {fields['status']!r}（合法值: {ITEM_STATUSES}）")
        # JSON 文本列（participants/refs）：调用方传 list/dict，落库前序列化
        sql_fields = dict(fields)
        for col in ('participants', 'refs'):
            if col in sql_fields:
                sql_fields[col] = _jdump(sql_fields[col])
        now = datetime.now()
        with self._tx() as (_conn, cur):
            cur.execute('SELECT * FROM work_item WHERE id = %s FOR UPDATE', (item_id,))
            rows = self._rows(cur)
            if not rows:
                return None
            old = rows[0]
            cols = ', '.join(f'{k} = %s' for k in sql_fields)
            cur.execute(
                f'UPDATE work_item SET {cols}, updated_at = %s WHERE id = %s',
                (*sql_fields.values(), now, item_id))
            old_cmp = dict(old)
            old_cmp['participants'] = _jload(old.get('participants')) or []
            old_cmp['refs'] = _jload(old.get('refs')) or []
            changed = [k for k in fields if fields[k] != old_cmp.get(k)]
            if changed:
                brief = {k: fields[k] for k in changed if k != 'background'}
                self._event(cur, item_id, 'item_change',
                            f'事项更新: {", ".join(changed)} -> {brief}', operator=operator)
            cur.execute('SELECT * FROM work_item WHERE id = %s', (item_id,))
            return self._item_row(self._rows(cur)[0])

    def delete_item(self, item_id: int) -> bool:
        """
        硬删事项及其阶段/留痕（三表同事务）。仅限误建清理——正常收尾用
        ``update --status cancelled``，留痕不删。
        """
        with self._tx() as (_conn, cur):
            cur.execute('DELETE FROM work_stage WHERE item_id = %s', (item_id,))
            cur.execute('DELETE FROM work_event WHERE item_id = %s', (item_id,))
            cur.execute('DELETE FROM work_item WHERE id = %s', (item_id,))
            return cur.rowcount > 0
    # endregion

    # region ======== 阶段（执行链） ========
    def add_stage(self, item_id: int, name: str, instruction: str | None = None,
                  owner: str | None = None, after_seq: int | None = None,
                  operator: str | None = None) -> dict[str, Any]:
        """
        加阶段：``after_seq`` 为空追加链尾（seq=max+1）；否则插入其后、后方顺延重排。

        自动留痕 ``stage_move``（谁、为什么加——reason 由调用方拼进 operator 或
        事后 ``log --type note`` 补充）。
        """
        now = datetime.now()
        with self._tx() as (_conn, cur):
            cur.execute('SELECT id FROM work_item WHERE id = %s', (item_id,))
            if not self._rows(cur):
                raise ValueError(f'事项不存在: {item_id}')
            if after_seq is None:
                cur.execute('SELECT COALESCE(MAX(seq), 0) AS m FROM work_stage '
                            'WHERE item_id = %s', (item_id,))
                seq = int(self._rows(cur)[0]['m']) + 1
                pos = '追加链尾'
            else:
                # 倒序 +1 防唯一键 (item_id, seq) 冲突
                cur.execute('UPDATE work_stage SET seq = seq + 1, updated_at = %s '
                            'WHERE item_id = %s AND seq > %s ORDER BY seq DESC',
                            (now, item_id, after_seq))
                seq = after_seq + 1
                pos = f'插入于阶段 {after_seq} 之后'
            cur.execute(
                'INSERT INTO work_stage '
                '(item_id, seq, name, status, owner, instruction, created_at, updated_at) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (item_id, seq, name, 'pending', owner, instruction, now, now))
            stage_id = self._lastrowid(cur)
            self._event(cur, item_id, 'stage_move', f'加阶段 {seq}. {name}（{pos}）',
                        stage_id=stage_id, operator=operator)
            cur.execute('SELECT * FROM work_stage WHERE id = %s', (stage_id,))
            return self._rows(cur)[0]

    def list_stages(self, item_id: int) -> list[dict[str, Any]]:
        """阶段清单（seq 升序）。"""
        return self._query('SELECT * FROM work_stage WHERE item_id = %s ORDER BY seq',
                           (item_id,))

    def get_stage(self, stage_id: int) -> dict[str, Any] | None:
        rows = self._query('SELECT * FROM work_stage WHERE id = %s', (stage_id,))
        return rows[0] if rows else None

    def set_stage_status(self, stage_id: int, to_status: str,
                         operator: str | None = None) -> dict[str, Any]:
        """
        阶段状态流转（自由流转但全程留痕；终端态可回 pending 重开，修错用）。

        联动规则（自动，各留一条 item_change）：
          - 阶段置 doing 且事项仍 todo → 事项置 doing；
          - 全部阶段终态（done/skipped）且事项非终态 → 事项置 done。
        """
        if to_status not in STAGE_STATUSES:
            raise ValueError(f"非法的阶段状态: {to_status!r}（合法值: {STAGE_STATUSES}）")
        now = datetime.now()
        with self._tx() as (_conn, cur):
            cur.execute('SELECT * FROM work_stage WHERE id = %s FOR UPDATE', (stage_id,))
            rows = self._rows(cur)
            if not rows:
                raise ValueError(f'阶段不存在: {stage_id}')
            stage = rows[0]
            item_id = int(stage['item_id'])
            from_status = str(stage['status'])
            started = stage['started_at'] or (now if to_status == 'doing' else None)
            finished = now if to_status in STAGE_TERMINAL_STATUSES else None
            cur.execute(
                'UPDATE work_stage SET status = %s, started_at = %s, finished_at = %s, '
                'updated_at = %s WHERE id = %s',
                (to_status, started, finished, now, stage_id))
            self._event(cur, item_id, 'stage_move',
                        f'阶段 {stage["seq"]}. {stage["name"]}: {from_status} → {to_status}',
                        stage_id=stage_id, operator=operator)
            # 事项状态联动
            cur.execute('SELECT status FROM work_item WHERE id = %s', (item_id,))
            item_status = str(self._rows(cur)[0]['status'])
            if to_status == 'doing' and item_status == 'todo':
                cur.execute("UPDATE work_item SET status = 'doing', updated_at = %s "
                            'WHERE id = %s', (now, item_id))
                self._event(cur, item_id, 'item_change',
                            '事项状态: todo → doing（阶段开工联动）', operator=operator)
            elif to_status in STAGE_TERMINAL_STATUSES and item_status not in ITEM_TERMINAL_STATUSES:
                cur.execute(
                    'SELECT COUNT(*) AS n FROM work_stage WHERE item_id = %s '
                    "AND status NOT IN ('done', 'skipped')", (item_id,))
                if int(self._rows(cur)[0]['n']) == 0:
                    cur.execute("UPDATE work_item SET status = 'done', updated_at = %s "
                                'WHERE id = %s', (now, item_id))
                    self._event(cur, item_id, 'item_change',
                                '事项状态: → done（全部阶段终态联动）', operator=operator)
            cur.execute('SELECT * FROM work_stage WHERE id = %s', (stage_id,))
            return self._rows(cur)[0]

    def update_stage(self, stage_id: int, name: str | None = None,
                     instruction: str | None = None, owner: str | None = None,
                     operator: str | None = None) -> dict[str, Any] | None:
        """改阶段名/指令/负责人（白名单三字段，仅传入者更新）；留痕 item_change。"""
        fields: dict[str, Any] = {}
        if name is not None:
            fields['name'] = name
        if instruction is not None:
            fields['instruction'] = instruction
        if owner is not None:
            fields['owner'] = owner
        if not fields:
            raise ValueError('未指定要更新的字段（--name/--instruction/--owner）')
        now = datetime.now()
        with self._tx() as (_conn, cur):
            cur.execute('SELECT * FROM work_stage WHERE id = %s FOR UPDATE', (stage_id,))
            rows = self._rows(cur)
            if not rows:
                return None
            stage = rows[0]
            cols = ', '.join(f'{k} = %s' for k in fields)
            cur.execute(f'UPDATE work_stage SET {cols}, updated_at = %s WHERE id = %s',
                        (*fields.values(), now, stage_id))
            self._event(cur, int(stage['item_id']), 'item_change',
                        f'阶段 {stage["seq"]}. {stage["name"]} 更新: {sorted(fields)}',
                        stage_id=stage_id, operator=operator)
            cur.execute('SELECT * FROM work_stage WHERE id = %s', (stage_id,))
            return self._rows(cur)[0]
    # endregion

    # region ======== 留痕（append-only）与外部索引 ========
    def add_event(self, item_id: int, event_type: str, content: str,
                  stage_id: int | None = None, ref: str | None = None,
                  operator: str | None = None, level: str = 'info') -> int:
        """追加留痕（独立事务）。这是留痕的唯一写入口，无任何修改/删除路径。"""
        with self._tx() as (_conn, cur):
            cur.execute('INSERT INTO work_event '
                        '(item_id, stage_id, event_type, level, content, ref, operator, created_at) '
                        'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                        (item_id, stage_id, event_type, level, content, ref,
                         operator, datetime.now()))
            return self._lastrowid(cur)

    def list_events(self, item_id: int, limit: int = 100,
                    ascending: bool = False) -> list[dict[str, Any]]:
        """留痕查询（默认最近在前；ascending=True 时时间线正序，复盘友好）。"""
        order = 'ASC' if ascending else 'DESC'
        return self._query(
            f'SELECT * FROM work_event WHERE item_id = %s ORDER BY id {order} LIMIT %s',
            (item_id, limit))

    def add_ref(self, item_id: int, kind: str, ref: str, note: str | None = None,
                operator: str | None = None) -> dict[str, Any] | None:
        """外部索引追加一条 ``{kind, ref, note}``（开放索引：加新 kind 永不改表）。"""
        if kind not in REF_KINDS:
            raise ValueError(f"非法的 kind: {kind!r}（合法值: {REF_KINDS}）")
        with self._tx() as (_conn, cur):
            cur.execute('SELECT refs FROM work_item WHERE id = %s FOR UPDATE', (item_id,))
            rows = self._rows(cur)
            if not rows:
                return None
            refs = _jload(rows[0].get('refs')) or []
            entry = {'kind': kind, 'ref': ref}
            if note:
                entry['note'] = note
            refs.append(entry)
            cur.execute('UPDATE work_item SET refs = %s, updated_at = %s WHERE id = %s',
                        (_jdump(refs), datetime.now(), item_id))
            self._event(cur, item_id, 'artifact',
                        f'挂索引 [{kind}] {ref}' + (f'（{note}）' if note else ''),
                        ref=ref, operator=operator)
            return {'item_id': item_id, 'refs': refs}
    # endregion

    # region ======== 接链包 ========
    def open_item(self, item_id: int, recent_events: int = 10) -> dict[str, Any] | None:
        """
        接链包：新会话/新人接手所需的全部信息，一个 dict。

          - ``item``          事项全字段（background=背景、recall_keywords=记忆检索词）
          - ``stages``        阶段链（seq 升序，含各自 status）
          - ``current_stage`` 当前阶段（第一个 doing；否则第一个 pending；链完成=None）
          - ``recent_events`` 最近 N 条留痕（时间线正序，接手看脉络）

        AI 接力协议：读包 → 按 ``item.recall_keywords`` 查记忆库拉背景 →
        干 ``current_stage`` 的活（instruction 是自包含指令）。
        """
        item = self.get_item(item_id)
        if item is None:
            return None
        stages = self.list_stages(item_id)
        current = next((s for s in stages if s['status'] == 'doing'), None) \
            or next((s for s in stages if s['status'] == 'pending'), None)
        # 最近 N 条：先按 id 倒序取尾，再反转为时间线正序（接手看脉络）
        events = self.list_events(item_id, limit=max(recent_events, 0))
        events.reverse()
        return {'item': item, 'stages': stages, 'current_stage': current,
                'recent_events': events}
    # endregion
