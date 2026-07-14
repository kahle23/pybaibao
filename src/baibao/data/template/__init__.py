"""模板引擎模块，提供多种模板引擎策略实现。"""

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
