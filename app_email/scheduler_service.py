import json, os, tempfile, datetime, re
import hashlib
import time
from typing import List
from tradingagents.utils.database import Database
from pathlib import Path
from tradingagents.utils.logging_manager import get_logger
from web.utils.report_exporter import ReportExporter
from app_email.analysis.analysis import run_analysis
from cli.models import AnalystType
from app_email.send_email import send_email

logger = get_logger("cli")
BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "data" / "sqlite"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DB_DIR / "app_email.db")
def ensure_email_queue_table():
    ddl = """
    CREATE TABLE IF NOT EXISTS incoming_emails (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      from_email TEXT NOT NULL,
      subject TEXT,
      body TEXT,
      body_hash TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','done','failed')),
      error TEXT,
      claimed_at TEXT,
      worker_id TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(from_email, subject, body_hash)
    );
    """
    idx = """
    CREATE INDEX IF NOT EXISTS idx_incoming_emails_status_created
      ON incoming_emails(status, created_at);
    """
    with Database(DB_PATH) as db:
        db.execute(ddl)
        db.execute(idx)

def _hash_body(body: str) -> str:
    body = body or ""
    return hashlib.sha256(body.encode("utf-8", "ignore")).hexdigest()

def enqueue_email(from_email: str, subject, body: str):
    now = _now_iso()
    # 临时加个这个,无意义
    bh = _hash_body(now + body)
    sql = """
    INSERT INTO incoming_emails (from_email, subject, body, body_hash, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """
    try:
        with Database(DB_PATH) as db:
            db.execute(sql, (from_email or "", subject, body, bh, now, now))
    except Exception as e:
        # 唯一约束冲突：视为已入队的重复邮件，忽略即可
        if "UNIQUE constraint failed" in str(e):
            logger.info("去重命中，邮件已存在队列（跳过）")
        else:
            raise

def claim_pending_email(worker_id: str):
    # 使用事务避免并发竞争
    with Database(DB_PATH) as db:
        db.execute("BEGIN IMMEDIATE")
        cur = db.execute(
            "SELECT id FROM incoming_emails WHERE status='pending' ORDER BY created_at LIMIT 1"
        )
        row = cur.fetchone() if cur else None
        if not row:
            db.execute("COMMIT")
            return None
        email_id = row["id"]
        now = _now_iso()
        # 二次条件防止并发更新
        db.execute(
            "UPDATE incoming_emails SET status='processing', claimed_at=?, worker_id=?, updated_at=? "
            "WHERE id=? AND status='pending'",
            (now, worker_id, now, email_id),
        )
        db.execute("COMMIT")
    # 取完整记录返回
    with Database(DB_PATH) as db:
        cur = db.execute("SELECT * FROM incoming_emails WHERE id=?", (email_id,))
        return dict(cur.fetchone()) if cur else None

# 查找pending和processing有多少个
def count_pending_processing():
    with Database(DB_PATH) as db:
        count = db.execute(
            "SELECT COUNT(*) AS c FROM incoming_emails WHERE status IN ('pending', 'processing')"
        )
        return count.fetchone()["c"]

def mark_email_done(email_id: int):
    with Database(DB_PATH) as db:
        db.execute(
            "UPDATE incoming_emails SET status='done', updated_at=?, error=NULL WHERE id=?",
            (_now_iso(), email_id),
        )

def mark_email_failed(email_id: int, error: str):
    with Database(DB_PATH) as db:
        db.execute(
            "UPDATE incoming_emails SET status='failed', updated_at=?, error=? WHERE id=?",
            (_now_iso(), str(error)[:1000], email_id),
        )

def requeue_stale_processing(visibility_timeout_seconds: int = 900):
    # 将超时未完成的 processing 记录回滚为 pending
    threshold = (datetime.datetime.now() - datetime.timedelta(seconds=visibility_timeout_seconds)).strftime("%Y-%m-%d %H:%M:%S")
    with Database(DB_PATH) as db:
        db.execute(
            "UPDATE incoming_emails SET status='pending', updated_at=? "
            "WHERE status='processing' AND (claimed_at IS NULL OR claimed_at < ?)",
            (_now_iso(), threshold),
        )

# 查询user的balancce余额
def check_balance(email):
    with Database(DB_PATH) as db:
        cur = db.execute("SELECT balance FROM users WHERE email=?", (email,))
        balance = cur.fetchone()
        return balance["balance"]

# 扣除balance余额
def debit_balance(email, amount):
    with Database(DB_PATH) as db:
        db.execute("UPDATE users SET balance=balance-? WHERE email=?", (amount, email))
    return check_balance(email)
def consume_email_queue_batch(max_n: int = 1, worker_id = None):
    """
    单次消费最多 max_n 条。建议由调度器高频触发。
    """
    wid = worker_id or os.getenv("HOSTNAME") or "worker"
    requeue_stale_processing()
    processed = 0
    while processed < max_n:
        msg = claim_pending_email(wid)
        if not msg:
            break
        try:
            # 复用已有的处理逻辑
            process_email_job(msg.get("body"), msg.get("from_email"))
            mark_email_done(msg["id"])
        except Exception as e:
            logger.exception(f"消费失败 id={msg['id']}: {e}")
            mark_email_failed(msg["id"], str(e))
        processed += 1
    if processed:
        logger.info(f"消费完成，本次处理 {processed} 条")

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

# 消耗处理
def consume_balance(email, amount):
    balance = debit_balance(email, amount)
    # 发送余额邮件
    info = f"余额还有{balance}"
    user_name = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    subject = info
    body_html = info
    to_email = email
    send_email(
            smtp_host="smtp.qq.com",
            smtp_port=587,
            username=user_name,
            password=password,
            subject=subject,
            body_text="股票多智能体回执",
            body_html=body_html,
            from_addr=user_name,
            to_addrs=[to_email],
            use_tls=True,
            attachments=[],
    )
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
        # 扣除消耗
        consume_balance(from_email, research_depth)

        
    except Exception as e:
        logger.exception(f"处理邮件任务失败: {e}")


def poll_and_run_jobs():
    rows = load_due_jobs()
    for job in rows:
        process_job(job)
