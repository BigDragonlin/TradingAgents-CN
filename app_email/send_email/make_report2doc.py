import logging
from pathlib import Path
import os
import tempfile
from datetime import datetime
import re
from web.utils.report_exporter import ReportExporter, report_exporter
import pypandoc
from tradingagents.utils.logging_manager import get_logger
from app_email.send_email import send_email, EmailSendError

logger = get_logger("cli")
class MakeReport2Doc:
    def __init__(self, send2email: str, stock_symbol: str):
        self.report_exporter = ReportExporter()
        self.send2email = send2email
        self.stock_symbol = stock_symbol

    def make_report2doc(self):
        # 收集最新日期目录下 reports 中的 Markdown 报告，路径兼容 TRADINGAGENTS_RESULTS_DIR
        stock_symbol = self.stock_symbol
        project_root = Path(__file__).resolve().parents[2]

        # 解析 results 根目录：优先环境变量 TRADINGAGENTS_RESULTS_DIR，否则使用项目根目录下 results
        results_dir_env = os.getenv("TRADINGAGENTS_RESULTS_DIR")
        if results_dir_env:
            results_base = Path(results_dir_env)
            if not results_base.is_absolute():
                results_base = project_root / results_dir_env
        else:
            results_base = project_root / "results"

        stock_dir = results_base / stock_symbol
        if not stock_dir.exists():
            logger.error(f"Results directory not found: {stock_dir}")
            return

        # 在股票目录下选择最新的日期子目录
        date_dirs = [p for p in stock_dir.iterdir() if p.is_dir()]
        if not date_dirs:
            logger.error(f"No date directories under {stock_dir}")
            return
        latest_date_dir = max(date_dirs, key=lambda p: p.name)
        reports_dir = latest_date_dir / "reports"
        md_files = sorted(reports_dir.glob("*.md"))
        if not md_files:
            logging.error(
                f"No reports found for {stock_symbol} in {reports_dir}"
            )
        if not getattr(report_exporter, "pandoc_available", False):
            logger.error("Pandoc is not available")

        docx_attachment_paths = []
        for idx, p in enumerate(md_files):
            md_text = p.read_text(encoding="utf-8", errors="ignore")

            # 直接将原始Markdown转换为DOCX，不注入任何模板内容
            tmp_docx = Path(tempfile.gettempdir()) / f"{p.stem}.docx"
            try:
                extra_args = ["--from=markdown-yaml_metadata_block"]
                pypandoc.convert_text(
                    md_text,
                    "docx",
                    format="markdown",
                    outputfile=str(tmp_docx),
                    extra_args=extra_args,
                )
                # 确认文件已生成且非空
                if tmp_docx.exists() and tmp_docx.stat().st_size > 0:
                    docx_attachment_paths.append(str(tmp_docx))
                else:
                    continue
            except Exception:
                # 单个失败不影响整体
                continue

        if not docx_attachment_paths:
            logger.error("No DOCX attachments generated")

        # 合并 reports_dir 内所有 Markdown，按文件名后缀数字升序组合（如 *_01.md, *_6.md, *_12.md）
        section_title_overrides = {
            "市场分析_01.md": "🎯 市场分析",
            "市场情绪分析_02.md": "💭 市场情绪分析",
            "新闻事件分析_03.md": "📰 新闻事件分析",
            "基本面分析_04.md": "💰 基本面分析",
            "研究团队决策_05.md": "🔬 研究团队决策",
            "交易计划_06.md": "🎯 交易计划",
            "最终投资决策_07.md": "✅ 最终投资决策",
        }

        def _suffix_number(name: str) -> int:
            m = re.search(r"_(\d+)\.md$", name)
            return int(m.group(1)) if m else 999999

        all_md_files = sorted(reports_dir.glob("*.md"), key=lambda p: (_suffix_number(p.name), p.name))

        combined_parts = [
            f"# {stock_symbol} 报告汇总",
            f"分析日期：{latest_date_dir.name}",
            "",
        ]
        for fp in all_md_files:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                # 单个文件失败不影响整体
                continue
            title = section_title_overrides.get(fp.name, fp.stem)
            combined_parts.append(f"---\n\n## {title}\n\n{content}\n")

        combined_markdown = "\n".join(combined_parts).strip()
        # 转为 HTML，用于邮件 HTML 正文
        body_html = None
        if combined_markdown:
            try:
                extra_args = ["--from=markdown-yaml_metadata_block"]
                body_html = pypandoc.convert_text(
                    combined_markdown,
                    "html",
                    format="markdown",
                    extra_args=extra_args,
                )
            except Exception:
                body_html = None

        subject = f"分析股票代码: {stock_symbol}, 请注意查收{len(docx_attachment_paths)}附件"
        body_text = combined_markdown if combined_markdown else f"该邮件包含股票代码（{stock_symbol}）的附件，请注意查收附件。"
        user_name = os.getenv("EMAIL_USER")
        password = os.getenv("EMAIL_PASSWORD")
        result = send_email(
            smtp_host="smtp.qq.com",
            smtp_port=587,
            username=user_name,
            password=password,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_addr="1363992060@qq.com",
            to_addrs=[self.send2email],
            use_tls=True,
            attachments=docx_attachment_paths,
        )
        if not result:
            logger.error("Failed to send email")