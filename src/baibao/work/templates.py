"""
工作事项内置阶段模板。

每个事项类型一份"标准链骨架"——建事项时按 :data:`DEFAULT_TEMPLATES` 展开
为 ``work_stage`` 实例行（模板只是默认草稿，不是铁笼子：建链后可随时
``stage add`` 增补/``stage update`` 改名，中途加阶段会自动留痕）。

新场景扩展 = 在此追加一个类型条目（或建链时 ``--stages-file`` 一次性自定义），
表结构与命令无需任何改动。
"""

#: 类型 → 默认阶段名列表（顺序即 seq 顺序）
DEFAULT_TEMPLATES: dict[str, list[str]] = {
    # 开发需求：业务沟通 → 文档 → 产品 → 设计 → 实施 → 测试
    'dev': [
        '业务需求沟通',
        '技术需求文档',
        '产品需求与原型',
        '技术设计',
        '实施',
        '测试发版',
    ],
    # 采购/报销类行政事项
    'purchase': [
        '提需求',
        '比价',
        '审批',
        '下单/执行',
        '到货验收',
        '归档',
    ],
    # 客诉/问题处理类事项
    'complaint': [
        '受理',
        '查因',
        '定方案',
        '执行与回访',
        '关闭',
    ],
    # 通用兜底：任何没想好流程的事
    'general': [
        '启动',
        '执行',
        '验收',
        '收尾',
    ],
}

#: 阶段模板取不到时的兜底类型
FALLBACK_TYPE = 'general'


def template_stages(item_type: str | None) -> list[str]:
    """按事项类型取默认阶段名列表；未知类型回退 general 模板。"""
    key = (item_type or FALLBACK_TYPE).strip().lower()
    return list(DEFAULT_TEMPLATES.get(key) or DEFAULT_TEMPLATES[FALLBACK_TYPE])
