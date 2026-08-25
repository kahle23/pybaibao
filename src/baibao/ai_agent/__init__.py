"""
AI Agent 能力模块（baibao 侧实现）。

承载自治 agent 的组成件，与 :mod:`pykunlun.ai_agent`（抽象层）对应：
本包提供基于 baibao 基础设施的具体实现与模块级实例。

当前包含：
  - 记忆（:mod:`baibao.ai_agent.memory`：基于 rdb_mgr 的 ``RdbMemoryStore``）
  - 长任务（:mod:`baibao.ai_agent.long_task`：基于 rdb_mgr 的 ``MySqlLongTaskService``）

后续可扩展技能管理等。
"""

from . import long_task, memory
from .long_task import MySqlLongTaskService, task_mgr
from .memory import RdbMemoryStore, memory_mgr

__all__ = ['MySqlLongTaskService', 'RdbMemoryStore', 'long_task', 'memory', 'memory_mgr',
           'task_mgr']
