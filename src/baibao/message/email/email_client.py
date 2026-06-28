"""
邮件客户端模块，提供邮件发送功能。

支持纯文本邮件、HTML 邮件和带附件的邮件发送，支持 SMTP/SMTPS 协议。
"""
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from email.utils import make_msgid
from pathlib import Path
from typing import Optional, List, Union
import os

from baibao.base import util


@dataclass
class EmailSendResult:
    """邮件发送结果。

    Attributes:
        message_id: 邮件的 Message-ID
        from_addr: 发件人地址
        recipients: 所有收件人地址列表（含抄送、密送）
        failed_recipients: 投递失败的收件人字典，空字典表示全部成功
    """
    message_id: str
    from_addr: str
    recipients: List[str]
    failed_recipients: dict


@dataclass
class EmailCfg:
    """
    邮件服务器配置类

    封装邮件发送和接收所需的所有参数，支持多种协议。

    Attributes:
        send_server: 发送服务地址，如 ``smtp.qq.com``、``smtp.gmail.com``
        username: 发件人邮箱账号
        password: 发件人邮箱密码或授权码
        send_port: 发送服务端口，普通端口为 25，SSL 端口通常为 465
        send_protocol: 发送协议，默认 ``smtp``，当前自动判断加密方式，无需手动设置
        sender_name: 发件人显示名称，默认为邮箱账号

        receive_server: 接收服务地址，如 ``imap.qq.com``、``imap.gmail.com``
        receive_port: 接收服务端口，IMAP 通常为 993，POP3 通常为 995
        receive_protocol: 接收协议，支持 ``imap``、``pop3``，默认 ``imap``
    """
    send_server: str
    username: str
    password: str
    send_port: int = 465
    send_protocol: str = "smtp"
    sender_name: Optional[str] = None

    receive_server: Optional[str] = None
    receive_port: int = 993
    receive_protocol: str = "imap"

    @staticmethod
    def load_from_json_cfg(config_path: Union[str, Path]) -> 'EmailCfg':
        """从 JSON 文件加载邮件服务器配置"""
        return util.load_dataclass_from_json_file(config_path, EmailCfg)


