import smtplib
import mimetypes
from email.message import EmailMessage
from typing import Iterable, Optional
from pathlib import Path


class EmailSendError(Exception):
    pass


def send_email(
    *,
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    from_addr: str,
    to_addrs: Iterable[str],
    use_tls: bool = True,
    timeout: Optional[float] = None,
    attachments: Optional[Iterable[str]] = None,
) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    # 文本/HTML 正文
    if body_html:
        # 优先使用纯文本作为回退
        msg.set_content(body_text or "")
        msg.add_alternative(body_html, subtype="html")
    else:
        msg.set_content(body_text)

    # 附件处理（可选）
    if attachments:
        for attachment_path in attachments:
            try:
                file_path = Path(attachment_path)
                if not file_path.exists() or not file_path.is_file():
                    # 忽略不存在或非文件的路径
                    continue
                data = file_path.read_bytes()
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if mime_type:
                    maintype, subtype = mime_type.split("/", 1)
                else:
                    maintype, subtype = "application", "octet-stream"
                msg.add_attachment(
                    data,
                    maintype=maintype,
                    subtype=subtype,
                    filename=file_path.name,
                )
            except Exception:
                # 防御式处理单个附件失败，避免影响整体发送
                continue

    try:
        smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)  # type: ignore[arg-type]
        try:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(msg)
            return True
        finally:
            try:
                smtp.quit()
            except Exception:
                # Ensure resources close without masking prior exceptions
                pass
    except smtplib.SMTPException as exc:
        raise EmailSendError(str(exc)) from exc


