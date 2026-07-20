"""
数据处理包，提供模板渲染、货币格式化等数据操作功能。

包含模板引擎（支持 Jinja2 等多种实现）、货币处理和元数据定义等子模块，
为数据展示和报告生成提供统一的处理能力。
"""

from baibao.data import currency
from baibao.data import template
from baibao.data.template import TemplateEngine, Jinja2Engine
from baibao.data.meta import Style, Field


__all__ = [
    'currency', 'template',
    'TemplateEngine', 'Jinja2Engine',
    'Style', 'Field',
]
