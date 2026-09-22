"""
工作事项 MySQL 表结构定义（单一信息源）。

集中承载 ``work_*`` 三张表的列定义、索引/唯一键与表注释，并提供 DDL 生成
函数 :func:`ddl`——列清单只此一份，建表语句由此生成，避免重复维护
（做法对标 ``baibao.task.plan.schema``）。

三表分工（事项 = 待办的"头" + 阶段链骨架 + append-only 留痕）：

  - ``work_item``   事项头：背景(background)/状态/负责人/参与者/记忆关键词/外部索引
  - ``work_stage``  阶段（执行链骨架）：从模板展开的实例行，可中途增删
  - ``work_event``  留痕：append-only，复盘与 AI 接链的上下文来源
"""

_COLUMNS_ITEM: list[tuple[str, str, str]] = [
    ('id',             'BIGINT AUTO_INCREMENT PRIMARY KEY',     '主键，自增'),
    ('title',          'VARCHAR(255) NOT NULL',                 '事项标题'),
    ('summary',        'VARCHAR(512) DEFAULT NULL',             '一句话摘要（列表展示用；NULL 取 title 代显）'),
    ('background',     'MEDIUMTEXT DEFAULT NULL',               '背景全文（markdown；讨论中不落文档的背景知识落这里）'),
    ('item_type',      "VARCHAR(32) NOT NULL DEFAULT 'general'", '事项类型（dev/purchase/complaint/general/...，决定默认阶段模板）'),
    ('status',         "VARCHAR(16) NOT NULL DEFAULT 'todo'",   'todo/doing/blocked/done/cancelled'),
    ('priority',       "VARCHAR(16) NOT NULL DEFAULT 'normal'", 'urgent/high/normal/low'),
    ('due_date',       'DATE DEFAULT NULL',                     '截止日期；NULL=不限'),
    ('owner',          'VARCHAR(64) DEFAULT NULL',              '负责人（人名字符串，不绑任何系统账号）'),
    ('creator',        'VARCHAR(64) DEFAULT NULL',              '创建者'),
    ('participants',   'TEXT DEFAULT NULL',                     '参与者列表（JSON 数组，人名/会话标识；空=未指定）'),
    ('recall_keywords', 'VARCHAR(255) DEFAULT NULL',            '记忆库 recall 关键词（逗号分隔；AI 接链时先按此查 agent_memory 拿背景）'),
    ('refs',           'TEXT DEFAULT NULL',                     '外部索引（JSON 数组 [{kind,ref,note}]；kind: file/report/diff/url/pt_task/zentao/memory/other）'),
    ('created_at',     'DATETIME NOT NULL',                     '创建时间'),
    ('updated_at',     'DATETIME NOT NULL',                     '更新时间'),
]

_COLUMNS_STAGE: list[tuple[str, str, str]] = [
    ('id',           'BIGINT AUTO_INCREMENT PRIMARY KEY',      '主键，自增'),
    ('item_id',      'BIGINT NOT NULL',                        '所属事项'),
    ('seq',          'INT NOT NULL',                           '阶段顺序，从 1 起，同事项内唯一（插入新阶段时后方顺延重排）'),
    ('name',         'VARCHAR(255) NOT NULL',                  '阶段名（如 业务需求沟通 / 比价 / 测试发版）'),
    ('status',       "VARCHAR(16) NOT NULL DEFAULT 'pending'", 'pending/doing/done/skipped'),
    ('owner',        'VARCHAR(64) DEFAULT NULL',               '该阶段负责人（可与人不同）'),
    ('instruction',  'MEDIUMTEXT DEFAULT NULL',                '该阶段的工作指令（自包含 prompt；AI 接链时随当前阶段带出）'),
    ('started_at',   'DATETIME DEFAULT NULL',                  '首次置 doing 时间'),
    ('finished_at',  'DATETIME DEFAULT NULL',                  '终态（done/skipped）时间'),
    ('created_at',   'DATETIME NOT NULL',                      '创建时间'),
    ('updated_at',   'DATETIME NOT NULL',                      '更新时间'),
]

_COLUMNS_EVENT: list[tuple[str, str, str]] = [
    ('id',         'BIGINT AUTO_INCREMENT PRIMARY KEY',        '主键，自增（单调递增=时间线序）'),
    ('item_id',    'BIGINT NOT NULL',                          '所属事项'),
    ('stage_id',   'BIGINT DEFAULT NULL',                      '关联阶段；NULL=事项级留痕'),
    ('event_type', 'VARCHAR(32) NOT NULL',                     'created/note/discuss/decision/artifact/handoff/stage_move/item_change'),
    ('level',      "VARCHAR(8) NOT NULL DEFAULT 'info'",       'info/warn/error'),
    ('content',    'TEXT NOT NULL',                            '留痕正文（markdown：这轮聊了什么/结论/产物路径）'),
    ('ref',        'VARCHAR(512) DEFAULT NULL',                '关联引用（产物路径/记忆条目/外链，单值）'),
    ('operator',   'VARCHAR(64) DEFAULT NULL',                 '操作者（人名或 AI 会话标识）'),
    ('created_at', 'DATETIME NOT NULL',                        '留痕时间'),
]

#: 表注册表：表名 → (列定义, 索引/唯一键, 表注释)；建表 DDL 由此生成
TABLES: dict[str, tuple[list[tuple[str, str, str]], list[str], str]] = {
    'work_item': (
        _COLUMNS_ITEM,
        [
            'KEY idx_work_item_status (status)',
            'KEY idx_work_item_owner (owner)',
            'KEY idx_work_item_type (item_type)',
            'KEY idx_work_item_updated (updated_at)',
        ],
        '工作事项（头：背景/状态/参与者/外部索引；与 plan_task 的 ai_task_* 同库不同域）',
    ),
    'work_stage': (
        _COLUMNS_STAGE,
        [
            'UNIQUE KEY uk_work_stage_seq (item_id, seq)',
            'KEY idx_work_stage_item (item_id, status)',
        ],
        '工作事项阶段（执行链骨架；模板展开为实例行，可中途增删）',
    ),
    'work_event': (
        _COLUMNS_EVENT,
        [
            'KEY idx_work_event_item (item_id, id)',
            'KEY idx_work_event_stage (stage_id)',
        ],
        '工作事项留痕（append-only，只追加不改写；复盘与 AI 接链的上下文来源）',
    ),
}


def sql_str(s: str) -> str:
    """转 SQL 单引号字符串字面量（``'`` → ``''`` 转义）。"""
    return "'" + s.replace("'", "''") + "'"


def ddl(table: str) -> str:
    """
    生成单表建表语句（MySQL 方言，utf8mb4 + 列/表注释 + 索引内联）。

    Args:
        table: 实际表名（``TABLES`` 的键，本域表名即基名，无前缀拼接）。
    """
    cols, keys, comment = TABLES[table]
    col_lines = [f'    {c[0]} {c[1]} COMMENT {sql_str(c[2])}' for c in cols]
    key_lines = [f'    {k}' for k in keys]
    body = ',\n'.join(col_lines + key_lines)
    return (f'CREATE TABLE IF NOT EXISTS {table} (\n{body}\n) '
            f'CHARACTER SET utf8mb4 COMMENT={sql_str(comment)}')
