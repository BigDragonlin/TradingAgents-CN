-- 用户与余额
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  balance REAL NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'CNY',
  status INTEGER NOT NULL DEFAULT 1, -- 1启用 0禁用
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 任务配置（触发时间）
CREATE TABLE IF NOT EXISTS analysis_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  ticker TEXT NOT NULL,
  --股票代码
  ticker_identifier TEXT NOT NULL,
  analysts TEXT NOT NULL,           -- JSON字符串: ["Market Analyst", ...]
  research_depth INTEGER NOT NULL,  -- 1,2,3
  trigger_type TEXT NOT NULL,       -- "once"|"interval"|"cron"
  interval_seconds INTEGER,         -- 仅当 trigger_type='interval'
  cron_expr TEXT,                   -- 可选，需要croniter支持
  next_run_at TEXT,                 -- ISO时间，到点执行；执行后更新
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 运行记录与结算
CREATE TABLE IF NOT EXISTS job_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  status TEXT,                      -- "success"|"failed"
  expected_cost REAL,
  actual_cost REAL,
  report_paths TEXT,                -- JSON字符串: [".../xxx.docx", ...]
  error TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (job_id) REFERENCES analysis_jobs(id)
);