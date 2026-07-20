"""
模板引擎模块，提供多种模板引擎策略实现。

采用策略模式设计，支持通过配置名动态切换引擎实例，
提供统一的模板渲染接口（流、文件、字符串）和线程安全的引擎管理。
"""

from ._template import (
    get_template_engine,
    set_template_engine,
    remove_template_engine,
    render_stream_to_stream,
    render_file_to_file,
    render_string_to_file,
    render_file_to_string,
    render_string_to_string,
    TemplateEngine,
    Jinja2Engine,
)


__all__ = [
    'get_template_engine',
    'set_template_engine',
    'remove_template_engine',
    'render_stream_to_stream',
    'render_file_to_file',
    'render_string_to_file',
    'render_file_to_string',
    'render_string_to_string',
    'TemplateEngine',
    'Jinja2Engine',
]
