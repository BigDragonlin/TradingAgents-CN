import imaplib
import time
import os
from types import SimpleNamespace
from app_email.receice_email.receiver import receive_emails
import pytest


class FakeIMAP4:
    def __init__(self, host, port=None):
        self.host = host
        self.port = port
        self.starttls_called = False
        self.logged_in = SimpleNamespace(user=None, password=None)
        self.selected_mailbox = None
        self.searched_criteria = None
        self.messages = {
            b"1": (b"OK", [b"From: a@x.com\r\nSubject: Hello\r\n\r\nBody1"]),
            b"2": (b"OK", [b"From: b@y.com\r\nSubject: News\r\n\r\nBody2"]),
        }

    def login(self, user, password):
        self.logged_in.user = user
        self.logged_in.password = password
        return b"OK", [b"Logged in"]

    def select(self, mailbox="INBOX"):
        self.selected_mailbox = mailbox
        return b"OK", [b"2"]

    def search(self, charset, criteria):
        self.searched_criteria = (charset, criteria)
        return b"OK", [b"1 2"]

    def fetch(self, num, parts):
        # Return a simple RFC822-like raw message
        return self.messages.get(num, (b"NO", []))

    def logout(self):
        return b"BYE", [b"Logged out"]


class ErrorIMAP4(FakeIMAP4):
    def login(self, user, password):
        raise imaplib.IMAP4.error("login failed")


def test_receive_basic_success(monkeypatch):
    from app_email.receice_email.receiver import receive_emails

    def fake_imap_ctor(host, port=None):
        assert host == "imap.example.com"
        assert port == 993
        return FakeIMAP4(host, port)

    monkeypatch.setattr(imaplib, "IMAP4_SSL", fake_imap_ctor)

    msgs = receive_emails(
        imap_host="imap.example.com",
        imap_port=993,
        username="user@example.com",
        password="secret",
        mailbox="INBOX",
        criteria="ALL",
        limit=2,
    )

    assert isinstance(msgs, list)
    assert len(msgs) == 2
    # Simple assertions on parsed fields
    assert msgs[0].get("subject") == "Hello"
    assert msgs[0].get("from") == "a@x.com"


def test_receive_login_error(monkeypatch):
    from app_email.receice_email.receiver import receive_emails, EmailReceiveError

    def fake_imap_ctor(host, port=None):
        return ErrorIMAP4(host, port)

    monkeypatch.setattr(imaplib, "IMAP4_SSL", fake_imap_ctor)

    with pytest.raises(EmailReceiveError):
        receive_emails(
            imap_host="imap.example.com",
            imap_port=993,
            username="bad",
            password="bad",
        )

# 真实接收
def test_receive_real():
    seen_keys = set()
    # 可配置参数（环境变量覆盖）
    user_name = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    imap_host = os.getenv("IMAP_HOST", "imap.qq.com")
    imap_port = int(os.getenv("IMAP_PORT", "993"))
    imap_user = os.getenv("IMAP_USER", user_name)
    imap_pass = os.getenv("IMAP_PASS", password)
    imap_mailbox = os.getenv("IMAP_MAILBOX", "INBOX")
    imap_criteria = os.getenv("IMAP_CRITERIA", "UNSEEN")

    poll_interval_seconds = int(os.getenv("EMAIL_POLL_INTERVAL_SECONDS", "10"))
    preview_len = int(os.getenv("EMAIL_PREVIEW_LEN", "500"))
    print_fields = {
        f.strip().lower()
        for f in os.getenv("EMAIL_PRINT_FIELDS", "from,subject,body").split(",")
        if f.strip()
    }
    while True:
        try:
            results = receive_emails(
                imap_host=imap_host,
                imap_port=imap_port,
                username=imap_user,
                password=imap_pass,
                mailbox=imap_mailbox,
                criteria=imap_criteria,
                limit=None,
            )

            new_count = 0
            for msg in results:
                key = (msg.get("from"), msg.get("subject"), msg.get("body"))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                new_count += 1
                print("[NEW EMAIL]")
                if "from" in print_fields:
                    print(f"From: {msg.get('from')}")
                if "subject" in print_fields:
                    print(f"Subject: {msg.get('subject')}")
                if "body" in print_fields:
                    body = msg.get("body", "")
                    preview = body if len(body) <= preview_len else body[:preview_len] + "..."
                    print(f"Body: {preview}")
                print("-" * 60)

            if new_count == 0:
                print("No new emails. Waiting...")
            time.sleep(poll_interval_seconds)
        except KeyboardInterrupt:
            print("Stopped by user.")
            break