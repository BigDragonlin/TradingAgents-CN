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

# 真实发送result（将Markdown格式化并转换为DOCX作为附件）
def test_send_email_real_result():
    from pathlib import Path
    import tempfile
    import markdown  # 保留以兼容旧逻辑或备用展示

    # 使用 ReportExporter 将 md 转为 DOCX 并作为附件发送
    try:
        from web.utils.report_exporter import ReportExporter
    except Exception as e:
        pytest.skip(f"无法导入ReportExporter: {e}")
    exporter = ReportExporter()
    if not getattr(exporter, "pandoc_available", False):
        pytest.skip("pandoc 不可用，跳过 DOCX 转换附件测试")

    # 硬编码股票代码 600276，收集其所有日期下 reports 中的 Markdown 报告
    base_dir = Path(__file__).resolve().parents[2]
    reports_glob = base_dir / "results" / "600276"
    md_files = sorted(reports_glob.glob("*/reports/*.md"))
    if not md_files:
        pytest.skip("No 600276 reports markdown files found to attach")

    docx_attachment_paths = []
    for idx, p in enumerate(md_files):
        md_text = p.read_text(encoding="utf-8", errors="ignore")

        # 构造最小化 results 以复用 generate_pdf_report
        results = {
            "stock_symbol": "600276",
            "decision": {
                "action": "info",
                "confidence": 1.0,
                "risk_score": 0.0,
                "target_price": "",
                "reasoning": f"来源: {p.parent.parent.name}/{p.parent.name}/{p.name}",
            },
            "state": {
                # 将原 md 内容放入一个模块字段中，避免模板为空
                "investment_plan": md_text,
            },
            "llm_provider": "n/a",
            "llm_model": "n/a",
            "analysts": [],
            "research_depth": "文件导入",
            "is_demo": True,
        }

        try:
            docx_bytes = exporter.generate_docx_report(results)
        except Exception:
            # 单个失败不影响整体
            continue

        # 将 DOCX 内容写入临时文件，作为附件
        tmp_docx = Path(tempfile.gettempdir()) / f"{p.stem}-{idx}.docx"
        try:
            tmp_docx.write_bytes(docx_bytes)
            docx_attachment_paths.append(str(tmp_docx))
        except Exception:
            continue

    if not docx_attachment_paths:
        pytest.skip("未生成任何 DOCX 附件，跳过发送")

    subject = f"Results Reports: 600276 docx attachments={len(docx_attachment_paths)}"
    body_text = "该邮件包含 DOCX 报告附件（600276），请查收附件。"

    result = send_email(
        smtp_host="smtp.qq.com",
        smtp_port=587,
        username="1363992060@qq.com",
        password="ghlwbuttcanwgcef",
        subject=subject,
        body_text=body_text,
        from_addr="1363992060@qq.com",
        to_addrs=["1363992060@qq.com"],
        use_tls=True,
        attachments=docx_attachment_paths,
    )
    assert result is True
