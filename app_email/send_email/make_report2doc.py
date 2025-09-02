import logging
from pathlib import Path
import tempfile
from datetime import datetime
from web.utils.report_exporter import ReportExporter, report_exporter
from tradingagents.utils.logging_manager import get_logger
from app_email.send_email import send_email, EmailSendError

logger = get_logger("cli")
class MakeReport2Doc:
    def __init__(self, send2email: str, stock_symbol: str):
        self.report_exporter = ReportExporter()
        self.send2email = send2email
        self.stock_symbol = stock_symbol

    def make_report2doc(self):
        # 仅收集“当天”目录下 reports 中的 Markdown 报告
        stock_symbol = self.stock_symbol
        base_dir = Path(__file__).resolve().parents[2]
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_reports_dir = base_dir / "results" / stock_symbol / today_str / "reports"
        md_files = sorted(today_reports_dir.glob("*.md"))
        if not md_files:
            logging.error(
                f"No reports found for {stock_symbol} on {today_str} in {today_reports_dir}"
            )
        if not getattr(report_exporter, "pandoc_available", False):
            logger.error("Pandoc is not available")

        docx_attachment_paths = []
        for idx, p in enumerate(md_files):
            md_text = p.read_text(encoding="utf-8", errors="ignore")
            # 构造最小化 results 以复用 generate_pdf_report
            results = {
                "stock_symbol": stock_symbol,
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
                docx_bytes = report_exporter.generate_docx_report(results)
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
            logger.error("No DOCX attachments generated")

        subject = f"分析股票代码: {stock_symbol}, 请注意查收={len(docx_attachment_paths)}附件"
        body_text = f"该邮件包含股票代码（{stock_symbol}）的附件，请注意查收附件。"
        result = send_email(
            smtp_host="smtp.qq.com",
            smtp_port=587,
            username="1363992060@qq.com",
            password="ghlwbuttcanwgcef",
            subject=subject,
            body_text=body_text,
            from_addr="1363992060@qq.com",
            to_addrs=[self.send2email],
            use_tls=True,
            attachments=docx_attachment_paths,
        )
        if not result:
            logger.error("Failed to send email")