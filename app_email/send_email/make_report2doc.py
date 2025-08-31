import logging
from pathlib import Path
import tempfile
from web.utils.report_exporter import ReportExporter, report_exporter
from tradingagents.utils.logging_manager import get_logger
from app_email.send_email import send_email, EmailSendError

logger = get_logger("cli")
class MakeReport2Doc:
    def __init__(self):
        self.report_exporter = ReportExporter()
    
    def make_report2doc(self, stock_symbol: str):
        # 收集其所有日期下 reports 中的 Markdown 报告
        base_dir = Path(__file__).resolve().parents[2]
        reports_glob = base_dir / "results" / stock_symbol
        md_files = sorted(reports_glob.glob("*/reports/*.md"))
        if not md_files:
            logging.error(f"No reports found for {stock_symbol}")
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

        subject = f"Results Reports: {stock_symbol} docx attachments={len(docx_attachment_paths)}"
        body_text = f"该邮件包含 DOCX 报告附件（{stock_symbol}），请查收附件。"
        
        logger.info(f"Sending email to {subject}")
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
        if not result:
            logger.error("Failed to send email")
