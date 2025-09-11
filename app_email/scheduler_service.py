import json, os, tempfile, datetime, re
from typing import List, Dict
from pathlib import Path
from tradingagents.utils.database import Database
from tradingagents.utils.logging_manager import get_logger
from tradingagents.config.config_manager import ConfigManager
from web.utils.report_exporter import ReportExporter
from app_email.analysis.analysis import run_analysis
from cli.models import AnalystType

logger = get_logger("cli")
BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "data" / "sqlite"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DB_DIR / "app_email.db")


def _now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def estimate_tokens(analysts: List[str], research_depth: str):
    # 与web/utils/analysis_runner.py保持一致
    in_map = {"快速": 1500, "标准": 2500, "深度": 4000}
    out_map = {"快速": 800, "标准": 1200, "深度": 2000}
    per_in = in_map.get(research_depth, 2500)
    per_out = out_map.get(research_depth, 1200)
    return len(analysts) * per_in, len(analysts) * per_out


def estimate_cost(
    provider: str, model: str, analysts: List[str], research_depth: str
) -> float:
    return 1
    cm = ConfigManager()
    in_tok, out_tok = estimate_tokens(analysts, research_depth)
    return cm.calculate_cost(provider, model, in_tok, out_tok)


def load_due_jobs():
    base_sql = """
    SELECT
      id, user_id, ticker, ticker_identifier, analysts, research_depth,
      trigger_type, interval_seconds, cron_expr, next_run_at, active,
      created_at, updated_at
    FROM analysis_jobs
    WHERE active=1 AND (next_run_at IS NULL OR next_run_at <= ?)
    """
    with Database(DB_PATH) as db:
        cur = db.execute(base_sql, (_now_iso(),))
        jobs = [dict(r) for r in cur.fetchall()] if cur else []
        if not jobs:
            logger.info("没有待处理的任务")
            return []

        user_ids = sorted({j["user_id"] for j in jobs})
        placeholders = ",".join(["?"] * len(user_ids))

        u_sql = f"SELECT id, email, balance, currency FROM users WHERE id IN ({placeholders})"
        u_cur = db.execute(u_sql, user_ids)
        users = {row["id"]: dict(row) for row in (u_cur.fetchall() if u_cur else [])}

        for j in jobs:
            u = users.get(j["user_id"], {})
            j["email"] = u.get("email")
            j["balance"] = u.get("balance")
            j["currency"] = u.get("currency")
        return jobs


def update_next_run(job):
    next_time = None
    if job["trigger_type"] == "interval" and job["interval_seconds"]:
        next_dt = datetime.datetime.now() + datetime.timedelta(
            seconds=int(job["interval_seconds"])
        )
        next_time = next_dt.strftime("%Y-%m-%d %H:%M:%S")
    elif job["trigger_type"] == "once":
        next_time = None
        with Database(DB_PATH) as db:
            db.execute(
                "UPDATE analysis_jobs SET active=0, updated_at=? WHERE id=?",
                (_now_iso(), job["id"]),
            )
        return
    # cron可选：若使用croniter，可在此计算
    if next_time:
        with Database(DB_PATH) as db:
            db.execute(
                "UPDATE analysis_jobs SET next_run_at=?, updated_at=? WHERE id=?",
                (next_time, _now_iso(), job["id"]),
            )


def debit_balance(user_id: int, amount: float):
    with Database(DB_PATH) as db:
        db.execute(
            "UPDATE users SET balance=balance-?, updated_at=? WHERE id=?",
            (amount, _now_iso(), user_id),
        )


def credit_balance(user_id: int, amount: float):
    with Database(DB_PATH) as db:
        db.execute(
            "UPDATE users SET balance=balance+?, updated_at=? WHERE id=?",
            (amount, _now_iso(), user_id),
        )


def record_run(
    job_id: int,
    status: str,
    expected_cost: float,
    actual_cost: float,
    report_paths: List[str],
    error: str = None,
):
    with Database(DB_PATH) as db:
        db.execute(
            "INSERT INTO job_runs (job_id, started_at, finished_at, status, expected_cost, actual_cost, report_paths, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job_id,
                _now_iso(),
                _now_iso(),
                status,
                expected_cost,
                actual_cost,
                json.dumps(report_paths, ensure_ascii=False),
                error,
            ),
        )