class EmailClient:
    """邮件发送工具类，支持发送纯文本邮件、HTML 邮件和带附件的邮件。

    提供简洁的 API 用于快速发送各种类型的邮件，支持抄送、密送和群发功能。

    示例::

        from baibao.message.email import EmailClient, EmailCfg

        # 1. 配置邮件服务器
        config = EmailCfg(
            send_server="smtp.qq.com",
            send_port=465,
            username="your_email@qq.com",
            password="your_auth_code",
            sender_name="我的邮箱"
        )

        # 2. 创建邮件发送器
        client = EmailClient(config)

        # 3. 发送纯文本邮件
        client.send(
            to="recipient@example.com",
            subject="测试邮件",
            content="这是一封测试邮件"
        )

        # 4. 发送 HTML 邮件
        html_content = (
            '<html>'
            '<body>'
            '<h1>欢迎使用邮件工具</h1>'
            '<p>这是一封 <strong>HTML</strong> 格式的邮件。</p>'
            '</body>'
            '</html>'
        )
        client.send(
            to="recipient@example.com",
            subject="HTML 邮件测试",
            content=html_content,
            is_html=True
        )

        # 5. 发送带附件的邮件
        client.send(
            to="recipient@example.com",
            subject="带附件的邮件",
            content="请查看附件",
            attachments=["report.pdf", "data.xlsx"]
        )

        # 6. 发送给多个收件人（含抄送和密送）
        client.send(
            to=["user1@example.com", "user2@example.com"],
            subject="群发邮件",
            content="Hello Everyone!",
            cc="manager@example.com",
            bcc=["admin1@example.com", "admin2@example.com"]
        )
    """

    def __init__(self, config: EmailCfg) -> None:
        """初始化邮件发送器。

        Args:
            config: 邮件服务器配置对象。
        """
        self._config = config
        self._smtp: Optional[smtplib.SMTP] = None

    def _connect(self) -> None:
        """建立与 SMTP 服务器的连接并登录。

        自动判断加密方式：先尝试 SSL 直连，若失败则回退到明文 + STARTTLS。
        """
        try:
            self._smtp = smtplib.SMTP_SSL(
                self._config.send_server,
                self._config.send_port,
                timeout=10
            )
        except (smtplib.SMTPException, OSError):
            self._smtp = smtplib.SMTP(
                self._config.send_server,
                self._config.send_port,
                timeout=10
            )
            self._smtp.starttls()
        self._smtp.login(self._config.username, self._config.password)

    def _disconnect(self) -> None:
        """关闭与 SMTP 服务器的连接。"""
        if self._smtp:
            try:
                self._smtp.quit()
            except Exception:
                pass
            self._smtp = None

    def _create_message(
        self,
        to: Union[str, List[str]],
        subject: str,
        content: str,
        content_type: str = "plain",
        attachments: Optional[List[str]] = None
    ) -> MIMEMultipart:
        """创建邮件消息对象。

        Args:
            to: 收件人邮箱地址，单个字符串或列表
            subject: 邮件主题
            content: 邮件内容
            content_type: 内容类型，``plain`` 或 ``html``
            attachments: 附件文件路径列表

        Returns:
            组装好的 MIMEMultipart 消息对象。
        """
        msg = MIMEMultipart()
        msg['Message-ID'] = make_msgid()

        sender_name = self._config.sender_name or self._config.username
        msg['From'] = f"{Header(sender_name, 'utf-8')} <{self._config.username}>"
        msg['To'] = ", ".join(to) if isinstance(to, list) else to
        msg['Subject'] = str(Header(subject, 'utf-8'))

        if content_type == "html":
            part = MIMEText(content, 'html', 'utf-8')
        else:
            part = MIMEText(content, 'plain', 'utf-8')
        msg.attach(part)

        if attachments:
            for file_path in attachments:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"附件文件不存在: {file_path}")
                with open(file_path, 'rb') as f:
                    attachment_part = MIMEApplication(f.read())
                    attachment_part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=('utf-8', '', os.path.basename(file_path))
                    )
                    msg.attach(attachment_part)

        return msg

    def send(
        self,
        to: Union[str, List[str]],
        subject: str,
        content: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None,
        is_html: bool = False
    ) -> EmailSendResult:
        """通用邮件发送方法。

        Args:
            to: 收件人邮箱地址，单个字符串或列表
            subject: 邮件主题
            content: 邮件正文内容
            cc: 抄送地址，单个字符串或列表，可选
            bcc: 密送地址，单个字符串或列表，可选
            attachments: 附件文件路径列表，可选
            is_html: 内容是否为 HTML 格式，默认 False

        Returns:
            EmailSendResult，包含 message_id、收件人列表、失败收件人等信息。
        """
        try:
            self._connect()
            content_type = "html" if is_html else "plain"
            msg = self._create_message(to, subject, content, content_type, attachments)
            
            if cc:
                msg['Cc'] = ", ".join(cc) if isinstance(cc, list) else cc
            if bcc:
                msg['Bcc'] = ", ".join(bcc) if isinstance(bcc, list) else bcc

            all_recipients = []
            all_recipients.extend(to if isinstance(to, list) else [to])
            if cc:
                all_recipients.extend(cc if isinstance(cc, list) else [cc])
            if bcc:
                all_recipients.extend(bcc if isinstance(bcc, list) else [bcc])

            assert self._smtp is not None
            failed_recipients = self._smtp.sendmail(
                self._config.username, all_recipients, msg.as_string()
            )
            return EmailSendResult(
                message_id=msg['Message-ID'],
                from_addr=self._config.username,
                recipients=all_recipients,
                failed_recipients=failed_recipients,
            )
        finally:
            self._disconnect()
