import smtplib
from types import SimpleNamespace

import pytest

from app_email.send_email import send_email, EmailSendError


class FakeSMTP:
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = SimpleNamespace(user=None, password=None)
        self.sent_message = None
        self.closed = False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in.user = user
        self.logged_in.password = password

    def send_message(self, msg):
        # Store message for assertions
        self.sent_message = msg

    def quit(self):
        self.closed = True

    # Context manager support if used
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.quit()


def test_send_email_success_with_tls(monkeypatch):
    fake_instance = FakeSMTP("smtp.example.com", 587)

    def fake_smtp_ctor(host, port, timeout=None):
        # Return the precreated instance so we can assert after call
        assert host == "smtp.example.com"
        assert port == 587
        return fake_instance

    monkeypatch.setattr(smtplib, "SMTP", fake_smtp_ctor)

    result = send_email(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="user@example.com",
        password="secret",
        subject="Test Subject",
        body_text="Hello plain",
        from_addr="user@example.com",
        to_addrs=["a@x.com", "b@y.com"],
        use_tls=True,
    )

    assert result is True
    assert fake_instance.started_tls is True
    assert fake_instance.logged_in.user == "user@example.com"
    assert fake_instance.logged_in.password == "secret"
    assert fake_instance.sent_message is not None
    msg = fake_instance.sent_message
    assert msg["Subject"] == "Test Subject"
    assert msg["From"] == "user@example.com"
    assert msg["To"] == "a@x.com, b@y.com"
    # body should contain the plain text
    payload = msg.get_body(preferencelist=("plain",))
    assert payload is not None
    assert "Hello plain" in payload.get_content()


def test_send_email_success_without_tls(monkeypatch):
    fake_instance = FakeSMTP("smtp.example.com", 25)

    def fake_smtp_ctor(host, port, timeout=None):
        assert host == "smtp.example.com"
        assert port == 25
        return fake_instance

    monkeypatch.setattr(smtplib, "SMTP", fake_smtp_ctor)

    result = send_email(
        smtp_host="smtp.example.com",
        smtp_port=25,
        username="user@example.com",
        password="secret",
        subject="No TLS",
        body_text="No tls body",
        from_addr="user@example.com",
        to_addrs=["c@z.com"],
        use_tls=False,
    )

    assert result is True
    assert fake_instance.started_tls is False
    assert fake_instance.sent_message["Subject"] == "No TLS"


def test_send_email_raises_on_smtp_error(monkeypatch):
    class ErrorSMTP(FakeSMTP):
        def send_message(self, msg):
            raise smtplib.SMTPException("send error")

    error_instance = ErrorSMTP("smtp.example.com", 587)

    def fake_smtp_ctor(host, port, timeout=None):
        return error_instance

    monkeypatch.setattr(smtplib, "SMTP", fake_smtp_ctor)

    with pytest.raises(EmailSendError):
        send_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="secret",
            subject="boom",
            body_text="will fail",
            from_addr="user@example.com",
            to_addrs=["x@y.com"],
            use_tls=True,
        )

# 真实发送
def test_send_email_real():
    result = send_email(
        smtp_host="smtp.qq.com",
        smtp_port=587,
        username="1363992060@qq.com",
        password="ghlwbuttcanwgcef",
        subject="Test Subject",
        body_text="Hello plain",
        from_addr="1363992060@qq.com",
        to_addrs=["1363992060@qq.com"],
        use_tls=True,
    )

    assert result is True
