"""
内容渲染包，提供 HTML 片段构建与模板引擎能力。

包含两个子模块：

  - html: 面向报告场景的 HTML 片段构建（表格、柱状图、折线图、指标卡片）
  - template: 模板引擎（支持 Jinja2 等多种实现）
"""

from baibao.render import html, template
from baibao.render.template import Jinja2Engine, TemplateEngine

__all__ = [
    'Jinja2Engine',
    'TemplateEngine',
    'html',
    'template',
]
