"""
邮件模块，支持多配置管理。

适用于需要管理多个邮件服务器配置的场景，通过 ``set_client`` 注册不同邮件服务器，
再通过 ``send_text``、``send_html`` 等方法快速发送邮件。

示例::

    from baibao.message.email import set_client, send_text, send_html
    from baibao.message.email import EmailCfg

    # 添加邮件配置（传入字典）
    set_client("qq", {
        "send_server": "smtp.qq.com",
        "send_port": 465,
        "username": "your_email@qq.com",
        "password": "your_auth_code",
        "sender_name": "我的邮箱",
    })

    # 或者传入 EmailCfg 对象
    cfg = EmailCfg(
        send_server="smtp.qq.com",
        send_port=465,
        username="your_email@qq.com",
        password="your_auth_code",
        sender_name="我的邮箱",
    )
    set_client("qq", cfg)

    # 发送纯文本邮件
    send_text("qq", to="recipient@example.com", subject="测试邮件", content="这是一封测试邮件")

    # 发送 HTML 邮件
    send_html("qq", to="recipient@example.com", subject="HTML 邮件", html_content="<h1>Hello</h1>")

    # 发送带附件的邮件
    send_text(
        config_name="qq",
        to="recipient@example.com",
        subject="带附件的邮件",
        content="请查收附件",
        attachments=["/path/to/file1.pdf", "/path/to/file2.txt"],
    )
"""

from typing import Dict, Optional, Union

from .email_client import EmailCfg, EmailClient, EmailSendResult

__all__ = [
    "EmailCfg",
    "EmailClient",
    "EmailSendResult",
    "set_client",
    "get_client",
    "remove_client",
    "send_text",
    "send_html",
    "send",
]

# 存储不同配置名对应的 EmailClient 实例
_clients: Dict[str, EmailClient] = {}

# 默认配置名
DEFAULT_CFG_NAME = "default"


def get_client(cfg_name: Optional[str] = None) -> EmailClient:
    """
    获取指定配置名对应的 EmailClient 实例

    对于默认配置名，如果尚未设置，会自动从 ./email.config 文件加载配置并初始化客户端。

    Args:
        cfg_name: 邮件配置名，如果不传则使用默认配置名

    Returns:
        EmailClient 实例

    Raises:
        KeyError: 指定的配置名对应的 EmailClient 不存在时抛出
    """
    # 如果未指定配置名，使用默认配置名
    if not cfg_name:
        cfg_name = DEFAULT_CFG_NAME
    # 如果配置名不存在，并且是默认配置名，尝试从 ./email.config 加载配置
    if cfg_name not in _clients:
        if cfg_name == DEFAULT_CFG_NAME:
            try:
                cfg = EmailCfg.load_from_json_cfg("./email.config")
                set_client(cfg_name, cfg)
            except Exception as e:
                raise KeyError(f"自动加载默认配置失败: {e}")
        else:
            raise KeyError(f"未找到配置名 '{cfg_name}' 对应的 EmailClient，请先调用 set_client() 设置")
    # 返回对应的 EmailClient 实例
    return _clients[cfg_name]


def set_client(cfg_name: str, client: Union[EmailClient, EmailCfg, dict]) -> None:
    """
    设置指定配置名对应的 EmailClient 或 EmailCfg

    如果传入 EmailCfg 或 dict，会自动创建 EmailClient 实例。

    Args:
        cfg_name: 邮件配置名
        client: EmailClient 实例、EmailCfg 配置对象或配置字典
    """
    # 如果未指定配置名，使用默认配置名
    if not cfg_name:
        cfg_name = DEFAULT_CFG_NAME
    # 设置对应的 EmailClient 实例
    if isinstance(client, EmailClient):
        _clients[cfg_name] = client
    elif isinstance(client, EmailCfg):
        _clients[cfg_name] = EmailClient(client)
    elif isinstance(client, dict):
        _clients[cfg_name] = EmailClient(EmailCfg(**client))
    else:
        raise TypeError(f"client 必须是 EmailClient、EmailCfg 或 dict 类型，实际类型: {type(client)}")


def remove_client(cfg_name: Optional[str] = None) -> None:
    """
    移除指定配置名对应的 EmailClient

    Args:
        cfg_name: 邮件配置名，如果不传则移除默认配置名
    """
    # 如果未指定配置名，使用默认配置名
    if not cfg_name:
        cfg_name = DEFAULT_CFG_NAME
    # 如果配置名存在，移除对应的 EmailClient 实例
    if cfg_name in _clients:
        del _clients[cfg_name]


def send_text(
    cfg_name: str,
    to: Union[str, list],
    subject: str,
    content: str,
    cc: Optional[Union[str, list]] = None,
    bcc: Optional[Union[str, list]] = None,
    attachments: Optional[list] = None
) -> EmailSendResult:
    """
    快速发送纯文本邮件。

    Args:
        cfg_name: 邮件配置名
        to: 收件人邮箱地址
        subject: 邮件主题
        content: 邮件内容
        cc: 抄送地址，可选
        bcc: 密送地址，可选
        attachments: 附件列表，可选

    Returns:
        EmailSendResult，包含发送结果信息

    Raises:
        KeyError: 指定的配置名不存在时抛出
    """
    return get_client(cfg_name).send(to, subject, content, cc=cc, bcc=bcc, attachments=attachments, is_html=False)


def send_html(
    cfg_name: str,
    to: Union[str, list],
    subject: str,
    html_content: str,
    cc: Optional[Union[str, list]] = None,
    bcc: Optional[Union[str, list]] = None,
    attachments: Optional[list] = None
) -> EmailSendResult:
    """
    快速发送 HTML 邮件。

    Args:
        cfg_name: 邮件配置名
        to: 收件人邮箱地址
        subject: 邮件主题
        html_content: HTML 内容
        cc: 抄送地址，可选
        bcc: 密送地址，可选
        attachments: 附件列表，可选

    Returns:
        EmailSendResult，包含发送结果信息

    Raises:
        KeyError: 指定的配置名不存在时抛出
    """
    return get_client(cfg_name).send(to, subject, html_content, cc=cc, bcc=bcc, attachments=attachments, is_html=True)


def send(
    cfg_name: str,
    to: Union[str, list],
    subject: str,
    content: str,
    cc: Optional[Union[str, list]] = None,
    bcc: Optional[Union[str, list]] = None,
    attachments: Optional[list] = None,
    is_html: bool = False
) -> EmailSendResult:
    """
    通用邮件发送方法。

    Args:
        cfg_name: 邮件配置名
        to: 收件人邮箱地址
        subject: 邮件主题
        content: 邮件内容
        cc: 抄送地址，可选
        bcc: 密送地址，可选
        attachments: 附件列表，可选
        is_html: 是否为 HTML 格式，默认 False

    Returns:
        EmailSendResult，包含发送结果信息

    Raises:
        KeyError: 指定的配置名不存在时抛出
    """
    return get_client(cfg_name).send(
        to, subject, content, cc=cc, bcc=bcc, attachments=attachments, is_html=is_html
    )
