"""
工作事项域（work_item / wi）：事项 = 待办的"头" + 阶段链 + append-only 留痕。

与 ``task/plan``（plan_task）的分工：plan_task 管"AI 执行状态机"（claim/finish/
重试预算），work 管"人与事的全周期"（背景/阶段推进/沟通留痕/外部索引）——
事项进入 AI 干活阶段时经 ``refs`` 挂 pt_task_id 关联，两系统互指一行字。
"""

from .service import (
    EVENT_LEVELS,
    EVENT_TYPES,
    ITEM_STATUSES,
    REF_KINDS,
    STAGE_STATUSES,
    MySqlWorkItemService,
)
from .templates import DEFAULT_TEMPLATES, FALLBACK_TYPE, template_stages

__all__ = [
    'DEFAULT_TEMPLATES',
    'EVENT_LEVELS',
    'EVENT_TYPES',
    'FALLBACK_TYPE',
    'ITEM_STATUSES',
    'REF_KINDS',
    'STAGE_STATUSES',
    'MySqlWorkItemService',
    'template_stages',
]
