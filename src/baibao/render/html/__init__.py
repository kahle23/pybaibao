"""
HTML 片段构建模块。

提供面向报告场景的 HTML 片段构建能力，包括表格、柱状图、折线图、指标卡片等。
所有输出均经过 HTML 转义以防止 XSS。

包含两个子模块：

  - html_builder: 表格、柱状图、折线图等报告片段构建
  - metric_card: 指标卡片网格渲染
"""

from .html_builder import (
    DEFAULT_BAR_COLOR,
    create_field,
    create_style,
    daily_trend_bar_chart,
    format_value,
    horizontal_single_bar_chart,
    hourly_distribution_bar_chart,
    multi_line_chart,
    table_html,
    topn_multi_bar_chart,
    topn_single_bar_chart,
)
from .metric_card import (
    MetricGroupSpec,
    MetricSpec,
    format_number,
    format_percent,
    render_metric_group,
    render_metric_section,
)

__all__ = [
    'DEFAULT_BAR_COLOR',
    'MetricGroupSpec',
    'MetricSpec',
    'create_field',
    'create_style',
    'daily_trend_bar_chart',
    'format_number',
    'format_percent',
    'format_value',
    'horizontal_single_bar_chart',
    'hourly_distribution_bar_chart',
    'multi_line_chart',
    'render_metric_group',
    'render_metric_section',
    'table_html',
    'topn_multi_bar_chart',
    'topn_single_bar_chart',
]