def generate_docx(results) -> List[str]:
    exporter = ReportExporter()
    docx_bytes = exporter.generate_docx_report(results)
    tmp = (
        Path(tempfile.gettempdir())
        / f"{results['stock_symbol']}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    )
    tmp.write_bytes(docx_bytes)
    return [str(tmp)]


def process_job(job):
    # 解析JSON字段
    analysts = (
        json.loads(job["analysts"])
        if isinstance(job["analysts"], str)
        else job["analysts"]
    )
    # expected_cost = estimate_cost(job["llm_provider"], job["llm_model"], analysts, job["research_depth"])
    expected_cost = 1
    # if job["balance"] < expected_cost:
    #     logger.info(f"用户余额不足，job_id={job['id']}, 需要{expected_cost}, 余额{job['balance']}")
    #     update_next_run(job)
    #     return

    try:
        temp_config = {
            "ticker": job["ticker_identifier"],
            "market": {
                "name": "A股",
                "name_en": "China A-Share",
                "default": "600036",
                "examples": [
                    "000001 (平安银行)",
                    "600036 (招商银行)",
                    "000858 (五粮液)",
                ],
                "format": "6位数字代码 (如: 600036, 000001)",
                "pattern": "^\\d{6}$",
                "data_source": "china_stock",
            },
            "analysis_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "analysts": [
                AnalystType.MARKET,
                # AnalystType.SOCIAL,
                AnalystType.NEWS,
                AnalystType.FUNDAMENTALS,
            ],
            # 阿里
            "backend_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "research_depth": 3,
            "llm_provider": "阿里百炼",
            "shallow_thinker": "qwen-turbo",
            "deep_thinker": "qwen-plus",
        }
        run_analysis(job["email"], job["ticker_identifier"], temp_config)
        # 这里可用真实Token统计写入 actual_cost；首版用expected_cost代替
        actual_cost = expected_cost
        delta = expected_cost - actual_cost
        if abs(delta) > 1e-6:
            # 多退少补（大多数情况下actual≈expected，此处保留逻辑位）
            credit_balance(job["user_id"], delta if delta > 0 else 0)
            if delta < 0:
                debit_balance(job["user_id"], -delta)
        # record_run(job["id"], "success", expected_cost, actual_cost, attachments)
        record_run(job["id"], "success", expected_cost, actual_cost, "")
    except Exception as e:
        # 失败回滚预扣
        credit_balance(job["user_id"], expected_cost)
        record_run(job["id"], "failed", expected_cost, 0.0, [], str(e))
        logger.exception(f"任务执行失败 job_id={job['id']}: {e}")
    finally:
        update_next_run(job)


# 处理直接通过邮件触发的任务
def process_email_job(email_body, from_email):
    try:
        logger.info("处理邮件任务 body")
        logger.info(email_body)
        logger.info("处理邮件任务 from_email")
        logger.info(from_email)
        # 预处理并解析邮件正文中的 JSON（容错：去掉包裹引号、替换单引号等）
        raw = (email_body or "").strip()
        if raw.startswith("'") and raw.endswith("'"):
            raw = raw[1:-1]
        raw = raw.replace("&nbsp;", " ").replace("\u00a0", " ").replace("\n", "").replace("'", '"')
        logger.info(raw)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"处理邮件任务失败: 解析json失败" + str(e))
            return

        # 提取股票代码并规范为6位数字字符串
        ticker_value = payload.get("股票代码")
        ticker_str = re.sub(r"\D", "", str(ticker_value))
        ticker_identifier = ticker_str.zfill(6)

        # 将中文分析师名称映射为内部 AnalystType 枚举
        analyst_name_map = {
            "市场分析": AnalystType.MARKET,
            "新闻分析": AnalystType.NEWS,
            "基本面分析": AnalystType.FUNDAMENTALS,
            "市场情绪分析": AnalystType.SOCIAL,
            "情绪分析": AnalystType.SOCIAL,
        }
        requested_analysts = payload.get("分析师")
        analysts = []
        for name in requested_analysts:
            mapped = analyst_name_map.get(str(name).strip())
            if mapped and mapped not in analysts:
                analysts.append(mapped)
        # 若为空则给出一个合理默认
        if not analysts:
            analysts = [AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS]

        research_depth = payload.get("研究深度")
        try:
            research_depth = int(research_depth)
        except Exception:
            research_depth = 3
        temp_config = {
            "ticker": ticker_identifier,
            "market": {
                "name": "A股",
                "name_en": "China A-Share",
                "default": "600036",
                "examples": [
                    "000001 (平安银行)",
                    "600036 (招商银行)",
                    "000858 (五粮液)",
                ],
                "format": "6位数字代码 (如: 600036, 000001)",
                "pattern": "^\\d{6}$",
                "data_source": "china_stock",
            },
            "analysis_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "analysts": analysts,
            "backend_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "research_depth": research_depth,
            "llm_provider": "阿里百炼",
            "shallow_thinker": "qwen-turbo",
            "deep_thinker": "qwen-plus",
        }

        run_analysis(from_email, ticker_identifier, temp_config)
    except Exception as e:
        logger.exception(f"处理邮件任务失败: {e}")


def poll_and_run_jobs():
    rows = load_due_jobs()
    for job in rows:
        process_job(job)
