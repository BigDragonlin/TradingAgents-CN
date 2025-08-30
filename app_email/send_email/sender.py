import smtplib
from email.message import EmailMessage
from typing import Iterable, Optional


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
    from_addr: str,
    to_addrs: Iterable[str],
    use_tls: bool = True,
    timeout: Optional[float] = None,
) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body_text)

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


