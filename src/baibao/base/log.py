"""
日志模块

提供简单的、带级别和时间的日志输出功能。

支持的日志级别（从低到高）：
- DEBUG: 调试信息
- INFO:  普通信息
- WARN:  警告信息
- ERROR: 错误信息
- USAGE: 用途/用法信息（特殊：始终打印，不受 LOG_LEVEL 限制）
"""

from datetime import datetime


# 日志级别颜色映射
_LOG_COLORS = {
    "DEBUG": "\033[90m",  # 灰色
    "INFO" : "\033[92m",  # 绿色
    "WARN" : "\033[93m",  # 黄色
    "ERROR": "\033[91m",  # 红色
    "USAGE": "\033[94m",  # 蓝色
    "RESET": "\033[0m",   # 重置颜色
}

# 日志级别优先级，数值越大优先级越高
_LEVEL_PRIORITY = {
    "DEBUG": 0,
    "INFO" : 1,
    "WARN" : 2,
    "ERROR": 3,
}

# 当前日志级别，只有级别高于或等于此值的日志才会被输出（USAGE 除外）
_LOG_LEVEL = "INFO"


def get_log_level():
    """
    获取当前全局日志级别。

    Returns:
        当前日志级别字符串，如 "DEBUG"、"INFO"、"WARN"、"ERROR"。
    """
    return _LOG_LEVEL


def set_log_level(level):
    """
    设置全局日志级别。

    Args:
        level: 日志级别字符串，可选值为 "DEBUG"、"INFO"、"WARN"、"ERROR"。
    """
    global _LOG_LEVEL
    level = level.upper().strip()
    if level in _LEVEL_PRIORITY:
        _LOG_LEVEL = level
    else:
        print(f"无效的日志级别: {level}，有效值为 DEBUG/INFO/WARN/ERROR")


def _log(level, msg):
    """内部日志输出函数。

    根据当前 _LOG_LEVEL 决定是否输出日志。
    USAGE 级别特殊，不受 _LOG_LEVEL 限制，始终输出。
    打印时将级别名补齐到5字符宽度，保证输出对齐。
    """
    if level == "USAGE" or _LEVEL_PRIORITY.get(level, 0) >= _LEVEL_PRIORITY.get(_LOG_LEVEL, 1):
        color = _LOG_COLORS.get(level, _LOG_COLORS["RESET"])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"{color}[{level.ljust(5)}]{_LOG_COLORS['RESET']} {timestamp} - {msg}"
        )


def debug(msg):
    """
    输出调试级别日志（仅在 _LOG_LEVEL 为 DEBUG 时显示）
    """
    _log("DEBUG", msg)


def info(msg):
    """
    输出信息级别日志（默认级别及以上显示）
    """
    _log("INFO", msg)


def warn(msg):
    """输出警告级别日志"""
    _log("WARN", msg)


def error(msg):
    """
    输出错误级别日志
    """
    _log("ERROR", msg)


def usage(msg):
    """
    输出用途/用法级别日志（始终显示，不受 _LOG_LEVEL 限制）
    """
    _log("USAGE", msg)

