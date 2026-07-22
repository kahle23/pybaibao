#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 生成工具模块
================
提供通用的 HTML 片段生成功能。
"""

import datetime
from typing import Any, Callable, Dict, List, Optional
from baibao import Field
from baibao.base.attr import get_attr
from baibao.data.meta import Style
from baibao.data import currency as currency_mod


def create_style(color: str = '', **kwargs) -> Style:
    """
    模板辅助：创建 Style 对象，可传入 Field 控制样式。

    Args:
        color: 颜色值（如 '#4e79a7'、'red'）
        **kwargs: 其他 Style 支持的属性
    """
    return Style(color=color, **kwargs) if color else Style(**kwargs)


def create_field(name: str, display_name: str = '', is_currency: bool = False,
                currency_field: str = '', currency_value: str = '',
                style: Optional[Style] = None) -> Field:
    """
    模板辅助：创建 Field 对象，供 topn_single_bar_chart 等函数使用。

    Args:
        name: 数据键名
        display_name: 显示名称（图例标签），默认同 name
        is_currency: 是否为货币字段
        currency_field: 数据中币种字段名（如 'settle_currency'）
        currency_value: 固定币种值（如 'USD'），与 currency_field 二选一
        style: Style 对象，控制颜色等样式
    """
    return Field(
        name=name,
        display_name=display_name or name,
        is_currency=is_currency,
        currency_field=currency_field or None,
        currency_value=currency_value or None,
        style=style,
    )


def format_value(data: Dict, field: Field) -> str:
    """
    根据 Field 元信息格式化数值（货币或普通数字）。

    支持两种币种指定方式：
    - currency_field: 从 row 中动态读取币种字段获取符号
    - currency_value: 使用固定币种值获取符号

    Args:
        data: 一行数据字典
        field: Field 对象，包含 name/is_currency/currency_field/currency_value 等信息

    Returns:
        格式化后的字符串，如 "¥ 1,234.56" 或 "1,234.56"
    """
    key = get_attr(field, 'name', None)
    value = data.get(key, 0) or 0 if key else 0
    is_currency = get_attr(field, 'is_currency', False)
    cur_field = get_attr(field, 'currency_field', None)
    cur_value = get_attr(field, 'currency_value', None)
    sym = ''
    if cur_field:
        sym = currency_mod.get_symbol_by_code(str(data.get(cur_field, '')), str(data.get(cur_field, ''))) or ''
    elif cur_value:
        sym = currency_mod.get_symbol_by_code(str(cur_value), str(cur_value)) or ''
    if isinstance(value, float):
        return f'{sym} {value:,.2f}' if is_currency else f'{value:,.2f}'
    if isinstance(value, int):
        return f'{sym} {value:,}' if is_currency else f'{value:,}'
    return str(value)


def table_html(
    title: str,
    data_list: List[Dict],
    headers: Optional[Dict[str, Optional[Field]]] = None
) -> str:
    """
    生成表格 HTML。

    功能：
    1. 自动识别单条记录（dict）或多条记录（list）
    2. 无数据时返回空状态提示
    3. 未指定 headers 时自动使用数据的第一行所有键作为列头
    4. 支持货币字段格式化（通过 Field.is_currency / currency_field / currency_value）

    Args:
        title: 表格标题
        data_list: 表格数据行列表或单个字典
        headers: 列头信息字典，键为字段名，值为 Field 对象。
                 Field 可选属性：display_name（列显示名）、is_currency、
                 currency_field（动态币种字段名）、currency_value（固定币种值）

    Returns:
        完整的表格 HTML 字符串，外层包裹 <div class="table-section">
    """
    # 1. 统一 data_list 为列表格式
    if isinstance(data_list, dict):
        data_list = [data_list]
    # 2. 无数据时返回空状态提示
    if not data_list:
        return f'<h3>{title}</h3><p class="empty">暂无数据</p>'
    # 3. 确定列头信息
    if not headers:
        headers = {k: None for k in data_list[0].keys()}
    # 4. 构建表格 HTML 头部（表头）
    html = f'<div class="table-section"><h3>{title}</h3>\n<table class="data-table"><thead><tr>'
    for key, field in headers.items():
        html += f'<th>{get_attr(field, "display_name", key)}</th>'
    html += '</tr></thead><tbody>'
    # 5. 遍历每一行数据，构建表格行
    for row in data_list:
        html += '<tr>'
        # 6. 遍历每一列数据，格式化并添加到表格行
        for key, field in headers.items():
            # 从行数据中获取值
            value = row.get(key, '')
            # 从列头信息中获取是否为货币字段、币种字段名、币种值
            is_currency = get_attr(field, 'is_currency', False)
            cur_field = get_attr(field, 'currency_field', None)
            cur_value = get_attr(field, 'currency_value', None)
            # 从行数据中获取币种符号
            sym = ''
            if cur_field:
                sym = currency_mod.get_symbol_by_code(str(row.get(cur_field, '')), str(row.get(cur_field, ''))) or ''
            elif cur_value:
                sym = currency_mod.get_symbol_by_code(str(cur_value), str(cur_value)) or ''
            # 格式化数值（货币或普通数字）
            if isinstance(value, float):
                value = f'{sym} {value:,.2f}' if is_currency else f'{value:,.2f}'
            elif isinstance(value, int):
                value = f'{sym} {value:,}' if is_currency else f'{value:,}'
            html += f'<td>{value}</td>'
        html += '</tr>'
    # 7. 闭合表格标签并返回
    html += '</tbody></table></div>'
    return html


def topn_single_bar_chart(
    title: str,
    name_field: Field,
    value_field: Field,
    data_list: List[Dict],
) -> str:
    """
    生成 TopN 单柱状图 HTML（水平条形图）。

    按 value_field 数值降序排列，展示排名前 N 的数据项。
    每条记录显示排名标签（TOP1/TOP2...）、名称、进度条和格式化数值。

    Args:
        title: 图表标题
        name_field: 名称字段，Field.name 为数据字典中的键名
        value_field: 数值字段，Field.name 为数据键名，display_name 为图例标签，
                      is_currency/currency_field/currency_value 控制数值格式化
        data_list: 数据列表，每项为包含 name_field 和 value_field 对应键名的字典

    Returns:
        TopN 单柱状图 HTML 字符串，外层包裹 <div class="chart-container">
    """
    if not data_list:
        return f'<h3>{title}</h3><p class="empty">暂无数据</p>'

    name_key = get_attr(name_field, 'name', '') or ''
    value_key = get_attr(value_field, 'name', '') or ''
    value_label = get_attr(value_field, 'display_name', '') or value_key

    max_value = max(r.get(value_key, 0) or 0 for r in data_list) or 1

    html = f'<div class="chart-container"><h3>{title}</h3>'
    html += f'<div class="chart-legend"><span class="legend-item"><span class="legend-color income-color"></span>{value_label}</span></div>'
    html += '<div class="horizontal-chart-wrapper">'

    for idx, data in enumerate(data_list):
        rank = idx + 1
        name = data.get(name_key, '') or f'#{rank}'
        value = data.get(value_key, 0) or 0
        value_w = (value / max_value) * 100

        formatted_value = format_value(data, value_field)

        html += (
            f'<div class="horizontal-bar-row">'
            f'<span class="bar-rank">TOP{rank}</span>'
            f'<span class="bar-name" title="{name}">{name}</span>'
            f'<div class="bar-track-group">'
            f'<div class="bar-track">'
            f'<div class="horizontal-bar income-bar" style="width:{value_w}%"></div>'
            f'</div>'
            f'</div>'
            f'<div class="bar-values">'
            f'<span class="value-item">{formatted_value}</span>'
            f'</div>'
            f'</div>'
        )

    html += '</div></div>'
    return html


def topn_multi_bar_chart(
    title: str,
    name_field: Field,
    value_fields: List[Field],
    data_list: List[Dict],
) -> str:
    """
    生成 TopN 多柱状图 HTML（水平条形图，支持多系列对比）。

    按各 value_fields 数值展示排名前 N 的数据项，每条记录可显示多个系列的柱子。
    支持正负值（取绝对值计算宽度），每个系列独立配色和格式化。

    Args:
        title: 图表标题
        name_field: 名称字段，Field.name 为数据字典中的键名
        value_fields: 数值字段列表，每项为 Field 对象：
            - name: 数据键名
            - display_name: 图例标签
            - style.color: 柱状图颜色（默认 #4472c4）
            - is_currency/currency_field/currency_value: 控制数值格式化
        data_list: 数据列表，每项为包含 name_field 和各 value_field 对应键名的字典

    Returns:
        TopN 多柱状图 HTML 字符串，外层包裹 <div class="chart-container">
    """
    if not data_list:
        return f'<h3>{title}</h3><p class="empty">暂无数据</p>'

    name_key = get_attr(name_field, 'name', '') or ''

    max_values = {}
    for vf in value_fields:
        key = get_attr(vf, 'name', '') or ''
        max_values[key] = max(abs(r.get(key, 0) or 0) for r in data_list) or 1

    html = f'<div class="chart-container"><h3>{title}</h3>'
    html += '<div class="chart-legend">'
    for vf in value_fields:
        key = get_attr(vf, 'name', '') or ''
        label = get_attr(vf, 'display_name', '') or key
        color = (vf.style.color if vf.style else None) or '#4472c4'
        html += f'<span class="legend-item"><span class="legend-color" style="background:{color}"></span>{label}</span>'
    html += '</div>'
    html += '<div class="horizontal-chart-wrapper">'

    for idx, data in enumerate(data_list):
        rank = idx + 1
        name = data.get(name_key, '') or f'#{rank}'

        html += (
            f'<div class="horizontal-bar-row">'
            f'<span class="bar-rank">TOP{rank}</span>'
            f'<span class="bar-name" title="{name}">{name}</span>'
            f'<div class="bar-track-group">'
        )

        formatted_values = []
        for vf in value_fields:
            key = get_attr(vf, 'name', '') or ''
            label = get_attr(vf, 'display_name', '') or key
            color = (vf.style.color if vf.style else None) or '#4472c4'
            value = data.get(key, 0) or 0
            value_w = min((abs(value) / max_values[key]) * 100, 100)
            formatted = format_value(data, vf)
            formatted_values.append(formatted)

            html += (
                f'<div class="bar-track">'
                f'<div class="horizontal-bar" style="width:{value_w}%;background:{color}" '
                f'title="{label}: {formatted}"></div>'
                f'</div>'
            )

        html += '</div><div class="bar-values">'
        for fv in formatted_values:
            html += f'<span class="value-item">{fv}</span>'
        html += '</div></div>'

    html += '</div></div>'
    return html


def multi_line_chart(
    title: str,
    rows: List[Dict],
    value_fields: List[Field],
    x_field: str = 'month_label',
) -> str:
    """
    生成折线图 HTML（纯 SVG 实现，不依赖 JS 库）。

    功能：
    1. 自动计算 Y 轴范围（含 10% 上留白）
    2. 支持多系列折线对比，每系列独立配色
    3. 绘制网格线、坐标轴、X 轴标签
    4. 每个数据点显示圆点标记
    5. 在数据点上方叠加组合标签（显示所有系列的格式化值）
    6. 首列标签自动右移避免与 Y 轴重叠

    Args:
        title: 图表标题
        rows: 数据行列表，每行为一个字典，包含 x_field 键和各 value_fields 对应的键
        value_fields: 数值字段列表，每项为 Field 对象：
            - name: 数据键名
            - display_name: 图例标签
            - style.color: 折线颜色（默认 #4472c4）
            - is_currency/currency_field/currency_value: 控制数值格式化
        x_field: X 轴字段名，默认为 'month_label'

    Returns:
        折线图 HTML 字符串，外层包裹 <div class="chart-container">，内含 <svg> 元素
    """
    if not rows:
        return f'<h3>{title}</h3><p class="empty">暂无数据</p>'

    n = len(rows)
    # SVG dimensions
    W, H = 900, 340
    PAD_L, PAD_R, PAD_T, PAD_B = 90, 40, 30, 50
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B

    # Gather all values to compute Y range
    all_vals = []
    for vf in value_fields:
        key = get_attr(vf, 'name', '') or ''
        for r in rows:
            v = r.get(key, 0) or 0
            all_vals.append(v)
    v_min = min(0, min(all_vals))
    v_max = max(all_vals) if all_vals else 1
    if v_max == v_min:
        v_max = v_min + 1
    # Add 10% headroom
    v_range = v_max - v_min
    v_max += v_range * 0.1
    if v_min < 0:
        v_min -= v_range * 0.05

    def x_pos(i):
        if n == 1:
            return PAD_L + chart_w / 2
        return PAD_L + i * chart_w / (n - 1)

    def y_pos(v):
        return PAD_T + chart_h * (1 - (v - v_min) / (v_max - v_min))

    # Build SVG
    svg = f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">'

    # Grid lines (5 horizontal)
    grid_steps = 5
    for i in range(grid_steps + 1):
        gy = PAD_T + chart_h * i / grid_steps
        gv = v_max - (v_max - v_min) * i / grid_steps
        svg += f'<line x1="{PAD_L}" y1="{gy}" x2="{W - PAD_R}" y2="{gy}" class="line-chart-grid"/>'
        svg += f'<text x="{PAD_L - 8}" y="{gy + 4}" text-anchor="end" class="line-chart-label">{gv:,.2f}</text>'

    # Axes
    svg += f'<line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{H - PAD_B}" class="line-chart-axis"/>'
    svg += f'<line x1="{PAD_L}" y1="{H - PAD_B}" x2="{W - PAD_R}" y2="{H - PAD_B}" class="line-chart-axis"/>'

    # X axis labels
    for i, r in enumerate(rows):
        mx = x_pos(i)
        label = r.get(x_field, '')
        svg += f'<text x="{mx}" y="{H - PAD_B + 20}" class="line-chart-month-label">{label}</text>'

    # Draw lines and dots for each series
    all_points: Dict[int, list] = {}  # x_index -> [(fi, px, py, v, color, formatted)]
    for fi, vf in enumerate(value_fields):
        key = get_attr(vf, 'name', '') or ''
        color = (vf.style.color if vf.style else None) or '#4472c4'

        points = []
        for i, r in enumerate(rows):
            v = r.get(key, 0) or 0
            px, py = x_pos(i), y_pos(v)
            points.append((px, py, v))
            formatted = format_value(r, vf)
            if i not in all_points:
                all_points[i] = []
            all_points[i].append((fi, px, py, v, color, formatted))

        # Area fill (polygon under the line)
        if points:
            area_path = f'M{points[0][0]},{H - PAD_B}'
            for px, py, _ in points:
                area_path += f' L{px},{py}'
            area_path += f' L{points[-1][0]},{H - PAD_B} Z'
            svg += f'<path d="{area_path}" fill="{color}" class="line-chart-area"/>'

        # Line polyline
        polyline_pts = ' '.join(f'{px},{py}' for px, py, _ in points)
        svg += f'<polyline points="{polyline_pts}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'

        # Dots
        for px, py, _ in points:
            svg += f'<circle cx="{px}" cy="{py}" r="4" fill="{color}" class="line-chart-dot"/>'

    # Combined labels: one per x-position showing all series values
    LABEL_LINE_H = 13  # Height per line in combined label
    for x_idx in range(n):
        if x_idx not in all_points:
            continue
        series_data = all_points[x_idx]
        # Find the highest point (smallest y) to position label above it
        min_py = min(d[2] for d in series_data)
        px = series_data[0][1]

        # Build combined label lines (sorted by series order)
        series_data.sort(key=lambda d: d[0])
        lines = []
        for fi, _, py, v, color, formatted in series_data:
            lines.append((color, formatted))

        # Background rect
        rect_h = len(lines) * LABEL_LINE_H + 6
        rect_w = 110
        rect_x = px - rect_w / 2
        rect_y = min_py - rect_h - 8

        # First point: move label to the right to avoid overlapping Y-axis labels
        if x_idx == 0:
            rect_x = px + 8

        # Clamp to top boundary
        if rect_y < PAD_T:
            rect_y = min_py + 12

        svg += f'<rect x="{rect_x}" y="{rect_y}" width="{rect_w}" height="{rect_h}" rx="4" fill="white" stroke="#ddd" stroke-width="0.8" opacity="0.5"/>'
        # Text lines
        for li, (color, txt) in enumerate(lines):
            ty = rect_y + 12 + li * LABEL_LINE_H
            svg += f'<circle cx="{rect_x + 8}" cy="{ty - 3.5}" r="3" fill="{color}"/>'
            svg += f'<text x="{rect_x + 15}" y="{ty}" class="line-chart-value-label" fill="#333">{txt}</text>'

    svg += '</svg>'

    # Assemble HTML
    html = f'<div class="chart-container"><h3>{title}</h3>'
    html += '<div class="chart-legend">'
    for vf in value_fields:
        key = get_attr(vf, 'name', '') or ''
        label = get_attr(vf, 'display_name', '') or key
        color = (vf.style.color if vf.style else None) or '#4472c4'
        html += f'<span class="legend-item"><span class="legend-color" style="background:{color}"></span>{label}</span>'
    html += '</div>'
    html += f'<div class="line-chart-wrapper">{svg}</div></div>'
    return html


def horizontal_single_bar_chart(
    title: str,
    data_list: List[Dict],
    name_field: str,
    value_field: str,
    name_formatter: Optional[Callable[[Dict, str], str]] = None,
    value_formatter: Optional[Callable[[Dict, int], str]] = None,
    extra_fields: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    生成通用水平柱状图 HTML。

    与 topn_single_bar_chart 不同，此函数不排序、不显示排名标签，
    直接按 data_list 顺序渲染，适合自定义排序场景。

    Args:
        title: 图表标题
        data_list: 数据列表，每项为字典
        name_field: 名称字段名（数据字典中的键）
        value_field: 数值字段名（用于计算柱状图宽度比例）
        name_formatter: 名称格式化函数，签名 (row: Dict, name_value: str) -> str
        value_formatter: 数值格式化函数，签名 (row: Dict, value: int) -> str，
                          用于 tooltip 显示
        extra_fields: 额外显示的字段列表，每项为字典：
            - field: 字段名
            - suffix: 后缀（如 '次', '人'）
            - formatter: 可选的格式化函数，签名 (row: Dict, value) -> str

    Returns:
        水平柱状图 HTML 字符串，外层包裹 <div class="chart-container">
    """
    if not data_list:
        return f'<h3>{title}</h3><p class="empty">暂无数据</p>'

    max_n = max(data.get(value_field, 0) or 0 for data in data_list) or 1
    html = f'<div class="chart-container"><h3>{title}</h3><div class="chart-bar-wrapper">'

    for data in data_list:
        name_value = data.get(name_field, '')
        value = data.get(value_field, 0) or 0
        pct = value / max_n * 100

        # 格式化名称
        if name_formatter:
            label = name_formatter(data, name_value)
        else:
            label = str(name_value)

        # 格式化数值（用于 tooltip）
        if value_formatter:
            tooltip_text = value_formatter(data, value)
        else:
            tooltip_text = f'{value:,}'

        # 构建右侧额外显示的字段
        extra_values = []
        if extra_fields:
            for extra in extra_fields:
                field_name = extra.get('field', '')
                suffix = extra.get('suffix', '')
                formatter = extra.get('formatter')
                extra_value = data.get(field_name, 0) or 0
                if formatter:
                    extra_values.append(formatter(data, extra_value))
                else:
                    extra_values.append(f'{extra_value:,}{suffix}')

        # 构建右侧显示文本
        right_text = ' '.join(extra_values) if extra_values else tooltip_text

        html += (
            f'<div class="chart-bar-row">'
            f'<span class="chart-bar-label">{label}</span>'
            f'<div class="chart-bar-track">'
            f'<div class="chart-bar-fill" style="width:{pct}%">'
            f'<span class="chart-bar-tooltip">{tooltip_text}</span>'
            f'</div>'
            f'</div>'
            f'<span class="chart-bar-value">{right_text}</span>'
            f'</div>'
        )

    html += '</div></div>'
    return html


def hourly_distribution_bar_chart(
    title: str,
    data_list: List[Dict],
    hour_field: str = 'hour',
    count_field: str = 'action_count'
) -> str:
    """
    生成时段分布柱状图 HTML。

    将数据按小时分组，展示一天 24 小时内各时段的活跃次数分布。
    内部复用 horizontal_single_bar_chart，自动格式化小时标签（HH:00）和计数（N 次）。

    Args:
        title: 图表标题
        data_list: 数据列表，每项包含 hour 和 action_count 字段
        hour_field: 小时字段名，默认为 'hour'
        count_field: 次数字段名，默认为 'action_count'

    Returns:
        时段分布柱状图 HTML 字符串
    """
    def format_hour(row, value):
        return f'{value:02d}:00'

    def format_count(row, value):
        return f'{value:,} 次'

    return horizontal_single_bar_chart(
        title=title,
        data_list=data_list,
        name_field=hour_field,
        value_field=count_field,
        name_formatter=format_hour,
        value_formatter=format_count,
    )


def daily_trend_bar_chart(rows: List[Dict], chart_title: str = '每日操作趋势') -> str:
    """
    生成每日趋势柱状图 HTML。

    展示每日的操作次数和独立用户数。内部复用 horizontal_single_bar_chart，
    自动格式化日期标签（MM月DD日）、计数（N 次）并额外显示用户数（N 人）。

    Args:
        rows: 数据行列表，每项包含 action_date（YYYY-MM-DD）、
              action_count、user_count 字段
        chart_title: 图表标题，默认为 '每日操作趋势'

    Returns:
        每日趋势柱状图 HTML 字符串
    """
    def format_date(row, value):
        date_str = str(value)[:10]
        try:
            dt = datetime.date.fromisoformat(date_str)
            return f'{dt.month}月{dt.day}日'
        except (ValueError, TypeError):
            return date_str

    def format_count(row, value):
        return f'{value:,} 次'

    return horizontal_single_bar_chart(
        title=chart_title,
        data_list=rows,
        name_field='action_date',
        value_field='action_count',
        name_formatter=format_date,
        value_formatter=format_count,
        extra_fields=[{'field': 'user_count', 'suffix': ' 人'}],
    )




